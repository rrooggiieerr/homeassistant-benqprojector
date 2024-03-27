"""The BenQ Projector integration."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Callable

import homeassistant.helpers.config_validation as cv
import serial
import voluptuous as vol
from benqprojector import BenQProjector, BenQProjectorSerial, BenQProjectorTelnet
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICE_ID, Platform, CONF_HOST, CONF_PORT, CONF_TYPE
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_BAUD_RATE, CONF_PROJECTOR, CONF_SERIAL_PORT, CONF_TYPE_SERIAL, CONF_TYPE_TELNET, DOMAIN

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

    def __init__(self, hass, projector: BenQProjector):
        """Initialize BenQ Projector Data Update Coordinator."""
        update_interval = timedelta(seconds=15)
        if isinstance(projector, BenQProjectorSerial):
            update_interval = timedelta(seconds=5)

        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name=__name__,
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=update_interval,
        )

        self.projector = projector

        self.unique_id = self.projector.unique_id
        self.model = self.projector.model
        self.power_status = self.projector.power_status

        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, self.unique_id)},
            name=f"BenQ {self.model}",
            model=self.model,
            manufacturer="BenQ",
        )

    # async def async_connect(self):
    #     try:
    #         if not await self.hass.async_add_executor_job(self.projector.connect):
    #             raise ConfigEntryNotReady(
    #                 f"Unable to connect to BenQ projector on {self.projector.connection}"
    #             )
    #     except TimeoutError as ex:
    #         raise ConfigEntryNotReady(
    #             f"Unable to connect to BenQ projector on {self.projector.connection}", ex
    #         )
    #
    #     _LOGGER.debug("Connected to BenQ projector on %s", self.projector.connection)
    #
    #     self.unique_id = self.projector.unique_id
    #     self.model = self.projector.model
    #     self.power_status = self.projector.power_status
    #
    #     self.device_info = DeviceInfo(
    #         identifiers={(DOMAIN, self.unique_id)},
    #         name=f"BenQ {self.model}",
    #         model=self.model,
    #         manufacturer="BenQ",
    #     )

    async def async_disconnect(self):
        await self.hass.async_add_executor_job(self.projector.disconnect)
        _LOGGER.debug("Disconnected from BenQ projector on %s", self.projector.connection)

    @callback
    def async_add_listener(
        self, update_callback: CALLBACK_TYPE, context: Any = None
    ) -> Callable[[], None]:
        remove_listener = super().async_add_listener(update_callback, context)

        _LOGGER.debug("Adding listener for %s", context)
        if context:
            if context not in self._listener_commands:
                self._listener_commands.append(context)

        return remove_listener

    def supports_command(self, command: str):
        return self.projector.supports_command(command)

    async def async_send_command(self, command: str, action: str | None = None):
        if action:
            return await self.hass.async_add_executor_job(
                self.projector.send_command, command, action
            )
        return await self.hass.async_add_executor_job(
            self.projector.send_command, command
        )

    async def async_send_raw_command(self, command: str):
        return await self.hass.async_add_executor_job(
            self.projector.send_raw_command, command
        )

    async def async_turn_on(self) -> bool:
        if await self.hass.async_add_executor_job(self.projector.turn_on):
            self.power_status = self.projector.power_status
            return True

        return False

    async def async_turn_off(self) -> bool:
        if await self.hass.async_add_executor_job(self.projector.turn_off):
            self.power_status = self.projector.power_status
            return True

        return False

    async def async_mute(self) -> bool:
        if await self.hass.async_add_executor_job(self.projector.mute):
            self.muted = True
            return True

        return False

    async def async_unmute(self) -> bool:
        if await self.hass.async_add_executor_job(self.projector.unmute):
            self.muted = False
            return True

        return False

    async def async_volume_level(self, volume: int):
        if await self.hass.async_add_executor_job(self.projector.volume_level, volume):
            self.volume = volume
            return True

        return False

    async def async_volume_up(self):
        if await self.hass.async_add_executor_job(self.projector.volume_up):
            self.volume += 1
            return True

        return False

    async def async_volume_down(self):
        if await self.hass.async_add_executor_job(self.projector.volume_down):
            self.volume -= 1
            return True

        return False

    async def async_select_video_source(self, source: str):
        if await self.hass.async_add_executor_job(
            self.projector.select_video_source, source
        ):
            self.source = source
            return True

        return False

    async def _async_update_data(self):
        """Fetch data from BenQ Projector."""
        _LOGGER.debug("BenQProjectorCoordinator._async_update_data")

        if self.projector.busy:
            return None

        try:
            if not await self.hass.async_add_executor_job(self.projector.update_power):
                return None
        except TimeoutError as ex:
            raise UpdateFailed(
                f"Error communicating with BenQ projector on {self.projector.connection}", ex,
            )

        power_status = self.projector.power_status
        if power_status is None:
            raise UpdateFailed(
                f"Error communicating with BenQ projector on {self.projector.connection}"
            )

        self.power_status = power_status

        data = {}

        if (pp := await self.async_send_command("pp")) is not None:
            data["pp"] = pp
        if (ltim := await self.async_send_command("ltim")) is not None:
            data["ltim"] = ltim
        if self.supports_command("ltim2"):
            if (ltim2 := await self.async_send_command("ltim2")) is not None:
                data["ltim2"] = ltim2

        if self.power_status == self.projector.POWERSTATUS_ON:
            await self.hass.async_add_executor_job(self.projector.update_volume)
            volume_level = None
            if self.projector.volume is not None:
                volume_level = self.projector.volume / 20.0
            self.volume = volume_level

            self.muted = self.projector.muted

            await self.hass.async_add_executor_job(self.projector.update_video_source)
            self.video_source = self.projector.video_source

            for command in self._listener_commands:
                if command not in ["pow", "pp", "ltim", "ltim2"]:
                    data[command] = await self.async_send_command(command)

        return data


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up BenQ Projector from a config entry."""
    projector = None

    conf_type = CONF_TYPE_SERIAL
    if CONF_TYPE in entry.data:
        conf_type = entry.data[CONF_TYPE]

    if conf_type == CONF_TYPE_TELNET:
        host = entry.data[CONF_HOST]
        port = entry.data[CONF_PORT]

        # Test if we can connect to the device.
        projector = BenQProjectorTelnet(host, port)

        # Open the connection.
        if not await hass.async_add_executor_job(projector.connect):
            raise ConfigEntryNotReady(f"Unable to connect to device {host}:{port}")
    else:
        serial_port = entry.data[CONF_SERIAL_PORT]
        baud_rate = entry.data[CONF_BAUD_RATE]

        # Test if we can connect to the device.
        try:
            projector = BenQProjectorSerial(serial_port, baud_rate)

            # Open the connection.
            if not await hass.async_add_executor_job(projector.connect):
                raise ConfigEntryNotReady(f"Unable to connect to device {serial_port}")
    
            _LOGGER.info("Device %s is available", serial_port)
        except serial.SerialException as ex:
            raise ConfigEntryNotReady(
                f"Unable to connect to device {serial_port}"
            ) from ex

    coordinator = BenQProjectorCoordinator(hass, projector)

    # try:
    #     serial_port = entry.data[CONF_SERIAL_PORT]
    #     coordinator = BenQProjectorCoordinator(
    #         hass, serial_port, entry.data[CONF_BAUD_RATE]
    #     )
    #
    #     # Open the connection.
    #     await coordinator.async_connect()
    #
    #     _LOGGER.info("BenQ projector on %s is available", serial_port)
    # except serial.SerialException as ex:
    #     raise ConfigEntryNotReady(
    #         f"Unable to connect to BenQ projector on {serial_port}: {ex}"
    #     ) from ex

    # Fetch initial data so we have data when entities subscribe
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    await coordinator.async_request_refresh()

    async def async_handle_send(call: ServiceCall):
        """Handle the send service call."""
        command: str = call.data.get(CONF_SERVICE_COMMAND)
        action: str = call.data.get(CONF_SERVICE_ACTION)

        await coordinator.async_send_command(command, action)

    async def async_handle_send_raw(call: ServiceCall):
        """Handle the send_raw service call."""
        command: str = call.data.get(CONF_SERVICE_COMMAND)

        await coordinator.async_send_raw_command(command)

    hass.services.async_register(
        DOMAIN, "send", async_handle_send, schema=SERVICE_SEND_SCHEMA
    )

    hass.services.async_register(
        DOMAIN, "send_raw", async_handle_send_raw, schema=SERVICE_SEND_RAW_SCHEMA
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("async_unload_entry")
    coordinator: BenQProjectorCoordinator = hass.data[DOMAIN][entry.entry_id]
    await coordinator.async_disconnect()

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
