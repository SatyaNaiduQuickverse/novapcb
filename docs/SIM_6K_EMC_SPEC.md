# Sim 6k — EMC / RF coupling sim (spec)

> **Status:** SPEC 2026-05-30 by master per Sai T8 raise-the-bar directive.
> **Worker action:** implement + run + commit results to `docs/SIM_6K_EMC_RESULT.md`.
> **Purpose:** validate that the TPS62177 buck switching node + DShot motor edges don't couple unacceptably into IMU SPI lines, baro I²C, or Mauch analog sense. Closes the Phase 6k gate item CONFIDENCE_MAP row 12 committed to.

---

## 1. Aggressors + victims

| Aggressor | Frequency / edge rate | Mechanism |
|---|---|---|
| **TPS62177 buck switching node (U2)** | ~1.8 MHz fundamental, fast edges (3–5 ns) | E-field + H-field coupling to nearby traces |
| **DShot300 motor edges (MOT1-6 @ J11)** | 300 kbit/s NRZ, ~30 ns edge | E-field via radiated emission from motor pigtail (treat as antenna) |
| **CRSF UART (USART6 PA0/PA1)** | 420 kbaud burst, ~50 ns edge | E-field on UART trace + connector pigtail |
| **USB-CDC (PA11/PA12)** | 12 Mbps full-speed, 4 ns edge | E-field on diff pair (already controlled-impedance per Sim 2; check fan-out region) |

| Victim | Sensitivity | Headroom |
|---|---|---|
| **ICM-42688-P SPI1 (PA5/PA6/PA7/PC15)** | Bit-error if jitter > 8 ns on SCK | SCK ~16 MHz operational |
| **BMI088 SPI2 (PB13-PB15 + PD4)** | Bit-error if jitter > 10 ns | SCK ~10 MHz operational |
| **LSM6DSV16X SPI3 (PB3-PB5)** | Same as ICM | SCK ~10 MHz |
| **DPS310 I²C2 (PB10/PB11) + LPS22HB** | Bit-error if jitter > 50 ns | I²C ~400 kHz |
| **Mauch V/I sense (PA0→ADC1_IN16, PA1→ADC1_IN17)** | ±10 mV noise tolerable | already RC-filtered 1.59 kHz |
| **IMU INT lines (PB1, PD4, [PE7 polled])** | Spurious edge = false sample | rising-edge sensitive |

## 2. Coupling models

- **E-field (capacitive crosstalk)**: parallel-trace approximation. C_couple ≈ ε × L_parallel / spacing. Significant when L_parallel × dV/dt > V_threshold × C_load.
- **H-field (inductive crosstalk)**: loop-area dependent. Mutual M ≈ µ × L × log(d/r). Significant on the buck switching loop.
- **Radiated (motor pigtail antenna)**: treat the 100-200mm motor lead as a quarter-wave dipole at the harmonic content; near-field coupling to nearby traces drops as 1/d³.

## 3. Sim approach (worker call: openEMS or skrf-microstrip + 3D EM)

Two-stage approach (cheap → expensive):

**Stage 1: trace geometry crosstalk (skrf or analytical)**
- Extract trace lengths + parallel runs from .kicad_pcb for each victim/aggressor pair
- Compute parallel-trace coupling per IPC-2141
- Identify pairs with >10dB above threshold
- Cost: ~1 hr scripted

**Stage 2: full-wave EM (openEMS) on flagged pairs only**
- Re-run only the worst-case coupling pairs through openEMS
- Validate Stage 1 estimates within 6dB
- Cost: ~4-8 hrs for ~5 pairs

If Stage 1 shows all pairs comfortably under threshold → skip Stage 2 + ship the analytical result + Phase 9 bench validates.

## 4. Pass criteria

| # | Gate | Why |
|---|---|---|
| 6k.A | Buck → IMU SPI: coupled noise on SCK edge < 1/4 V_IL (≤ 0.4V) at any operating point | No bit error |
| 6k.B | Buck → IMU INT: coupled noise on INT line < 1/2 V_threshold (≤ 0.8V) | No spurious interrupt |
| 6k.C | DShot300 → IMU SPI: coupled noise < 1/4 V_IL | Motor edges don't corrupt IMU |
| 6k.D | CRSF UART → IMU SPI: coupled noise < 1/4 V_IL | RC link doesn't corrupt IMU |
| 6k.E | All aggressors → Mauch V/I ADC: ≤ ±10 mV after RC filter | Telem unaffected |
| 6k.F | USB-CDC fan-out region: trace crosstalk to nearby F.Cu signals < -20 dB at 12 MHz | USB doesn't corrupt SDMMC1 (lives in same NE corridor) |

## 5. Tool

- Worker decides: openEMS (full-wave 3D, slow) vs skrf-microstrip (analytical, fast) vs hybrid
- Reference existing controlled-impedance sims (Sim 2 USB Z, Sim 4 CAN Z) for openEMS setup
- Run on worker per Sai's "sims on the Pi" memory

## 6. Output

Worker commits `docs/SIM_6K_EMC_RESULT.md` with:
- Stage 1 analytical coupling table (every aggressor/victim pair)
- Stage 2 openEMS results for flagged pairs (if any)
- Per-gate PASS/FAIL + the worst-case coupling number
- If FAIL: identification of which trace pair + fix proposal
- Update CONFIDENCE_MAP row 12 to HIGH if all 6 gates PASS

## 7. If a gate fails

**No corner cuts** — fix the layout, don't relax the gate. Likely fixes:
- **6k.A/B fail (buck→IMU)**: increase buck-to-IMU distance (currently ≥ 25 mm per master condition); add ground guard trace between buck switching node and IMU SPI; re-route buck output via inner layer
- **6k.C fail (DShot→IMU)**: re-route motor traces deeper into inner layers; add GND guard between MOT and IMU; check that MOT* runs don't parallel SPI* for > 5 mm
- **6k.D fail (CRSF→IMU)**: re-route CRSF UART deeper; add GND stitching between CRSF connector and IMU island
- **6k.E fail (any→Mauch ADC)**: tighter RC (drop C from 100 nF to 220 nF for lower 720 Hz cutoff)
- **6k.F fail (USB-CDC fan)**: this was flagged as `phase4-dfm-usb-fan` already RESOLVED — if FAILs here re-open

Per Sai directive: any fail triggers design iteration, not gate relaxation.
