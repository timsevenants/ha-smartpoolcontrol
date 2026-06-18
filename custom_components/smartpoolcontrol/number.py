"""Number platform for Smart Pool Control (target setpoints)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SmartPoolConfigEntry
from .api import PoolStatus, SmartPoolControlClient
from .entity import SmartPoolEntity


@dataclass(frozen=True, kw_only=True)
class SmartPoolNumberDescription(NumberEntityDescription):
    """Describes a writable setpoint."""

    value_fn: Callable[[PoolStatus], float | None]
    set_fn: Callable[[SmartPoolControlClient, float], Awaitable[None]]


NUMBERS: tuple[SmartPoolNumberDescription, ...] = (
    SmartPoolNumberDescription(
        key="ph_target",
        translation_key="ph_target",
        icon="mdi:ph",
        native_min_value=6.8,
        native_max_value=7.6,
        native_step=0.1,
        mode=NumberMode.BOX,
        value_fn=lambda s: s.ph_target,
        set_fn=lambda c, v: c.async_set_ph_target(v),
    ),
    SmartPoolNumberDescription(
        key="rx_target",
        translation_key="rx_target",
        icon="mdi:flash",
        native_unit_of_measurement="mV",
        native_min_value=0,
        native_max_value=999,
        native_step=10,
        mode=NumberMode.BOX,
        value_fn=lambda s: s.rx_target,
        set_fn=lambda c, v: c.async_set_rx_target(v),
    ),
    SmartPoolNumberDescription(
        key="water_temperature_target",
        translation_key="water_temperature_target",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=10,
        native_max_value=40,
        native_step=0.5,
        mode=NumberMode.BOX,
        value_fn=lambda s: s.water_temperature_target,
        set_fn=lambda c, v: c.async_set_water_target(v),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartPoolConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the number entities."""
    coordinator = entry.runtime_data
    async_add_entities(
        SmartPoolNumber(coordinator, description) for description in NUMBERS
    )


class SmartPoolNumber(SmartPoolEntity, NumberEntity):
    """A writable target value."""

    entity_description: SmartPoolNumberDescription

    def __init__(self, coordinator, description: SmartPoolNumberDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | None:
        return self.entity_description.value_fn(self.coordinator.data)

    async def async_set_native_value(self, value: float) -> None:
        await self.entity_description.set_fn(self.coordinator.client, value)
        await self.coordinator.async_request_refresh()
