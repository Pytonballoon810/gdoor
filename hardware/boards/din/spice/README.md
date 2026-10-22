# GDoor DIN — SPICE simulation of the bus and audio front end

Simulated 2026-10-21. The first run used `esp32.kicad_sch` at commit 53a064e,
where R3/R4 were 100k. That run found the RX oscillation (section 1), and R3/R4
went back to 82k the same day. The R and C values in `frontend.cir` are checked
against a fresh netlist export of the schematic, and all 60 match. The Ethernet
front end (magjack side, terminations, analog supply, crystal) is in
`eth_sim.py` (sections 6–8). The MCU and USB are not simulated.

```
"C:/Program Files/KiCad/10.0/bin/python.exe" sim.py    # ~5 min, writes results.json
"C:/Program Files/KiCad/10.0/bin/python.exe" plot.py   # writes the *.svg plots
```

It runs KiCad's own `ngspice.dll` through `ngs.py` (ctypes), so it needs nothing
beyond KiCad 10.

## Files

| File | What |
|---|---|
| `frontend.cir` | Netlist of the bus side: bridge D1, bus divider, RX band-pass U2 + comparator U6A, Q1/Q2 `+5V_onoff` switch, TX band-pass U3 + driver U1, codec coupling (C21/C29/C31), codec supply. Node names follow the KiCad nets. R3/R4 = `{R_RX}`, R18/R19 = `{R_TX}`. |
| `models.lib` | Behavioural models written from datasheet figures (see *Models*). |
| `sim.py` | All testbenches; aborted transients raise. |
| `plot.py`, `*.svg` | Plots. |
| `eth_sim.py`, `eth_results.json`, `eth_*.svg` | Ethernet front end: the netlist, magjack model, testbenches and plots in one script. |
| `results.json` | All numbers and waveforms. |

## Models and assumptions

- **Op amps**: single-pole macromodels from the datasheets, not vendor models.
  LMV321 (U2, U3): 1 MHz GBW, 1 V/µs, rail-to-rail output; GBW also run at 0.7
  and 1.5 MHz because LCSC clones differ. TLV9351 (U1): 3.5 MHz, 20 V/µs,
  ±60 mA. The models have no supply-voltage dependence apart from the rail
  limits, and their output is high-Z when unpowered. Every pin has ESD diodes to
  the rails.
- **LM393 (U6A)**: open-collector comparator, ~0.3 µs, 16 mA sink.
- **Transistors**: standard 2N2222A / 2N5401 parameter sets. Diodes: generic
  MB10S and SS14 sets.
- **Bus**: 26 V DC (30 V for the plug-in test) behind a resistance of
  10/30/100/300 Ω. The real bus impedance at 50–60 kHz is **not known**, so
  every bus-level number is shown against it. RX carriers are sine bursts of 0.5 ms.
- **ES8374 codec**: MONOOUT is a 1.65 V (VMID) source behind 1 MΩ ("high-Z",
  output off) or 5 Ω ("low-Z", driving). The mic inputs are 20 kΩ to VMID. Pin ESD
  goes to AVDD (behind R41 33 Ω); the codec's load is lumped as 10 mA on
  AVDD. U7 (AMS1117) can source but **cannot sink**.

## Results

### 1. RX band-pass oscillates with R3/R4 = 100k; fixed with 82k

The board now has 82k, as upstream; 100k was there from 7ce317d until
2026-10-21. Since 2026-10-22 R3/R4 are 0603 (C23254, JLC Basic) instead of
0402 (C2909388, Extended); the value is the same.

U2 is a Sallen-Key band-pass with gain K = 1 + R12/(R5‖R7) = 1.94. Its damping term is

    C4·(1/R1 + (1−K)/R10) + (C2+C4)/(R3‖R4)

