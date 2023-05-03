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
    """Set up the BenQ Projector media player."""
    coordinator: BenQProjectorCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    # Fetch initial data so we have data when entities subscribe
    await coordinator.async_config_entry_first_refresh()

    async_add_entities([BenQProjectorMediaPlayer(coordinator)])


class BenQProjectorMediaPlayer(CoordinatorEntity, MediaPlayerEntity):
    _attr_has_entity_name = True
    _attr_name = None
    _attr_device_class = MediaPlayerDeviceClass.TV
    _attr_icon = "mdi:projector"
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

    def __init__(self, coordinator: BenQProjectorCoordinator) -> None:
        """Initialize the media player."""
        super().__init__(coordinator)

        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"{coordinator.unique_id}-mediaplayer"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        if self.coordinator.projector:
            if self.coordinator.power_status in [
                BenQProjector.POWERSTATUS_POWERINGON,
                BenQProjector.POWERSTATUS_ON,
            ]:
                self._attr_state = MediaPlayerState.ON

                self._attr_volume_level = self.coordinator.volume
                self._attr_is_volume_muted = self.coordinator.muted

                self._attr_source = self.coordinator.video_source

                self._attr_available = True
            elif self.coordinator.power_status == BenQProjector.POWERSTATUS_POWERINGOFF:
                self._attr_state = MediaPlayerState.OFF
                self._attr_available = False
            elif self.coordinator.power_status == BenQProjector.POWERSTATUS_OFF:
                self._attr_state = MediaPlayerState.OFF
                self._attr_available = True

            self._attr_source_list = self.coordinator.projector.video_sources

            self.async_write_ha_state()
        else:
            _LOGGER.debug("%s is not available", self.command)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        updated = False

        if self.coordinator.power_status in [
            BenQProjector.POWERSTATUS_POWERINGON,
            BenQProjector.POWERSTATUS_ON,
        ]:
            volume_level = None
            if self.coordinator.volume is not None:
                volume_level = self.coordinator.volume
            if self._attr_volume_level != volume_level:
                self._attr_volume_level = volume_level
                updated = True

            if self._attr_is_volume_muted != self.coordinator.muted:
                self._attr_is_volume_muted = self.coordinator.muted
                updated = True

            if self._attr_source != self.coordinator.video_source:
                self._attr_source = self.coordinator.video_source
                updated = True

            if (
                self._attr_state != MediaPlayerState.ON
                or self._attr_available is not True
            ):
                self._attr_state = MediaPlayerState.ON
                self._attr_available = True
                updated = True
        elif self.coordinator.power_status == BenQProjector.POWERSTATUS_POWERINGOFF:
            if (
                self._attr_state != MediaPlayerState.OFF
                or self._attr_available is not False
            ):
                self._attr_state = MediaPlayerState.OFF
                self._attr_available = False
                updated = True
        elif self.coordinator.power_status == BenQProjector.POWERSTATUS_OFF:
            if (
                self._attr_state != MediaPlayerState.OFF
                or self._attr_available is not True
            ):
                self._attr_state = MediaPlayerState.OFF
                self._attr_available = True
                updated = True

        # Only update the HA state if state has updated.
        if updated:
            self.async_write_ha_state()

    async def async_turn_on(self) -> None:
        """Turn projector on."""
        if self.coordinator.turn_on():
            self._attr_state = MediaPlayerState.ON

    async def async_turn_off(self) -> None:
        """Turn projector off."""
        if self.coordinator.turn_off():
            self._attr_state = MediaPlayerState.OFF
            self._attr_available = False

    async def async_mute_volume(self, mute: bool) -> None:
        """Mute (true) or unmute (false) media player."""
        if mute is True and self.coordinator.projector.mute():
            self._attr_is_volume_muted = True
            self.async_write_ha_state()
        elif mute is False and self.coordinator.projector.unmute():
            self._attr_is_volume_muted = False
            self.async_write_ha_state()

    async def async_set_volume_level(self, volume: float) -> None:
        """Set volume level, range 0..1."""
        _LOGGER.debug("async_set_volume_level(%s)", volume)

        volume = int(volume * 20.0)
        if self.coordinator.projector.volume_level(volume):
            self._attr_volume_level = self.coordinator.projector.volume / 20.0
            self.async_write_ha_state()

    async def async_volume_up(self) -> None:
        """Increase volume."""
        if self.coordinator.projector.volume_up():
            self._attr_volume_level = self.coordinator.projector.volume / 20.0
            self._attr_is_volume_muted = False
            self.async_write_ha_state()

    async def async_volume_down(self) -> None:
        """Decrease volume."""
        if self.coordinator.projector.volume_down():
            self._attr_volume_level = self.coordinator.projector.volume / 20.0
            self._attr_is_volume_muted = False
            self.async_write_ha_state()

    async def async_select_source(self, source: str) -> None:
        """Set the input video source."""
        if self.coordinator.projector.select_video_source(source):
            self._attr_source = source
            self.async_write_ha_state()
