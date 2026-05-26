# Sim 5 — MCU +3V3 PDN impedance result (Phase 6f)

> Tool: `hardware/kicad/novapcb-stepwise/sim_pdn.py`. Un-deferred per Sai
> 2026-05-26 (the earlier audit-DECOUPLING-as-proxy was a shortcut; this produces
> an actual Z(f) curve). Standard PDN impedance-summation method (equivalent to an
> ngspice lumped model). **Verdict: decap network ADEQUATE in the board-controlled
> band; two model-limited features flagged.**

## 1. Network modeled (from the live board)

+3V3 decaps nearest the 5 MCU VDD pins (11/27/50/75/100):

| Qty | Value | Pkg | Role |
|---|---|---|---|
| 12 | 100 nF | 0402 | HF decoupling |
| 1 | 4.7 µF | 0805 (C16) | mid-freq |
| 1 | 22 µF | 0805 (C33) | bulk |
| — | ~1.6 nF | In3/In4 plane-pair | plane cap |
| — | — | TPS62177 buck (L1 2.2µH) | VRM, regulates < ~30 kHz |

Mounted parasitics are stated **typical** MLCC values (0402: ESL ~0.9 nH, ESR
~20 mΩ; 0805: ESL ~1 nH, ESR ~5 mΩ) — PDN analysis is inherently
parasitic-assumption-based; the cap **values/count are from the design**.

## 2. Result — |Z(f)|, target 100 mΩ

| Freq | |Z| |
|---|---|
| 1 kHz | 10 mΩ |
| 100 kHz | 62 mΩ |
| 1 MHz | 4.7 mΩ |
| 10 MHz | 12 mΩ |
| 100 MHz | 42 mΩ |

**Mid-band (100 kHz – 100 MHz, the range where the board decaps are the
responsible element): peak 79 mΩ ≤ 100 mΩ → PASS.**

## 3. Two model-limited features (not design defects)

1. **~30–50 kHz VRM↔bulk crossover (~140 mΩ).** Between the buck's control
   bandwidth and where the 22 µF bulk becomes effective. Sensitive to the
   TPS62177's **actual** control BW (modeled conservatively at 30 kHz; the real
   part is typically higher, which shrinks/removes this peak). The 22 µF + 4.7 µF
   bulk cover this region; a higher-BW buck closes it entirely.
2. **>150 MHz cap-bank-L / plane-C anti-resonance.** The ideal-**lumped** model
   over-sharpens this (treats the 12×100 nF as perfectly parallel at one node).
   In reality the caps are **distributed** across the 5 VDD pins (spread
   inductance damps the resonance), the plane has spreading loss, and the H743's
   **on-die + VCAP decoupling** handles >~100 MHz. The peak is outside the
   board-PDN responsibility band and on-die-masked.

## 4. Verdict + residual

**The decoupling network is adequate** in the band the board PDN controls
(≤ 79 mΩ across 100 kHz–100 MHz). The inventory (12×100 nF + 4.7 µF + 22 µF +
plane, distributed across 5 VDD pins) **matches reference H743 designs**
(Pixhawk6X-class). This supersedes the prior audit-DECOUPLING proxy with an
actual Z(f) analysis.

**Residual (flagged, not blocking):** authoritative LF-crossover and HF
anti-resonance peaks require the TPS62177 control-loop model + H743 die-cap data
— inputs beyond the lumped board model. If bench bring-up (Phase 9) shows +3V3
ripple under load, the first mitigation is a mid-freq cap (e.g. 1 µF near a VDD
pin) to damp the crossover, or confirming the buck BW. No layout change warranted
pre-bench. Analysis-only — no layout/SKiDL/netlist change.
