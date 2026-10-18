# Released hardware

One folder per fabricated version of the GDoor adapter. The KiCad source of each
version is at the git tag of the same name.

| Version | Git tag | Files |
|---|---|---|
| `v3.0/` | `3.0` | `esp32.zip` gerbers + drill, `bom.csv`, `positions.csv`, `designators.csv`, `netlist.ipc` |
| `v3.1/` | `3.1` | `esp32.zip` gerbers + drill, `bom.csv`, `positions.csv`, `designators.csv` |
| `v3.1-1/` | `3.1-1` | `esp32.zip` gerbers + drill, `netlist.ipc`; `gdoor_v3.1-1_jlcpcb_gerbers.zip` |
| `v4.0/` | `4.0` | `esp32.zip` gerbers + drill, `netlist.ipc`; `gdoor_v4.0_jlcpcb_gerbers.zip` (first audio board, ES8374) |

`esp32.zip` and `netlist.ipc` are the original upstream production files.
`gdoor_v*_jlcpcb_gerbers.zip` is a later re-export of the same board with
bennymeg's Fabrication Toolkit (JLCPCB file names, drill maps included); its IPC
netlist matched the upstream one and is not kept twice.

The DIN board is not released yet; its JLCPCB files are in
`../boards/din/production/`.
