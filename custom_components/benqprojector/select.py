"""Creates Select entities for the BenQ Projector Home Assistant integration."""

from __future__ import annotations

import logging
import re

from benqprojector import BenQProjector
from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import BenQProjectorCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the BenQ Serial Projector select."""
    coordinator: BenQProjectorCoordinator = config_entry.runtime_data

    entity_descriptions = [
        SelectEntityDescription(
            key="audiosour",
            translation_key="audiosour",
            options=coordinator.projector.audio_sources,
        ),
        SelectEntityDescription(
            key="appmod",
            translation_key="appmod",
            options=coordinator.projector.picture_modes,
        ),
        SelectEntityDescription(
            key="ct",
            translation_key="ct",
            options=coordinator.projector.color_temperatures,
            entity_category=EntityCategory.CONFIG,
        ),
        SelectEntityDescription(
            key="asp",
            translation_key="asp",
            options=coordinator.projector.aspect_ratios,
        ),
        SelectEntityDescription(
            key="lampm",
            translation_key="lampm",
            options=coordinator.projector.lamp_modes,
            entity_category=EntityCategory.CONFIG,
        ),
        SelectEntityDescription(
            key="3d",
            translation_key="3d",
            options=coordinator.projector.threed_modes,
            entity_category=EntityCategory.CONFIG,
        ),
        # SelectEntityDescription(key="rr", None, translation_key="rr", entity_category=EntityCategory.CONFIG],
        SelectEntityDescription(
            key="pp",
            translation_key="pp",
            options=coordinator.projector.projector_positions,
            entity_category=EntityCategory.CONFIG,
        ),
        SelectEntityDescription(
            key="menuposition",
            translation_key="menuposition",
            options=coordinator.projector.menu_positions,
            entity_category=EntityCategory.CONFIG,
        ),
    ]

    entities = []

    for entity_description in entity_descriptions:
        if coordinator.supports_command(entity_description.key):
            entities.append(
                BenQProjectorSelect(
                    coordinator, entity_description, config_entry.entry_id
                )
            )

    async_add_entities(entities)


class BenQProjectorSelect(CoordinatorEntity, SelectEntity):
    """Base BenQ Projector Select."""

    _attr_has_entity_name = True
    _attr_available = False

    def __init__(
        self,
        coordinator: BenQProjectorCoordinator,
        entity_description: SelectEntityDescription,
        config_entry_id: str,
    ) -> None:
        """Initialize the select."""
        super().__init__(coordinator, entity_description.key)

        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"{config_entry_id}-{entity_description.key}"

        self._options_map = {
            re.sub("[^a-z0-9]", "_", value.lower()): value
            for value in entity_description.options
        }

        self.entity_description = entity_description

    async def async_added_to_hass(self) -> None:
        """Called when select is added to Home Assistant."""
        await super().async_added_to_hass()

        if self.coordinator.data and (
            current_option := self.coordinator.data.get(self.entity_description.key)
        ):
            self._attr_current_option = current_option
            self._attr_available = True
        else:
            _LOGGER.debug("%s is not available", self.entity_description.key)
            self._attr_available = False

        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not self._attr_available:
            return self._attr_available

        return self.coordinator.last_update_success

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self.entity_description.key in self.coordinator.data:
            self._attr_current_option = self.coordinator.data.get(
                self.entity_description.key
            )
            self._attr_available = True
        elif self.coordinator.power_status in [
            BenQProjector.POWERSTATUS_POWERINGON,
            BenQProjector.POWERSTATUS_ON,
        ]:
            self._attr_available = True
        else:
            self._attr_available = False

        self.async_write_ha_state()

    @property
    def options(self) -> list[str]:
        return list(self._options_map.keys())

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        option = self._options_map[option]

        response = await self.coordinator.async_send_command(
            self.entity_description.key, option
        )
        if response == option:
            self._attr_current_option = option
            self.async_write_ha_state()
        else:
            _LOGGER.error("Failed to set %s to %s", self.name, option)
