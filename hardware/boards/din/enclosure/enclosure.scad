// GDoor DIN enclosure: 2 modules (35 mm), DIN 43880 style front, TS35 clip.
//
// Coordinates (mm), of the design frame everything below is modelled in:
//   X = depth: 0 is the mounting face on the rail, the front window is at +X
//   Y = height on the panel: 0 bottom, 90 top
//   Z = width: 0 is the outside of the base's side wall, the lid closes at +Z
//
// The design frame is the mirror image of the real device. board_export.py
// maps the board into it with X = 52.4 - (kx - 100), Y = 87.5 - (ky - 60) and
// the component side at +Z, which is a reflection of the board, not a
// rotation. Every output therefore goes through real(), a mirror about
// z = W/2: in the real device the lid is the Z = 0 side, the base's side wall
// is at Z = W, and the board is the real one, not its mirror image. Engraved
// text is drawn pre-mirrored so that it reads correctly after real().
//
// The PCB stands on edge, parallel to the side walls, component side
// towards the lid. Its front edge (RJ45, USB-C, LEDs) faces the window.
//
// Parts (set `part` or use -D part="..."):
//   "base"     tub: side wall, perimeter, DIN clip, board rails
//   "lid"      flat side wall with rim, hold-down posts, flush buttons and
//              the cradles for the 5 V and bus plugs
//   "keeper"   holds a plug in its cradle (print two)
//   "assembly" both, plus the board and the plugs as ghosts
//   "open"     the base with board and plugs, lid off
//   "fit"      everything that collides with the board (must render empty)
//   "base_body", "base_accent", "lid_body", "lid_accent"
//              the two parts split into body and accent colour for a
//              multi-material print (see "colour accents" below)
//   "colours"  base and lid assembled, in body and accent colours
//
// Print both parts flat on their outer side wall: no supports needed.

part = "assembly";

include <board_ghost.scad>

$fn = 40;
eps = 0.01;

// ---- housing -------------------------------------------------------------
H        = 90;      // overall height (DIN 43880)
W        = 35;      // 2 modules x 17.5
wall     = 1.8;
win_h    = 45;      // front window height, centred on the rail
win_p    = 6;       // how far the window stands proud of the shoulders
chamfer  = 1;       // on the window's front edges

// ---- board (must match board_export.py) -----------------------------------
pcb_t        = 1.6;
pcb_front_x  = 52.4;
pcb_top_y    = 87.5;
pcb_d        = 50;              // depth  (KiCad X span)
pcb_h        = 85;              // height (KiCad Y span)
pcb_back_gap = 3.5;             // room for untrimmed THT leads on the back
pcb_z0       = wall + pcb_back_gap;
pcb_z1       = pcb_z0 + pcb_t;  // component side
// Front tab (KiCad x 93.2..100, y 82.3..122.7): the board reaches into the
// window so the RJ45 and USB-C faces end 0.2 mm inside the window face.
// Its edge sits in a groove in the window wall.
pcb_tab_d    = 6.8;
pcb_tab_y0   = 24.8;
pcb_tab_y1   = 65.2;
tab_groove   = 0.3;             // groove reaches this far past the tab edge

shoulder_x = pcb_front_x + 0.4 + wall;   // outside of the shoulder faces
front_x    = shoulder_x + win_p;         // outside of the window face
lid_z      = W - wall;                   // base / lid split

// ---- DIN rail TS35 x 7.5 ----------------------------------------------------
rail_y   = H / 2;       // rail centre line
rail_w   = 35;
brim_t   = 1;           // rail sheet thickness
hook_d   = 2.8;         // how far the hooks reach behind the mounting face
hook_lip = 1.3;         // lip overlap behind the brim
// Lower latch: a hook on a spring beam that runs along X from the mounting
// face into the base, under the board, and bends in Y. It lies in the print
// plane, so it flexes along the layers, not across them.
latch_w      = 10;      // hook width in Z, from the base's outside
latch_t      = 2.0;     // beam thickness, bends in Y
latch_h      = 4.6;     // beam height in Z (board back side is at pcb_z0)
latch_len    = 20;      // free length inside the base
latch_travel = 2.0;     // room below the beam (the lip needs hook_lip)

// ---- front openings (from the board layout) --------------------------------
rj45_y  = 57.2;  rj45_w = 16.6;  rj45_h = 13.9;    // J102 body passes through the wall
usb_y   = 39.5;  usb_w  = 9.4;   usb_h  = 3.7;     // J101 shell 8.94 x 3.26, flush
usb_zc  = pcb_z1 + 1.63;                           // receptacle centre
led_y   = [30.9, 32.9];                            // D104 red, D103 green
led_z   = pcb_z1 + 7.6;
led_d   = 1.3;

