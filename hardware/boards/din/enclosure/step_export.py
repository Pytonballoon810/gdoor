# Converts the OpenSCAD STLs into STEP solids: gdoor-din-base.step,
# gdoor-din-lid.step (print orientation, like the STLs) and
# gdoor-din-enclosure.step (base and lid in their assembled position).
#
# OpenSCAD 2021.01 cannot write STEP, so this sews the STL triangles into a
# closed solid and merges coplanar triangles into planar faces. Flat faces come
# out as single faces; round features stay faceted ($fn = 40).
#
# Needs OpenCascade's python bindings: pip install cadquery-ocp
# Usage: python step_export.py [stl_dir] [out_dir]   (both default to .)
import sys, os
from OCP.StlAPI import StlAPI_Reader
from OCP.TopoDS import TopoDS_Shape, TopoDS, TopoDS_Compound
from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing, BRepBuilderAPI_MakeSolid, BRepBuilderAPI_Transform
from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.TopAbs import TopAbs_SHELL, TopAbs_FACE
from OCP.TopExp import TopExp_Explorer
from OCP.gp import gp_Trsf, gp_Ax1, gp_Ax2, gp_Pnt, gp_Dir, gp_Vec
import math
from OCP.BRep import BRep_Builder
from OCP.STEPControl import STEPControl_Writer, STEPControl_AsIs
from OCP.Interface import Interface_Static
from OCP.IFSelect import IFSelect_RetDone

W = 35.0  # enclosure width
H = 90.0  # enclosure height; the base STL is turned 180 deg about y = H/2, z = W/2


def load_solid(path):
    mesh = TopoDS_Shape()
    assert StlAPI_Reader().Read(mesh, path), path
    sew = BRepBuilderAPI_Sewing(1e-4)
    sew.Add(mesh)
    sew.Perform()
    sewn = sew.SewedShape()
    ms = BRepBuilderAPI_MakeSolid()
    exp = TopExp_Explorer(sewn, TopAbs_SHELL)
    n = 0
    while exp.More():
        ms.Add(TopoDS.Shell(exp.Current()))
        n += 1
        exp.Next()
    solid = ms.Solid()
    # merge coplanar triangles into planar faces
    u = ShapeUpgrade_UnifySameDomain(solid, True, True, True)
    u.Build()
    return u.Shape(), n


def report(name, s):
    p = GProp_GProps()
    BRepGProp.VolumeProperties_s(s, p)
    b = Bnd_Box()
    BRepBndLib.Add_s(s, b)
    (x0, y0, z0), (x1, y1, z1) = b.CornerMin().Coord(), b.CornerMax().Coord()
    nf = 0
    e = TopExp_Explorer(s, TopAbs_FACE)
    while e.More():
        nf += 1
        e.Next()
    print(f"{name}: valid={BRepCheck_Analyzer(s).IsValid()} vol={p.Mass():.1f} mm3 faces={nf} "
          f"bbox=({x0:.2f},{y0:.2f},{z0:.2f})..({x1:.2f},{y1:.2f},{z1:.2f})")


def write(path, shape):
    w = STEPControl_Writer()
    Interface_Static.SetCVal_s("write.step.unit", "MM")
    Interface_Static.SetCVal_s("write.step.schema", "AP214IS")
    w.Transfer(shape, STEPControl_AsIs)
    assert w.Write(path) == IFSelect_RetDone, path


src = sys.argv[1] if len(sys.argv) > 1 else "."
out = sys.argv[2] if len(sys.argv) > 2 else "."
base_print, nb = load_solid(os.path.join(src, "gdoor-din-base.stl"))
lid, nl = load_solid(os.path.join(src, "gdoor-din-lid.stl"))
print("shells:", nb, nl)

# The lid STL is already in its assembled position (its outer face is the
# real device's Z = 0 side). The base is printed turned over: undo
# translate([0,H,W]) rotate([180,0,0]).
t = gp_Trsf()
t.SetRotation(gp_Ax1(gp_Pnt(0, H / 2, W / 2), gp_Dir(1, 0, 0)), math.pi)
base = BRepBuilderAPI_Transform(base_print, t, True).Shape()

report("base (print)", base_print)
report("base (assembled)", base)
report("lid", lid)

write(os.path.join(out, "gdoor-din-base.step"), base_print)
write(os.path.join(out, "gdoor-din-lid.step"), lid)
comp = TopoDS_Compound()
bb = BRep_Builder()
bb.MakeCompound(comp)
bb.Add(comp, base)
bb.Add(comp, lid)
write(os.path.join(out, "gdoor-din-enclosure.step"), comp)
print("written")
