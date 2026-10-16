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
"""Text sensor showing the last received bus message."""
import esphome.codegen as cg
from esphome.components import text_sensor
import esphome.config_validation as cv
from esphome.const import CONF_TYPE

from . import CONF_GDOOR_ID, GDOOR_CHILD_SCHEMA, gdoor_ns

DEPENDENCIES = ["gdoor"]

GDoorTextSensor = gdoor_ns.class_("GDoorTextSensor", text_sensor.TextSensor, cg.Component)
GDoorTextSensorType = gdoor_ns.enum("GDoorTextSensorType")

TYPES = {
    "action": GDoorTextSensorType.GDOOR_TEXT_ACTION,
    "busdata": GDoorTextSensorType.GDOOR_TEXT_BUSDATA,
    "json": GDoorTextSensorType.GDOOR_TEXT_JSON,
}

CONFIG_SCHEMA = (
    text_sensor.text_sensor_schema(GDoorTextSensor, icon="mdi:door")
    .extend(GDOOR_CHILD_SCHEMA)
    .extend({cv.Optional(CONF_TYPE, default="action"): cv.enum(TYPES, lower=True)})
    .extend(cv.COMPONENT_SCHEMA)
)


async def to_code(config):
    var = await text_sensor.new_text_sensor(config)
    await cg.register_component(var, config)
    parent = await cg.get_variable(config[CONF_GDOOR_ID])
    cg.add(var.set_parent(parent))
    cg.add(var.set_type(config[CONF_TYPE]))
