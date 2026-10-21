"""Draw the key curves from results.json as SVG files (no matplotlib needed)."""
import json, math, os

HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HERE, "results.json")))
COLORS = ["#d62728", "#1f77b4", "#2ca02c", "#9467bd", "#ff7f0e"]


def svg_plot(fname, title, series, xlabel, ylabel, logx=False, logy=False, xlim=None, ylim=None,
             vlines=(), w=720, h=360):
    L, Rm, T, B = 64, 16, 34, 46
    fx = (lambda v: math.log10(v)) if logx else (lambda v: v)
    fy = (lambda v: math.log10(max(v, 1e-12))) if logy else (lambda v: v)
    xs = [fx(x) for _, xx, _ in series for x in xx]
    ys = [fy(y) for _, _, yy in series for y in yy]
    x0, x1 = (fx(xlim[0]), fx(xlim[1])) if xlim else (min(xs), max(xs))
    y0, y1 = (fy(ylim[0]), fy(ylim[1])) if ylim else (min(ys), max(ys))
    pad = (y1 - y0) * 0.05 or 1
    if not ylim:
        y0, y1 = y0 - pad, y1 + pad
    px = lambda v: L + (fx(v) - x0) / (x1 - x0) * (w - L - Rm)
    py = lambda v: T + (y1 - fy(v)) / (y1 - y0) * (h - T - B)
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" font-family="sans-serif" font-size="11">',
         f'<rect width="{w}" height="{h}" fill="white"/>',
         f'<text x="{w/2}" y="18" text-anchor="middle" font-size="13" font-weight="bold">{title}</text>',
         f'<rect x="{L}" y="{T}" width="{w-L-Rm}" height="{h-T-B}" fill="none" stroke="#888"/>']

    def ticks(a, b, log):
        if log:
            return [10 ** e for e in range(math.floor(a), math.ceil(b) + 1)]
        step = 10 ** math.floor(math.log10((b - a) / 5))
        for m in (1, 2, 5, 10):
            if (b - a) / (step * m) <= 8:
                step *= m; break
        v = math.ceil(a / step) * step
        out = []
        while v <= b + 1e-12:
            out.append(round(v, 10)); v += step
        return out

    for v in ticks(x0, x1, logx):
        if x0 <= fx(v) <= x1:
            X = px(v)
            o.append(f'<line x1="{X}" y1="{T}" x2="{X}" y2="{h-B}" stroke="#eee"/>')
            o.append(f'<text x="{X}" y="{h-B+14}" text-anchor="middle">{v:g}</text>')
    for v in ticks(y0, y1, logy):
        if y0 <= fy(v) <= y1:
            Y = py(v)
            o.append(f'<line x1="{L}" y1="{Y}" x2="{w-Rm}" y2="{Y}" stroke="#eee"/>')
            o.append(f'<text x="{L-6}" y="{Y+4}" text-anchor="end">{v:g}</text>')
    for xv, lab in vlines:
        X = px(xv)
        o.append(f'<line x1="{X}" y1="{T}" x2="{X}" y2="{h-B}" stroke="#555" stroke-dasharray="4 3"/>')
        o.append(f'<text x="{X+3}" y="{T+12}" fill="#555">{lab}</text>')
    for i, (lab, xx, yy) in enumerate(series):
        pts = " ".join(f"{px(x):.1f},{py(min(max(fy(y), y0), y1) if not logy else y):.1f}"
                       for x, y in zip(xx, yy) if (fx(x) >= x0 and fx(x) <= x1))
        if logy:
            pts = " ".join(f"{px(x):.1f},{min(max(py(y), T), h-B):.1f}" for x, y in zip(xx, yy) if x0 <= fx(x) <= x1)
        else:
            pts = " ".join(f"{px(x):.1f},{min(max(py(y), T), h-B):.1f}" for x, y in zip(xx, yy) if x0 <= fx(x) <= x1)
        o.append(f'<polyline points="{pts}" fill="none" stroke="{COLORS[i % 5]}" stroke-width="1.4"/>')
        o.append(f'<text x="{L+10}" y="{T+16+14*i}" fill="{COLORS[i % 5]}">{lab}</text>')
    o.append(f'<text x="{(L+w-Rm)/2}" y="{h-10}" text-anchor="middle">{xlabel}</text>')
    o.append(f'<text x="14" y="{(T+h-B)/2}" text-anchor="middle" transform="rotate(-90 14 {(T+h-B)/2})">{ylabel}</text>')
    o.append("</svg>")
    open(os.path.join(HERE, fname), "w").write("\n".join(o))


c = R["rx_filter_curve"]
f = [x / 1e3 for x in c["f"]]
svg_plot("rx_filter.svg", "RX band-pass, bus to RX_ANA (U2 GBW 1 MHz)",
         [("R3/R4 100k (7ce317d; unstable, formal response)", f, c["100k"]),
          ("R3/R4 82k (board)", f, c["82k"])],
         "frequency [kHz]", "gain [dB]", logx=True, xlim=(20, 150), ylim=(-25, 16),
         vlines=[(52, "52k TX"), (60, "60k bus")])

c = R["tx_filter_curve"]
f = [x / 1e3 for x in c["f"]]
svg_plot("tx_filter.svg", "TX band-pass, GPIO4 to U1 output",
         [("R18/R19 100k (board)", f, c["100k"]), ("R18/R19 82k (upstream)", f, c["82k"])],
         "frequency [kHz]", "gain [dB]", logx=True, xlim=(20, 150), ylim=(-15, 5),
         vlines=[(52, "52k TX"), (60, "60k")])

ser = []
for k in R["kick"]:
    if k["gbw"] == "1meg" or True:
        ser.append((f"R3/R4 {k['r_rx']}, GBW {k['gbw']}", k["env_t_ms"], k["env_mV"]))
svg_plot("rx_kick.svg", "RX_ANA ringing after a 1 mV bus step (p-p per 50 us)",
         ser, "time [ms]", "RX_ANA p-p [mV]", logy=True, ylim=(1e-4, 5000))

w = R["rx_wave"]
svg_plot("rx_wave.svg", "RX, 60 kHz burst, 82k dividers, ~0.5 Vpp on the line",
         [("RX_ANA", w["t_us"], w["rx_ana"]), ("RX (GPIO6)", w["t_us"], w["rx"]),
          ("line AC (J1)", w["t_us"], w["line_ac"])], "time from burst start [us]", "V")

w = R["tx_wave"]
svg_plot("tx_wave.svg", "TX, 52 kHz, bus 100 ohm, codec MONOOUT high-Z",
         [("U3 out", w["t_us"], w["u3out"]), ("U1 out", w["t_us"], w["u1out"]),
          ("line AC at J1", w["t_us"], w["line_ac"]), ("BUS node AC (after bridge)", w["t_us"], w["busnode_ac"])],
         "time from TX start [us]", "V")

w = R["plugin_wave"]
svg_plot("plugin.svg", "Plug-in onto a 30 V bus (10 ohm source), board powered",
         [("+3.3V_ANA", w["t_ms"], w["v33a"]), ("codec AVDD", w["t_ms"], w["avdd"]),
          ("MONOOUT pin current / 100 [mA]", w["t_ms"], [x / 100 for x in w["imo_mA"]])],
         "time [ms]", "V", xlim=(0, 30))
print("plots written")
