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

## Master recommendation

**Combine Option (A) lite + Option (B): grow to 110×90mm AND swap LDO→buck.**

Reasoning:
- Buck saves 445 mW → ~28% total board heat reduction.
- 110×90mm is small enough to keep mounting-tray re-design minimal.
- IMU noise: combined buck switching-noise + larger board distance to IMU
  island (D placement) makes noise budget achievable.
- Belt-and-braces: even if buck efficiency degrades or board sim conservative,
  margin >5°C achievable.

Sai picks ultimately. Options (A) alone, (B) alone, or (C) all viable; (D) not.

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
