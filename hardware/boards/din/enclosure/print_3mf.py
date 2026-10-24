# Packs the base, the lid and the two plug keepers into one unsliced 3MF,
# gdoor-din.3mf, in both versions on two Bambu Studio plates; slice the plate
# you want to print:
#
#   plate 1  gdoor-din-base, gdoor-din-lid                 single colour, from
#                                                          gdoor-din-{base,lid}.stl
#   plate 2  gdoor-din-base-colour, gdoor-din-lid-colour   two colours, from
#                                                          gdoor-din-{base,lid}-{body,accent}.stl:
#                                                          two components, "body" and
#                                                          "accent", each a mesh object
#
# Both plates also carry gdoor-din-keeper-1 and -2, from gdoor-din-keeper.stl,
# in the body colour. Other slicers ignore the plates and show all eight
# objects side by side.
#
# Slicers that follow the 3MF core spec (Bambu Studio, OrcaSlicer,
# PrusaSlicer) load a component object as one object with one part per
# component, so the accents only need their filament picked. Geometry only,
# in mm, in the STLs' print orientation (moved, not turned): no printer,
# filament or process settings.
#
# Needs only the standard library.
# Usage: python print_3mf.py [stl_dir] [out_dir]   (both default to .)
import sys, os, re, zipfile

OUT = "gdoor-din.3mf"
HERE = os.path.dirname(os.path.abspath(__file__))
# Bambu Studio's settings for the file, which it cannot open without: the
# P1S 0.2 nozzle, 0.10mm Standard @BBL X1C 0.2 nozzle and Bambu PLA Basic
# @BBL X1C 0.2 nozzle twice (black, white). Written by Bambu Studio 2.6.1
# from those system profiles. A starting point only: pick your own presets
# when you slice.
SETTINGS = "bambu_project_settings.config"
# Two Bambu Studio plates: 1 single colour, 2 two colours. Bambu lays plates
# out in a row, each the bed width plus a fifth further along X.
PLATES = ["single colour", "two colours"]
PLATE_STRIDE = 256 * 1.2      # P1S bed 256 x 256 mm
# [object name, part, STL roles (None: the part's single-colour STL), plate,
# (x, y) offset on its plate]. Base and lid side by side, 10 mm apart,
# centred on the plate (base x -2.8 .. 60.6, lid x 0 .. 60.6, both y 0 .. 90),
# and the two plug keepers in front of them (each x -5.3 .. 5.3, y 0 .. 14.5),
# in the body colour on plate 2.
OBJECTS = [("gdoor-din-base", "base", [None], 1, (63.8, 83.0)),
           ("gdoor-din-lid", "lid", [None], 1, (134.4, 83.0)),
           ("gdoor-din-keeper-1", "keeper", [None], 1, (118.0, 58.0)),
           ("gdoor-din-keeper-2", "keeper", [None], 1, (138.0, 58.0)),
           ("gdoor-din-base-colour", "base", ["body", "accent"], 2, (63.8, 83.0)),
           ("gdoor-din-lid-colour", "lid", ["body", "accent"], 2, (134.4, 83.0)),
           ("gdoor-din-keeper-1", "keeper", [None], 2, (118.0, 58.0)),
           ("gdoor-din-keeper-2", "keeper", [None], 2, (138.0, 58.0))]

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
 <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
 <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>
</Types>
"""

RELS = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>
</Relationships>
"""

# Bambu Studio / OrcaSlicer name the parts after the object ("_2" for the
# second) and ignore the component objects' names, and plates are theirs
# alone; their own config file carries the part names, which object sits on
# which plate, and the filament per part (accent: filament 2).
NAMES = """<?xml version="1.0" encoding="UTF-8"?>
<config>
{objects}
{plates}
</config>
"""

PLATE = """ <plate>
  <metadata key="plater_id" value="{n}"/>
  <metadata key="plater_name" value="{name}"/>
{instances}
 </plate>"""

INSTANCE = """  <model_instance>
   <metadata key="object_id" value="{oid}"/>
   <metadata key="instance_id" value="0"/>
  </model_instance>"""

VERTEX = re.compile(r"vertex\s+(\S+)\s+(\S+)\s+(\S+)")


