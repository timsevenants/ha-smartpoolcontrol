"""Cover platform for the pool deck.

SAFETY WARNING
==============
Operating a pool cover remotely is potentially dangerous: a person or animal
could be in or near the pool. The web portal enforces a "you must be within
100 m and have direct line of sight" rule in the browser; this integration
cannot verify either. Only enable/use this entity if you have another reliable
way to ensure the pool area is clear before moving the cover.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SmartPoolConfigEntry
from .entity import SmartPoolEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartPoolConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the pool cover."""
    async_add_entities([PoolCover(entry.runtime_data)])


class PoolCover(SmartPoolEntity, CoverEntity):
    """The pool deck / cover."""

    _attr_translation_key = "cover"
    _attr_device_class = CoverDeviceClass.SHADE
    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
    )
    # Disabled by default because of the safety considerations above.
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "cover")

    @property
    def is_closed(self) -> bool | None:
        state = self.coordinator.data.cover_state
        if state is None:
            return None
        return state == "closed"

    async def async_open_cover(self, **kwargs: Any) -> None:
        await self.coordinator.client.async_cover_open()
        await self.coordinator.async_request_refresh()

    async def async_close_cover(self, **kwargs: Any) -> None:
        await self.coordinator.client.async_cover_close()
        await self.coordinator.async_request_refresh()

    async def async_stop_cover(self, **kwargs: Any) -> None:
        await self.coordinator.client.async_cover_stop()
        await self.coordinator.async_request_refresh()
