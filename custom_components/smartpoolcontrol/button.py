"""Button platform for Smart Pool Connect momentary commands.

⚠️ SAFETY — these buttons move the physical pool cover / deck. A moving cover
can trap a person or animal, and Home Assistant cannot see whether the pool is
clear (the vendor's own app enforces a "within 100 m, direct line of sight"
rule). They are therefore:

* **disabled by default** — each must be explicitly enabled in the entity
  settings before it does anything;
* intended for **manual, on-site** use only. Do NOT wire them into unattended
  automations. Only press them with the pool area in clear view.
"""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SmartPoolConfigEntry
from .const import CMD_COVER_CLOSE, CMD_COVER_OPEN, CMD_COVER_STOP
from .entity import SmartPoolControllableEntity


@dataclass(frozen=True, kw_only=True)
class SmartPoolButtonDescription(ButtonEntityDescription):
    """Describes a momentary command button."""

    command: str


# All cover buttons are disabled by default (opt-in) for the safety reasons
# documented at the top of this module.
BUTTONS: tuple[SmartPoolButtonDescription, ...] = (
    SmartPoolButtonDescription(
        key="cover_open",
        translation_key="cover_open",
        icon="mdi:window-shutter-open",
        command=CMD_COVER_OPEN,
        entity_registry_enabled_default=False,
    ),
    SmartPoolButtonDescription(
        key="cover_stop",
        translation_key="cover_stop",
        icon="mdi:stop-circle-outline",
        command=CMD_COVER_STOP,
        entity_registry_enabled_default=False,
    ),
    SmartPoolButtonDescription(
        key="cover_close",
        translation_key="cover_close",
        icon="mdi:window-shutter",
        command=CMD_COVER_CLOSE,
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartPoolConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the command buttons."""
    coordinator = entry.runtime_data
    async_add_entities(
        SmartPoolButton(coordinator, description) for description in BUTTONS
    )


class SmartPoolButton(SmartPoolControllableEntity, ButtonEntity):
    """A momentary command (e.g. move the cover)."""

    entity_description: SmartPoolButtonDescription

    def __init__(self, coordinator, description: SmartPoolButtonDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    async def async_press(self) -> None:
        self._check_online()
        await self.coordinator.client.async_send_command(
            self.entity_description.command
        )
