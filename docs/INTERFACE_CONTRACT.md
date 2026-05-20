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

The RC link arrives via an ELRS RP4TD receiver. The receiver's CRSF UART is wired directly into novapcb v1 (no ESP32-C6 bridge for v1; DECISIONS §4 locked the on-board-CRSF-UART path).

**Protocol-level properties:**

| Property | Value |
|---|---|
| Baud | 420 000 (8N1) |
| Frame rate | ~150 Hz |
| Telemetry ratio | 1:2 (downlink:uplink — one telemetry slot per two RC frames) |
| Channel range | u11, 172=−1, 992=centre, 1811=+1 |
| Safety channels | CH5 arm, CH6 force-disarm, CH7 mode (6-pos today, 12-pos planned) |

**novapcb v1 FC-side CRSF allocation** (Phase 2f, 2026-05-20):

| Property | Value |
|---|---|
| ArduPilot SERIAL slot | `SERIAL7` (= USART6 per `SERIAL_ORDER` index 7 in `hwdef.dat`) |
| USART pin (RX) | PC7 — inherited from MatekH743-bdshot hwdef.dat:19 via Phase 2e amendment |
| USART pin (TX) | PC6 — inherited from MatekH743-bdshot hwdef.dat:20 |
| `SERIAL7_PROTOCOL` default | `23` (RCIN) — set in `firmware/hwdef-novapcb/defaults.parm`; inherited from `MatekH743-bdshot/defaults.parm` |
| `SERIAL7_BAUD` default | `420` (= 420 000 baud) — novapcb-specific 1-number deviation from bdshot's `115` per DECISIONS §4 CRSF lock |
| Inversion / half-duplex | None at hwdef level. ArduPilot CRSF driver handles polarity at protocol layer (CRSF is non-inverted at TTL). Grep across both MatekH743 + MatekH743-bdshot confirms zero `RXINV`/`TXINV`/`HALF_DUPLEX` flags. |
| FT-pin verification | Deferred. PC7 is bdshot-inherited (production-validated on MatekH743-bdshot shipping hardware). Phase 6e sim can measure edge-rate / 5 V-tolerance on real silicon when available. |
| Out-of-box behavior | User flashes novapcb-v1 firmware, plugs ELRS RX into the CRSF UART connector → CRSF works at 420 kbaud without further GCS configuration. |

**Sign convention** (do not "fix" in firmware): phone-side has already negated pitch before transmitting. FC sees drone-convention values directly. Re-negating crashes the drone — this bug was caught in v0 review.

**Link-loss guard**: if no CRSF frame for >300 ms, stop sending MANUAL_CONTROL and let ArduPilot's `FS_THR_*` failsafe fire. Do not synthesize neutral sticks.

## ESC outputs

| Property | Value |
|---|---|
| Channel count | **8 channels locked** (DShot300/600 preferred, PWM fallback) — see DECISIONS #3. Inherited from MatekH743-bdshot variant PWM 1-8 per Phase 2e amended 2026-05-20. |
| Protocol | DShot300 / DShot600 standard direction on all 8 channels; PWM fallback. **4/8 BIDIR-DShot enabled** (motor RPM telemetry on PB0/PA0/PA2/PD12 — one per timer per H743 "one BIDIR per timer" constraint). |
| Connector | TBD — JST-SH 1.0 or solder pads |

**Locked pin / timer / channel / BIDIR assignment** (Phase 2e amended, MatekH743-bdshot inheritance, lines 23-30):

| PWM # | Pin | Timer | Channel | GPIO# | BIDIR |
|---:|---|---|---|---:|:---:|
| 1 | PB0  | TIM3 | CH3  | 50 | ✓ |
| 2 | PB1  | TIM3 | CH4  | 51 | — |
| 3 | PA0  | TIM2 | CH1  | 52 | ✓ |
| 4 | PA1  | TIM2 | CH2  | 53 | — |
| 5 | PA2  | TIM5 | CH3  | 54 | ✓ |
| 6 | PA3  | TIM5 | CH4  | 55 | — |
| 7 | PD12 | TIM4 | CH1  | 56 | ✓ |
| 8 | PD13 | TIM4 | CH2  | 57 | — |

**DMA isolation:** `DMA_NOSHARE SPI1* TIM3* TIM2* TIM5* TIM4*` — motor timers get dedicated DMA streams, no conflict with SPI1 (IMU). Pattern matches MatekH743-bdshot exactly.

