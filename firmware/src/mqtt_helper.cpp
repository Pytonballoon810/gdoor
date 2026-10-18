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
#include "defines.h"
#include "mqtt_helper.h"
#include "printer_helper.h"
#include "gdoor_data.h"
#include "wifi_helper.h"
#include "web_console.h"
#include <MQTT.h>
#include <esp_ota_ops.h>

#include <WiFi.h>
/** 
 * Constructor for MQTT_RINTER.
 * @param mqttClient the parent mqttClient, used to publish data
*/
MQTT_PRINTER::MQTT_PRINTER(MQTTClient *mqttClient) {
    this->mqttClient = mqttClient;
}

/**
 * Sends out the collected data via Serial and MQTT (if available).
 * @param topic The MQTT topic to which the collected data is send.
*/
void MQTT_PRINTER::publish(const char *topic) {
    JSONDEBUG("MQTT_PRINTER publish()");
    if (this->mqttClient->connected()) {
        this->mqttClient->publish(topic, this->read());
    }
    PRINT(this->read());
}

/**
 * Arduino IDE specific write function ti implement prints().
 * @param byte: Byte to write
 * @return Number of bytes written
*/
size_t MQTT_PRINTER::write(uint8_t byte) {
    if(index < BUFFER_SIZE) {
        this->buffer[index] = (char) byte;
        index = index + 1;
        return 1;
    } else {
        JSONDEBUG("!!WARNING MQTT_PRINTER OUTPUT OVERFLOW, LOOSING DATA!!");
    }
    return 0;
}

/** Function which returns collected data.
 * @return string of collected data
*/
char* MQTT_PRINTER::read() {
    JSONDEBUG("MQTT_PRINTER read()");
    if(this->index < BUFFER_SIZE && this->index > 0) {
        this->buffer[index] = '\0'; //just to be sure
    }
    this->index = 0;
    return this->buffer;
}

namespace MQTT_HELPER { //Namespace as we can only use it once
    WiFiClient net; // Arduinio helper object, needed by MQTTClient
    MQTTClient mqttClient; // MQTT Library object

    const char* rx_topic_name; // Which callback topic
    const char* tx_topic_name; // For HA discovery message
    const char* user; // Username
    const char* password; // Password

    MQTT_PRINTER printer(&mqttClient); // Printer, so that code can use the Arduino print functions

    String received_mqtt_payload; // Global variable which stores received MQTT payload
    String empty(""); //Empty string, useful as global and fixed allocated value.
    String availability_topic; //Topic where availabiliy is shown
    String status_topic; //Topic where the periodic status JSON is published
    String client_id; //MQTT client id, unique per adapter so that two adapters do not kick each other off the broker
    uint32_t mqtt_connects = 0; //Number of successful MQTT connections since boot
    uint32_t last_status = 0; //millis() of last availability/status publish
    bool status_requested = false; //Publish status as soon as possible (e.g. after connect)

    bool new_string_available = false; // Global variable to indicate that a new MQTT String was received

    bool newly_connected = true; // Global variable to indicate a newly established WIFI connection
    bool new_connection_established = false; //Global variable to indicate we successfully connected new
    bool ha_online = false; // Indicates if Home assistant messaged a new online state, so that we can resend our state

