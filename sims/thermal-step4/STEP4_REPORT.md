# Step 4 thermal validation report (Sai Path B grown board)

> ## ⚠ CORRECTION 2026-05-23 — original numbers were mesh-formulation artifacts
>
> The numbers reported in §1–§4 below were generated with a Body-Force
> heat-source expressed as `MATC` bounding-box conditional. That
> formulation is **mesh-divergent**: the total injected power depends
> on how many Gauss points fall inside the bbox at the given cell size.
> The reported 2 mm-cell results UNDER-INJECTED power.
>
> **Corrected results** (gate12 v3 with per-body Body Force assignment,
> total injected power = design power EXACTLY, energy-balance gate +0.3%
> on all meshes, T_MCU converged to ±0.6 °C across cell sizes
> 2/1/0.675/0.5 mm):
>
> | Quantity | Old reported | Corrected | Δ | Target | Status (corrected) |
> |---|---|---|---|---|---|
> | T_avg | 71.5 | **77.6 °C** | +6.1 | n/a | informational |
> | T_max | 76.8 | **84.7 °C** | +7.9 | n/a | informational |
> | T_LDO | 69.0 | **79.7 °C** | +10.7 | ≤ 80 °C | **TIGHT (+0.3 °C)** |
> | T_MCU | 75.2 | **84.0 °C** | +8.8 | ≤ 80 °C | **FAIL (−4.0 °C)** |
>
> Implication: the 80×60 mm Sai Path B board does NOT meet the 80 °C
> target. Original "Path B PASS" conclusion is rescinded. v1.1 needs a
> larger board to achieve the same ≥5 °C MCU margin. Determination of
> the corrected smallest-board-with-margin is in progress under the
> gate12 v3 architecture pass.
>
> **Root cause**: `Real MATC "if(abs(tx-x0)<w/2 & abs(ty-y0)<h/2) q=q+q_per_kg"`
> in `run_thermal.py:make_sif` injects heat only at Gauss points
> satisfying the inequality. With 8-pt Gauss per hex cell and a 2 mm
> cell, sources smaller than ~1.15 mm in any dimension get under-counted
> Gauss-point coverage. STEP4's Q2_PFET (3.0 × 1.5 mm) and U6_eFuse
> (3.0 × 4.0 mm) both fall in the under-coverage zone; U1_MCU (14 × 14 mm)
> was less affected but still skewed by element-edge alignment.
>
> **Fix**: `hardware/kicad/novapcb-stepwise/gate12_thermal.py` v3
> (2026-05-23) replaces MATC with per-meshed-body assignment: each
> heat source is its own body ID, element centers in source bbox →
> body ID i, `Body Force i: Heat Source = P_i / (ρ × V_body_i_actual)`.
> Total injected = P_design exactly, regardless of mesh refinement.
> Energy-balance + min-mesh-density gate assertions added per master
> 2026-05-23 directive.
>
> The §1–§4 numbers below are LEFT AS-RECORDED for traceability —
> they document what the v2-formulation MATC model said. The corrected
> values above are the authoritative thermal result.

---

> **Status (original — superseded by correction header above)**: thermal FEA on the FEA-arbitrated 80×60 mm board: **LDO Tj = 69.0°C, MCU Tj = 75.2°C** at master's worst-case h=5 W/m²·K / 50°C ambient. **BOTH PASS the 80°C target.** Sai Path B (grow the board to PASS at h=5 still-air) is realized. Steps 3+4 done; Step 5 routing next.
>
> Supersedes the Step 4 escalation in PR #59 (62×42 mm board FAIL'd; placement iteration shown to be ineffective in the convection-limited regime; Sai adjudicated Path B over Paths A/C/D).

---

## 1. Headline result — 80×60 mm board, h=5, T_amb=50°C

| Quantity | Target | Elmer-FEM | Margin | Status |
|---|---|---|---|---|
| **AP2112K LDO Tj** | ≤ 80 °C | **69.0 °C** | +11.0 °C | **PASS** |
| **STM32H743 MCU Tj** | ≤ 80 °C | **75.2 °C** | +4.8 °C | **PASS** (in target band) |
| Board T avg | n/a | 71.5 °C | — | informational |
| Board T max | n/a | 76.8 °C | — | informational |
| Tj eFuse U6 | < 150 °C | 73.8 °C | huge | PASS |
| Tj P-FET Q2 | < 150 °C | 72.4 °C | huge | PASS |

**Master's sizing-target band per directive**: "Target = LDO and MCU Tj ≤ 80°C at h=5/50°C ambient with ~5°C margin … If your first size gives junctions well under 75°C, the board is bigger than it needs to be."

MCU at **75.2°C** is right in the 75-80°C target band with 4.8°C margin — perfect hit. LDO at 69°C is the secondary heat source and is naturally well-cooled relative to MCU on this layout.

## 2. Sizing iteration (FEA-arbitrated, not estimate-driven)

Per master's directive ("let the FEA be the arbiter, not the area-scaling estimate + a fixed buffer"):

