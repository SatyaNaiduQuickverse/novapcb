# Sim 3 — SDMMC1 signal-integrity result (Phase 6f)

> Tool: `hardware/kicad/novapcb-stepwise/sim_sdmmc_si.py`. Method per
> `SIM_SUITE_PLAN §3` (length-extraction + flight-time skew; no FEM needed).
> Resolves the ±0.5mm-gate-vs-SD-skew-budget question raised in
> `MICROSD_ROUTING_SURVEY §47`, and the `STM32_SDC_MAX_CLOCK` lift deferred to
> this sim (`BUILD_BASELINE.md`, `INTERFACE_CONTRACT §`). **Verdict: PASS.**

## 1. Routed lengths (from board)

| Net | Length |
|---|---|
| SDMMC1_CLK | 60.045 mm |
| SDMMC1_CMD | 81.216 mm |
| SDMMC1_D0 | 57.234 mm |
| SDMMC1_D1 | 60.883 mm |
| SDMMC1_D2 | 77.324 mm |
| SDMMC1_D3 | 85.914 mm |
| data avg | 70.339 mm |

## 2. Flight-time skew

Traces are outer-layer microstrip (F.Cu ref In1 GND, B.Cu ref In4 GND),
t_pd ≈ 6.0 ps/mm (er_eff ~3.2); range 5.9 (microstrip) – 7.1 (stripline) ps/mm.

| Skew | Δlength | flight time |
|---|---|---|
| data-to-data (D0-D3) | 28.68 mm | **172 ps** (169–204) |
| CLK-to-data (worst) | 25.87 mm | 155 ps (153–184) |
| CMD-to-CLK | 21.17 mm | 127 ps (125–150) |

## 3. Skew vs bit period (SDR)

| Clock | Period | Worst skew / period | Verdict | |
|---|---|---|---|---|
| 12.5 MHz | 80.0 ns | 0.22 % | PASS | **current cap** |
| 25.0 MHz | 40.0 ns | 0.43 % | PASS | |
| 50.0 MHz | 20.0 ns | 0.86 % | PASS | **SDR25 target** |
| 100.0 MHz | 10.0 ns | 1.72 % | PASS | (headroom check) |

SD High-Speed host timing budget (SD Physical Layer Spec): tISU = 6 ns +
tIH = 2 ns = 8 ns window. Worst trace skew 172 ps = **2.2 %** of that window.

## 4. Gate resolution

- **Plan-doc ±0.5mm data-match gate: FAIL** (28.7 mm spread). This is a
  DDR-memory-class length-match spec and is **inappropriate for an SD
  interface** — confirmed the concern raised in `MICROSD_ROUTING_SURVEY §47`.
- **SD-appropriate skew budget: PASS** at all rates including the 50 MHz SDR25
  target. Length-induced skew (172 ps) is < 1 % of the 50 MHz bit period and
  2.2 % of the setup+hold window — negligible.

**Recommendation:** retire the ±0.5mm gate for SDMMC; replace with the
SD-appropriate criterion *"worst data-bus flight-time skew ≤ 10 % of the bit
period at the target clock"* (here 0.86 % at 50 MHz). No re-routing of SDMMC1
is warranted — the existing routing is electrically sound.

**Clock-cap note:** from a length-skew standpoint the `STM32_SDC_MAX_CLOCK`
cap is liftable from 12.5 MHz to the 50 MHz SDR25 target. (Skew is only one SI
factor; crosstalk/reflection are bounded by the slow CMOS edges + `Default`
0.20 mm controlled-impedance class per `CONTROLLED_IMPEDANCE.md`. The cap lift
is a firmware decision; this sim removes the length-skew objection to it.)

## 5. Verification

Analysis-only — **no layout / SKiDL / netlist change**. Reproducible via
`python3 sim_sdmmc_si.py`. Closes the SDMMC length-matching item (task #77).
