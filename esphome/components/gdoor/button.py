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
"""Button that sends a fixed bus message, e.g. to open the door."""
import esphome.codegen as cg
from esphome.components import button
import esphome.config_validation as cv

from . import CONF_BUSDATA, CONF_GDOOR_ID, GDOOR_CHILD_SCHEMA, gdoor_ns, hex_string

DEPENDENCIES = ["gdoor"]

GDoorButton = gdoor_ns.class_("GDoorButton", button.Button, cg.Component)

CONFIG_SCHEMA = (
    button.button_schema(GDoorButton)
    .extend(GDOOR_CHILD_SCHEMA)
    .extend({cv.Required(CONF_BUSDATA): hex_string()})
    .extend(cv.COMPONENT_SCHEMA)
)


async def to_code(config):
    var = await button.new_button(config)
    await cg.register_component(var, config)
    parent = await cg.get_variable(config[CONF_GDOOR_ID])
    cg.add(var.set_parent(parent))
    cg.add(var.set_busdata(config[CONF_BUSDATA]))
