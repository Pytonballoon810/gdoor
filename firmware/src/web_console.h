/*
 * This file is part of the GDoor distribution (https://github.com/gdoor-org).
 * Copyright (c) 2024 GDoor authors.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, version 3.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program. If not, see <http://www.gnu.org/licenses/>.
 */
#ifndef WEB_CONSOLE_H
#define WEB_CONSOLE_H
#include <Arduino.h>
#include <WebServer.h>
#include <functional>

#define WEB_CONSOLE_LINES 60 // Log lines kept in RAM for the console
#define APP_PARTITION_MIN_SIZE 0x1E0000 // App slot size of min_spiffs.csv, smaller means the old layout

/**
 * High level log and bus console in the web interface (/console).
 * Shows bus messages and network events as they happen, the status JSON,
 * and (if enabled in the config) allows sending a message to the bus.
 * It keeps the last WEB_CONSOLE_LINES lines in RAM only, nothing is written to flash.
 */
namespace WEB_CONSOLE { //Namespace as we can only use it once
    void register_routes(WebServer *server);
    void set_status_provider(std::function<String()> provider);
    void set_send_enabled(bool enabled);
    void log(const String &line);
    String json_escape(const String &in);
    String& receive();
};

#endif
