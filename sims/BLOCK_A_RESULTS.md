# Step 6 Block A — routed-trace SI results

Date: 2026-05-21
Branch: `sim/step6-block-a-routed-si`
Input: `sims/trace_geometry.json` (extracted from the merged Step 5 board at main 0f1548f)
Run: `sims/run_block_a_routed_si.py`
Stackup: JLC06161H-7628 (CONTROLLED_IMPEDANCE.md §1)

## Summary

| Sub | Subsystem | Verdict | Detail |
|---|---|---|---|
| **6b** | USB diff pair | **FAIL** | ~21 mm of each diff line is on In3.Cu (+5V plane layer) → Z_diff ≈ 25 Ω in that section (vs USB 2.0 spec 76.5..103.5 Ω). |S11| at F.Cu↔In3.Cu transition ≈ -4 dB (spec <-15 dB). **Design change required: reroute USB on F.Cu only.** |
| **6c** | IMU SPI | **MARGINAL** | All 4 SPI1 nets show modeled overshoot 354-489 mV at the IMU pin (criterion: ≤200 mV). Rise times 1.45 ns (PASS, <5 ns). Cause: lumped LRC model with 30 Ω driver + 13 nH/5 pF trace + 10 pF load resonates. **Disposition needs master adjudication: series-term R fix vs §2 criterion review (lumped model is conservative; real distributed TL + ICM-42688 ESD clamps would reduce observed overshoot)**. |
| **6f** | SDMMC | **PASS** | 6/6 SDR25 lines at 12.5 MHz. Lengths 18..36 mm; overshoot ≤53 mV; rise time ~2.5 ns. Lumped regime; slow SDMMC undemanding. |
| **6g** | DShot | **PASS** | 8/8 MOT lines at DShot600 (600 kHz). Lengths 38..58 mm; overshoot ≤45 mV; rise time ~7.9 ns. Trace electrically short at 600 kHz. |

## Findings

### 6b USB diff pair — FAIL

Extracted geometry:

| Net | Total | F.Cu | In3.Cu | Vias |
|---|---|---|---|---|
| USB_DM | 30.24 mm | ~9 mm | **21.27 mm continuous** | 2 |
| USB_DP | 28.59 mm | ~5 mm | **23.57 mm continuous** | 2 |

Stackup probe (verified by reading actual zone fills on the board): In3.Cu = +5V plane (NOT GND as a USB microstrip would require). Each diff line transitions F.Cu → via → In3.Cu (~21 mm) → via → F.Cu.

Analytical impedances (H-J microstrip + Wheeler stripline + IPC-2141 edge-coupled):

| Section | Z_se (Ω) | Z_diff (Ω) | In USB 2.0 ±15% spec [76.5,103.5]? |
|---|---|---|---|
| F.Cu microstrip (Step 5 design intent) | 68.7 | 95.6 | **YES** |
| In3.Cu stripline (close-plane dominant b=2·0.109 mm) | 14.0 | **25.4** | NO (far below) |
| Far-plane-only theoretical bound | 60.9 | 89.3 | YES |

Via-transition reflection (per-line, single-ended): |Γ| = |68.7-14.0| / (68.7+14.0) = **0.66**, |S11| ≈ **-3.6 dB**. Spec is < -15 dB (|Γ| < 0.18). Massive discontinuity.

**Root cause guess**: USB net class allowed all signal layers (Default class). Freerouter chose In3.Cu for a long straight run. Net class should have been layer-constrained to F.Cu (or B.Cu) only at the Step 5 setup.

**Proposed design change**: hand-route USB_DM/USB_DP on F.Cu only, end-to-end, ref'd to In1.Cu (L2 GND). Restores Z_diff = 95.6 Ω microstrip. Board has 80×60 mm — room for a ~30 mm F.Cu-only pair from USB-C J1 to MCU PA11/PA12.

### 6c IMU SPI — MARGINAL

| Net | Length | Vias | Layers | Modeled overshoot | Verdict |
|---|---|---|---|---|---|
| SPI1_SCK | 45.22 mm | 2 | F.Cu, In2.Cu | 489.4 mV | over |
| SPI1_MISO | 43.33 mm | 2 | F.Cu, In2.Cu | 462.8 mV | over |
| IMU1_CS | 44.82 mm | 2 | F.Cu, In2.Cu | 483.9 mV | over |
| SPI1_MOSI | 35.76 mm | 2 | F.Cu, In2.Cu | 354.7 mV | over |

