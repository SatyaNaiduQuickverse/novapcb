# PR — T3 partial: MOT3-6 routing (task #49)

> Branch `hw/t3-partial-mot3-6` off `sch/option-b-buck`. Routes the 4 currently-
> unrouted south-edge motor outputs (MOT3-6 = PE9/PE11/PE13/PE14, TIM1) from the
> MCU to J11.3-6 on a **B.Cu-primary** path. MOT7-8 stay unrouted (Sai option D).
> Survey: `docs/T3_PARTIAL_SURVEY.md`.

## 1. What changed

MOT3-6 routed (each ~50–53 mm, 3 wires + 2 vias): **MCU F.Cu exit stub → via-drop
(≈Y48, just S of the R12/C51/C17 footprint band) → B.Cu south run → via → J11
F.Cu pad.** Via scoped Freerouting (4 nets, B+F), converged in 38 s.

This is the **flight-critical** motor routing. The prior F.Cu corridor-redesign
attempts failed twice (148 then 49 DRC) — the F.Cu corridor is saturated (~9
sensor-bus crossings, made worse by the +I2C1 crossings from GPS PR #101).

## 2. Why B.Cu-primary (the reframe that worked)

The survey's actual-density count: **F.Cu ~9 crossings** (I2C1_SCL/SDA, I2C2_SCL/SDA,
SPI1_SCK/MISO/MOSI, IMU1_CS, IMU3_CS) + 3 footprints, vs **B.Cu ~3-4** (IMU2_GYR_CS,
SPI3_MOSI, IMU2_ACC_INT1). Routing the MOT3-6 south run on **B.Cu** (the 2-3×
lower-density layer) sidesteps the saturated F.Cu field. DShot (≤600 kHz digital)
on B.Cu referenced to In4 GND is electrically equivalent to F.Cu over In1 GND —
no SI/length concern. Same craft as the SPI3 B.Cu wraparound (PR #77). Freerouting,
forced onto B.Cu by the fixed F.Cu traffic, wove the 4 MOT runs between the few
B.Cu crossings and converged.

## 3. Verification (5-gate)

| Gate | Result |
|---|---|
| DRC | **0 new errors.** This branch (pre-#106) shows 21 = pre-existing baseline; MOT-area violations = **0**. (On merge to sch/option-b-buck, #106's net-assigns resolve those to 12.) |
| STACKUP-SPEC-MATCH | **PASS** (4 plane pairs match DECISIONS §8) |
| MIRROR / DECOUPLING / audit | **PASS** — all layout-compliance checks clean, no new warnings |
| Connectivity | **MOT3-6: 0 unconnected** (all 4 fully routed MCU→J11). MOT7-8: 2 unconnected — **expected** (deferred per Sai option D) |
| Cluster walk | MOT3-6 **PASS** — B.Cu runs over In4 GND, F.Cu exit/entry stubs over In1 GND, continuous |

## 4. Notes

- **MOT7-8 (PB8/PB9, TIM4) stay unrouted** per Sai option D (quad/hex pilot, no
  octo). hwdef defines all 8 PWM channels; ArduPilot sees MOT7-8 as "not present"
  at runtime — no boot failure. v2 routes them if octo is pursued.
- **6/8 motors routed** = full quad + hex capability for v1.
- Freerouting net-name quoting: MOT3-6 emit **unquoted** in the SES (plain
  alphanumeric); the SES-apply regex handles both quoted + unquoted (per the
  earlier BUZZER lesson).
