"""Data coordinator for Somtoday."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .client import SomtodayClient
from .const import DEFAULT_LOOKAHEAD_DAYS, DOMAIN, UPDATE_INTERVAL
from .exceptions import SomtodayError

_LOGGER = logging.getLogger(__name__)


class SomtodayCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch the current roster and grades for one student."""

    def __init__(self, hass: HomeAssistant, client: SomtodayClient) -> None:
        super().__init__(hass, logger=_LOGGER, name=DOMAIN, update_interval=UPDATE_INTERVAL)
        self.client = client
        self.student: dict[str, Any] | None = None

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            if self.student is None:
                self.student = await self.client.async_get_student()
            today = dt_util.now().date()
            schedule = await self.client.async_get_schedule(today - timedelta(days=1), today + timedelta(days=DEFAULT_LOOKAHEAD_DAYS))
            try:
                grades = await self.client.async_get_grades(self.student["links"][0]["id"])
            except SomtodayError as err:
                # A school may allow a timetable while withholding grade access.
                _LOGGER.warning("Somtoday grades are unavailable: %s", err)
                grades = []
            return {"schedule": schedule, "grades": grades}
        except SomtodayError as err:
            raise UpdateFailed(str(err)) from err
