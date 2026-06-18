"""Binary sensor platform for Smart Pool Control."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SmartPoolConfigEntry
from .api import PoolStatus
from .entity import SmartPoolEntity


@dataclass(frozen=True, kw_only=True)
class SmartPoolBinaryDescription(BinarySensorEntityDescription):
    """Describes a Smart Pool Control binary sensor."""

    value_fn: Callable[[PoolStatus], bool | None]


BINARY_SENSORS: tuple[SmartPoolBinaryDescription, ...] = (
    SmartPoolBinaryDescription(
        key="heating",
        translation_key="heating",
        device_class=BinarySensorDeviceClass.HEAT,
        icon="mdi:radiator",
        value_fn=lambda s: s.heating_on,
    ),
    SmartPoolBinaryDescription(
        key="online",
        translation_key="online",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda s: s.online,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartPoolConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        SmartPoolBinarySensor(coordinator, description)
        for description in BINARY_SENSORS
    )


class SmartPoolBinarySensor(SmartPoolEntity, BinarySensorEntity):
    """A boolean state derived from the measurements page."""

    entity_description: SmartPoolBinaryDescription

    def __init__(self, coordinator, description: SmartPoolBinaryDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.value_fn(self.coordinator.data)
