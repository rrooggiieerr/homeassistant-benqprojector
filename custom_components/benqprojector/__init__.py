"""The BenQ Projector integration."""
from __future__ import annotations

import logging
import os

import serial
from benqprojector import BenQProjector
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import CONF_BAUD_RATE, CONF_PROJECTOR, CONF_SERIAL_PORT, DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.MEDIA_PLAYER, Platform.SENSOR, Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up BenQ Projector from a config entry."""
    projector = None

    try:
        serial_port = entry.data[CONF_SERIAL_PORT]
        projector = BenQProjector(serial_port, entry.data[CONF_BAUD_RATE])

        # Open the connection.
        if not projector.connect():
            raise ConfigEntryNotReady(f"Unable to connect to device {serial_port}")

        _LOGGER.info("Device %s is available", serial_port)
    except serial.SerialException as ex:
        raise ConfigEntryNotReady(
            f"Unable to connect to device {serial_port}: {ex}"
        ) from ex

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = projector

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    projector: BenQProjector = hass.data[DOMAIN][entry.entry_id]
    projector.disconnect()

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