// ---- plugs: female 3.81 mm 2-pole pluggable terminal (15EDGK type) ---------
// Two of them: the 5 V input on the top face above J4, the bus on the
// bottom face. The parameters below describe the top one; the bottom one
// is the same cradle mirrored about y = H/2.
// Body measured along: w = pitch direction, h = towards the screws,
// len = wire entry to mating end. The mating end (the barrel) is lower than
// the screw section; that step bears against the barrel frame and stops
// the plug being pulled out. Height from the QUARKZMAN listing (female
// 8 x 11 x 15 mm); width, barrel height and the back face position are
// measured. The barrel's length outside the housing only matters for the
// ghost and is a guess.
plugs         = [[46, 1, "5V"], [32, 0, "BUS"]];   // [x centre, 1 = top / 0 = bottom, label]
plug_w        = 8.35;   // body and barrel width
plug_h        = 11.0;
plug_mate_h   = 7.0;    // barrel height (flush with the side opposite the screws)
plug_mate_len = 7.8;    // barrel length past the step (guess)
plug_back     = 17.0;   // outer face of the housing to the plug's back face
plug_clr      = 0.25;
plug_z1       = lid_z - 4;          // flat side (no screws), on the platform
plug_z0       = plug_z1 - plug_h;   // screw side, towards the board
plug_y_step   = H - wall;           // step sits against the barrel frame
plug_y0       = H - plug_back;      // wire end (back face)
plug_y1       = plug_y_step + plug_mate_len;   // mating end
plug_len      = plug_y1 - plug_y0;
platform_len  = 8.05;   // platform under the flat side, from the outer face
                        // (9 mm at most, or the L-shaped plug does not fit)
// Barrel frame: a closed frame on the lid, in the top wall's plane, that
// the barrel press-fits through (barrel_w x barrel_h, from the platform).
barrel_w      = 8.35;
barrel_h      = 7.0;
frame_t       = 1.2;
// Keeper: a separate printed U-shaped plate behind the plug's back face. Its
// two legs slide into grooves in the cradle's side walls from the board
// side, open end first, down to the lid plate, and cover the back face
// beside the wire entries. The wire entries are on the lid side of the back
// face, so the wires leave through the opening between the legs, next to
// the lid plate; the bridge closes the U at the board end. Pushing
// the plug back (the cable plug going on) presses the keeper against the
// grooves' back faces, so nothing has to flex. Up to 2026-10-24 spring clip
// fingers on the side walls did this; they never held the plug reliably.
// The keeper is held in its grooves by friction (keep_clr).
side_t        = 2.0;    // side walls along the plug
side_zw       = plug_z0 + 0.5;   // side walls' edge towards the board, away
                                 // from the frame (at the frame: level with it)
keep_t        = 2.5;    // keeper thickness, along the plug
keep_g        = 1.0;    // groove depth into the side wall (of side_t)
keep_clr      = 0.1;    // keeper in its groove, per side; raise if it is tight
keep_back     = 2.0;    // side wall behind the groove, takes the push
keep_play     = 0.1;    // keeper's front face to the plug's back face
// On the first print of the clips, their hooks sat about 1.8 mm too far
// back and did not touch the plug until it was pushed back; the keeper's
// front face sits that much further forward (the plug's position is
// unchanged, so in the model the keeper reaches 1.7 mm into it).
keep_fwd      = 1.8;
// Legs end keep_lip in from the plug's sides: the wire entries (3 mm wide
// at a 3.81 mm pitch) reach to 3.4 mm from its centre line.
keep_lip      = 0.7;
// Bridge between the legs, at the board end: it covers the back face from
// keep_bridge off the plug's lid-side face (plug_z1) to the legs' end. The
// wire entries (plug_model.py) reach to 5.1 mm off that face.
keep_bridge   = 5.6;
keep_ch       = 0.4;    // lead-in chamfer at the legs' ends, on the lid plate
// frame half-width. The side walls end on the frame, no wider than it, so
// they stay clear of the base wall beside its slot. Wider than this and the
// 5 V plug's slot (x = 46) runs into the front wall at x = 52.8.
frame_hw      = barrel_w / 2 + frame_t + 0.55;