    /**
     * Function which sends home assistant discovery message,
     * e.g.
     * {
     *  "name": "Bus Data",
     *  "force_update": True,
     *  "icon": "mdi:door",
     *  "state_topic": "gdoor/rx",
     *  "command_topic": "gdoor/tx",
     *  "json_attributes_topic": "gdoor/rx",
     *  "value_template": "{{ value_json.action }}",
     *  "uniq_id": "gdoor_data_mac",
     *  "device": {
     *      "sw_version": "3.0",
     *      "name": "GDoor Adapter",
     *      "model": "ESP32 (de:ad:be:ef)",
     *      "manufacturer": "GDoor Project",
     *      "configuration_url": "http://127.0.0.1",
     *      "ids": "gdoor_mac",
     *      "availability_topic": "homeassistant/sensor/gdoor/data/config/mac"
     *  }
     * }
    */
    /**
     * Sends a home assistant discovery message for one diagnostic sensor,
     * read from the periodic status JSON (see publish_status()).
     * Optional fields are left out when NULL.
    */
    void send_ha_diagnostic(const char* key, const char* name, const char* value_template,
                            const char* unit, const char* device_class, const char* state_class, const char* icon) {
        String mac = WiFi.macAddress();
        String mac_clean = mac;
        mac_clean.replace(":", "_");

        String message = "{";
        message += "\"name\": \"" + String(name) + "\",";
        message += "\"uniq_id\": \"gdoor_" + String(key) + "_" + mac_clean + "\",";
        message += "\"state_topic\": \"" + status_topic + "\",";
        message += "\"value_template\": \"" + String(value_template) + "\",";
        message += "\"availability_topic\": \"" + availability_topic + "\",";
        message += "\"entity_category\": \"diagnostic\",";
        if (unit != NULL) {
            message += "\"unit_of_measurement\": \"" + String(unit) + "\",";
        }
        if (device_class != NULL) {
            message += "\"device_class\": \"" + String(device_class) + "\",";
        }
        if (state_class != NULL) {
            message += "\"state_class\": \"" + String(state_class) + "\",";
        }
        if (icon != NULL) {
            message += "\"icon\": \"" + String(icon) + "\",";
        }
        message += "\"device\": {\"ids\": \"gdoor_" + mac_clean + "\"}";
        message += "}";

        String topic = "homeassistant/sensor/gdoor_" + mac_clean + "/" + String(key) + "/config";
        mqttClient.publish(topic, message, true, 1);
    }

    void send_ha_discovery(){
        String mac = WiFi.macAddress();
        String mac_clean = mac;
        mac_clean.replace(":", "_");

        availability_topic = "homeassistant/sensor/gdoor/data/config/"+mac_clean;

        String ip;
        ip = WIFI_HELPER::local_ip().toString();

        String message = 
R"""(
{
"name": "Bus Data",
"force_update": true,
"icon": "mdi:door",
"value_template": "{{ value_json.action }}",
"device": {
"name": "GDoor Adapter",
"manufacturer": "GDoor Project",
)"""
"";
        
        message += "\"sw_version\": \"" + String(GDOOR_VERSION) + "\",";
        message += "\"model\": \"ESP32 (" + mac + ")\",";
        message += "\"configuration_url\": \"http://" + ip + "\",";
        message += "\"ids\": \"gdoor_" + mac_clean + "\"";
        message += "},";
        message += "\"availability_topic\": \"" + availability_topic + "\",";
        message += "\"uniq_id\": \"gdoor_data_" + mac_clean + "\",";
        message += "\"state_topic\": \"" + String(tx_topic_name) + "\",";
        message += "\"json_attributes_topic\": \"" + String(tx_topic_name) + "\",";
        message += "\"command_topic\": \"" + String(rx_topic_name) + "\"";
        message += "}";
        mqttClient.publish("homeassistant/sensor/gdoor/data/config", message, true, 1);

        send_ha_diagnostic("rssi", "WiFi Signal", "{{ value_json.rssi }}", "dBm", "signal_strength", "measurement", NULL);
        send_ha_diagnostic("uptime", "Uptime", "{{ value_json.uptime }}", "s", "duration", "total_increasing", NULL);
        send_ha_diagnostic("ip", "IP Address", "{{ value_json.ip }}", NULL, NULL, NULL, "mdi:ip-network");
        send_ha_diagnostic("wifi_disconnects", "WiFi Disconnects", "{{ value_json.wifi_disconnects }}", NULL, NULL, "total_increasing", "mdi:wifi-off");
        send_ha_diagnostic("bus_rx_count", "Bus Messages Received", "{{ value_json.bus_rx_count }}", NULL, NULL, "total_increasing", "mdi:download");
        send_ha_diagnostic("bus_tx_count", "Bus Messages Sent", "{{ value_json.bus_tx_count }}", NULL, NULL, "total_increasing", "mdi:upload");
    }

