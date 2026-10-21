"""SPICE testbenches for the GDoor DIN Ethernet front end (W5500 + HR911105A).

    "C:/Program Files/KiCad/10.0/bin/python.exe" eth_sim.py
Writes eth_results.json and eth_*.svg next to this file.

Board parts are as in mcu_eth.kicad_sch (2026-10-21). The magjack's insides
(HR911105A) and the W5500 pins are models from typical figures, see MAGJACK
and the chip sources below; HanRun publishes no SPICE model.
"""
import json, math, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ngs
from plot import svg_plot

OPTS = ".options reltol=1e-4 abstol=1e-12 vntol=1e-7 method=gear\n"

# --- Board side (mcu_eth.kicad_sch) -----------------------------------------
# FB101 120R@100MHz 0603 (C14709): Rdc + (L || R || C), |Z(100 MHz)| ~ 125 ohm.
# Capacitors carry ESL 0.4 nH (0402) / 0.6 nH (0603, 0805) and 10 mohm ESR.
BOARD = """
* +3.3V rail (U103 output, 22u + 10u + 100n local) -> FB101 -> +3.3V_ETHA
V33 V33S 0 3.3
RSRC V33S V33 20m
RFBDC V33 FBM 0.25
LFB FBM AVDD 0.6u
RFB FBM AVDD 150
CFB FBM AVDD 1.5p
* +3.3V_ETHA decoupling: C112 10u, C113 1u, C114/C115/C119 100n
C112 AVDD c112a 10u
L112 c112a c112b 0.6n
R112E c112b 0 10m
C113 AVDD c113a 1u
L113 c113a c113b 0.4n
R113E c113b 0 10m
C114 AVDD c114a 100n
L114 c114a c114b 0.4n
R114E c114b 0 10m
C115 AVDD c115a 100n
L115 c115a c115b 0.4n
R115E c115b 0 10m
C119 AVDD c119a 100n
L119 c119a c119b 0.4n
R119E c119b 0 10m
* TX: R113/R112 0R, R115/R114 49.9 to +3.3V_ETHA, TCT via R116 10R + C120 22n
R113 TXP_CHIP TD_P 1m
R112 TXN_CHIP TD_N 1m
R115 AVDD TD_P 49.9
R114 AVDD TD_N 49.9
R116 AVDD TCT 10
C120 TCT 0 22n
* RX: C122/C121 {CRX} series, R120/R119 49.9 to RX_CM, C123 10n, RCT = RX_CM
C122 RD_P RXP_C {CRX}
C121 RD_N RXN_C {CRX}
R120 RXP_C RX_CM 49.9
R119 RXN_C RX_CM 49.9
C123 RX_CM 0 10n
R118 RXP_C RXP_CHIP 1m
R117 RXN_C RXN_CHIP 1m
* W5500 RX inputs: 5k to an internal 1.2 V bias, 3 pF (assumed)
VRXB RXB 0 1.2
RRXP RXP_CHIP RXB 5k
RRXN RXN_CHIP RXB 5k
CRXP RXP_CHIP 0 3p
CRXN RXN_CHIP 0 3p
* W5500 TX outputs: current sinks (sources added per test), 3 pF
CTXP TXP_CHIP 0 3p
CTXN TXN_CHIP 0 3p
"""

# --- HR911105A model ----------------------------------------------------------
# Per channel: 1CT:1CT transformer, OCL 350 uH (8 mA bias), 0.06 uH leakage and
# 3 pF interwinding capacitance per end, then a common-mode choke (100 uH, 0.02 uH
# leakage per winding, 1 pF). Leakage and capacitances are fitted so the jack alone
# (100 ohm on both sides) has the return loss and insertion loss typical of 10/100
# magjacks (Pulse H1102 / Bothhand TS6121 class): RL 20.5 dB at 30 MHz, 12 dB at
# 80 MHz, IL -0.4 dB at 100 MHz. HanRun's datasheet gives no such figures that
# could be read here. Line-side centre taps go
# through 75 ohm each to 1 nF / 2 kV to pin 8 (GND): the usual "Bob Smith"
# termination inside this class of magjack. Pins: 1 TD+, 2 TD-, 4 TCT, 3 RD+,
# 6 RD-, 5 RCT; RJ45 pins 1/2 = TX pair, 3/6 = RX pair.
def channel(n, chip_p, chip_n, chip_ct, line_p, line_n):
    q = 350e-6 / 4               # each half winding (L ~ N^2)
    k = 1 - 0.06e-6 / 350e-6     # 0.06 uH leakage on the whole winding
    return f"""
LP1{n} {chip_p} pc{n} {q}
LP2{n} pc{n} {chip_n} {q}
RPC{n} pc{n} {chip_ct} 0.3
LS1{n} s1{n} sc{n} {q}
LS2{n} sc{n} s2{n} {q}
K1{n} LP1{n} LP2{n} {k}
K2{n} LP1{n} LS1{n} {k}
K3{n} LP1{n} LS2{n} {k}
K4{n} LP2{n} LS1{n} {k}
K5{n} LP2{n} LS2{n} {k}
K6{n} LS1{n} LS2{n} {k}
CW1{n} {chip_p} s1{n} 3p
CW2{n} {chip_n} s2{n} 3p
RBS{n} sc{n} BS 75
LC1{n} s1{n} {line_p} 100u
LC2{n} s2{n} {line_n} 100u
KC{n} LC1{n} LC2{n} {1 - 0.02e-6 / 100e-6}
CC1{n} s1{n} {line_p} 1p
CC2{n} s2{n} {line_n} 1p
"""


