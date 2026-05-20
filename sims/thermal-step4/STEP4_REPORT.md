# Step 4 thermal validation report

> **Status**: Step 4 thermal FEA executed on the merged Step 3 P1
> placement (novapcb-layout-v2 at 62×42 mm 6-layer). PLACEMENT_STRATEGY
> §3.4 prediction (LDO Tj ≤ 80°C at 50°C ambient) **FAILS** under
> master's worst-case BCs (h_conv = 5 W/m²·K still air). FEA correctly
> surfaces the THERMAL_BUDGET §2.5.6 re-evaluation trigger:
> AP2112K Tj > 85°C in Elmer-FEM with realized placement → architecture
> assumption was wrong, escalation required.
>
> **PR outcome**: ESCALATE to master + Sai for architecture/BC decision
> per §2.5.6 trigger. NOT a placement iteration (convection-limited;
> placement repositioning cannot fix it).

---

## 1. Headline result (h_conv = 5 W/m²·K worst case, T_amb = 50°C)

| Quantity | Predicted (PLACEMENT_STRATEGY §3.4) | Elmer-FEM (Step 4) | Delta | Status |
|---|---|---|---|---|
| **AP2112K LDO Tj** | ≤ 80.0 °C | **92.1 °C** | **+12.1 °C over target** | **FAIL** (and 7.1 °C over 85°C abs spec) |
| **STM32H743 MCU Tj** | ≤ 75 °C (THERMAL_BUDGET §5) | **94.0 °C** | **+19.0 °C over target** | **FAIL** (and 9 °C over 85°C abs spec) |
| Board T avg | ~75-80 °C predicted | 89.9 °C | +10 °C over prediction | n/a — informational |
| Board T max | n/a (whole-board predicted uniform) | 95.2 °C | +20 °C over avg-prediction | n/a |

**Root cause**: the placement is **convection-limited**, not heat-spreading-limited. Total board dissipation 1.33 W (LDO 0.595 W + MCU 0.700 W + others) divided by the 62×42 mm board's convective dissipation capacity at h = 5 W/m²·K (per surface, top + bot):

```
G_conv = h × 2 × A_board = 5 × 2 × (0.062 × 0.042) = 0.026 W/K
ΔT_board_steady = P_total / G_conv = 1.33 / 0.026 = 51.2 °C above ambient
T_board_avg ≈ 50 + 51 ≈ 101 °C  (analytical board-average steady state)
T_board_avg ≈ 90 °C (Elmer-FEM with finite mesh + spatial distribution)
```

The whole board sits at ~90°C; the LDO and MCU sit a few °C above that. The PLACEMENT_STRATEGY prediction assumed θ_JA = 50 °C/W (vendor JEDEC 51-7 test board) which implicitly assumes the board itself is at ambient — but with novapcb's smaller surface area + still-air convection, the board itself is at 90°C, so the θ_JA model is not applicable.

## 2. Sensitivity sweep (h_conv ∈ {5, 8, 10, 15, 25} W/m²·K at T_amb=50°C)

| h_conv (W/m²·K) | Airflow scenario | Board avg (°C) | Board max (°C) | LDO Tj (°C) | MCU Tj (°C) | PASS vs 80°C target? |
|---|---|---|---|---|---|---|
| **5.0** (worst case, master directive) | Sealed enclosure, no airflow | 89.9 | 95.2 | **92.1** | **94.0** | **FAIL both** (+12, +14) |
| **8.0** (light natural convection) | Open chassis, light buoyancy | 74.9 | 80.0 | **77.0** | **78.9** | **PASS** (LDO -3, MCU -1) |
| **10.0** (moderate natural) | Drone bay, some air movement | 69.9 | 75.0 | 71.9 | 73.8 | PASS (-8, -6) |
| **15.0** (warm-board buoyancy) | Warm board → strong local plume | 63.3 | 68.1 | 65.1 | 66.9 | PASS (-15, -13) |
| **25.0** (light propwash) | Propellers spinning, idle hover | 57.9 | 62.5 | 59.6 | 61.3 | PASS (-20, -19) |

### Interpretation

- **At h=5 W/m²·K** (master-stated worst case): FAIL by 7-12°C.
- **At h=8 W/m²·K** (realistic still-air; per Holman *Heat Transfer* 10th ed. Table 7-2 for a vertical PCB at ΔT≈30K): PASS with 1-3°C margin.
- **At h=10 W/m²·K** (open enclosure with natural convection): PASS comfortably.
- **At h≥15 W/m²·K** (any forced airflow): PASS with large margin.

The h_conv assumption is the dispositive parameter. Choosing h=5 vs h=8 changes the PASS/FAIL verdict.

## 3. THERMAL_BUDGET §2.5.6 re-evaluation trigger (FIRED)

The architecture re-evaluation in THERMAL_BUDGET §2.5.6 listed four triggers; the first one has now fired:

