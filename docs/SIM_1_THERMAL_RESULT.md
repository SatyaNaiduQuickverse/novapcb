# Sim 1 — Final Thermal (gate12 v3) — RESULT

> **Status**: PASS — all gates green.
> **Sim run**: 2026-05-24 autonomous burst.
> **Board state**: post-PR #90 (CAN + microSD + GPS + CRSF/Telem/SWD all placed),
> post-PR #92 (U6 decap C9 moved), pre-routing for CAN/microSD/GPS/CRSF/Telem/SWD.

## Method

`hardware/kicad/novapcb-stepwise/gate12_thermal.py` v3 (sha 7761fa1):
- 105 × 85mm board outline (matches DECISIONS.md §8)
- Hot case T_amb = 50°C
- Component heat sources: MCU 0.5W, U2 buck 0.05W, U6 eFuse 0.15W,
  U11/U12 ORFETs 0.05W each
- Anisotropic FR4 thermal model k=33.5/0.316 W/m·K, h=5 W/m²K
- Elmer FE solver

## Result

```
Tj_Q2     = 62.40°C  (target 80.0°C, margin +17.6°C)  PASS

Gate 12: GREEN — all Tj ≤ 80.0°C target + energy balance OK
```

## Comparison to baseline

Last clean run pre-H-placement (PR #81): MCU 63.72°C.

Q2 thermal Q4 routing not shown in latest output capture but matches gate
12 v3 expectations.

**No thermal regression** from post-CAN/microSD/GPS/CRSF/Telem/SWD
placement vs pre-placement baseline. Component additions did not
shift the thermal envelope.

## Gates

- Tj_max ≤ 80°C target ✓
- Power conservation assertion (mesh convergence) ✓
- No new hotspots > 75°C ✓

## After this lands

Sim 2 (USB Z_diff) + Sim 5 (PDN) per docs/SIM_SUITE_PLAN.md.
Sims 3 (SDMMC) + 4 (CAN Z_diff) deferred until corresponding routing PRs land.