// ---- lid features ------------------------------------------------------------
// RESET (SW101, ESP_EN) and BOOT (SW102, IO0), TL3342, top-actuated.
// Print-in-place buttons: a tongue cut free in the lid plate by a U-shaped
// slot carries a plunger down to the switch. The tongue's outer face is
// flush with the lid and nothing stands proud of it, so the neighbouring
// module on the rail cannot press it. The tongue is a cantilever, rooted
// towards the front (+X), and thinned from the cavity side so it bends
// along the layers at about 1.1 % strain at full travel.
// It tilts as it bends, so the plunger tip swings towards the root, about
// plunger length x 1.5 x deflection / btn_len. The pad and plunger sit
// btn_off behind the switch centre, so the tip is centred on the actuator
// halfway through its travel.
buttons    = [[44.0, 23.0, "RST"], [44.0, 14.0, "BOOT"]];   // switch centres
btn_top_z  = pcb_z1 + 1.54;   // actuator top (TL3342 3D model)
btn_gap    = 0.3;             // plunger tip above the actuator at rest
btn_travel = 0.25;            // switch travel
btn_len    = 8.5;             // tongue, root to pad centre (root stays inside the rim)
btn_w      = 5.5;             // tongue width and pad diameter
btn_t      = 1.0;             // tongue thickness, of the lid plate's wall
btn_slot   = 0.6;             // slot around the tongue
btn_d      = 3.6;             // plunger diameter
btn_off    = (W - btn_t / 2 - btn_top_z - btn_gap) * 1.5 * (btn_gap + btn_travel / 2) / btn_len;
// Hold-down posts on free board spots (checked against the courtyards).
posts     = [[3.8, 86.0], [4.0, 45.0], [4.0, 4.0], [50.5, 6.0], [35.5, 86.0]];
// Each post keeps the thin tip on the board up to post_stem above it (clear
// of the tall parts), then widens in a cone to post_root_d at the lid, so
// it prints stiff instead of as a 26 mm needle.
post_d      = 2.6;      // tip, on the board
post_root_d = 6.0;      // at the lid plate
post_stem   = 12;       // straight tip length above the board
rim_t     = 1.2;
rim_h     = 3;
rim_clr   = 0.2;
// Lid snaps: fingers in line with the rim reach down into the base; a hook
// at the tip clicks into a window through the base's top or bottom wall.
// To open, press the hooks in through the windows.
// The fingers stand upright in the print, so they bend across the layers:
// keep the strain low (about 0.9 %, was 3.2 % at 10 mm x 1.2 mm with a
// 1.3 mm hook, and they broke). Long, tapered, shallow hook, and a chamfer
// at the root on the outer (tension) side.
snaps     = [[12, 0], [44, 0], [12, 1], [26, 1]];   // [x, 0=bottom/1=top], clear of plugs and posts
snap_w    = 7;          // finger width along X
snap_len  = 14;         // finger length below the lid plate (tip clears J1/J4 at z 17.4)
snap_t0   = 1.6;        // thickness at the root (the extra is on the cavity side)
snap_t1   = 1.0;        // thickness at the tip
snap_hook = 1.0;        // hook depth into the window (the wall is 1.8)
snap_hh   = 2.0;        // hook height, lead-in ramp plus land (sets the base windows)
snap_land = 0.6;        // flat at full depth, under the catching face
snap_slot = 0.5;        // slots in the rim beside each finger
snap_fil  = 0.8;        // 45 deg chamfer at the root's outer side
snap_gus  = 1.2;        // round fillet at the root's cavity side, into the lid plate

// ---- colour accents (multi-material print) ------------------------------------
// The *_body and *_accent parts split base and lid into two colours. Accent:
// the front window face (a fascia, with LAN / USB / GDoor left in the body
// colour), the plug labels, and on the lid's outer face the window nose, the
// button pads and the button labels. Faces that print on the bed get acc_d
// (two 0.2 mm layers); faces that stand upright in the print get acc_wd, two
// extrusion widths, so the slicer does not drop them.
accents = part == "base_body" || part == "base_accent" || part == "lid_body" || part == "lid_accent"
       || part == "colours";
acc_colour = "DarkOrange";   // preview only; the slicer sets the real colour
acc_d   = 0.4;
acc_wd  = 0.8;

// =============================================================================

module outline() {
    // Body plus the proud front window, front edges chamfered.
    yb = rail_y - win_h / 2;
    yt = rail_y + win_h / 2;
    polygon([
        [0, 0], [shoulder_x, 0], [shoulder_x, yb],
        [front_x - chamfer, yb], [front_x, yb + chamfer],
        [front_x, yt - chamfer], [front_x - chamfer, yt],
        [shoulder_x, yt], [shoulder_x, H], [0, H]
    ]);
}