def read_stl(path):
    """ASCII STL to (vertices, triangles), sharing vertices that coincide."""
    coords = VERTEX.findall(open(path).read())
    assert coords and len(coords) % 3 == 0, path
    index, verts, tris = {}, [], []
    for i in range(0, len(coords), 3):
        tri = []
        for c in coords[i:i + 3]:
            if c not in index:
                index[c] = len(verts)
                verts.append(c)
            tri.append(index[c])
        if len(set(tri)) == 3:            # drop triangles that collapsed to a line
            tris.append(tri)
    return verts, tris


def mesh_object(oid, name, verts, tris):
    v = "\n".join(f'     <vertex x="{x}" y="{y}" z="{z}"/>' for x, y, z in verts)
    t = "\n".join(f'     <triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in tris)
    return (f'  <object id="{oid}" name="{name}" type="model">\n   <mesh>\n    <vertices>\n{v}\n'
            f'    </vertices>\n    <triangles>\n{t}\n    </triangles>\n   </mesh>\n  </object>\n')


def write_3mf(path, parts):
    """parts: [(name, plate, (dx, dy), [(role, verts, tris)])]; one mesh is a
    plain object, more are the components of one object."""
    objs, items, names, oid = "", [], [], 0
    on_plate = {n: [] for n in range(1, len(PLATES) + 1)}
    for name, plate, (dx, dy), meshes in parts:
        dx += (plate - 1) * PLATE_STRIDE
        if len(meshes) == 1:
            oid += 1
            objs += mesh_object(oid, name, *meshes[0][1:])
            names.append(f' <object id="{oid}">\n  <metadata key="name" value="{name}"/>\n'
                         f'  <metadata key="extruder" value="1"/>\n </object>')
        else:
            ids = []
            for role, v, t in meshes:
                oid += 1
                ids.append(oid)
                objs += mesh_object(oid, role, v, t)
            oid += 1
            comps = "\n".join(f'    <component objectid="{i}"/>' for i in ids)
            objs += (f'  <object id="{oid}" name="{name}" type="model">\n'
                     f'   <components>\n{comps}\n   </components>\n  </object>\n')
            pnames = "\n".join(f'  <part id="{i}" subtype="normal_part">\n'
                               f'   <metadata key="name" value="{role}"/>\n'
                               f'   <metadata key="extruder" value="{2 if role == "accent" else 1}"/>\n  </part>'
                               for i, (role, _, _) in zip(ids, meshes))
            names.append(f' <object id="{oid}">\n  <metadata key="name" value="{name}"/>\n'
                         f'  <metadata key="extruder" value="1"/>\n{pnames}\n </object>')
        items.append(f'  <item objectid="{oid}" transform="1 0 0 0 1 0 0 0 1 {dx:g} {dy:g} 0"/>')
        on_plate[plate].append(INSTANCE.format(oid=oid))
    plates = "\n".join(PLATE.format(n=n, name=PLATES[n - 1], instances="\n".join(inst))
                       for n, inst in on_plate.items())
    # Bambu Studio reads its plates only from files it takes for its own
    # project, which it tells by these two tags. Such a project must also
    # carry Metadata/project_settings.config, or Bambu Studio crashes on it.
    model = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             '<model unit="millimeter" xml:lang="en-US" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">\n'
             ' <metadata name="Application">BambuStudio-02.06.01.55</metadata>\n'
             ' <metadata name="BambuStudio:3mfVersion">1</metadata>\n'
             f' <resources>\n{objs} </resources>\n'
             f' <build>\n' + "\n".join(items) + '\n </build>\n</model>\n')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", RELS)
        z.writestr("3D/3dmodel.model", model)
        z.writestr("Metadata/model_settings.config", NAMES.format(objects="\n".join(names), plates=plates))
        z.write(os.path.join(HERE, SETTINGS), "Metadata/project_settings.config")


stl_dir = sys.argv[1] if len(sys.argv) > 1 else "."
out = sys.argv[2] if len(sys.argv) > 2 else "."
parts = []
for name, part, roles, plate, offset in OBJECTS:
    meshes = []
    for role in roles:
        stl = f"gdoor-din-{part}" + (f"-{role}" if role else "") + ".stl"
        v, t = read_stl(os.path.join(stl_dir, stl))
        meshes.append((role or name, v, t))
        print(f"{name}: {stl}: {len(v)} vertices, {len(t)} triangles")
    parts.append((name, plate, offset, meshes))
write_3mf(os.path.join(out, OUT), parts)
print("written", OUT)