    void setWill() {
        String mac = WiFi.macAddress();
        String mac_clean = mac;
        mac_clean.replace(":", "_");

        availability_topic = "homeassistant/sensor/gdoor/data/config/"+mac_clean;
        mqttClient.setWill(availability_topic.c_str(), "offline");
    }
   

    /**
     * MQTT Callback function,
     * executes when a new String is received via the subscribed topic
    */
    void on_message_received(String &topic, String &payload) {
        if(topic == "homeassistant/status") {
            if(payload == "online") {
                ha_online = true;
            }
            return; // HA status is not meant for the bus
        }
        new_string_available = true;
        received_mqtt_payload = payload;
        received_mqtt_payload.trim();
    }

    /**
     * Internal WiFi Event callback,
     * used to detect if a new Wifi connection was established
    */
    void on_wifi_active(WiFiEvent_t event, WiFiEventInfo_t info) {
        newly_connected = true;
    }

    /**
     * Setup MQTT.
     * @param server MQTT Broker ip/hostname
     * @param port MQTT Broker TCP port
     * @param username MQTT Broker username
     * @param pw MQTT Broker password
     * @param rx_topic Topic from which data is received
     * @param tx_topic Topic from which is announced in HA discovery as bus outgoing topic
    */
    void setup(const char* server, int port, const char* username, const char* pw, const char* rx_topic, const char* tx_topic) {
        WiFi.onEvent(on_wifi_active, WiFiEvent_t::ARDUINO_EVENT_WIFI_STA_GOT_IP);
        WiFi.onEvent(on_wifi_active, WiFiEvent_t::ARDUINO_EVENT_ETH_GOT_IP);
        
        mqttClient.begin(server, port, net);
        mqttClient.onMessage(on_message_received);
        rx_topic_name = rx_topic;
        tx_topic_name = tx_topic;
        user = username;
        password = pw;

        String mac_clean = WiFi.macAddress();
        mac_clean.replace(":", "");
        client_id = "GDoor-" + mac_clean;
        status_topic = String(tx_topic) + "/status";
    }

    /** Returns true when the periodic status should be published (see publish_status()) */
    bool statusDue() {
        if (!mqttClient.connected()) {
            return false;
        }
        return status_requested || (millis() - last_status >= STATUS_INTERVAL_MS);
    }

    /** Returns true if the firmware runs from the old, smaller app partition (needs a USB flash to migrate) */
    bool legacy_partition_layout() {
        const esp_partition_t *running = esp_ota_get_running_partition();
        return running != NULL && running->size < APP_PARTITION_MIN_SIZE;
    }

    /**
     * Builds the status JSON, e.g.
     * {"version": "v3.2", "ip": "192.168.1.20", "network": "wifi", "ssid": "MyWifi", "bssid": "..",
     *  "rssi": -61, "uptime": 3600, "free_heap": 210000, "reset_reason": 1, "wifi_disconnects": 0,
     *  "mqtt_connected": true, "mqtt_connects": 1, "legacy_partitions": false,
     *  "bus_rx_count": 12, "bus_tx_count": 2}
     * @param bus_rx_count Number of valid messages received from the bus since boot
     * @param bus_tx_count Number of messages sent to the bus since boot
     * @param wifi_disconnects Number of WiFi disconnects since boot
    */
    String status_json(uint32_t bus_rx_count, uint32_t bus_tx_count, uint32_t wifi_disconnects) {
        String message = "{";
        message += "\"version\": \"" + String(GDOOR_VERSION) + "\", ";
        message += "\"ip\": \"" + WIFI_HELPER::local_ip().toString() + "\", ";
        message += "\"network\": \"" + String(WIFI_HELPER::network_type()) + "\", ";
        message += "\"ssid\": \"" + WEB_CONSOLE::json_escape(WiFi.SSID()) + "\", ";
        message += "\"bssid\": \"" + WiFi.BSSIDstr() + "\", ";
        message += "\"rssi\": " + String(WiFi.RSSI()) + ", ";
        message += "\"uptime\": " + String((uint32_t)(millis() / 1000)) + ", ";
        message += "\"free_heap\": " + String(ESP.getFreeHeap()) + ", ";
        message += "\"reset_reason\": " + String((int)esp_reset_reason()) + ", ";
        message += "\"wifi_disconnects\": " + String(wifi_disconnects) + ", ";
        message += "\"mqtt_connected\": " + String(mqttClient.connected() ? "true" : "false") + ", ";
        message += "\"mqtt_connects\": " + String(mqtt_connects) + ", ";
        message += "\"legacy_partitions\": " + String(legacy_partition_layout() ? "true" : "false") + ", ";
        message += "\"bus_rx_count\": " + String(bus_rx_count) + ", ";
        message += "\"bus_tx_count\": " + String(bus_tx_count);
        message += "}";
        return message;
    }

