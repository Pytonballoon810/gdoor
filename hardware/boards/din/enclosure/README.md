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
supports. Both parts print flat on their outer side wall; the base STL is
already turned over.

## Mirrored design frame

`enclosure.scad` models everything in a design frame that is the mirror
image of the real device: `board_export.py` maps the board into it with a
reflection (X = 52.4 − (kx − 100), Y = 87.5 − (ky − 60), component side at
+Z). Up to 2026-10-22 the parts were exported straight from that frame, so
they were drawn for a mirror image of the board, and the real board would
not have fitted (terminals at the wrong edge, RJ45, USB-C and LEDs off their
openings).

Now every output goes through `real()`, a mirror about z = W/2. The real
board fits the exported parts, and the fit check covers it unchanged,
because mirroring the housing and the ghost together does not change their
overlap. In the real device the lid is the Z = 0 side, on the right when you
look at the front window. Engraved labels are drawn pre-mirrored, so that
they read correctly on the printed parts. Keep `board_export.py` and
`real()` as a pair: changing either one alone mirrors the board against the
housing again.

## Layout

- The board stands on edge, its back side on four rails in the base
  (3.5 mm clearance for untrimmed THT leads), its component side towards
  the lid. Five posts on the lid hold it down at free spots. Each keeps a
  2.6 mm tip for the first 12 mm above the board, clear of the tall parts,
  then widens in a cone to 6 mm at the lid plate, so it prints stiff.
- Lid closure: four snap fingers (7 mm wide, 1.2 mm thick), two on the
  top wall and two on the bottom wall, in line with the rim and cut free
  from it by 0.5 mm slots. They reach 10 mm into the base. A hook at each
  tip (1.3 mm deep into the 1.8 mm wall, ramped on the tip side, with a
  0.6 mm flat at full depth under the catching face) clicks into a window
  through the base wall. The fingers bend across the layers, by about
  2.3 % strain: fine for PETG, at the limit for PLA.
  To open, press the four hooks in through the windows with a small
  screwdriver and lift the lid.
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

Each cradle on the lid has three parts:

- **Barrel frame**: a closed frame at the housing's outer face, in the
  plane of the top wall (bottom wall for the bus plug), which sits in a
  slot in the base wall. The barrel press-fits through its 8.35 x 7 mm hole
  (`barrel_w`, `barrel_h`, measured from the platform the plug lies on).
  The step between the screw section and the barrel bears on the inside of
  the frame, so the plug stays in when the cable is pulled.
- **Platform**: the plug's flat side lies on it, 8.05 mm in from the outer
  face (`platform_len`).
- **Side walls with clips**: the side walls run from the frame back to the
  plug's back face, 17 mm in from the outer face (`plug_back`), about 9 mm
  past the end of the platform. Their last 10 mm (`clip_free`) are spring
  fingers, 2.0 mm thick (`clip_t`), cut free from the lid plate by a 45 deg
  cut so they print without support. They bend sideways, in the print plane
  (about 3.8 % strain while the plug goes in: close to PETG's limit, too
  much for PLA). At 1.0 mm they flexed enough to let the plug give when the
  cable plug was pressed on; 2.0 mm is 8 times as stiff. The barrel frame
  and its slot in the base wall are 0.55 mm wider each side than the frame
  alone needs (`frame_hw`); the side walls narrow to that width over their
  last 0.2 mm, where they join the frame. The frame cannot grow further: the
  5 V plug's slot would reach the front wall. A hook at
  each tip, 4.5 mm tall, drops in behind
  the plug's back face and overlaps it by 1.0 mm beside the wire entries
  (`clip_lip`). Each hook has a 2 mm lead-in ramp, a 0.5 mm flat at full
  depth and a catching face undercut by 0.3 mm (`clip_under`), so pushing
  the plug back pulls the hooks in rather than spreading them. The plug
  cannot be pushed back in when the cable plug goes on.

To fit a plug: lay it flat side down behind the cradle and slide it out
through the frame, barrel first, until both hooks click in behind it; no
glue. To take it out, spread the two fingers and slide it back. If the
hooks cover your plug's wire entries, reduce `clip_lip`; if the barrel is
loose or too tight, change `barrel_w` / `barrel_h`.

The height (11 mm, `plug_h`) comes from the listing. Width, barrel height
and the back face position (17 mm from the outer face) are measured. How
far the barrel sticks out (`plug_mate_len`) is a guess; it only shapes the
ghost in the preview.

Wiring: J1 (bus) and J4 (5 V) both sit on the board's top edge, and their
wire entries face the top wall with about 1 mm to spare, so screw terminals
fitted there cannot take wires inside this housing. Leave both unfitted and
solder wires into their holes: two short ones from J4 to the 5 V plug, and
two from J1 down to the bus plug at the bottom (about 90 mm, run along the
component side, under the lid).

## Assembly

1. Solder the 5 V wires into J4's holes and the bus wires into J1's holes.
2. Slide the plugs into the lid cradles until they click, clamp the wires.
3. Lay the board into the base: back side down onto the rails, front tab
   into the groove in the window wall, so the RJ45 and USB-C come through
   their openings.
4. Close the lid; the barrel frames drop into the slots in the top and
   bottom walls, and the four snap hooks click into their windows.
