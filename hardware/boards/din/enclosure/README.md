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
| `gdoor-din-keeper.stl` | holds a plug in its cradle; print two |
| `gdoor-din.3mf` | unsliced Bambu Studio project, two plates: 1 single colour, 2 two colours (`body` and `accent` parts); both with the two keepers |
| `print_3mf.py` | packs the STLs into `gdoor-din.3mf` |
| `bambu_project_settings.config` | the Bambu settings `gdoor-din.3mf` needs to open; a starting point only |
| `gdoor-din-{base,lid}-{body,accent}.stl` | the same parts split into two colours, for a multi-material print |
| `gdoor-din-base.step`, `gdoor-din-lid.step`, `gdoor-din-keeper.step` | the same parts as STEP solids, for other CAD tools |
| `gdoor-din-enclosure.step` | base, lid and keepers in their assembled position |
| `step_export.py` | converts the STLs into the STEP files |
| `gdoor-din-full.step` | the whole device: enclosure, plugs, board with its parts, mock wires |
| `full_assembly.py` | builds `gdoor-din-full.step` |

## Build the STLs

```
openscad -o gdoor-din-base.stl -D 'part="base"' enclosure.scad
openscad -o gdoor-din-lid.stl  -D 'part="lid"'  enclosure.scad
openscad -o gdoor-din-keeper.stl -D 'part="keeper"' enclosure.scad
openscad -o fit.stl            -D 'part="fit"'  enclosure.scad   # see below
python print_3mf.py   # after the colour STLs below too: writes gdoor-din.3mf
```

The fit check renders everything that collides: the housing and the
keepers against the board, against the plugs, and the keepers against the
housing. It must be empty except for two thin U-shaped slivers, one per
keeper, where the keepers reach 1.65 mm into the modelled plugs' back ends
on purpose (`keep_fwd`, see Plugs below).

Rebuild the 3MF whenever any of the STLs change. `gdoor-din.3mf` is an
unsliced Bambu Studio project with two plates, each with the base and the
lid side by side and the two keepers in front of them, moved on the plate
but not turned:

- **Plate 1, single colour**: `gdoor-din-base`, `gdoor-din-lid`,
  `gdoor-din-keeper-1`, `gdoor-din-keeper-2`.
- **Plate 2, two colours**: `gdoor-din-base-colour`, `gdoor-din-lid-colour`,
  each with a `body` part (filament 1) and an `accent` part (filament 2),
  and the two keepers on filament 1.

Open it in Bambu Studio and slice the plate you want. Plates exist only in
Bambu's own project format, and Bambu Studio cannot open such a project
without its settings file, so the 3MF carries `bambu_project_settings.config`:
the P1S 0.2 nozzle, 0.10mm Standard @BBL X1C 0.2 nozzle and Bambu PLA Basic
twice (black, white), written by Bambu Studio from its system profiles. It
is only there so the file opens: pick your own printer, process and
filaments before slicing. Other slicers ignore the plates and show all four
objects, the two-colour ones a plate width to the right.

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

