# GDoor ESPHome component

An [ESPHome external component](https://esphome.io/components/external_components.html)
for the GDoor adapter, as an alternative to the MQTT firmware (see issue #25).
With it the adapter appears in Home Assistant through the ESPHome integration,
with native entities instead of an MQTT sensor and shell commands, and the ESP32
can run other ESPHome components (e.g. a Bluetooth proxy) next to GDoor.

The component compiles the same bus encoder/decoder as the MQTT firmware
(`firmware/esp32/gdoor/src`). ESPHome only builds files inside the component
directory, so `esphome/components/gdoor` carries copies of those files; edit
the firmware sources and run `python tools/sync_esphome_core.py`. CI fails if
the copies are out of date.

## Quick start

```yaml
esp32:
  board: wemos_d1_mini32
  framework:
    type: arduino   # required

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
| `rx_threshold_pin` | – | DAC pin of the comparator threshold, `26` on the v3.1 adapter. Leave out for the fixed-threshold inputs. |
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

## Ethernet

For Ethernet, use ESPHome's own [`ethernet:`](https://esphome.io/components/ethernet.html)
component instead of `wifi:`. A W5500 module on the free VSPI pins of the
adapter (wiring in [the firmware README](../firmware/esp32/gdoor/README.md#ethernet-w5500-module)):

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

## Limitations

- ESP32 with the Arduino framework only: the bus timing uses the Arduino core
  3.x hardware timer and LEDC API. The component uses three hardware timers.
- The comparator threshold uses the DAC, which only the original ESP32 has
  (not the S2/S3/C3).
- Audio (adapter v4) is not supported by this component.
