"""
Created on 27 Nov 2022

@author: Rogier van Staveren
"""
from __future__ import annotations

import logging
from datetime import timedelta

from benqprojector import BenQProjector
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import TIME_HOURS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=1)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the BenQ Projector media player."""
    projector: BenQProjector = hass.data[DOMAIN][config_entry.entry_id]

    entities = []
    if projector.lamp2_time is not None:
        entities.append(
            BenQProjectorLampTimeSensor(projector, "lamp_time", "Lamp 1 Time")
        )
        entities.append(
            BenQProjectorLampTimeSensor(projector, "lamp2_time", "Lamp 2 Time")
        )
    else:
        entities.append(
            BenQProjectorLampTimeSensor(projector, "lamp_time", "Lamp Time")
        )

    async_add_entities(entities)


class BenQProjectorSensor(SensorEntity):
    _projector = None
    _property = None

    def __init__(
        self,
        projector: BenQProjector,
        attribute,
        name,
        icon=None,
    ):
        """Initialize the sensor."""
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, projector._unique_id)},
            name=f"BenQ {projector.model}",
            model=projector.model,
            manufacturer="BenQ",
        )
        self._attr_unique_id = f"{projector._unique_id}-{attribute}"

        self._projector = projector
        self._attribute = attribute
        self._attr_name = name
        self._attr_icon = icon


class BenQProjectorLampTimeSensor(BenQProjectorSensor):
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = TIME_HOURS
    _attr_native_value = None

    async def async_update(self) -> None:
        response = getattr(self._projector, self._attribute)
        if self._attr_native_value != response:
            self._attr_native_value = response
            self.async_write_ha_state()