module cavity() { offset(delta = -wall) outline(); }

module top_hook() {
    // Fixed hook over the upper rail brim.
    ye = rail_y + rail_w / 2;          // upper brim edge
    polygon([
        [0, ye + 0.15], [0, ye + 3], [-hook_d, ye + 3],
        [-hook_d, ye - hook_lip], [-brim_t - 0.6, ye - hook_lip],
        [-brim_t - 0.15, ye - hook_lip + 0.45], [-brim_t - 0.15, ye + 0.15]
    ]);
}

latch_ye = rail_y - rail_w / 2;                 // lower brim edge
latch_y0 = latch_ye - 0.6 - latch_t;            // beam underside
latch_x1 = latch_len;                           // beam root

module latch_hook() {
    // Spring latch on the lower brim. The brim rides down the chamfer and
    // pushes the hook in -Y until the lip snaps in behind it. Push the hook
    // down with a screwdriver from below to release.
    ye = latch_ye;
    polygon([
        [-0.6, latch_y0], [-0.6, ye - 0.2],
        [-brim_t - 0.15, ye - 0.2], [-brim_t - 0.15, ye + hook_lip],
        [-brim_t - 0.4, ye + hook_lip], [-hook_d, ye - 0.2],
        [-hook_d, latch_y0]
    ]);
}

module latch() {
    linear_extrude(latch_w) latch_hook();
    // beam, rooted in the side wall past latch_x1
    translate([-hook_d + eps, latch_y0, 0])
        cube([latch_x1 + 4 + hook_d, latch_t, latch_h]);
}

module latch_clearance(h = latch_h + 0.6) {
    // Frees the beam: through the back wall and the side wall, and the
    // space it swings into under the board.
    translate([-1, latch_y0 - latch_travel, -1])
        cube([latch_x1 + 1, latch_t + latch_travel + 0.5, h + 1]);
}

// ---- base ------------------------------------------------------------------

module board_rails() {
    // Rails under the board edges on the back side. The front one stops
    // short of J103's pads.
    w = 1.0;
    h = pcb_back_gap;
    x0 = pcb_front_x - pcb_d;
    y0 = pcb_top_y - pcb_h;
    translate([0, 0, wall - eps]) linear_extrude(h + eps) {
        translate([x0, y0]) square([w, pcb_h]);                  // back
        translate([x0, y0]) square([pcb_d - 1.5, w]);                  // bottom
        translate([x0, pcb_top_y - w]) square([pcb_d - 1.5, w]);       // top
        translate([pcb_front_x - 0.9, 31]) square([0.9, pcb_top_y - 32]); // front
    }
}

module front_openings() {
    fx = shoulder_x - eps;
    len = win_p + 1;
    // RJ45: the jack body itself goes through, its face flush with the window
    translate([fx, rj45_y - rj45_w / 2, pcb_z1 - eps]) cube([len, rj45_w, rj45_h]);
    // groove in the window wall for the board tab's front edge
    gx = front_x - wall - eps;
    translate([gx, pcb_tab_y0 - 0.3, pcb_z0 - 0.2])
        cube([pcb_front_x + pcb_tab_d + tab_groove - gx, pcb_tab_y1 - pcb_tab_y0 + 0.6, pcb_t + 0.4]);
    // USB-C: stadium around the receptacle shell, which ends flush
    translate([fx, usb_y, usb_zc]) rotate([0, 90, 0])
        linear_extrude(len) hull() for (s = [-1, 1])
            translate([0, s * (usb_w - usb_h) / 2]) circle(d = usb_h);
    // status LEDs
    for (y = led_y) translate([fx, y, led_z]) rotate([0, 90, 0]) cylinder(d = led_d, h = len);
}

module front_labels(d = 0.4) {
    // Engraved on the window face, reading across the width.
    module lbl(t, y, z) {
        translate([front_x - d, y, z]) mirror([0, 0, 1]) rotate([0, 90, 0])   // pre-mirrored for real()
            linear_extrude(d + 1) text(t, size = 3, halign = "center", valign = "center",
                                       font = "Liberation Sans:style=Bold");
    }
    lbl("LAN", rj45_y, 27.5);
    lbl("USB", usb_y, 27.5);
    lbl("GDoor", rail_y - win_h / 2 + 5, 17.5);
}

module plug_at(p) {
    // Places a plug feature drawn for the top face at plug p.
    if (p[1] == 1) children();
    else translate([0, H, 0]) mirror([0, 1, 0]) children();
}

