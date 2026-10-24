# Packs each part's body and accent STLs into one two-colour 3MF:
# gdoor-din-base-colour.3mf and gdoor-din-lid-colour.3mf.
#
# Each file holds one object, the part, made of two components: "body" and
# "accent", each a mesh object. Slicers that follow the 3MF core spec
# (Bambu Studio, OrcaSlicer, PrusaSlicer) load that as one object with two
# parts, so the accent only needs its filament picked. Geometry only, in mm,
# in the STLs' print orientation: no printer, filament or process settings.
#
# Needs only the standard library.
# Usage: python colour_3mf.py [stl_dir] [out_dir]   (both default to .)
import sys, os, re, zipfile

PARTS = ["base", "lid"]

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
# carries the part names. Names only: no extruder or other settings.
NAMES = """<?xml version="1.0" encoding="UTF-8"?>
<config>
 <object id="{top}">
  <metadata key="name" value="{name}"/>
{parts}
 </object>
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


def write_3mf(path, name, meshes):
    objs = "".join(mesh_object(i + 1, n, v, t) for i, (n, v, t) in enumerate(meshes))
    top = len(meshes) + 1
    comps = "\n".join(f'    <component objectid="{i + 1}"/>' for i in range(len(meshes)))
    model = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             '<model unit="millimeter" xml:lang="en-US" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">\n'
             f' <resources>\n{objs}  <object id="{top}" name="{name}" type="model">\n'
             f'   <components>\n{comps}\n   </components>\n  </object>\n </resources>\n'
             f' <build>\n  <item objectid="{top}"/>\n </build>\n</model>\n')
    parts = "\n".join(f'  <part id="{i + 1}" subtype="normal_part">\n'
                      f'   <metadata key="name" value="{n}"/>\n  </part>'
                      for i, (n, _, _) in enumerate(meshes))
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", RELS)
        z.writestr("3D/3dmodel.model", model)
        z.writestr("Metadata/model_settings.config", NAMES.format(top=top, name=name, parts=parts))


stl_dir = sys.argv[1] if len(sys.argv) > 1 else "."
out = sys.argv[2] if len(sys.argv) > 2 else "."
for part in PARTS:
    meshes = []
    for role in ("body", "accent"):
        v, t = read_stl(os.path.join(stl_dir, f"gdoor-din-{part}-{role}.stl"))
        meshes.append((role, v, t))
        print(f"{part} {role}: {len(v)} vertices, {len(t)} triangles")
    write_3mf(os.path.join(out, f"gdoor-din-{part}-colour.3mf"), f"gdoor-din-{part}", meshes)
print("written")
