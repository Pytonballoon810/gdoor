"""JLCPCB production files for the DIN board: gerbers, drill, BOM, CPL.

Run with KiCad's own python (bennymeg's Fabrication Toolkit installed in KiCad 10's plugin dir):
  "C:/Program Files/KiCad/10.0/bin/python.exe" jlcfab.py <output_dir>

Works on a copy of the board in a temporary directory; the project files are never written.
On the copy, before the toolkit runs:
- every part gets an `FT Rotation Offset`. Parts with the board's own JLC offset field
  (JlcRotOffset / JLCPCB Rotation Offset) keep exactly that offset; the toolkit's -t pass adds its
  footprint-database value on top, so the field holds manual - db. Every other part gets the
  database correction alone. ROT_OVERRIDE parts get a fixed final offset instead of either.
- POS_OFFSET parts get an `FT Position Offset` (toolkit frame: footprint-local, y up, rotated by the
  footprint angle), for footprints whose origin differs from JLC's model.
- HAND_SOLDERED parts are marked DNP, which leaves them out of BOM and CPL like the DNP parts.
After it runs, the BOM columns are rewritten to JLC's template (Comment, Designator, Footprint,
LCSC Part #); with the toolkit's "Value"/"Quantity" columns the PCBA quote fails.
The toolkit refills all zones (-f) before plotting, so a stale fill in the saved board cannot reach
the gerbers.

KiCad's python pops a modal wx dialog for every assert and log message. The toolkit's package
registers an ActionPlugin when imported after pcbnew, which asserts ("PgmOrNull()" failed in
register_action) outside the KiCad app. Both are switched off before anything else is imported.
"""
import wx
wx.DisableAsserts()
wx.Log.EnableLogging(False)
import pcbnew
pcbnew.ActionPlugin.register = lambda self: None

import csv
import importlib
import os
import runpy
import shutil
import sys
import tempfile
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGINS = os.path.join(os.path.expanduser("~"), "Documents", "KiCad", "10.0", "3rdparty", "plugins")
TOOLKIT = "com_github_bennymeg_JLC-Plugin-for-KiCad"
COPY = ["esp32.kicad_pcb", "esp32.kicad_pro", "esp32.kicad_dru", "esp32.kicad_sch", "mcu_eth.kicad_sch",
        "fp-lib-table", "sym-lib-table"]

# J101 (HRO TYPE-C-31-M-12, C165948): KiCad's origin is 4.045 mm from the pad row and 2.60 mm from the
# peg holes, JLC's (EasyEDA) 2.474 mm and 1.206 mm. Aligned on the peg holes the CPL point moves
# 1.39 mm toward the pad row: +X on this board, where J101 sits at -90 deg. In the toolkit's frame
# that is local +y. The run checks the resulting CPL value against EXPECT.
#
# U101 (ESP32-S3-WROOM-1): KiCad's origin is not the module centre, JLC's is; 3.63 mm along the
# module. U7/U103 (SOT-223): JLC's origin sits 0.18/0.05 mm toward the pin row. All three fitted
# on the pads of JLC's EasyEDA footprints.
POS_OFFSET = {"J101": (0.0, 1.39), "U101": (0.0, -3.627), "U7": (-0.18, 0.0), "U103": (-0.05, 0.0)}
EXPECT = {"J101": (97.09, -108.0), "U101": (135.0, -128.623), "U7": (142.82, -85.5)}

# Final JLC rotation minus the KiCad rotation, for parts where the toolkit's footprint database
# (which assumes KiCad's standard footprints) and the board's JlcRotOffset fields give the wrong
# answer. Each value comes from fitting JLC's EasyEDA footprint (pad numbers and pin names) onto
# the board's pads. Library:SOT-23 and Library:SOT-23-5 are drawn 180 deg from KiCad's standard
# ones; the EasyEDA SOT-23-6 of C2687116 is drawn turned 90 deg; J1's offset field (-180) put its
# pads crosswise.
ROT_OVERRIDE = {"Q1": 0, "Q2": 0, "U2": 0, "U3": 0, "D1": 0, "U102": -90, "J1": -90}
EXPECT_ROT = {"Q1": 90, "Q2": 90, "U2": 0, "U3": 0, "D1": 0, "U102": 270, "J1": 0, "U1": 180}
# Left off the JLC order and soldered by hand: J103 has no LCSC part; U101 (ESP32 module) cannot
# be placed in JLC's Economic PCBA; the rest are Extended parts that are easy to solder by iron,
# each saving JLC's $3 loading fee. J4 is the same terminal as J1. Y101 stays with JLC: its pads
# are under the part. The rotation and position entries above stay for these parts, in case they
# go back to JLC.
HAND_SOLDERED = ["J103", "U101", "J1", "J4", "J102", "U103", "U102", "U2", "U3", "C19", "C20", "C59"]
BOM_COLUMNS = ["Comment", "Designator", "Footprint", "LCSC Part #"]


