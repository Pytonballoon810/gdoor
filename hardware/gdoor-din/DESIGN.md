# GDoor DIN — design spec

A GDoor adapter for a 2-module DIN-rail enclosure (35 mm wide) with Ethernet,
audio and the bus interface on one board, the ESP32-S3 module soldered on.
Status: **schematic in progress, no layout yet.** `esp32.kicad_sch` is the v4.1
bus and audio sheet (devkit removed); `mcu_eth.kicad_sch` holds the new
MCU, USB-C, power and Ethernet circuitry (W5500 per WIZnet's WIZ850io
reference). The file stem stays `esp32` because the copied sheet stores its
references under that project name.

Decisions (2026-10-16):

- Enclosure: 2 modules (35 mm), 3D printed. The PCB stands on edge, parallel
  to the side walls, so the connectors face the front window.
- MCU: ESP32-S3-WROOM-1-N8R2 module (8 MB flash, 2 MB quad PSRAM; PSRAM is
  needed for the VoIP audio stack), assembled by JLCPCB.
- Power: 5 V from USB-C or a screw terminal. No PoE, no power from the bus.
- Opening the door (bus TX) is mandatory and keeps its own pins; no feature
  may share them.

## Blocks

| Block | Based on | Notes |
|---|---|---|
| Bus interface (rectifier, RX comparators, TX filter and driver, +5Vonoff switch) | v4.0 schematic, unchanged | Proven on v3.x/v4.0. TX_EN switches the TX filter supply, which keeps the TX pin low at boot. |
| Bus voltage measurement | v4.0 (`BUS_DCVOLT`) | Closes issue #28 (bus connected/disconnected). |
| Audio codec ES8374 + bus coupling | v4.0 audio section | Own 3.3 V LDO (`+3.3V_ANA`) as on v4.0. |
| RX threshold | v4.0, fixed | The S3 has no DAC; the fixed-threshold input of v4.0 (`RX`) is used. The adjustable path (`RX_DAC`, via unfitted R56) is not connected to the MCU. |
| Ethernet | new: W5500 + HR911105A (magnetics and LEDs integrated) | 25 MHz crystal, standard Wiznet reference circuit. |
| MCU | new: ESP32-S3-WROOM-1-N8R2 | Native USB (flashing, console), BOOT and RESET buttons. |
| USB-C | new: TYPE-C-31-M-12, 5.1 kΩ CC pull-downs, USBLC6-2SC6 ESD | Power and programming. |
| Power | AMS1117-3.3 for 3.3 V digital (S3 + W5500), second AMS1117 for the codec | 5 V inputs OR-ed with SS14 Schottkys. |
| Status LEDs | new: green (GPIO2) + red (GPIO17), 0603 | Issue #46. Plain LEDs instead of a WS2812, which needs more than 3.3 V logic when run from 5 V. |

## ESP32-S3 pin map

Avoided: GPIO0/3/45/46 (strapping; GPIO0 only for the BOOT button),
GPIO19/20 (USB), GPIO26–32 (flash/PSRAM), GPIO35–37 (kept free for octal-PSRAM
module variants), GPIO43/44 (UART0, test pads for a serial console).

| Function | GPIO | Why there |
|---|---|---|
| Bus TX (LEDC PWM, 52 kHz) | 4 | mandatory, own pin |
| Bus TX enable | 5 | |
| Bus RX (comparator, digital) | 6 | |
| Bus RX analog | 7 | ADC1, usable with WiFi on |
| Bus DC voltage | 8 | ADC1 |
| Status LED red | 17 | |
| W5500 CS / MOSI / SCK / MISO | 10 / 11 / 12 / 13 | SPI2 IO_MUX pins, full speed |
| W5500 INT / RST | 14 / 21 | |
| I2S MCLK / BCLK / LRCK | 38 / 39 / 40 | S3 routes MCLK to any pin (the v4.0 GPIO0 problem is gone) |
| I2S DOUT (to codec DSDIN) / DIN (from codec ASDOUT) | 41 / 42 | |
| I2C SDA / SCL (codec control) | 47 / 48 | |
| Status LED green | 2 | |
| Expansion header (with 3V3, GND, TXD0, RXD0) | 15, 16 | sensors, serial console |

## Board and enclosure

- 4 layers, 1.6 mm, about 85 × 50 mm (height × depth in the housing).
- Front edge (inside the 45 mm DIN front window): RJ45, USB-C, status LED,
  light pipes/holes for BOOT and RESET.
- Top edge: bus screw terminal (2-pin, 3.5 mm) and 5 V screw terminal.
- The enclosure (printable, two halves, DIN clip) is designed after the
  board outline is final.

## Firmware impact

- MQTT firmware: needs an S3 build environment and a third pin map (in
  addition to v3.x and v4.0); Ethernet via the existing W5500 support with the
  new pins; the RX threshold via LEDC PWM instead of `dacWrite`.
- Audio: the working VoIP firmware (ESP-ADF) is the maintainer's private code;
  this board only provides the hardware for it.

## Open points

- AMS1117 dropout from 5 V minus a Schottky drop (about 4.6 V) is tight at
  the S3's WiFi peaks; check, or use a lower-dropout 1 A LDO.
- Keep the codec, the bus coupling and the WiFi antenna apart: antenna at
  the board edge away from the RJ45 and with no copper below it.
