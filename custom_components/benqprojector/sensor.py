"""Creates Sensor entities for the BenQ Projector Home Assistant integration."""

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import BenQProjectorConfigEntry, BenQProjectorCoordinator
from .entity import BenQProjectorEntity

_LOGGER = logging.getLogger(__name__)


def _lamp_time(key: str, translation_key: str) -> SensorEntityDescription:
    return SensorEntityDescription(
        key=key,
        translation_key=translation_key,
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=0,
    )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: BenQProjectorConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the BenQ Projector sensors."""
    coordinator = config_entry.runtime_data

    entity_descriptions = []
    if coordinator.supports_command("ltim2"):
        entity_descriptions.append(_lamp_time("ltim", "ltim1"))
        entity_descriptions.append(_lamp_time("ltim2", "ltim2"))
    elif coordinator.supports_command("ltim"):
        entity_descriptions.append(_lamp_time("ltim", "ltim"))

    async_add_entities(
        BenQProjectorLampTimeSensor(
            coordinator, entity_description, config_entry.entry_id
        )
        for entity_description in entity_descriptions
    )


class BenQProjectorLampTimeSensor(BenQProjectorEntity, SensorEntity):
    """BenQ Projector Lamp Time Sensor."""

    # The lamp time can also be read while the projector is off.
    _requires_power_on = False

    def __init__(
        self,
        coordinator: BenQProjectorCoordinator,
        entity_description: SensorEntityDescription,
        config_entry_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator,
            f"{config_entry_id}-{entity_description.key}",
            entity_description.key,
        )
        self.entity_description = entity_description

    @callback
    def _update_from_data(self) -> None:
        value = self._value
        try:
            self._attr_native_value = None if value is None else int(value)
        except (TypeError, ValueError):
            _LOGGER.debug("Invalid lamp time for %s: %s", self._key, value)
            self._attr_native_value = None
