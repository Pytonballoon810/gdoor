// GDoor DIN enclosure: 2 modules (35 mm), DIN 43880 style front, TS35 clip.
//
// Coordinates (mm):
//   X = depth: 0 is the mounting face on the rail, the front window is at +X
//   Y = height on the panel: 0 bottom, 90 top
//   Z = width: 0 is the outside of the base's side wall, the lid closes at +Z
//
// The PCB stands on edge, parallel to the side walls, component side
// towards the lid. Its front edge (RJ45, USB-C, LEDs) faces the window.
//
// Parts (set `part` or use -D part="..."):
//   "base"     tub: side wall, perimeter, DIN clip, board rails
//   "lid"      flat side wall with rim, hold-down posts, button tubes and
//              the clip cradles for the 5 V and bus plugs
//   "assembly" both, plus the board and the plugs as ghosts
//   "open"     the base with board and plugs, lid off
//   "fit"      everything that collides with the board (must render empty)
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
// len = wire entry to mating end. The mating end is lower than the screw
// section; that step bears against the inside of the top wall and stops
// the plug being pulled out. Outer size from the QUARKZMAN listing
// (female 8 x 11 x 15 mm, male 8 x 11 x 18 mm). The mating section
// (plug_mate_len, plug_mate_h) is not in the listing and is still an
// estimate: measure it.
plugs         = [[46, 1, "5V"], [42, 0, "BUS"]];   // [x centre, 1 = top / 0 = bottom, label]
plug_w        = 8.0;    // listing: female 8 x 11 x 15 mm
plug_h        = 11.0;
plug_len      = 15.0;
plug_mate_len = 9.0;    // length of the lower mating section
plug_mate_h   = 8.0;    // its height (flush with the side opposite the screws)
plug_clr      = 0.25;
plug_z1      = lid_z - 4;          // flat side (no screws), towards the lid
plug_z0       = plug_z1 - plug_h;   // screw side, towards the board
plug_y_step   = H - wall;           // step sits against the top wall
plug_y0       = plug_y_step - (plug_len - plug_mate_len);   // wire end
plug_y1       = plug_y0 + plug_len;                         // mating end
// Retention clip: a snap finger in each cradle side wall, cut free by a
// slot, with a lip that catches the edge of the screw-side face. The plug
// presses in from the board side and clicks in; spread the fingers to take
// it out.
clip_w        = 4.0;    // finger width along Y, at the step end of the body
clip_slot     = 0.5;    // slot between the finger and the rest of the wall
clip_lip      = 0.5;    // overlap with the screw-side face (beside the screws)
clip_lead     = 1.2;    // lead-in chamfer height

// ---- lid features ------------------------------------------------------------
// RESET (SW101, ESP_EN) and BOOT (SW102, IO0), top-actuated, poked through
// the lid.
buttons   = [[44.0, 23.0, "RST"], [44.0, 14.0, "BOOT"]];
btn_top_z = pcb_z1 + 1.6;
// Hold-down posts on free board spots (checked against the courtyards).
posts     = [[3.8, 86.0], [4.0, 45.0], [4.0, 4.0], [50.5, 6.0], [35.5, 86.0]];
post_d    = 2.6;
rim_t     = 1.2;
rim_h     = 3;
rim_clr   = 0.2;
snap_y    = [[12, 0], [32, 0], [12, 1], [32, 1]];   // [x, 0=bottom/1=top]

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

