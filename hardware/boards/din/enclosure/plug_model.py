# Solid model of the 2-pole 3.81 mm pluggable terminal pair (15EDGK type,
# QUARKZMAN PCB-Klemmleiste kit) used for the 5 V and bus connections:
#
#   female: the 17 mm part in the lid cradle. Screw section, then a socket
#           shroud (7 mm high, flush with its flat side) whose mouth sits flush
#           in the housing's outer wall: two pockets with a pin in each. Drawn
#           without the side flanges with the screw holes.
#   male:   the 15 mm cable plug. Screw section, then a tongue on its flat side,
#           split into one prong per pole, that goes into the shroud: a contact
#           opening in each prong and a latch nib at the tip.
#
# Both have a slotted clamp screw and a box clamp per pole, a square wire
# entry under each screw and a test slot behind it. Sizes are taken off photos
# of the real parts, scaled by the 11 mm height: about +-0.3 mm, except the
# female's length (17 mm), which is measured. In the cradle its back face sits
# 15.2 mm in from the outer face (plug_back in enclosure.scad), so its mouth
# stands about 1.8 mm proud.
#
# Local frame of both parts: x across the poles (centred, pitch 3.81 mm), y from
# the wire end (y = 0) towards the mating end, z from the flat side (z = 0) to
# the screw face (z = 11). mated() puts the male in the female's frame.
#
# Needs OpenCascade's python bindings: pip install cadquery-ocp
# Usage: python plug_model.py [out_dir]   writes plug-3.81-2p-female.step,
#        plug-3.81-2p-male.step and plug-3.81-2p-mated.step (coloured)
import sys, os, math
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder, BRepPrimAPI_MakePrism
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace, BRepBuilderAPI_Transform
from OCP.gp import gp_Pnt, gp_Ax1, gp_Ax2, gp_Dir, gp_Vec, gp_Trsf

pitch    = 3.81
poles    = (-pitch / 2, pitch / 2)
w        = 8.35    # width of both parts (plug_w)
h        = 11.0    # height of both parts, flat side to screw face

# screw section, the same on both parts
screw_y  = 3.7     # screw axes from the wire end
well_d   = 2.8     # screw well
well_z   = 9.4     # well bottom = top of the wire entry
entry_w  = 3.0     # square wire entry, z 5.9 .. 9.4
entry_z0 = 5.9
entry_len = 6.3
test_y   = 1.0     # test slot centre from the wire end

# female (in the cradle)
f_len    = 17.0    # wire end to the shroud mouth
f_step   = 8.8     # wire end to the step down to the shroud
f_sh_h   = 7.0     # shroud height (plug_mate_h)
pocket_w = 2.9     # one pocket per pole
pocket_z = (1.2, 5.8)
pocket_d = 7.0
pin_t    = 0.64
pin_z    = 3.5
pin_tip  = 0.7     # pin tip inside the mouth

# male (cable plug)
m_len    = 15.0    # wire end to the tongue tip
m_step   = 8.3     # wire end to the tongue root
prong_w  = 2.7
prong_t  = 4.4
clr      = 0.1     # tongue in the pocket

GREEN = (0.13, 0.60, 0.25)
METAL = (0.78, 0.78, 0.74)


def box(x0, y0, z0, x1, y1, z1):
    return BRepPrimAPI_MakeBox(gp_Pnt(x0, y0, z0), gp_Pnt(x1, y1, z1)).Shape()


def zcyl(x, y, z0, d, length):
    return BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(x, y, z0), gp_Dir(0, 0, 1)), d / 2, length).Shape()


def xprism(pts, x0, x1):
    """Prism along x from x0 to x1 over a polygon given as (y, z) points."""
    poly = BRepBuilderAPI_MakePolygon()
    for y, z in pts:
        poly.Add(gp_Pnt(x0, y, z))
    poly.Close()
    face = BRepBuilderAPI_MakeFace(poly.Wire()).Face()
    return BRepPrimAPI_MakePrism(face, gp_Vec(x1 - x0, 0, 0)).Shape()


def cut(a, *bs):
    for b in bs:
        a = BRepAlgoAPI_Cut(a, b).Shape()
    return a


def fuse(a, *bs):
    for b in bs:
        a = BRepAlgoAPI_Fuse(a, b).Shape()
    return a


def moved(shape, t):
    return BRepBuilderAPI_Transform(shape, t, True).Shape()


def screw_section(body, tag):
    """Cuts the screw wells, wire entries and test slots into body (screw face at
    z = h, wire end at y = 0) and returns it with the screws and box clamps."""
    metal = []
    for i, x in enumerate(poles):
        body = cut(body,
                   zcyl(x, screw_y, well_z, well_d, h - well_z + 0.01),
                   zcyl(x, screw_y, h - 0.4, 3.4, 0.41),                        # figure-8 rim recess
                   box(x - entry_w / 2, -0.01, entry_z0, x + entry_w / 2, entry_len, well_z),
                   box(x - 0.3, test_y - 0.5, well_z - 0.01, x + 0.3, test_y + 0.5, h + 0.01))
        # box clamp: a square tube in the wire entry, the screw through its roof
        cage = cut(box(x - 1.45, 0.6, entry_z0 + 0.05, x + 1.45, 6.0, well_z - 0.05),
                   box(x - 1.15, 0.59, entry_z0 + 0.35, x + 1.15, 6.01, well_z - 0.35),
                   zcyl(x, screw_y, well_z - 0.4, 1.7, 0.5))
        head = cut(zcyl(x, screw_y, well_z, 2.4, 1.0),
                   box(x - 1.3, screw_y - 0.25, well_z + 0.6, x + 1.3, screw_y + 0.25, well_z + 1.01))
        screw = fuse(head, zcyl(x, screw_y, entry_z0 + 1.1, 1.5, well_z - entry_z0 - 1.1 + 0.01))
        metal += [(cage, f"{tag} clamp {i + 1}", METAL), (screw, f"{tag} screw {i + 1}", METAL)]
    body = cut(body, box(poles[0], screw_y - 1.0, h - 0.4, poles[1], screw_y + 1.0, h + 0.01))
    return body, metal


