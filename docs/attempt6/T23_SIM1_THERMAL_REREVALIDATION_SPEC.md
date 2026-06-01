# Sim 1 thermal re-validation for board grow 105×85 → 105×100mm

> Mandatory per master combined-attack contract + T23 board-grow campaign.
> Worker runs `gate12_thermal.py` (or equivalent) with new board outline.

## What changed

- Board outline: 105 × 85 mm → **105 × 100 mm**
- Area: 8925 mm² → **10500 mm² (+17.6%)**
- Heat sources: SAME XY positions (no component moved yet for board grow)
- Convection: same h = 5 W/m²K
- Inner planes (In1-In4): extended south to new outline (more copper area)

## Expected result

Tj for all heat sources should **DROP** because:
- More board area = more convection surface
- Inner planes extend = more horizontal heat-spreading
- Heat-source-to-edge distance INCREASED for south-edge sources (better dissipation)

Master prediction (rough scaling): MCU Tj drops ~3-5°C from 65.05°C baseline.

## PASS gate

| Metric | Spec | Baseline | New target |
|---|---|---|---|
| MCU Tj | ≤ 80°C | 65.05°C | should be ≤ baseline (better is fine) |
| U2 buck Tj | ≤ 80°C | 62.40°C | should be ≤ baseline |
| All 13 heat sources | ≤ 80°C | ≤ 66.32°C | should be ≤ baseline |
| Energy balance | < 1% err | 0.31% | spot-check |

## FAIL handling (unlikely but documented)

If any Tj INCREASES (regression from board grow):
- Unexpected — board grow should only help thermal
- Check mesh density (gate12 v3 enforces min-mesh-density gate)
- Check heat source XYs didn't accidentally shift in the new model
- Revert + investigate

If Tj IMPROVES significantly:
- Document the new baseline as the post-board-grow reference
- May unlock margin for v1.5 / v2 features

## Worker action sequence

1. After Edge.Cuts outline updated to 105×100 (already DONE per Step 1 53f6d07):
2. Update `gate12_thermal.py` board outline coordinates (or whatever the FE input expects)
3. Re-mesh (mesh density auto-adjusts)
4. Re-run thermal sim
5. Commit results to `sims/thermal-step4/runs/v11_postgrow_2026-06-02.log`
6. Update `docs/SIM_1_THERMAL_RESULT.md` with new MCU/Q2/U8/U11/all-13 Tj
7. If PASS: combined-attack gate Sim 1 ✓
8. If FAIL: investigate per FAIL handling above

## Cross-reference

- Original gate12 v3 PR #94 / PR #126
- T23 board-grow campaign per master burst-15
- All-or-nothing combined-attack contract per PR #168
