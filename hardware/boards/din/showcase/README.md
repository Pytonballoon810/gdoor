# GDoor DIN showcase

[![GDoor DIN: assembly, mounting, wiring and a doorbell press travelling to Home Assistant](showcase.gif)](showcase.mp4)

The GIF is a small preview. Click it, or open [`showcase.mp4`](showcase.mp4), for the full
1280 × 720 video.

An animated 3D page (three.js), about 46 s long, playing in a loop:

1. **Assembly**: the board, plugs and lid fly together, a reversed exploded view.
2. **Onto the rail**: the device hooks onto a TS35 rail in a distribution board and clicks in.
3. **Wired up**: 5 V from a DIN-rail supply goes to the top plug, the door bus to the bottom plug,
   and an Ethernet cable to the front.
4. **Ding dong**: someone presses the button on the door station. The signal runs along the bus,
   through the board (bus RX, then the ESP32-S3, then the W5500), out over Ethernet to Home
   Assistant, and on to a phone notification.

## View it

It loads models over HTTP, so serve `hardware/boards/din` and open `/showcase/`
(PowerShell, from `hardware/boards/din`):

```powershell
python -m http.server 8766 --bind 127.0.0.1
```

Then open http://127.0.0.1:8766/showcase/. Use the chapter buttons, drag the bar to scrub, press
space to pause, and click "Free camera" to orbit.

URL option: `?t=33&paused` opens at a given second, paused.

## Re-render the video

`record.mjs` renders the page frame by frame in headless Edge, each frame at an exact time
(`?capture`). It encodes `showcase.mp4` (1280 × 720, 30 fps) and `showcase.gif` (480 px wide,
8 fps, kept under 8 MB so the README stays light). It serves the files itself, so no other
server is needed, and takes a few minutes. Run it in PowerShell, from this folder:

```powershell
npm install
npm run record
```

For another Chromium-based browser, set `$env:BROWSER` to its executable first. Re-render after
changing the page, the board model or the enclosure STLs.

## Models

- `models/board.min.glb`: the board with its parts, from KiCad, compressed with meshopt.
  Re-export it after a layout change (PowerShell, from `hardware/boards/din`):

  ```powershell
  & "C:\Program Files\KiCad\10.0\bin\kicad-cli.exe" pcb export glb --force --subst-models --include-tracks --include-pads --include-silkscreen --include-soldermask --user-origin 100x60mm -o showcase/models/board.glb esp32.kicad_pcb
  npx -y @gltf-transform/cli@4.1.1 optimize showcase/models/board.glb showcase/models/board.min.glb --compress meshopt --simplify-error 0.0005 --texture-compress false
  Remove-Item showcase/models/board.glb
  ```

- The enclosure is loaded directly from `../enclosure/gdoor-din-base.stl` and `gdoor-din-lid.stl`.
- The distribution board, breakers, power supply, door station, Home Assistant box and phone are
  simple stand-ins built in the page.

## Coordinates

The page loads the enclosure STLs as printed and puts them back in their assembled position: the
lid as it is, the base turned over (see `../enclosure/README.md`, *Mirrored design frame*). The
plugs, LEDs and RJ45 cable plug are built in enclosure.scad's design frame, which is the mirror
image of the real device. The board is placed with X = 52.4 − (kx − 100), Y = 87.5 − (ky − 60),
and its component side towards the lid at Z = 0.
