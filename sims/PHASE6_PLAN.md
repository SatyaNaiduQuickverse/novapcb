# Phase 6 — Simulation execution plan

> **Status**: Phase 6 P0 setup 2026-05-20. Per-sub-phase scaffolds live in `sims/<subsystem>/`. Run order + schematic-vs-layout dependency captured below.
>
> **6l SITL regression** already DONE (PR #52). 6a power tree may run now (fully schematic-level — see §6a).
>
> **Layout-dependent sub-phases gate on**: Sai's GUI routing + Phase 4f gerber export (`hardware/kicad/novapcb-layout/run_gerber_export.py`).

---

## Why Phase 6 P0 exists

Same pattern as Phase 3 P0 (SKiDL scaffolding) and Phase 4 P0 (placement test): write the harness ahead of the data so that when the data lands, the simulations run *fast* instead of being authored from scratch.

For Phase 6 specifically: when Sai's routing lands + Phase 4f exports gerbers/drill/Touchstone-extracted parasitics, the layout-dependent SI sims (6b USB, 6c IMU SPI, 6f SDMMC, 6g DShot) should run in minutes, not days. Pre-built scaffolds with clearly-marked TODO trace-geometry inputs make that possible.

P0 also identifies which sub-phases are **fully schematic-level** (run now) vs **layout-dependent** (gate on Phase 4f) vs **partial** (some checks run now, deeper validation post-layout).

---

## Per-sub-phase summary

| Sub | Subsystem | Primary tool | Input dependency | Status post-P0 |
|---|---|---|---|---|
| 6a | Power tree | ngspice + PySpice + analytical | Mostly schematic-level; routed trace L/R parasitics refine but don't define | **RUN NOW** (per 6P0.6) |
| 6b | USB-CDC diff pair | Hammerstad-Jensen + scikit-rf (OpenEMS deferred) | Stackup + trace geometry — 4d already locked W=0.25/S=0.10/h=0.21mm; lengths plug in post-4f | **Scaffold ready; geometry-plug-in post-4f** |
| 6c | IMU SPI bus | ngspice + IBIS (estimated from datasheet) | Trace length + via count + driver IBIS | Scaffold ready; layout-dependent |
| 6d | I²C buses (baro + GPS/mag) | ngspice (RC analysis) | Pullup R + bus C — schematic-level for pullup-vs-load choice + tracelen-est | **PARTIAL — pullup analysis runs now; final BUS_C post-4f** |
| 6e | UARTs (GPS, CRSF) | ngspice rise-time | Datasheet rise/fall + load cap | **PARTIAL — schematic-level rise-time runs now; line driving post-4f** |
| 6f | SDMMC bus (SDR25 → 12.5 MHz) | ngspice + IBIS | Trace length/skew + pullup analysis | Scaffold ready; layout-dependent on trace lengths |
| 6g | ESC DShot outputs (300/600) | ngspice + IBIS | Trace length to solder pad + IBIS | Scaffold ready; layout-dependent |
| 6h | VBAT / current sense ADC | ngspice + noise analysis | RC filter + Mauch HS-200-LV datasheet — fully defined | **RUN NOW** (RC + LPF + noise) |
| 6i | Reverse polarity + ESD | ngspice transient + analytical | Protection topology — novapcb v1 currently has minimal protection (3b sheet flagged for Phase 3.5 + 6.5 forum review) | **PARTIAL — analyze gap, document for 6.5 forum review** |
| 6j | Thermal | Elmer FEM (SAI-HANDOFF) — analytical lumped fallback | Component dissipation + board area | **PARTIAL — analytical lumped-element estimate now; Elmer post-handoff** |
| 6k | EMC / clock-harmonics | Analytical Fourier (OpenEMS deferred) | Clock frequencies + transition times — schematic-level | **PARTIAL — analytical spectrum now; coupling post-4f** |
| 6l | ArduPilot SITL functional | SITL (HAL_BOARD_SITL) | ArduPilot defaults.parm + CH7 mode map | **DONE** (PR #52, 18/18 PASS) |
| 6m | Manufacturability — DRC / DFM / BOM | KiCad + interactiveHtmlBom | Routed board + gerbers | Scaffold ready; gates on Phase 4f |

---

## Run order

### Tier 1 — Run NOW (schematic-level only, no routing needed)
1. **6a Power tree** — AP2112K LDO + cap network analysis. Run in P0; ship result here.
2. **6h ADC noise** — Mauch RC filter LPF + noise — fully defined from Phase 3h sheet.
3. **6d I²C pullup analysis** — 4.7kΩ choice + bus-cap budget — schematic-level partial.
4. **6e UART rise-time** — CRSF 420kbaud + GPS protocols — schematic-level partial.
5. **6i ESD/reverse-polarity** — analyze the (currently-minimal) protection gap; document for the Phase 6.5 forum review.
6. **6j Thermal** — analytical lumped-element estimate as a floor (Elmer FEM later when Sai installs it).
7. **6k EMC analytical Fourier** — clock harmonics from 8 MHz HSE + 16 MHz SPI + 12.5 MHz SDMMC + 600 kHz DShot + 1.5 GHz USB → check against GPS L1, ELRS bands.

### Tier 2 — Gate on Sai's routing + Phase 4f gerber export
8. **6b USB diff pair** — Hammerstad-Jensen (Phase 4d done) + scikit-rf transmission-line model on actual routed trace length.
9. **6c IMU SPI SI** — ringing + setup/hold on actual trace.
10. **6f SDMMC SI** — clock skew on actual trace lengths.
11. **6g DShot SI** — ringing on actual MOTx trace.
12. **6m Manufacturability — DRC / DFM / interactiveHtmlBom** — on routed board + gerbers.

### Tier 3 — Layout-dependent + tool-handoff-blocked
13. **6j Thermal — Elmer FEM deep pass** — after Sai installs Elmer or equivalent.
14. **6b / 6k OpenEMS deep validation** — after Sai installs OpenEMS or equivalent (per TOOLCHAIN.md OpenEMS deferral).

---

## Per-sub-phase files

Each `sims/<subsystem>/` directory contains:
- `README.md` — what this sim covers + what its inputs are
- `run_6X.py` — the script harness (PySpice / scikit-rf / analytical Python)
- `results.md` — populated post-run with pass/fail + plots
- `results.json` — structured per-check pass/fail (canonical)
- Plus per-sub-phase data files (Touchstone, plots, etc.)

Tier-1 sub-phases ship complete scripts. Tier-2 sub-phases ship harness + clearly-marked TODO sections for the layout-dependent inputs.

---

## SIMULATION_PLAN.md per-sub-phase pass criteria (reproduced for ready reference)

| Sub | Pass criterion |
|---|---|
| 6a | <5% rail droop on step; impedance ≤100 mΩ across 100 kHz–10 MHz; BOR matches H743 setting; inrush <2 A peak |
| 6b | Zdiff = 90 Ω ±10%; \|S11\| < −15 dB to 480 MHz; crosstalk margin > 20 dB |
| 6c | Rise/fall <5 ns; setup/hold margin >2 ns; no ringing past 200 mV |
| 6d | SDA/SCL rise ≤300 ns @ 400 kHz I²C; no overshoot >+0.5V; bus cap budget within spec |
| 6e | UART eye open at 420 kbaud + GPS 38400; no excessive ringing |
| 6f | Clock skew <2 ns across 4 data lines at 12.5 MHz SDMMC clock |
| 6g | DShot300/600 rise/fall + ringing within ESC tolerances (rise <100 ns @ 600 kHz) |
| 6h | ADC accuracy <1% at full scale; settling <10 µs to within 0.5 LSB; cross-talk <0.1% |
| 6i | Survive ±2 kV HBM ESD; reverse polarity protection clamps within MCU absolute max |
| 6j | Steady-state junction temp <85°C ambient + load; no hot spots on board area |
| 6k | All clock harmonics below sensitive bands (GPS L1 1575 MHz, ELRS 868/915 MHz) emission limit |
| 6l | All flight modes engage + failsafes + heartbeat (DONE 2026-05-20) |
| 6m | DRC clean, BOM ↔ board cross-check 100%, interactiveHtmlBom renders |

---

## Tooling per sub-phase (from TOOLCHAIN.md §2)

| Tool | Sub-phases using | Status |
|---|---|---|
| ngspice (binary) + PySpice (Python) | 6a, 6c, 6d, 6e, 6f, 6g, 6h, 6i | INSTALLED userspace (`~/local/ngspice/`) |
| scikit-rf | 6b, 6k | INSTALLED |
| numpy + scipy + matplotlib | All | INSTALLED |
| InteractiveHtmlBom | 6m | INSTALLED |
| kicad-cli (DRC) | 6m | INSTALLED |
| OpenEMS | 6b, 6k (deeper) | **DEFERRED** — analytical fallback ships now |
| Elmer FEM | 6j | **DEFERRED** — analytical lumped fallback ships now |

---

## Confidence map updates

Each sub-phase, on completion, updates `docs/CONFIDENCE_MAP.md` per the row it touches:
- 6a → row 3 (LDO + decoupling)
- 6b → row 2 (USB-CDC) + row 8 stackup
- 6c → row 4 (IMU SPI)
- 6d → row 5 (Baro I²C) + row 6 (Ext I²C/UART)
- 6e → row 6 (UART), row 9 (CRSF)
- 6f → row 7 (SDMMC)
- 6g → row 8 (ESC DShot)
- 6h → row 10 (VBAT/current sense)
- 6i → row 11 (Reverse polarity / ESD)
- 6j → row 13 (Thermal)
- 6k → row 12 (EMC)
- 6m → row 14 (Manufacturability — already partially covered Phase 4f)

---

## What 6 P0 does NOT do

- **Doesn't run layout-dependent sims early** — that would mean assuming trace geometry; if Sai's routing differs, the work is wasted. Tier 2 sub-phases ship scaffold + clearly-marked TODO inputs only.
- **Doesn't replace 6.5 forum review** — the LOW-confidence rows (11 ESD, 12 EMC) still need external EE eyes post-sim.
- **Doesn't lock the v1 design** — Phase 6 is a GO/NO-GO gate; any sub-phase failing kicks back to Phase 4 with measured evidence.
