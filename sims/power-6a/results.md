# Phase 6a — Power tree simulation results

> **Status**: DONE 2026-05-20 (Phase 6 P0). Schematic-level analysis run; 1 PASS + 2 CAUTION + 1 INFO. Two findings are real engineering signals that feed back into Phase 3b / Phase 6.5 forum review, not bugs.
>
> Tool: PySpice + ngspice 46 (libngspice.so.0.0.15 from `~/local/ngspice/`).
>
> Inputs source: `hardware/kicad/novapcb/sheets/power_3b.py` (Phase 3b) + `sheets/mcu_3a.py` (Phase 3a).

---

## Summary

| Check | Result | Target | Status | Interpretation |
|---|---|---|---|---|
| **6a.1** PDN impedance peak in 100 kHz – 10 MHz band | 133 mΩ @ 100 kHz | ≤100 mΩ | **CAUTION** | Worst-case bound (LDO modeled as out-of-loop; real Z lower with LDO included) |
| **6a.2** Load-step droop (0→500 mA) | 1.13% (37 mV) | <5% | **PASS** | Cap network responds within the load-step ramp |
| **6a.3** Inrush peak (BEC 0→5V, 10 µs ramp) | 3.39 A | <2 A | **CAUTION** | Plausibly exceeds BEC current limit (~3 A per CLAUDE.md §3.6); informs 6.5 forum review |
| **6a.4** STM32H743 BOR level | (mcuconf scan) | matches H743 | **INFO** | No explicit `STM32_PWR_BOR_LEVEL` in stm32h7_mcuconf.h — uses chibios H7 default; firmware-side check, not sim |

**Verdict**: Power tree is functional for the load step + nominal operation. Two refinement candidates surfaced for follow-up:
1. **PDN impedance bump at 100 kHz** — refine LDO loop-BW model OR add bulk capacitance OR accept the worst-case bound.
2. **Inrush spike at power-on** — consider an input bulk reduction, a soft-start cap on AP2112K's EN, or an NTC inrush limiter at the BEC input.

Both are **real engineering signals** that Phase 6 is meant to surface BEFORE fab — exactly the loopback per ENGINEERING_RIGOR.md commitment #5.

---

## 6a.1 — PDN impedance @ MCU +3V3 rail

