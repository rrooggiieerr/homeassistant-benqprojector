"""The BenQ Projector integration."""

import logging
from collections.abc import Callable
from typing import Any

import homeassistant.helpers.config_validation as cv
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
from homeassistant.core import (
    CALLBACK_TYPE,
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import ConfigEntryNotReady, ServiceValidationError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_BAUD_RATE,
    CONF_DEFAULT_INTERVAL,
    CONF_INTERVAL,
    CONF_MODEL,
    CONF_SERIAL_PORT,
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

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

CONF_SERVICE_COMMAND = "command"
CONF_SERVICE_ACTION = "action"

SERVICE_SEND_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DEVICE_ID): cv.string,
        vol.Required(CONF_SERVICE_COMMAND): cv.string,
        vol.Optional(CONF_SERVICE_ACTION): cv.string,
    }
)
SERVICE_SEND_RAW_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DEVICE_ID): cv.string,
        vol.Required(CONF_SERVICE_COMMAND): cv.string,
    }
)

type BenQProjectorConfigEntry = ConfigEntry[BenQProjectorCoordinator]


class BenQProjectorCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """
    BenQ Projector Data Update Coordinator.

    The library polls the projector itself and pushes every changed value. The coordinator
    keeps the latest value of every command so entities that are added or re-added later
    still see the current state (it used to keep only the last pushed value).
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        projector: BenQProjector,
    ) -> None:
        """Initialize BenQ Projector Data Update Coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            # Name of the data. For logging purposes.
            name=entry.title,
        )

        self.projector = projector
        self.data = {}

        # Use the unique ID of the config entry for the device. The projector reports its
        # MAC address only when the macaddr command succeeds, otherwise the library falls
        # back to host:port, which created a second device.
        self.unique_id = entry.unique_id or projector.unique_id
        self.model = projector.model or entry.data.get(CONF_MODEL)

        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, self.unique_id)},
            name=entry.title,
            model=self.model,
            manufacturer="BenQ",
        )

        self.projector.add_listener(self._listener)

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
        return self.projector.video_sources or []

    @property
    def is_on(self) -> bool:
        return self.projector.power_status in (
            BenQProjector.POWERSTATUS_POWERINGON,
            BenQProjector.POWERSTATUS_ON,
        )

    @callback
    def _listener(self, command: str, data):
        self.async_set_updated_data({**(self.data or {}), command: data})

    async def _async_update_data(self) -> dict[str, Any]:
        """The library pushes updates, there is nothing to fetch."""
        return self.data or {}

    async def async_disconnect(self):
        await self.projector.disconnect()
        _LOGGER.debug(
            "Disconnected from BenQ projector on %s", self.projector.connection
        )

    @callback
    def async_add_listener(
        self, update_callback: CALLBACK_TYPE, context: Any = None
    ) -> Callable[[], None]:
        # The context is the command an entity needs, the library starts polling it.
        if context is not None:
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


