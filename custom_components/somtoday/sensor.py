"""Grade sensor for Somtoday."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import SomtodayConfigEntry
from .coordinator import SomtodayCoordinator


async def async_setup_entry(hass, entry: SomtodayConfigEntry, async_add_entities) -> None:
    """Set up the latest grade sensor."""
    async_add_entities([SomtodayLatestGradeSensor(entry.runtime_data, entry)])


def _grade_date(grade: dict[str, Any]) -> datetime:
    return dt_util.parse_datetime(grade.get("datumInvoer")) or datetime.min.replace(tzinfo=dt_util.UTC)


class SomtodayLatestGradeSensor(CoordinatorEntity[SomtodayCoordinator], SensorEntity):
    """Show the most recently entered numeric grade."""

    _attr_has_entity_name = True
    _attr_translation_key = "latest_grade"
    _attr_icon = "mdi:school-outline"

    def __init__(self, coordinator: SomtodayCoordinator, entry: SomtodayConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.unique_id}_latest_grade"

    @property
    def _latest(self) -> dict[str, Any] | None:
        grades = [grade for grade in self.coordinator.data["grades"] if grade.get("geldendResultaat") or grade.get("resultaat")]
        return max(grades, key=_grade_date, default=None)

    @property
    def native_value(self) -> str | None:
        grade = self._latest
        return grade.get("geldendResultaat") or grade.get("resultaat") if grade else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        grade = self._latest
        if grade is None:
            return None
        subject = grade.get("vak", {})
        return {"vak": subject.get("naam"), "datum": grade.get("datumInvoer"), "omschrijving": grade.get("omschrijving")}