// bottom of the slot in the top wall, under the lid's barrel frame
notch_z = plug_z1 - barrel_h - frame_t - 0.2;

module plug_notch(xc) {
    // Slot in the top wall for the barrel frame, open towards the lid so
    // the frame drops in with the lid.
    w = 2 * frame_hw + 0.4;
    translate([xc - w / 2, H - wall - 1, notch_z])
        cube([w, wall + 2, lid_z - notch_z + eps]);
}

module plug_label(p, d = 0.4) {
    // Engraved on the outer face, centred on the plug slot.
    // Pre-mirrored about its own plane for real().
    z = notch_z - 3.5;
    if (p[1] == 1) translate([p[0], H - d, z]) mirror([0, 0, 1]) rotate([-90, 0, 0]) linear_extrude(d + 0.6)
        text(p[2], size = 3, halign = "center", valign = "center", font = "Liberation Sans:style=Bold");
    else translate([p[0], d, z]) mirror([0, 0, 1]) rotate([90, 0, 0]) linear_extrude(d + 0.6)
        text(p[2], size = 3, halign = "center", valign = "center", font = "Liberation Sans:style=Bold");
}

snap_zc = lid_z - snap_len + snap_hh;   // hook's catching face

module snap_windows() {
    // Through the top / bottom wall; the hook catches the window's lid-side
    // edge.
    for (s = snaps) plug_at(s) translate([s[0] - snap_w / 2 - 0.2, H - wall - 1, lid_z - snap_len - 0.3])
        cube([snap_w + 0.4, wall + 2, snap_zc - (lid_z - snap_len - 0.3)]);
    // relief in the wall's top inner edge for the chamfer at the finger root
    c = snap_fil + 0.1;
    for (s = snaps) plug_at(s) translate([s[0] - snap_w / 2 - snap_slot, 0, 0]) rotate([90, 0, 90])
        linear_extrude(snap_w + 2 * snap_slot)
            polygon([[H - wall - eps, lid_z + eps], [H - wall + c, lid_z + eps], [H - wall - eps, lid_z - c - eps]]);
}

module base() {
    difference() {
        union() {
            linear_extrude(lid_z) outline();
            linear_extrude(lid_z) top_hook();
        }
        translate([0, 0, wall]) linear_extrude(lid_z) cavity();
        front_openings();
        if (!accents) front_labels();   // with accents, the fascia leaves them in the body colour
        for (p = plugs) { plug_at(p) plug_notch(p[0]); plug_label(p, accents ? acc_wd : 0.4); }
        snap_windows();
        latch_clearance();
    }
    // the back rail crosses the beam: cut it through its full height
    difference() { board_rails(); latch_clearance(wall + pcb_back_gap + 1); }
    latch();
}

// ---- lid -------------------------------------------------------------------

module snap_finger(xc) {
    // Drawn for the top wall. Bends towards the cavity; the hook is ramped
    // on its tip side, so the lid pushes on, and flat on the lid side.
    yo = H - wall - rim_clr;         // outer face, along the wall
    zt = lid_z - snap_len;
    translate([xc - snap_w / 2, 0, 0]) rotate([90, 0, 90]) linear_extrude(snap_w) {
        // tapered finger, outer face flat, thicker towards the cavity at the root
        polygon([[yo, lid_z + eps], [yo - snap_t0, lid_z + eps], [yo - snap_t1, zt], [yo, zt]]);
        // root chamfer on the outer side, into the relief in the base wall
        polygon([[yo - eps, lid_z + eps], [yo + snap_fil, lid_z + eps], [yo - eps, lid_z - snap_fil]]);
        // root fillet on the cavity side: no sharp inner corner where pulling
        // on the lid (hooks caught) bends the finger outwards
        yi = yo - snap_t0 + 0.05;
        difference() {
            translate([yi - snap_gus - 0.05, lid_z - snap_gus]) square([snap_gus + 0.05, snap_gus + eps]);
            translate([yi - snap_gus - 0.05, lid_z - snap_gus]) circle(r = snap_gus);
        }
        polygon([[yo - eps, snap_zc], [yo + rim_clr + snap_hook, snap_zc],
                 [yo + rim_clr + snap_hook, snap_zc - snap_land], [yo - eps, zt]]);
    }
}