`full_assembly.py` then builds `gdoor-din-full.step`, the whole device in
the assembled position. It contains everything in `gdoor-din-enclosure.step`
and the board from a kicad-cli export, half-turned into the housing's frame.
The board export has no copper and no J1/J4, which stay unfitted. The script
adds four mock wires (1.6 mm insulation, stripped ends through the pads and
into the plugs' wire entries):

- J4 to the 5 V plug: red (+5 V, pin 2) and black (GND, pin 1), back over
  the plug and down into its entries from behind, clear of the RJ45.
- J1 to the bus plug: blue (pin 2) and white (pin 1), diagonally across the
  component side under the lid, at the height of the plug's wire entries,
  then down between the cradle's side walls and the keeper's legs.

It checks each wire against the base, the lid, the plugs and every board
part, and prints the overlap (0 now). The command for the board export is in
the script's header.

```
python full_assembly.py board.step
```

## Print

PETG preferred: the rail latch is a printed spring. 0.2 mm layers, no
supports. Base and lid print flat on their outer side wall; the base STL is
already turned over. The keepers print flat on their back face.

PLA works for the springs: the lid snaps (0.9 %, across the layers) and the
rail latch (about 1 %, along the layers). But PLA softens from about 55 °C and creeps under steady load,
which slowly relaxes the rail latch in a warm cabinet. Fine for a test fit
and for a cool spot; in a warm cabinet print it in PETG or ASA.

### Colour accents (multi-material)

Each part also comes as a body and an accent STL, in the same print
orientation, that together make up the part. Easiest is plate 2 of
`gdoor-din.3mf`: the base and the lid, each one object with two parts
named `body` and `accent`, the accents already on filament 2. Or load both STLs of a part at once as
one object with two parts (Bambu Studio / OrcaSlicer ask when you import
them together). Accent:

- **Front window face**: a 0.8 mm fascia over the whole window face, base
  and lid. LAN, USB and GDoor are left out of it, so they read flush in
  the body colour.
- **Lid face**: the window nose (the part of the lid in front of the
  shoulders), the round pads of the RST and BOOT buttons and their labels,
  each 0.4 mm deep (the first two layers).
- **Plug labels**: 5V and BUS, filled 0.8 mm deep.

Faces that stand upright in the print are 0.8 mm deep (`acc_wd`), two
extrusion widths, so the slicer keeps them; faces on the bed are 0.4 mm
(`acc_d`). Together, body and accent are the single-colour part with its
engraved labels filled flush. `-D 'part="colours"'` previews them assembled.

```
openscad -o gdoor-din-base-body.stl   -D 'part="base_body"'   enclosure.scad
openscad -o gdoor-din-base-accent.stl -D 'part="base_accent"' enclosure.scad
openscad -o gdoor-din-lid-body.stl    -D 'part="lid_body"'    enclosure.scad
openscad -o gdoor-din-lid-accent.stl  -D 'part="lid_accent"'  enclosure.scad
python print_3mf.py
```

`print_3mf.py` needs only Python's standard library. On plate 2 each part
is one object with its two meshes as components. Bambu Studio's
`Metadata/model_settings.config` in the file carries the object and part
names (Bambu Studio and OrcaSlicer ignore the names in the mesh file), the
plates, and the filament per part; `bambu_project_settings.config` goes in
as `Metadata/project_settings.config`.

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
- Lid closure: four snap fingers (7 mm wide), two on the top wall and two
  on the bottom wall, in line with the rim and cut free from it by 0.5 mm
  slots. They reach 14 mm into the base and taper from 1.6 mm at the root
  to 1.0 mm at the tip; the extra root thickness is on the cavity side, so
  the outer face stays flat against the wall. A hook at each tip (1.0 mm
  deep into the 1.8 mm wall, ramped on the tip side, with a 0.6 mm flat at
  full depth under the catching face) clicks into a window through the
  base wall. The fingers stand upright in the print, so they bend across
  the layers, the weakest direction. They used to be 10 mm long, 1.2 mm
  thick with a 1.3 mm hook (about 3.2 % strain) and broke off at the root.
  Now the strain is about 0.9 %, and a 0.8 mm 45° chamfer at the root's
  outer (tension) side, with a matching relief in the base wall's top
  edge, removes the sharp corner the cracks started from. The tips stop
  1.8 mm above J1 and J4 (17.4 mm), which sets the length.
  To open, press the four hooks in through the windows with a small
  screwdriver and lift the lid.
- Front window: the board's front tab reaches into it, its edge in a
  0.3 mm groove in the window wall. The RJ45 jack goes through a body-sized
  opening (16.6 x 13.9 mm), and the USB-C receptacle in a stadium opening
  around its shell (9.4 x 3.7 mm, 0.2 mm clearance). Both faces end 0.2 mm
  inside the window face, so the cable overmold stops on the face. There are also two 1.3 mm holes for the LEDs. The LEDs are top-emitting
  on the board, so the holes show their glow, not the LED itself; a short
  piece of clear filament works as a light pipe.
- BOOT and RESET are print-in-place buttons in the lid (labelled). Each is
  a tongue cut free from the lid plate by a 0.6 mm U-shaped slot (5.5 mm
  wide, 8.5 mm from its root, at the front, to the round pad), thinned to
  1.0 mm from the inside, with its outer face flush with the lid. A 3.6 mm
  plunger hangs from the pad down to 0.3 mm above the switch's actuator
  (TL3342, top at 1.54 mm). Press the pad with a finger: about 0.55 mm
  travel, about 1.1 % strain in the tongue, which bends along the layers.
  Nothing stands proud of the lid, so the neighbouring module on the rail
  cannot press them; take the device off the rail to reach them.
  The tongue tilts as it bends, so the plunger tip swings about 2.5 mm
  towards the root over the full travel. Pad and plunger therefore sit
  1.9 mm behind the switch centre (`btn_off`), which puts the tip on the
  actuator halfway through the travel. If a button does not click, the
  plunger is too short for your board: reduce `btn_gap`.
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
  BOOT button plungers (x = 42).

The screws face the board, so they are reached with the lid off.

Each cradle on the lid has three parts, and a separate keeper holds the
plug in it:

- **Barrel frame**: a closed frame at the housing's outer face, in the
  plane of the top wall (bottom wall for the bus plug), which sits in a
  slot in the base wall. The barrel press-fits through its 8.35 x 7 mm hole
  (`barrel_w`, `barrel_h`, measured from the platform the plug lies on).
  The step between the screw section and the barrel bears on the inside of
  the frame, so the plug stays in when the cable is pulled.
- **Platform**: the plug's flat side lies on it, 8.05 mm in from the outer
  face (`platform_len`). 9 mm at most: any longer and the L-shaped plug
  cannot be fitted (a full-length platform was tried on 2026-10-23 and
  taken out again).
- **Side walls**: fixed, 2.0 mm thick (`side_t`), from the frame back past
  the plug's back face, which is 17 mm in from the outer face
  (`plug_back`), to 2 mm behind the keeper (`keep_back`). The barrel frame
  and its slot in the base wall are 0.55 mm wider each side than the frame
  alone needs (`frame_hw`); the side walls narrow to that width over their
  last 0.2 mm, where they join the frame. The frame cannot grow further:
  the 5 V plug's slot would reach the front wall. Each side wall has a
  vertical groove for the keeper, 1.0 mm deep (`keep_g`), open towards the
  board and running down to the lid plate.
- **Keeper** (separate part, `gdoor-din-keeper.stl`, one per plug): a
  2.5 mm (`keep_t`) U-shaped plate, 10.6 mm wide and 14.5 mm tall, that
  drops into the two grooves behind the plug's back face and stands on
  the lid plate. Its legs cover the back face at both sides, 0.7 mm in
  from the edges (`keep_lip`), clear of the wire entries (3 mm wide at the
  3.81 mm pitch, to 3.4 mm from the centre line). The bridge between them
  fills the gap between the lid plate and the plug's flat side and reaches
  1.2 mm (`keep_bridge`) onto the back face. The wires leave through the
  opening between the legs. Pushing the plug back (the cable plug going on)
  presses the keeper against the grooves' back faces, so nothing bends;
  pulling on the cable is taken by the barrel frame. The keeper is held in
  its grooves by friction, 0.1 mm clearance each side (`keep_clr`), and by
  the wires under its bridge.
  Its front face is 15.3 mm in from the outer face: 0.1 mm behind the
  plug's modelled back face (`keep_play`), then 1.8 mm forward
  (`keep_fwd`), because on the first print of the clips that came before
  it, their hooks sat about 1.8 mm too far back and did not touch the plug
  until it was pushed back. The plug's position is unchanged, so in the
  model (fit check, STEP export) the keepers reach about 1.65 mm into the
  plug's back end.
  **Why a keeper:** up to 2026-10-24 a spring clip finger on each side wall
  hooked in behind the plug. Across its versions the hooks spread open
  under the push, were too stiff to let the plug in, sat too far back, or
  let the plug slip under them. The keeper takes the same load with no
  spring.

To fit a plug: lay it flat side down behind the cradle, between the side
walls, and slide it out through the frame, barrel first, until its step
sits against the frame. Clamp the wires, then push the keeper into the two
grooves from the board side, bridge first, with the wires between its
legs, until it sits on the lid plate; no glue. To take the plug out, pull
the keeper and slide the plug back. If the keeper will not go in, the plug
sits further back than the model says: reduce `keep_fwd`; if it is loose in
its grooves, reduce `keep_clr`, or raise it if it is too tight. If the
barrel is loose or too tight, change `barrel_w` / `barrel_h`.

The height (11 mm, `plug_h`) comes from the listing. Width and barrel
height and the back face position (17 mm from the outer face) are
measured. How
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
2. Slide the plugs into the lid cradles, clamp the wires, and push a
   keeper in behind each plug.
3. Lay the board into the base: back side down onto the rails, front tab
   into the groove in the window wall, so the RJ45 and USB-C come through
   their openings.
4. Close the lid; the barrel frames drop into the slots in the top and
   bottom walls, and the four snap hooks click into their windows.
