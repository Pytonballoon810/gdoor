# GDoor ESPHome component

An [ESPHome external component](https://esphome.io/components/external_components.html)
for the GDoor adapter, as an alternative to the MQTT firmware (see issue #25).
With it the adapter appears in Home Assistant through the ESPHome integration,
with native entities instead of an MQTT sensor and shell commands, and the ESP32
can run other ESPHome components (e.g. a Bluetooth proxy) next to GDoor.

The component compiles the same bus encoder/decoder as the MQTT firmware
(`firmware/src`). ESPHome only builds files inside the component
directory, so `esphome/components/gdoor` carries copies of those files; edit
the firmware sources and run `python tools/sync_esphome_core.py`. CI fails if
the copies are out of date.

## Quick start

```yaml
esp32:
  board: wemos_d1_mini32
  framework:
    type: esp-idf   # or arduino

external_components:
  - source: github://gdoor-org/gdoor@main
    components: [gdoor]

gdoor:
  rx_threshold_pin: 26   # v3.1 adapter, "adjustable (IO22)" input

event:
  - platform: gdoor
    name: Doorbell
    device_class: doorbell
    actions: [BUTTON_RING]

button:
  - platform: gdoor
    name: Open Door
    busdata: "020031ECF3EB0060A103C27A3D"   # your DOOR_OPEN message, see below
```

A complete example is in [`gdoor-example.yaml`](gdoor-example.yaml).

## Finding the bus data of your installation ("learning mode")

Every valid bus message is logged at `INFO` level, with its action, source,
parameters and the complete `busdata`:

```
[I][gdoor]: Received DOOR_OPEN (type INDOOR, source ECF3EB, parameters 0060), busdata: 020031ECF3EB0060A103C27A3D
```

Open the ESPHome log, press the door opener, light button or ring button, and
copy the `busdata` into a `button`, or the `parameters`/`source` into an
`event` filter.

## Configuration

### `gdoor:` hub

| Option | Default | Description |
|---|---|---|
| `rx_pin` | `22` | Bus receive input. v3.1: `22` (adjustable) or `21`; v3.0: `12` (bugfix) or `32`. |
| `tx_pin` | `25` | PWM output that modulates the bus. |
| `tx_enable_pin` | `27` | Enables the bus output driver. |
| `rx_threshold_pin` | – | DAC pin of the comparator threshold, `26` on the v3.1 adapter. Leave out for the fixed-threshold inputs and on chips without DAC (S3). |
| `rx_sensitivity` | `1.45` | Comparator threshold in volts (the MQTT firmware offers 1.3 / 1.45 / 1.65). |
| `log_invalid` | `false` | Also log messages with parity/CRC errors, at `DEBUG` level. |
| `on_message` | – | Automation for every valid received message, with `message` (`action`, `type`, `source`, `destination`, `parameters`, `busdata`, all `std::string`). |
| `on_sent` | – | Automation after a message was put on the bus, same `message` variable. |

### `event` platform

Fires when a received message matches all given filters. The event type is
the bus action (e.g. `BUTTON_RING`), so in Home Assistant an automation can use
the `event.received` trigger on it.

| Option | Description |
|---|---|
| `actions` | List of bus actions to react to; also becomes the event's event types. Default: all actions. |
| `parameters` | 2 bytes hex, e.g. `"0360"`: for `BUTTON_RING` this tells several doorbell buttons apart. |
| `source` / `destination` | 3 bytes hex, the bus address of the sending/receiving station. |
| `busdata` | Complete message, exact match. |

### `button` platform

Sends a fixed message when pressed. `busdata` is required.

### `text_sensor` platform

Last received message, `type` is `action` (default), `busdata` or `json` (same
fields as the MQTT firmware).

### `gdoor.send` action

```yaml
on_...:
  - gdoor.send: "020031ECF3EB0060A103C27A3D"
  # or templated
  - gdoor.send:
      busdata: !lambda 'return id(door_code).state;'
```

Messages are queued and sent as soon as the bus is idle.

## Adapter hardware v4.0

The v4.0 audio prototype moved the transmit pin and has no threshold DAC:

```yaml
gdoor:
  tx_pin: 12
  rx_pin: 21
  # no rx_threshold_pin: IO26 is an audio line on v4.0
```

ESPHome warns that GPIO12 is a strapping pin. On v4.0 that is fine: the pin
reads low at boot as required (R21 not fitted, transmit filter unpowered until
TX enable). Do not use the W5500 Ethernet pins below on v4.0, they are taken
by the codec.

## Ethernet

For Ethernet, use ESPHome's own [`ethernet:`](https://esphome.io/components/ethernet.html)
component instead of `wifi:`. A W5500 module on the free VSPI pins of the
adapter (wiring in [the firmware README](../firmware/README.md#ethernet-w5500-module)):

```yaml
ethernet:
  type: W5500
  clk_pin: 18
  miso_pin: 19
  mosi_pin: 23
  cs_pin: 5
  interrupt_pin: 4
  reset_pin: 16
```

## DIN board (ESP32-S3)

The DIN-rail board (`hardware/boards/din`) has ready-made configurations:

| File | Network | Contents |
|---|---|---|
| [`gdoor-din-ethernet.yaml`](gdoor-din-ethernet.yaml) | W5500 Ethernet | doorbell, door opener, bus voltage, "bus connected", status LEDs |
| [`gdoor-din-wifi.yaml`](gdoor-din-wifi.yaml) | WiFi | the same |
| [`gdoor-din-voice.yaml`](gdoor-din-voice.yaml) | W5500 Ethernet | the same, plus two-way voice through Home Assistant |

The shared parts are in [`din/common.yaml`](din/common.yaml) (pins, LEDs,
entities) and [`din/voice.yaml`](din/voice.yaml). ESPHome runs either
Ethernet or WiFi, never both. The S3 has no DAC, so the board uses the fixed
comparator threshold and `rx_threshold_pin` is rejected. Flash the first time
over the USB-C port (hold BOOT, press RESET); the log also runs over USB.

## Voice (DIN board)

**Not tested on hardware yet.** `gdoor-din-voice.yaml` drives the ES8374
codec with [esphome-audio-stack](https://github.com/n-IA-hane/esphome-audio-stack)
and makes calls with [VoIP Stack](https://github.com/n-IA-hane/esphome-intercom)
(ESPHome 2026.9.x, Home Assistant 2026.7+). ESPHome 2026.10 does not build
it yet: esphome-audio-stack 2026.10.2 uses a ring-buffer member that ESPHome
2026.10 turned into a function.

1. A ring at the door (`BUTTON_RING`) calls `ring_target` in Home Assistant.
2. When the call is answered, the adapter sends the learned `AUDIO_REQUEST`
   message, so the door station switches its speech path onto the bus.
3. Hanging up on either side (or the 45 s calling timeout) sends
   `AUDIO_VIDEO_END`.
4. The door is opened from Home Assistant with the "Open Door" button.

Setup:

1. Home Assistant: install **VoIP Stack** from HACS, restart, add it under
   Settings → Devices & services, and add the browser/Companion phones that
   should ring. The phone card is `type: custom:voip-stack-card`. Browsers
   need HTTPS for the microphone. Behind a reverse proxy, `/api/voip_stack/ws`
   needs the WebSocket upgrade headers.
2. Learn the bus messages: with the plain DIN config running, pick up and
   hang up at the indoor station, and copy the `AUDIO_REQUEST` and
   `AUDIO_VIDEO_END` busdata from the log into the substitutions of
   `din/voice.yaml`. Until then calls work on the network side only.
3. Set `ring_target` to the phone or ring group that should ring.
4. Bring-up: check the ES8374 answers on I2C (address 0x10 in 7-bit form),
   call the adapter and listen at the door station, then raise or lower
   `codec_mic_gain_db` (below 24, the driver rejects more) and `call_volume`.

Codec notes (from Everest's reference drivers, the datasheet has no register
map): the driver fixes the input to MIC1P/MIC1N (LIN1/RIN1), which is where the
bus is coupled in, adds a +15 dB differential boost, and routes the DAC to
MONOOUT. It also switches on the unused class-D speaker at every start; the
`codec_board_setup` script switches it off again.

## Limitations

- ESP32 family only. The bus timing uses the ESP-IDF gptimer, LEDC (timer 3,
  channel 7) and GPIO interrupt drivers, so it builds with the ESP-IDF and
  the Arduino framework. The component uses two hardware timers.
- The comparator threshold uses the DAC, which only the ESP32 and ESP32-S2
  have (not the S3/C3).
- Voice needs the DIN board (ESP32-S3 with PSRAM and the ES8374 codec). The
  v3.x adapters have no codec.
