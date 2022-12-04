import logging
from datetime import timedelta

from benqprojector import BenQProjector
from homeassistant.components.select import SelectEntity
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
        ["audiosour", projector.audio_sources, "Audio Source", "mdi:audio-input-rca"],
        ["appmod", projector.picture_modes, "Picture Mode", None],
        ["ct", projector.color_temperatures, "Color Temperature", "mdi:thermometer"],
        ["asp", projector.aspect_ratios, "Aspect Ratio", "mdi:aspect-ratio"],
        ["lampm", projector.lamp_modes, "Lamp Mode", None],
        ["3d", projector.threed_modes, "3D Sync", None],
        # ["rr", None, "Remote Receiver", None],
        ["pp", projector.projector_positions, "Projector Position", None],
    ]

    entities = []

    for entity_config in entities_config:
        if projector.supports_command(entity_config[0]):
            entities.append(
                BenQProjectorSelect(
                    projector,
                    entity_config[0],
                    entity_config[1],
                    entity_config[2],
                    entity_config[3],
                )
            )

    async_add_entities(entities)


class BenQProjectorSelect(SelectEntity):
    _attr_has_entity_name = True
    _attr_available = False

    _attr_current_option = None

    def __init__(
        self,
        projector,
        command,
        options,
        name,
        icon=None,
    ) -> None:
        """Initialize the select."""
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, projector._unique_id)},
            name=f"BenQ {projector.model}",
            model=projector.model,
            manufacturer="BenQ",
        )

        self._attr_unique_id = f"{projector._unique_id}-{command}"

        self._projector = projector
        self._command = command
        self._attr_options = options
        self._attr_name = name
        self._attr_icon = icon

    async def async_added_to_hass(self) -> None:
        await self.async_update()

    async def async_update(self) -> None:
        if self._projector.power_status == BenQProjector.POWERSTATUS_ON:
            self._attr_available = True
            response = self._projector.send_command(self._command)
            if response is not None:
                if self._attr_current_option != response:
                    self._attr_current_option = response
                    self.async_write_ha_state()
            elif self._attr_available != False:
                self._attr_available = False
                self.async_write_ha_state()
        elif self._attr_available != False:
            self._attr_available = False
            self.async_write_ha_state()

        self.async_write_ha_state()

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        response = self._projector.send_command(self._command, option)
        if response is not None:
            self._attr_current_option = response
            self.async_write_ha_state()
        else:
            _LOGGER.error("Failed to set %s to %s", self._attr_name, option)