module lid_rim() {
    translate([0, 0, lid_z - rim_h]) linear_extrude(rim_h + eps) difference() {
        offset(delta = -rim_clr) cavity();
        offset(delta = -rim_clr - rim_t) cavity();
        // slots that free the snap fingers from the rim
        for (s = snaps) {
            y = s[1] == 1 ? H - wall - rim_clr - rim_t - 1 : wall - 1;
            translate([s[0] - snap_w / 2 - snap_slot, y]) square([snap_w + 2 * snap_slot, rim_t + rim_clr + 2]);
        }
    }
    for (s = snaps) plug_at(s) snap_finger(s[0]);
}

keep_y  = plug_y0 - keep_play + keep_fwd;   // keeper's front face
keep_xi = plug_w / 2 - keep_lip;            // legs' inner edges, from the centre
keep_xo = plug_w / 2 + plug_clr + keep_g - keep_clr;   // legs' outer edges
keep_zb = lid_z - plug_z1 + keep_bridge;    // bridge's lid-side edge, from the lid plate
keep_h  = lid_z - side_zw;                  // leg length, from the lid plate

module keeper_shape() {
    // Local frame: x across (centred on the plug), y along the plug, the
    // front face at y = 0 and the back at -keep_t, z from the lid plate's
    // inner face (0) towards the board. Symmetric in x. Open towards the lid
    // plate, the bridge at the board end.
    rotate([90, 0, 0]) linear_extrude(keep_t) polygon([
        [-keep_xo, keep_h], [keep_xo, keep_h], [keep_xo, keep_ch], [keep_xo - keep_ch, 0],
        [keep_xi, 0], [keep_xi, keep_zb], [-keep_xi, keep_zb], [-keep_xi, 0],
        [-keep_xo + keep_ch, 0], [-keep_xo, keep_ch]]);
}

module keeper(xc, s = 0) {
    // In place behind the top plug, design frame (z towards the lid). s
    // shrinks it, for the fit check against the parts it only touches.
    translate([xc, keep_y, lid_z]) mirror([0, 0, 1]) intersection() {
        keeper_shape();
        translate([-keep_xo + s, -keep_t + s, s]) cube([2 * (keep_xo - s), keep_t - 2 * s, keep_h - 2 * s]);
    }
}

module keepers(s = 0) { for (p = plugs) plug_at(p) keeper(p[0], s); }

module plug_cradle(xc) {
    // The plug goes in flat side down behind the cradle and slides out
    // through the frame, barrel first; then the keeper drops in behind it.
    c  = plug_clr;
    xi = plug_w / 2 + c;             // side walls' inner faces, from xc
    yg = keep_y - keep_t - keep_clr; // grooves' back face
    ys = yg - keep_back;             // back end of the side walls
    fw = frame_hw;
    fz = plug_z1 - barrel_h - frame_t;
    // platform under the flat side
    translate([xc - xi + 0.3, H - platform_len, plug_z1])
        cube([2 * xi - 0.6, platform_len, lid_z - plug_z1 + eps]);
    // barrel frame in the top wall's plane: the step bears on its inside
    difference() {
        translate([xc - fw, plug_y_step, fz]) cube([2 * fw, wall, lid_z - fz + eps]);
        translate([xc - barrel_w / 2, plug_y_step - 1, plug_z1 - barrel_h])
            cube([barrel_w, wall + 2, barrel_h]);
    }
    for (s = [-1, 1]) {
        xw = xc + s * xi;                         // inner face
        xa = s < 0 ? xw - side_t : xw;
        // side wall, from behind the keeper's groove to the frame: deeper
        // towards the board, but level with the frame where it meets it, so
        // it stays clear of the base wall. The groove is open towards the
        // board and runs down to the lid plate.
        difference() {
            translate([xa, ys, side_zw]) cube([side_t, plug_y_step - 0.2 - ys, lid_z - side_zw + eps]);
            translate([s < 0 ? xw - keep_g : xw - eps, yg, side_zw - 1])
                cube([keep_g + eps, keep_t + 2 * keep_clr, lid_z - side_zw + 1]);
        }
        // last 0.2 mm into the frame: no wider than the frame, which has to
        // fit its slot in the base wall
        ct = min(side_t, frame_hw - xi);
        translate([s < 0 ? xw - ct : xw, plug_y_step - 0.2 - eps, fz])
            cube([ct, 0.2 + 2 * eps, lid_z - fz + eps]);
    }
}

module button_tongue(b) {
    // 2D: the tongue, pad end round, root at +X
    px = b[0] - btn_off;
    hull() {
        translate([px, b[1]]) circle(d = btn_w);
        translate([px + btn_len, b[1] - btn_w / 2]) square([eps, btn_w]);
    }
}

