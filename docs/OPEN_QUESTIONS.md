# Open questions

Decisions not yet made on the FC. None of these block writing the README; all of them block laying out a board. Owner: Sai. Update with chosen answer + date when resolved.

## 1. MCU

**Options on the table:**

- **STM32H743VIT6** — what most modern ArduPilot boards use (CubeOrange, MatekH743). Highest software path-of-least-resistance; existing board defs to fork.
- **STM32H753** — cryptographic peripherals; nice if we ever want signed firmware, otherwise overkill.
- **STM32H723** — cheaper, smaller flash; tight for ArduCopter.
- **RP2350** — interesting because we're already a Pi house, dual-core M33, but ArduPilot doesn't target it; would need a non-ArduPilot firmware path (INAV / Betaflight / custom MAVLink shim). Punts on ArduCopter parity.

**Recommendation:** start with H743 unless there's a strong reason not to. It keeps the firmware story trivial.

## 2. Form factor

- **Pixhawk standard 30.5×30.5 mm with M3 holes** — drops into existing frames; easy to swap with the CubeOrange+ during bring-up to A/B test.
- **Custom outline** — only if there's a frame-fit problem with standard.

**Recommendation:** Pixhawk standard for v1. Custom is a v2 conversation.

## 3. ESC channel count

4 / 6 / 8. Depends on the airframe — the current Nova drone is a quad (4 motors), but we may want headroom for a hex or for gimbal/payload PWM. 8 channels of DShot is cheap on H7 (timer-rich) so this is mostly a connector-real-estate question.

## 4. ELRS RX integration

- **Off-board** (status quo): RP4TD on USB, ESP32-C6 bridge, FC consumes CRSF over UART from the bridge.
- **On-board CRSF UART**: skip the ESP32, route ELRS RX directly to an FC UART. Saves a USB port and ~15 g.
- **On-board ELRS module socket** (SX1280 + STM32 daughterboard): all-in-one. Higher PCB risk — RF layout.

**Recommendation:** v1 on-board CRSF UART, RX module stays external. Skip the integrated RF for now.

## 5. Voltage / current monitoring

- Onboard hall-effect current sensor (e.g. ACS758) vs external power module (Mauch / Holybro).
- Mauch 200 A is what the current frame uses.

**Recommendation:** match what the airframe already has — external Mauch, FC just provides the analog input.

## 6. Logging / SD card

ArduPilot wants a microSD slot for `.bin` logs. Yes/no and where it sits mechanically.

## 7. Connector standard

JST-GH (Pixhawk standard) vs JST-SH 1.0 vs solder pads. JST-GH is bulky but matches all our existing harnesses.

## 8. PCB stack-up

4-layer minimum for a clean ground plane under the IMU. 6-layer if RF gets integrated.
