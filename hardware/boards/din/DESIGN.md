# GDoor DIN — design spec

A GDoor adapter for a 2-module DIN-rail enclosure (35 mm wide) with Ethernet,
audio and the bus interface on one board, the ESP32-S3 module soldered on.
Status: **layout routed and DRC-clean, schematic logic-checked (2026-10-18),
not yet built or tested.** The JLCPCB production files are in the repo (see
*Manufacturing*).

`esp32.kicad_sch` is the v4.1 bus and audio sheet (devkit removed);
`mcu_eth.kicad_sch` holds the new MCU, USB-C, power and Ethernet circuitry
(W5500 per WIZnet's WIZ850io reference). The file stem stays `esp32` because
the copied sheet stores its references under that project name.

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
| Bus interface (rectifier, RX filter and comparator, TX filter and driver, +5V_onoff switch) | v4.0 schematic | TX_EN switches the TX filter and driver supply (Q1/Q2), which keeps the TX stage off at boot. C10, R21 and C18 are DNP here but fitted on v4.0 (see *Open points*). |
| Bus voltage measurement | v4.0 (`BUS_DCVOLT`, R35/R73 82k/10k) | Reads up to about 30 V on ADC1. Closes issue #28 (bus connected/disconnected). |
| Audio codec ES8374 + bus coupling | v4.0 audio section | Own AMS1117 (U7, `+3.3V_ANA`). MONOOUT drives the bus through R32 and C21; the bus feeds MIC1P/MIC2P through C29/C31. Speaker outputs unused. |
| RX threshold | v4.0, fixed | The S3 has no DAC, so the fixed-threshold comparator U6A (`RX`, GPIO6) is used. The adjustable path (`RX_DAC`, R56) is removed; U6B is unused and sits latched high through R22/R27/R30/R31. |
| Ethernet | new: W5500 + HR911105A (magnetics and LEDs integrated) | 25 MHz crystal, WIZ850io reference circuit, PMODE all-capable. |
| MCU | new: ESP32-S3-WROOM-1-N8R2 | Native USB (flashing, console). SW101 = RESET (EN, 10k/1 µF), SW102 = BOOT (IO0, 10k). |
| USB-C | new: TYPE-C-31-M-12, 5.1 kΩ CC pull-downs, USBLC6-2SC6 ESD | Power and programming. |
| Power | AP2114H-3.3TRG1 (U103, LCSC C150716) for 3.3 V digital (S3 + W5500) | 5 V inputs OR-ed with SS14 Schottkys (D101 USB, D2 terminal). AP2114H: 1 A, 450 mV typ / 750 mV max dropout at 1 A, AMS1117 pinout (1 GND, 2/tab VOUT, 3 VIN). The AP2114**HA** has a different pinout and does not fit this footprint. 10 µF in (C104), 22 µF out (C106). |
| Status LEDs | new: green (GPIO2, 100 Ω) + red (GPIO17, 1 kΩ), 0603 | Issue #46. Plain LEDs instead of a WS2812, which needs more than 3.3 V logic when run from 5 V. |

## ESP32-S3 pin map

Avoided: GPIO0/3/45/46 (strapping; GPIO0 only for the BOOT button, GPIO3,
45 and 46 left open on their internal defaults), GPIO19/20 (USB), GPIO26–32
(flash/PSRAM), GPIO35–37 (kept free for octal-PSRAM module variants).

| Function | GPIO | Why there |
|---|---|---|
| Bus TX (LEDC PWM, 52 kHz) | 4 | mandatory, own pin |
| Bus TX enable | 5 | |
| Bus RX (comparator, digital) | 6 | |
| Bus RX analog | 7 | ADC1, usable with WiFi on |
| Bus DC voltage | 8 | ADC1 |
| Status LED green | 2 | |
| Status LED red | 17 | |
| W5500 CS / MOSI / SCK / MISO | 10 / 11 / 12 / 13 | SPI2 IO_MUX pins, full speed |
| W5500 INT / RST | 14 / 21 | 4.7k pull-ups (also on CS) |
| I2S MCLK / BCLK / LRCK | 38 / 39 / 40 | S3 routes MCLK to any pin (the v4.0 GPIO0 problem is gone) |
| I2S DOUT (to codec DSDIN) / DIN (from codec ASDOUT) | 41 / 42 | |
| I2C SDA / SCL (codec control) | 47 / 48 | 2.4k pull-ups; codec address set by CE (R45 to GND) |
| Expansion header J103 (3V3, GND, TXD0, RXD0, IO15, IO16) | 43, 44, 15, 16 | serial console, sensors |

## Board and enclosure

- 4 layers, 1.6 mm, about 85 × 50 mm (height × depth in the housing), plus
  a 6.8 × 40.4 mm front tab (KiCad x 93.2–100, y 82.3–122.7). The tab sits
  in the 45 mm DIN front window, and its edge runs in a 0.3 mm groove in the
  window wall.
- Front: J102 (RJ45) and J101 (USB-C) stand on the tab, their faces 0.2 mm
  inside the window face (flush). The window has a body-sized RJ45 opening
  (16.6 × 13.9 mm), a stadium around the USB-C shell (9.4 × 3.7 mm) and two
  LED holes.
- Top edge: bus screw terminal J1 (2-pin, 3.5 mm) and 5 V screw terminal J4.
  Neither can take wires inside the enclosure (see *Open points*).
- RESET (SW101) and BOOT (SW102) are labelled on the silkscreen and on the
  lid, and pressed with a pin through the lid.
- The enclosure (printable base and lid, DIN clip) is in `enclosure/`; see
  its README. The bus connects through a pluggable 3.81 mm terminal on the
  top face, wired to J1's pads.

## Layout

Stack-up and copper:

- The board's physical stackup is JLCPCB's JLC04161H-7628 (1.6 mm, 1 oz
  outer, 0.5 oz inner): 0.035 mm copper / 0.2104 mm 7628 prepreg (εr 4.4) /
  0.0152 mm / 1.065 mm core / 0.0152 mm / 0.2104 mm prepreg / 0.035 mm.
  Order the board with this stackup so KiCad's impedance numbers hold. A 2D
  field solve on it gives 65.7 Ω single-ended for a 0.2 mm track and
  98.8 Ω differential for the 0.2/0.15 mm USB and Ethernet RD pairs.
- F.Cu and B.Cu carry signals and a GND pour each (0.2 mm clearance, thermal
  reliefs, islands removed). In1.Cu is a GND plane, In2.Cu the +3.3V plane.
- GND stitching vias on a 3 mm grid tie the four layers together; each is
  placed only where it clears every other net.
- Antenna: the ESP32-S3-WROOM-1 footprint's own keepout covers F.Cu and
  B.Cu only. A rule area named "Antenna keepout (planes)" adds the same on
  In1.Cu and In2.Cu, so no plane runs under the antenna. The antenna sits at
  the board edge away from the RJ45.

Front-tab move (2026-10-17): J101 and J102 moved 8.45 mm forward (J102 also
0.8 mm down, to clear the top of the window), with their Ethernet parts
(R108, R117–R120, C121–C124) and USB parts (R103, D101, U102); R104 moved to
the old D101 corner. Tracks crossing the edge of the moved block kept their
geometry and got straight connectors along the move, so both halves of each
pair grew by the same amount: USB D+/D− skew is −4.20 mm (was −4.17), the
Ethernet pairs are unchanged. 17 stitching vias under the moved parts were
removed.

Rules (`esp32.kicad_pro`, `esp32.kicad_dru`, JLCPCB 4-layer):

- Vias 0.45 mm / 0.2 mm drill (JLCPCB standard, no extra cost on 4 layers);
  Default netclass track 0.2 mm; copper to edge 0.3 mm.
- The "PTH to Track" and "Pad to Track" rules apply to pads only; written
  for any item, they also caught vias and overrode the 0.254 mm via rule.
- Silkscreen text is 0.8 × 0.8 mm, 0.12 mm thick (the Nobble convention),
  placed clear of pads, other silk and the board edge. The "Minimum Text"
  rule was lowered from the JLC template's 1.0 / 0.15 to match. 39
  references in the densest 0402 groups (around the codec and the W5500)
  have no free spot and are hidden; they stay on F.Fab.

Parts removed from the copied v4.1 sheet:

- 2026-10-17: the microphone option parts C28, C30, R61–R66, R67 and R68,
  with their wiring; the codec speaker pins (U5 pins 11 and 14) are
  no-connects.
- 2026-10-18: the unfitted options R55 (+3.3V to `+3.3V_AUDIO` link), R56
  (`RX_DAC` link), R69–R72 (mic attenuation) and C62/C63 (alternative mic
  coupling), with their wiring and tracks.

Passives on the copied sheet are 0402 (C1, C12, C29, C31 stay 0603).

## Logic check (2026-10-18)

ERC has no errors; the 319 off-grid warnings come from the copied sheet.
Checked block
by block against the netlist:

- **Power:** both 5 V inputs are OR-ed by SS14 diodes (40 V). U103 and U7
  have their caps in place; the AP2114H has no enable pin.
- **USB:** CC1/CC2 have 5.1 kΩ pull-downs; ESD is on D+/D− and VBUS; D+/D−
  go to the module's USB pins.
- **ESP32-S3:** EN has 10k/1 µF and IO0 a 10k pull-up. IO3/45/46 are open,
  so the defaults hold: 3.3 V flash and normal boot.
- **W5500:** RSVD pins are tied to GND, PMODE pins high, EXRES 12.4k 1 %,
  TOCAP 4.7 µF, 1V2O 10 nF. The 25 MHz crystal has 18 pF caps and 1 MΩ
  across it. Analog supply goes through FB101. TX has 49.9 Ω to AVDD, RX is
  terminated 2 × 49.9 Ω to RX_CM (10 nF), and the shield goes through
  1 nF / 2 kV.
- **Bus:** RX is the v4.0 band-pass into U6A. TX is the band-pass U3 into
  the line driver U1, AC-coupled by C1 (47 nF 50 V).
- **Codec:** each supply has its own 33 Ω + 10 µF/100 nF. I2C has 100 Ω/22 pF
  in series and I2S 33 Ω/22 pF.

Found and fixed: the BOOT/RESET labels on the silkscreen (2026-10-17) and on
the enclosure lid were swapped. SW101 is wired to EN (RESET), SW102 to IO0
(BOOT).

## Manufacturing

JLCPCB files live in `production/gdoor_din/` (gerbers, drill, BOM, CPL,
IPC netlist, iBOMs), generated by `jlcfab.py`:

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
  97.09 / -108.0, not 95.70.
- **J103 left out:** J103 (expansion header, hand-soldered, no LCSC part)
  is marked DNP, so it drops out of BOM and CPL like the DNP parts.

After the toolkit:

- **BOM columns:** they are rewritten to JLC's template: `Comment,
  Designator, Footprint, LCSC Part #`. The toolkit's `Value`/`Quantity`
  columns made the PCBA quote fail ("fee item calculate failed").
- **Self-check:** the script checks that BOM and CPL list the same
  designators, that every BOM line has an LCSC number, and J101's CPL
  point. It exits non-zero on a problem.

The iBOMs: `ibom.html` comes from the InteractiveHtmlBom plugin (with tracks
and nets), `ibom-partdb.html` from `partdb_ibom.py` (Part-DB storage and JLC
cost; `--offline` reuses `jlc-prices.json`).

Other notes:

- **No popups:** KiCad's python pops a modal wx dialog for every assert and
  log message. The script disables both, and stubs
  `pcbnew.ActionPlugin.register`, before importing anything. Otherwise
  the toolkit asserts ("PgmOrNull()" failed in register_action).
- **LCSC numbers** come from the `LCSC` field, or from `MPN` on the copied
  sheet.
- **Single-sided assembly:** every B.Cu part is DNP. Left on B.Cu: C18
  (hand-soldered, see *Open points*) and the ESD logo S1.
- **Check rotations** in JLCPCB's placement preview. U101 (module), U103,
  J102 (RJ45), SW101/SW102, Y101 and the LEDs have no correction in the
  database.

## Firmware impact

- MQTT firmware: needs an S3 build environment and a third pin map (in
  addition to v3.x and v4.0); Ethernet via the existing W5500 support with the
  new pins; the RX threshold via LEDC PWM instead of `dacWrite`.
- Audio: the working VoIP firmware (ESP-ADF) is the maintainer's private code;
  this board only provides the hardware for it.

## Open points

Decisions:

- **C10, R21, C18** (done 2026-10-18): fitted on the upstream
  `hardware/boards/esp32-mini` board, so they are fitted here too.
  - C18 (100 pF) filters the TX driver input (U1 +, with R11 10k).
  - C10 (1 nF) and R21 (4k7) load the TX node behind R34; R21 also pulls TX
    low while the pin floats.
  - C10 and R21 are on F.Cu and fitted by JLC, at (131.25, 64.3) and
    (128.9, 64.3). A via at (129.0, 65.0) joins them to the old B.Cu TX-node
    track, and GND vias at (128.3, 63.55) and (132.65, 64.3) ground them.
  - C18 stays on B.Cu, routed but DNP: **hand-solder it** (100 pF 0402,
    C1546). There is no free F.Cu spot near U1 or R11, because the strip
    above U1 is crossed by the C1-Pad1 and +5V_onoff diagonals and Q2 and
    R14/R15/R16/R24 close in on the other sides.
- **C29, C31** (done 2026-10-18): they sit on the bus DC through R74, so
  they now have a 50 V rating (the bus runs up to about 30 V).
  - C29: 10 µF 50 V 1206 (C13585, like C21), at (120.6, 106.3).
  - C31: 10 µF 50 V 0805 (C440198, Murata GRM21BR61H106KE43L), at (129.357,
    100.5); a 1206 did not fit there. Its pad-1 route to R40 now runs down
    the right side of the part at x 130.385.
- **0 Ω links:** R34, R36, R57, R58, R59, R60 and R74 are fitted 0 Ω links
  left over from upstream options. They could become plain copper (7 fewer
  placements), but each one would need a schematic and routing change.
- **J4 and D2:** the 5 V terminal cannot take wires in the enclosure (its
  entries face the top wall), so the second 5 V input is only usable with
  wires soldered to J4's pads. Keep it, or drop J4 and D2.
- **Unused parts:** U6B with its four resistors, and the codec's MICBIAS caps
  C22/C35, are unused on this board. They are kept so the unused inputs stay
  defined.
- **Status LEDs:** the green resistor (R105, 100 Ω, about 12 mA) and the red
  one (R106, 1 kΩ, about 1.3 mA) differ by 10×, so green is much brighter.

To do in KiCad:

- **Tidy:** the front-tab connectors are long straight runs across the
  strip the move emptied (x 113–122, y 98–113). That strip also has room for
  new stitching vias.

To check on the first build:

- U103 is a JLC extended part ($3 fee); check its rotation in the placement
  preview.
- Front window: the RJ45 opening, the USB-C stadium and the tab groove
  (1.1 mm of wall left) need checking on the first print.
- J1 should be DNP: the enclosure wires the bus plug straight to its pads,
  but it is in the JLC BOM as C695629.
- J103 (expansion header) has no LCSC number; it is hand-soldered.
- Several decoupling caps sit further from their pins than ideal (C116,
  C57, C59, C61, C29 are 5–12 mm away), and some codec/W5500 routes meander.
