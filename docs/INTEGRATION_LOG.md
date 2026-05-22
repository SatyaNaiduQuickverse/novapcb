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

## In progress

| Sub-phase | Branch | Notes |
|---|---|---|
| Step 5 — place B (POWER_REG_3V3) | `integ/C-F-B-step5` (branches from integ/C-F-usb @ c4c47f1) | First HIGH-conflict subsystem (places main LDO U2 — first real new heat source). Full constraint analysis up front before placement (master direction 2026-05-23). |

## Tracked, non-blocking

| Item | Reference | Must close before |
|---|---|---|
| openEMS coupled-pair S=0.13 independent cross-check (K-J or 2D field solver) | task #75 (extended), `docs/OPEN_QUESTIONS.md` (to add) | Phase 7a freeze |
| JLCPCB DFM gate (#11) — USB fan-region 0.106mm thin clearance vs 0.10mm rule | `docs/OPEN_QUESTIONS.md phase4-dfm-usb-fan` | Fab order |
| USBLC6-2P6 pin-swap final ratification log | PR #70 closed; ratification recorded master 2026-05-23 | n/a — done, lands with v1.1 |