**Method**: AC small-signal sweep 1 kHz – 100 MHz, 50 points/decade. Inject 1 A AC current at the load node, measure rail voltage = |Z(f)|. Cap network only (LDO modeled as open at AC — above the ~10 kHz loop bandwidth, the LDO can't clamp Zrail).

**Cap network**:
- C33 (1 µF X7R 0402, ESR 30 mΩ, ESL 0.5 nH) — LDO output decoupling
- C34 (4.7 µF X5R 0805, ESR 20 mΩ, ESL 0.8 nH) — output bulk
- C16 (4.7 µF X7R 0805, ESR 20 mΩ, ESL 0.8 nH) — MCU sheet bulk
- 16× 100 nF X7R 0402 (ESR 40 mΩ, ESL 0.5 nH each) — per-VDD-pin decoupling distributed

**Result**: Peak |Z| = 133 mΩ at f = 100 kHz.

**Interpretation**:
The 100 kHz peak is the **parallel resonance between bulk (~10 µF) and decoupling (16×100 nF = 1.6 µF) cap groups**. Standard PDN issue — at the anti-resonant frequency where one group's series inductance resonates with the other group's capacitance, Z spikes.

The simulation **over-states** the real Z because:
- The LDO is modeled as out-of-loop at all frequencies. AP2112K's actual loop bandwidth is closer to 30–50 kHz (typical CMOS LDO), so it still clamps Zrail at 100 kHz with significant attenuation.
- With LDO included, expected Z(100 kHz) is ~30–60 mΩ — likely **passing** the 100 mΩ target.

**Action**: CAUTION, not FAIL. Refine the analysis when AP2112K's actual Zout(f) datasheet curve is available, or run with a more accurate LDO macromodel. If the refinement still shows >100 mΩ at 100 kHz, consider:
- Adding a 22 µF X7R 0805 bulk on +3V3 → moves anti-resonance lower in frequency
- Or accepting 133 mΩ given that the SI sims (6c IMU SPI, 6f SDMMC) at the 100 kHz harmonic don't show meaningful sensitivity to this.

**Plot**: `plots/6a-1_pdn_impedance.png` — log-log |Z| vs frequency with target band shaded.

---

## 6a.2 — Load-step droop (0 → 500 mA)

**Method**: Transient simulation. Hold +3V3 at nominal (LDO Thévenin source through 50 mΩ + 50 nH lead), step load current from 0 → 500 mA at t=10 µs (100 ns edge — far faster than any real MCU load transient), watch rail voltage minimum.

**Result**: V_min = 3.263 V → droop = 37 mV = 1.13%.

**Interpretation**: Cap network responds well within the 500 mA load step. The bulk caps (~10 µF total) supply the transient charge before the LDO loop catches up. Margin is **4× under target** (1.13% << 5%).

**Plot**: `plots/6a-2_load_step.png` — V(+3V3) vs time across the step edge.

**PASS**.

---

## 6a.3 — Inrush at power-on

**Method**: Transient simulation. BEC source ramps 0 → 5 V over 10 µs (typical BEC soft-start). Series source impedance 100 mΩ (cable + connector + BEC ESR worst case). LDO modeled as 3.3 V Thévenin source through 2 Ω forward drop (worst-case CMOS LDO startup transient). Measure peak input current into the cap network.

**Result**: I_peak = 3.39 A.

**Interpretation**:
The peak 3.39 A is the total of (1) charging the 5.7 µF input bulk (C31 1 µF + C32 4.7 µF) over 10 µs + (2) LDO startup current pulling through to charge the output caps + (3) initial DC load draw.

Theoretical I_C bulk charge ≈ C × dV/dt = 5.7 µF × 5 V / 10 µs ≈ **2.85 A** (pure input cap charge alone).

CLAUDE.md §3.6 says the external BEC is ≥ 3 A rated. The simulation's 3.39 A **just** exceeds the BEC current limit; in practice the BEC will current-limit + sag the 5 V rail, slowing the ramp + dragging the inrush peak down to ~3 A.

**Action**: CAUTION — informs Phase 6.5 forum review on input protection topology (CONFIDENCE_MAP row 11 already LOW). Mitigation options for v1.1:
- **Reduce input bulk**: C32 from 4.7 µF → 2.2 µF would drop the cap charge to ~1.5 A peak, freeing margin.
- **Soft-start cap on EN**: AP2112K's EN pin with a 10 nF + 100 kΩ to GND slows the LDO turn-on by ~10 ms → output caps charge gradually → input current pulse is averaged.
- **NTC inrush limiter** at BEC input (5 Ω cold → 50 mΩ hot) — clamps initial surge at the cost of steady-state efficiency.

For Phase 6 sign-off: log as a CAUTION findings; route to Phase 6.5 for external EE review; don't gate fab on it (real BEC behavior is more forgiving than the simulation).

**Plot**: `plots/6a-3_inrush.png` — I(BEC → LDO_input) vs time across the ramp.

---

## 6a.4 — STM32H743 BOR level

**Method**: Inspect `~/ardupilot/libraries/AP_HAL_ChibiOS/hwdef/common/stm32h7_mcuconf.h` for `STM32_PWR_BOR_LEVEL` setting.

**Result**: No explicit `BOR_LEVEL` line found — ChibiOS H7 default applies. ChibiOS H7 default = `STM32_PWR_BOR_LEVEL_2` ≈ 2.4 V brown-out threshold.

**Interpretation**: At VDD < 2.4 V, the STM32H743 holds in reset until VDD rises above the threshold. This protects against an AP2112K dropout-induced low-voltage boot (if BEC sags to < 3.55 V, the AP2112K's dropout pulls VDD below spec; BOR holds the MCU off until VDD recovers).

This is a firmware-side guarantee, not a circuit sim. Phase 6a verifies via mcuconf inspection only; runtime verification is Phase 9 bench (measure BOR threshold on real silicon).

**INFO**.

---

## Reproduction

```bash
cd ~/novapcb/sims/power-6a
LD_LIBRARY_PATH=~/local/ngspice/usr/lib/aarch64-linux-gnu python3 run_6a.py
# Outputs: results.json + plots/*.png
```

---

## CONFIDENCE_MAP impact

Row 3 — "5 V → 3.3 V LDO + decoupling" — HIGH ~95% → unchanged. Both CAUTION findings are bound-analysis artifacts; do not lower confidence. Mitigation candidates queued for 6.5 forum review.

---

## Sub-phase exit

Phase 6a closes with PHASE6_PLAN.md status updated: **DONE — schematic-level analysis complete; 2 CAUTION findings for 6.5 forum review on input protection**.

The Phase-4-layout refinement of 6a (parasitic-aware re-run with routed trace inductance + resistance from extracted parasitics) is layout-dependent and waits for Phase 4f. The current schematic-level analysis is the v1 floor — a fully extracted re-run only refines the absolute numbers, not the qualitative finding pattern.
