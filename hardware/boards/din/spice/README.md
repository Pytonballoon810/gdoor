# GDoor DIN — SPICE simulation of the bus and audio front end

Simulated 2026-10-21. The first run used `esp32.kicad_sch` at commit 53a064e,
where R3/R4 were 100k. That run found the RX oscillation (section 1), and R3/R4
went back to 82k the same day. The R and C values in `frontend.cir` are checked
against a fresh netlist export of the schematic, and all 60 match. The MCU,
Ethernet and USB parts are digital and are not simulated.

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

The board now has 82k (C2909388), as upstream; 100k was there from 7ce317d
until 2026-10-21.

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

## Not simulated

The bus impedance and the other stations' real carrier levels; ES8374
absolute-maximum ratings (not checked); thermal behaviour; layout parasitics; the
digital side.
