"""Client for the undocumented Somtoday REST API.

This uses Somtoday's legacy password grant. Some schools disable that grant or
use SSO; those installations cannot be configured with this integration.
"""

from __future__ import annotations

import base64
from datetime import date
import hashlib
import logging
import secrets
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse

from aiohttp import ClientError, ClientSession

from .const import AUTHORIZE_URL, CLIENT_ID, REDIRECT_URI, TOKEN_URL
from .exceptions import SomtodayAuthenticationError, SomtodayConnectionError

_LOGGER = logging.getLogger(__name__)


class SomtodayClient:
    """Authenticated Somtoday API client."""

    def __init__(self, session: ClientSession, tenant_id: str, username: str, password: str) -> None:
        """Initialize the client."""
        self._session = session
        self._tenant_id = tenant_id
        self._username = username
        self._password = password
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._api_url: str | None = None

    async def async_login(self) -> None:
        """Acquire an API token through the current Somtoday native-app flow."""
        verifier = secrets.token_urlsafe(96)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
        parameters = {
            "redirect_uri": REDIRECT_URI,
            "client_id": CLIENT_ID,
            "state": secrets.token_urlsafe(16),
            "response_type": "code",
            "scope": "openid",
            "tenant_uuid": self._tenant_id,
            "session": "no_session",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        try:
            async with self._session.get(AUTHORIZE_URL, params=parameters, allow_redirects=False, timeout=20) as response:
                location = response.headers.get("Location")
                response.raise_for_status()
            if not location:
                raise SomtodayConnectionError("Somtoday gaf geen inloglocatie terug")
            login_url = urljoin(AUTHORIZE_URL, location)
            auth = parse_qs(urlparse(login_url).query).get("auth", [None])[0]
            if not auth:
                raise SomtodayConnectionError("Somtoday gaf geen inlogcode terug")

            # This response establishes the session cookie and redirects to the login form.
            async with self._session.get(login_url, allow_redirects=False, timeout=20) as response:
                form_location = response.headers.get("Location")
                response.raise_for_status()
            if not form_location:
                raise SomtodayConnectionError("Somtoday gaf geen loginformulier terug")
            form_url = urljoin(login_url, form_location)
            auth = parse_qs(urlparse(form_url).query).get("auth", [None])[0]
            if not auth:
                raise SomtodayConnectionError("Somtoday gaf geen geldige loginstatus terug")
            async with self._session.get(form_url, allow_redirects=False, timeout=20) as response:
                response.raise_for_status()
            async with self._session.post(
                "https://inloggen.somtoday.nl/?0-1.-panel-signInForm",
                params={"auth": auth},
                data={
                    "loginLink": "x",
                    "usernameFieldPanel:usernameFieldPanel_body:usernameField": self._username,
                    "passwordFieldPanel:passwordFieldPanel_body:passwordField": self._password,
                },
                headers={"Origin": "https://inloggen.somtoday.nl"},
                allow_redirects=False,
                timeout=20,
            ) as response:
                location = response.headers.get("Location")
                if response.status in (400, 401, 403) or not location:
                    raise SomtodayAuthenticationError("Inloggen bij Somtoday is niet gelukt")
                response.raise_for_status()
        except SomtodayAuthenticationError:
            raise
        except (ClientError, TimeoutError, ValueError) as err:
            raise SomtodayConnectionError("Kon de Somtoday-inlogpagina niet bereiken") from err

        authorization_code = parse_qs(urlparse(location).query).get("code", [None])[0]
        if not authorization_code:
            raise SomtodayAuthenticationError("Somtoday vraagt een andere inlogmethode (SSO/2FA)")
        await self._async_token_request(
            {
                "grant_type": "authorization_code",
                "session": "no_session",
                "scope": "openid",
                "client_id": CLIENT_ID,
                "tenant_uuid": self._tenant_id,
                "code": authorization_code,
                "code_verifier": verifier,
            },
            is_login=True,
        )

    async def _async_token_request(self, data: dict[str, str], *, is_login: bool) -> None:
        try:
            async with self._session.post(TOKEN_URL, data=data, timeout=20) as response:
                payload = await response.json(content_type=None)
                if response.status in (400, 401, 403):
                    raise SomtodayAuthenticationError("Inloggen bij Somtoday is niet gelukt")
                response.raise_for_status()
        except SomtodayAuthenticationError:
            raise
        except (ClientError, TimeoutError, ValueError) as err:
            if is_login:
                raise SomtodayConnectionError("Kon niet inloggen bij Somtoday") from err
            raise SomtodayAuthenticationError("Somtoday-sessie kon niet worden vernieuwd") from err

        try:
            self._access_token = payload["access_token"]
            self._refresh_token = payload["refresh_token"]
            self._api_url = payload["somtoday_api_url"].rstrip("/")
        except (KeyError, AttributeError) as err:
            raise SomtodayConnectionError("Somtoday gaf geen geldige sessie terug") from err

    async def _async_refresh(self) -> None:
        if not self._refresh_token:
            await self.async_login()
            return
        await self._async_token_request(
            {"grant_type": "refresh_token", "refresh_token": self._refresh_token, "scope": "openid", "client_id": CLIENT_ID},
            is_login=False,
        )

    async def _async_get(
        self,
        path: str,
        params: list[tuple[str, str]] | None = None,
        extra_headers: dict[str, str] | None = None,
        *,
        retry: bool = True,
    ) -> dict[str, Any]:
        if not self._access_token or not self._api_url:
            await self.async_login()
        assert self._api_url is not None
        headers = {"Accept": "application/json", "Authorization": f"Bearer {self._access_token}"}
        if extra_headers:
            headers.update(extra_headers)
        try:
            async with self._session.get(f"{self._api_url}{path}", params=params, headers=headers, timeout=20) as response:
                if response.status == 401 and retry:
                    await self._async_refresh()
                    return await self._async_get(path, params, extra_headers, retry=False)
                response.raise_for_status()
                return await response.json(content_type=None)
        except SomtodayAuthenticationError:
            raise
        except (ClientError, TimeoutError, ValueError) as err:
            raise SomtodayConnectionError(f"Somtoday-verzoek voor {path} is mislukt") from err

    async def async_get_student(self) -> dict[str, Any]:
        """Return the student associated with these credentials."""
        payload = await self._async_get("/rest/v1/leerlingen")
        items = payload.get("items", [])
        if not items:
            raise SomtodayConnectionError("Somtoday gaf geen leerling voor dit account terug")
        return items[0]

    async def async_get_schedule(self, start: date, end: date) -> list[dict[str, Any]]:
        """Return appointments within a date range."""
        payload = await self._async_get(
            "/rest/v1/afspraken",
            [("sort", "asc-id"), ("additional", "vak"), ("additional", "docentAfkortingen"), ("begindatum", start.isoformat()), ("einddatum", end.isoformat())],
        )
        return payload.get("items", [])

    async def async_get_grades(self, student_id: int | str) -> list[dict[str, Any]]:
        """Return the first 100 current grade results."""
        payload = await self._async_get(
            f"/rest/v1/resultaten/huidigVoorLeerling/{student_id}", extra_headers={"Range": "items=0-99"}
        )
        return payload.get("items", [])
