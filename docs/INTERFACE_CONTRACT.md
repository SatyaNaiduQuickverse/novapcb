# Interface contract

The hard pin-level / protocol constraints the FC must honor to drop into the existing Nova stack. Numbers come from `~/drone_handoff/PROMPT.md` and the `~/novaros` compose file. If you're about to deviate from anything here, raise it in OPEN_QUESTIONS.md first — most of these are load-bearing for software written months ago.

## Primary host link — USB-CDC MAVLink

| Property | Value | Source |
|---|---|---|
| Transport | USB 2.0 full-speed, CDC-ACM | drone-control container expects /dev/ttyACM* |
| Baud (logical) | 115200 8N1 | drone-control config |
| Protocol | MAVLink v2, ArduPilot dialect | MAVROS depends on this |
| Identifier | Must enumerate as `usb-ArduPilot_*` for udev by-id pinning | drone_handoff/PROMPT.md serial pinning section |

**USB descriptor fields (load-bearing for the udev by-id path above):**

| Field | Value | Notes |
|---|---|---|
| `USB_VID` | TBD (ArduPilot allocation) | See DECISIONS #9. |
| `USB_PID` | TBD (ArduPilot allocation) | See DECISIONS #9. |
| `USB_VENDOR_STRING` | TBD; **must start with `ArduPilot`** | udev composes `usb-{VENDOR}_{PRODUCT}_{SERIAL}` (spaces → underscores); the `ArduPilot_*` glob in drone-side scripts matches on this prefix. |
| `USB_PRODUCT_STRING` | TBD | Concatenated after the vendor string in the by-id path. |
| `USB_SERIAL` | non-empty, unique-per-unit | If two FCs share a serial (or one is empty), udev by-id symlinks alias and the wrong device opens. |

udev only requires the **strings** prefix to match — VID/PID are not part of the by-id name. They still matter for any downstream consumer (some GCSs) that filters on VID/PID.

## RC input — CRSF over UART

The RC link arrives via an ELRS RP4TD receiver. Today this is bridged through an ESP32-C6 on USB; if the FC has a spare 5V-tolerant UART we may move CRSF directly onto the FC instead.

| Property | Value |
|---|---|
| Baud | 420 000 (8N1) |
| Frame rate | ~150 Hz |
| Telemetry ratio | 1:2 (downlink:uplink — one telemetry slot per two RC frames) |
| Channel range | u11, 172=−1, 992=centre, 1811=+1 |
| Safety channels | CH5 arm, CH6 force-disarm, CH7 mode (6-pos today, 12-pos planned) |

**Sign convention** (do not "fix" in firmware): phone-side has already negated pitch before transmitting. FC sees drone-convention values directly. Re-negating crashes the drone — this bug was caught in v0 review.

**Link-loss guard**: if no CRSF frame for >300 ms, stop sending MANUAL_CONTROL and let ArduPilot's `FS_THR_*` failsafe fire. Do not synthesize neutral sticks.

## ESC outputs

| Property | Value |
|---|---|
| Channel count | 8 (DShot300/600 preferred, PWM fallback) — see DECISIONS #3 |
| Protocol | DShot300 / DShot600 preferred; PWM fallback |
| Connector | TBD — JST-SH 1.0 or solder pads |

## Sensors required for ArduCopter parity

| Sensor | Notes |
|---|---|
| IMU (primary) | **ICM-42688-P on SPI1**, MODE3, 2 MHz init / 16 MHz operational. CS = `IMU1_CS` (PC15). Polled (DRDY pin deferred — see `OPEN_QUESTIONS.md` "IMU DRDY pin"). Driver: ArduPilot `Invensensev3`. Locked Phase 2a 2026-05-18 — `DECISIONS #5 / CLAUDE.md §3.5`. |
| IMU (secondary) | Parked. CLAUDE.md §3.5 allows "ICM-42688-P or BMI088"; sub-phase TBD. Don't add a second IMU until that decision lands. |
| Barometer | **DPS310 on I²C2 at 0x76** (SDO tied to GND). Bus index 0 in I2C_ORDER. Driver: ArduPilot built-in `DPS310` baro driver. Locked Phase 2b 2026-05-20 — `CLAUDE.md §3.5` (DPS310 preferred over BMP388 per noise floor). Divergence from Pixhawk6X intentional (6X uses BMP388/BMP581/ICP201XX). |
| Magnetometer | **External via I²C, IST8310 (primary) + RM3100 (alternative), both on `ALL_EXTERNAL` buses**. IST8310 at 0x0E, RM3100 at 0x20, both `ROTATION_NONE` defaulted with `HAL_COMPASS_AUTO_ROT_DEFAULT 2` for runtime auto-detect. No internal compass per `CLAUDE.md §3.5`. Specific I²C bus → GPS-connector mapping is a Phase 4 layout decision. Locked Phase 2c 2026-05-20. SOTA: CUAV-Nora/X7/CarbonixF405 same pattern. |
| GPS | **GPS1 on USART2 (PD5 TX / PD6 RX) = SERIAL3 in SERIAL_ORDER; GPS2 on USART3 (PD8 TX / PD9 RX) = SERIAL4.** Compass shares the GPS connector via I²C: both `I2C1` (PB6/PB7) and `I2C2` (PB10/PB11) are exposed; `HAL_I2C_INTERNAL_MASK 0` makes both buses external, so `ALL_EXTERNAL` (used by Phase 2c COMPASS lines) covers whichever bus is physically wired to the GPS connector. Specific GPS-connector → I²C-bus pinout is a Phase 4 layout decision. Verified Phase 2d 2026-05-20 — inherited from MatekH743 unchanged. |

## Power

| Rail | Spec |
|---|---|
| VBAT input | 4S–6S LiPo monitoring (16 V – 26 V) |
| 5 V in | from external BEC, ≥3 A |
| 3.3 V | on-board LDO for sensors / MCU |
| USB 5 V | for bench bring-up only; do not power motors from USB |

## Ports the Pi expects to reach (none directly on the FC)

These are software ports on the Pi for reference only — the FC never opens TCP sockets. Listed so firmware bring-up scripts can verify the Pi-side stack came up cleanly:

- `127.0.0.1:8080` — drone-control FastAPI (calibration / mission / params / fence)
- `127.0.0.1:8081` — vision-detect (Hailo)
- MongoDB on `:27017`
