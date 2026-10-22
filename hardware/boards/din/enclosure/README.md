# GDoor DIN enclosure

3D-printable DIN-rail housing for the gdoor-din board: 2 modules (35 mm),
90 mm high, DIN 43880 style front window (45 mm) standing 6 mm proud of the
shoulders, TS35 rail clip. RJ45, USB-C and the two status LEDs face the
front window. Two pluggable 3.81 mm terminals: the external 5 V input on
the top face, the bus on the bottom face.

![assembly](preview.png)

| File | What |
|---|---|
| `enclosure.scad` | the model (OpenSCAD 2021.01) |
| `board_ghost.scad` | board and parts as boxes, generated, for the fit check |
| `board_export.py` | regenerates `board_ghost.scad` from `../esp32.kicad_pcb` |
| `gdoor-din-base.stl`, `gdoor-din-lid.stl` | ready to print |
| `gdoor-din-base.step`, `gdoor-din-lid.step` | the same parts as STEP solids, for other CAD tools |
| `gdoor-din-enclosure.step` | base and lid in their assembled position |
| `step_export.py` | converts the STLs into the STEP files |

## Build the STLs

```
openscad -o gdoor-din-base.stl -D 'part="base"' enclosure.scad
openscad -o gdoor-din-lid.stl  -D 'part="lid"'  enclosure.scad
openscad -o fit.stl            -D 'part="fit"'  enclosure.scad   # must be empty
```

After a layout change run `board_export.py` (KiCad's python, from
`hardware/boards/din`) and the fit check again. The front openings, posts
and button holes are parameters in `enclosure.scad`, not derived from the
board, so they have to be moved by hand if the parts move.

OpenSCAD cannot write STEP, so `step_export.py` converts the STLs: it
sews the triangles into a closed solid and merges flat faces. Round
features stay faceted (`$fn = 40`). It needs OpenCascade's python bindings
(`pip install cadquery-ocp`); run it after the STLs:

```
python step_export.py
```

## Print

PETG preferred: the rail latch is a printed spring. 0.2 mm layers, no
supports. Both parts print flat on their outer side wall; the lid STL is
already flipped.

## Layout

- The board stands on edge, its back side on four rails in the base
  (3.5 mm clearance for untrimmed THT leads), its component side towards
  the lid. Five posts on the lid hold it down at free spots.
- Front window: the board's front tab reaches into it, its edge in a
  0.3 mm groove in the window wall. The RJ45 jack goes through a body-sized
  opening (16.6 x 13.9 mm), and the USB-C receptacle in a stadium opening
  around its shell (9.4 x 3.7 mm, 0.2 mm clearance). Both faces end 0.2 mm
  inside the window face, so the cable overmold stops on the face. There are also two 1.3 mm holes for the LEDs. The LEDs are top-emitting
  on the board, so the holes show their glow, not the LED itself; a short
  piece of clear filament works as a light pipe.
- BOOT and RESET are pressed with a pin through the lid (labelled). The lid
  is covered by the neighbouring module on the rail, so take the device off
  the rail to reach them.
- Rail clip: fixed hook at the top, spring latch at the bottom. Hook the
  top on, press the bottom on. To remove, push the latch hook down with a
  small screwdriver from below. The latch (10 mm wide) sits on a 2 x 4.6 mm
  beam that runs 20 mm into the base under the board, cut free through the
  back and side wall. It bends in the print plane, along the layers.

## Plugs (5 V input, bus)

Each plug is the female half of a 2-pole 3.81 mm pluggable terminal (15EDGK
type, e.g. QUARKZMAN PCB-Klemmleiste) in a cradle on the lid:

- **5 V** (external input): mating end out of the top face, above J4
  (`5V_IN`), labelled `5V`. The male cable plug goes on from above.
- **BUS**: mating end out of the bottom face, labelled `BUS`. The male
  cable plug goes on from below. Its cradle is the top one mirrored, at
  x = 32, so its wires leave the back of the plug clear of the RST and
  BOOT button tubes (x = 44).

The screws face the board, so they are reached with the lid off.

Retention clips sit at the back (wire-entry) end of the plug. At each back
corner an arm (2 mm thick) stands up from the lid plate behind the back
face, overlapping it by 0.6 mm beside the wire entries; it takes the push
when the cable plug goes on. A hook at the arm's tip reaches 0.8 mm over
the back edge of the screw-side face, with a lead-in chamfer. The side
walls only guide the plug sideways. Press the plug into the cradle from the
open side, flat side first, until it clicks; no glue. To take it out, pull
the two arms back. The arms bend across the layers, by about 1 % strain,
which PETG and PLA both take. If the arms cover the wire entries of your
plug, or it is loose, change `clip_back` / `clip_lip`.

The outer size comes from the listing: female 8 x 11 x 15 mm (`plug_w`,
`plug_h`, `plug_len`); the male cable half is 8 x 11 x 18 mm. The mating
section (`plug_mate_len` 9 mm, `plug_mate_h` 8 mm) is still an estimate:
measure it on the part. The step between the screw
section and the lower mating section rests against the inside of the top
wall (bottom wall for the bus plug) and keeps the plug in when the cable is
pulled.

Wiring: J1 (bus) and J4 (5 V) both sit on the board's top edge, and their
wire entries face the top wall with about 1 mm to spare, so screw terminals
fitted there cannot take wires inside this housing. Leave both unfitted and
solder wires into their holes: two short ones from J4 to the 5 V plug, and
two from J1 down to the bus plug at the bottom (about 90 mm, run along the
component side, under the lid).

## Assembly

1. Solder the 5 V wires into J4's holes and the bus wires into J1's holes.
2. Clip the plugs into the lid cradles, clamp the wires.
3. Lay the board into the base: back side down onto the rails, front tab
   into the groove in the window wall, so the RJ45 and USB-C come through
   their openings.
4. Close the lid; the plugs drop into the slots in the top and bottom
   walls. The rim
   snaps into the base.
