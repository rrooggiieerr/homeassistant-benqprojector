"""Config flow for the BenQ Projector integration."""

import logging
import os
from pathlib import Path
from typing import Any

import serial
import serial.tools.list_ports
import voluptuous as vol
from benqprojector import (
    BAUD_RATES,
    DEFAULT_PORT,
    BenQProjectorSerial,
    BenQProjectorTelnet,
)
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_PORT, UnitOfTime
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    SerialPortSelector,
    TextSelector,
)

from .const import (
    CONF_BAUD_RATE,
    CONF_DEFAULT_INTERVAL,
    CONF_INTERVAL,
    CONF_MODEL,
    CONF_SERIAL_PORT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SERIAL_PORT, default=""): SerialPortSelector(),
        vol.Required(CONF_BAUD_RATE): vol.In(BAUD_RATES),
    }
)


class BenQProjectorConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for BenQ Projector."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate user input.
            USER_SCHEMA(user_input)

            serial_port = user_input[CONF_SERIAL_PORT]
            baud_rate = user_input[CONF_BAUD_RATE]

            model = None
            unique_id = None

            # Test if we can connect to the device
            try:
                projector = BenQProjectorSerial(serial_port, baud_rate)
                if not await projector.connect():
                    errors["base"] = "cannot_connect"
                else:
                    _LOGGER.info("Device %s available", serial_port)

                    # Get model from the device
                    model = projector.model

                    if (
                        model is None
                        and projector.power_status != projector.POWERSTATUS_ON
                    ):
                        errors["base"] = "cannot_detect_model_when_off"

                    unique_id = projector.unique_id
                await projector.disconnect()
            except serial.SerialException:
                errors["base"] = "cannot_connect"

            if not errors:
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                title = f"BenQ {model}"
                data = {
                    CONF_MODEL: model,
                    CONF_SERIAL_PORT: serial_port,
                    CONF_BAUD_RATE: baud_rate,
                }
                return self.async_create_entry(title=title, data=data)

        # Combine user input with schema.
        data_schema = self.add_suggested_values_to_schema(USER_SCHEMA, user_input or {})

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> OptionsFlow:
        """Create the options flow."""
        return BenQProjectorOptionsFlowHandler()


class BenQProjectorOptionsFlowHandler(OptionsFlow):
    _OPTIONS_SCHEMA = vol.Schema(
        {
            vol.Optional(CONF_INTERVAL, default=CONF_DEFAULT_INTERVAL): NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement=UnitOfTime.SECONDS,
                )
            ),
        }
    )

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._OPTIONS_SCHEMA(user_input)
            return self.async_create_entry(title="", data=user_input)

        data_schema = self.add_suggested_values_to_schema(
            self._OPTIONS_SCHEMA, user_input or self.config_entry.options
        )

        return self.async_show_form(
            step_id="init", data_schema=data_schema, errors=errors
        )
