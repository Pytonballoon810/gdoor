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
"""Event entity that fires on (filtered) bus messages, e.g. a doorbell button."""
import esphome.codegen as cg
from esphome.components import event
import esphome.config_validation as cv

from . import (
    ACTIONS,
    CONF_ACTIONS,
    CONF_BUSDATA,
    CONF_DESTINATION,
    CONF_GDOOR_ID,
    CONF_PARAMETERS,
    CONF_SOURCE,
    FILTER_SCHEMA,
    GDOOR_CHILD_SCHEMA,
    gdoor_ns,
)

DEPENDENCIES = ["gdoor"]

GDoorEvent = gdoor_ns.class_("GDoorEvent", event.Event, cg.Component)

CONFIG_SCHEMA = (
    event.event_schema(GDoorEvent)
    .extend(GDOOR_CHILD_SCHEMA)
    .extend(FILTER_SCHEMA)
    .extend(cv.COMPONENT_SCHEMA)
)


async def to_code(config):
    # The event types are the bus actions the filter lets through, e.g. ["BUTTON_RING"]
    event_types = config.get(CONF_ACTIONS, ACTIONS)
    var = await event.new_event(config, event_types=event_types)
    await cg.register_component(var, config)

    parent = await cg.get_variable(config[CONF_GDOOR_ID])
    cg.add(var.set_parent(parent))

    for action in config.get(CONF_ACTIONS, []):
        cg.add(var.add_filter_action(action))
    if CONF_PARAMETERS in config:
        cg.add(var.set_filter_parameters(config[CONF_PARAMETERS]))
    if CONF_SOURCE in config:
        cg.add(var.set_filter_source(config[CONF_SOURCE]))
    if CONF_DESTINATION in config:
        cg.add(var.set_filter_destination(config[CONF_DESTINATION]))
    if CONF_BUSDATA in config:
        cg.add(var.set_filter_busdata(config[CONF_BUSDATA]))
