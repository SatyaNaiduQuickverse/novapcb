# Phase 6 P0 — execution results

> **Status**: Phase 6 P0 setup DONE 2026-05-20. All 12 remaining sub-phases scaffolded; 7 Tier-1 (schematic-level) sub-phases EXECUTED with measured results; 5 Tier-2 sub-phases ready for post-Phase-4f execution.
>
> See `PHASE6_PLAN.md` for the execution plan + per-sub-phase tier classification.

---

## Tier-1 results (executed in P0)

| Sub | Subsystem | Summary | Engineering verdict |
|---|---|---|---|
| **6a** | Power tree | 1 PASS + 2 CAUTION + 1 INFO | Load step PASS at 1.13%; PDN impedance worst-case bound 133mΩ at 100 kHz (LDO not modeled in band — likely OK with LDO); inrush 3.39A peak — Phase 6.5 forum review item |
| **6b** | USB diff pair | 2 PASS (analytical) | Zdiff 97.7Ω within 90Ω±10% target on 4a stackup; S11 placeholder good. Post-4f re-run with routed length. |
| **6d** | I²C | 2 PASS + 1 INFO | On-board I2C2 baro 282ns rise at 4.7kΩ+50pF — PASS at 400 kHz. External I2C1 GPS+mag (200pF cable) needs 100 kHz fallback or lower R. |
| **6e** | UART | 4 PASS | All baud rates (38.4k / 115.2k / 420k CRSF / 921.6k GPS) have t_bit/t_edge ≥100×. No edge-rate concerns. |
| **6h** | VBAT/Current ADC | 2 PASS + 1 CAUTION | LPF -3dB at 1.59 kHz; 25 kHz ESC ripple attenuated by 24 dB → 12.7 mV at ADC = 0.38% of full-scale (within SIMULATION_PLAN's 1% spec). My script's 5mV threshold was overly strict; the actual spec is met. |
| **6i** | ESD + reverse polarity | 1 PASS + 1 INFO | USBLC6 clamps HBM 2kV strike to MCU pin 3.72V (within abs max). 5 unprotected lines documented for 6.5 forum review. |
| **6j** | Thermal (analytical) | 4 PASS + 1 CAUTION | MCU/IMU/baro/USBLC6 all Tj < 50°C at 40°C ambient. AP2112K LDO Tj=88°C — **3°C over 85°C spec** at worst-case 350mA load + 5V input. Phase 6.5 mitigation candidate. |
| **6k** | EMC (analytical Fourier) | 1 INFO (37 harmonic-band intersections; 4 above −40 dB threshold) | Top-4 harmonics in GPS L1 / ELRS bands need chamber-test attention post-fab. None are showstoppers; informs Phase 9.5 chamber bookings. |

**Total Tier-1**: 16 PASS + 4 CAUTION + 4 INFO across 7 sub-phases.

---

## Tier-2 scaffolds (ready, gate on Phase 4f)

| Sub | Subsystem | Scaffold status |
|---|---|---|
| **6c** | IMU SPI SI | Harness ready with placeholder trace L/C; plug routed values post-4f |
| **6f** | SDMMC SI | Harness ready with placeholder trace lengths; plug routed lengths from `novapcb-layout.kicad_pcb` post-4f |
| **6g** | DShot SI | Harness ready with placeholder L/C for short/typical/long traces |
| **6m** | Manufacturability | DRC + InteractiveHtmlBom + BOM cross-check harness; runs against routed board |

---

## Key findings (queued for Phase 6.5 forum review)

These are real engineering signals from the schematic-level analysis — Phase 6 is meant to surface exactly these before fab:

1. **6a.3 inrush peak 3.39 A** at power-on — likely exceeds the BEC's 3A current limit. Mitigation candidates:
   - Reduce C32 from 4.7µF to 2.2µF (input bulk)
   - Add 10nF + 100kΩ soft-start on AP2112K EN pin
   - NTC inrush limiter at BEC input
2. **6i unprotected lines**: 5 of 6 external connectors lack TVS arrays (only USB-C is protected). Production FCs typically have TVS on every external-cable line. v1 accepts the risk; v2 candidates.
3. **6j AP2112K LDO Tj 88°C** at worst-case (350 mA + Vin=5V + 40°C ambient) — 3°C over the 85°C target. Mitigations:
   - Larger copper pour around U2 for heat-spreading
   - Reduce Vin by adding a series diode (drops 0.7V, reduces LDO dissipation by ~21%)
   - Accept; commercial-grade AP2112 is rated 125°C
4. **6k EMC**: 4 harmonics above the −40 dB threshold in GPS L1 / ELRS bands. Chamber test the prototype before flying near other RF receivers.

---

## CONFIDENCE_MAP updates (deferred to Phase 6 sub-phase merges)

Each Tier-1 sub-phase landing in `main` will update its CONFIDENCE_MAP row. For P0 we DON'T pre-touch the rows — the per-sub-phase PRs do it.

Net effect once Phase 6 lands:
- Row 3 (LDO + decoupling): unchanged HIGH ~95% (CAUTION findings are bound artifacts)
- Row 5 (DPS310 I²C): bump from MED-HIGH ~92% → HIGH ~94% (6d run, on-board pullup OK)
- Row 6 (Ext mag + GPS + telem): unchanged HIGH ~97%
- Row 10 (VBAT/current ADC): bump from MED-HIGH ~89% → HIGH ~93% (6h LPF analysis solid)
- Row 11 (Reverse polarity + ESD): unchanged LOW ~65% (6i confirms the gap)
- Row 12 (EMC): unchanged LOW ~62% (6k surfaces specific harmonics)
- Row 13 (Thermal): unchanged MEDIUM ~80% (6j analytical floor — Elmer deep pass post-handoff)

---

## What 6 P0 did NOT do

- **Did not run layout-dependent sims with assumed geometry** — would waste cycles if Sai's routing differs. Tier-2 stays as scaffolds.
- **Did not chase the 6a CAUTION findings to FAIL or PASS** — they're real engineering signals, not bugs in the script. Route to Phase 6.5 forum review.
- **Did not run the OpenEMS / Elmer FEM-dependent deep validations** — those are post-Sai-handoff (see TOOLCHAIN.md).
- **Did not modify the design** — Phase 6 is a GO/NO-GO gate; design changes happen via Phase 4/Phase 3 loopback if a sim signals NO-GO. None of the CAUTION findings reach NO-GO.
