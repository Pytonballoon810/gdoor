# Writes gdoor-din-full.step: the whole device as assembled, in the real
# frame of gdoor-din-enclosure.step (X = depth, 0 on the rail; Y = height,
# 0 bottom; Z = width, the lid's outer face at 0):
#
#   - base, lid and both plug pairs, from gdoor-din-enclosure.step
#     (step_export.py), with their names and colours
#   - the board with all its parts, from a kicad-cli STEP export with J1 and
#     J4 left out (they stay unfitted, see README.md)
#   - mock wires: two from J4's holes to the 5 V plug, two from J1's holes
#     down to the bus plug. Insulated 1.6 mm, stripped 0.9 mm ends through
#     the board and into the plugs' wire entries.
#
# Every wire is checked against the base, the lid, the plugs and the board's
# parts, and the overlap is printed (it should be 0, apart from the stripped
# ends in the board's holes and the plugs' clamps, which are not checked).
#
# Needs OpenCascade's python bindings: pip install cadquery-ocp
# Usage, from this directory, after step_export.py:
#   python full_assembly.py <board.step> [out.step]
# with board.step from (PowerShell, in hardware/boards/din; the component
# list is every reference except J1 and J4):
#   & "C:\Program Files\KiCad\10.0\bin\kicad-cli.exe" pcb export step --force
#     --subst-models --user-origin 121.6x102.5mm --component-filter "<refs>"
#     -o board.step esp32.kicad_pcb
# No copper (tracks, pads, zones): with it the result is about 170 MB, over
# GitHub's 100 MB file limit; without it, about 42 MB.
import sys, math
from OCP.STEPCAFControl import STEPCAFControl_Reader, STEPCAFControl_Writer
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.XCAFDoc import XCAFDoc_DocumentTool, XCAFDoc_ColorType
from OCP.TDataStd import TDataStd_Name
from OCP.OCP.collections import Sequence_TDF_Label as TDF_LabelSequence
from OCP.TopLoc import TopLoc_Location
from OCP.Quantity import Quantity_Color, Quantity_TypeOfColor
from OCP.STEPControl import STEPControl_AsIs
from OCP.Interface import Interface_Static
from OCP.IFSelect import IFSelect_RetDone
from OCP.gp import gp_Trsf, gp_Ax1, gp_Ax2, gp_Pnt, gp_Dir, gp_Vec, gp_Circ
from OCP.OCP.collections import HArray1_gp_Pnt as TColgp_HArray1OfPnt
from OCP.GeomAPI import GeomAPI_Interpolate
from OCP.BRepBuilderAPI import (BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire,
                                BRepBuilderAPI_MakeFace, BRepBuilderAPI_Transform)
from OCP.BRepOffsetAPI import BRepOffsetAPI_MakePipe
from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID

# ---- board placement --------------------------------------------------------
# kicad-cli's STEP (--user-origin at the board centre, KiCad 121.6, 102.5):
# x = kx - 121.6, y = 102.5 - ky, the board's back side at z = 0, its
# component side at z = 1.6. In the real frame (board_export.py and real() in
# enclosure.scad): X = 152.4 - kx, Y = 147.5 - ky, the component side at
# Z = W - pcb_z1 = 28.1, facing the lid. That is a half turn about Y plus a
# shift.
W, PCB_Z1, PCB_T = 35.0, 6.9, 1.6
BOARD_FRONT = W - PCB_Z1          # component side, Z
BOARD_BACK = BOARD_FRONT + PCB_T  # back side, Z


def kx(x):  # KiCad x, y -> real X, Y
    return 152.4 - x


def ky(y):
    return 147.5 - y


# ---- wires ------------------------------------------------------------------
WIRE_D, CORE_D = 1.6, 0.9
ENTRY_Z = 5.8 + (5.9 + 9.4) / 2   # plugs' wire entries: flat side + entry centre
STRIP = 4.0                        # stripped length inside the wire entry
RED, BLACK = (0.80, 0.08, 0.08), (0.08, 0.08, 0.08)
WHITE, BLUE = (0.92, 0.92, 0.90), (0.10, 0.30, 0.80)
COPPER = (0.85, 0.50, 0.25)


