"""Creates Select entities for the BenQ Projector Home Assistant integration."""

import logging
import re

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import BenQProjectorConfigEntry, BenQProjectorCoordinator
from .entity import BenQProjectorEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: BenQProjectorConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the BenQ Serial Projector select."""
    coordinator = config_entry.runtime_data
    projector = coordinator.projector

    entity_descriptions = [
        SelectEntityDescription(
            key="audiosour",
            translation_key="audiosour",
            options=projector.audio_sources,
        ),
        SelectEntityDescription(
            key="appmod",
            translation_key="appmod",
            options=projector.picture_modes,
        ),
        SelectEntityDescription(
            key="ct",
            translation_key="ct",
            options=projector.color_temperatures,
            entity_category=EntityCategory.CONFIG,
        ),
        SelectEntityDescription(
            key="asp",
            translation_key="asp",
            options=projector.aspect_ratios,
        ),
        SelectEntityDescription(
            key="lampm",
            translation_key="lampm",
            options=projector.lamp_modes,
            entity_category=EntityCategory.CONFIG,
        ),
        SelectEntityDescription(
            key="3d",
            translation_key="3d",
            options=projector.threed_modes,
            entity_category=EntityCategory.CONFIG,
        ),
        SelectEntityDescription(
            key="pp",
            translation_key="pp",
            options=projector.projector_positions,
            entity_category=EntityCategory.CONFIG,
        ),
        SelectEntityDescription(
            key="menuposition",
            translation_key="menuposition",
            options=projector.menu_positions,
            entity_category=EntityCategory.CONFIG,
        ),
    ]

    async_add_entities(
        BenQProjectorSelect(coordinator, entity_description, config_entry.entry_id)
        for entity_description in entity_descriptions
        if entity_description.options
        and coordinator.supports_command(entity_description.key)
    )


def _option_key(value: str) -> str:
    """Option keys must be lowercase a-z, 0-9 and _ for translations."""
    return re.sub("[^a-z0-9]", "_", value.lower())


class BenQProjectorSelect(BenQProjectorEntity, SelectEntity):
    """BenQ Projector Select."""

    def __init__(
        self,
        coordinator: BenQProjectorCoordinator,
        entity_description: SelectEntityDescription,
        config_entry_id: str,
    ) -> None:
        """Initialize the select."""
        super().__init__(
            coordinator,
            f"{config_entry_id}-{entity_description.key}",
            entity_description.key,
        )
        self.entity_description = entity_description

        # option key -> value the projector uses, e.g. "16_9" -> "16:9"
        self._options_map = {
            _option_key(value): value for value in entity_description.options
        }
        self._attr_options = list(self._options_map)

    @callback
    def _update_from_data(self) -> None:
        # The projector reports the raw value, map it to the option key so values like
        # "16:9" or "2.35" show.
        value = self._value
        self._attr_current_option = None if value is None else _option_key(value)

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        value = self._options_map[option]

        response = await self.coordinator.async_send_command(self._key, value)
        if response is None or response.lower() != value.lower():
            raise HomeAssistantError(f"Failed to set {self.entity_id} to {option}")
        self.coordinator.async_set_updated_data(
            {**self.coordinator.data, self._key: value}
        )
