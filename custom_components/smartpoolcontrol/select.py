"""Select platform for Smart Pool Connect (pump speed)."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SmartPoolConfigEntry
from .const import PUMP_SPEEDS
from .entity import SmartPoolControllableEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartPoolConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the select entities."""
    coordinator = entry.runtime_data
    async_add_entities([PumpSpeedSelect(coordinator)])


class PumpSpeedSelect(SmartPoolControllableEntity, SelectEntity):
    """Configured filter pump speed (``filter.config.pump_speed``)."""

    _attr_translation_key = "pump_speed"
    _attr_icon = "mdi:pump"
    _attr_options = list(PUMP_SPEEDS)

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "pump_speed_select")

    @property
    def current_option(self) -> str | None:
        speed = self.coordinator.data.pump_speed
        return speed if speed in self._attr_options else None

    async def async_select_option(self, option: str) -> None:
        self._check_online()
        await self.coordinator.client.async_set_pump_speed(option)
        await self.coordinator.async_request_refresh()
