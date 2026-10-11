"""Base entity for the BenQ Projector integration."""

from typing import Any

from benqprojector import BenQProjector
from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import BenQProjectorCoordinator


class BenQProjectorEntity(CoordinatorEntity[BenQProjectorCoordinator]):
    """
    Base BenQ Projector entity.

    Availability is derived from the current power state and the cached value, instead of
    a flag that each platform has to keep in sync.
    """

    _attr_has_entity_name = True
    # Most settings can only be read and changed while the projector is on.
    _requires_power_on = True

    def __init__(
        self,
        coordinator: BenQProjectorCoordinator,
        unique_id: str,
        key: str | None = None,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator, key)

        self._key = key
        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = unique_id

    @property
    def _value(self) -> Any:
        if self._key is None or not self.coordinator.data:
            return None
        return self.coordinator.data.get(self._key)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if self.coordinator.power_status == BenQProjector.POWERSTATUS_UNKNOWN:
            return False
        if self._requires_power_on and not self.coordinator.is_on:
            return False
        return self._key is None or self._value is not None

    async def async_added_to_hass(self) -> None:
        """Pick up the values that were received before the entity was added."""
        await super().async_added_to_hass()
        self._update_from_data()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_from_data()
        self.async_write_ha_state()

    @callback
    def _update_from_data(self) -> None:
        """Update the entity attributes from the coordinator data."""
