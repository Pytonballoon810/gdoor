"""Interactive BOM with Part-DB storage and JLCPCB cost, for the DIN board.

    python partdb_ibom.py                          # production/gdoor_din, 5 boards
    python partdb_ibom.py --boards 10 --parts-json dump.json

Nobble's pipeline (Nobble/hardware/tools/production/partdb_bom.py), run on this
board's JLC BOM. Its matcher, suggestions and iBOM overlay are imported, not
copied: a fix there applies here. Only the adaptation lives in this file:

  - the BOM is JLC's template (`Comment` instead of `Value`), and some values
    carry a tolerance or rating the matcher does not read (`12.4k 1%`,
    `1n 2kV`, `120R@100MHz`): they are normalised for matching only;
  - every LCSC number is priced from JLCPCB's parts library (price ladder,
    basic/extended, attrition and minimum quantity);
  - `ibom-partdb.html` gets a cost panel: per BOM line, what JLC charges for it
    on an order of N boards (parts + the $3 extended-part fee), whether you own
    it and where it is. Tick lines to hand-solder and the panel totals the
    saving and prints the designators for jlcfab.py's HAND_SOLDERED list.

Reads `production/gdoor_din/bom.csv` and `ibom.html` (iBOM plugin); writes
`bom-partdb.csv` and `ibom-partdb.html` next to them, and `jlc-prices.json`
(the price snapshot, reused with --offline).

Part-DB credentials are nobble's (tools/.env.partdb there). Stdlib only.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENTRY = HERE / "production" / "gdoor_din"
NOBBLE = Path(os.environ.get("NOBBLE_PRODUCTION_TOOLS",
                             Path.home() / "Documents" / "Nobble" / "hardware" / "tools" / "production"))
JLC_SEARCH = "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList"
EXTENDED_FEE = 3.0          # USD per unique extended part per order (JLC's published fee)

sys.path.insert(0, str(NOBBLE))
try:
    import partdb_bom as nb
except ImportError:
    sys.exit(f"nobble's partdb_bom.py not found in {NOBBLE}; set NOBBLE_PRODUCTION_TOOLS")


def match_value(comment: str) -> str:
    """The BOM's comment as the matcher reads values: `1n 2kV` -> `1n/2000V`, `12.4k 1%` -> `12.4k`."""
    s = comment.split("@")[0].strip()
    s = re.sub(r"\s*\d+(?:\.\d+)?\s*%", "", s)
    m = re.fullmatch(r"(\S+)\s+(\d+(?:\.\d+)?)\s*(k?)V", s)
    if m:
        s = f"{m.group(1)}/{float(m.group(2)) * (1000 if m.group(3) else 1):g}V"
    return s


def difficulty(footprint: str) -> str:
    f = footprint.upper()
    if re.search(r"QFN|LQFP|DFN|BGA", f):
        return "hard"
    if "0402" in f or "SOT-353" in f or "SC-70" in f or "USB_C" in f:
        return "fiddly"
    return "easy"


