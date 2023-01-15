from __future__ import annotations

import logging

from benqprojector import BenQProjector
from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
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
    """Set up the BenQ Projector switch."""
    coordinator: BenQProjectorCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    # Fetch initial data so we have data when entities subscribe
    await coordinator.async_config_entry_first_refresh()

    entities_config = [
        ["bc", "Brilliant Color", "mdi:diamond-stone", None],
        ["qas", "Quick Auto Search", None, EntityCategory.CONFIG],
        ["directpower", "Direct Power On", "mdi:power", EntityCategory.CONFIG],
        ["autopower", "Signal Power On", "mdi:power", EntityCategory.CONFIG],
        ["standbynet", "Standby Settings Network", None, None],
        ["standbymic", "Standby Settings Microphone", None, None],
        ["standbymnt", "Standby Settings Monitor Out ", None, None],
        ["blank", "Blank", None, None],
        ["freeze", "Freeze", None, None],
        ["ins", "Instant On", "mdi:power", EntityCategory.CONFIG],
        ["lpsaver", "Lamp Saver Mode", "mdi:lightbulb-outline", EntityCategory.CONFIG],
        ["prjlogincode", "Projection Log In Code", None, EntityCategory.CONFIG],
        ["broadcasting", "Broadcasting", None, EntityCategory.CONFIG],
        ["amxdd", "AMX Device Discovery", None, EntityCategory.CONFIG],
        ["highaltitude", "High Altitude Mode", "mdi:image-filter-hdr", EntityCategory.CONFIG,],
    ]

    entities = []

    for entity_config in entities_config:
        if coordinator.supports_command(entity_config[0]):
            entities.append(
                BenQProjectorSwitch(
                    coordinator,
                    entity_config[0],
                    entity_config[1],
                    entity_config[2],
                    entity_config[3],
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
        entity_category=None,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, command)

        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"{coordinator.unique_id}-{command}"

        self.command = command
        self._attr_name = name
        self._attr_icon = icon
        self._attr_entity_category = entity_category

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        if (
            self.coordinator.data
            and (new_state := self.coordinator.data.get(self.command))
        ):
            if new_state == "on":
                self._attr_is_on = True
                self._attr_available = True
            else:
                self._attr_is_on = False
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
            if (
                self.coordinator.data
                and (new_state := self.coordinator.data.get(self.command))
            ):
                new_state = new_state == "on"
                if self._attr_is_on != new_state:
                    self._attr_is_on = new_state
                    updated = True

                if self._attr_available is not True:
                    self._attr_available = True
                    updated = True
            elif self._attr_available is not False:
                self._attr_available = False
                updated = True
        elif self._attr_available is not False:
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
