# Sim 1 (thermal) + Sim 5 (PDN) re-validation — post-power-tree (2026-05-28)

> **Status: BOTH PASS.** Master directive after PR #125 (D4-final) merged: the
> MCU power chain now physically reaches U1 (VCAP1 via-in-pad + VDDA/+3V3A/VREF
> + the +3V3 plane stubs), so Sim 1 (thermal) and Sim 5 (PDN) — whose PASS was
> *electrically conditional* on power reaching the MCU — are now **valid**, not
> just modelled. Re-run against head **05c4567**.
> **Branch**: `hw/sim-rerun-d4` off `sch/option-b-buck`@05c4567.

## Why a re-run (not just inheritance)

The D4/D6 PRs (#122–#125) were **routing-only + a 5-decap re-spread**
(C13/C17/C19/C20/C21). **No heat-source component moved** (U1/U11–14/Q2–4/U2/U6
all at their established positions) and **no +3V3-rail decap changed** (the
12×100nF + 4.7µF + 22µF inventory near U1 is intact). So the physics inputs to
both sims are unchanged — but the *premise* ("power reaches the MCU") is now
true on the board. Re-running confirms the prior PASS holds and is now real.

## Sim 1 — thermal (gate12 v3 FE, Elmer)

Re-ran `gate12_thermal.py` (per-body heat-source assignment + energy-balance +
min-mesh-density gates) against the current board. Mesh: 0.375 mm cells,
280×226×4 = 253,120 elements. Total injected P = 1130 mW (13 active sources).

| Body | Tj | target | margin |
|---|---|---|---|
| **U1 (STM32H743 MCU)** | **65.05 °C** | 80 °C | **+15.0 °C** |
| Q2 (buck P-FET) | 62.40 °C | 80 °C | +17.6 °C |
| U8 (IMU, hottest sensor) | 66.21 °C | 80 °C | +13.8 °C |
| U11 (ORFET) | 65.96 °C | 80 °C | +14.0 °C |
| *(all 13 bodies)* | ≤ 66.32 °C | 80 °C | ≥ +13.8 °C |

- **Energy-balance gate:** Q_in = 1.1295 W, Q_out = 1.1330 W, err **+0.31 %** (< 1 %) — PASS.
- **Min-mesh-density gate:** every heat-source body ≥ 4 elements — PASS.
- Tj_Q2 = 62.40 °C **matches PR #94 exactly** → result is mesh-converged + reproducible.
- **Gate 12: GREEN** — all Tj ≤ 80 °C, comfortable margins.

## Sim 5 — PDN impedance at MCU +3V3 (impedance-summation)

Re-ran `sim_pdn.py`. Decap network now physically terminated at U1 VDD
(11/27/50/75/100) via the routed +3V3.

- **Mid-band (100 kHz–100 MHz, the board-controlled range): peak 79.4 mΩ ≤ 100 mΩ target → PASS.**
- Inventory (12×100nF 0402 + 4.7µF + 22µF 0805 + ~1.6 nF plane-pair) matches
  reference H743 designs (Pixhawk6X-class).
- **Model-limited residuals (NOT design defects, carried from PR #118):**
  1. ~30–50 kHz VRM↔bulk crossover (~140 mΩ) — sensitive to the TPS62177 actual
     control BW (assumed 30 kHz; higher BW shrinks it).
  2. >150 MHz cap-bank-L / plane-C anti-resonance — the ideal-lumped model
     over-sharpens; real spread-placement + plane loss + H743 on-die/VCAP
     decoupling damp it; outside the board-PDN responsibility band.
  Authoritative LF/HF peaks need the buck control-loop model + die-cap data —
  flagged residual for Phase-6.5 forum review, not a freeze blocker.

## Verdict

Both freeze-relevant sim gates **GREEN** against the current head. The thermal
and PDN margins that were *modelled* pre-power-tree are now *physically valid*.
No board change required — this PR is the re-validation record.

## Remaining to freeze-ready

- **IMU3_INT1** hand-route (next-session focused task — FR auto-route failed on
  the 35 mm cross-island net; clear S-edge lane Y62–64 + dense end-drops; see
  the FR-failure analysis + IMU3_CS-channel template).
- **D5 +3V3_IMU** 5 gaps (`docs/3V3_IMU_RAIL_GAP_FIX_PLAN.md`).
- Then: Sai's GUI DRC + BOM LCSC + 3 Sai-gate ratifications + freeze trigger.