def jlc_part(lcsc: str) -> dict:
    body = json.dumps({"keyword": lcsc, "currentPage": 1, "pageSize": 5}).encode()
    req = urllib.request.Request(JLC_SEARCH, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        items = json.load(resp)["data"]["componentPageInfo"]["list"] or []
    hit = next((i for i in items if i.get("componentCode") == lcsc), None)
    if hit is None:
        return {"found": False}
    return {
        "found": True,
        "type": "preferred" if hit.get("preferredComponentFlag") else hit.get("componentLibraryType"),
        "ladder": sorted([p["startNumber"], p["productPrice"]] for p in hit.get("componentPrices") or []),
        "loss": hit.get("lossNumber") or 0,
        "least": hit.get("leastPatchNumber") or 0,
        "stock": hit.get("stockCount"),
        "mpn": hit.get("componentModelEn") or "",
        "describe": hit.get("describe") or "",
        "url": hit.get("lcscGoodsUrl") or "",
    }


def line_cost(info: dict, qty: int, boards: int) -> float:
    """What JLC charges for one BOM line: attrition and minimum quantity included, fee excluded."""
    if not info.get("ladder"):
        return 0.0
    buy = max(qty * boards + info["loss"], info["least"])
    unit = info["ladder"][0][1]
    for start, price in info["ladder"]:
        if buy >= start:
            unit = price
    return buy * unit


_COST_CSS = """
.jlc-panel{font-size:12px;margin:2px 0 6px;border-left:3px solid #b45309;background:rgba(180,83,9,.07);padding:4px 6px}
.dark .jlc-panel{background:rgba(251,191,36,.10);border-left-color:#fbbf24}
.jlc-panel summary{cursor:pointer;font-weight:600}
.jlc-panel table{border-collapse:collapse;width:100%;margin-top:4px}
.jlc-panel th,.jlc-panel td{padding:1px 4px;text-align:left;border-bottom:1px solid rgba(128,128,128,.25);white-space:nowrap}
.jlc-panel td.num,.jlc-panel th.num{text-align:right}
.jlc-panel tr.owned td{background:rgba(22,163,74,.10)}
.jlc-panel .ext{color:#b45309;font-weight:600}.dark .jlc-panel .ext{color:#fbbf24}
.jlc-panel .hard{color:#b91c1c}.jlc-panel .fiddly{color:#a16207}.jlc-panel .easy{color:#15803d}
.jlc-panel code{font-size:11px;user-select:all}
.jlc-panel .wrap{max-height:45vh;overflow:auto}
"""

_COST_JS = r"""
(function () {
  var C = jlcCost;   // {boards, fee, lines: [...]}
  var picked = {};
  try { picked = JSON.parse(readStorage("jlc_handsolder") || "{}"); } catch (e) {}
  var boards = parseInt(readStorage("jlc_boards") || C.boards, 10) || C.boards;

  function cost(l) {
    if (!l.ladder.length) return 0;
    var buy = Math.max(l.qty * boards + l.loss, l.least), unit = l.ladder[0][1];
    l.ladder.forEach(function (p) { if (buy >= p[0]) unit = p[1]; });
    return buy * unit;
  }
  function fee(l) { return l.type === "expand" ? C.fee : 0; }
  function $(n) { return "$" + n.toFixed(2); }
  function td(tr, text, cls) { var d = document.createElement("td"); d.textContent = text; if (cls) d.className = cls; tr.appendChild(d); return d; }

  var panel = document.createElement("details");
  panel.className = "jlc-panel";
  panel.open = readStorage("jlc_open") !== "0";
  panel.ontoggle = function () { writeStorage("jlc_open", panel.open ? "1" : "0"); };

  function render() {
    var lines = C.lines.slice().sort(function (a, b) { return (cost(b) + fee(b)) - (cost(a) + fee(a)); });
    var total = 0, saved = 0, refs = [], fees = 0;
    lines.forEach(function (l) {
      var c = cost(l) + fee(l); total += c; fees += fee(l);
      if (picked[l.key]) { saved += c; refs = refs.concat(l.refs); }
    });
    panel.textContent = "";
    var sum = document.createElement("summary");
    sum.textContent = "JLC parts cost for " + boards + " boards: " + $(total) + " (incl. " + $(fees) +
      " extended fees)" + (saved ? " · hand-solder saves " + $(saved) + " → " + $(total - saved) : "");
    panel.appendChild(sum);

    var bar = document.createElement("div");
    bar.appendChild(document.createTextNode("Boards: "));
    var n = document.createElement("input");
    n.type = "number"; n.min = 1; n.value = boards; n.style.width = "4em";
    n.onchange = function () { boards = Math.max(1, parseInt(n.value, 10) || 1); writeStorage("jlc_boards", String(boards)); render(); };
    bar.appendChild(n);
    var own = document.createElement("button");
    own.textContent = "Tick owned parts";
    own.onclick = function () { C.lines.forEach(function (l) { if (l.owned) picked[l.key] = true; }); save(); };
    var clr = document.createElement("button");
    clr.textContent = "Clear";
    clr.onclick = function () { picked = {}; save(); };
    bar.appendChild(own); bar.appendChild(clr);
    bar.appendChild(document.createTextNode(" Prices from JLCPCB, " + C.priced + "; assembly and PCB fees not included."));
    panel.appendChild(bar);

    var wrap = document.createElement("div"); wrap.className = "wrap";
    var t = document.createElement("table");
    var h = t.insertRow();
    ["Hand", "Refs", "Value", "Pkg", "Solder", "Lib", "Qty/bd", "JLC cost", "Owned · location · stock"].forEach(function (x, i) {
      var th = document.createElement("th"); th.textContent = x; if (i === 6 || i === 7) th.className = "num"; h.appendChild(th);
    });
    lines.forEach(function (l) {
      var tr = t.insertRow();
      if (l.owned) tr.className = "owned";
      var cb = document.createElement("input"); cb.type = "checkbox"; cb.checked = !!picked[l.key];
      cb.onchange = function () { if (cb.checked) picked[l.key] = true; else delete picked[l.key]; save(); };
      td(tr, "").appendChild(cb);
      var r = td(tr, l.refs.length > 3 ? l.refs.slice(0, 3).join(", ") + " +" + (l.refs.length - 3) : l.refs.join(", "));
      r.title = l.refs.join(", ");
      td(tr, l.value).title = l.mpn + " — " + l.describe;
      td(tr, l.footprint.length > 12 ? l.footprint.slice(0, 11) + "…" : l.footprint).title = l.footprint;
      td(tr, l.difficulty, l.difficulty);
      td(tr, l.type === "expand" ? "extended" : l.type, l.type === "expand" ? "ext" : "");
      td(tr, String(l.qty), "num");
      td(tr, $(cost(l)) + (fee(l) ? " +" + $(fee(l)) : ""), "num");
      var o = td(tr, l.owned ? "✓ " + l.location + " · " + l.stock : (l.suggestion ? "≈ " + l.suggestion : "—"));
      o.title = l.owned ? l.part : "";
      if (l.owned && l.stock !== "unknown" && parseInt(l.stock, 10) < l.qty * boards) o.textContent += " (short for " + boards + ")";
    });
    wrap.appendChild(t);
    panel.appendChild(wrap);
    if (refs.length) {
      var out = document.createElement("div");
      out.appendChild(document.createTextNode("jlcfab.py: "));
      out.appendChild(Object.assign(document.createElement("code"), {
        textContent: "HAND_SOLDERED = " + JSON.stringify(["J103"].concat(refs)).replace(/,/g, ", ")}));
      panel.appendChild(out);
    }
  }
  function save() { writeStorage("jlc_handsolder", JSON.stringify(picked)); render(); }

  window.addEventListener("load", function () {
    var host = document.getElementById("bomdiv");
    if (host) { host.insertBefore(panel, host.firstChild); render(); }
  });
})();
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("entry", nargs="?", type=Path, default=ENTRY)
    ap.add_argument("--boards", type=int, default=5, help="order size the cost panel starts with (default 5)")
    ap.add_argument("--parts-json", type=Path, help="a saved Part-DB /api/parts dump instead of the server")
    ap.add_argument("--offline", action="store_true", help="reuse jlc-prices.json instead of asking JLCPCB")
    args = ap.parse_args()
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")

    if args.parts_json:
        raw = json.loads(args.parts_json.read_text(encoding="utf-8"))
        raw = raw.get("hydra:member", raw) if isinstance(raw, dict) else raw
    else:
        raw = nb.fetch_parts(*nb.load_env())
    parts = [nb.Part(p) for p in raw]

    with (args.entry / "bom.csv").open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    prices_file = args.entry / "jlc-prices.json"
    if args.offline:
        prices = json.loads(prices_file.read_text(encoding="utf-8"))
    else:
        prices = {"priced": datetime.now().strftime("%Y-%m-%d"), "parts": {}}
        for row in rows:
            lcsc = row["LCSC Part #"].strip()
            prices["parts"][lcsc] = jlc_part(lcsc)
        prices_file.write_text(json.dumps(prices, indent=1, ensure_ascii=False), encoding="utf-8")

    owned, suggestions, storage_by_ref, lines = [], {}, {}, []
    for row in rows:
        mrow = dict(row, Value=match_value(row["Comment"]))
        hits, how, note = nb.match_row(mrow, parts)
        sug = None if hits else nb.suggest(mrow, parts)
        refs = [r.strip() for r in row["Designator"].split(",") if r.strip()]
        info = prices["parts"].get(row["LCSC Part #"].strip(), {"found": False})
        locs = []
        for p in hits:
            for loc in p.locations() or ["(no location)"]:
                locs.append(loc if len(hits) == 1 else f"{loc} [{p.label()}]")
        short = "; ".join(l.split(" > ")[-1] for l in locs)
        if hits:
            owned += refs
        elif sug:
            sug["fromFootprint"] = nb.package_key(row["Footprint"])
            for r in refs:
                suggestions[r] = sug
        for r in refs:
            storage_by_ref[r] = short
        cost = line_cost(info, len(refs), args.boards)
        fee = EXTENDED_FEE if info.get("type") == "expand" else 0.0
        row.update({
            "Qty": len(refs), "JLC Type": info.get("type", "not found"),
            f"JLC Cost ({args.boards} boards, USD)": f"{cost:.2f}", "Extended Fee": f"{fee:.2f}",
            "Hand Solder": difficulty(row["Footprint"]),
            "Storage Location": "; ".join(locs), "Stock": "; ".join(p.stock() for p in hits),
            "Part-DB Part": "; ".join(p.label() for p in hits), "Part-DB ID": "; ".join(str(p.id) for p in hits),
            "Match": how if len(hits) <= 1 else f"{how}, {len(hits)} candidates", "Note": note,
            "Suggestion": f"{sug['to']} {sug['part']} ({sug['footprint']}): {sug['reason']}" if sug else "",
            "Suggestion Location": sug["location"] if sug else "",
        })
        lines.append({
            "key": row["LCSC Part #"].strip() + "|" + row["Designator"], "refs": refs, "qty": len(refs),
            "value": row["Comment"], "footprint": nb.package_key(row["Footprint"]) or row["Footprint"],
            "difficulty": difficulty(row["Footprint"]), "type": info.get("type", "?"),
            "ladder": info.get("ladder", []), "loss": info.get("loss", 0), "least": info.get("least", 0),
            "mpn": info.get("mpn", ""), "describe": info.get("describe", ""),
            "owned": bool(hits), "part": "; ".join(p.label() for p in hits), "location": short,
            "stock": "; ".join(p.stock() for p in hits),
            "suggestion": f"{sug['to']} {sug['footprint']} · {sug['location'].split(' > ')[-1]}" if sug else "",
        })

    with (args.entry / nb.OUT_CSV).open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    html = (args.entry / "ibom.html").read_text(encoding="utf-8")
    overlay = {"stamp": datetime.now().strftime("%Y%m%dT%H%M%S"), "owned": owned, "suggestions": suggestions}
    html = nb.ibom_with_storage(html, storage_by_ref, overlay)
    data = json.dumps({"boards": args.boards, "fee": EXTENDED_FEE, "priced": prices["priced"], "lines": lines},
                      ensure_ascii=False).replace("</", "<\\/")
    end = html.rindex("</body>")
    html = html[:end] + f"<style>{_COST_CSS}</style>\n<script>var jlcCost = {data};\n{_COST_JS}</script>\n" + html[end:]
    (args.entry / nb.OUT_IBOM).write_text(html, encoding="utf-8")

    # Summary, most expensive first.
    def total(l):
        return line_cost(l, l["qty"], args.boards) + (EXTENDED_FEE if l["type"] == "expand" else 0)
    grand = sum(total(l) for l in lines)
    print(f"{len(rows)} BOM lines, {sum(1 for l in lines if l['owned'])} owned in Part-DB ({len(parts)} parts); "
          f"JLC parts cost for {args.boards} boards ${grand:.2f}")
    for l in sorted(lines, key=total, reverse=True):
        mark = "OWN " if l["owned"] else ("sug " if l["suggestion"] else "    ")
        print(f"  {mark}${total(l):7.2f}  {l['type']:9} {l['difficulty']:6} {', '.join(l['refs'])[:28]:28} "
              f"{l['value'][:22]:22} {l['location'] or l['suggestion']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
