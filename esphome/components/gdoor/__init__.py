# This file is part of the GDoor distribution (https://github.com/gdoor-org).
# Copyright (c) 2024 GDoor authors.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
"""ESPHome external component for the GDoor Gira TKS bus adapter."""
import re

from esphome import automation, pins
import esphome.codegen as cg
from esphome.components import esp32
from esphome.components.esp32.const import VARIANT_ESP32, VARIANT_ESP32S2
import esphome.config_validation as cv
from esphome.const import CONF_ID

CODEOWNERS = ["@gdoor-org"]

gdoor_ns = cg.esphome_ns.namespace("gdoor")
GDoorComponent = gdoor_ns.class_("GDoorComponent", cg.Component)
GDoorMessage = gdoor_ns.struct("GDoorMessage")
GDoorSendAction = gdoor_ns.class_("GDoorSendAction", automation.Action)

CONF_GDOOR_ID = "gdoor_id"
CONF_RX_PIN = "rx_pin"
CONF_TX_PIN = "tx_pin"
CONF_TX_ENABLE_PIN = "tx_enable_pin"
CONF_RX_THRESHOLD_PIN = "rx_threshold_pin"
CONF_RX_SENSITIVITY = "rx_sensitivity"
CONF_LOG_INVALID = "log_invalid"
CONF_ON_MESSAGE = "on_message"
CONF_ON_SENT = "on_sent"
CONF_BUSDATA = "busdata"
CONF_ACTIONS = "actions"
CONF_PARAMETERS = "parameters"
CONF_SOURCE = "source"
CONF_DESTINATION = "destination"

# Bus actions the firmware can decode (see GDOOR_DATA_ACTION in gdoor_data.cpp)
ACTIONS = [
    "BUTTON",
    "BUTTON_LIGHT",
    "DOOR_OPEN",
    "VIDEO_REQUEST",
    "AUDIO_REQUEST",
    "AUDIO_VIDEO_END",
    "BUTTON_FLOOR",
    "CALL_INTERNAL",
    "BUTTON_RING",
    "CTRL_DOOROPENER_ACK",
    "CTRL_RESET",
    "CTRL_DOORSTATION_ACK",
    "CTRL_BUTTONS_TRAINING_START",
    "CTRL_DOOROPENER_TRAINING_START",
    "CTRL_DOOROPENER_TRAINING_STOP",
    "CTRL_PROGRAMMING_START",
    "CTRL_PROGRAMMING_STOP",
    "ACTION_UNKOWN",  # sic, as spelled by the firmware
]

# Pin defaults of the GDoor adapter v3.1 on a Wemos D1 mini ESP32
DEFAULT_RX_PIN = 22
DEFAULT_TX_PIN = 25
DEFAULT_TX_ENABLE_PIN = 27

MAX_BYTES = 24  # MAX_WORDLEN - 1, see defines.h

# DAC pins that can drive the comparator threshold, per chip. The ESP32-S3
# has no DAC; boards with it (e.g. the DIN board) use a fixed threshold.
DAC_PINS = {
    VARIANT_ESP32: (25, 26),
    VARIANT_ESP32S2: (17, 18),
}

# Driver functions the bus ISRs call are put in IRAM, so bus timing keeps
# running while flash is written (OTA, saving preferences). The core checks
# for all of them (GDOOR_ISR_IRAM_SAFE in defines.h).
IRAM_SDKCONFIG_OPTIONS = (
    "CONFIG_GPTIMER_ISR_CACHE_SAFE",
    "CONFIG_GPTIMER_CTRL_FUNC_IN_IRAM",
    "CONFIG_GPIO_CTRL_FUNC_IN_IRAM",
    "CONFIG_LEDC_CTRL_FUNC_IN_IRAM",
)


def hex_string(length=None):
    """Validate a hex string (spaces allowed), optionally of an exact byte length."""

    def validator(value):
        value = cv.string_strict(value)
        cleaned = re.sub(r"\s", "", value).upper()
        if not re.fullmatch(r"[0-9A-F]*", cleaned) or len(cleaned) % 2:
            raise cv.Invalid(f"'{value}' is not an even number of hex digits")
        if length is not None and len(cleaned) != 2 * length:
            raise cv.Invalid(f"'{value}' must be exactly {length} bytes ({2 * length} hex digits)")
        if not cleaned:
            raise cv.Invalid("Bus data must not be empty")
        if len(cleaned) > 2 * MAX_BYTES:
            raise cv.Invalid(f"Bus data can be at most {MAX_BYTES} bytes")
        return cleaned

    return validator


def bus_action(value):
    value = cv.string_strict(value).upper()
    if value not in ACTIONS:
        raise cv.Invalid(f"Unknown bus action '{value}', expected one of {', '.join(ACTIONS)}")
    return value


