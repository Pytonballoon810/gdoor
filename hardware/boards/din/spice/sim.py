"""SPICE testbenches for the GDoor DIN bus and audio front end.

Runs on KiCad's bundled ngspice.dll through ngs.py:
    "C:/Program Files/KiCad/10.0/bin/python.exe" sim.py
Writes results.json (numbers and decimated waveforms) next to this file.

The board (2026-10-21): R3/R4 = 82k, R18/R19 = 100k. Variants simulated:
  R3/R4 = 100k  as in 7ce317d..2026-10-21 (RX band-pass oscillates)
  R18/R19 = 82k as upstream (hardware/boards/esp32-mini, v4.0)
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ngs

MODELS = os.path.join(HERE, "models.lib")
FRONT = os.path.join(HERE, "frontend.cir")
OPTS = (".options reltol=1e-4 abstol=1e-10 vntol=1e-6 itl4=200 method=gear\n"
        # U6A has two stable DC states and RX_ANA idles ~15 mV above its threshold;
        # start the operating point in the nominal one (RX low).
        ".nodeset V(RX)=0.05\n")

VBUS = 26.0      # nominal bus DC (DESIGN.md: "up to about 30 V")
FCAR = 60e3      # bus carrier
FTX = 52e3       # TX_PWM_HZ
# R3/R4 (RX) and R18/R19 (TX) variants. Board since 2026-10-21: R3/R4 82k, R18/R19 100k;
# 7ce317d had R3/R4 at 100k too; upstream esp32-mini has all four at 82k.
DESIGNS = {"100k": "100k", "82k": "82k"}
DEFAULTS = {"RMO": "1meg", "GBW_U2": "1meg", "R_RX": "82k", "R_TX": "100k"}


class Aborted(RuntimeError):
    pass


def deck(body, front=FRONT, **p):
    par = " ".join(f"{k}={v}" for k, v in {**DEFAULTS, **p}.items())
    return (f"gdoor din\n.param {par}\n.include \"{MODELS}\"\n.include \"{front}\"\n"
            f"{OPTS}{body}\n.end")


def run(body, partial=False, **p):
    """Run a deck. Raises on errors and on aborted transients unless partial=True."""
    ngs.run(deck(body, **p))
    bad = [l for l in ngs.LOG if "rror" in l or "aborted" in l or "too small" in l]
    if bad and not partial:
        raise Aborted("\n".join(bad))
    return bad


def tv(*names):
    t = np.array(ngs.vec("time"))
    return t, [np.array(ngs.vec(n)) for n in names]


def falling_edges(t, v, lo=1.0, hi=2.3):
    """Count falling edges with hysteresis on a logic waveform."""
    state, times = v[0] > hi, []
    for ti, vi in zip(t, v):
        if state and vi < lo:
            state = False; times.append(ti)
        elif not state and vi > hi:
            state = True
    return len(times), times


def window(t, y, a, b):
    return y[(t >= a) & (t <= b)]


def thin(*arrs, n=1200):
    idx = np.linspace(0, len(arrs[0]) - 1, min(n, len(arrs[0]))).astype(int)
    return [np.asarray(a)[idx].tolist() for a in arrs]


R = {"designs": DESIGNS}

# ================================================================== 1. Stability, ideal op amp
# Sallen-Key band-pass: R1 into node A, C2 A-GND, C4 A-to-(+), Rb = Ra||Rb on (+),
# Rf from the output back to A, gain K = 1 + Rfb/(Rg1||Rg2).
# Denominator: s^2 C2 C4 + s [C4 (1/R1 + (1-K)/Rf) + (C2 + C4)/Rb] + (1/R1 + 1/Rf)/Rb
def sk_poles(r1, rf, rb, c2, c4, k):
    a2 = c2 * c4
    a1 = c4 * (1 / r1 + (1 - k) / rf) + (c2 + c4) / rb
    a0 = (1 / r1 + 1 / rf) / rb
    w0 = np.sqrt(a0 / a2)
    return {"f0_kHz": w0 / 2 / np.pi / 1e3, "Q": (w0 * a2 / a1) if a1 > 0 else -w0 * a2 / abs(a1),
            "damping_uS_per_100pF": a1 / 100e-12 * 1e6, "stable": bool(a1 > 0)}


def par(a, b):
    return a * b / (a + b)


STAGES = {
    "rx": dict(r1=130e3, rf=18e3, c2=100e-12, c4=100e-12, k=1 + 2.4e3 / par(5.1e3, 5.1e3)),
    "tx": dict(r1=130e3, rf=18e3, c2=100e-12, c4=100e-12, k=1 + 1e3 / par(5.1e3, 5.1e3)),
}
R["stability_ideal"] = {}
for stage, s in STAGES.items():
    for name, rv in DESIGNS.items():
        r = float(rv.rstrip("k")) * 1e3
        R["stability_ideal"][f"{stage}_{name}"] = sk_poles(rb=r / 2, **s)
# Boundary: R3 = R4 value at which the RX damping term crosses zero.
s = STAGES["rx"]
rb_crit = (s["c2"] + s["c4"]) / -(s["c4"] * (1 / s["r1"] + (1 - s["k"]) / s["rf"]))
R["stability_ideal"]["rx_R3R4_limit_k"] = 2 * rb_crit / 1e3

# Tolerance spread for the upstream 82k RX stage (ideal op amp): R 1 %, C 5 %.
rng = np.random.default_rng(1)
u = lambda tol, n: 1 + rng.uniform(-tol, tol, n)
N = 20000
r1, rf, c2, c4 = 130e3 * u(.01, N), 18e3 * u(.01, N), 100e-12 * u(.05, N), 100e-12 * u(.05, N)
k = 1 + 2.4e3 * u(.01, N) / par(5.1e3 * u(.01, N), 5.1e3 * u(.01, N))
for name, rv in DESIGNS.items():
    rb = par(float(rv.rstrip("k")) * 1e3 * u(.01, N), float(rv.rstrip("k")) * 1e3 * u(.01, N))
    a1 = c4 * (1 / r1 + (1 - k) / rf) + (c2 + c4) / rb
    a2, a0 = c2 * c4, (1 / r1 + 1 / rf) / rb
    q = np.sqrt(a0 / a2) * a2 / a1
    R["stability_ideal"][f"rx_{name}_tolerance"] = {
        "samples": N, "fraction_unstable": float((a1 <= 0).mean()),
        "Q_p5_p50_p95_of_stable": np.percentile(q[a1 > 0], [5, 50, 95]).tolist() if (a1 > 0).any() else None}

# ================================================================== 2. Stability, SPICE kick test
# 1 mV step on the bus, then watch RX_ANA ring: decay = stable, growth = oscillator.
def kick(r_rx, gbw):
    bad = run("""
