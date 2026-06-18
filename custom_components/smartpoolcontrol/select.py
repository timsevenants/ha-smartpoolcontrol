"""Select platform for Smart Pool Control (pump speed, lighting mode)."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SmartPoolConfigEntry
from .const import (
    LIGHTING_MODES,
    LIGHTING_MODES_REVERSE,
    PUMP_SPEEDS,
    PUMP_SPEEDS_REVERSE,
)
from .entity import SmartPoolEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartPoolConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the select entities."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            PumpSpeedSelect(coordinator),
            LightingModeSelect(coordinator),
        ]
    )


class PumpSpeedSelect(SmartPoolEntity, SelectEntity):
    """Pump speed of filter schedule 1.

    The portal has no read-back of the schedule speed on the measurements
    page, so the option is applied optimistically and mirrored from the live
    pump-speed sensor when available.
    """

    _attr_translation_key = "pump_speed"
    _attr_icon = "mdi:pump"
    _attr_options = list(PUMP_SPEEDS.values())

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "pump_speed_select")
        self._optimistic: str | None = None

    @property
    def current_option(self) -> str | None:
        return self.coordinator.data.pump_speed or self._optimistic

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.client.async_set_pump_speed(PUMP_SPEEDS_REVERSE[option])
        self._optimistic = option
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()


class LightingModeSelect(SmartPoolEntity, SelectEntity):
    """Lighting program. Write-only on the portal, so kept optimistic."""

    _attr_translation_key = "lighting_mode"
    _attr_icon = "mdi:palette"
    _attr_options = list(LIGHTING_MODES.values())

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "lighting_mode")
        self._optimistic: str | None = None

    @property
    def current_option(self) -> str | None:
        return self._optimistic

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.client.async_set_lighting_mode(
            LIGHTING_MODES_REVERSE[option]
        )
        self._optimistic = option
        self.async_write_ha_state()
