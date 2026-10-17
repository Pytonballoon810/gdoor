"""JLCPCB production files for the DIN board: gerbers, drill, BOM, CPL.

Run with KiCad's own python (bennymeg's Fabrication Toolkit installed in KiCad 10's plugin dir):
  "C:/Program Files/KiCad/10.0/bin/python.exe" jlcfab.py <output_dir>

Works on a copy of the board in a temporary directory; the project files are never written.
On the copy, before the toolkit runs:
- every part gets an `FT Rotation Offset`. Parts with the board's own JLC offset field
  (JlcRotOffset / JLCPCB Rotation Offset) keep exactly that offset; the toolkit's -t pass adds its
  footprint-database value on top, so the field holds manual - db. Every other part gets the
  database correction alone.
- POS_OFFSET parts get an `FT Position Offset` (toolkit frame: footprint-local, y up, rotated by the
  footprint angle), for footprints whose origin differs from JLC's model.
- HAND_SOLDERED parts are marked DNP, which leaves them out of BOM and CPL like the DNP parts.
After it runs, the BOM columns are rewritten to JLC's template (Comment, Designator, Footprint,
LCSC Part #); with the toolkit's "Value"/"Quantity" columns the PCBA quote fails.

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
POS_OFFSET = {"J101": (0.0, 1.39)}
EXPECT = {"J101": (105.54, -108.0)}
HAND_SOLDERED = ["J103"]      # expansion header, no LCSC part
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
        if manual not in (None, ""):
            set_field(f, "FT Rotation Offset", str(float(manual) - db))
        if ref in POS_OFFSET:
            set_field(f, "FT Position Offset", "%g,%g" % POS_OFFSET[ref])
        if ref in HAND_SOLDERED:
            f.SetDNP(True)
    pcbnew.SaveBoard(path, board)


def run_toolkit(path):
    sys.argv = ["cli", "-p", path, "-nI", "-nB", "-e", "-t"]
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
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(BOM_COLUMNS)
        for r in rows:
            w.writerow([r["Value"], r["Designator"], r["Footprint"], r["LCSC Part #"]])
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
        got = (float(cpl[ref]["Mid X"]), float(cpl[ref]["Mid Y"]))
        if abs(got[0] - x) > 0.005 or abs(got[1] - y) > 0.005:
            problems.append("%s at %s, expected %s" % (ref, got, (x, y)))
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
