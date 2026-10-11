"""Creates Number entities for the BenQ Projector Home Assistant integration."""

import logging

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import BenQProjectorConfigEntry, BenQProjectorCoordinator
from .entity import BenQProjectorEntity

_LOGGER = logging.getLogger(__name__)


def _config_number(
    key: str, max_value: float, min_value: float = 0
) -> NumberEntityDescription:
    return NumberEntityDescription(
        key=key,
        translation_key=key,
        native_min_value=min_value,
        native_max_value=max_value,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    )


ENTITY_DESCRIPTIONS = [
    NumberEntityDescription(key="con", translation_key="con", native_max_value=100),
    NumberEntityDescription(key="bri", translation_key="bri", native_max_value=100),
    NumberEntityDescription(key="color", translation_key="color", native_max_value=20),
    NumberEntityDescription(key="sharp", translation_key="sharp", native_max_value=20),
    NumberEntityDescription(
        key="micvol", translation_key="micvol", native_max_value=20
    ),
    _config_number("keyst", 20),
    _config_number("hkeystone", 20),
    _config_number("vkeystone", 20),
    _config_number("rgain", 200),
    _config_number("ggain", 200),
    _config_number("bgain", 200),
    _config_number("roffset", 511),
    _config_number("goffset", 511),
    _config_number("boffset", 511),
    _config_number("hdrbri", 2, -2),
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: BenQProjectorConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the BenQ Serial Projector number."""
    coordinator = config_entry.runtime_data

    async_add_entities(
        BenQProjectorNumber(coordinator, entity_description, config_entry.entry_id)
        for entity_description in ENTITY_DESCRIPTIONS
        if coordinator.supports_command(entity_description.key)
    )


class BenQProjectorNumber(BenQProjectorEntity, NumberEntity):
    """BenQ Projector Number."""

    _attr_native_step = 1

    def __init__(
        self,
        coordinator: BenQProjectorCoordinator,
        entity_description: NumberEntityDescription,
        config_entry_id: str,
    ) -> None:
        """Initialize the number."""
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
            self._attr_native_value = None if value is None else float(value)
        except (TypeError, ValueError):
            _LOGGER.debug("Invalid value for %s: %s", self._key, value)
            self._attr_native_value = None

    async def async_set_native_value(self, value: float) -> None:
        """
        The projector only supports stepping a value up or down, one step at a time.
        """
        if not self.available or self.native_value is None:
            raise HomeAssistantError(f"{self.entity_id} can only be changed while on")

        current = self.native_value
        step = self.native_step or 1
        action = "+" if value > current else "-"
        for _ in range(round(abs(value - current) / step)):
            if await self.coordinator.async_send_command(self._key, action) != action:
                break
            current += step if action == "+" else -step

        self.coordinator.async_set_updated_data(
            {**self.coordinator.data, self._key: str(current)}
        )
        if current != value:
            raise HomeAssistantError(f"{self.entity_id} stopped at {current}")
