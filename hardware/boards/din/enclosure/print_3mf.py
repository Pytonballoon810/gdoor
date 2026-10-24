# Packs the base and the lid into two unsliced 3MFs, each with both parts
# side by side on the plate:
#
#   gdoor-din.3mf         single colour, from gdoor-din-{base,lid}.stl: one
#                         object per part
#   gdoor-din-colour.3mf  two colours, from gdoor-din-{base,lid}-{body,accent}.stl:
#                         one object per part, made of two components, "body"
#                         and "accent", each a mesh object
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

# [part, (x, y) offset on the plate]: the two side by side, 10 mm apart,
# centred on the P1S's 256 x 256 mm plate (base x -2.8 .. 60.6, lid
# x 0 .. 60.6, both y 0 .. 90)
PARTS = [("base", (63.8, 83.0)), ("lid", (134.4, 83.0))]
# [output, STL roles per part; None is the part's own single-colour STL]
FILES = [("gdoor-din.3mf", [None]), ("gdoor-din-colour.3mf", ["body", "accent"])]

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
# second) and ignore the component objects' names; their own config file
# carries the part names. Names only: no extruder or other settings. Only
# written for the two-colour file.
NAMES = """<?xml version="1.0" encoding="UTF-8"?>
<config>
{objects}
</config>
"""

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
    """parts: [(name, (dx, dy), [(role, verts, tris)])]; one mesh is a plain
    object, more are the components of one object."""
    objs, items, names, oid = "", [], [], 0
    for name, (dx, dy), meshes in parts:
        if len(meshes) == 1:
            oid += 1
            objs += mesh_object(oid, name, *meshes[0][1:])
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
                               f'   <metadata key="name" value="{role}"/>\n  </part>'
                               for i, (role, _, _) in zip(ids, meshes))
            names.append(f' <object id="{oid}">\n  <metadata key="name" value="{name}"/>\n{pnames}\n </object>')
        items.append(f'  <item objectid="{oid}" transform="1 0 0 0 1 0 0 0 1 {dx} {dy} 0"/>')
    model = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             '<model unit="millimeter" xml:lang="en-US" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">\n'
             f' <resources>\n{objs} </resources>\n'
             f' <build>\n' + "\n".join(items) + '\n </build>\n</model>\n')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", RELS)
        z.writestr("3D/3dmodel.model", model)
        if names:
            z.writestr("Metadata/model_settings.config", NAMES.format(objects="\n".join(names)))


stl_dir = sys.argv[1] if len(sys.argv) > 1 else "."
out = sys.argv[2] if len(sys.argv) > 2 else "."
for fname, roles in FILES:
    parts = []
    for part, offset in PARTS:
        meshes = []
        for role in roles:
            stl = f"gdoor-din-{part}" + (f"-{role}" if role else "") + ".stl"
            v, t = read_stl(os.path.join(stl_dir, stl))
            meshes.append((role or part, v, t))
            print(f"{fname}: {stl}: {len(v)} vertices, {len(t)} triangles")
        parts.append((f"gdoor-din-{part}", offset, meshes))
    write_3mf(os.path.join(out, fname), parts)
    print("written", fname)
