from __future__ import annotations

import logging

from benqprojector import BenQProjector
from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
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

    entity_descriptions = [
        SwitchEntityDescription(
            key="bc", name="Brilliant Color", icon="mdi:diamond-stone"
        ),
        SwitchEntityDescription(
            key="qas",
            name="Quick Auto Search",
            entity_category=EntityCategory.CONFIG,
            entity_registry_enabled_default=False,
        ),
        SwitchEntityDescription(
            key="directpower",
            name="Direct Power On",
            icon="mdi:power",
            entity_category=EntityCategory.CONFIG,
            entity_registry_enabled_default=False,
        ),
        SwitchEntityDescription(
            key="autopower",
            name="Signal Power On",
            icon="mdi:power",
            entity_category=EntityCategory.CONFIG,
            entity_registry_enabled_default=False,
        ),
        SwitchEntityDescription(
            key="standbynet",
            name="Standby Settings Network",
            entity_category=EntityCategory.CONFIG,
            entity_registry_enabled_default=False,
        ),
        SwitchEntityDescription(
            key="standbymic",
            name="Standby Settings Microphone",
            entity_category=EntityCategory.CONFIG,
            entity_registry_enabled_default=False,
        ),
        SwitchEntityDescription(
            key="standbymnt",
            name="Standby Settings Monitor Out",
            entity_category=EntityCategory.CONFIG,
            entity_registry_enabled_default=False,
        ),
        SwitchEntityDescription(key="blank", name="Blank"),
        SwitchEntityDescription(key="freeze", name="Freeze"),
        SwitchEntityDescription(
            key="ins",
            name="Instant On",
            icon="mdi:power",
            entity_category=EntityCategory.CONFIG,
            entity_registry_enabled_default=False,
        ),
        SwitchEntityDescription(
            key="lpsaver",
            name="Lamp Saver Mode",
            icon="mdi:lightbulb-outline",
            entity_category=EntityCategory.CONFIG,
            entity_registry_enabled_default=False,
        ),
        SwitchEntityDescription(
            key="prjlogincode",
            name="Projection Log In Code",
            entity_category=EntityCategory.CONFIG,
            entity_registry_enabled_default=False,
        ),
        SwitchEntityDescription(
            key="broadcasting",
            name="Broadcasting",
            entity_category=EntityCategory.CONFIG,
            entity_registry_enabled_default=False,
        ),
        SwitchEntityDescription(
            key="amxdd",
            name="AMX Device Discovery",
            entity_category=EntityCategory.CONFIG,
            entity_registry_enabled_default=False,
        ),
        SwitchEntityDescription(
            key="highaltitude",
            name="High Altitude Mode",
            icon="mdi:image-filter-hdr",
            entity_category=EntityCategory.CONFIG,
            entity_registry_enabled_default=False,
        ),
    ]

    entities = []

    for entity_description in entity_descriptions:
        if coordinator.supports_command(entity_description.key):
            entities.append(BenQProjectorSwitch(coordinator, entity_description))

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
        entity_description: SwitchEntityDescription,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, entity_description.key)

        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"{coordinator.unique_id}-{entity_description.key}"

        self.entity_description = entity_description

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        if self.coordinator.data and (
            new_state := self.coordinator.data.get(self.entity_description.key)
        ):
            if new_state == "on":
                self._attr_is_on = True
            else:
                self._attr_is_on = False
            self._attr_available = True
            self.async_write_ha_state()
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
        updated = False

        if self.coordinator.power_status in [
            BenQProjector.POWERSTATUS_POWERINGON,
            BenQProjector.POWERSTATUS_ON,
        ]:
            if self.coordinator.data and (
                new_state := self.coordinator.data.get(self.entity_description.key)
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
            _LOGGER.debug("%s is not available", self.entity_description.key)
            self._attr_available = False
            updated = True

        # Only update the HA state if state has updated.
        if updated:
            self.async_write_ha_state()

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the entity on."""
        _LOGGER.debug("Turning on %s", self.name)
        response = await self.coordinator.async_send_command(
            self.entity_description.key, "on"
        )
        if response == "on":
            self._attr_is_on = True
            self.async_write_ha_state()
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to switch on %s", self.name)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the entity off."""
        _LOGGER.debug("Turning off %s", self.name)
        response = await self.coordinator.async_send_command(
            self.entity_description.key, "off"
        )
        if response == "off":
            self._attr_is_on = False
            self.async_write_ha_state()
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to switch off %s", self.name)
