from __future__ import annotations

import logging

from benqprojector import BenQProjector
from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the BenQ Projector switch."""
    coordinator: BenQProjectorCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    # Fetch initial data so we have data when entities subscribe
    await coordinator.async_config_entry_first_refresh()

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
        if coordinator.supports_command(entity_config[0]):
            entities.append(
                BenQProjectorSwitch(
                    coordinator, entity_config[0], entity_config[1], entity_config[2]
                )
            )

    async_add_entities(entities)


class BenQProjectorSwitch(CoordinatorEntity, SwitchEntity):
    _attr_has_entity_name = True
    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_available = False
    # _attr_should_poll = False

    _attr_is_on = None

    def __init__(
        self,
        coordinator: BenQProjectorCoordinator,
        command: str,
        name: str,
        icon=None,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, command)

        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"{coordinator.unique_id}-{command}"

        self.command = command
        self._attr_name = name
        self._attr_icon = icon

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        if (
            not self.coordinator.data
            or self.command not in self.coordinator.data
            or not self.coordinator.data[self.command]
        ):
            _LOGGER.debug("%s is not available", self.command)
            self._attr_available = False
        elif self.coordinator.data[self.command] == "on":
            self._attr_is_on = True
            self._attr_available = True
        else:
            self._attr_is_on = False
            self._attr_available = True

        await self.async_update()

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
            if self._attr_available != True:
                self._attr_available = True
                updated = True

            if (
                self.coordinator.data
                and self.command in self.coordinator.data
                and self.coordinator.data[self.command]
            ):
                new_state = self.coordinator.data[self.command] == "on"
                if self._attr_is_on != new_state:
                    self._attr_is_on = new_state
                    updated = True
            elif self._attr_available != False:
                self._attr_available = False
                updated = True
        elif self._attr_available != False:
            _LOGGER.debug("%s is not available", self.command)
            self._attr_available = False
            updated = True

        # Only update the HA state if state has updated.
        if updated:
            self.async_write_ha_state()

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the entity on."""
        _LOGGER.debug("Turning on %s", self._attr_name)
        response = self.coordinator.send_command(self.command, "on")
        if response == "on":
            self._attr_is_on = True
            self.async_write_ha_state()
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to switch on %s", self._attr_name)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the entity off."""
        _LOGGER.debug("Turning off %s", self._attr_name)
        response = self.coordinator.send_command(self.command, "off")
        if response == "off":
            self._attr_is_on = False
            self.async_write_ha_state()
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to switch off %s", self._attr_name)
