"""
Created on 27 Nov 2022

@author: Rogier van Staveren
"""

from __future__ import annotations

import logging

from benqprojector import BenQProjector
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import BenQProjectorCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the BenQ Projector media player."""
    coordinator: BenQProjectorCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entity_descriptions = []
    if coordinator.supports_command("ltim2"):
        entity_descriptions.append(
            SensorEntityDescription(key="ltim", name="Lamp 1 Time")
        )
        entity_descriptions.append(
            SensorEntityDescription(key="ltim2", name="Lamp 2 Time")
        )
    elif coordinator.supports_command("ltim"):
        entity_descriptions.append(
            SensorEntityDescription(key="ltim", name="Lamp Time")
        )

    entities = []

    for entity_description in entity_descriptions:
        if coordinator.supports_command(entity_description.key):
            entities.append(
                BenQProjectorLampTimeSensor(coordinator, entity_description)
            )

    async_add_entities(entities)


class BenQProjectorSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_available = False
    _attr_native_value = None

    def __init__(
        self,
        coordinator: BenQProjectorCoordinator,
        entity_description: SensorEntityDescription,
    ):
        """Initialize the sensor."""
        super().__init__(coordinator, entity_description.key)

        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"{coordinator.unique_id}-{entity_description.key}"

        self.entity_description = entity_description

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        if self.coordinator.data and (
            native_value := self.coordinator.data.get(self.entity_description.key)
        ):
            self._attr_native_value = native_value
            self._attr_available = True
        else:
            _LOGGER.debug("%s is not available", self.entity_description.key)
            self._attr_available = False

        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not self._attr_available:
            return self._attr_available

        return self.coordinator.last_update_success

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self.coordinator.power_status in [
            BenQProjector.POWERSTATUS_POWERINGON,
            BenQProjector.POWERSTATUS_ON,
        ]:
            _LOGGER.debug(self.coordinator.data)

            if self.coordinator.data and (
                new_value := self.coordinator.data.get(self.entity_description.key)
            ):
                self._attr_native_value = new_value
                self._attr_available = True
            else:
                self._attr_available = False
        else:
            self._attr_available = False

        self.async_write_ha_state()


class BenQProjectorLampTimeSensor(BenQProjectorSensor):
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_native_value = None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self.coordinator.data and (
            new_value := self.coordinator.data.get(self.entity_description.key)
        ):
            try:
                self._attr_native_value = int(new_value)
                self._attr_available = True
            except ValueError as ex:
                _LOGGER.error(ex)
                self._attr_available = False
        else:
            self._attr_available = False

        self.async_write_ha_state()
