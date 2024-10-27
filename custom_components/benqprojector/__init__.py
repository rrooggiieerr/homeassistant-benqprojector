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
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_HOST,
    CONF_PORT,
    CONF_TYPE,
    Platform,
)
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import entity_registry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_BAUD_RATE,
    CONF_DEFAULT_INTERVAL,
    CONF_INTERVAL,
    CONF_MODEL,
    CONF_SERIAL_PORT,
    CONF_TYPE_SERIAL,
    CONF_TYPE_TELNET,
    DOMAIN,
)

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

    def __init__(self, hass, projector: BenQProjector):
        """Initialize BenQ Projector Data Update Coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name=__name__,
        )

        self.projector = projector
        self.projector.add_listener(self._listener)

        self.unique_id = self.projector.unique_id
        model = self.projector.model
        if model is not None:
            model = model.upper()

        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, self.unique_id)},
            name=f"BenQ {model}",
            model=model,
            manufacturer="BenQ",
        )

    @property
    def power_status(self):
        return self.projector.power_status

    @property
    def volume(self):
        return self.projector.volume

    @property
    def muted(self):
        return self.projector.muted

    @property
    def video_source(self):
        return self.projector.video_source

    @property
    def video_sources(self):
        return self.projector.video_sources

    @callback
    def _listener(self, command: str, data):
        self.async_set_updated_data({command: data})

    # async def async_connect(self):
    #     try:
    #         if not await self.projector.connect():
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
    #     model = self.projector.model.upper()
    #
    #     self.device_info = DeviceInfo(
    #         identifiers={(DOMAIN, self.unique_id)},
    #         name=f"BenQ {model}",
    #         model=model,
    #         manufacturer="BenQ",
    #     )

    async def async_disconnect(self):
        await self.projector.disconnect()
        _LOGGER.debug(
            "Disconnected from BenQ projector on %s", self.projector.connection
        )

    @callback
    def async_add_listener(
        self, update_callback: CALLBACK_TYPE, context: Any = None
    ) -> Callable[[], None]:
        self.projector.add_listener(command=context)

        return super().async_add_listener(update_callback, context)

    def supports_command(self, command: str):
        return self.projector.supports_command(command)

    async def async_send_command(self, command: str, action: str | None = None):
        if action:
            return await self.projector.send_command(command, action)
        return await self.projector.send_command(command)

    async def async_send_raw_command(self, command: str):
        return await self.projector.send_raw_command(command)

    async def async_turn_on(self) -> bool:
        return await self.projector.turn_on()

    async def async_turn_off(self) -> bool:
        return await self.projector.turn_off()

    async def async_mute(self) -> bool:
        return await self.projector.mute()

    async def async_unmute(self) -> bool:
        return await self.projector.unmute()

    async def async_volume_level(self, volume: int):
        return await self.projector.volume_level(volume)

    async def async_volume_up(self):
        return await self.projector.volume_up()

    async def async_volume_down(self):
        return await self.projector.volume_down()

    async def async_select_video_source(self, source: str):
        return await self.projector.select_video_source(source)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up BenQ Projector from a config entry."""
    projector = None

    model = entry.data.get(CONF_MODEL)
    conf_type = entry.data.get(CONF_TYPE, CONF_TYPE_SERIAL)
    interval = entry.options.get(CONF_INTERVAL, CONF_DEFAULT_INTERVAL)

    if conf_type == CONF_TYPE_TELNET:
        host = entry.data[CONF_HOST]
        port = entry.data[CONF_PORT]

        projector = BenQProjectorTelnet(host, port, model)
    else:
        serial_port = entry.data[CONF_SERIAL_PORT]
        baud_rate = entry.data[CONF_BAUD_RATE]

        projector = BenQProjectorSerial(serial_port, baud_rate, model)

    @callback
    def _async_migrate_entity_entry(
        registry_entry: entity_registry.RegistryEntry,
    ) -> dict[str, Any] | None:
        """
        Migrates old unique ID to the new unique ID.
        """
        if registry_entry.entity_id.startswith(
            "media_player."
        ) and registry_entry.unique_id.endswith("-mediaplayer"):
            _LOGGER.debug("Migrating media_player entity unique id")
            return {"new_unique_id": f"{registry_entry.config_entry_id}-projector"}

        if registry_entry.unique_id.startswith(f"{projector.unique_id}-"):
            new_unique_id = registry_entry.unique_id.replace(
                f"{projector.unique_id}-", f"{registry_entry.config_entry_id}-"
            )
            _LOGGER.debug("Migrating entity unique id")
            return {"new_unique_id": new_unique_id}

        # No migration needed
        return None

    await entity_registry.async_migrate_entries(
        hass, entry.entry_id, _async_migrate_entity_entry
    )

    # Test if we can connect to the device.
    try:
        # Open the connection.
        if not await projector.connect(interval=interval):
            raise ConfigEntryNotReady(
                f"Unable to connect to device {projector.unique_id}"
            )

        _LOGGER.info("Device %s is available", projector.unique_id)
    except serial.SerialException as ex:
        raise ConfigEntryNotReady(
            f"Unable to connect to device {projector.unique_id}"
        ) from ex

    coordinator = BenQProjectorCoordinator(hass, projector)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(update_listener))

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


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    hass.config_entries.async_schedule_reload(entry.entry_id)
