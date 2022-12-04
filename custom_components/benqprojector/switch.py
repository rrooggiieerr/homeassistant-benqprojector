from __future__ import annotations

import logging
from datetime import timedelta

from benqprojector import BenQProjector
from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON
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
    """Set up the BenQ Projector switch."""
    projector: BenQProjector = hass.data[DOMAIN][config_entry.entry_id]

    entities_config = [
        ["bc", "Brilliant Color", "mdi:diamond-stone"],
        ["qas", "Quick Auto Search", None],
        ["directpower", "Direct Power On", "mdi:power"],
        ["autopower", "Signal Power On", "mdi:power"],
        ["standbynet", "Standby Settings Network", None],
        ["standbymic", "Standby Settings Microphone", None],
        ["standbymnt", "Standby Settings Monitor Out ", None],
        ["blank", "Blank", None],
        ["freeze", "Freeze", None],
        ["menu", "Menu", "mdi:menu"],
        ["ins", "Instant On", "mdi:power"],
        ["lpsaver", "Lamp Saver Mode", "mdi:lightbulb-outline"],
        ["prjlogincode", "Projection Log In Code", None],
        ["broadcasting", "Broadcasting", None],
        ["amxdd", "AMX Device Discovery", None],
        ["highaltitude", "High Altitude Mode", "mdi:image-filter-hdr"],
    ]

    entities = []

    for entity_config in entities_config:
        if projector.supports_command(entity_config[0]):
            entities.append(
                BenQProjectorSwitch(
                    projector, entity_config[0], entity_config[1], entity_config[2]
                )
            )

    async_add_entities(entities)


class BenQProjectorSwitch(SwitchEntity):
    _attr_has_entity_name = True
    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_available = False
    # _attr_should_poll = False

    _attr_is_on = None
    _attr_state = False

    def __init__(
        self,
        projector,
        command,
        name,
        icon=None,
    ) -> None:
        """Initialize the switch."""
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

    async def async_added_to_hass(self) -> None:
        await self.async_update()

    async def async_update(self) -> None:
        if self._projector.power_status in [
            BenQProjector.POWERSTATUS_POWERINGON,
            BenQProjector.POWERSTATUS_ON,
        ]:
            response = self._projector.send_command(self._command)
            if response is not None:
                if not self._attr_available:
                    self._attr_available = True
                    self.async_write_ha_state()

                if response == "on" and self._attr_is_on is not True:
                    self._attr_is_on = True
                    self._attr_state = STATE_ON
                    self.async_write_ha_state()
                elif response == "off" and self._attr_is_on is not False:
                    self._attr_is_on = False
                    self._attr_state = STATE_OFF
                    self.async_write_ha_state()
            elif self._attr_available != False:
                self._attr_available = False
                self.async_write_ha_state()
        elif self._attr_available != False:
            self._attr_available = False
            self.async_write_ha_state()

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the entity on."""
        _LOGGER.debug("Turning on %s", self._attr_name)
        response = self._projector.send_command(self._command, "on")
        if response == "on":
            self._attr_is_on = True
            self._attr_state = STATE_ON
            self.async_write_ha_state()
        else:
            _LOGGER.error("Failed to switch on %s", self._attr_name)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the entity off."""
        _LOGGER.debug("Turning off %s", self._attr_name)
        response = self._projector.send_command(self._command, "off")
        if response == "off":
            self._attr_is_on = False
            self._attr_state = STATE_OFF
            self.async_write_ha_state()
        else:
            _LOGGER.error("Failed to switch off %s", self._attr_name)