def female():
    """The part in the cradle, its shroud mouth at y = f_len."""
    body = fuse(box(-w / 2, 0, 0, w / 2, f_step, h),
                box(-w / 2, f_step - 0.01, 0, w / 2, f_len, f_sh_h))
    # wire end set back towards the flat side, 0.7 mm at the flat side
    body = cut(body, xprism([(-0.01, -0.01), (0.7, -0.01), (-0.01, 5.5)], -w / 2 - 1, w / 2 + 1))
    # groove across the flat side at the step
    body = cut(body, box(-w / 2 - 1, f_step - 0.25, -0.01, w / 2 + 1, f_step + 0.25, 0.4))
    tip = f_len - (m_len - m_step)    # where the male's tongue tip ends up
    pins = []
    for i, x in enumerate(poles):
        body = cut(body,
                   box(x - pocket_w / 2, f_len - pocket_d, pocket_z[0], x + pocket_w / 2, f_len + 0.01, pocket_z[1]),
                   # recess for the male's latch nib, in the pocket floor
                   box(x - pocket_w / 2, tip - 0.15, 0.5, x + pocket_w / 2, tip + 1.2, pocket_z[0] + 0.01),
                   # flat-side marks near the wire end
                   box(x - 0.35, 0.9, -0.01, x + 0.35, 2.2, 0.5),
                   box(x - pin_t / 2, 7.0, pin_z - pin_t / 2, x + pin_t / 2, f_len - pocket_d + 0.01, pin_z + pin_t / 2))
        pins.append((box(x - pin_t / 2, 7.0, pin_z - pin_t / 2, x + pin_t / 2, f_len - pin_tip, pin_z + pin_t / 2),
                     f"female pin {i + 1}", METAL))
    body, metal = screw_section(body, "female")
    return [(body, "female body", GREEN)] + metal + pins


def male():
    """The cable plug, tongue tip at y = m_len."""
    body = box(-w / 2, 0, 0, w / 2, m_step, h)
    zc = pin_z - pocket_z[0] - clr          # contact opening centre above the flat side
    for x in poles:
        prong = box(x - prong_w / 2, m_step - 0.01, 0, x + prong_w / 2, m_len, prong_t)
        prong = cut(prong, box(x - 0.55, m_len - 6.1, zc - 0.55, x + 0.55, m_len + 0.01, zc + 0.55))
        # latch nib under the tip, with a lead-in ramp
        nib = xprism([(m_len - 1.0, 0.01), (m_len - 1.0, -0.6), (m_len - 0.4, -0.6), (m_len, 0.01)],
                     x - 1.0, x + 1.0)
        body = fuse(body, prong, nib)
    body, metal = screw_section(body, "male")
    return [(body, "male body", GREEN)] + metal


def mated():
    """Both parts in the female's frame: the male turned end for end, its tongue
    in the pockets and its front face on the shroud mouth."""
    t = gp_Trsf()
    t.SetTranslation(gp_Vec(0, f_len + m_step, pocket_z[0] + clr))
    r = gp_Trsf()
    r.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), math.pi)
    t.Multiply(r)
    return female() + [(moved(s, t), n, c) for s, n, c in male()]


def write(path, parts):
    """STEP with names and colours; parts = [(shape, name, (r, g, b))]."""
    from OCP.TDocStd import TDocStd_Document
    from OCP.TCollection import TCollection_ExtendedString
    from OCP.XCAFDoc import XCAFDoc_DocumentTool, XCAFDoc_ColorType
    from OCP.TDataStd import TDataStd_Name
    from OCP.Quantity import Quantity_Color, Quantity_TypeOfColor
    from OCP.STEPCAFControl import STEPCAFControl_Writer
    from OCP.STEPControl import STEPControl_AsIs
    from OCP.Interface import Interface_Static
    from OCP.IFSelect import IFSelect_RetDone
    doc = TDocStd_Document(TCollection_ExtendedString("MDTV-XCAF"))
    st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    ct = XCAFDoc_DocumentTool.ColorTool_s(doc.Main())
    for shape, name, rgb in parts:
        lab = st.AddShape(shape, False)
        TDataStd_Name.Set_s(lab, TCollection_ExtendedString(name))
        ct.SetColor(lab, Quantity_Color(*rgb, Quantity_TypeOfColor.Quantity_TOC_RGB), XCAFDoc_ColorType.XCAFDoc_ColorSurf)
    Interface_Static.SetCVal_s("write.step.unit", "MM")
    Interface_Static.SetCVal_s("write.step.schema", "AP214IS")
    wr = STEPCAFControl_Writer()
    wr.SetColorMode(True)
    wr.SetNameMode(True)
    wr.Transfer(doc, STEPControl_AsIs)
    assert wr.Write(path) == IFSelect_RetDone, path


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    write(os.path.join(out, "plug-3.81-2p-female.step"), female())
    write(os.path.join(out, "plug-3.81-2p-male.step"), male())
    write(os.path.join(out, "plug-3.81-2p-mated.step"), mated())
    print("written")
