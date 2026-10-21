# ESP32 Firmware
More information about the firmware are located on the
[GDoor Homepage](https://gdoor-org.github.io/documentation/firmware.html).

## Bus core

The bus encoder/decoder in `src/gdoor*.cpp` uses the ESP-IDF drivers
(gptimer, LEDC timer 3 / channel 7, GPIO interrupt, DAC) directly, not the
Arduino timer and LEDC API, so the ESPHome component compiles the same code on
ESP-IDF. This firmware still needs the Arduino core 3.x (pinned in
`platformio.ini`) for WiFi, MQTT and the web configuration. With Arduino's
prebuilt settings the bus interrupts pause while flash is written (saving the
configuration, OTA), as before.

## Adapter hardware v4.0

The v4.0 audio prototype wires the ESP32 differently, because IO25 and IO26
go to the audio codec there. Select "v4.0 (audio prototype)" under
"Adapter hardware" in the setup, then the firmware uses:

| | v3.x | v4.0 |
|---|---|---|
| Bus transmit (TX) | IO25 | IO12 |
| Transmit enable | IO27 | IO27 |
| Bus receive | "RX Input" setting (IO22 adjustable) | IO21, fixed threshold |
| RX threshold (DAC) | IO26 | none, "IO22 Sensitivity" does not apply |

Only the bus functions are supported on v4.0; the firmware does not use the
audio codec or the bus voltage measurement. Ethernet (W5500) can not be used
on v4.0: its pins are taken by the codec (IO5 I2S, IO18/IO23 I2C), the firmware
refuses to start it there.

IO12 is a strapping pin of the ESP32 (it selects the flash voltage at boot).
On v4.0 it reads low as required: R21 is not fitted and the transmit filter is
only powered once TX_EN switches it on.

A board flashed with the default setting (v3.x) drives IO25 low and puts a
voltage on IO26, both inputs of the codec on v4.0; this does no harm, but
sending does not work until v4.0 is selected.

## Migrating to the larger partition layout

Firmware from this version on uses a different flash layout: two app slots of
1.875 MB (instead of 1.25 MB) and 128 kB for the configuration (instead of
1.375 MB). Ethernet support and the web console no longer fit the old slots.

The partition table can not be changed by an update over the web interface,
so **flash once over USB**. This erases the configuration:

1. Write down your settings from the web configuration ("Setup"): MQTT server,
   port, user, password, both topics, RX input and sensitivity.
2. Connect the ESP32 via USB and flash the firmware with the
   [web installer](https://gdoor-org.github.io/documentation/firmware.html), or
   with `pio run -t upload` from this directory.
3. Connect to the "GDoor" WiFi access point (password `12345678`) and enter
   WiFi and the settings from step 1 again.

The web installer writes the complete flash, so WiFi has to be entered again
as well. With `pio run -t upload` the WiFi credentials usually survive, the
MQTT settings never do (their file system moved).

Home Assistant keeps the existing entities: their unique IDs are derived from
the ESP32's MAC address, not from the configuration.

If a new firmware is installed via "Update" in the web interface instead, the
update either fails (image larger than the old slot) or the adapter runs on
the old layout. It then reports `"legacy_partitions": true` in the status
topic, and the web console and serial port show a warning, until it was
flashed over USB once.

## Web console

"Console" in the web interface menu (or `http://<adapter-ip>/console`) shows,
while the page is open:

- every bus message as it is received or sent (the same JSON as on MQTT),
- WiFi, Ethernet and MQTT connects and disconnects,
- the status JSON (version, network, RSSI, uptime, counters, ...),
- a field to send bus data, e.g. to test a door opener code.

The log keeps the last 60 lines in RAM, nothing is written to flash, and it is
cleared on restart. Low level debug output is still only available on the
serial port (`*debug`).

Sending from the console is **disabled by default**: the web interface has no
password, so anyone in the network could open the door. Enable "Web console
can send to the bus" in the setup only if your network is trusted. Requests
from other web pages are rejected, so a malicious site can not use your browser
to send to the bus.

## Ethernet (W5500 module)

Where WiFi does not reach the adapter, e.g. in a metal distribution cabinet,
a W5500 SPI Ethernet module can be wired to the ESP32 of an existing adapter.
The adapter v3.x only uses GPIO 21, 22, 25, 26, 27 (and 12/32 on v3.0), so the
module goes on the free VSPI pins:

| W5500 module | ESP32 (Wemos D1 mini ESP32) |
|---|---|
| SCLK | GPIO 18 |
| MISO | GPIO 19 |
| MOSI | GPIO 23 |
| CS / SCS | GPIO 5 |
| INT | GPIO 4 |
| RST | GPIO 16 |
| 3V3 | 3V3 |
| GND | GND |

The pins are set in `src/defines.h` (`ETH_W5500_*`). INT is optional: set
`ETH_W5500_INT` to `-1` and the module is polled instead. The W5500 draws up
to about 150 mA from 3.3 V; power the ESP32 board from a supply that can
deliver this in addition to the adapter.

Enable "Ethernet (W5500 module on SPI)" in the web configuration (first setup
via the "GDoor" WiFi access point, as usual). After the restart:

- With a cable plugged in, MQTT and the web configuration run over Ethernet,
  at the address the DHCP server assigns to it.
- WiFi stays available as a fallback. For Ethernet only, do not save WiFi
  credentials; the configuration access point then closes after 5 minutes.
- The status topic (`<bus_rx topic>/status`) shows `"network": "ethernet"`.

If the module is enabled but not found, GDoor prints a message on the serial
port and continues with WiFi.

The ESPHome component does not need this: use ESPHome's own
[`ethernet:`](https://esphome.io/components/ethernet.html) component with
`type: W5500` and the same pins.