def prepare(path, sys_path):
    sys.path.insert(0, sys_path)
    process = importlib.import_module(TOOLKIT + ".process")
    board = pcbnew.LoadBoard(path)
    pm = process.ProcessManager(board)

    def set_field(f, name, text):
        fld = pcbnew.PCB_FIELD(f, f.GetNextFieldOrdinal(), name)
        fld.SetText(text)
        fld.SetVisible(False)
        f.Add(fld)

    for f in board.GetFootprints():
        ref = f.GetReference()
        fields = {x.GetName(): x.GetText() for x in f.GetFields()}
        db = pm._get_rotation_from_db(str(f.GetFPID().GetLibItemName()), str(f.GetFPID().GetLibNickname()))
        manual = fields.get("JlcRotOffset") or fields.get("JLCPCB Rotation Offset")
        if ref in ROT_OVERRIDE:
            set_field(f, "FT Rotation Offset", str(ROT_OVERRIDE[ref] - db))
        elif manual not in (None, ""):
            set_field(f, "FT Rotation Offset", str(float(manual) - db))
        if ref in POS_OFFSET:
            set_field(f, "FT Position Offset", "%g,%g" % POS_OFFSET[ref])
        if ref in HAND_SOLDERED:
            f.SetDNP(True)
    pcbnew.SaveBoard(path, board)


def run_toolkit(path):
    sys.argv = ["cli", "-p", path, "-nI", "-nB", "-e", "-t", "-f"]
    try:
        runpy.run_module(TOOLKIT + ".cli", run_name="__main__")
    except SystemExit as e:
        if e.code not in (None, 0):
            raise
    # the CLI starts its ProcessThread and returns; wait for it to write production/
    for t in threading.enumerate():
        if t is not threading.main_thread():
            t.join()


def rewrite_bom(path):
    # Lines with the same LCSC part are merged: the toolkit groups by value text, so "4k7" and
    # "4.7k" end up as two lines, which JLC flags as "multiple lines matched to the same part".
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    merged = {}
    for r in rows:
        key = r["LCSC Part #"] or ("", r["Value"], r["Footprint"])
        if key in merged:
            merged[key]["Designator"] += ", " + r["Designator"]
        else:
            merged[key] = dict(r)
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(BOM_COLUMNS)
        for r in merged.values():
            refs = sorted((d.strip() for d in r["Designator"].split(",")),
                          key=lambda d: (d.rstrip("0123456789"), int(d[len(d.rstrip("0123456789")):] or 0)))
            w.writerow([r["Value"], ", ".join(refs), r["Footprint"], r["LCSC Part #"]])
    return rows


def check(prod):
    with open(os.path.join(prod, "positions.csv"), encoding="utf-8-sig", newline="") as fh:
        cpl = {r["Designator"]: r for r in csv.DictReader(fh)}
    with open(os.path.join(prod, "bom.csv"), encoding="utf-8-sig", newline="") as fh:
        bom = list(csv.DictReader(fh))
    bom_refs = {d.strip() for r in bom for d in r["Designator"].split(",")}
    problems = []
    if set(cpl) != bom_refs:
        problems.append("BOM/CPL designators differ: only BOM %s, only CPL %s"
                        % (sorted(bom_refs - set(cpl)), sorted(set(cpl) - bom_refs)))
    for r in bom:
        if not r["LCSC Part #"]:
            problems.append("no LCSC number: " + r["Designator"])
    for ref, (x, y) in EXPECT.items():
        if ref in HAND_SOLDERED:
            continue
        got = (float(cpl[ref]["Mid X"]), float(cpl[ref]["Mid Y"]))
        if abs(got[0] - x) > 0.005 or abs(got[1] - y) > 0.005:
            problems.append("%s at %s, expected %s" % (ref, got, (x, y)))
    for ref, rot in EXPECT_ROT.items():
        if ref in HAND_SOLDERED:
            continue
        if float(cpl[ref]["Rotation"]) % 360 != rot:
            problems.append("%s rotated %s, expected %s" % (ref, cpl[ref]["Rotation"], rot))
    lcsc = [r["LCSC Part #"] for r in bom if r["LCSC Part #"]]
    if len(lcsc) != len(set(lcsc)):
        problems.append("LCSC part on several BOM lines")
    for ref in HAND_SOLDERED:
        if ref in cpl or ref in bom_refs:
            problems.append(ref + " still in BOM/CPL")
    return problems, len(bom), len(cpl)


def main():
    out = os.path.abspath(sys.argv[1])
    work = tempfile.mkdtemp(prefix="gdoor-din-fab-")
    for name in COPY:
        shutil.copy(os.path.join(HERE, name), work)
    board = os.path.join(work, "esp32.kicad_pcb")
    prepare(board, PLUGINS)
    run_toolkit(board)
    prod = os.path.join(work, "production")
    rewrite_bom(os.path.join(prod, "bom.csv"))
    problems, nbom, ncpl = check(prod)
    os.makedirs(out, exist_ok=True)
    for name in ("bom.csv", "positions.csv", "designators.csv", "netlist.ipc"):
        shutil.copy(os.path.join(prod, name), out)
    shutil.copy(os.path.join(prod, "esp32.zip"), os.path.join(out, "gdoor_din_gerbers.zip"))
    shutil.rmtree(work)
    print("BOM lines %d, CPL parts %d -> %s" % (nbom, ncpl, out))
    for p in problems:
        print("PROBLEM:", p)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