MAGJACK = (channel("T", "TD_P", "TD_N", "TCT", "LTX_P", "LTX_N")
           + channel("R", "RD_P", "RD_N", "RX_CM", "LRX_P", "LRX_N")
           + "CBS BS 0 1n\n"
           # RJ45 pins float on the cable side; keep DC defined
           + "RLT1 LTX_P 0 100meg\nRLT2 LTX_N 0 100meg\nRLR1 LRX_P 0 100meg\nRLR2 LRX_N 0 100meg\n")


def deck(body, crx="6.8n"):
    return f"eth\n.param CRX={crx}\n{BOARD}{MAGJACK}{OPTS}{body}\n.end"


def run(body, **kw):
    ngs.run(deck(body, **kw))
    bad = [l for l in ngs.LOG if "rror" in l or "aborted" in l or "too small" in l]
    if bad:
        raise RuntimeError("\n".join(bad))


def port(p, n):
    """Balanced 100-ohm port driven with 1 V differential AC (+0.5/-0.5)."""
    return f"""
VPP sp 0 DC 0 AC 0.5
VPN sn 0 DC 0 AC 0.5 180
RPP sp {p} 50
RPN sn {n} 50
"""


def rl_mask(f):
    """IEEE 802.3 100BASE-TX (TP-PMD) return-loss limit, dB; 10BASE-T 15 dB 5-10 MHz."""
    f = f / 1e6
    return np.where(f < 2, np.nan, np.where(f <= 30, 16, np.where(f <= 60, 16 - 20 * np.log10(f / 30),
                    np.where(f <= 80, 10, np.nan))))


R = {}
FREQ = ".ac dec 100 10k 300meg"

# ================================================================== RX: return loss and transfer
def rx_ac(crx):
    run(port("LRX_P", "LRX_N") + "ITXP TXP_CHIP 0 0\nITXN TXN_CHIP 0 0\n" + FREQ, crx=crx)
    f = np.array(ngs.vec("frequency")).real
    vd = np.array(ngs.vec("LRX_P")) - np.array(ngs.vec("LRX_N"))
    i = -np.array(ngs.vec("vpp#branch"))
    z = vd / i
    gam = (z - 100) / (z + 100)
    rl = -20 * np.log10(np.abs(gam))
    chip = np.array(ngs.vec("RXP_CHIP")) - np.array(ngs.vec("RXN_CHIP"))
    # insertion: chip diff voltage relative to what a matched 100-ohm load would see (0.5 V)
    il = 20 * np.log10(np.abs(chip) / 0.5)
    return f, rl, il, np.abs(z)


def summary_rx(f, rl, il):
    m = rl_mask(f)
    ok = ~np.isnan(m)
    margin = rl[ok] - m[ok]
    def at(x, y): return float(np.interp(x, f, y))
    corner = f[np.argmax(il > il[np.argmin(np.abs(f - 10e6))] - 3)]
    return {"RL_dB_at_MHz": {str(x): at(x * 1e6, rl) for x in (1, 5, 10, 30, 60, 80, 100)},
            "RL_worst_margin_dB_2_80MHz": float(margin.min()),
            "RL_worst_margin_at_MHz": float(f[ok][np.argmin(margin)] / 1e6),
            "gain_dB_at_MHz": {str(x): at(x * 1e6, il) for x in (0.1, 0.5, 1, 10, 50, 100)},
            "low_corner_3dB_kHz": float(corner / 1e3)}


R["rx"], curves = {}, {}
for crx in ("6.8n", "1u"):      # 1u ~ caps replaced by a short, for comparison
    f, rl, il, z = rx_ac(crx)
    R["rx"][crx] = summary_rx(f, rl, il)
    curves[crx] = (f, rl, il)