| R3 = R4 | R3‖R4 | damping (per 100 pF) | ideal op amp |
|---|---|---|---|
| 100k (7ce317d until 2026-10-21) | 50k | **−4.6 µS** | **unstable**, oscillates near 57 kHz |
| 82k (board now; upstream esp32-mini) | 41k | +4.2 µS | stable, f0 62.5 kHz, Q 9.4 (6.7–16 over R 1 %/C 5 %) |

The stability limit is R3 = R4 ≈ 90k. Commit 7ce317d treated R3/R4 as a plain
1.65 V divider, but they are also the filter's ground leg.

SPICE kick test (1 mV bus step, `rx_kick.svg`): with 100k, the RX_ANA ringing grows
about 10⁴–10⁷× per ms and saturates at 3.25 Vpp, for every U2 GBW tried
(0.7/1/1.5 MHz). A board built that way would have RX toggling at about 49 kHz
with no bus signal. With 82k it decays below 0.1 µV within 0.5 ms. All 20 000
tolerance samples of the 100k version are unstable; none of the 82k version.

The TX stage (K = 1.39) is stable either way: Q 1.4 with 100k and 1.1 with 82k.

### 2. RX filter and sensitivity (82k)

- Response bus → RX_ANA: peak at 54 kHz (51–57 kHz over U2 GBW 0.7–1.5 MHz;
  52–56 kHz over part tolerances). Peak gain 8.8 dB; +7.2 dB at 52 kHz, +2.7 dB at
  60 kHz. The unstable 100k version's formal peak is at 49 kHz (`rx_filter.svg`).
- Comparator U6A: upper threshold 1.63 V, lower 1.31 V (313 mV hysteresis).
  RX_ANA idles at 1.65 V, only **15 mV above the upper threshold**. With 1 %
  resistors and the op-amp offsets, about 20 % of boards would idle with RX high
  instead of low (−43…+75 mV margin). Detection still works either way, but an
  RX-high board needs only a few tens of mV of positive noise for a false edge.
- Minimum carrier on the line (J1, codec high-Z) for full pulse counts:

  | carrier | 0.4 Vpp | 0.6 Vpp | 1.0 Vpp | 1.9 Vpp |
  |---|---|---|---|---|
  | 60 kHz | 0/30 | 29/30 | 30/30 | 32/30 |
  | 52 kHz | 24/26 | 27/26 | 28/26 | 30/26 |

  Above about 0.6 Vpp the high-Q filter rings on for 20–70 µs after the burst ends
  and adds 1–4 extra edges (`rx_wave.svg`). Whether that matters depends on how
  the firmware's pulse counter tolerates it.
- **If the codec drives MONOOUT (low-Z), RX is dead.** R32 22 Ω + C21 short the bus
  node: 0/30 edges even at 1.4 Vpp on the line.

### 3. TX path (R18/R19 = 100k as on the board)

- `+5V_onoff` (Q1/Q2): 4.98 V on; 0–90 % in 32 µs after TX_EN; dips to 4.8 V
  during TX.
- TX band-pass: peak 51.4 kHz (gain at 52 kHz +2.4 dB; with 82k the peak would be at
  56 kHz and −0.4 dB at 52 kHz). U3 out 1.6–3.3 V, U1 out 0.2–4.8 V, which is
  close to clipping. U1 peak current 17–46 mA, under the 60 mA limit.
- Carrier on the line at J1 (40 cycles at 52 kHz):

  | bus impedance | 30 Ω | 100 Ω | 300 Ω |
  |---|---|---|---|
  | codec high-Z | 0.81 Vpp | 1.45 Vpp | 2.05 Vpp |
  | codec low-Z | 0.43 Vpp | 0.71 Vpp | 0.97 Vpp |

  The bridge makes the TX one-sided: U1 can only pull the line down (−0.4 to
  −1.9 V, +0.01 to +0.12 V upward). The rectified BUS node swings 4.3–4.8 Vpp.
  That swing drives **16–31 mA of 52 kHz ESD current into MONOOUT** through C21 and R32
  while the codec output is off.
