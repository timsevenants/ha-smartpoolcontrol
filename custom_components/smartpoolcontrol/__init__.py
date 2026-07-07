"""The Smart Pool Connect integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .api import SmartPoolControlClient
from .const import CONF_API_KEY, CONF_BASE_URL, CONF_POOL_ID, DEFAULT_BASE_URL
from .coordinator import SmartPoolControlCoordinator

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

type SmartPoolConfigEntry = ConfigEntry[SmartPoolControlCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: SmartPoolConfigEntry) -> bool:
    """Set up Smart Pool Connect from a config entry."""
    client = SmartPoolControlClient(
        entry.data[CONF_API_KEY],
        base_url=entry.data.get(CONF_BASE_URL, DEFAULT_BASE_URL),
        pool_id=entry.data[CONF_POOL_ID],
    )

    coordinator = SmartPoolControlCoordinator(hass, client, entry)
    try:
        # Raises ConfigEntryAuthFailed / ConfigEntryNotReady on failure.
        await coordinator.async_config_entry_first_refresh()
    except Exception:
        await client.close()
        raise

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SmartPoolConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.client.close()
    return unload_ok