def wires():
    """[(name, colour, pad (X, Y), insulation path, plug end (X, Y), +-1 the
    direction the wire goes into the entry along Y)]"""
    out = []
    # 5 V: J4 pads (KiCad 105.25 / 108.75, 64.5) to the top plug at x = 46,
    # wire end at Y = 74.8, entries facing -Y. The wire drops from the pad,
    # runs back over the plug (its screw face is at Z 16.8, the cradle's clip
    # fingers end at 16.3), turns down behind the plug clear of the RJ45
    # (its top ends at Y 65.3) and goes into the entry.
    for kxp, xe, name, col in [(108.75, 46 - 1.905, "5V +5V wire (J4 pin 2)", RED),
                               (105.25, 46 + 1.905, "5V GND wire (J4 pin 1)", BLACK)]:
        x, y = kx(kxp), ky(64.5)
        path = [(x, y, BOARD_FRONT - 1.0), (x, y, 24.0), ((x + xe) / 2, y - 3.5, 20.5),
                (xe, 75.8, 19.8), (xe, 71.3, 19.2), (xe, 69.1, 16.6), (xe, 70.3, 14.2),
                (xe, 72.3, ENTRY_Z), (xe, 75.8, ENTRY_Z)]
        out.append((name, col, (x, y), path, (xe, 75.8), +1))
    # Bus: J1 pads (KiCad 141.25 / 144.75, 64.5) down to the bottom plug at
    # x = 32 (turned half a turn, so its entries face +Y, wire end at
    # Y = 15.2). The wires drop to the entries' height and run diagonally
    # across the component side, under the lid, then straight down the
    # channel between the cradle's clip fingers.
    for kxp, xe, name, col in [(144.75, 32 - 1.905, "BUS wire (J1 pin 2)", BLUE),
                               (141.25, 32 + 1.905, "BUS wire (J1 pin 1)", WHITE)]:
        x, y = kx(kxp), ky(64.5)
        path = [(x, y, BOARD_FRONT - 1.0), (x, y, 19.0), (x + 0.8, y - 1.5, 14.6),
                (x + 2.0, y - 4.0, ENTRY_Z), (xe - 1.0, 40.0, ENTRY_Z), (xe, 34.0, ENTRY_Z),
                (xe, 25.0, ENTRY_Z), (xe, 14.2, ENTRY_Z)]
        out.append((name, col, (x, y), path, (xe, 14.2), -1))
    return out


def pipe(points, d):
    pts = TColgp_HArray1OfPnt(1, len(points))
    for i, p in enumerate(points):
        pts.SetValue(i + 1, gp_Pnt(*p))
    it = GeomAPI_Interpolate(pts, False, 1e-6)
    it.Perform()
    curve = it.Curve()
    spine = BRepBuilderAPI_MakeWire(BRepBuilderAPI_MakeEdge(curve).Edge()).Wire()
    p0, t0 = gp_Pnt(), gp_Vec()
    curve.D1(curve.FirstParameter(), p0, t0)
    circ = gp_Circ(gp_Ax2(p0, gp_Dir(t0)), d / 2)
    prof = BRepBuilderAPI_MakeFace(BRepBuilderAPI_MakeWire(BRepBuilderAPI_MakeEdge(circ).Edge()).Wire()).Face()
    mk = BRepOffsetAPI_MakePipe(spine, prof)
    mk.Build()
    return mk.Shape()


def rod(p, direction, length, d):
    return BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(*p), gp_Dir(*direction)), d / 2, length).Shape()


def volume(s):
    g = GProp_GProps()
    BRepGProp.VolumeProperties_s(s, g)
    return g.Mass()


def bbox(s):
    b = Bnd_Box()
    BRepBndLib.Add_s(s, b)
    return b


def solids(s):
    e = TopExp_Explorer(s, TopAbs_SOLID)
    while e.More():
        yield e.Current()
        e.Next()


# ---- assemble ---------------------------------------------------------------
board_path = sys.argv[1]
out_path = sys.argv[2] if len(sys.argv) > 2 else "gdoor-din-full.step"

doc = TDocStd_Document(TCollection_ExtendedString("MDTV-XCAF"))
st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
ct = XCAFDoc_DocumentTool.ColorTool_s(doc.Main())


