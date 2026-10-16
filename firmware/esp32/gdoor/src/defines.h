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
#ifndef DEFINES_H
#define DEFINES_H

// GDoor
#ifndef GDOOR_VERSION
#define GDOOR_VERSION "dev"
#endif

#define MAX_WORDLEN 25

// RX Statemachine
#define FLAG_RX_ACTIVE 0x01
#define FLAG_BITSTREAM_RECEIVED 0x02
#define FLAG_BITSTREAM_CONVERTED 0x04
#define FLAG_DATA_READY 0x08

// RX
#define BIT_ONE_DIV 2.5
#define BIT_MIN_LEN 5
#define STARTBIT_MIN_LEN 45

// TX
#define STARTBIT_PULSENUM 66
#define ONE_PULSENUM 16
#define ZERO_PULSENUM 37
#define PAUSE_PULSENUM 30

#define STATE_SENDING 0x01

// WIFI
#define DEFAULT_WIFI_SSID     "GDoor"
#define DEFAULT_WIFI_PASSWORD "12345678"
#define WIFI_WATCHDOG_RETRY_MS   30000UL  // Retry WiFi connection every 30 s while disconnected
#define WIFI_WATCHDOG_RESTART_MS 600000UL // Restart if WiFi stays down for 10 min

// Ethernet (optional W5500 SPI module, enabled in the web config)
// Uses the ESP32 VSPI pins, which the GDoor adapter v3.x leaves free
#define ETH_W5500_SPI_HOST SPI3_HOST
#define ETH_W5500_SCK  18
#define ETH_W5500_MISO 19
#define ETH_W5500_MOSI 23
#define ETH_W5500_CS   5
#define ETH_W5500_INT  4   // Module INT pin, W5500 is polled if not connected (set to -1)
#define ETH_W5500_RST  16  // Module RST pin (set to -1 if not connected)
#define ETH_W5500_SPI_MHZ 20

// Status
#define STATUS_INTERVAL_MS 60000UL // How often availability and status are published via MQTT
#define MQTT_RECONNECT_INTERVAL_MS 5000UL // Wait between MQTT connection attempts, as connect() blocks

// MQTT
#define DEFAULT_MQTT_SERVER   "0.0.0.0" 
#define DEFAULT_MQTT_PORT     "1883" 
#define DEFAULT_MQTT_TOPIC_BUS_RX "gdoor/bus_rx"
#define DEFAULT_MQTT_TOPIC_BUS_TX "gdoor/bus_tx"

// Settings

#define PIN_TX 25
#define PIN_TX_EN 27
#define PIN_RX_THRESH 26

// Adapter hardware selection: v4.0 (audio prototype) moved TX to IO12, because IO25/IO26
// carry I2S to the audio codec there. It has no RX threshold DAC, and IO22 is not
// connected (R56 not fitted), so the fixed threshold input IO21 is used.
// IO12 is a strapping pin (flash voltage), it reads low at boot on v4.0: R21 is not
// fitted and the TX filter is unpowered until TX_EN switches +5Vonoff on.
#define HW_V3_NAME "v3.x"
#define HW_V4_NAME "v4.0 (audio prototype)"
#define HW_CHOICES {HW_V3_NAME, HW_V4_NAME}
#define HW_CHOICES_LEN 2
#define PIN_TX_V4 12
#define PIN_RX_V4 21

// RX Pin Settings
#define RX_PIN_22_NAME "v3.1 adjustable (IO22)"
#define RX_PIN_22_NUM 22

#define RX_PIN_21_NAME "v3.1 (IO21)"
#define RX_PIN_21_NUM 21

#define RX_PIN_12_NAME "v3.0 bugfix (IO12)"
#define RX_PIN_12_NUM 12

#define RX_PIN_32_NAME "v3.0 (IO32)"
#define RX_PIN_32_NUM 32

#define RX_PIN_CHOICES {RX_PIN_22_NAME, RX_PIN_21_NAME, RX_PIN_12_NAME, RX_PIN_32_NAME}
#define RX_PIN_CHOICES_LEN 4

// RX Pin Sensitivity (only working for RX PIN22)
#define RX_SENS_LOW_NAME "Low (1.3V)"
#define RX_SENS_LOW_NUM 1.3
#define RX_SENS_MED_NAME "Med (1.45V)"
#define RX_SENS_MED_NUM 1.45
#define RX_SENS_HIGH_NAME "High (1.65V)"
#define RX_SENS_HIGH_NUM 1.65

#define RX_SENS_CHOICES {RX_SENS_HIGH_NAME, RX_SENS_MED_NAME, RX_SENS_LOW_NAME}
#define RX_SENS_CHOICES_LEN 3

#endif