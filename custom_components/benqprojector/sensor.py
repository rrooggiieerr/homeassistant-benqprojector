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
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import TIME_HOURS
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

    # Fetch initial data so we have data when entities subscribe
    await coordinator.async_config_entry_first_refresh()

    entities_config = []
    if coordinator.supports_command("ltim2"):
        entities_config.append(["ltim", "Lamp 1 Time", None])
        entities_config.append(["ltim2", "Lamp 2 Time", None])
    elif coordinator.supports_command("ltim"):
        entities_config.append(["ltim", "Lamp Time", None])

    entities = []

    for entity_config in entities_config:
        if coordinator.supports_command(entity_config[0]):
            entities.append(
                BenQProjectorLampTimeSensor(
                    coordinator, entity_config[0], entity_config[1], entity_config[2]
                )
            )

    async_add_entities(entities)


class BenQProjectorSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_available = False
    _attr_native_value = None

    def __init__(
        self,
        coordinator: BenQProjectorCoordinator,
        command: str,
        name: str,
        icon=None,
    ):
        """Initialize the sensor."""
        super().__init__(coordinator, command)

        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"{coordinator.unique_id}-{command}"

        self.command = command
        self._attr_name = name
        self._attr_icon = icon

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        if (
            self.coordinator.data
            and self.command in self.coordinator.data
            and self.coordinator.data[self.command]
        ):
            self._attr_native_value = self.coordinator.data[self.command]
            self._attr_available = True
            self.async_write_ha_state()
        else:
            _LOGGER.debug("%s is not available", self.command)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not self._attr_available:
            return self._attr_available

        return self.coordinator.last_update_success

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        updated = False

        if self.coordinator.power_status in [
            BenQProjector.POWERSTATUS_POWERINGON,
            BenQProjector.POWERSTATUS_ON,
        ]:
            _LOGGER.debug(self.coordinator.data)

            if (
                self.coordinator.data
                and self.command in self.coordinator.data
                and self.coordinator.data[self.command]
            ):
                new_value = self.coordinator.data[self.command]
                if self._attr_native_value != new_value:
                    self._attr_native_value = new_value
                    updated = True

                if self._attr_available is not True:
                    self._attr_available = True
                    updated = True
            elif self._attr_available is not False:
                self._attr_available = False
                updated = True
        elif self._attr_available is not False:
            self._attr_available = False
            updated = True

        # Only update the HA state if state has updated.
        if updated:
            self.async_write_ha_state()


class BenQProjectorLampTimeSensor(BenQProjectorSensor):
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = TIME_HOURS
    _attr_native_value = None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        updated = False

        if (
            self.coordinator.data
            and self.command in self.coordinator.data
            and self.coordinator.data[self.command]
        ):
            try:
                new_state = int(self.coordinator.data[self.command])
                if self._attr_native_value != new_state:
                    self._attr_native_value = self.coordinator.data[self.command]
                    updated = True

                if self._attr_available is not True:
                    self._attr_available = True
                    updated = True
            except ValueError as ex:
                _LOGGER.error(ex)
                if self._attr_available is not False:
                    self._attr_available = False
                    updated = True
        elif self._attr_available is not False:
            self._attr_available = False
            updated = True

        # Only update the HA state if state has updated.
        if updated:
            self.async_write_ha_state()