def read_into(path):
    """Reads a STEP into doc; returns its new top-level labels."""
    before = TDF_LabelSequence()
    st.GetFreeShapes(before)
    rd = STEPCAFControl_Reader()
    rd.SetColorMode(True)
    rd.SetNameMode(True)
    assert rd.ReadFile(path) == IFSelect_RetDone, path
    assert rd.Transfer(doc), path
    after = TDF_LabelSequence()
    st.GetFreeShapes(after)
    old = {before.Value(i).Tag() for i in range(1, before.Length() + 1)}
    return [after.Value(i) for i in range(1, after.Length() + 1) if after.Value(i).Tag() not in old]


enclosure_labels = read_into("gdoor-din-enclosure.step")
board_labels = read_into(board_path)
print("enclosure labels:", len(enclosure_labels), " board labels:", len(board_labels))

# the board goes into a sub-assembly, placed by a location
t = gp_Trsf()
t.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 1, 0)), math.pi)
shift = gp_Trsf()
shift.SetTranslation(gp_Vec(kx(121.6), ky(102.5), BOARD_BACK))
t = shift.Multiplied(t)
board_assy = st.NewShape()
TDataStd_Name.Set_s(board_assy, TCollection_ExtendedString("gdoor-din board"))
for lab in board_labels:
    st.AddComponent(board_assy, lab, TopLoc_Location(t))

# obstacles for the wire check: the enclosure parts and the placed board's solids
obstacles = []
for lab in enclosure_labels:
    s = st.GetShape_s(lab)
    obstacles += list(solids(s))
board_solids = []
bb = Bnd_Box()
for lab in board_labels:
    placed = st.GetShape_s(lab).Moved(TopLoc_Location(t))
    board_solids += list(solids(placed))
    BRepBndLib.Add_s(placed, bb)
print(f"obstacles: {len(obstacles)} enclosure solids, {len(board_solids)} board solids")
print("board bbox: (%.2f, %.2f, %.2f) .. (%.2f, %.2f, %.2f)" % (*bb.CornerMin().Coord(), *bb.CornerMax().Coord()))

wire_assy = st.NewShape()
TDataStd_Name.Set_s(wire_assy, TCollection_ExtendedString("mock wires"))
total = 0.0
for name, col, (px, py), path, (ex, ey), sense in wires():
    ins = pipe(path, WIRE_D)
    # stripped ends: through the pad's hole and 1 mm past the back side; into the entry
    core_pad = rod((px, py, BOARD_FRONT - 1.0), (0, 0, 1), 1.0 + PCB_T + 1.0, CORE_D)
    core_plug = rod((ex, ey, ENTRY_Z), (0, sense, 0), STRIP, CORE_D)
    hit = 0.0
    wb = bbox(ins)
    for o in obstacles + board_solids:
        if bbox(o).IsOut(wb):
            continue
        v = volume(BRepAlgoAPI_Common(ins, o).Shape())
        if v > 1e-4:
            hit += v
    total += hit
    print(f"{name}: insulation overlap {hit:.4f} mm3, volume {volume(ins):.1f} mm3")
    for s, n, c in [(ins, name, col), (core_pad, name + " end at board", COPPER),
                    (core_plug, name + " end in plug", COPPER)]:
        lab = st.AddShape(s, False)
        TDataStd_Name.Set_s(lab, TCollection_ExtendedString(n))
        ct.SetColor(lab, Quantity_Color(*c, Quantity_TypeOfColor.Quantity_TOC_RGB),
                    XCAFDoc_ColorType.XCAFDoc_ColorSurf)
        st.AddComponent(wire_assy, lab, TopLoc_Location())
print(f"wires: total overlap {total:.4f} mm3")

st.UpdateAssemblies()
Interface_Static.SetCVal_s("write.step.unit", "MM")
Interface_Static.SetCVal_s("write.step.schema", "AP214IS")
wr = STEPCAFControl_Writer()
wr.SetColorMode(True)
wr.SetNameMode(True)
wr.Transfer(doc, STEPControl_AsIs)
assert wr.Write(out_path) == IFSelect_RetDone, out_path
print("written", out_path)
