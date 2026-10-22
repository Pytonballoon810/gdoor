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
