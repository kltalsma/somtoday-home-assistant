"""Calendar entity for the Somtoday timetable."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.util import dt as dt_util

from . import SomtodayConfigEntry
from .coordinator import SomtodayCoordinator


async def async_setup_entry(hass, entry: SomtodayConfigEntry, async_add_entities) -> None:
    """Set up the Somtoday calendar."""
    async_add_entities([SomtodayCalendar(entry.runtime_data, entry)])


def _event_from_appointment(appointment: dict[str, Any]) -> CalendarEvent | None:
    """Convert a Somtoday appointment to a Home Assistant calendar event."""
    try:
        start = dt_util.parse_datetime(appointment["beginDatumTijd"])
        end = dt_util.parse_datetime(appointment["eindDatumTijd"])
    except (KeyError, TypeError, ValueError):
        return None
    if start is None or end is None:
        return None
    additional = appointment.get("additionalObjects", {})
    subject = additional.get("vak", {})
    teacher = additional.get("docentAfkortingen", "")
    summary = subject.get("naam") or appointment.get("titel") or appointment.get("afspraakType", {}).get("naam", "Afspraak")
    details = [appointment.get("omschrijving", "")]
    if teacher:
        details.append(f"Docent: {teacher}")
    if appointment.get("beginLesuur"):
        details.append(f"Lesuur: {appointment['beginLesuur']}-{appointment.get('eindLesuur', appointment['beginLesuur'])}")
    return CalendarEvent(summary=summary, start=start, end=end, description="\n".join(filter(None, details)) or None, location=appointment.get("locatie"))


class SomtodayCalendar(CalendarEntity):
    """Expose a student's Somtoday timetable as a calendar."""

    _attr_has_entity_name = True
    _attr_translation_key = "timetable"

    def __init__(self, coordinator: SomtodayCoordinator, entry: SomtodayConfigEntry) -> None:
        self.coordinator = coordinator
        self._attr_unique_id = f"{entry.unique_id}_timetable"

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next appointment."""
        now = dt_util.now()
        events = [event for item in self.coordinator.data["schedule"] if (event := _event_from_appointment(item)) and event.end > now]
        return min(events, key=lambda event: event.start, default=None)

    async def async_get_events(self, hass, start_date: datetime, end_date: datetime) -> list[CalendarEvent]:
        """Return events requested by the calendar UI, including older dates."""
        items = await self.coordinator.client.async_get_schedule(start_date.date(), end_date.date())
        return [event for item in items if (event := _event_from_appointment(item)) and event.end >= start_date and event.start <= end_date]
