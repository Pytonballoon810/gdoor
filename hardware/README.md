# Hardware

More information about the hardware is on the
[GDoor Homepage](https://gdoor-org.github.io/documentation/firmware.html).

| Folder | Contents |
|---|---|
| `boards/esp32-mini/` | The GDoor adapter (KiCad). The schematic is V4.1 (ESP32-S3, work in progress); the layout is still the V4.0 board. |
| `boards/din/` | DIN-rail board with Ethernet and audio, plus its 3D-printed enclosure. See [`DESIGN.md`](boards/din/DESIGN.md). |
| `lib/` | KiCad footprints (`Library.pretty`) and symbols (`symbols.kicad_sym`) shared by both boards. |
| `releases/` | Production files of every released adapter version, see [`releases/README.md`](releases/README.md). |

Older board sources are not kept as folders; check out the git tag of a release
(`3.0`, `3.1`, `3.1-1`, `4.0`) to open that version in KiCad.

Each board keeps its own `3dmodels/`, because the boards store the model paths
relative to their project folder.
