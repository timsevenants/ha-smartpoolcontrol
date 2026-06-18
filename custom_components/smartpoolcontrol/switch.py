"""Switch platform for Smart Pool Control."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SmartPoolConfigEntry
from .api import PoolStatus, SmartPoolControlClient
from .entity import SmartPoolEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class SmartPoolSwitchDescription(SwitchEntityDescription):
    """Describes a Smart Pool Control switch."""

    # None when the current state cannot be read back from the portal.
    value_fn: Callable[[PoolStatus], bool | None] | None = None
    set_fn: Callable[[SmartPoolControlClient, bool], Awaitable[None]]


SWITCHES: tuple[SmartPoolSwitchDescription, ...] = (
    SmartPoolSwitchDescription(
        key="lighting",
        translation_key="lighting",
        device_class=SwitchDeviceClass.SWITCH,
        icon="mdi:lightbulb",
        value_fn=lambda s: s.lighting_on,
        set_fn=lambda c, on: c.async_toggle_lighting(),
    ),
    SmartPoolSwitchDescription(
        key="frost_protection",
        translation_key="frost_protection",
        icon="mdi:snowflake-alert",
        set_fn=lambda c, on: c.async_set_frost_protection(on),
    ),
    SmartPoolSwitchDescription(
        key="pump_force_on",
        translation_key="pump_force_on",
        icon="mdi:pump",
        set_fn=lambda c, on: c.async_set_pump_force(on),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartPoolConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switches."""
    coordinator = entry.runtime_data
    async_add_entities(
        SmartPoolSwitch(coordinator, description) for description in SWITCHES
    )


class SmartPoolSwitch(SmartPoolEntity, SwitchEntity):
    """A togglable feature on the portal."""

    entity_description: SmartPoolSwitchDescription

    def __init__(self, coordinator, description: SmartPoolSwitchDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description
        # Optimistic state for switches whose state is not exposed by the portal.
        self._optimistic: bool | None = None

    @property
    def is_on(self) -> bool | None:
        if self.entity_description.value_fn is not None:
            return self.entity_description.value_fn(self.coordinator.data)
        return self._optimistic

    async def async_turn_on(self, **kwargs) -> None:
        await self._set(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self._set(False)

    async def _set(self, on: bool) -> None:
        desc = self.entity_description
        # The lighting endpoint only toggles, so avoid toggling when already
        # in the requested state.
        if desc.key == "lighting" and desc.value_fn is not None:
            current = desc.value_fn(self.coordinator.data)
            if current is on:
                return
        await desc.set_fn(self.coordinator.client, on)
        if desc.value_fn is None:
            self._optimistic = on
            self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
