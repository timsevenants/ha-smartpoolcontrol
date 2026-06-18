"""The Smart Pool Control integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from .api import AuthenticationError, SmartPoolControlClient, SmartPoolControlError
from .const import CONF_BASE_URL, CONF_POOL_ID, DEFAULT_BASE_URL, DOMAIN
from .coordinator import SmartPoolControlCoordinator

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.COVER,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

type SmartPoolConfigEntry = ConfigEntry[SmartPoolControlCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: SmartPoolConfigEntry) -> bool:
    """Set up Smart Pool Control from a config entry."""
    client = SmartPoolControlClient(
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        base_url=entry.data.get(CONF_BASE_URL, DEFAULT_BASE_URL),
        pool_id=entry.data.get(CONF_POOL_ID),
    )

    try:
        await client.async_login()
    except AuthenticationError as err:
        await client.close()
        raise ConfigEntryAuthFailed(str(err)) from err
    except SmartPoolControlError as err:
        await client.close()
        raise ConfigEntryNotReady(str(err)) from err

    coordinator = SmartPoolControlCoordinator(hass, client, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SmartPoolConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.client.close()
    return unload_ok