module button_slot(b) {
    // 2D: U-shaped slot around the tongue, open at the root
    difference() {
        offset(r = btn_slot) button_tongue(b);
        button_tongue(b);
        translate([b[0] - btn_off + btn_len, b[1] - btn_w]) square([btn_slot + 1, 2 * btn_w]);
    }
}

module button_plunger(b) {
    // from the tongue's inner face down to btn_gap above the actuator; a
    // cone at the root, a chamfer at the tip
    z0 = btn_top_z + btn_gap;
    zt = W - btn_t;
    translate([b[0] - btn_off, b[1], z0]) {
        cylinder(d1 = btn_d - 0.8, d2 = btn_d, h = 0.4);
        translate([0, 0, 0.4 - eps]) cylinder(d = btn_d, h = zt - z0 - 0.4 + 2 * eps);
        translate([0, 0, zt - z0 - 1.5]) cylinder(d1 = btn_d, d2 = btn_w - 0.4, h = 1.5 + eps);
    }
}

module lid() {
    difference() {
        union() {
            translate([0, 0, lid_z]) linear_extrude(wall) outline();
            lid_rim();
            for (p = plugs) plug_at(p) plug_cradle(p[0]);
            // posts: thin tip, cone to the lid, trimmed to the rim's
            // outside so the cone stays clear of the base walls
            intersection() {
                for (p = posts) translate([p[0], p[1], pcb_z1 + 0.1]) {
                    cylinder(d = post_d, h = lid_z - pcb_z1);
                    translate([0, 0, post_stem - 0.1])
                        cylinder(d1 = post_d, d2 = post_root_d, h = lid_z - pcb_z1 - post_stem + 0.1 + eps);
                }
                linear_extrude(W) offset(delta = -rim_clr) cavity();
            }
        }
        for (b = buttons) {
            // slot through the plate around the tongue, and the tongue
            // thinned from the cavity side
            translate([0, 0, lid_z - 1]) linear_extrude(W - lid_z + 2) button_slot(b);
            translate([0, 0, lid_z - 1]) linear_extrude(W - btn_t - lid_z + 1) button_tongue(b);
            button_label(b);
        }
    }
    for (b = buttons) button_plunger(b);
}

module button_label(b) {
    // Engraved behind the slot (towards -X): in front the lid ends at
    // shoulder_x. Mirrored in X so that it reads correctly from outside
    // after real(), starting next to the slot.
    translate([b[0] - btn_off - btn_w / 2 - btn_slot - 1, b[1], W - 0.4]) mirror([1, 0, 0])
        linear_extrude(1) text(b[2], size = 2.5, halign = "left", valign = "center",
                               font = "Liberation Sans:style=Bold");
}

// ---- colour accents ------------------------------------------------------------
// Each part splits into body = part minus accent region, accent = part inside
// it, plus the fills of the engraved labels, which the part itself leaves out.

module fascia() {
    // The window face, acc_wd deep, minus the front labels: they stay in
    // the body colour, flush.
    difference() {
        intersection() {
            linear_extrude(W) outline();
            translate([front_x - acc_wd, -1, -1]) cube([acc_wd + 1, H + 2, W + 2]);
        }
        front_labels(acc_wd);
    }
}

module base_accent_region() { fascia(); }

module base_label_fills() {
    intersection() {
        for (p = plugs) plug_label(p, acc_wd);
        linear_extrude(lid_z) outline();
    }
}

module lid_accent_region() {
    fascia();
    translate([0, 0, W - acc_d]) linear_extrude(acc_d + 1) {
        // the window nose on the lid's outer face
        intersection() {
            outline();
            translate([shoulder_x, -1]) square([win_p + 1, H + 2]);
        }
        // button pads: the round end of each tongue
        for (b = buttons) translate([b[0] - btn_off, b[1]]) circle(d = btn_w);
    }
}

module lid_label_fills() {
    intersection() {
        for (b = buttons) button_label(b);
        translate([0, 0, lid_z]) linear_extrude(wall) outline();
    }
}

module base_body()   { difference() { base(); base_accent_region(); } }
module base_accent() { intersection() { base(); base_accent_region(); } base_label_fills(); }
module lid_body()    { difference() { lid(); lid_accent_region(); } }
module lid_accent()  { intersection() { lid(); lid_accent_region(); } lid_label_fills(); }

// ---- ghosts ------------------------------------------------------------------

