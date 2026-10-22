# ESPHome port and voice — implementation plan

Goal: the DIN board (ESP32-S3) runs the gdoor ESPHome component on ESP-IDF, with
two-way voice through the door intercom bus, calls handled by Home Assistant via
[intercom-api](https://github.com/n-IA-hane/intercom-api) (no FritzBox, PBX or
phone number needed), and the classic GDoor adapters (v3.x, ESP32) keep working.

Status: plan only (2026-10-20). Nothing here is implemented or tested. The DIN
board is routed but not built.

## Decisions this plan rests on

| Decision | Why |
|---|---|
| ESPHome, not the MQTT firmware, is the target for the DIN board | Home Assistant native API, Ethernet/ADC/LEDs are YAML, the voice stack is ESPHome |
| ESP-IDF framework | intercom-api's `esp_audio_stack`, `esp_aec` and `esp_afe` refuse Arduino (`only_with_framework(ESP_IDF)`); ESP-IDF is also ESPHome's default |
| One shared bus core, rewritten against ESP-IDF drivers | `firmware/src` stays the single source (`tools/sync_esphome_core.py`); Arduino-ESP32 3.x is built on ESP-IDF 5, so the MQTT firmware compiles the same code |
| Audio through `esp_audio_stack` with `codec: es8374` | It already drives the ES8374 via Espressif `esp_codec_dev` and brings echo cancellation, which the bus needs: MONOOUT and the mic input share the same line |
| Video comes from the existing IP cameras, shown in Home Assistant | The Gira bus carries no video; `voip_stack`'s `video:` needs an ESPHome camera on the ESP, which the adapter has none of |

## Phase 0 — prerequisites (owner: Philipp)

1. ES8374 datasheet: register 0x21 (input select) — does the driver's fixed `LIN1`
   input equal the MIC1P/MIC2P pair the bus feeds (C29/C31)? Registers for MONOOUT
   level and for switching off the class-D speaker output (unused on this board).
2. A classic GDoor adapter (v3.1, ESP32) on the bus, for regression-testing the
   ported bus timing before the DIN board exists.
3. Order and assemble the DIN board (JLCPCB files in `hardware/boards/din`), plus
   the hand-soldered parts listed in `DESIGN.md`.
4. Learn the bus messages of the real indoor station: with the current component
   in learning mode, record `BUTTON_RING`, `DOOR_OPEN`, `AUDIO_REQUEST` and
   `AUDIO_VIDEO_END` busdata while picking up and hanging up at the indoor station.

## Phase 1 — framework-neutral bus core (code only)

Edit in `firmware/src`, then sync. Both CI workflows must stay green.

1. **Timing on ESP-IDF drivers** (`gdoor_rx.cpp`, `gdoor_tx.cpp`):
   - TX: LEDC timer 52 kHz, 10-bit, duty 512 (= 50 %), gated on/off by a 60 kHz
     `gptimer` alarm callback that keeps today's pulse-count state machine.
   - RX: GPIO falling-edge ISR (`gpio_isr_handler_add`; tolerate
     `ESP_ERR_INVALID_STATE` from `gpio_install_isr_service`, Arduino may have
     installed it) counts pulses and records the edge time. One free-running
     `gptimer` replaces the two Arduino timers: the edge ISR re-arms its alarm to
     "last edge + 20 ticks @120 kHz" (bit end), the alarm callback stores the
     count and re-arms to "last edge + 6 × STARTBIT_MIN_LEN" (bitstream end).
     This avoids stop/start calls from ISRs, which gptimer rejects when the
     timer is already in that state.
   - All ISR code and data `IRAM_ATTR`/DRAM, shared state `volatile`, no logging.
     `CONFIG_GPTIMER_ISR_IRAM_SAFE` and `CONFIG_GPTIMER_CTRL_FUNC_IN_IRAM` set via
     `sdkconfig_options` in ESPHome. The MQTT firmware uses Arduino's prebuilt
     sdkconfig, which may not allow these; it then keeps today's behaviour (bus
     ISRs paused during flash writes), which is acceptable there.
   - RX threshold: `dac_oneshot` on chips with `SOC_DAC_SUPPORTED` (v3.1
     adjustable input), compiled out elsewhere (S3 has no DAC; the DIN board uses
     a fixed comparator threshold).
2. **No Arduino types in the core**: `Printable`/`printTo`, `Serial` (`printer_helper.h`)
   and `boolean` go behind `#ifdef ARDUINO`; `send(String)` becomes
   `send(const char *)`, the MQTT firmware passes `str.c_str()`.
3. **Fallback if timing breaks under load** (only if Phase 3 shows lost or
   corrupt messages while audio runs): TX via RMT with hardware carrier (no
   60 kHz ISR), RX via PCNT or RMT. Decided on measurements, not up front.

Done when: `firmware.yml` and `esphome.yml` builds pass; on the v3.1 adapter the
ported firmware receives a ring and opens the door, and the logged raw pulse
counts match the pre-port firmware for the same messages.

## Phase 2 — ESPHome component on ESP-IDF and the S3

1. `__init__.py`: drop `cv.only_with_arduino`; allow both frameworks.
   `rx_threshold_pin` only on chips with a DAC (validation error on the S3).
2. `esphome/gdoor-example.yaml` (v3.1, ESP32) switches to `framework: esp-idf`;
   keep an Arduino variant only if users need it.