| Iteration | Board | Area | LDO Tj | MCU Tj | Verdict |
|---|---|---|---|---|---|
| 0 (P1-rev baseline) | 62×42 mm | 2604 mm² | 92.1 °C | 94.0 °C | FAIL (PR #59 escalation; → Sai Path B) |
| 1 (first Path-B size) | 85×62 mm | 5270 mm² | 71.1 °C | 75.7 °C | PASS but LDO well under 75°C → over-built per master |
| **2 (FEA-converged)** | **80×60 mm** | **4800 mm²** | **69.0 °C** | **75.2 °C** | **PASS** (MCU in 75-80°C target band) |

The size came down from 85×62 because the 85×62 attempt had LDO at 71°C (well under 75°C → over-built per master's "don't over-build" steer). 80×60 tightened that to MCU=75.2°C which hits the band exactly.

Further shrinking (toward 75×55 or 78×58) would push MCU close to or over 80°C — accepted that 80×60 is the sweet spot.

## 3. h_conv sensitivity sweep (for the record)

| h_conv (W/m²·K) | Scenario | T_avg | T_max | LDO Tj | MCU Tj | PASS @ 80°C? |
|---|---|---|---|---|---|---|
| **5.0** (master worst case) | Sealed enclosure, no airflow | 71.5 | 76.8 | **69.0** | **75.2** | **PASS** |
| 8.0 | Light natural convection | 63.4 | 68.6 | 61.1 | 67.0 | PASS comfortable |
| 10.0 | Open chassis, natural | 60.7 | 65.8 | 58.5 | 64.2 | PASS large |
| 25.0 | Light propwash | 54.3 | 58.8 | 52.6 | 57.2 | PASS huge |

The design is robust across the full realistic airflow range.

## 4. Path B rationale (Sai-adjudicated, master 2026-05-21)

Why Path B (grow the board) was chosen over A/C/D:

- **Path A** (BC re-evaluation, assume h≥8): didn't satisfy Sai's won't-fail / worst-case mandate. The drone bay COULD be h=5 (sealed enclosure scenario); design for that.
- **Path B** ✓ (grow the board for h=5): deterministic physics fix; no schematic change; no sensor-noise regression; cools the MCU too (which the LDO-architecture changes wouldn't).
- **Path C** (buck-switcher hybrid for 3V3): would put a switcher within 20-40 mm of the IMU; sensor-noise regression risk for ~280mW savings. Doesn't help MCU thermal.
- **Path D** (external heatsink): mechanical, v2 territory.

Mounting-tray redesign (74×54 mm c-to-c) accepted by Sai as part of Path B.

## 5. EMC re-check (placement preserves 4-zone strategy)

The 4-zone strategy is preserved on 80×60 with even more breathing room than 62×42:

| Aggressor-victim pair | 62×42 (P1-rev) | 80×60 (Path B grown) | Improvement |
|---|---|---|---|
| Zone-1 eFuse U6 ↔ Zone-3 IMU U3 | ~41 mm | **~61 mm** | +49% |
| Zone-1 LDO U2 ↔ Zone-3 baro U4 | ~36 mm | **~62 mm** | +72% |
| SDMMC J2 ↔ USB-C J1 (Zone 2 close-pair) | ~17 mm | **~26 mm** | +53% |
| ESC long-edge ↔ MCU U1 (Y direction) | ~10 mm | **~14 mm** | +40% |

Phase 6k EMC-critical USB-self-band harmonics remain Phase 9.5 chamber-test items (clock-frequency-determined, not placement-determined).

## 6. Why placement iteration alone wouldn't have fixed 62×42

The Step 4 escalation analysis still stands: at the 62×42 board, total dissipation 1.33 W / convective capacity at h=5 → ΔT_board ≈ 51°C → board at 90°C. No amount of placement repositioning fixes a convection-limited regime — only changing the convective capacity (bigger board, higher h, or removing a heat source) helps.

Path B's "grow the board" works because larger surface area lowers ΔT_board (ΔT ∝ 1/A).

## 7. Model + reproducibility

- Elmer 3D heat-conduction on 80×60×1.6 mm box
- Effective isotropic k = 22.9 W/m·K (geometric mean of in-plane 158.5 / through-plane 0.478)
- 40 × 30 × 4 hex mesh
- Heat sources at U2 LDO + U1 MCU (97% of total) + U6 eFuse + Q2 P-FET (residual)
- Convection BC h_conv = 5 W/m²·K on top + bottom faces; adiabatic edges
- T_amb = 50 °C
- Steady-state direct solve

Reproduce:
```sh
cd sims/thermal-step4
python3 run_thermal.py
```

Output: `runs/results.json` + console PASS/FAIL table.

## 8. Methodology notes (limitations + future-pass improvements — informational)

- **Isotropic effective k**: understates lateral spreading. Sanity-checked with k=158 (full Cu in-plane): T_avg unchanged, T_max only ~1°C lower — convection-limited regime makes the choice irrelevant for the design conclusion.
- **No mounting-hole heat sink contribution**: assumed adiabatic. Real airframe-tray contact would be additional cooling — conservative omission.
- **No CHT (conjugate heat transfer)**: convection BC h_conv = 5 W/m²·K is a fixed coefficient. A CHT solve coupling to the air domain would capture buoyancy-driven flow more accurately but adds significant solve time. Master accepted h_conv = 5 as the worst-case design BC.

These are Phase 6.5 forum review + Phase 9 bench validation refinement items.

## 9. Status

- Step 3+4 thermal validation: **DONE + PASSING** at 80×60 mm.
- PR #59 (the escalation artifact): superseded by this PR.
- Step 5 (routing): **READY TO DISPATCH** once this PR merges.
