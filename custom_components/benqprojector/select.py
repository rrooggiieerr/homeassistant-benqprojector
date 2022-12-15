from __future__ import annotations

import logging

from benqprojector import BenQProjector
from homeassistant.components.select import SelectEntity
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
    """Set up the BenQ Serial Projector switch."""
    coordinator: BenQProjectorCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    # Fetch initial data so we have data when entities subscribe
    await coordinator.async_config_entry_first_refresh()

    entities_config = [
        [
            "audiosour",
            coordinator.projector.audio_sources,
            "Audio Source",
            "mdi:audio-input-rca",
            None,
        ],
        ["appmod", coordinator.projector.picture_modes, "Picture Mode", None, None],
        [
            "ct",
            coordinator.projector.color_temperatures,
            "Color Temperature",
            "mdi:thermometer",
            EntityCategory.CONFIG,
        ],
        [
            "asp",
            coordinator.projector.aspect_ratios,
            "Aspect Ratio",
            "mdi:aspect-ratio",
            None,
        ],
        [
            "lampm",
            coordinator.projector.lamp_modes,
            "Lamp Mode",
            None,
            EntityCategory.CONFIG,
        ],
        [
            "3d",
            coordinator.projector.threed_modes,
            "3D Sync",
            None,
            EntityCategory.CONFIG,
        ],
        # ["rr", None, "Remote Receiver", None, EntityCategory.CONFIG],
        [
            "pp",
            coordinator.projector.projector_positions,
            "Projector Position",
            None,
            EntityCategory.CONFIG,
        ],
    ]

    entities = []

    for entity_config in entities_config:
        if coordinator.supports_command(entity_config[0]):
            entities.append(
                BenQProjectorSelect(
                    coordinator,
                    entity_config[0],
                    entity_config[1],
                    entity_config[2],
                    entity_config[3],
                    entity_config[4],
                )
            )

    async_add_entities(entities)


class BenQProjectorSelect(CoordinatorEntity, SelectEntity):
    _attr_has_entity_name = True
    _attr_available = False

    _attr_current_option = None

    def __init__(
        self,
        coordinator: BenQProjectorCoordinator,
        command: str,
        options,
        name: str,
        icon: str | None = None,
        entity_category=None,
    ) -> None:
        """Initialize the select."""
        super().__init__(coordinator, command)

        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"{coordinator.unique_id}-{command}"

        self.command = command
        self._attr_options = options
        self._attr_name = name
        self._attr_icon = icon
        self._attr_entity_category = entity_category

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        if (
            self.coordinator.data
            and self.command in self.coordinator.data
            and self.coordinator.data[self.command]
        ):
            self._attr_current_option = self.coordinator.data[self.command]
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
                and self.command in self.coordinator.data
                and self.coordinator.data[self.command]
            ):
                new_state = self.coordinator.data[self.command]
                if self._attr_current_option != new_state:
                    self._attr_current_option = self.coordinator.data[self.command]
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

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        response = self.coordinator.send_command(self.command, option)
        if response is not None:
            self._attr_current_option = response
            self.async_write_ha_state()
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to set %s to %s", self._attr_name, option)