# ================================================================== TX: return loss and transfer
run(port("LTX_P", "LTX_N") + "ITXP TXP_CHIP 0 0\nITXN TXN_CHIP 0 0\n" + FREQ)
f = np.array(ngs.vec("frequency")).real
z = (np.array(ngs.vec("LTX_P")) - np.array(ngs.vec("LTX_N"))) / -np.array(ngs.vec("vpp#branch"))
rl_tx = -20 * np.log10(np.abs((z - 100) / (z + 100)))
m = rl_mask(f); ok = ~np.isnan(m)
R["tx_return_loss"] = {"RL_dB_at_MHz": {str(x): float(np.interp(x * 1e6, f, rl_tx)) for x in (1, 5, 10, 30, 60, 80, 100)},
                       "RL_worst_margin_dB_2_80MHz": float((rl_tx[ok] - m[ok]).min()),
                       "RL_worst_margin_at_MHz": float(f[ok][np.argmin(rl_tx[ok] - m[ok])] / 1e6)}
curves["tx"] = (f, rl_tx)

# Chip differential current -> line voltage into a 100-ohm cable
run("""
RLD LTX_P LTX_N 100
ITXP TXP_CHIP 0 DC 0 AC 0.5
ITXN TXN_CHIP 0 DC 0 AC 0.5 180
""" + FREQ)
f = np.array(ngs.vec("frequency")).real
zt = np.abs(np.array(ngs.vec("LTX_P")) - np.array(ngs.vec("LTX_N")))   # V per A (diff)
R["tx_transimpedance_ohm"] = {str(x): float(np.interp(x * 1e6, f, zt)) for x in (0.1, 1, 10, 31.25, 62.5, 100)}
I_100 = 1.0 / float(np.interp(31.25e6, f, zt))    # A diff for 1 V peak on the line
R["tx_current_for_1V_peak_mA"] = I_100 * 1e3
curves["tx_zt"] = (f, zt)

# ================================================================== TX: MLT-3 transient
# 125 MBd MLT-3 from a scrambled (LFSR) bit stream, 3 ns edges; each pin sinks a
# bias plus half the signal current, sized for a 1 V peak line level at 31 MHz.
rng = np.random.default_rng(3)
nsym, T, tr = 1500, 8e-9, 3e-9
bits = rng.integers(0, 2, nsym)
lvl, state, seq = [0, 1, 0, -1], 0, []
for b in bits:
    if b:
        state = (state + 1) % 4
    seq.append(lvl[state])
ib = I_100 / 2
pwl_p, pwl_n = ["0 0"], ["0 0"]
for i, s in enumerate(seq):
    t = 200e-9 + i * T
    pwl_p += [f"{t:.4e} {pwl_p[-1].split()[1]}", f"{t + tr:.4e} {ib * (1 + s) / 2 * 2:.5f}"]
    pwl_n += [f"{t:.4e} {pwl_n[-1].split()[1]}", f"{t + tr:.4e} {ib * (1 - s) / 2 * 2:.5f}"]
run(f"""
RLD LTX_P LTX_N 100
ITXP TXP_CHIP 0 PWL({' '.join(pwl_p)})
ITXN TXN_CHIP 0 PWL({' '.join(pwl_n)})
.tran 0.2n {200e-9 + nsym * T:.4e} 0 0.2n
""")
t = np.array(ngs.vec("time"))
vl = np.array(ngs.vec("LTX_P")) - np.array(ngs.vec("LTX_N"))
avdd = np.array(ngs.vec("AVDD"))
# sample each symbol 6 ns after its edge; group by MLT-3 level
samp = np.array([np.interp(200e-9 + i * T + 6e-9, t, vl) for i in range(nsym)])
seq = np.array(seq)
late = np.arange(nsym) > 100
R["tx_mlt3"] = {
    "symbols": nsym, "chip_bias_mA_per_pin": ib * 1e3,
    "level_V_min_mean_max": {str(s): [float(samp[late & (seq == s)].min()), float(samp[late & (seq == s)].mean()),
                                      float(samp[late & (seq == s)].max())] for s in (-1, 0, 1)},
    "overshoot_V": float(np.abs(vl[t > 1e-6]).max()),
    "avdd_ripple_mVpp": float(np.ptp(avdd[t > 1e-6]) * 1e3),
}
m = (t > 2e-6) & (t < 2.4e-6)
curves["mlt3"] = ((t[m] - 2e-6) * 1e9, vl[m])

# ================================================================== +3.3V_ETHA filter
run("""
VAC V33S_AC 0 0
ITXP TXP_CHIP 0 0
ITXN TXN_CHIP 0 0
IAV AVDD 0 DC 0.08 AC 1
.ac dec 100 1k 300meg
""")
f = np.array(ngs.vec("frequency")).real
zav = np.abs(np.array(ngs.vec("AVDD")))
R["avdd_impedance"] = {"peak_ohm": float(zav.max()), "peak_at_kHz": float(f[np.argmax(zav)] / 1e3),
                       **{f"at_{x}MHz_ohm": float(np.interp(x * 1e6, f, zav)) for x in (1, 25, 100)}}
