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
#include <Arduino.h>
#include "src/gdoor.h"
#include "src/mqtt_helper.h"
#include "src/wifi_helper.h"
#include "src/printer_helper.h"
#include "src/web_console.h"

GDOOR_DATA_PROTOCOL gdoor_data_idle(NULL, true);

boolean debug = false; // Global variable to indicate if we are in debug mode (true)
boolean tx_echo = true; // Publish messages sent to the bus back on the bus_rx topic
const char* mqtt_topic_bus_rx = NULL;
uint32_t bus_rx_count = 0; // Valid messages received from the bus since boot
uint32_t bus_tx_count = 0; // Messages sent to the bus since boot

/**
 * Function which parses user provided serial input
 * for commands and executes logic based on these commands.
 * @param input String with input from user.
 * @return boolean, true if a command was found, false if no valid command was found.
*/
boolean parse(String  &input) {
    if(input == "*debug") {
        debug = true;
        return true;
    } else if(input == "*normal") {
        debug = false;
        return true;
    }
    return false;
}

/**
 * Function which outputs bus data via the serial port and MQTT.
 * Depending in debug mode, it may output more data.
 * 
 * In normal mode, it also checks the valid flag and only
 * outputs valid bus messages.
 * @param busmessage The bus message to be send out to the user.
*/
void output(GDOOR_DATA_PROTOCOL &busmessage, const char* topic, bool force=false) {
    if(force || debug || (busmessage.raw != NULL && busmessage.raw->valid)) {
        MQTT_HELPER::printer.print("{");
        MQTT_HELPER::printer.print(busmessage);
        MQTT_HELPER::printer.println("}");
        MQTT_HELPER::printer.publish((const char*)topic);

        // Bus messages also go to the web console, the idle keepalive would only be noise there
        if(busmessage.raw != NULL) {
            String line(MQTT_HELPER::printer.buffer);
            line.trim();
            WEB_CONSOLE::log(line);
        }
    }
}

void setup() {
    Serial.begin(115200);
    Serial.setTimeout(1);
    JSONDEBUG("GDoor Setup start");
    
    WIFI_HELPER::setup();
    MQTT_HELPER::setup(WIFI_HELPER::mqtt_server(),
                       WIFI_HELPER::mqtt_port(),
                       WIFI_HELPER::mqtt_user(),
                       WIFI_HELPER::mqtt_password(),
                       WIFI_HELPER::mqtt_topic_bus_tx(),
                       WIFI_HELPER::mqtt_topic_bus_rx());

    if(WIFI_HELPER::hardware_v4()) {
        // v4.0: IO25/IO26 are I2S lines to the codec there and must not be driven,
        // fixed RX threshold only (RX input and sensitivity settings do not apply)
        GDOOR::setup(PIN_TX_V4, PIN_TX_EN, PIN_RX_V4);
    } else {
        GDOOR::setRxThreshold(PIN_RX_THRESH, WIFI_HELPER::rx_sensitivity());
        GDOOR::setup(PIN_TX, PIN_TX_EN, WIFI_HELPER::rx_pin());
    }

    mqtt_topic_bus_rx = WIFI_HELPER::mqtt_topic_bus_rx();
    debug = WIFI_HELPER::debug();
    tx_echo = WIFI_HELPER::tx_echo();

    WEB_CONSOLE::set_send_enabled(WIFI_HELPER::console_send());
    WEB_CONSOLE::set_status_provider([]() {
        return MQTT_HELPER::status_json(bus_rx_count, bus_tx_count, WIFI_HELPER::wifi_disconnects());
    });
    WEB_CONSOLE::log("GDoor " GDOOR_VERSION " started");
    if(WIFI_HELPER::hardware_v4()) {
        WEB_CONSOLE::log("Adapter hardware " HW_V4_NAME ": TX IO" + String(PIN_TX_V4) + ", RX IO" + String(PIN_RX_V4));
    } else {
        WEB_CONSOLE::log("Adapter hardware " HW_V3_NAME ": TX IO" + String(PIN_TX) + ", RX IO" + String(WIFI_HELPER::rx_pin()));
    }

    // Firmware updated over the air keeps the old partition table, a USB flash is needed once
    if(MQTT_HELPER::legacy_partition_layout()) {
        JSONPRINT("Old partition layout, please flash once via USB (see firmware README)");
        WEB_CONSOLE::log("WARNING: old partition layout, please flash once via USB (see firmware README)");
    }

    JSONDEBUG("GDoor Setup done");
    JSONDEBUG("RX Pin: ");
    JSONDEBUG(WIFI_HELPER::rx_pin());
    JSONDEBUG("RX Sensitivity: ");
    JSONDEBUG(WIFI_HELPER::rx_sensitivity());
}

void loop() {
    WIFI_HELPER::loop();
    MQTT_HELPER::loop();
    GDOOR::loop();
    GDOOR_DATA* rx_data = GDOOR::read();

    // Output bus idle message on new MQTT connections to set a defined state
    if(MQTT_HELPER::isNewConnection()) {
        output(gdoor_data_idle, mqtt_topic_bus_rx, true);
    }
    if(MQTT_HELPER::statusDue()) {
        MQTT_HELPER::publish_status(bus_rx_count, bus_tx_count, WIFI_HELPER::wifi_disconnects());
    }

    // Report messages we put on the bus, once transmission finished, so that
    // the sender can confirm it went out (origin field distinguishes it from received data)
    GDOOR_DATA* tx_data = GDOOR::sent();
    if(tx_data != NULL) {
        bus_tx_count++;
        if(tx_echo) {
            GDOOR_DATA_PROTOCOL sentmessage = GDOOR_DATA_PROTOCOL(tx_data);
            sentmessage.origin = "GDOOR_TX";
            output(sentmessage, mqtt_topic_bus_rx);
            output(gdoor_data_idle, mqtt_topic_bus_rx, true);
        }
    }

    if(rx_data != NULL) {
        JSONDEBUG("Received data from bus");
        GDOOR_DATA_PROTOCOL busmessage = GDOOR_DATA_PROTOCOL(rx_data);
        if(rx_data->valid) {
            bus_rx_count++;
        }
        output(busmessage, mqtt_topic_bus_rx);
        JSONDEBUG("Output bus data via Serial and MQTT, done");
        // Output idle message after bus message, to reset values so that
        //home automation can trigger again
        output(gdoor_data_idle, mqtt_topic_bus_rx, true);

    } else if (!GDOOR::active()) { // Neither RX nor TX active,
        String str_received("");
        if (Serial.available() > 0) { // let's check the serial port if something is in buffer
            str_received = Serial.readString();
        } else {
            str_received = MQTT_HELPER::receive();
            if (str_received.length() == 0) {
                str_received = WEB_CONSOLE::receive();
            }
        }
        str_received.trim();    

        if(str_received.length() > 0) {
            if(!parse(str_received)) { //Check if received string is a command
                GDOOR::send(str_received.c_str()); // Send to bus if it is not a command
                JSONDEBUG("Send: ");
                JSONDEBUG(str_received);
            }
        }
        
    }
}
