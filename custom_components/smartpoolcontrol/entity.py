"""Base entity for Smart Pool Control."""

from __future__ import annotations

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