> *Trigger 1*: "AP2112K Tj > 85°C in Elmer-FEM with realized placement (Step 3 P1+ Round-2 sim). Means the thermal budget assumption was wrong."

Step 4 FEA at h=5 W/m²·K: AP2112K Tj = 92.1°C > 85°C → trigger FIRED.

Per the documented escalation policy in §2.5.5, this is NOT a quiet schematic swap. The architecture decision (linear LDO retained) was master-adjudicated in PR #57; revisiting it requires master + Sai sign-off.

## 4. Why this is NOT a placement-iteration problem

Per master's directive: "If a junction exceeds target → iterate the placement (more copper pour / thermal vias / spread the heat sources) → re-run."

Placement-level levers AND why each is ineffective for the current failure mode:

| Lever | Mechanism | Effective here? | Why |
|---|---|---|---|
| Bigger LDO copper pour | Local θ_JC → board T | **NO** | Local θ_JC is already low (LDO Tj only 2-3°C above board avg). Bottleneck is convection from the board surface, not pad-to-board. |
| More thermal vias under LDO | Local θ_JC → board T | **NO** | Same reason — adding more vias under U2 doesn't help because heat is already escaping the LDO into the copper. |
| Spread heat sources (move LDO + MCU apart) | More uniform distribution | **NO** | They're already at opposite ends of the board (U2 at (9.5, 28), U1 at (30, 20) — ~22 mm apart). Sim shows board avg 90°C / max 95°C — only 5°C non-uniformity. Already nearly uniform. |
| Bigger board | More convective surface | **YES** but at architecture cost | Doubling board area halves ΔT_board. 62×42 → 88×60 (~5300 mm²) would drop ΔT_board from 51°C to ~25°C, putting LDO Tj at ~75°C. But +40% larger board has its own consequences (mounting tray redesign, airframe fit). |

The first three are NOT effective. Only "bigger board" works at the placement level, and that's a strategic decision not an iteration.

## 5. Recommended next-action paths (master + Sai adjudication)

In order of cost/disruption (least to most):

### Path A — BC re-evaluation (lowest cost; needs Sai input on real drone-bay airflow)

If the actual drone bay has any natural convection (open chassis, vent slots, propwash even at idle), h=5 W/m²·K is overly conservative. h=8 W/m²·K (realistic still air per published correlations) puts the design at PASS with 1-3°C margin.

**Decision needed from Sai**: what is the realistic airflow assumption for the Nova drone bay? "Truly sealed dead-air" (h=5) or "open chassis with natural convection" (h=8-10)? If the latter, the design PASSES and Step 4 closes.

### Path B — bigger board (placement-level fix; needs no schematic change)

Grow the board to ~75×52 mm (+ ~50% area). Per the convection-limited model, ΔT_board scales as 1/A, so 1.5× area → 0.67× ΔT → LDO Tj at h=5, 50°C ambient drops from 92°C to ~78°C → PASS at 80°C target.

**Cost**: airframe-tray redesign (mounting hole pattern shifts), +50% board area, ~+50% fab cost. Sai's reliability mandate easily justifies that cost; "size is OUTPUT of placement" was Sai's directive too.

### Path C — buck-switcher hybrid for 3V3 (architecture change; needs schematic update)

Per THERMAL_BUDGET §2.5.5 escalation path: switch from linear AP2112K LDO to buck+LDO hybrid. Eliminates 0.595W LDO heat → total board dissipation drops from 1.33W to ~0.85W → ΔT_board at h=5 drops from 51°C to 32°C → LDO Tj-equivalent at ~62°C → PASS with large margin.

**Cost**: Step 2 schematic update + EMC re-analysis + +1 buck IC + inductor on the FC near the IMU (the noise concern that originally motivated retaining linear LDO).

### Path D — external heatsink (mechanical, v2-territory)

Bond a small heatsink (10×10×5 mm aluminium fin) to the LDO + MCU through thermal pad on the bottom side. Adds significant local convection at the heat sources.

**Cost**: mechanical complexity, v2 conversation.

## 6. EMC re-check (placement preserves 4-zone strategy)

Per master's secondary directive, re-confirmed the 6k EMC analytical findings against the new 62×42 mm placement:

### Findings from Phase 6k (unchanged by placement)

The 4 critical harmonics (SDMMC 12.5MHz + USB FS 12MHz fundamental + DShot600 19th/21st harmonics at 11.4/12.6 MHz, all in USB FS self-band, all > -40 dB) are determined by **clock frequencies**, NOT by placement. They remain Phase 9.5 chamber-test items regardless of physical layout.

### Placement-dependent physical separations (preserved by Step 3 P1-rev)