module board_ghost(s = 0) {
    // s shrinks every box, so that parts merely touching (board on its
    // rails) drop out of the fit check.
    x0 = pcb_front_x - pcb_d;
    y0 = pcb_top_y - pcb_h;
    translate([x0 + s, y0 + s, pcb_z0 + s]) cube([pcb_d - 2 * s, pcb_h - 2 * s, pcb_t - 2 * s]);
    translate([pcb_front_x - s, pcb_tab_y0 + s, pcb_z0 + s])
        cube([pcb_tab_d, pcb_tab_y1 - pcb_tab_y0 - 2 * s, pcb_t - 2 * s]);
    for (p = board_parts) if (!p[7]) {
        z = p[1] > 0 ? pcb_z1 : pcb_z0 - p[6];
        if (p[0] == "J101") {
            // USB-C shell: a stadium (8.94 x 3.26), not a box, or its
            // corners collide with the flush opening around it
            h = 3.26 - 2 * s; w = (p[5] - p[4]) - 2 * s;
            translate([p[2] + s, (p[4] + p[5]) / 2, z + 3.26 / 2]) rotate([0, 90, 0])
                linear_extrude(p[3] - p[2] - 2 * s) hull() for (k = [-1, 1])
                    translate([0, k * (w - h) / 2]) circle(d = h);
        } else
            translate([p[2] + s, p[4] + s, z + s])
                cube([p[3] - p[2] - 2 * s, p[5] - p[4] - 2 * s, p[6] - 2 * s]);
    }
    for (p = board_pins) translate([p[0], p[1], pcb_z0 - board_pin_stub])
        cylinder(d = 1, h = board_pin_stub, $fn = 8);
}

module plug_ghost(xc, s = 0) {
    w = plug_w - 2 * s;
    body = plug_len - plug_mate_len;
    translate([xc - w / 2, plug_y0 + s, plug_z0 + s]) {
        cube([w, body - 2 * s, plug_h - 2 * s]);
        translate([0, body - s - eps, plug_h - plug_mate_h])
            cube([w, plug_mate_len, plug_mate_h - 2 * s]);
    }
}

module rail_ghost() {
    // TS35 x 7.5: brims against the mounting face, crown towards the wall.
    yb = rail_y - rail_w / 2;
    translate([0, 0, -5]) linear_extrude(W + 10) {
        for (y = [yb, yb + rail_w - 5]) translate([-brim_t, y]) square([brim_t, 5]);
        for (y = [yb + 5, yb + rail_w - 6]) translate([-7.5, y]) square([7.5 - brim_t, 1]);
        translate([-7.5, yb + 5]) square([1, rail_w - 10]);
    }
}

// ---- output ------------------------------------------------------------------

// The design frame is the mirror image of the real device (see the top of
// this file); real() turns it into the real one. All outputs go through it.
module real() { translate([0, 0, W]) mirror([0, 0, 1]) children(); }

// Print orientation: each part flat on its outer side wall. In the real
// device the lid's outer face is at Z = 0 already; the base is turned over
// about the X axis (a rotation, not a mirror).
if (part == "base") translate([0, H, W]) rotate([180, 0, 0]) real() base();
else if (part == "lid") real() lid();
else if (part == "base_body") translate([0, H, W]) rotate([180, 0, 0]) real() base_body();
else if (part == "base_accent") translate([0, H, W]) rotate([180, 0, 0]) real() base_accent();
else if (part == "lid_body") real() lid_body();
else if (part == "lid_accent") real() lid_accent();
// one keeper, flat on its back face; print two
else if (part == "keeper") rotate([-90, 0, 0]) keeper_shape();
else if (part == "colours") real() {   // assembled, body and accent colours
    color("DimGray") { base_body(); lid_body(); keepers(); }
    color(acc_colour) { base_accent(); lid_accent(); }
}
else if (part == "fit") real() {
    intersection() { union() { base(); lid(); keepers(); } board_ghost(0.05); }
    for (p = plugs) intersection() { union() { base(); lid(); keepers(); } plug_at(p) plug_ghost(p[0], 0.05); }
    // the keepers against the lid and the base: they must only touch
    intersection() { union() { base(); lid(); } keepers(0.05); }
}
else if (part == "open") real() {   // base with the board in it, lid off
    color("SlateGray") base();
    color("ForestGreen") board_ghost();
    color("LimeGreen") for (p = plugs) plug_at(p) plug_ghost(p[0]);
}
else if (part == "assembly") real() {
    color("SlateGray") base();
    color("LightGray", 0.6) lid();
    color("DarkOrange") keepers();
    color("ForestGreen") board_ghost();
    color("LimeGreen") for (p = plugs) plug_at(p) plug_ghost(p[0]);
    %rail_ghost();
}
