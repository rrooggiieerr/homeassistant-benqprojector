"""The BenQ Projector integration."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Callable

import homeassistant.helpers.config_validation as cv
import serial
import voluptuous as vol
from benqprojector import BenQProjector
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICE_ID, Platform
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_BAUD_RATE, CONF_PROJECTOR, CONF_SERIAL_PORT, DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.MEDIA_PLAYER,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.SELECT,
    Platform.NUMBER,
]

CONF_SERVICE_COMMAND = "command"
CONF_SERVICE_ACTION = "action"

SERVICE_SEND_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DEVICE_ID): cv.string,
        vol.Required(CONF_SERVICE_COMMAND): cv.string,
        vol.Required(CONF_SERVICE_ACTION): cv.string,
    }
)
SERVICE_SEND_RAW_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DEVICE_ID): cv.string,
        vol.Required(CONF_SERVICE_COMMAND): cv.string,
    }
)


class BenQProjectorCoordinator(DataUpdateCoordinator):
    """BenQ Projector Data Update Coordinator."""

    unique_id = None
    model = None
    device_info: DeviceInfo = None
    power_status = None
    volume = None
    muted = None
    video_source = None

    _listener_commands = []

    def __init__(self, hass, serial_port: str, baud_rate: int):
        """Initialize BenQ Projector Data Update Coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name=__name__,
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(seconds=5),
        )

        self._serial_port = serial_port
        self.projector = BenQProjector(self._serial_port, baud_rate)

    async def connect(self):
        if not self.projector.connect():
            raise ConfigEntryNotReady(
                f"Unable to connect to BenQ projector on {self._serial_port}"
            )

        self.unique_id = self.projector.unique_id
        self.model = self.projector.model
        self.power_status = self.projector.power_status

        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, self.unique_id)},
            name=f"BenQ {self.model}",
            model=self.model,
            manufacturer="BenQ",
        )

    async def disconnect(self):
        await self.projector.disconnect()

    @callback
    def async_add_listener(
        self, update_callback: CALLBACK_TYPE, context: Any = None
    ) -> Callable[[], None]:
        remove_listener = super().async_add_listener(update_callback, context)

        _LOGGER.debug("Adding listener for %s", context)
        if context:
            if context not in self._listener_commands:
                self._listener_commands.append(context)
                if (
                    context in ["pp", "ltim", "ltim2"]
                    or self.power_status == BenQProjector.POWERSTATUS_ON
                ):
                    if self.data:
                        self.data[context] = self.send_command(context)
                        _LOGGER.debug(self.data)

        return remove_listener

    def supports_command(self, command: str):
        return self.projector.supports_command(command)

    def send_command(self, command: str, action: str | None = None):
        if action:
            return self.projector.send_command(command, action)
        return self.projector.send_command(command)

    def send_raw_command(self, command: str):
        return self.projector.send_raw_command(command)

    def turn_on(self) -> bool:
        if self.projector.turn_on():
            self.power_status = self.projector.power_status
            return True

        return False

    def turn_off(self) -> bool:
        if self.projector.turn_off():
            self.power_status = self.projector.power_status
            return True

        return False

    async def _async_update_data(self):
        """Fetch data from BenQ Projector."""
        _LOGGER.debug("BenQProjectorCoordinator._async_updadatata")

        if not self.projector.update_power():
            return None

        power_status = self.projector.power_status
        if power_status is None:
            raise UpdateFailed(
                f"Error communicating with BenQ projector on {self._serial_port}"
            )

        self.power_status = power_status

        data = {}

        data["pp"] = self.send_command("pp")
        data["ltim"] = self.send_command("ltim")
        if self.supports_command("ltim2"):
            data["ltim2"] = self.send_command("ltim2")

        if self.power_status == BenQProjector.POWERSTATUS_ON:
            self.projector.update_volume()
            volume_level = None
            if self.projector.volume is not None:
                volume_level = self.projector.volume / 20.0
            self.volume = volume_level

            self.muted = self.projector.muted

            self.projector.update_video_source()
            self.video_source = self.projector.video_source

            for command in self._listener_commands:
                if command not in ["pow", "pp", "ltim", "ltim2"]:
                    data[command] = self.send_command(command)

        return data


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up BenQ Projector from a config entry."""
    try:
        serial_port = entry.data[CONF_SERIAL_PORT]
        projector_coordinator = BenQProjectorCoordinator(
            hass, serial_port, entry.data[CONF_BAUD_RATE]
        )

        # Open the connection.
        await projector_coordinator.connect()

        _LOGGER.info("BenQ projector on %s is available", serial_port)
    except serial.SerialException as ex:
        raise ConfigEntryNotReady(
            f"Unable to connect to BenQ projector on {serial_port}: {ex}"
        ) from ex

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = projector_coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def async_handle_send(call: ServiceCall):
        """Handle the send service call."""
        command: str = call.data.get(CONF_SERVICE_COMMAND)
        action: str = call.data.get(CONF_SERVICE_ACTION)

        projector_coordinator.send_command(command, action)

    async def async_handle_send_raw(call: ServiceCall):
        """Handle the send_raw service call."""
        command: str = call.data.get(CONF_SERVICE_COMMAND)

        projector_coordinator.send_raw_command(command)

    hass.services.async_register(
        DOMAIN, "send", async_handle_send, schema=SERVICE_SEND_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, "send_raw", async_handle_send_raw, schema=SERVICE_SEND_RAW_SCHEMA
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    projector_coordinator: BenQProjectorCoordinator = hass.data[DOMAIN][entry.entry_id]
    await projector_coordinator.disconnect()

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
