from __future__ import annotations

import logging

from benqprojector import BenQProjector
from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
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
    """Set up the BenQ Serial Projector number."""
    coordinator: BenQProjectorCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entity_descriptions = [
        NumberEntityDescription(
            key="con", name="Contrast", icon="mdi:contrast", native_max_value=100
        ),
        NumberEntityDescription(
            key="bri", name="Brightness", icon="mdi:brightness-6", native_max_value=100
        ),
        NumberEntityDescription(
            key="color", name="Color", icon="mdi:palette", native_max_value=20
        ),
        NumberEntityDescription(key="sharp", name="Sharpness", native_max_value=20),
        NumberEntityDescription(
            key="micvol",
            name="Microphone Volume",
            icon="mdi:microphone",
            native_max_value=20,
        ),
        NumberEntityDescription(key="keyst", name="Keystone", native_max_value=20, entity_category=EntityCategory.CONFIG,),
        NumberEntityDescription(key="rgain", name="Red Gain", native_max_value=200, entity_category=EntityCategory.CONFIG,),
        NumberEntityDescription(key="ggain", name="Green Gain", native_max_value=200, entity_category=EntityCategory.CONFIG,),
        NumberEntityDescription(key="bgain", name="Blue Gain", native_max_value=200, entity_category=EntityCategory.CONFIG,),
        NumberEntityDescription(key="roffset", name="Red Offset", native_max_value=511, entity_category=EntityCategory.CONFIG,),
        NumberEntityDescription(key="goffset", name="Green Offset", native_max_value=511, entity_category=EntityCategory.CONFIG,),
        NumberEntityDescription(key="boffset", name="Blue Offset", native_max_value=511, entity_category=EntityCategory.CONFIG,),
        # NumberEntityDescription(key="gamma", name="Gamma", icon="mdi:gamma", native_min_value=1.6, native_max_value=2.8, native_step=0.1, entity_category=EntityCategory.CONFIG,),
        NumberEntityDescription(key="hdrbri", name="HDR Brightness", icon="mdi:brightness-6", native_min_value=-2, native_max_value=2, entity_category=EntityCategory.CONFIG,),
    ]

    entities = []

    for entity_description in entity_descriptions:
        if coordinator.supports_command(entity_description.key):
            entities.append(BenQProjectorNumber(coordinator, entity_description))

    async_add_entities(entities)


class BenQProjectorNumber(CoordinatorEntity, NumberEntity):
    _attr_has_entity_name = True
    _attr_available = False
    _attr_native_min_value = 0
    _attr_native_step = 1
    _attr_native_value = None

    def __init__(
        self,
        coordinator: BenQProjectorCoordinator,
        entity_description: NumberEntityDescription,
    ) -> None:
        """Initialize the number."""
        super().__init__(coordinator, entity_description.key)

        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"{coordinator.unique_id}-{entity_description.key}"

        self.entity_description = entity_description

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        if self.coordinator.data and (
            native_value := self.coordinator.data.get(self.entity_description.key)
        ):
            try:
                self._attr_native_value = float(native_value)
                self._attr_available = True
                self.async_write_ha_state()
            except ValueError as ex:
                _LOGGER.error(
                    "ValueError for %s = %s, %s",
                    self.entity_description.key,
                    self.coordinator.data.get(self.entity_description.key),
                    ex,
                )
            except TypeError as ex:
                _LOGGER.error("TypeError for %s, %s", self.entity_description.key, ex)
        else:
            _LOGGER.debug("%s is not available", self.entity_description.key)

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
            if self.coordinator.data and (
                new_value := self.coordinator.data.get(self.entity_description.key)
            ):
                try:
                    self._attr_native_value = float(new_value)
                    self._attr_available = True
                except ValueError as ex:
                    _LOGGER.error(
                        "ValueError for %s = %s, %s",
                        self.entity_description.key,
                        self.coordinator.data.get(self.entity_description.key),
                        ex,
                    )
                    self._attr_available = False
                except TypeError as ex:
                    _LOGGER.error(
                        "TypeError for %s, %s", self.entity_description.key, ex
                    )
                    self._attr_available = False
            else:
                self._attr_available = False
        else:
            _LOGGER.debug("%s is not available", self.entity_description.key)
            self._attr_available = False

        self.async_write_ha_state()

    async def async_set_native_value(self, value: float) -> None:
        _LOGGER.debug("async_set_native_value")
        if self.coordinator.power_status == BenQProjector.POWERSTATUS_ON:
            if self._attr_native_value == value:
                return

            while self._attr_native_value < value:
                if (
                    await self.coordinator.async_send_command(
                        self.entity_description.key, "+"
                    )
                    == "+"
                ):
                    self._attr_native_value += self._attr_native_step
                else:
                    break

            while self._attr_native_value > value:
                if (
                    await self.coordinator.async_send_command(
                        self.entity_description.key, "-"
                    )
                    == "-"
                ):
                    self._attr_native_value -= self._attr_native_step
                else:
                    break

            self.async_write_ha_state()
            await self.coordinator.async_request_refresh()
        else:
            self._attr_available = False

        self.async_write_ha_state()
