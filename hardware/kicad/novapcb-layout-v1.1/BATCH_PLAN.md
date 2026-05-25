# R4 routing batch plan (master 2026-05-22)

Per-net DRC-aware re-routing of 36 residual placements. Batches of 5-8
nets each. After each batch: DRC clean (≤baseline), commit + push,
render. Master reviews before next.

## Inventory at -mp 30 baseline (commit 1e91717)

- 29 two-pad signal nets
- 3 three-pad nets (+3V3 star, USBC_D_M_PRE star, USBC_D_P_PRE star)
- 4 one-pad residuals (I2C1_SCL, I2C1_SDA, SPI2_MISO, VREF_P) — likely
  already partially routed; investigate, may not need new route
- 7 plane-stitch via failures

Baseline DRC: 62 errors, 44 unconnected. Frozen baseline for the
batches. Pre-existing 4 shorts (MOT3/4 vs +3V3A, I2C2_SCL vs +3V3,
GND vs VCAP1) and 8 tracks_crossing are carried in from -mp 30; flag
to master as a separate cleanup.

## Batch 1 — methodology proof (RUNNING)

- 7 plane-stitch via fails: C19.1, C20.1, FB1.2, R1.1 (+3V3A);
  R53.1, R54.1, U1.100 (+3V3)
- HSE_IN (U1.12 ↔ Y1.1) — short crystal trace, MUST be short
- HSE_OUT (U1.13 ↔ C25.1) — short crystal trace, MUST be short

Goal: validate per-net DRC-aware methodology on low-risk placements.

## Batch 2 — SDMMC + SPI1 (6 nets)

Same region (MCU west edge ↔ R51-55 microSD pull-ups ↔ U3 IMU NW).
- SDMMC1_CMD, SDMMC1_D0, SDMMC1_D3
- SPI1_SCK, SPI1_MISO, SPI1_MOSI

## Batch 3 — SPI3 + IMU chip selects (6 nets)

Same region (MCU east ↔ U3/U8/U9 IMU bank).
- SPI3_SCK, SPI3_MISO, SPI3_MOSI
- IMU1_CS (U1.9 ↔ U3.10)
- IMU2_GYR_CS (U1.85 ↔ U8.5)
- IMU3_CS (U1.1 ↔ U9.12)

## Batch 4 — CAN + IMU interrupts (5 nets)

East side (MCU ↔ U14 CAN transceiver, U8/U9 IMU interrupts).
- CAN1_RX, CAN1_TX, GPIO_CAN1_SILENT (U1 ↔ U14)
- IMU2_GYR_INT3 (U1.5 ↔ U8.12)
- IMU3_INT1 (U1.41 ↔ U9.4) — was one of the route_residuals shorts;
  needs careful layer routing around USB_DM

## Batch 5 — Motors + heater + VCAP (5 nets)

South edge (J11-J15 motor connectors) + MCU.
- MOT1 (J11.1 ↔ U1.34)
- MOT2 (J12.1 ↔ U1.35)
- MOT5 (J15.1 ↔ U1.24)
- HEATER_PWM (Q5.1 ↔ U1.31)
- VCAP1 (C17.1 ↔ U1.48) — was a baseline short (GND vs VCAP1);
  fix while routing

## Batch 6 — GPS/UART + USB-CC + GND (5 nets)

Top edge + USB connector area.
- GPS1_RX (D6.1 ↔ U1.87)
- USART6_TX (D13.1 ↔ U1.63)
- USBC_CC1 (J1.A5 ↔ R31.1)
- USBC_CC2 (J1.B5 ↔ R32.1)
- GND (U1.19 ↔ U1.74) — pad-to-pad stitch on MCU

## Batch 7 — USB diff pair (2 nets, controlled impedance — DEDICATED)

- USBC_D_M_PRE star: J1.A7 ↔ J1.B7 (reversibility) ↔ U5.3
- USBC_D_P_PRE star: J1.A6 ↔ J1.B6 (reversibility) ↔ U5.1

Routed as COUPLED PAIR within USB keepout corridor (X=36.5..43.0,
Y=28..63). Width 0.30mm, gap 0.10mm, length-matched. Z_diff=94.4Ω per
docs/CONTROLLED_IMPEDANCE.md §2.4. Requires bespoke pairwise router.

## Batch 8 (audit) — single-pad residuals

VREF_P, SPI2_MISO, I2C1_SCL, I2C1_SDA each have only 1 residual pad.
Investigate: are these pads on an already-routed trace? If so, no
action. If genuinely floating, they need an end-of-net via or
trace.
