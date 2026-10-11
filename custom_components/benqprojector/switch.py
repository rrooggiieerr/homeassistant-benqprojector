"""Creates Switch entities for the BenQ Projector Home Assistant integration."""

import logging

from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import BenQProjectorConfigEntry, BenQProjectorCoordinator
from .entity import BenQProjectorEntity

_LOGGER = logging.getLogger(__name__)


def _config_switch(key: str) -> SwitchEntityDescription:
    return SwitchEntityDescription(
        key=key,
        translation_key=key,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    )


ENTITY_DESCRIPTIONS = [
    SwitchEntityDescription(key="bc", translation_key="bc"),
    _config_switch("qas"),
    _config_switch("directpower"),
    _config_switch("autopower"),
    _config_switch("standbynet"),
    _config_switch("standbymic"),
    _config_switch("standbymnt"),
    SwitchEntityDescription(key="blank", translation_key="blank"),
    SwitchEntityDescription(key="freeze", translation_key="freeze"),
    _config_switch("ins"),
    _config_switch("lpsaver"),
    _config_switch("prjlogincode"),
    _config_switch("broadcasting"),
    _config_switch("amxdd"),
    _config_switch("highaltitude"),
    _config_switch("led"),
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: BenQProjectorConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the BenQ Projector switch."""
    coordinator = config_entry.runtime_data

    async_add_entities(
        BenQProjectorSwitch(coordinator, entity_description, config_entry.entry_id)
        for entity_description in ENTITY_DESCRIPTIONS
        if coordinator.supports_command(entity_description.key)
    )


class BenQProjectorSwitch(BenQProjectorEntity, SwitchEntity):
    """BenQ Projector Switch."""

    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(
        self,
        coordinator: BenQProjectorCoordinator,
        entity_description: SwitchEntityDescription,
        config_entry_id: str,
    ) -> None:
        """Initialize the switch."""
        super().__init__(
            coordinator,
            f"{config_entry_id}-{entity_description.key}",
            entity_description.key,
        )
        self.entity_description = entity_description

    @callback
    def _update_from_data(self) -> None:
        value = self._value
        self._attr_is_on = None if value is None else value == "on"

    async def _async_set(self, action: str) -> None:
        response = await self.coordinator.async_send_command(self._key, action)
        if response != action:
            raise HomeAssistantError(f"Failed to switch {action} {self.entity_id}")
        self.coordinator.async_set_updated_data(
            {**self.coordinator.data, self._key: action}
        )

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the entity on."""
        await self._async_set("on")

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the entity off."""
        await self._async_set("off")