VB SRC0 J1_2 DC 26
VK SRC SRC0 PWL(0 0 0.1m 0 0.1001m 0.001)
RBUS SRC J1_1 100
VTXEN TX_EN 0 0
VTX TX 0 0
.tran 0.2u 3m 0 0.2u
""", partial=True, R_RX=r_rx, GBW_U2=gbw)
    t, (rxa, rx) = tv("RX_ANA", "RX")
    edges = np.arange(0.12e-3, t[-1] - 50e-6, 50e-6)
    env = np.array([np.ptp(window(t, rxa, a, a + 50e-6)) for a in edges])
    ok = env > 1e-7
    # growth rate from the linear part (before clipping, above numerical noise)
    lin = ok & (env < 0.3)
    slope = np.polyfit(edges[lin], np.log(env[lin]), 1)[0] if lin.sum() > 3 else float("nan")
    return {"r_rx": r_rx, "gbw": gbw, "growth_per_ms": float(np.exp(slope * 1e-3)),
            "envelope_end_mV": float(env[-1] * 1e3), "rx_edges": falling_edges(t, rx)[0],
            "sim_end_ms": float(t[-1] * 1e3), "aborted": bool(bad),
            "env_t_ms": (edges * 1e3).tolist(), "env_mV": (env * 1e3).tolist()}


R["kick"] = [kick(rv, g) for rv in DESIGNS.values() for g in ("0.7meg", "1meg", "1.5meg")]

# ================================================================== 3. AC: RX filter
def ac_rx(front=FRONT, **p):
    run("""
