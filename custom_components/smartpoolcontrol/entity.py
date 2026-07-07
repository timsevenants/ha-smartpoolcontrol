"""Base entity for Smart Pool Control."""

from __future__ import annotations

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_POOL_ID, DOMAIN, MANUFACTURER
from .coordinator import SmartPoolControlCoordinator


class SmartPoolEntity(CoordinatorEntity[SmartPoolControlCoordinator]):
    """Common base linking entities to the pool device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SmartPoolControlCoordinator, key: str) -> None:
        super().__init__(coordinator)
        pool_id = coordinator.entry.data[CONF_POOL_ID]
        self._attr_unique_id = f"{pool_id}_{key}"
        status = coordinator.data
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, pool_id)},
            name=(status.name if status else None) or f"Pool {pool_id}",
            manufacturer=MANUFACTURER,
            model="Smart Pool Control",
            connections=(
                {("mac", status.mac)} if status and status.mac else set()
            ),
            configuration_url=coordinator.client._base_url,  # noqa: SLF001
        )

    @property
    def available(self) -> bool:
        return super().available and bool(self.coordinator.data)


class SmartPoolControllableEntity(SmartPoolEntity):
    """Base for entities that send commands to the pool.

    The portal refuses to apply any change while the pool controller is
    offline (it shows "Veranderingen worden niet opgeslagen" and disables the
    controls). These entities therefore report themselves as unavailable when
    the pool is offline instead of silently accepting commands that go
    nowhere, and raise a clear error if a service is still called.
    """

    @property
    def available(self) -> bool:
        data = self.coordinator.data
        return super().available and bool(data and data.online)

    def _check_online(self) -> None:
        """Raise if the pool is offline so callers get real feedback."""
        data = self.coordinator.data
        if not (data and data.online):
            raise HomeAssistantError(
                "Pool is offline; the portal will not apply changes"
            )
