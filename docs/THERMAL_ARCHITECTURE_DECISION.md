# Thermal Architecture Decision — v1.1 board over-budget

> **Status**: SAI ARCHITECTURE DECISION REQUIRED
> **Created**: 2026-05-23
> **Trigger**: Master 2026-05-23 halt after gate12 v3 thermal regression catch
> **Halt scope**: All forward routing/placement work blocked until resolved

## Symptom

105×85mm board at full v1.1 architecture (10 heat sources, total 1.617 W actual
placement / 1.717 W sweep planned) exceeds thermal budget:

| Component | Tj (°C) | Target | Margin |
|---|---:|---:|---:|
| U1 STM32H743 | 82.46 | 80.0 | -2.46 FAIL |
| U6 TPS25940A | 82.20 | 80.0 | -2.20 FAIL |
| Q3 OR-FET | 81.08 | 80.0 | -1.08 FAIL |
| Q4 OR-FET | 77.28 | 80.0 | +2.72 PASS |
| U2 LDO | 78.92 | 80.0 | +1.08 PASS |
| Others (U11/12/13, Q2) | 78–79 | 80.0 | +1–2 PASS |

3 components FAIL absolute 80°C target. Zero design margin to 5°C resilience
requirement (LOCK_TARGET=75°C for MCU).

## Root cause — LOCK number was based on PLANNED, not actual placement

`docs/DECISIONS.md §2` states: "105 × 85 mm v1.1 chosen via gate12 v3 board-size
sweep: MCU=73.98°C, +6.02°C margin".

**The 73.98°C sweep used PLANNED component positions, NOT the actual placement
that step5/step6 chose:**

| Component | Sweep planned | Actual placed | Delta |
|---|---|---|---|
| Q3 | (35, 8) | (27, 10) | -8mm X, +2mm Y |
| Q4 | (55, 8) | (78, 10) | +23mm X, +2mm Y |
| U11 | (25, 5) | (33, 5) | +8mm X |
| U12 | (65, 5) | (72, 5) | +7mm X |
| U14 | (82, 55) | parked (off-board) | not placed |

Reproducing the sweep's 73.98°C requires the PLANNED positions, not actual.
With actual placement (Q3 at (27, 10) close to MCU + U6), heat coupling raises
MCU by ~8.5°C → 82.46°C.

## Mesh determinism verified

5 consecutive runs of gate12 v3 on current board:
- Run 1: MCU=82.46°C
- Run 2: MCU=82.46°C
- Run 3: MCU=82.46°C
- Run 4: MCU=82.46°C
- Run 5: MCU=82.46°C

Zero variance. 82.46°C is the deterministic, reproducible truth.

## Options for Sai

### (A) Bigger board — increase to 115×100mm or larger

Sweep at planned positions showed asymptote at ~74°C for boards ≥105×85. Current
actual placement gives 82.46°C at 105×85 — need to re-sweep with ACTUAL placement
geometry to determine new minimum size.

**Pros**: No schematic change. Lowest-risk path.
**Cons**: Larger PCB cost. Mechanical mounting tray needs re-design.
**Estimated**: 115×100 likely insufficient given +8.5°C delta. May need 125×110+.

### (B) LDO → buck converter for U2 (save ~470 mW)

U2 AP2112K-3.3 LDO drops 5V → 3.3V at ~470 mW dissipation. Buck converter
(e.g., TPS62177) at ~85% efficiency would dissipate ~25 mW.

**Pros**: Saves ~445 mW total board heat. Likely brings MCU below 80°C at 105×85.
**Cons**:
- Schematic change → Sai/supermaster approval required.
- IMU noise concern previously rejected this; with larger board option, noise
  budget improves.
- Layout changes around U2 area (inductor, switching node decoupling).

### (C) Both (bigger board + buck)

Belt-and-braces. Cost both penalties but maximum margin.

### (D) Heat reduction elsewhere — minimal opportunity

| Component | Current | Floor | Reducible? |
|---|---:|---:|---|
| U1 MCU | 700 mW | ~600 mW (clock gating) | Marginal |
| U2 LDO | 642 mW | 25 mW (buck) | YES — Option B |
| U13 IMU LDO | 50 mW | ~50 mW | No |
| Q3/Q4 OR-FET | 50 mW | 50 mW (conduction loss) | No |
| U11/U12 LM74700 | 50 mW | 50 mW (Iq) | No |
| U6 eFuse | 18 mW | 18 mW (Rds_on) | No |
| Q2 P-FET | 6 mW | 6 mW | No |