VB SRC J1_2 DC 26 AC 1
RBUS SRC J1_1 100
VTXEN TX_EN 0 0
VTX TX 0 0
.ac dec 400 10k 200k
""", **p) if front == FRONT else ngs.run(deck("""
VB SRC J1_2 DC 26 AC 1
RBUS SRC J1_1 100
VTXEN TX_EN 0 0
VTX TX 0 0
.ac dec 400 10k 200k
""", front=front, **p))
    f = np.array(ngs.vec("frequency")).real
    return f, np.abs(np.array(ngs.vec("RX_ANA")) / np.array(ngs.vec("BUS")))


def filt_stats(f, h):
    db = 20 * np.log10(h)
    ipk = int(np.argmax(h))
    above = f[db >= db[ipk] - 3]
    return {"f_peak_kHz": float(f[ipk] / 1e3), "gain_peak_dB": float(db[ipk]),
            "gain_52k_dB": float(np.interp(52e3, f, db)), "gain_60k_dB": float(np.interp(60e3, f, db)),
            "bw3dB_kHz": [float(above.min() / 1e3), float(above.max() / 1e3)]}


R["rx_filter"], R["rx_filter_curve"] = {}, {}
for name, rv in DESIGNS.items():
    for g in ("0.7meg", "1meg", "1.5meg"):
        f, h = ac_rx(R_RX=rv, GBW_U2=g)
        R["rx_filter"][f"{name}_{g}"] = filt_stats(f, h)
        if g == "1meg":
            R["rx_filter_curve"]["f"] = f[::4].tolist()
            R["rx_filter_curve"][name] = (20 * np.log10(h))[::4].tolist()

# Monte Carlo over the RX filter parts (upstream 82k): R 1 %, C 5 %, uniform.
MC_PARTS = {"R1": 0.01, "C2": 0.05, "C4": 0.05, "R10": 0.01, "R3": 0.01, "R4": 0.01,
            "R5": 0.01, "R7": 0.01, "R12": 0.01}
src = open(FRONT).read()
tmp = os.path.join(os.environ.get("TEMP", HERE), "gdoor_mc.cir")
mc = []
for _ in range(100):
    lines = []
    for ln in src.splitlines():
        p = ln.split()
        if p and p[0] in MC_PARTS:
            p[3] = "{" + p[3].strip("{}") + f"*{1 + rng.uniform(-1, 1) * MC_PARTS[p[0]]:.5f}" + "}"
            ln = " ".join(p)
        lines.append(ln)
    open(tmp, "w").write("\n".join(lines))
    s = filt_stats(*ac_rx(front=tmp, R_RX="82k"))
    mc.append([s["f_peak_kHz"], s["gain_52k_dB"], s["gain_60k_dB"]])
mc = np.array(mc)
R["rx_filter_mc_upstream"] = {"runs": len(mc), **{
    k: [float(mc[:, i].min()), float(mc[:, i].mean()), float(mc[:, i].max())]
    for i, k in enumerate(["f_peak_kHz", "gain_52k_dB", "gain_60k_dB"])}}

# ================================================================== 4. AC: TX filter
R["tx_filter"], R["tx_filter_curve"] = {}, {}
for name, rv in DESIGNS.items():
    run("""