3. New `esphome/gdoor-din.yaml` (DIN board, ESP32-S3 N8R2):
   - `psram: {mode: quad, speed: 80MHz}`, logger on `USB_SERIAL_JTAG`.
   - `gdoor:` TX GPIO4, TX enable GPIO5, RX GPIO6.
   - `ethernet: type: W5500` on SPI2 (CS 10, MOSI 11, CLK 12, MISO 13, INT 14,
     RST 21) — ESPHome runs Ethernet *or* WiFi, so ship two variants.
   - Bus voltage: `adc` GPIO8, `multiply: 11`, plus a `binary_sensor` "bus
     connected" from a threshold (closes upstream issue #28).
   - Status LEDs GPIO2 and GPIO17 as `output` + `light` or a `status_led`.
   - Doorbell `event`, door-open `button`, last-message `text_sensor` as today.
4. CI: compile both examples; ESPHome min version follows intercom-api
   (2026.9.0+).

Done when: both YAMLs compile in CI; on the DIN board the doorbell event reaches
Home Assistant and the door-open button works, over Ethernet and over WiFi.

## Phase 3 — audio bring-up, no VoIP yet (needs the DIN board)

1. Add `esp_audio_stack` (I2S MCLK 38, BCLK 39, LRCK 40, DOUT 41, DIN 42; I2C
   SDA 47, SCL 48) with `codec: {input: {type: es8374, address: 0x20, gain_db: 21},
   output: {type: es8374, address: 0x20}}`. `gain_db` must stay below 24: the
   ES8374 driver rejects higher mic gains, and the component default (30) fails.
2. A board package with the register writes from Phase 0 step 1 (input select,
   speaker off, MONOOUT level), applied after codec open — the component exposes
   no private register writes on purpose.
3. Speech-channel test: replay the learned `AUDIO_REQUEST`, check that the door
   station switches its audio onto the bus; play a test tone to MONOOUT and
   capture mic level; replay `AUDIO_VIDEO_END`.
4. Measure: audio level on the bus at the indoor station, echo of our own output
   in the mic signal, and bus message decoding while audio streams (Phase 1 step 3
   decision).

Done when: a tone sent from the ESP is heard at the door station, the door
station microphone is captured at a usable level, and no bus messages are lost
during audio.

## Phase 4 — VoIP with intercom-api

1. ESPHome: `voip_stack` from esphome-voip-stack, `esp_aec` (or `esp_afe`) from
   esphome-audio-stack, following their `generic-s3-voip.yaml` profile.
2. Glue in `gdoor-din.yaml`:
   - doorbell event (`BUTTON_RING`) → `voip_stack.call` to the Home Assistant
     ring group;
   - `on_in_call` → `gdoor.send` learned `AUDIO_REQUEST`;
   - `on_hangup` / `on_idle` → `gdoor.send` learned `AUDIO_VIDEO_END`;
   - a call timeout so an unanswered ring ends cleanly.
3. Home Assistant: install intercom-api via HACS (needs HA 2026.7+), add the
   adapter and the Phone (4a) Pro as phones, ring group.
4. Door opening during a call: dashboard button → gdoor door-open button; keypad
   code via the `voip_stack.dtmf_received` trigger (DTMF only exists on the HA side).
5. Echo cancellation tuning with the reference signal from MONOOUT.

Done when: ring at the door → call in Home Assistant → answer in the browser or
Companion app → both sides hear each other without disturbing echo → door opens
from the call → hang-up releases the bus.

## Phase 5 — Home Assistant workflow

1. Dashboard "Tür": live `camera.haustur` (MJPEG), intercom-api phone card,
   door-open button.
2. Automation `automation.klingel_push_mit_einfahrt_kamera` reworked: trigger on
   the new doorbell event, only when nobody is home, notify
   `notify.mobile_app_phone_4a_pro`, `clickAction` opens the dashboard.
3. nginx: WebSocket upgrade for `/api/voip_stack/ws` and `/api/voip_stack/video_ws`
   (intercom-api uses HA WebSockets, not WebRTC, so no TURN), HTTPS for
   microphone access, `proxy_buffering off` for the MJPEG stream.
4. UniFi: allow SIP 5060/UDP and RTP 40000+/UDP between the adapter and Home
   Assistant if they are on different VLANs; mDNS or a fixed IP for ESPHome.

## Phase 6 — documentation and upstream

- `esphome/README.md`: framework change, DIN board config, voice setup,
  limitations; remove "Audio is not supported".
- `firmware/README.md`: note the ESP-IDF based core (Arduino core 3.x still required).
- Upstream PRs to gdoor-org in order: core port → component/S3 → voice.

## Risks

| Risk | Effect | Mitigation |
|---|---|---|
| ISR load (60 kHz RX edges, TX gating) next to AEC and WiFi on the S3 | Lost or corrupt bus messages | Measure in Phase 3; RMT/PCNT fallback |
| Echo through the bus coupling stronger than AEC handles | Caller hears themselves | MONOOUT level, mic gain, AFE instead of AEC |
| `AUDIO_REQUEST` alone does not open the speech path | No audio from the door | Learn the full exchange from the real indoor station (Phase 0 step 4) |
| ES8374 routing differs from the driver's fixed setup | No or distorted audio | Board-package register writes from the datasheet |
| intercom-api is young; upgrades have needed reconfiguration | Breakage on update | Pin versions in the YAML and HACS |
| No hardware until the DIN board is built | Phases 3–5 blocked | Phases 1–2 are verifiable on a v3.1 adapter |

Licences: gdoor is GPL-3.0; intercom-api is MIT and Espressif `esp_codec_dev`
is permissive, both usable from a GPL project.
