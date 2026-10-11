"""Creates Media Player entities for the BenQ Projector Home Assistant integration."""

import logging

from benqprojector import BenQProjector
from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import BenQProjectorConfigEntry
from .entity import BenQProjectorEntity

_LOGGER = logging.getLogger(__name__)

# Volume range of the projector.
MAX_VOLUME = 20


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: BenQProjectorConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the BenQ Projector media player."""
    coordinator = config_entry.runtime_data

    async_add_entities(
        [BenQProjectorMediaPlayer(coordinator, f"{config_entry.entry_id}-projector")]
    )


class BenQProjectorMediaPlayer(BenQProjectorEntity, MediaPlayerEntity):
    """BenQ Projector Media Player."""

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
    # Power can be switched while the projector is off.
    _requires_power_on = False

    def _source_translation_key(self, source: str | None) -> str | None:
        """
        Projectors can have 1 or multiple sources for HDMI, RGB and YPBR. In case multiple sources
        of the same kind are present the source translation should include a sequence number, if
        only one source of a kind is present no sequence number is needed in the translation.
        """
        if source is None:
            return None
        if (
            source in ("hdmi", "rgb", "ypbr")
            and len([s for s in self.coordinator.video_sources if s.startswith(source)])
            > 1
        ):
            return source + "1"
        return source

    @callback
    def _update_from_data(self) -> None:
        self._attr_source_list = [
            self._source_translation_key(source)
            for source in self.coordinator.video_sources
        ]

        power_status = self.coordinator.power_status
        if power_status in (
            BenQProjector.POWERSTATUS_POWERINGON,
            BenQProjector.POWERSTATUS_ON,
        ):
            self._attr_state = MediaPlayerState.ON
        elif power_status in (
            BenQProjector.POWERSTATUS_POWERINGOFF,
            BenQProjector.POWERSTATUS_OFF,
        ):
            self._attr_state = MediaPlayerState.OFF
        else:
            self._attr_state = None

        if self._attr_state == MediaPlayerState.ON:
            volume = self.coordinator.volume
            self._attr_volume_level = (
                None if volume is None else min(volume / MAX_VOLUME, 1.0)
            )
            self._attr_is_volume_muted = self.coordinator.muted
            self._attr_source = self._source_translation_key(
                self.coordinator.video_source
            )
        else:
            self._attr_volume_level = None
            self._attr_is_volume_muted = None
            self._attr_source = None

    def _write_state(self) -> None:
        self._update_from_data()
        self.async_write_ha_state()

    async def async_turn_on(self) -> None:
        """Turn projector on."""
        if not await self.coordinator.async_turn_on():
            raise HomeAssistantError(f"{self.coordinator.name} did not turn on")
        self._write_state()

    async def async_turn_off(self) -> None:
        """Turn projector off."""
        if not await self.coordinator.async_turn_off():
            raise HomeAssistantError(f"{self.coordinator.name} did not turn off")
        self._write_state()

    async def async_mute_volume(self, mute: bool) -> None:
        """Mute (true) or unmute (false) media player."""
        if mute:
            result = await self.coordinator.async_mute()
        else:
            result = await self.coordinator.async_unmute()
        if not result:
            raise HomeAssistantError(
                f"Failed to change mute of {self.coordinator.name}"
            )
        self._write_state()

    async def async_set_volume_level(self, volume: float) -> None:
        """Set volume level, range 0..1."""
        if not await self.coordinator.async_volume_level(round(volume * MAX_VOLUME)):
            raise HomeAssistantError(f"Failed to set volume of {self.coordinator.name}")
        self._write_state()

    async def async_volume_up(self) -> None:
        """Increase volume."""
        if await self.coordinator.async_volume_up():
            self._write_state()

    async def async_volume_down(self) -> None:
        """Decrease volume."""
        if await self.coordinator.async_volume_down():
            self._write_state()

    async def async_select_source(self, source: str) -> None:
        """Set the input video source."""
        video_source = source.rstrip("1")
        if not await self.coordinator.async_select_video_source(video_source):
            raise HomeAssistantError(
                f"Failed to select source {source} on {self.coordinator.name}"
            )
        self._write_state()