VB SRC J1_2 DC 26
RBUS SRC J1_1 100
VTXEN TX_EN 0 3.3
VTX TXS 0 DC 1.65 AC 1
RTX TXS TX 30
.ac dec 400 10k 200k
""", R_TX=rv, R_RX="82k")
    f = np.array(ngs.vec("frequency")).real
    u1 = np.abs(np.array(ngs.vec("U1OUT")))
    R["tx_filter"][name] = filt_stats(f, u1)
    R["tx_filter_curve"]["f"] = f[::4].tolist()
    R["tx_filter_curve"][name] = (20 * np.log10(u1))[::4].tolist()

# ================================================================== 5. RX comparator
ngs.run(f"""thr
.include "{MODELS}"
{OPTS}
V33 VDD33 0 3.3
VR RX_ANA 0 PWL(0 0 1m 3.3 2m 0)
R26 RX_ANA U6AN 4.7k
R28 RX U6AP 47k
R23 U6AP 0 10k
R24 U6AP R24B 10k
R25 VDD33 R24B 2.4k
R29 RX VDD33 10k
XU6A U6AP U6AN VDD33 0 RX CMP
.tran 0.2u 2m
.end""")
t, (vin, rx) = tv("RX_ANA", "RX")
up = float(vin[np.argmax((rx < 1.65) & (t < 1e-3))])
dn = float(vin[np.argmax((rx > 1.65) & (t > 1e-3))])
R["rx_comparator"] = {"threshold_rising_V": up, "threshold_falling_V": dn, "hysteresis_mV": (up - dn) * 1e3}

# Idle RX_ANA against the upper threshold under tolerances (DC, computed, not SPICE):
# R 1 %, LMV321 Vos +-7 mV (x1.94 noise gain), LM393 Vos +-5 mV. Positive margin
# means RX idles low (comparator sinking); negative means it idles high.
N = 20000
r3, r4, r5, r7, r12 = (v * u(.01, N) for v in (82e3, 82e3, 5.1e3, 5.1e3, 2.4e3))
r23, r24, r25, r28, r29 = (v * u(.01, N) for v in (10e3, 10e3, 2.4e3, 47e3, 10e3))
vp = 3.3 * r4 / (r3 + r4) + rng.uniform(-7e-3, 7e-3, N)
idle = vp + (vp - 3.3 * r7 / (r5 + r7)) * r12 / par(r5, r7)
thr = 3.3 * r23 / (r23 + par(r25 + r24, r29 + r28)) + rng.uniform(-5e-3, 5e-3, N)
marg = idle - thr
R["rx_idle_margin"] = {"mean_mV": float(marg.mean() * 1e3), "min_mV": float(marg.min() * 1e3),
                       "max_mV": float(marg.max() * 1e3), "fraction_idle_high": float((marg < 0).mean())}

# ================================================================== 6. RX sensitivity (upstream 82k)
def tran_rx(amp, fc=FCAR, rmo="1meg", r_rx="82k"):
    t0, t1 = 0.4e-3, 0.9e-3
    run(f"""