module front_labels() {
    // Engraved on the window face, reading across the width.
    d = 0.4;
    module lbl(t, y, z) {
        translate([front_x - d, y, z]) rotate([0, 90, 0])
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

module plug_notch(xc) {
    // Slot in the top wall for the mating section, open towards the lid so
    // the plug drops in with the lid.
    c = plug_clr;
    translate([xc - plug_w / 2 - c, H - wall - 1, plug_z1 - plug_mate_h - c])
        cube([plug_w + 2 * c, wall + 2, lid_z - (plug_z1 - plug_mate_h - c) + eps]);
}

module plug_label(p) {
    // Engraved on the outer face, centred on the plug slot.
    z = plug_z1 - plug_mate_h - plug_clr - 3.5;
    if (p[1] == 1) translate([p[0], H - 0.4, z]) rotate([-90, 0, 0]) linear_extrude(1)
        text(p[2], size = 3, halign = "center", valign = "center", font = "Liberation Sans:style=Bold");
    else translate([p[0], 0.4, z]) rotate([90, 0, 0]) linear_extrude(1)
        text(p[2], size = 3, halign = "center", valign = "center", font = "Liberation Sans:style=Bold");
}

module snap_grooves() {
    for (s = snap_y) {
        y = s[1] == 0 ? wall - 0.5 : H - wall - eps;
        translate([s[0] - 3.5, y, lid_z - rim_h + 1]) cube([7, 0.5 + eps, 1.0]);
    }
}

module base() {
    difference() {
        union() {
            linear_extrude(lid_z) outline();
            linear_extrude(lid_z) top_hook();
        }
        translate([0, 0, wall]) linear_extrude(lid_z) cavity();
        front_openings();
        front_labels();
        for (p = plugs) { plug_at(p) plug_notch(p[0]); plug_label(p); }
        snap_grooves();
        latch_clearance();
    }
    // the back rail crosses the beam: cut it through its full height
    difference() { board_rails(); latch_clearance(wall + pcb_back_gap + 1); }
    latch();
}

// ---- lid -------------------------------------------------------------------

module lid_rim() {
    translate([0, 0, lid_z - rim_h]) linear_extrude(rim_h + eps) difference() {
        offset(delta = -rim_clr) cavity();
        offset(delta = -rim_clr - rim_t) cavity();
    }
    // snap bumps
    for (s = snap_y) {
        y = s[1] == 0 ? wall + rim_clr - 0.4 : H - wall - rim_clr;
        translate([s[0] - 3, y, lid_z - rim_h + 1.1]) cube([6, 0.4, 0.8]);
    }
}

module plug_cradle(xc) {
    c = plug_clr;
    x0 = xc - plug_w / 2 - c;
    x1 = xc + plug_w / 2 + c;
    t = 1.6;
    yw = plug_y0 - c - t;            // wire-end edge of the side walls
    fy = plug_y_step - clip_w;       // clip finger, up to the step end
    zc = plug_z0 - c;                // lip's catching face
    zt = zc - clip_lead;             // finger tip
    // side walls, each with a clip finger reaching past the screw side
    for (x = [x0 - t, x1]) difference() {
        union() {
            translate([x, yw, plug_z0 + 1])
                cube([t, plug_y_step - yw, lid_z - plug_z0 - 1 + eps]);
            translate([x, fy, zt]) cube([t, clip_w, plug_z0 + 1 - zt + eps]);
        }
        // the slot frees the finger up to the lid plate
        translate([x - 1, fy - clip_slot, zt - 1]) cube([t + 2, clip_slot, lid_z - zt + 1]);
    }
    // lips, chamfered on the side the plug comes in from
    translate([0, fy + clip_w, 0]) rotate([90, 0, 0]) linear_extrude(clip_w) {
        polygon([[x0 - eps, zc], [x0 + clip_lip, zc], [x0 - eps, zt]]);
        polygon([[x1 + eps, zc], [x1 - clip_lip, zc], [x1 + eps, zt]]);
    }
    // backer against the flat side, filling the top-wall slot above the plug
    translate([x0 + 0.15, plug_y0 - c, plug_z1 + c])
        cube([x1 - x0 - 0.3, H - (plug_y0 - c), lid_z - plug_z1 - c + eps]);
    // push-in stop under the wire end, on the screw side, clear of the
    // wire entries
    translate([x0 - t, plug_y0 - c - t, plug_z0 - 0.5])
        cube([x1 - x0 + 2 * t, t, 3]);
}

module lid() {
    difference() {
        union() {
            translate([0, 0, lid_z]) linear_extrude(wall) outline();
            lid_rim();
            for (p = plugs) plug_at(p) plug_cradle(p[0]);
            for (p = posts) translate([p[0], p[1], pcb_z1 + 0.1])
                cylinder(d = post_d, h = lid_z - pcb_z1);
            for (b = buttons) translate([b[0], b[1], btn_top_z + 1.5])
                cylinder(d = 4.6, h = lid_z - btn_top_z - 1.5 + eps);
        }
        for (b = buttons) {
            translate([b[0], b[1], 0]) cylinder(d = 2.2, h = W + 1);
            // left of the hole: to the right the lid ends at shoulder_x
            translate([b[0] - 3.5, b[1], W - 0.4]) linear_extrude(1)
                text(b[2], size = 2.5, halign = "right", valign = "center",
                     font = "Liberation Sans:style=Bold");
        }
    }
}

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

if (part == "base") base();
// print orientation: turned over about the X axis (a rotation, not a mirror,
// or the printed lid is the mirror image of the real one)
else if (part == "lid") translate([0, H, W]) rotate([180, 0, 0]) lid();
else if (part == "fit") {
    intersection() { union() { base(); lid(); } board_ghost(0.05); }
    for (p = plugs) intersection() { union() { base(); lid(); } plug_at(p) plug_ghost(p[0], 0.05); }
}
else if (part == "open") {   // base with the board in it, lid off
    color("SlateGray") base();
    color("ForestGreen") board_ghost();
    color("LimeGreen") for (p = plugs) plug_at(p) plug_ghost(p[0]);
}
else if (part == "assembly") {
    color("SlateGray") base();
    color("LightGray", 0.6) lid();
    color("ForestGreen") board_ghost();
    color("LimeGreen") for (p = plugs) plug_at(p) plug_ghost(p[0]);
    %rail_ghost();
}