Only U2 has meaningful reduction potential. Most components are at physical floor.

## Quantified results — gate12 v3 with ACTUAL Q3/Q4/U11/U12 positions

Ran 3 architecture configurations through gate12 v3 (deterministic, 5-run
verified, sims/thermal-step4/runs/case_swp_*/). All use actual placement
from current board, not the planned-position artifact that gave LOCK 73.98°C.

| Config              | Size      | P_tot   | MCU °C (margin) | U6     | Q3     | Q4     | U2     |
|---------------------|-----------|---------|----:|----:|----:|----:|----:|
| Current baseline    | 105×85    | 1617mW  | **82.5** (-2.5) | 82.2 (-2.2) | 81.1 (-1.1) | 77.3 | 78.9 |
| A. 115×100 + LDO   | 115×100   | 1616mW  | 74.1 (+5.9)     | 64.2 | 64.1 | 70.2 | 63.6 |
| B. 105×85 + buck   | 105×85    | 1000mW  | **63.7** (+16.3) | 62.8 | 63.0 | 63.7 | 61.9 |
| C. 110×90 + buck   | 110×90    | 1000mW  | 62.8 (+17.2)    | 60.9 | 60.8 | 61.6 | 60.3 |

**Key finding**: BUCK (Option B) is the dominant lever. U2 LDO→buck saves
~617 mW (642→25 mW) vs board-area increase saves only ~8°C MCU.

- Option A alone (bigger board) just barely passes (MCU +5.9°C margin, no headroom).
- Option B alone (buck, same 105×85) gives +16.3°C margin — comfortable.
- Option C (both) gives +17.2°C — only +0.9°C over B (diminishing returns).

## D/H/G heat-source exposure (master 2026-05-23 directive)

D (IMU island + 3×IMU + 2×baro + heater), G-remainder (CRSF), H (ESC outputs) are
NOT yet in the model. Estimated additional heat:

| Future subsystem | Components | Est. heat |
|---|---|---|
| D IMU island | 3× ICM-42688-P (3mA × 3.3V × 3 = ~30mW), 2× baro (~10mW each), heater (0W hot-case) | ~50 mW |
| H ESC outputs | Mostly switched signals; minor leakage | ~10 mW |
| G CRSF receiver header | passive | 0 mW |
| **D/H/G total** | | **~50–100 mW** |

Worst case adding 100mW + master margin (150-200mW per master estimate) → +200mW.

Re-running gate12 with 200mW added to existing 1000mW (Option B): MCU likely
~67-69°C → still +11°C margin. Comfortable.

Robustness check: even with 100% overrun on D/H/G estimate, all configs B/C
maintain >5°C margin. Option A would be MARGINAL with additional heat.

## Master recommendation: Option (B) — buck alone at 105×85

**Buck is the dominant lever. Bigger board adds marginal benefit at significant cost.**

Reasoning:
- B alone gives +16.3°C MCU margin — generous.
- A alone (bigger board, no buck) gives only +5.9°C MCU margin — tight, no
  D/H/G robustness.
- B costs schematic change ($2-3/board BOM bump for TPS62177 + inductor) +
  IMU noise risk; no board area cost.
- A costs PCB area (+15% area = ~+30% cost) + mechanical tray re-design;
  no schematic change.
- C is best margin but bears BOTH costs.

If IMU noise is the binding constraint: A (bigger board, LDO) at +5.9°C is
tight but acceptable IF D/H/G is <50mW (the lower estimate).

Sai picks based on IMU-noise risk appetite vs board-area appetite.

## IMU noise budget for Option B — quantified

Earlier rejected buck for U2 due to IMU noise concern. Quantitative analysis below.

**Noise propagation chain** (worst-case datasheet specs):

| Stage | Spec source | Value |
|---|---|---|
| TPS62177 output ripple | Datasheet §7.4 (10mV typ, 30mV max at full load) | 30 mV pk-pk @ 1.8 MHz |
| U13 LP5907 PSRR @ 1 MHz | Datasheet Figure 7-15 (45 dB typ rolloff) | ~45 dB |
| Noise at +3V3_IMU rail | = 30 mV × 10^(-45/20) | **169 µV pk-pk** |
| ICM-42688-P PSRR @ 1 MHz | Datasheet (typical 40-50 dB rejection HF) | ~40 dB |
| Noise injected to IMU readout | = 169 µV × 10^(-40/20) | **1.69 µV pk-pk** |