VB SRC0 J1_2 DC {VBUS}
BCAR SRC SRC0 V = {amp}*sin(2*3.14159*{fc}*(time-{t0}))*(time>{t0})*(time<{t1})
RBUS SRC J1_1 100
VTXEN TX_EN 0 0
VTX TX 0 0
.tran 0.1u 1.4m 0 0.1u
""", RMO=rmo, R_RX=r_rx)
    t, (busv, rxa, rx, j1, j2) = tv("BUS", "RX_ANA", "RX", "J1_1", "J1_2")
    n, times = falling_edges(t, rx)
    return {"fc_kHz": fc / 1e3, "amp_src_mV": amp * 1e3,
            "line_pp_mV": float(np.ptp(window(t, j1 - j2, t0 + 0.1e-3, t1)) * 1e3),
            "rx_ana_pp_V": float(np.ptp(window(t, rxa, t0 + 0.1e-3, t1))),
            "rx_edges": n, "carrier_cycles": round((t1 - t0) * fc),
            "edges_after_burst": sum(1 for x in times if x > t1),
            "ring_last_edge_us_after_burst": float((max(times) - t1) * 1e6) if times and max(times) > t1 else 0.0,
            }, (t, rxa, rx, j1 - j2)


R["rx_sweep"] = []
for fc in (FCAR, FTX):
    for a in (0.02, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0, 2.0):
        r, wav = tran_rx(a, fc)
        R["rx_sweep"].append(r)
        if fc == FCAR and a == 0.3:
            t, rxa, rx, line = wav
            m = (t > 0.38e-3) & (t < 1.1e-3)
            tt, ra, rr, ll = thin((t[m] - 0.4e-3) * 1e6, rxa[m], rx[m], line[m] - np.mean(window(t, line, 0.2e-3, 0.4e-3)), n=2500)
            R["rx_wave"] = {"t_us": tt, "rx_ana": ra, "rx": rr, "line_ac": ll}
R["rx_codec_lowZ"] = [tran_rx(a, rmo="5")[0] for a in (0.3, 1.0)]

# ================================================================== 7. TX transient
def tran_tx(rbus, rmo="1meg", r_tx="100k"):
    ten, t0, t1 = 0.2e-3, 1.0e-3, 1.0e-3 + 40 / FTX
    # GPIO4: 40 cycles of a 50 % square wave, 20 ns edges
    tr, per = 20e-9, 1 / FTX
    pwl = ["0 0"]
    for i in range(40):
        a = t0 + i * per
        pwl += [f"{a:.9g} 0", f"{a + tr:.9g} 3.3", f"{a + per / 2:.9g} 3.3", f"{a + per / 2 + tr:.9g} 0"]
    run(f"""
VB SRC J1_2 DC {VBUS}
RBUS SRC J1_1 {rbus}
VTXEN TX_EN 0 PWL(0 0 {ten} 0 {ten + 1e-6} 3.3)
VTX TXS 0 PWL({' '.join(pwl)})
RTX TXS TX 30
.tran 0.1u {t1 + 0.4e-3} 0 0.1u
""", RMO=rmo, R_TX=r_tx, R_RX="82k")
    t, (v5on, u3o, u1o, busv, iu1, imo, j1, j2) = tv(
        "V5ON", "U3OUT", "U1OUT", "BUS", "viu1#branch", "viesd_mo#branch", "J1_1", "J1_2")
    line = j1 - j2
    lpre = np.mean(window(t, line, 0.15e-3, ten))
    ls = window(t, line, t0 + 20 / FTX, t1)
    rise = t[np.argmax((t > ten) & (v5on > 0.9 * 4.98))] - ten
    res = {
        "rbus_ohm": rbus, "codec_rout": rmo, "R_TX": r_tx,
        "v5on_on_V": float(np.mean(window(t, v5on, t0 - 0.2e-3, t0))),
        "v5on_rise_0_90_us": float(rise * 1e6),
        "v5on_min_during_tx_V": float(window(t, v5on, t0, t1).min()),
        "u3out_min_max_V": [float(window(t, u3o, t0, t1).min()), float(window(t, u3o, t0, t1).max())],
        "u1out_min_max_V": [float(window(t, u1o, t0, t1).min()), float(window(t, u1o, t0, t1).max())],
        "u1_peak_current_mA": float(np.abs(window(t, iu1, t0, t1)).max() * 1e3),
        "line_carrier_pp_V": float(np.ptp(ls)),
        "line_carrier_min_max_V": [float(ls.min() - lpre), float(ls.max() - lpre)],
        "line_step_at_txen_mV": float(np.abs(window(t, line, ten, t0) - lpre).max() * 1e3),
        "busnode_carrier_pp_V": float(np.ptp(window(t, busv, t0 + 20 / FTX, t1))),
        "monoout_esd_peak_mA": float(np.abs(window(t, imo, t0, t1)).max() * 1e3),
    }
    return res, (t, v5on, u3o, u1o, line - lpre, busv - np.mean(window(t, busv, 0.15e-3, ten)), ten, t0)


R["tx_sweep"] = []
for rb in (30, 100, 300):
    for rmo in ("1meg", "5"):
        r, wav = tran_tx(rb, rmo)
        R["tx_sweep"].append(r)
        if rb == 100 and rmo == "1meg":
            t, v5on, u3o, u1o, lac, bac, ten, t0 = wav
            m = (t > t0 - 20e-6) & (t < t0 + 200e-6)
            tt, a, b, c, d = thin((t[m] - t0) * 1e6, u3o[m], u1o[m], lac[m], bac[m], n=2000)
            R["tx_wave"] = {"t_us": tt, "u3out": a, "u1out": b, "line_ac": c, "busnode_ac": d}
            m = (t > ten - 20e-6) & (t < ten + 300e-6)
            tt, a, b = thin((t[m] - ten) * 1e6, v5on[m], u1o[m])
            R["txen_wave"] = {"t_us": tt, "v5on": a, "u1out": b}
R["tx_sweep"].append(tran_tx(100, "1meg", "82k")[0])

# ================================================================== 8. Plug-in transient
def plugin(rbus, tx_en=0.0, vbus=30.0):
    run(f"""
