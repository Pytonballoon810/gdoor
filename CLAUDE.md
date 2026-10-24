# gdoor project notes

## 3D STEP export of the DIN board

`hardware/boards/din/PowerModule.step` is the 3D model of the whole DIN board (`esp32.kicad_pcb`),
with its components. Re-export it after any layout or 3D-model change, with these settings. Run this
in PowerShell, from `hardware/boards/din`:

```powershell
& "C:\Program Files\KiCad\10.0\bin\kicad-cli.exe" pcb export step --force --subst-models --include-tracks --include-pads --include-zones --user-origin 121.6x102.5mm -o PowerModule.step esp32.kicad_pcb
```

- **Copper:** include tracks and vias, pads, and zones (the copper fills). Inner layers
  (In1.Cu, In2.Cu) are left out.
- **Origin:** the centre of the board outline, at 121.6, 102.5 mm in board coordinates. `kicad-cli`
  has no board-centre option, so the point is given with `--user-origin`. If the outline changes,
  recompute that point from the `Edge.Cuts` extents.
- **Models:** `--subst-models` uses a STEP model wherever one sits next to a VRML model of the same
  name.
- The export takes about 30 s, and the file is about 60 MB.

## Printable files of the DIN enclosure

In `hardware/boards/din/enclosure`, `gdoor-din.3mf` sits next to the STLs: an unsliced Bambu Studio
project with two plates, plate 1 the single-colour base and lid, plate 2 both with body and accent
parts (accent on filament 2). `print_3mf.py` builds it from the STLs. Rebuild it every time any of
those STLs is rebuilt (commands in that folder's `README.md`). Philipp slices it himself in Bambu
Studio, so never add G-code or sliced files. It goes into the DIN release
(`.github/workflows/din-release.yml`), so keep that in step if the file name changes.

Plates exist only in Bambu's project format, and Bambu Studio crashes on a project without
`Metadata/project_settings.config`. So the file carries `bambu_project_settings.config`: Philipp's
own slicing settings (P1S 0.4 nozzle, 0.20mm Standard @BBL P1S with his changes, PLA Basic x2), as he
saved them from Bambu Studio into `gdoor-din.3mf` on 2026-10-24.

**Keep his settings.** He sets them in Bambu Studio and saves the project, and they must survive
every rebuild. `print_3mf.py` reads them from the existing `gdoor-din.3mf` before overwriting it:
the project settings (also copied back into `bambu_project_settings.config`) and every setting on
an object, part or plate, matched by name. So always rebuild in place, over the committed file,
never from a fresh copy, and never edit, regenerate or "tune" `bambu_project_settings.config`
yourself. If you rename an object, part or plate in `print_3mf.py`, its saved settings no longer
match; carry them over to the new name.

Bambu Studio's CLI (`bambu-studio.exe --info` / `--export-3mf`) writes a `result.json` into the
current directory. Delete it after a test run; it is not a project file.