    /**
     * Publishes availability and the status JSON (see status_json()).
    */
    void publish_status(uint32_t bus_rx_count, uint32_t bus_tx_count, uint32_t wifi_disconnects) {
        last_status = millis();
        status_requested = false;

        mqttClient.publish(availability_topic, "online");
        mqttClient.publish(status_topic, status_json(bus_rx_count, bus_tx_count, wifi_disconnects));
    }

    /**
     * MQTT loop function,
     * needs to be executed in main loop().
    */
    void loop() {
        static uint32_t last_attempt = 0;
        static bool attempted = false;
        // WiFi (also while the config portal is open) or Ethernet. A newly connected interface
        // reconnects MQTT, so the connection moves to Ethernet once it becomes the default route.
        if(WIFI_HELPER::network_connected()) {
            // connect() blocks for up to the socket timeout, so do not retry on every loop,
            // otherwise an unreachable broker stalls the main loop (and bus decoding)
            if (newly_connected && (!attempted || millis() - last_attempt >= MQTT_RECONNECT_INTERVAL_MS)) {
                JSONDEBUG("Newly connected WIFI detected in MQTT loop");
                attempted = true;
                last_attempt = millis();
                setWill();
                if (mqttClient.connect(client_id.c_str(), user, password)) {
                    JSONDEBUG("Successfully connected MQTT");
                    WEB_CONSOLE::log("MQTT connected as " + client_id);
                    mqttClient.subscribe(rx_topic_name);
                    mqttClient.subscribe("homeassistant/status");

                    send_ha_discovery();

                    mqtt_connects++;
                    newly_connected = false;
                    new_connection_established = true;
                    status_requested = true;
                }
            }

            mqttClient.loop();
            if (!mqttClient.connected()) {
                if (!newly_connected) {
                    JSONDEBUG("MQTT lost connection");
                    WEB_CONSOLE::log("MQTT lost connection (error " + String((int)mqttClient.lastError()) + ")");
                }
                newly_connected = true;
            } else {
                // Indicate a new connection if HA gets online,
                // so that state is resend
                if(ha_online) {
                    ha_online = false;
                    send_ha_discovery();
                    new_connection_established = true;
                    status_requested = true;
                }
            }
        }
    }

    /**
     * If a new MQTT message is received, it can be retrievd via this function.
     * Trailing whitespaces of received data is removed.
     * @return String, if nothiung was received, receives an empty String.
    */
    String& receive() {
        if(new_string_available) {
            new_string_available = false;
            return received_mqtt_payload;
        }
        return empty;
    }

    /** Returns true if MQTT was newly connected since last call*/
    bool isNewConnection() {
        static uint16_t counter = 0;

        //Delay new connection return because otherwise discovery and value is send too fast after each other
        if(new_connection_established) {
            counter = counter + 1;
        } else {
            counter = 0;
        }

        if (counter >= 1<<14 && new_connection_established) {
            new_connection_established = false;
            return true;
        }
        return false;
    }

};