VB SRC J1_2 PWL(0 0 0.5m 0 0.51m {vbus})
RBUS SRC J1_1 {rbus}
VTXEN TX_EN 0 {tx_en}
VTX TX 0 0
.tran 1u 40m 0 2u
""", R_RX="82k")
    t, (busv, avdd, v33a, v5on, imo, im1, iu1, adc) = tv(
        "BUS", "AVDD", "V33A", "V5ON", "viesd_mo#branch", "viesd_m1#branch", "viu1#branch", "BUS_DCVOLT")
    return {
        "rbus_ohm": rbus, "vbus_V": vbus, "tx_en": tx_en,
        "monoout_esd_peak_mA": float(np.abs(imo).max() * 1e3),
        "monoout_esd_charge_uC": float(np.trapezoid(np.abs(imo), t) * 1e6),
        "mic1p_esd_peak_mA": float(np.abs(im1).max() * 1e3),
        "u1out_pin_peak_mA": float(np.abs(iu1).max() * 1e3),
        "avdd_peak_V": float(avdd.max()), "v33ana_peak_V": float(v33a.max()),
        "v33ana_above_3V6_ms": float(((v33a > 3.6).sum()) * 0 + np.trapezoid((v33a > 3.6).astype(float), t) * 1e3),
        "v5on_peak_V": float(v5on.max()), "bus_dcvolt_peak_V": float(adc.max()),
    }, (t, busv, avdd, v33a, imo)


R["plugin"] = []
for rb in (10, 100):
    for txe in (0.0, 3.3):
        r, wav = plugin(rb, txe)
        R["plugin"].append(r)
        if rb == 10 and txe == 0.0:
            t, busv, avdd, v33a, imo = wav
            m = t < 30e-3
            tt, a, b, c, d = thin(t[m] * 1e3, busv[m], avdd[m], v33a[m], imo[m] * 1e3, n=2000)
            R["plugin_wave"] = {"t_ms": tt, "bus": a, "avdd": b, "v33a": c, "imo_mA": d}

# ================================================================== 9. Bus voltage divider (calc)
R["bus_divider"] = {f"{v}V": v * 10 / 110 for v in (20, 26, 30, 34)}

with open(os.path.join(HERE, "results.json"), "w") as fh:
    json.dump(R, fh, indent=1)

skip = ("_curve", "_wave")
summary = {k: v for k, v in R.items() if not k.endswith(skip)}
for kk in summary.get("kick", []):
    kk.pop("env_t_ms", None); kk.pop("env_mV", None)
print(json.dumps(summary, indent=1, default=float))
