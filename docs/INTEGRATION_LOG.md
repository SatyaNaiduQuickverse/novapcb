# Integration log — locked subsystem-by-subsystem build (v1.1 90×70)

> **Purpose.** Running record of locked integration steps for the
> novapcb v1.1 placement + routing build. One row per locked sub-phase
> with the commit sha, gates passed, and the date. Lightweight
> traceability: lets a cold reader (or master) verify which sub-phases
> are committed-and-locked vs in-progress, without scrolling the full
> git log.
>
> **Convention.** Adding a row here means master has audited and
> approved the sub-phase. A WIP commit does NOT get a row until
> master locks it. The branch `integ/C-F-usb` is the active
> integration mainline; sub-phase branches merge into it before
> appearing here.
>
> **Gates** referenced are from `docs/PLACEMENT_ROUTING_GATES.md` (1-14):
> 1 bbox overlap · 2 render eyeball · 3 uniqueness · 4 artifact trust ·
> 7 thermal-via density · 8 routing density · 12 thermal FE per-step ·
> 13 sim-tool validated · 14 KiCad DRC zero.

---

## Locked integration steps

| # | Sub-phase | Branch / PR / sha | Date | Gates passed | Notes |
|---|---|---|---|---|---|
| 1 | **Step 1 — place C (MCU_CORE)** | `step1/C-mcu-core` → main, sha `7c48fa6` | 2026-05-22 | 1, 2, 3, 4, 12 (analytical) | U1 + Y1 + HSE caps + decoupling halo. Gate 12 was analytical Theta_ja at this step (FE gate not yet built). |
| 2 | **Step 2 — place E (BARO_I2C)** | `step2/E-baro` → main, sha `6e0eb03` | 2026-05-22 | 1, 3, 4, 12 (convergence 1.14%) | DPS310 + RM3100 + I²C2 pullups. First step using Elmer 3D FE thermal gate. |
| 3 | **C↔E integration (I²C2 routing)** | `integ/C-E-i2c2` → step3, sha `db0d071` | 2026-05-22 | 8, 12, 13, 14, SI sanity | I²C2 routed at 100 kHz; lots of margin. Phase-3 master's process-gap fix added Gate 14 (mandatory KiCad DRC). |
| 4 | **Step 3 — place F (USB_INTERFACE)** | `step3/F-usb` → integ/C-F-usb, sha `2b1efe5` (+ re-opens) | 2026-05-22 → 2026-05-23 | 1, 2, 3, 4 | F zone re-opened TWICE: (a) U5 moved Y=30→35 to clear pair Y=31 corridor (root cause: original Y inside corridor), (b) U5 moved Y=35→31 ON the corridor + pin-swap after master's USBLC6 root-cause analysis. |
| 5 | **C↔F integration (USB diff pair)** | `integ/C-F-usb`, sha `c4c47f1` | 2026-05-23 | 1, 2, 3, 4, 8, 12 v2, 13, 14 | DRC 0. USBLC6-2P6 pin-swap (electrically a no-op — datasheet-symmetric ESD) eliminated U5-body crossing → both pairs pure F.Cu, no vias/tunnels/detours. Render eyeballed (Gate 2 PASS). openEMS coupled-pair setup validated via limit-case (2×openEMS-single-line at S/h=9.52 within 2.9%) — 87.4 Ω is the trustworthy Z_diff (in-spec on all estimates, K-J cross-check tracked for Phase 7a). Pin-swap ratified by master (PR #70 closed, no merge — diff carried unrelated v1.1 changes; pin-swap lands with v1.1). gate12 v2 rebuilt with anisotropic k + 80°C target + STEP4 regression PASS (all 4 metrics within ±2°C). |
| **M** | **MILESTONE — thermal architecture resolved at 105×85 mm, LDO kept** | branch `sim/gate12-v3-perbody`, PR #71, sha `874de12` | 2026-05-23 | 12 v3 (energy-balance + min-mesh-density PERMANENT gates), 13 | Master sign-off after gate12 v3 refactor (per-body Body Force replaces mesh-divergent MATC bbox; total injected power EXACT regardless of mesh). STEP4 regression: T_MCU spread 0.57°C across 4 meshes, energy balance +0.3% all meshes. Board-size sweep with rigorous powers (MCU=0.700W, U2=0.642W, Q5=0W hot-case, total 1.717W): smallest size with ≥5°C MCU margin = **105×85 mm** (MCU=73.98°C, +6.02°C margin). LDO→buck escalation CLOSED — `OPEN_QUESTIONS.md phase5-thermal-ldo-vs-buck`. Outline + mounting holes updated; DECISIONS.md §2 records the full evolution. STEP4's 80×60mm Path B PASS rescinded — was MATC artifact (corrected T_MCU=84°C FAILS 80°C). |
| 6 | **C↔B integration (+3V3 plane on In4.Cu + B-internal traces)** | `integ/C-B-power`, sha TBD | 2026-05-23 | 14 (DRC=0), 12 v3 (MCU=73.98°C +6.02°C, energy balance +0.31% PASS) | +3V3 main rail via In4.Cu plane + vias on all wide pads (18 vias on caps/sensors) + L-stubs from 3 MCU VDD pins (U1.11, U1.75, U1.100) to nearby decap caps. R11 via deferred (congested I2C2_SDA neighborhood). +3V3_IMU_PRE chain FB2→C77→U13.1 + U13.3 stub routed clear of C78 (+3V3_IMU) and U13.2 (GND). +5V_BEC routing deferred (U2.1 is on +5V net, source is A-zone unplaced). Mounting hole inset shifted 3.0→3.25mm to satisfy 0.5mm edge-clearance rule with 5.5mm pads. C77 placement moved (58,27)→(56.5,27) to clear U13.5 collision. |

## In progress

| Sub-phase | Branch | Notes |
|---|---|---|
| Step 5 — place B (POWER_REG_3V3) | `integ/C-F-B-step5` (HOLD) | B placement HELD pending v1.1 thermal architecture re-evaluation. First try at +2.1°C MCU margin (within model uncertainty) rejected by master 2026-05-23. Now blocked on board-size determination from corrected gate12 v3 + rigorous power inputs. |
| gate12 v3 refactor | `sim/gate12-v3-perbody` (PR #71, signed off by master) | Per-body Body Force replaces MATC bbox. Energy-balance + min-mesh-density gates permanent. STEP4 regression: T_MCU converged 0.57°C across 4 meshes, energy balance +0.3% all meshes. Sign-off recorded as PR #71 comment (single-account repo can't gh review-approve). |
| v1.1 full-load board sizing | `sim/gate12-v3-perbody` (sweep complete 2026-05-23, recommendation pending master sign-off) | Sweep 90×70 → 120×100. Smallest board with ≥5°C MCU margin = **105×85 mm** (Tj_MCU = 73.98°C, +6.02°C margin). 100×80 falls short at +2.75°C. Above 105×85 the MCU is asymptotic ~74°C (heat-spreading length scale reached). Sweep log saved to `sims/thermal-step4/runs/v11_sweep_2026-05-23.log`. Recommendation: adopt 105×85; LDO→buck NOT needed. |

## Tracked, non-blocking

| Item | Reference | Must close before |
|---|---|---|
| openEMS coupled-pair S=0.13 independent cross-check (K-J or 2D field solver) | task #75 (extended), `docs/OPEN_QUESTIONS.md` (to add) | Phase 7a freeze |
| JLCPCB DFM gate (#11) — USB fan-region 0.106mm thin clearance vs 0.10mm rule | `docs/OPEN_QUESTIONS.md phase4-dfm-usb-fan` | Fab order |
| USBLC6-2P6 pin-swap final ratification log | PR #70 closed; ratification recorded master 2026-05-23 | n/a — done, lands with v1.1 |
