"""Config flow for the BenQ Projector integration."""

from __future__ import annotations

import logging
import os
from typing import Any, Final

import serial
import serial.tools.list_ports
import voluptuous as vol
from benqprojector import (
    BAUD_RATES,
    DEFAULT_PORT,
    BenQProjectorSerial,
    BenQProjectorTelnet,
)
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_TYPE
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_BAUD_RATE,
    CONF_MANUAL_PATH,
    CONF_SERIAL_PORT,
    CONF_TYPE_SERIAL,
    CONF_TYPE_TELNET,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class BenQProjectorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for BenQ Projector."""

    VERSION = 1

    _step_setup_serial_schema = None

    _step_setup_network_schema = vol.Schema(
        {
            vol.Required(CONF_HOST): str,
            vol.Required(CONF_PORT, default=DEFAULT_PORT): NumberSelector(
                NumberSelectorConfig(min=1, max=65535, mode=NumberSelectorMode.BOX)
            ),
        }
    )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        return self.async_show_menu(
            step_id="user",
            menu_options=["setup_serial", "setup_network"],
        )

    async def async_step_setup_serial(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the setup serial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            title, data, options = await self.validate_input_setup_serial(
                user_input, errors
            )

            if not errors:
                return self.async_create_entry(title=title, data=data, options=options)

        ports = await self.hass.async_add_executor_job(serial.tools.list_ports.comports)
        list_of_ports = {}
        for port in ports:
            list_of_ports[port.device] = (
                f"{port}, s/n: {port.serial_number or 'n/a'}"
                + (f" - {port.manufacturer}" if port.manufacturer else "")
            )

        self._step_setup_serial_schema = vol.Schema(
            {
                vol.Required(CONF_SERIAL_PORT, default=""): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            SelectOptionDict(value=k, label=v)
                            for k, v in list_of_ports.items()
                        ],
                        mode=SelectSelectorMode.DROPDOWN,
                        custom_value=True,
                        sort=True,
                    )
                ),
                vol.Required(CONF_BAUD_RATE): vol.In(BAUD_RATES),
            }
        )

        if user_input is not None:
            data_schema = self.add_suggested_values_to_schema(
                self._step_setup_serial_schema, user_input
            )
        else:
            data_schema = self._step_setup_serial_schema

        return self.async_show_form(
            step_id="setup_serial",
            data_schema=data_schema,
            errors=errors,
        )

    async def validate_input_setup_serial(
        self, data: dict[str, Any], errors: dict[str, str]
    ) -> dict[str, Any]:
        """Validate the user input and create data.

        Data has the keys from _step_setup_serial_schema with values provided by the user.
        """
        # Validate the data can be used to set up a connection.
        self._step_setup_serial_schema(data)

        serial_port = data.get(CONF_SERIAL_PORT)

        if serial_port is None:
            raise vol.error.RequiredFieldInvalid("No serial port configured")

        serial_port = await self.hass.async_add_executor_job(
            get_serial_by_id, serial_port
        )

        # Test if the device exists.
        if not os.path.exists(serial_port):
            errors[CONF_SERIAL_PORT] = "nonexisting_serial_port"

        await self.async_set_unique_id(serial_port)
        self._abort_if_unique_id_configured()

        if errors.get(CONF_SERIAL_PORT) is None:
            # Test if we can connect to the device
            try:
                # Get model from the device
                projector = BenQProjectorSerial(serial_port, data[CONF_BAUD_RATE])
                if not await projector.connect():
                    errors["base"] = "cannot_connect"

                model = projector.model

                await projector.disconnect()
                _LOGGER.info("Device %s available", serial_port)
            except serial.SerialException:
                errors["base"] = "cannot_connect"

        # Return title, data and options.
        return (
            f"BenQ {model}",
            {
                CONF_SERIAL_PORT: serial_port,
                CONF_BAUD_RATE: data[CONF_BAUD_RATE],
            },
            None,
        )

    async def async_step_setup_network(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step when setting up network configuration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await self.validate_input_setup_network(user_input, errors)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception as ex:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception: %s", ex)
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=info)
            # data = await self.validate_input_setup_network(user_input, errors)
            # if not errors:
            #     return self.async_create_entry(
            #         title=f"{data[CONF_HOST]}:{data[CONF_PORT]}", data=data
            #     )

        return self.async_show_form(
            step_id="setup_network",
            data_schema=self._step_setup_network_schema,
            errors=errors,
        )

    async def validate_input_setup_network(
        self, data: dict[str, Any], errors: dict[str, str]
    ) -> dict[str, Any]:
        """Validate the user input allows us to connect.

        Data has the keys from _step_setup_network_schema with values provided by the user.
        """
        # Validate the data can be used to set up a network connection.
        self._step_setup_network_schema(data)

        host = data[CONF_HOST]
        port = int(data[CONF_PORT])

        # ToDo Test if the host exists

        await self.async_set_unique_id(f"{host}:{port}")
        self._abort_if_unique_id_configured()

        # Test if we can connect to the device.
        try:
            projector = BenQProjectorTelnet(host, port)
            if not await projector.connect():
                raise CannotConnect(f"Unable to connect to the device on {host}:{port}")

            model = projector.model

            await projector.disconnect()
            _LOGGER.info("Device on %s:%s available", host, port)
        except serial.SerialException as ex:
            raise CannotConnect(
                f"Unable to connect to the device on {host}:{port}"
            ) from ex

        # Return info that you want to store in the config entry.
        return {
            "title": f"BenQ {model} {host}:{port}",
            CONF_TYPE: CONF_TYPE_TELNET,
            CONF_HOST: host,
            CONF_PORT: port,
        }


def get_serial_by_id(dev_path: str) -> str:
    """Return a /dev/serial/by-id match for given device if available."""
    by_id = "/dev/serial/by-id"
    if not os.path.isdir(by_id):
        return dev_path

    for path in (entry.path for entry in os.scandir(by_id) if entry.is_symlink()):
        if os.path.realpath(path) == dev_path:
            return path
    return dev_path


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
