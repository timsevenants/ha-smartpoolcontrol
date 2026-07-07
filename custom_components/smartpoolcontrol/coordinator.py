"""Data update coordinator for Smart Pool Connect."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    AuthenticationError,
    PoolStatus,
    SmartPoolControlClient,
    SmartPoolControlError,
)
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class SmartPoolControlCoordinator(DataUpdateCoordinator[PoolStatus]):
    """Polls the API and shares the parsed status with all entities."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: SmartPoolControlClient,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.client = client
        self.entry = entry

    async def _async_update_data(self) -> PoolStatus:
        try:
            return await self.client.async_get_status()
        except AuthenticationError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except SmartPoolControlError as err:
            raise UpdateFailed(str(err)) from err