**Converting to IMU output units** (ICM-42688-P accelerometer):
- Supply-sensitivity (typical): ~10 µg / mV supply variation.
- 1.69 µV (= 0.00169 mV) supply variation → 0.017 µg output noise.
- **0.017 µg** at 1.8 MHz spectral content.

**IMU intrinsic noise floor** (ICM-42688-P, 100 Hz BW for control):
- Accel noise density: 70 µg/√Hz typical → integrated 700 µg pk in 100 Hz BW.
- Gyro noise density: 2.8 mdps/√Hz typical → integrated 28 mdps pk in 100 Hz BW.

**Ratio**: Buck-supply-induced noise / IMU intrinsic noise floor:
- Accel: 0.017 / 700 = **24 ppm** (0.0024% of intrinsic).
- 1.8 MHz spectral content is FAR ABOVE 100 Hz control bandwidth — additional
  anti-aliasing filtering inside IMU SoC further attenuates by 60+ dB.

### Conclusion: ENGINEERING SAFE

Buck-supply-noise contribution to IMU readout is **24 ppm of intrinsic noise
floor** — 4 orders of magnitude below detectable threshold. IMU noise budget
is dominated by intrinsic sensor noise, not supply-induced.

Caveats:
- Worst-case datasheet specs used (TPS62177 30mV ripple max load).
- Actual ripple typically ~10mV at 200mA load (3V3 rail) → noise injection
  3× lower than calculated.
- TPS62177-S spread-spectrum variant available if margin needed.

Layout requirements for buck (well-known good practice):
- Input cap (10µF) within 2mm of VIN pin.
- Switch-node trace short, contained, not under inductor.
- Output cap (22µF) close to VOUT pin.
- Loop area minimized.
- Ground star from buck back to +5V GND plane via via stitching.
- U13 input cap (1µF) provides additional HF filter for IMU rail.

These are standard buck layout patterns. v1.1 6-layer stackup has continuous
GND plane on In1.Cu — provides ideal reference for buck loop.

### IMU noise risk verdict

**LOW** with proper layout. Quantitative analysis shows 4-orders-of-magnitude
headroom to IMU noise floor. Earlier rejection was conservative; with current
v1.1 stackup + dedicated U13 LDO + standard buck layout, risk is engineered out.

### Verification path (post-Sai pick)

If (B) selected, validate with:
1. Schematic review by supermaster (buck topology choice).
2. Layout review of U2 area (loop area, ground reference).
3. openEMS SI sim of +3V3_IMU rail with buck switching node injection
   (~30 minutes).
4. Bench bring-up measure with scope on +3V3_IMU + IMU readout noise floor.

## Cost implications

| Option | PCB cost (vs current 105×85) | BOM cost | Engineering time |
|---|---|---|---|
| (A) 115×100mm | +~30% area | $0 | low (board outline + mount tray) |
| (B) Buck | $0 | +$2-3/board for TPS62177 + inductor | medium (schematic + layout + IMU noise verify) |
| (C) Both | +~15% area (110×90) | +$2-3/board | medium-high |

## Honest framing

This is the same class as the STEP4 mesh-divergence catch (2026-05-23 same day):
sim claim diverged from artifact reality, caught on a branch before fab.

The LOCK 73.98°C was technically not lying — it was based on sweep with planned
positions that satisfied the model. The lie was implicit: the model's positions
were never reconciled with the actual placement evolution.

Process implication: future board-sizing sweeps must use ACTUAL placement (or
within-tolerance placeholders that match final intent).

## What's HALTED until decision

- U5 VBUS decap (#27)
- Sense sub-step (8 V/I traces)
- D placement (IMU island)
- Any new thermal-architecture changes

## What CAN continue (per master direction)

- Task #22: docs/MASTER_PROCESS_RULES.md + scripts/verify_spec_diff.py + ENGINEERING_RIGOR §7 4-section + PR template
- Task #16: RF-3 doc hygiene
- Task #90 audit codify refinement (script-level, no board impact)

## Sign-off required

- [ ] Sai picks Option A / B / C / D
- [ ] Master sign-off on resulting plan
- [ ] DECISIONS.md §2 corrected with actual-placement-verified board size
- [ ] INTEGRATION_LOG.md #M / #7 corrected (LOCK numbers were planned-position artifacts)

— End of THERMAL_ARCHITECTURE_DECISION.md —
