# ESP32 Firmware
More information about the firmware are located on the
[GDoor Homepage](https://gdoor-org.github.io/documentation/firmware.html).

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
