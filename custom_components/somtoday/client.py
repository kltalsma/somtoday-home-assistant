"""Client for the undocumented Somtoday REST API.

This uses Somtoday's legacy password grant. Some schools disable that grant or
use SSO; those installations cannot be configured with this integration.
"""

from __future__ import annotations

from datetime import date
import logging
from typing import Any

from aiohttp import ClientError, ClientSession

from .const import CLIENT_ID, ORGANISATIONS_URL, TOKEN_URL
from .exceptions import SomtodayAuthenticationError, SomtodayConnectionError

_LOGGER = logging.getLogger(__name__)


class SomtodayClient:
    """Authenticated Somtoday API client."""

    def __init__(self, session: ClientSession, school_uuid: str, username: str, password: str) -> None:
        """Initialize the client."""
        self._session = session
        self._school_uuid = school_uuid
        self._username = username
        self._password = password
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._api_url: str | None = None

    @staticmethod
    async def find_school(session: ClientSession, school_name: str) -> dict[str, str]:
        """Resolve a school name to its public Somtoday organisation record."""
        try:
            async with session.get(ORGANISATIONS_URL, timeout=20) as response:
                response.raise_for_status()
                payload = await response.json(content_type=None)
        except (ClientError, TimeoutError, ValueError) as err:
            raise SomtodayConnectionError("Kon de Somtoday-scholenlijst niet ophalen") from err

        organisations = payload[0].get("instellingen", []) if isinstance(payload, list) else []
        normalized = school_name.casefold().strip()
        exact = [item for item in organisations if item.get("naam", "").casefold().strip() == normalized]
        matches = exact or [item for item in organisations if normalized in item.get("naam", "").casefold()]
        if len(matches) != 1:
            raise SomtodayConnectionError("School niet gevonden of niet eenduidig; gebruik de volledige schoolnaam")
        school = matches[0]
        return {"uuid": school["uuid"], "name": school["naam"], "city": school.get("plaats", "")}

    async def async_login(self) -> None:
        """Acquire an API token using the native app's password grant."""
        data = {
            "grant_type": "password",
            "username": f"{self._school_uuid}\\{self._username}",
            "password": self._password,
            "scope": "openid",
            "client_id": CLIENT_ID,
        }
        await self._async_token_request(data, is_login=True)

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