**Channels intentionally NOT exposed on novapcb v1** (available on MatekH743 base but trimmed per DECISIONS §3's 8-channel cap):

- PWM 9: PD14 TIM4_CH3
- PWM 10: PD15 TIM4_CH4
- PWM 11: PE5 TIM15_CH1
- PWM 12: PE6 TIM15_CH2
- PWM 13: PA8 TIM1_CH1 (WS2812 LED — no documented novapcb v1 LED requirement)

These pins are *available on the H743* if a future v1.x respin needs more channels; not routed in v1.

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
| VBAT input | 4S–6S LiPo monitoring (16 V – 26 V) — **via external Mauch HS-200-LV power module** per `DECISIONS.md §5` (Mauch 200A pinned) + CLAUDE.md §3.6 (4-6S → LV variant, max 28V). Module provides voltage-divided VBAT line (9:1 1% resistor divider) + offset-shifted Hall-effect current sensor output (ACS-250U, 0V=0A → 3.3V=200A); novapcb has NO onboard power circuit. |
| 5 V in | from external BEC, ≥3 A |
| 3.3 V | on-board LDO for sensors / MCU |
| USB 5 V | for bench bring-up only; do not power motors from USB |

**novapcb v1 FC-side power-monitor allocation** (Phase 2g, 2026-05-20):

| Property | Value |
|---|---|
| BATT (primary) voltage ADC pin | PC0 — `ADC1`, channel index `HAL_BATT_VOLT_PIN 10`. Inherited from MatekH743. |
| BATT (primary) current ADC pin | PC1 — `ADC1`, channel index `HAL_BATT_CURR_PIN 11`. Inherited from MatekH743. |
| BATT2 (secondary) voltage ADC pin | PA4 — `ADC1`, channel index `HAL_BATT2_VOLT_PIN 18`. Inherited from MatekH743 as harmless scaffolding; `BATT_MONITOR2 = 0` default → unused at runtime. Removal queued for Phase 2-exit. |
| BATT2 (secondary) current ADC pin | PA7 — `ADC1`, channel index `HAL_BATT2_CURR_PIN 7`. Same status as BATT2 voltage. |
| `BATT_MONITOR` default | `4` (Analog Voltage + Current) via `HAL_BATT_MONITOR_DEFAULT 4` — correct for Mauch analog VBAT + Hall current. |
| `BATT_VOLT_MULT` default | **`9.0`** via `HAL_BATT_VOLT_SCALE 9.0` — researched Mauch HS-200-LV 9:1 divider typical. Replaces inherited Matek-onboard `11.0` (which described Matek's onboard divider — wrong hardware for novapcb). Per-unit precision: user enters the value from the Mauch sensor's final-test calibration card (typical ±1-3% deviation). |
| `BATT_AMP_PERVLT` default | **`60.6`** via `HAL_BATT_CURR_SCALE 60.6` — researched Mauch HS-200 typical (200A unidirectional over 0-3.3V analog full-scale, ACS-250U hall sensor with offset shifting). Replaces inherited Matek-onboard `40.0` (Matek's onboard current sensor — wrong hardware for novapcb). Per-unit precision: user enters the value from the Mauch sensor's final-test calibration card. |
| `BATT2_VOLT_MULT` default | `11.0` (inherited Matek) — `BATT2` is `#ifdef`-guarded and `BATT_MONITOR2` defaults to `0` (never read). Harmless cruft; removal queued for Phase 2-exit. |
| Pre-calibration UX | Failsafes (`BATT_LOW_VOLT`, `BATT_CRT_VOLT`) function approximately on first power-up with the typical Mauch HS-200-LV defaults, and become precise after the user enters their unit's per-unit calibration card values. No "ship broken to force calibration" sentinel mode (that would leave uncalibrated users with no failsafe protection, strictly more dangerous than 0-3% calibration error). |
| HV variant note | If a future Nova frame switches to HS-200-HV (>6S, up to 14S), update `HAL_BATT_VOLT_SCALE 9.0 → 18.0` (HV uses 18:1 divider). Current calibration (`60.6`) is unchanged — HV and LV share the same ACS-250U hall sensor. |
| ADC peripheral | ADC1 (all 4 BATT pins). MatekH743 + Pixhawk6X both use ADC1 for primary battery monitoring; H743V (LQFP-100) exposes all 4 channels. |
| DMA | ADC DMA uses DMA2 streams, no conflict with Phase 2e's `DMA_NOSHARE SPI1* TIM3* TIM2* TIM5* TIM4*` (those are on DMA1 or other DMA2 streams). |
| Sources | Mauch HS-200-HV product page (`mauch-electronic.com/products/076-hs-200-hv` — ACS-250U sensor + "0.0V (0A) until 3.3V" full-range claim); Craft & Theory listing for Mauch 075 HS-200-LV (`craftandtheoryllc.com/store/mauch-075-hs-200-lv/` — "up to 6S max 28V for LV version"); ArduPilot wiki Mauch page (`ardupilot.org/copter/docs/common-mauch-power-modules.html` — divider 9:1 (LV) and 18:1 (HV), per-unit calibration card workflow). |

## Ports the Pi expects to reach (none directly on the FC)

These are software ports on the Pi for reference only — the FC never opens TCP sockets. Listed so firmware bring-up scripts can verify the Pi-side stack came up cleanly:

- `127.0.0.1:8080` — drone-control FastAPI (calibration / mission / params / fence)
- `127.0.0.1:8081` — vision-detect (Hailo)
- MongoDB on `:27017`
