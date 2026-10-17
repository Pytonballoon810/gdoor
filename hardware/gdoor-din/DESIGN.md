# GDoor DIN — design spec

A GDoor adapter for a 2-module DIN-rail enclosure (35 mm wide) with Ethernet,
audio and the bus interface on one board, the ESP32-S3 module soldered on.
Status: **layout routed and DRC-clean (2026-10-17), not yet built or tested.**
JLCPCB production files are generated outside the repo (see *Manufacturing*).
`esp32.kicad_sch` is the v4.1
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

## Layout

Stack-up and copper:

- F.Cu and B.Cu carry signals and a GND pour each (0.2 mm clearance, thermal
  reliefs, islands removed). In1.Cu is a GND plane, In2.Cu the +3.3V plane.
- 134 GND stitching vias on a 3 mm grid tie the four layers together; each
  is placed only where it clears every other net.
- Antenna: the ESP32-S3-WROOM-1 footprint's own keepout covers F.Cu and
  B.Cu only. A rule area named "Antenna keepout (planes)" adds the same on
  In1.Cu and In2.Cu, so no plane runs under the antenna.

Rules (`esp32.kicad_pro`, `esp32.kicad_dru`, JLCPCB 4-layer):

- Vias 0.45 mm / 0.2 mm drill (JLCPCB standard, no extra cost on 4 layers);
  Default netclass track 0.2 mm.
- The "PTH to Track" and "Pad to Track" rules apply to pads only; written
  for any item, they also caught vias and overrode the 0.254 mm via rule.
- Silkscreen reference text is 0.8 × 0.8 mm, 0.12 mm thick (the Nobble
  convention), placed clear of pads, other silk and the board edge, so
  `silk_overlap`, `silk_edge_clearance` and `silk_over_copper` are zero.
  The "Minimum Text" rule was lowered from the JLC template's 1.0 / 0.15 to
  match. 39 references in the densest 0402 groups (around the codec and the
  W5500) have no free spot and are hidden; they stay on F.Fab.

Parts removed from the copied v4.1 audio sheet (2026-10-17): the microphone
option parts C28, C30, R61–R66, R67 and R68, with their wiring; the unused
codec speaker pins (U5 pins 11 and 14) are no-connects. R69–R72
(attenuation) and C62/C63 (filtering) stay as unfitted options on B.Cu.

Passives on the copied sheet are 0402 (C1, C12, C29, C31 stay 0603).

## Manufacturing

JLCPCB files live in `production/gdoor_din/` (gerbers, drill, BOM, CPL,
IPC netlist), generated from commit `0a8af0d` by `jlcfab.py`:

```
"C:/Program Files/KiCad/10.0/bin/python.exe" jlcfab.py production/gdoor_din
```

It runs bennymeg's Fabrication Toolkit CLI (`-nI -nB -e -t`) on a copy of
the board in a temp directory and never writes the project files. On the
copy, before the toolkit runs:

- **Rotation:** every part gets an `FT Rotation Offset`. Parts with the
  board's own `JlcRotOffset` / `JLCPCB Rotation Offset` (J1, J4, U1, U5,
  U6, U7) keep exactly that offset. Every other part gets the toolkit's
  footprint-database correction.
- **J101 position:** J101 gets `FT Position Offset` `0,1.39`. KiCad's
  footprint origin sits 2.60 mm from the USB-C peg holes, JLC's model
  origin 1.206 mm. Aligned on the holes, JLC's point is 1.39 mm further
  +X on this board, where J101 sits at -90°. The CPL point is therefore
  105.54 / -108.0, not 104.15.
- **J103 left out:** J103 (expansion header, hand-soldered, no LCSC part)
  is marked DNP, so it drops out of BOM and CPL like the DNP parts.

After the toolkit:

- **BOM columns:** they are rewritten to JLC's template: `Comment,
  Designator, Footprint, LCSC Part #`. The toolkit's `Value`/`Quantity`
  columns made the PCBA quote fail ("fee item calculate failed").
- **Self-check:** the script checks that BOM and CPL list the same
  designators, that every BOM line has an LCSC number, and J101's CPL
  point. It exits non-zero on a problem.

Other notes:

- **No popups:** KiCad's python pops a modal wx dialog for every assert and
  log message. The script disables both, and stubs
  `pcbnew.ActionPlugin.register`, before importing anything. Otherwise
  the toolkit asserts ("PgmOrNull()" failed in register_action).
- **LCSC numbers** come from the `LCSC` field, or from `MPN` on the copied
  sheet.
- **Single-sided assembly:** every B.Cu part is DNP.
- **Check rotations** in JLCPCB's placement preview. U101 (module), J102
  (RJ45), SW101/SW102, Y101 and the LEDs have no correction in the
  database.

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
- J4 (5 V screw terminal) is DNP and excluded from the BOM, so JLCPCB will
  not fit it; the 5 V input from a terminal needs it soldered by hand.
- J103 (expansion header) has no LCSC number; it is hand-soldered and
  left out of the JLC files.
- Several decoupling caps sit further from their pins than ideal (C116,
  C57, C59, C61, C29 are 5–12 mm away), and some codec/W5500 routes meander.