# Filter keys shared by the event platform
FILTER_SCHEMA = {
    cv.Optional(CONF_ACTIONS): cv.ensure_list(bus_action),
    cv.Optional(CONF_PARAMETERS): hex_string(2),
    cv.Optional(CONF_SOURCE): hex_string(3),
    cv.Optional(CONF_DESTINATION): hex_string(3),
    cv.Optional(CONF_BUSDATA): hex_string(),
}

GDOOR_CHILD_SCHEMA = cv.Schema({cv.GenerateID(CONF_GDOOR_ID): cv.use_id(GDoorComponent)})


def validate_rx_threshold_pin(config):
    if CONF_RX_THRESHOLD_PIN not in config:
        return config
    variant = esp32.get_esp32_variant()
    dac_pins = DAC_PINS.get(variant)
    if dac_pins is None:
        raise cv.Invalid(
            f"The {variant} has no DAC; leave out rx_threshold_pin (the board needs a fixed RX threshold)",
            path=[CONF_RX_THRESHOLD_PIN],
        )
    if config[CONF_RX_THRESHOLD_PIN] not in dac_pins:
        raise cv.Invalid(
            f"rx_threshold_pin must be a DAC pin of the {variant}: {', '.join(f'GPIO{p}' for p in dac_pins)}",
            path=[CONF_RX_THRESHOLD_PIN],
        )
    return config

CONFIG_SCHEMA = cv.All(
    cv.Schema(
        {
            cv.GenerateID(): cv.declare_id(GDoorComponent),
            cv.Optional(CONF_RX_PIN, default=DEFAULT_RX_PIN): pins.internal_gpio_input_pin_number,
            cv.Optional(CONF_TX_PIN, default=DEFAULT_TX_PIN): pins.internal_gpio_output_pin_number,
            cv.Optional(CONF_TX_ENABLE_PIN, default=DEFAULT_TX_ENABLE_PIN): pins.internal_gpio_output_pin_number,
            # Only the v3.1 "adjustable" input on IO22 has a DAC driven comparator threshold (GPIO26)
            cv.Optional(CONF_RX_THRESHOLD_PIN): pins.internal_gpio_output_pin_number,
            cv.Optional(CONF_RX_SENSITIVITY, default=1.45): cv.All(cv.float_, cv.Range(min=0.0, max=3.3)),
            cv.Optional(CONF_LOG_INVALID, default=False): cv.boolean,
            cv.Optional(CONF_ON_MESSAGE): automation.validate_automation({}),
            cv.Optional(CONF_ON_SENT): automation.validate_automation({}),
        }
    ).extend(cv.COMPONENT_SCHEMA),
    # The bus timing uses the ESP-IDF gptimer, LEDC and GPIO drivers (Arduino or ESP-IDF framework)
    cv.only_on_esp32,
    validate_rx_threshold_pin,
)

_CALLBACK_AUTOMATIONS = (
    automation.CallbackAutomation(
        CONF_ON_MESSAGE,
        "add_on_message_callback",
        [(GDoorMessage.operator("const").operator("ref"), "message")],
    ),
    automation.CallbackAutomation(
        CONF_ON_SENT,
        "add_on_sent_callback",
        [(GDoorMessage.operator("const").operator("ref"), "message")],
    ),
)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    cg.add(var.set_rx_pin(config[CONF_RX_PIN]))
    cg.add(var.set_tx_pin(config[CONF_TX_PIN]))
    cg.add(var.set_tx_enable_pin(config[CONF_TX_ENABLE_PIN]))
    if CONF_RX_THRESHOLD_PIN in config:
        cg.add(var.set_rx_threshold_pin(config[CONF_RX_THRESHOLD_PIN]))
        # ESPHome leaves the DAC driver out of the build unless a component asks for it
        esp32.include_builtin_idf_component("esp_driver_dac")
    for option in IRAM_SDKCONFIG_OPTIONS:
        esp32.add_idf_sdkconfig_option(option, True)
    cg.add(var.set_rx_sensitivity(config[CONF_RX_SENSITIVITY]))
    cg.add(var.set_log_invalid(config[CONF_LOG_INVALID]))
    await automation.build_callback_automations(var, config, _CALLBACK_AUTOMATIONS)


@automation.register_action(
    "gdoor.send",
    GDoorSendAction,
    cv.maybe_simple_value(
        {
            cv.GenerateID(): cv.use_id(GDoorComponent),
            cv.Required(CONF_BUSDATA): cv.templatable(hex_string()),
        },
        key=CONF_BUSDATA,
    ),
    synchronous=True,
)
async def gdoor_send_to_code(config, action_id, template_args, args):
    parent = await cg.get_variable(config[CONF_ID])
    var = cg.new_Pvariable(action_id, template_args, parent)
    template_ = await cg.templatable(config[CONF_BUSDATA], args, cg.std_string)
    cg.add(var.set_busdata(template_))
    return var
