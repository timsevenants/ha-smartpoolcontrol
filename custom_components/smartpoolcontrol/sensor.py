"""Sensor platform for Smart Pool Control."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SmartPoolConfigEntry
from .api import PoolStatus
from .entity import SmartPoolEntity


@dataclass(frozen=True, kw_only=True)
class SmartPoolSensorDescription(SensorEntityDescription):
    """Describes a Smart Pool Control sensor."""

    value_fn: Callable[[PoolStatus], float | str | None]


SENSORS: tuple[SmartPoolSensorDescription, ...] = (
    SmartPoolSensorDescription(
        key="ph",
        translation_key="ph",
        icon="mdi:ph",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.ph,
    ),
    SmartPoolSensorDescription(
        key="ph_target",
        translation_key="ph_target",
        icon="mdi:ph",
        entity_registry_enabled_default=False,
        value_fn=lambda s: s.ph_target,
    ),
    SmartPoolSensorDescription(
        key="rx",
        translation_key="rx",
        icon="mdi:flash",
        native_unit_of_measurement="mV",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.rx,
    ),
    SmartPoolSensorDescription(
        key="rx_target",
        translation_key="rx_target",
        icon="mdi:flash",
        native_unit_of_measurement="mV",
        entity_registry_enabled_default=False,
        value_fn=lambda s: s.rx_target,
    ),
    SmartPoolSensorDescription(
        key="water_temperature",
        translation_key="water_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.water_temperature,
    ),
    SmartPoolSensorDescription(
        key="outside_temperature",
        translation_key="outside_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.outside_temperature,
    ),
    SmartPoolSensorDescription(
        key="solar_temperature",
        translation_key="solar_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda s: s.solar_temperature,
    ),
    SmartPoolSensorDescription(
        key="pump_speed",
        translation_key="pump_speed",
        icon="mdi:pump",
        device_class=SensorDeviceClass.ENUM,
        options=["off", "low", "medium", "high", "maximum"],
        value_fn=lambda s: s.pump_speed,
    ),
    SmartPoolSensorDescription(
        key="cover_state",
        translation_key="cover_state",
        icon="mdi:window-shutter",
        device_class=SensorDeviceClass.ENUM,
        options=["open", "closed"],
        value_fn=lambda s: s.cover_state,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartPoolConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        SmartPoolSensor(coordinator, description) for description in SENSORS
    )


class SmartPoolSensor(SmartPoolEntity, SensorEntity):
    """A scraped value from the measurements page."""

    entity_description: SmartPoolSensorDescription

    def __init__(self, coordinator, description: SmartPoolSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | str | None:
        return self.entity_description.value_fn(self.coordinator.data)