Pass criterion (SIMULATION_PLAN §6c): no ringing >200 mV. Rise time ≤5 ns met (all ~1.45 ns).

Why the modeled overshoot: lumped LRC tank with R_drv = 30 Ω (STM32H743 GPIO very-high-speed slew), L ≈ 13 nH, C ≈ 5 pF (trace) + 10 pF (ICM-42688 input). Q = (1/R)·√(L/C) ≈ 1.7 → moderate overshoot at the first peak.

Conservatism notes:
- Lumped LRC ignores distributed dielectric/skin loss that damps HF resonance.
- ICM-42688 input has ESD clamp diodes that bound overshoot at ~V_DD+0.6 V = 3.9 V; modeled 3.79 V peak is below that clamp threshold (so no clamp action; functionally tolerated, with body-diode current excursion only above 3.9 V).
- Real distributed TL + IBIS-class driver would predict lower overshoot.

Disposition options for master adjudication:
- **(D1)** Add 22 Ω series termination R at MCU pin on SCK/MOSI/CS (3 footprints) — eliminates ringing in any model, costs 3 0402 resistors, requires schematic + placement + reroute.
- **(D2)** §2 criterion review: model is conservative; observed peak 3.79 V is below the 3.9 V ESD-clamp threshold; ICM-42688 datasheet absolute max V_IN = V_DD + 0.5 V = 3.8 V. Marginal but no functional failure at modeled peak.
- **(D3)** Hand-route IMU SPI on F.Cu only to remove In2.Cu transitions — small Q reduction, but doesn't eliminate the LRC tank.

### 6f SDMMC — PASS

| Net | Length | Vias | Overshoot | Rise |
|---|---|---|---|---|
| SDMMC1_CLK | 18.45 mm | 2 | 0.5 mV | 2.51 ns |
| SDMMC1_CMD | 35.61 mm | 2 | 50.4 mV | 2.46 ns |
| SDMMC1_D0 | 34.65 mm | 2 | 46.7 mV | 2.46 ns |
| SDMMC1_D1 | 24.01 mm | 2 | 10.3 mV | 2.49 ns |
| SDMMC1_D2 | 36.23 mm | 2 | 52.9 mV | 2.46 ns |
| SDMMC1_D3 | 33.12 mm | 1 | 40.7 mV | 2.46 ns |

12.5 MHz SDR25 with edge ~3 ns + driver R=50 Ω → Q lower than IMU case. All clear.

### 6g DShot — PASS

| Net | Length | Vias | Overshoot | Rise |
|---|---|---|---|---|
| MOT1 | 58.00 mm | 2 | 44.9 mV | 7.88 ns |
| MOT2 | 50.71 mm | 3 | 37.0 mV | 7.90 ns |
| MOT3 | 37.88 mm | 2 | 20.9 mV | 7.95 ns |
| MOT4 | 38.51 mm | 2 | 21.7 mV | 7.95 ns |
| MOT5 | 43.60 mm | 2 | 28.1 mV | 7.93 ns |
| MOT6 | 48.19 mm | 2 | 33.9 mV | 7.91 ns |
| MOT7 | 45.15 mm | 2 | 30.0 mV | 7.92 ns |
| MOT8 | 51.18 mm | 2 | 37.6 mV | 7.90 ns |

DShot600 (600 kHz). Trace electrically tiny at this frequency. Trivially passes.

## V&V (Phase 0.6 bar)

Each computation has a trusted-reference floor:
- Microstrip Z0: Hammerstad-Jensen formulation (Pozar §3.8, IPC-2141 reference).
- Stripline Z0: Wheeler / Cohn formula (Pozar §3.7, IPC-2141 §3.6.6).
- Diff-pair factor: IPC-2141 edge-coupled approximation (Cohn).
- Lumped L/C from Z0 and v_p = c0/√εeff.
- ngspice 46 for transient circuit response (validated tool).

No tolerances loosened. The criteria are the SIMULATION_PLAN.md ones; 6b/6c fall short and are surfaced as findings, not quietly converted to PASS.

## Decisions deferred to master

1. **6b USB**: reroute on F.Cu only (recommended) — escalated separately.
2. **6c IMU SPI**: D1 (series-term R) vs D2 (§2 criterion review) vs D3 (route-only fix) — awaiting adjudication.
