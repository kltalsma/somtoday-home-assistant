"""Config flow for Somtoday."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import SomtodayClient
from .const import CONF_PASSWORD, CONF_SCHOOL, CONF_USERNAME, DOMAIN
from .exceptions import SomtodayAuthenticationError, SomtodayConnectionError


class SomtodayConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a Somtoday config flow."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                session = async_get_clientsession(self.hass)
                school = await SomtodayClient.find_school(session, user_input[CONF_SCHOOL])
                client = SomtodayClient(session, school["uuid"], user_input[CONF_USERNAME], user_input[CONF_PASSWORD])
                await client.async_login()
                student = await client.async_get_student()
            except SomtodayAuthenticationError:
                errors["base"] = "invalid_auth"
            except SomtodayConnectionError:
                errors["base"] = "cannot_connect"
            else:
                student_id = str(student["links"][0]["id"])
                await self.async_set_unique_id(student_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Somtoday - {student.get('roepnaam', user_input[CONF_USERNAME])}",
                    data={**user_input, "school_uuid": school["uuid"], "school_name": school["name"]},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_SCHOOL): str,
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
            }),
            errors=errors,
            description_placeholders={"hint": "Gebruik de volledige naam zoals die in Somtoday staat."},
        )