- Switching TX_EN on steps the line by 12–115 mV.

### 4. Plugging into a live 30 V bus (board powered, bus 10 µs rise)

C21 (10 µF) has to charge to ~28 V through R32 and the MONOOUT pin. The same applies to
C29/C31 through 1 kΩ into MIC1P/MIC2P, and to C1 into U1's output:

| bus source | MONOOUT pin peak | charge into codec | codec AVDD peak | `+3.3V_ANA` peak | MIC1P peak | U1 out pin peak |
|---|---|---|---|---|---|---|
| 10 Ω | **710 mA** | 250 µC | **10 V** | **5.4 V** | 19 mA | 94 mA |
| 100 Ω | **194 mA** | 250 µC | **6.7 V** | **5.1 V** | 15 mA | 44–57 mA |

The charge (C21 × ΔV) is fixed by the topology. It ends up in the codec supply,
which U7 cannot sink, so `+3.3V_ANA` stays above 3.6 V for tens of ms (how long
depends on the assumed 10 mA codec load). The same circuit is on the upstream
v4.0 board. Whether real hot-plugs are this hard, and what the ES8374 pins
survive, is not known here. Treat this as a risk to check, not a confirmed failure.

### 5. Other checks

- `BUS_DCVOLT`: 26 V → 2.36 V, 30 V → 2.73 V, 34 V → 3.09 V (calculated).
  Peak 2.6 V during a 30 V plug-in.
- With TX_EN low, a plug-in charges `+5V_onoff` to 1–2 V through U1's output diode.
  That is harmless.

## Ethernet front end (`eth_sim.py`)

```
"C:/Program Files/KiCad/10.0/bin/python.exe" eth_sim.py   # ~1 min, writes eth_results.json, eth_*.svg
```