| Aggressor-victim pair | Phase 4 baseline (36×36, 4-layer) | Step 3 P1-rev (62×42, 6-layer) | Improvement |
|---|---|---|---|
| Zone-1 power switching (eFuse U6) ↔ Zone-3 IMU (U3) | ~30 mm | **~41 mm** | +37% physical separation |
| Zone-1 LDO (U2) ↔ Zone-3 baro (U4) | ~25 mm | **~36 mm** | +44% |
| ESC long-edge ↔ Zone-3 IMU U3 (perpendicular) | ~18 mm (Y) | **~18 mm (Y)** | unchanged (Y dim ~same) |
| SDMMC J2 ↔ USB-C J1 (both Zone 2 — short-trace containment) | ~12 mm | **~17 mm** | +42% |
| ESC row ↔ MCU U1 (Y direction) | ~8 mm | **~10 mm** | +25% |

Zone-separation improvements range +25 to +44%. The 4-zone strategy is preserved with more breathing room. Coupling reduction (estimated 6-10 dB per Force-3 of PLACEMENT_STRATEGY §3.1) is on track.

**Verdict**: EMC zone-separation passes — no changes needed at placement level for EMC. The Phase 9.5 chamber-test items remain in their queue.

## 7. Methodology notes (Elmer model limitations + improvements roadmap)

### Limitations of this model

- **Isotropic effective k** (22.9 W/m·K geometric mean): underestimates lateral spreading (real k_xy ≈ 158 W/m·K), but the result is **insensitive** to this — verified with k=158 sanity check: T_avg unchanged at 90°C, T_max only 0.8°C above avg (vs 5.3°C with k=22.9). The convection-limited regime makes spatial detail unimportant.
- **Single uniform material**: doesn't model the discrete L2/L3/L4/L5 inner copper layers. For the LDO thermal pour question specifically, the inner +5V plane (L4) is the relevant heat-spreading conductor. A layered model would change ΔT-from-LDO-pad-to-board-avg slightly, but not the dominant ΔT_board-avg-to-ambient.
- **No conduction to mounting holes**: H1-H4 M3 holes are GND-pad-tied to the airframe chassis. Per THERMAL_BUDGET §4.3, this contribution is "treated as negligible" — but the chassis may be a significant heat sink in practice. Sai input needed on airframe-tray material + chassis thermal mass.
- **Body-source model**: heat is deposited uniformly through the package volume rather than via the actual JEDEC junction-to-pad model. Acceptable for whole-board T but introduces small errors in local Tj.

### Improvements for a more rigorous model (not in this PR's scope)

- Multi-layer Elmer model with discrete L1-L6 copper sheets (anisotropic per-layer k).
- Conduction BC at mounting holes representing the airframe heat sink.
- Detailed LDO model with thermal pad as a separate body with q_input distributed over the pad surface only.
- Coupled with the actual ambient-air domain (CHT — conjugate heat transfer) to capture buoyancy-driven convection rather than assumed h_conv.

These are Phase 6.5 forum review + Phase 9 bench validation items.

## 8. Files

- `sims/thermal-step4/run_thermal.py` — Elmer model generator + runner + result parser. Reproducible.
- `sims/thermal-step4/runs/case_h5/` — Elmer working directory at h_conv=5 W/m²·K (worst case).
- `sims/thermal-step4/runs/case_h{5,8,10,15,25}_done/` — sensitivity-sweep result directories.
- `sims/thermal-step4/runs/results.json` — summary JSON of the h_conv=5 baseline.
- `sims/thermal-step4/STEP4_REPORT.md` — this report.

## 9. Status + ask

**Step 4 thermal validation: COMPLETE.** Result: PLACEMENT_STRATEGY §3.4 prediction does not hold under master's worst-case BCs. Architecture re-evaluation trigger per THERMAL_BUDGET §2.5.6 has fired.

**Step 4 EMC re-check: COMPLETE.** Result: 4-zone strategy preserved with +25-44% improved separation; Phase 9.5 chamber-test items unchanged.

**Master + Sai adjudication needed**: which of Path A (BC re-evaluation), B (bigger board), C (buck-switcher hybrid), or D (external heatsink) to pursue. Worker stopped at the architecture trigger per documented escalation policy in THERMAL_BUDGET §2.5.5 — does NOT silently iterate placement (won't help) or silently swap schematic (needs sign-off).

**Critical-path impact**: Step 5 (routing) is **NOT BLOCKED** by this finding because:
- The placement geometry is valid; routing can proceed on the current board.
- IF the adjudication picks Path B or C, the placement (or schematic) changes and routing waits.
- IF Path A (Sai confirms h ≥ 8 W/m²·K is realistic), Step 5 dispatches immediately.

Recommend: master + Sai converge on Path A first (Sai's input on drone-bay airflow is the cheapest disambiguator). If h=5 is genuinely the design assumption, then Path B or C — Path B (bigger board) is the placement-only fix; Path C is the architecturally cleaner one but reopens Step 2.
