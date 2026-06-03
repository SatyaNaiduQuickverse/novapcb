# Sim 5 PDN re-validation for board grow 105×85 → 105×100mm

> Mandatory per master combined-attack contract + T23 board-grow campaign.
> Companion to `T23_SIM1_THERMAL_REREVALIDATION_SPEC.md` (PR #176).

## What changed (board grow context)

- Board outline: 105 × 85 → 105 × 100 mm
- Area: 8925 → 10500 mm² (+17.6%)
- Inner planes (In1 GND / In2 +5V_BEC / In3 +3V3 / In4 GND): EXTENDED south to new outline
- Plane area for the +3V3 PDN test point (MCU VDD pins 11/27/50/75/100): increased proportionally
- Cap inventory near U1: UNCHANGED (12×100nF 0402 + 4.7µF + 22µF 0805)

## Expected result

PDN mid-band peak should **DROP** because:
- More plane area = lower plane impedance contribution
- Plane spreading more uniform = less local hotspot impedance
- Cap network unchanged (still 12+1+1 stack)

Master prediction: mid-band peak drops from 79.4 mΩ baseline → ~70-75 mΩ at 105×100.

## PASS gate

| Metric | Spec | Baseline (105×85) | Target (105×100) |
|---|---|---|---|
| Mid-band peak (100 kHz – 100 MHz) | ≤ 100 mΩ | 79.4 mΩ | should be ≤ baseline |
| LF (1–100 kHz) | within ±10% of baseline | model-limited | flag-only |
| HF (>100 MHz) | no major new resonance | model-limited (~140 mΩ over-sharp) | flag-only |

**Primary gate:** mid-band peak ≤ 100 mΩ. Hard gate.

## FAIL handling

If mid-band peak INCREASES beyond 100 mΩ (regression from board grow):
- Unexpected — board grow should only help PDN
- Investigate: was plane re-pour clean? Any plane voids introduced by board outline change?
- Verify cap network position assumptions in the sim model match current geometry
- If genuinely degraded: add bulk cap stitching near U1 (could add one more 10µF if needed)
- Revert investigation; flag for master/Sai if can't recover

## Worker action sequence

1. **After Edge.Cuts outline at 105×100** (already DONE at Step 1 53f6d07):
2. Re-pour inner planes (In1-In4) to fill new outline
3. Re-run `sim_pdn.py` (`hardware/kicad/novapcb-stepwise/sim_pdn.py` or wherever the runner lives)
4. Commit `sims/pdn/runs/v11_postgrow_2026-06-02.log`
5. Update `docs/SIM_5_PDN_RESULT.md` with new mid-band peak
6. If PASS: combined-attack gate Sim 5 ✓
7. If FAIL: investigate per FAIL handling above

## Cross-reference

- Sim 5 baseline: PR #118 (un-deferred) + PR #126 (re-validation post-power-tree)
- Original mid-band peak: 79.4 mΩ
- T23 board-grow campaign master burst-15 (PR #174)
- Combined-attack contract PR #168
- Companion Sim 1 thermal re-validation: PR #176

## Sequencing in sim cascade

Order (per master combined-attack contract PR #168):
1. Sim 2 USB Z_diff spot-check (USB pair unchanged; verify Z₀ ≥ 81Ω)
2. Sim 4 CAN Z_diff spot-check (CAN unchanged unless re-routed)
3. Sim 5 PDN re-run (this doc) — plane area changed
4. Sim 6h ADC settling spot-check (Mauch unchanged unless touched)
5. Sim 3 SDMMC1 SI spot-check (SDMMC1 unchanged unless touched)
6. Sim 1 thermal re-run (per PR #176 spec) — board area changed
7. Sim 1+5 are the ONLY mandatory re-runs; others are spot-checks

All sims PASS → freeze gate per `docs/PHASE7A_FREEZE_PROCEDURE.md`.
Any sim FAIL → investigate per per-sim FAIL handling.