curves["zav"] = (f, zav)
# supply noise on +3.3V -> +3.3V_ETHA
ngs.run(deck("ITXP TXP_CHIP 0 0\nITXN TXN_CHIP 0 0\nIAV AVDD 0 0.08\n.ac dec 100 1k 300meg").replace(
    "V33 V33S 0 3.3", "V33 V33S 0 DC 3.3 AC 1"))
f = np.array(ngs.vec("frequency")).real
h = 20 * np.log10(np.abs(np.array(ngs.vec("AVDD"))))
R["avdd_noise_transfer_dB"] = {"peak_dB": float(h.max()), "peak_at_kHz": float(f[np.argmax(h)] / 1e3),
                               **{f"at_{x}MHz": float(np.interp(x * 1e6, f, h)) for x in (1, 10, 25, 100)}}
curves["fb"] = (f, h)

# ================================================================== 25 MHz crystal load
# Y101 C164045 (Yajingxin TAXM25M4RLBCCT2T): 25 MHz, CL 20 pF, ESR 80 ohm, +-10 ppm,
# +-50 ppm over temperature. Motional parameters assumed typical for 3225 25 MHz:
# C1 4 fF, C0 1.5 pF; L1 set so the crystal is exactly on 25 MHz at its rated 20 pF.
# Load seen in the circuit: C108 and C109 in series plus stray (pins + traces, 3-5 pF).
# C108/C109 are 33 pF (C1562) since 2026-10-21; 18 pF before (CL only 12-14 pF).
C1, C0, CLR, F0 = 4e-15, 1.5e-12, 20e-12, 25e6
L1 = 1 / ((2 * math.pi * F0) ** 2 * (C1 * (C0 + CLR) / (C1 + C0 + CLR)))


def xtal_f(cl):
    ngs.run(f"""xt
VX a 0 AC 1
CLD a b {cl}
LM b m1 {L1}
CM m1 m2 {C1}
RM m2 0 80
C0 b 0 {C0}
.ac lin 4001 {F0 * 0.999} {F0 * 1.001}
.end""")
    f = np.array(ngs.vec("frequency")).real
    i = np.abs(np.array(ngs.vec("vx#branch")))
    return float(f[np.argmax(i)])


R["crystal"] = {"C1_fF": C1 * 1e15, "C0_pF": C0 * 1e12, "rated_CL_pF": 20}
rows = []
for c, stray in ((18e-12, 3e-12), (18e-12, 5e-12), (33e-12, 3e-12), (33e-12, 5e-12), (30e-12, 4e-12)):
    cl = c / 2 + stray
    rows.append({"caps_pF": c * 1e12, "stray_pF": stray * 1e12, "CL_pF": cl * 1e12,
                 "offset_ppm": (xtal_f(cl) - F0) / F0 * 1e6})
R["crystal"]["load_cases"] = rows

json.dump(R, open(os.path.join(HERE, "eth_results.json"), "w"), indent=1)

# ================================================================== plots
mhz = lambda f: f / 1e6
fr = curves["6.8n"][0]
mask = rl_mask(fr)
okm = ~np.isnan(mask)
svg_plot("eth_return_loss.svg", "Ethernet return loss at the RJ45 (100 ohm)",
         [("RX pair, 6.8 nF caps (board)", mhz(fr), curves["6.8n"][1]),
          ("RX pair, caps shorted", mhz(curves["1u"][0]), curves["1u"][1]),
          ("TX pair", mhz(curves["tx"][0]), curves["tx"][1]),
          ("802.3 100BASE-TX limit", mhz(fr[okm]), mask[okm])],
         "frequency [MHz]", "return loss [dB]", logx=True, xlim=(0.1, 300), ylim=(0, 40))
svg_plot("eth_rx_gain.svg", "RX: cable (100 ohm source) to W5500 RXP-RXN",
         [("6.8 nF caps (board)", mhz(fr), curves["6.8n"][2]),
          ("caps shorted", mhz(curves["1u"][0]), curves["1u"][2])],
         "frequency [MHz]", "gain vs matched load [dB]", logx=True, xlim=(0.01, 300), ylim=(-30, 3))
tt, vv = curves["mlt3"]
svg_plot("eth_tx_mlt3.svg", "TX: 100BASE-TX MLT-3 on the line (100 ohm load)",
         [("line differential", tt, vv)], "time [ns]", "V")
svg_plot("eth_avdd.svg", "+3.3V_ETHA: noise transfer from +3.3V through FB101",
         [("+3.3V -> +3.3V_ETHA", curves["fb"][0] / 1e3, curves["fb"][1])],
         "frequency [kHz]", "dB", logx=True, xlim=(1, 3e5))

print(json.dumps(R, indent=1, default=float))
