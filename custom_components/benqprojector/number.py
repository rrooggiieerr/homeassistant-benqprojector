import logging
from datetime import timedelta

from benqprojector import BenQProjector
from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
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
    """Set up the BenQ Serial Projector switch."""
    projector: BenQProjector = hass.data[DOMAIN][config_entry.entry_id]

    entities_config = [
        ["con", "Contrast", "mdi:contrast", 100],
        ["bri", "Brightness", "mdi:brightness-6", 100],
        ["color", "Color", "mdi:palette", 20],
        ["sharp", "Sharpness", None, 20],
        ["micvol", "Microphone Volume", "mdi:microphone", 20],
    ]

    entities = []

    for entity_config in entities_config:
        _LOGGER.debug(entity_config)
        if projector.supports_command(entity_config[0]):
            entities.append(
                BenQProjectorNumber(
                    projector, entity_config[0], entity_config[1], entity_config[2], entity_config[3]
                )
            )

    async_add_entities(entities)


class BenQProjectorNumber(NumberEntity):
    _attr_has_entity_name = True
    _attr_available = False
    _attr_native_max_value = 20
    _attr_native_min_value = 0
    _attr_native_step = 1
    _attr_native_value = None

    _attr_current_option = None

    def __init__(
        self,
        projector,
        command,
        name,
        icon=None,
        max_value = None
    ) -> None:
        """Initialize the number."""
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, projector._unique_id)},
            name=f"BenQ {projector.model}",
            model=projector.model,
            manufacturer="BenQ",
        )

        self._attr_unique_id = f"{projector._unique_id}-{command}"

        self._projector = projector
        self._command = command
        self._attr_name = name
        self._attr_icon = icon
        self._attr_native_max_value = max_value

    async def async_added_to_hass(self) -> None:
        await self.async_update()

    async def async_update(self) -> None:
        _LOGGER.debug("async_update")
        if self._projector.power_status == BenQProjector.POWERSTATUS_ON:
            if not self._attr_available:
                self._attr_available = True
                self.async_write_ha_state()

            response = self._projector.send_command(self._command)
            if response is not None:
                response = int(response)
                if self._attr_native_value != response:
                    self._attr_native_value = response
                    self.async_write_ha_state()
            elif self._attr_available != False:
                self._attr_available = False
                self.async_write_ha_state()
        elif self._attr_available != False:
            self._attr_available = False
            self.async_write_ha_state()

    async def async_set_native_value(self, value: float) -> None:
        _LOGGER.debug("async_update")
        if self._projector.power_status == BenQProjector.POWERSTATUS_ON:
            if self._attr_native_value == int(value):
                return

            while self._attr_native_value < int(value):
                if self._projector.send_command(self._command, "+") == "+":
                    self._attr_native_value += self._attr_native_step
                else:
                    return

            while self._attr_native_value > int(value):
                if self._projector.send_command(self._command, "-") == "-":
                    self._attr_native_value -= self._attr_native_step
                else:
                    return
        else:
            self._attr_available = False

        self.async_write_ha_state()
