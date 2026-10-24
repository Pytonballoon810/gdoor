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
| `gdoor-din-base.3mf`, `gdoor-din-lid.3mf` | the same parts as unsliced 3MF: geometry only, no print settings |
| `gdoor-din-{base,lid}-colour.3mf` | each part as one object with two parts, `body` and `accent`: unsliced, no print settings |
| `colour_3mf.py` | packs the body and accent STLs into the colour 3MFs |
| `gdoor-din-{base,lid}-{body,accent}.stl` | the same parts split into two colours, for a multi-material print |
| `gdoor-din-base.step`, `gdoor-din-lid.step` | the same parts as STEP solids, for other CAD tools |
| `gdoor-din-enclosure.step` | base and lid in their assembled position |
| `step_export.py` | converts the STLs into the STEP files |
| `gdoor-din-full.step` | the whole device: enclosure, plugs, board with its parts, mock wires |
| `full_assembly.py` | builds `gdoor-din-full.step` |

## Build the STLs

```
openscad -o gdoor-din-base.stl -D 'part="base"' enclosure.scad
openscad -o gdoor-din-lid.stl  -D 'part="lid"'  enclosure.scad
openscad -o gdoor-din-base.3mf -D 'part="base"' enclosure.scad
openscad -o gdoor-din-lid.3mf  -D 'part="lid"'  enclosure.scad
openscad -o fit.stl            -D 'part="fit"'  enclosure.scad   # must be empty
```

Rebuild the 3MFs whenever the STLs change. They hold only the mesh (in
mm, in the same print orientation), no printer, filament or process
settings, so open them in Bambu Studio and slice with your own presets.

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
  then down the channel between the cradle's clip fingers.

It checks each wire against the base, the lid, the plugs and every board
part, and prints the overlap (0 now). The command for the board export is in
the script's header.

```
python full_assembly.py board.step
```

## Print

PETG preferred: the rail latch is a printed spring. 0.2 mm layers, no
supports. Both parts print flat on their outer side wall; the base STL is
already turned over.

PLA works for the springs: the lid snaps (0.9 %, across the layers), the
rail latch (about 1 %) and the plug clips (1.5 to 1.9 %), both along the
layers. But PLA softens from about 55 °C and creeps under steady load,
which slowly relaxes the rail latch in a warm cabinet. Fine for a test fit
and for a cool spot; in a warm cabinet print it in PETG or ASA.

### Colour accents (multi-material)

Each part also comes as a body and an accent STL, in the same print
orientation, that together make up the part. Easiest is the colour 3MF
(`gdoor-din-base-colour.3mf`, `gdoor-din-lid-colour.3mf`): it opens as one
object with two parts named `body` and `accent`, so you only give the
accent part the second filament. Or load both STLs of a part at once as
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
python colour_3mf.py
```

`colour_3mf.py` needs only Python's standard library. Each colour 3MF holds
the two meshes as components of one object, plus Bambu Studio's
`Metadata/model_settings.config` with nothing in it but the object and part
names (Bambu Studio and OrcaSlicer ignore the names in the mesh file). No
extruder, filament, printer or process settings. Rebuild them whenever the
body or accent STLs change.

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

Each cradle on the lid has three parts:

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
- **Side walls**: fixed, 2.0 mm thick (`side_t`), from the frame back to
  0.6 mm (`clip_gap`) in front of the plug's back face, which is 17 mm in
  from the outer face (`plug_back`). The barrel frame and its slot in the
  base wall are 0.55 mm wider each side than the frame alone needs
  (`frame_hw`); the side walls narrow to that width over their last 0.2 mm,
  where they join the frame. The frame cannot grow further: the 5 V plug's
  slot would reach the front wall.
- **Clip fingers**: behind each side wall, a spring finger runs back from
  a hook at the plug's back face to its root 9.5 mm further back
  (`clip_free`), and on 3 mm onto the lid plate (`clip_anchor`). It is cut
  free from the lid plate by a 45 deg cut, so it prints without support,
  and bends sideways, in the print plane. Because of that cut, the free
  length also sets how close the hook comes to the lid plate. It tapers
  from 1.2 mm at the root (`clip_t0`) to 0.8 mm at the hook (`clip_t1`):
  about 1.5 % strain while the plug goes in (1.9 % if the plug sits
  off-centre), fine for PLA along the layers. The 5 V fingers' back part
  only reaches down to 2 mm above the RJ45 jack (`clip_step`, `clip_zr`).
  The hook's catching face is 15.3 mm in from the outer face: 0.1 mm
  behind the plug's modelled back face (`clip_play`), then 1.8 mm forward
  (`clip_fwd`), because on the first print the hooks sat about 1.8 mm too
  far back and did not touch the plug until it was pushed back. The plug's
  position is unchanged, so in the model (fit check, STEP export) the
  hooks now reach about 1.6 mm into the plug's back end. The hook is 5 mm tall: it covers the back face from 5.5 to
  10.5 mm above the plug's flat side, beside the wire entries (5.9 to
  9.4 mm), and overlaps it by 1.0 mm (`clip_lip`). It has a 2 mm lead-in
  ramp, a 0.5 mm flat at full depth and a catching face undercut by 0.3 mm
  (`clip_under`).
  **Why the root is behind the hook:** the hook sits on the finger's inner
  side, so a push on it also bends the finger. Up to 2026-10-23 the root
  was in front of the hook: pushing the plug back (the cable plug going on)
  pulled on the finger and bent the hooks outward, open, so only stiffness
  held the plug. At 1.0 mm the fingers gave; at 2.0 mm they had to bend by
  about 4 % to let the plug in, too much for PLA. With the root behind, the
  same push compresses the finger and bends the hook inward, further
  behind the plug, so the hold no longer depends on stiffness and the
  finger can be thin.
  **First print of that (2026-10-23):** the plug could slip under the
  hooks. Hence the hook 1.5 mm closer to the lid plate (`clip_free`
  11 -> 9.5).

To fit a plug: lay it flat side down behind the cradle, between the two
fingers and behind their hooks, and slide it out through the frame, barrel
first, until both hooks click in behind it; no glue. To take it out, spread the two fingers and slide it back. If the
hooks cover your plug's wire entries, reduce `clip_lip`; if the barrel is
loose or too tight, change `barrel_w` / `barrel_h`.

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
2. Slide the plugs into the lid cradles until they click, clamp the wires.
3. Lay the board into the base: back side down onto the rails, front tab
   into the groove in the window wall, so the RJ45 and USB-C come through
   their openings.
4. Close the lid; the barrel frames drop into the slots in the top and
   bottom walls, and the four snap hooks click into their windows.