The board parts come from `mcu_eth.kicad_sch`: TX 49.9 Ω pull-ups (R114/R115), TCT
through R116 10 Ω with C120 22 nF, RX through C121/C122 6.8 nF into 2 × 49.9 Ω
(R119/R120) to RX_CM (C123 10 nF, and the jack's RCT), FB101 with the
`+3.3V_ETHA` capacitors, and Y101 with C108/C109.

**Models:**
- **HR911105A magjack:** 1CT:1CT transformer with 350 µH OCL, then a common-mode
  choke, then 75 Ω + 1 nF "Bob Smith" centre-tap termination. Leakage and winding
  capacitance are fitted to typical 10/100 magjack figures, because HanRun's
  datasheet couldn't be read. Fitted that way, the jack alone has 20.5 dB return
  loss at 30 MHz, 12 dB at 80 MHz, and −0.4 dB insertion loss at 100 MHz.
  **Everything above about 30 MHz therefore depends on the jack model**; the
  board-side results are below 30 MHz.
- **W5500 pins:** TX as current sinks with 3 pF; RX as 5 kΩ to 1.2 V with 3 pF.
  Both are assumed.

### 6. Matching and levels

- **Return loss at the RJ45** (802.3 100BASE-TX limit: 16 dB from 2–30 MHz,
  falling to 10 dB at 60–80 MHz):

  | pair | 1 MHz | 5 MHz | 10 MHz | 30 MHz | 60 MHz | 80 MHz | worst margin, 2–80 MHz |
  |---|---|---|---|---|---|---|---|
  | RX (board, 6.8 nF) | 13.7 | 30.6 | 41.8 | 22.6 | 16.0 | 13.4 dB | +3.6 dB at 79 MHz |
  | RX, caps shorted | 32.3 | 34.6 | 30.6 | 21.7 | 15.8 | 13.3 dB | +3.5 dB |
  | TX | 31.9 | 34.9 | 30.7 | 21.8 | 15.9 | 13.4 dB | +3.5 dB |

  Both pairs pass. The 10BASE-T limit (15 dB, 5–10 MHz) also passes.
- **TX level:** 49.9 Ω ∥ the line gives a flat 24–25 Ω transimpedance up to
  100 MHz. About 40 mA of differential chip current gives 1.0 V peak on the line,
  which is the 802.3 nominal level and the usual current for this kind of PHY.
  In a 125 MBd MLT-3 run (1500 symbols, `eth_tx_mlt3.svg`), the ±1 levels sit at
  0.99–1.02 V and the zero level at ±0.02 V, with 1.03 V overshoot.
- **RX low end:** the series caps C121/C122 (6.8 nF each, 3.4 nF together)
  with the 100 Ω termination put the low −3 dB corner at **220 kHz**, against
  21 kHz with the caps shorted (the 350 µH OCL alone). The gain is −8.3 dB at
  100 kHz and −0.8 dB at 500 kHz (`eth_rx_gain.svg`). WIZnet asks for these caps
  when the magjack's centre taps are tied to 3.3 V. On the HR911105A, RCT is a
  separate pin, and here it goes only to RX_CM, so the caps are not strictly
  needed. They are WIZnet's reference value (used on the WIZ850io), the W5500's
  baseline-wander correction is built to work with them, and 10BASE-T is
  unaffected. No change is proposed.

### 7. `+3.3V_ETHA` (FB101)

FB101 is modelled as 0.25 Ω + (0.6 µH ∥ 150 Ω ∥ 1.5 pF). Noise on +3.3V reaches
`+3.3V_ETHA` at +0.3 dB peak (32 kHz, so no harmful LC resonance), −48 dB at
1 MHz, and −88 dB at 25 MHz. `+3.3V_ETHA` impedance peaks at 0.32 Ω at 45 kHz.
The MLT-3 TX current makes 10 mVpp of ripple on it.

### 8. 25 MHz crystal: C9006 with 15 pF

Y101 is C9006 (TXC X322525MOB4SI, JLC Basic) since 2026-10-22: 25 MHz, **rated
for CL = 12 pF**, ESR 50 Ω, ±10 ppm tolerance, ±20 ppm over temperature, same
3225-4P footprint. C108/C109 are 15 pF (C1548, JLC Basic). The load is the two
caps in series plus stray (3–5 pF for pins and traces). The model assumes typical
motional values for a 3225 crystal (C1 4 fF, C0 1.5 pF); the pull scales roughly
with C1.

| C108 = C109 | stray | CL | offset |
|---|---|---|---|
| 15 pF (board) | 3 pF | 10.5 pF | +18.5 ppm |
| 15 pF (board) | 4 pF | 11.5 pF | +5.5 ppm |
| 15 pF (board) | 5 pF | 12.5 pF | −5.5 ppm |
| 18 pF | 3 pF | 12.0 pF | 0.0 ppm |
| 18 pF | 5 pF | 14.0 pF | −19.5 ppm |

IEEE 802.3u allows ±50 ppm for the 100BASE-TX clock. With 15 pF the pull is
−5.5…+18.5 ppm; with the crystal's ±10 ppm tolerance and ±20 ppm over temperature
the worst case is about +48.5 ppm, inside the budget. 18 pF would be −19.5…0 ppm
(worst case −49.5 ppm); 15 pF is closer to centred for the likely 4 pF stray.

Before 2026-10-22, Y101 was C164045 (Yajingxin TAXM25M4RLBCCT2T, CL 20 pF, ESR
80 Ω, ±50 ppm over temperature, JLC Extended). Its caps were 18 pF until
2026-10-21, which gave only 12–14 pF of load and +35…+55 ppm of pull; 33 pF
(C1562) brought that to −6.5…+1.5 ppm, but the ±50 ppm temperature rating alone
still filled the 802.3u budget.

## Not simulated

The bus impedance and the other stations' real carrier levels; ES8374
absolute-maximum ratings (not checked); thermal behaviour; layout parasitics; the
W5500's internal PHY (adaptive equalizer, baseline-wander correction, oscillator
gain margin with the 80 Ω ESR); USB; the digital side.