def _coordinator_for_device(
    hass: HomeAssistant, device_id: str
) -> BenQProjectorCoordinator:
    """Return the coordinator of the projector a service call targets."""
    device = dr.async_get(hass).async_get(device_id)
    if device is not None:
        for entry_id in device.config_entries:
            entry = hass.config_entries.async_get_entry(entry_id)
            if (
                entry is not None
                and entry.domain == DOMAIN
                and isinstance(
                    getattr(entry, "runtime_data", None), BenQProjectorCoordinator
                )
            ):
                return entry.runtime_data

    raise ServiceValidationError(f"{device_id} is not a loaded BenQ projector")


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the services once, they route to the projector given by device_id."""

    async def async_handle_send(call: ServiceCall) -> ServiceResponse:
        """Handle the send service call."""
        coordinator = _coordinator_for_device(hass, call.data[CONF_DEVICE_ID])
        command: str = call.data[CONF_SERVICE_COMMAND]
        action: str = call.data.get(CONF_SERVICE_ACTION) or "?"

        response = await coordinator.projector.send_command(command, action, False)

        return {"response": response}

    async def async_handle_send_raw(call: ServiceCall) -> ServiceResponse:
        """Handle the send_raw service call."""
        coordinator = _coordinator_for_device(hass, call.data[CONF_DEVICE_ID])
        command: str = call.data[CONF_SERVICE_COMMAND]

        response = await coordinator.async_send_raw_command(command)

        return {"response": response}

    hass.services.async_register(
        DOMAIN,
        "send",
        async_handle_send,
        schema=SERVICE_SEND_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )

    hass.services.async_register(
        DOMAIN,
        "send_raw",
        async_handle_send_raw,
        schema=SERVICE_SEND_RAW_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )

    return True


async def async_setup_entry(
    hass: HomeAssistant, entry: BenQProjectorConfigEntry
) -> bool:
    """Set up BenQ Projector from a config entry."""
    model = entry.data.get(CONF_MODEL)
    conf_type = entry.data.get(CONF_TYPE)
    # An interval of 0 used to be accepted by the options flow but makes the library fail.
    interval = max(entry.options.get(CONF_INTERVAL, CONF_DEFAULT_INTERVAL) or 0, 1)

    if conf_type == CONF_TYPE_TELNET:
        # BenQProjectorTelnet detects if the connection has a prompt: serial to network
        # bridges do, projectors with a native network interface do not.
        # BenQProjectorSerial always expects a prompt.
        projector = BenQProjectorTelnet(
            entry.data[CONF_HOST], entry.data[CONF_PORT], model
        )
    else:
        projector = BenQProjectorSerial(
            entry.data[CONF_SERIAL_PORT], entry.data[CONF_BAUD_RATE], model
        )

    @callback
    def _async_migrate_entity_entry(
        registry_entry: er.RegistryEntry,
    ) -> dict[str, Any] | None:
        """Migrates old unique ID to the new unique ID."""
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

    await er.async_migrate_entries(hass, entry.entry_id, _async_migrate_entity_entry)

    # Open the connection. Any failure means "try again later": HA retries the setup with
    # a back off. An AssertionError used to escape here, which made HA give up for good.
    try:
        connected = await projector.connect(interval=interval)
    except Exception as ex:  # pylint: disable=broad-exception-caught
        await projector.disconnect()
        raise ConfigEntryNotReady(
            f"Unable to connect to BenQ projector on {projector.connection}: {ex}"
        ) from ex
    if not connected:
        await projector.disconnect()
        raise ConfigEntryNotReady(
            f"Unable to connect to BenQ projector on {projector.connection}"
        )

    _LOGGER.info("Device %s is available", projector.unique_id)

    coordinator = BenQProjectorCoordinator(hass, entry, projector)
    entry.runtime_data = coordinator

    # Make sure the read task is stopped whatever happens to the entry from here on.
    entry.async_on_unload(coordinator.async_disconnect)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    try:
        _async_remove_stale_devices(hass, entry, coordinator.unique_id)
    except Exception:  # pylint: disable=broad-exception-caught
        # Housekeeping only, never fail the setup over it.
        _LOGGER.exception("Failed to clean up duplicate devices")

    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True


@callback
def _async_remove_stale_devices(
    hass: HomeAssistant, entry: ConfigEntry, unique_id: str
) -> None:
    """
    The device used to be named after the connection (host:port or serial port) whenever
    the MAC address could not be read, which created a second device for the same
    projector. Move every entity of this entry
    to the current device, then remove the others. Entities are moved first because
    removing a device also removes the entity registry entries attached to it.
    """
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)

    devices = dr.async_entries_for_config_entry(device_registry, entry.entry_id)
    device = next((d for d in devices if (DOMAIN, unique_id) in d.identifiers), None)
    if device is None:
        return

    for stale in devices:
        if stale.id == device.id:
            continue
        for entity in er.async_entries_for_device(
            entity_registry, stale.id, include_disabled_entities=True
        ):
            if entity.config_entry_id == entry.entry_id:
                entity_registry.async_update_entity(
                    entity.entity_id, device_id=device.id
                )
        _LOGGER.info("Removing duplicate device %s", stale.identifiers)
        device_registry.async_remove_device(stale.id)


async def async_unload_entry(
    hass: HomeAssistant, entry: BenQProjectorConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    hass.config_entries.async_schedule_reload(entry.entry_id)
