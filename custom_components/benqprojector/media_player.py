"""The BenQ Projector integration."""

from __future__ import annotations

import logging

from benqprojector import BenQProjector
from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import BenQProjectorCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the BenQ Projector media player."""
    coordinator: BenQProjectorCoordinator = config_entry.runtime_data

    async_add_entities([BenQProjectorMediaPlayer(coordinator, config_entry.entry_id)])


class BenQProjectorMediaPlayer(CoordinatorEntity, MediaPlayerEntity):
    _attr_has_entity_name = True
    _attr_name = None
    _attr_device_class = MediaPlayerDeviceClass.TV
    _attr_translation_key = "projector"
    _attr_supported_features = (
        MediaPlayerEntityFeature.VOLUME_MUTE
        | MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.VOLUME_STEP
        | MediaPlayerEntityFeature.TURN_ON
        | MediaPlayerEntityFeature.TURN_OFF
        | MediaPlayerEntityFeature.SELECT_SOURCE
    )

    _attr_available = False
    _attr_state = None

    _attr_source_list = None
    _attr_source = None

    _attr_is_volume_muted = None
    _attr_volume_level = None

    def __init__(
        self, coordinator: BenQProjectorCoordinator, config_entry_id: str
    ) -> None:
        """Initialize the media player."""
        super().__init__(coordinator)

        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"{config_entry_id}-projector"

    def _get_source_translation_key(self, source: str):
        """
        Projectors can have 1 or multiple sources for HDMI, RGB and YPBR. In case multiple sources
        of the same kind are present the source translation should include a sequence number, if
        only one source of a kind is present no sequence number is needed in the translation.
        """
        source_translation_key = source
        if (
            source in ("hdmi", "rgb", "ypbr")
            and len([s for s in self._attr_source_list if s.startswith(source)]) > 1
        ):
            # More than 1 source of this kind present, add "1" to the source to use the translation
            # with sequence number.
            source_translation_key = source + "1"
        return source_translation_key

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        self._attr_source_list = self.coordinator.video_sources
        source_list = [
            self._get_source_translation_key(source)
            for source in self.coordinator.video_sources
        ]
        self._attr_source_list = source_list

        if self.coordinator.power_status == BenQProjector.POWERSTATUS_UNKNOWN:
            _LOGGER.debug("Projector is not available")
            self._attr_available = False
        elif self.coordinator.power_status in [
            BenQProjector.POWERSTATUS_POWERINGON,
            BenQProjector.POWERSTATUS_ON,
        ]:
            self._attr_state = MediaPlayerState.ON

            if self.coordinator.volume is not None:
                self._attr_volume_level = self.coordinator.volume / 20

            self._attr_is_volume_muted = self.coordinator.muted

            self._attr_source = self._get_source_translation_key(
                self.coordinator.video_source
            )

            self._attr_available = True
        elif self.coordinator.power_status == BenQProjector.POWERSTATUS_POWERINGOFF:
            self._attr_state = MediaPlayerState.OFF
            self._attr_available = False
        elif self.coordinator.power_status == BenQProjector.POWERSTATUS_OFF:
            self._attr_state = MediaPlayerState.OFF
            self._attr_available = True

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
        if self.coordinator.power_status == BenQProjector.POWERSTATUS_UNKNOWN:
            self._attr_available = False
        elif self.coordinator.power_status in [
            BenQProjector.POWERSTATUS_POWERINGON,
            BenQProjector.POWERSTATUS_ON,
        ]:
            self._attr_state = MediaPlayerState.ON
            self._attr_available = True
        elif self.coordinator.power_status == BenQProjector.POWERSTATUS_POWERINGOFF:
            self._attr_state = MediaPlayerState.OFF
            self._attr_available = False
        elif self.coordinator.power_status == BenQProjector.POWERSTATUS_OFF:
            self._attr_state = MediaPlayerState.OFF
            self._attr_available = True

        if "vol" in self.coordinator.data:
            self._attr_volume_level = self.coordinator.data.get("vol") / 20.0

        if "mute" in self.coordinator.data:
            self._attr_is_volume_muted = self.coordinator.data.get("mute")

        if "sour" in self.coordinator.data:
            self._attr_source = self._get_source_translation_key(
                self.coordinator.data.get("sour")
            )

        self.async_write_ha_state()

    async def async_turn_on(self) -> None:
        """Turn projector on."""
        if await self.coordinator.async_turn_on():
            self._attr_state = MediaPlayerState.ON

    async def async_turn_off(self) -> None:
        """Turn projector off."""
        if await self.coordinator.async_turn_off():
            self._attr_state = MediaPlayerState.OFF
            self._attr_available = False

    async def async_mute_volume(self, mute: bool) -> None:
        """Mute (true) or unmute (false) media player."""
        if mute:
            await self.coordinator.async_mute()
        else:
            await self.coordinator.async_unmute()

        self._attr_is_volume_muted = self.coordinator.muted
        self.async_write_ha_state()

    async def async_set_volume_level(self, volume: float) -> None:
        """Set volume level, range 0..1."""
        volume = int(volume * 20.0)
        if await self.coordinator.async_volume_level(volume):
            self._attr_volume_level = self.coordinator.volume / 20.0
            self.async_write_ha_state()

    async def async_volume_up(self) -> None:
        """Increase volume."""
        if await self.coordinator.async_volume_up():
            self._attr_volume_level = self.coordinator.volume / 20.0
            self._attr_is_volume_muted = False
            self.async_write_ha_state()

    async def async_volume_down(self) -> None:
        """Decrease volume."""
        if await self.coordinator.async_volume_down():
            self._attr_volume_level = self.coordinator.volume / 20.0
            self._attr_is_volume_muted = False
            self.async_write_ha_state()

    async def async_select_source(self, source: str) -> None:
        """Set the input video source."""
        video_source = source.rstrip("1")
        if await self.coordinator.async_select_video_source(video_source):
            self._attr_source = source
            self.async_write_ha_state()
