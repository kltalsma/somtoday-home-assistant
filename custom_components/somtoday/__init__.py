"""Somtoday Home Assistant integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import SomtodayClient
from .const import CONF_PASSWORD, CONF_SCHOOL, CONF_USERNAME, DOMAIN, PLATFORMS
from .coordinator import SomtodayCoordinator

SomtodayConfigEntry = ConfigEntry


async def async_setup_entry(hass: HomeAssistant, entry: SomtodayConfigEntry) -> bool:
    """Set up Somtoday from a config entry."""
    client = SomtodayClient(
        async_get_clientsession(hass), entry.data["school_uuid"], entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD]
    )
    coordinator = SomtodayCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SomtodayConfigEntry) -> bool:
    """Unload a Somtoday config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
