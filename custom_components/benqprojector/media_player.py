"""The BenQ Projector integration."""
from __future__ import annotations

import logging
from datetime import timedelta

from benqprojector import BenQProjector
from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=5)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the BenQ Projector media player."""
    projector: BenQProjector = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([BenQProjectorMediaPlayer(projector)])


class BenQProjectorMediaPlayer(MediaPlayerEntity):
    _attr_has_entity_name = True
    _attr_name = "Projector"
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
    # _attr_should_poll = False

    _attr_available = False
    _attr_state = None

    _attr_source = None

    _attr_is_volume_muted = None
    _attr_volume_level = None

    _attr_extra_state_attributes = {}

    _update_counter = 1

    def __init__(self, projector: BenQProjector) -> None:
        """Initialize the sensor."""
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, projector._unique_id)},
            name=f"BenQ {projector.model}",
            model=projector.model,
            manufacturer="BenQ",
        )
        self._attr_unique_id = f"{projector._unique_id}-mediaplayer"
        self._attr_source_list = projector.sources

        self._projector = projector

    async def async_update(self) -> None:
        """Update state of device."""
        if self._update_counter % 10 == 0:
            _LOGGER.debug("Full update")
            if not self._projector.update():
                return
        else:
            _LOGGER.debug("Partial update")
            if not self._projector.update_power():
                return

            elif self._projector.power_status in [
                BenQProjector.POWERSTATUS_POWERINGON,
                BenQProjector.POWERSTATUS_ON
            ]:
                self._projector.update_source()
                self._projector.update_volume()

        if self._projector.power_status in [
            BenQProjector.POWERSTATUS_POWERINGON,
            BenQProjector.POWERSTATUS_ON,
        ]:
            self._attr_state = MediaPlayerState.ON
            self._attr_available = True
        elif self._projector.power_status == BenQProjector.POWERSTATUS_POWERINGOFF:
            self._attr_available = False
            self._attr_state = MediaPlayerState.OFF
        elif self._projector.power_status == BenQProjector.POWERSTATUS_OFF:
            self._attr_state = MediaPlayerState.OFF
            self._attr_available = True

        self._attr_extra_state_attributes[
            "projector_position"
        ] = self._projector.position

        if self._projector.lamp2_time is not None:
            self._attr_extra_state_attributes["lamp1_time"] = self._projector.lamp_time
            self._attr_extra_state_attributes["lamp2_time"] = self._projector.lamp2_time
        else:
            self._attr_extra_state_attributes["lamp_time"] = self._projector.lamp_time

        if self._projector.power_status == BenQProjector.POWERSTATUS_ON:
            self._attr_extra_state_attributes["3d"] = self._projector.threed
            self._attr_extra_state_attributes[
                "picture_mode"
            ] = self._projector.picture_mode
            self._attr_extra_state_attributes[
                "aspect_ratio"
            ] = self._projector.aspect_ratio
            self._attr_extra_state_attributes[
                "brilliant_color"
            ] = self._projector.brilliant_color
            self._attr_extra_state_attributes["blank"] = self._projector.blank

            self._attr_extra_state_attributes[
                "picture_brightness"
            ] = self._projector.brightness
            self._attr_extra_state_attributes[
                "picture_contrast"
            ] = self._projector.contrast
            self._attr_extra_state_attributes[
                "picture_sharpness"
            ] = self._projector.sharpness
            self._attr_extra_state_attributes[
                "picture_color_temperature"
            ] = self._projector.color_temperature

            self._attr_extra_state_attributes[
                "color_value"
            ] = self._projector.color_value
            self._attr_extra_state_attributes[
                "high_altitude"
            ] = self._projector.high_altitude
            self._attr_extra_state_attributes["lamp_mode"] = self._projector.lamp_mode
            self._attr_extra_state_attributes[
                "quick_auto_search"
            ] = self._projector.quick_auto_search

            volume_level = None
            if self._projector.volume is not None:
                volume_level = self._projector.volume / 20.0
            self._attr_volume_level = volume_level

            self._attr_is_volume_muted = self._projector.muted

            self._attr_source = self._projector.source

            self.async_write_ha_state()

            self._update_counter += 1

    async def async_turn_on(self) -> None:
        """Turn projector on."""
        if self._projector.turn_on():
            self._attr_state = MediaPlayerState.ON

    async def async_turn_off(self) -> None:
        """Turn projector off."""
        if self._projector.turn_off():
            self._attr_state = MediaPlayerState.OFF
            self._attr_available = False

    async def async_mute_volume(self, mute: bool) -> None:
        """Mute (true) or unmute (false) media player."""
        if mute is True and self._projector.mute():
            self._attr_is_volume_muted = True
            self.async_write_ha_state()
        elif mute is False and self._projector.unmute():
            self._attr_is_volume_muted = False
            self.async_write_ha_state()

    async def async_set_volume_level(self, volume: float) -> None:
        """Set volume level, range 0..1."""
        _LOGGER.debug("async_set_volume_level(%s)", volume)

        volume = int(volume * 20.0)
        if self._projector.volume_level(volume):
            self._attr_volume_level = self._projector.volume / 20.0
            self.async_write_ha_state()

    async def async_volume_up(self) -> None:
        """Increase volume."""
        if self._projector.volume_up():
            self._attr_volume_level = self._projector.volume / 20.0
            self.async_write_ha_state()

    async def async_volume_down(self) -> None:
        """Decrease volume."""
        if self._projector.volume_down():
            self._attr_volume_level = self._projector.volume / 20.0
            self.async_write_ha_state()

    async def async_select_source(self, source: str) -> None:
        """Set the input source."""
        if self._projector.select_source(source):
            self._attr_source = source
            self.async_write_ha_state()
