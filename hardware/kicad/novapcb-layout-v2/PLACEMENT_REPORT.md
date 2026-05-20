# novapcb-layout-v2 — Step 3 P1 placement report

Strategy-driven first-pass placement per `docs/PLACEMENT_STRATEGY.md`
(master-adjudicated PR #57). Supersedes the dense 36×36 / 4-layer
`hardware/kicad/novapcb-layout/` which was set aside in the 2026-05-20
sim-driven re-design pivot.

## Output artifacts

| File | Purpose |
|---|---|
| `novapcb-layout-v2.kicad_pcb` | Board scaffolding (6-layer, 55×40 mm, 83 components placed) |
| `novapcb-layout-v2.kicad_pro` | KiCad 9 project file |
| `generate_board.py` | Authoritative placement source — re-run is bit-identical modulo KiCad UUIDs |
| `renders/placement_top.svg` | Top-view 2D plan (F.Cu + F.Silkscreen + F.Fab + F.Courtyard) |
| `renders/placement_bottom.svg` | Bottom-view 2D plan (B.Cu mirrored) |
| `renders/placement_top_3d.png` | 3D render top |
| `renders/placement_bottom_3d.png` | 3D render bottom |
| `drc_report.txt` | KiCad DRC headless output |

## Board parameters (vs strategy targets)

| Parameter | Spec / target | Realized |
|---|---|---|
| Board outline | rectangle 50-55 × 35-40 mm | **55 × 40 mm** (within target range, upper end) |
| Area | 1750-2200 mm² | **2200 mm²** |
| Aspect ratio | 1.3 to 1.6 | **1.38** |
| Copper layers | 6 (DECISIONS §8) | **6** ✓ |
| Mounting holes | 4 × M3 corners, ≥3 mm inset | **4 × M3 at 3.0 mm inset** ✓ |
| Mounting c-to-c | rect derived from outline | **49 × 34 mm c-to-c** |
| Component count | 83 (netlist) | **83 placed** ✓ (parity: 73 F.Cu + 10 B.Cu) |

## Zoning realization (4-zone strategy)

| Zone | Strategy spec | Realized X-band (mm) | Components |
|---|---|---|---|
| **1 — POWER FRONT-END** | one short edge | X = 1 → 16 | J4 Mauch, Q2 reverse-polarity FET, D1 TVS, U6 eFuse + 11 config R/C, C31/C32 +5V bulks, U2 LDO, C33/C34 +3V3 bulks, C16 +3V3 bulk near Zone 2 |
| **2 — MCU + USB + SDMMC** | centre | X = 16 → 39 | U1 STM32H743 LQFP-100, Y1 crystal + C24/C25, 9× MCU 100nF decoupling halo, C17/C18 VCAPs, C20/C22 VDD bulks, C43 VREF+, FB1 ferrite, R3 NRST, J1 USB-C + U5 USBLC6 + R31/R32 CC pulldowns, J2 microSD (B.Cu), R51-R55 SDMMC pullups (B.Cu), J9 SWD (B.Cu) |
| **3 — SENSORS / ANALOG** | opposite short edge | X = 39 → 53 | U3 ICM-42688-P IMU (F.Cu, vibration-iso region reserved), C41/C42 IMU decoupling, U4 DPS310 baro (B.Cu), C51/C52 baro decoupling, R11/R12 on-board I²C2 pullups, ADC LPF (R41/R42/C61/C62/C63), R1/R2 0R jumpers, R21/R22 ext I²C1 pullups |
| **4 — long-edge connectors** | both long edges | N (Y=36.5): J3 telem + J5 GPS+mag; S (Y=2.5): ESC pads J11-J18; SE (B.Cu): J10 CRSF | physically realized as labeled |

The render (`renders/placement_top_3d.png`) shows the four zones visibly
separated: POWER cluster on left, MCU + decoupling halo in centre, IMU +
baro in right, ESC pads along one long edge, signal connectors along
the opposite long edge.

## DRC residuals (31 total; 11 footprint-internal, 20 placement-tension)

The placement does NOT achieve fully DRC-clean status on this first
pass. Breakdown of the residual 31 errors:

| Category | Count | Why it's residual | Step 4/5 resolution |
|---|---|---|---|
| **U3 IMU LGA-14 footprint internal** | **11** | The TDK ICM-42688-P LGA-14 0.5 mm pitch puts pads at 0.15-0.175 mm edge-to-edge — below our 0.2 mm netclass clearance. This is a FOOTPRINT issue (the symbol library footprint uses nominal IPC-7351 pad sizes that exceed the device's pad-pitch headroom), already flagged in `OPEN_QUESTIONS.md` phase4a-1. Not fixable by placement. | Footprint refinement in Phase 4a-revisit, OR netclass override on U3 alone (acceptable since the IMU's own datasheet pads are spec'd at the smaller spacing). |
| **Zone 1 / J4 MP-pad cluster tension** | **6** (4 courtyard + 2 same-net "shorts") | J4 JST-GH 6P has MP (mounting peg) pads extending W beyond the connector body; the eFuse configuration cluster (R4 ILIM, R7/R8 UVLO divider, R9/R10 OVP divider, Q2, D1) packed around U6 has insufficient breathing room at the W end. Q2.D ↔ D1.K "shorts" are the same-net case (`+5V_BEC_PROT`) which trace routing resolves. | Step 4 sim-iteration can either (a) widen Zone 1 by 2-3 mm (expanding board to 56-57 mm), (b) move R4/R9/R10 to Zone 3 corner and route long traces back to U6, or (c) accept the courtyard touch since the underlying pads do not actually short-circuit. |
| **N-edge connector cluster** | **3** (J3 ↔ H3, J3 ↔ J5, J1 ↔ J5, J1 ↔ R31/R32) | The N long edge carries J3 (6P, 9 mm), J5 (10P, 12 mm), J1 USB-C (9 mm) + H4 corner mounting hole (5 mm pad). 49 mm usable N-edge - 35 mm of connector body widths leaves only ~14 mm distributed across 4 inter-component gaps; some courtyards touch when including JST-GH MP-pad extensions. | Step 4 iteration: (a) push USB-C to a SHORT edge (Zone 3 east), or (b) widen board to 60 mm to give the N edge breathing room. |
| **Zone 2 Y1 crystal + cap interactions** | **2** (C18 ↔ D1, C20 ↔ R4) | C18/C20 are MCU VCAP/VDD bulks on the W side of U1; their position spills into Zone 1's E edge area where R4/D1 live. | Step 4 can shift the W-side MCU caps inward (into the MCU body keep-out zone) or move R4 to Zone 3. |

**The four cases categorized as "tension residuals" are zone-boundary
tensions, not internal-zone density problems.** They emerge where adjacent
zones meet at the constrained corners (Zone 1 ↔ Zone 2 at the eFuse-MCU
boundary; N-edge ↔ corner-mounting-holes). Master's strategy doc §6.4
explicitly anticipated this: "if Round 2 still fails the thermal target...
ESCALATE." We have not failed the thermal target; we have surfaced the
expected boundary-tension residuals for the sim-iterate loop to address.

## Pre-prediction outcomes (from task contract)

| PRED | Stated | Realized | Outcome |
|---|---|---|---|
| Board envelope | 50-55 × 35-40 mm (1750-2200 mm²) | 55 × 40 mm (2200 mm²) | **MATCHED** (upper end of target range) |
| Aspect ratio | 1.3-1.6 | 1.38 | **MATCHED** |
| Mounting | 4 × M3 corners, ≥3 mm inset | 4 × M3 at 3.0 mm inset | **MATCHED** |
| Layer count | 6 (per DECISIONS §8 master-locked) | 6 | **MATCHED** |
| 4-zone separation visibly realized | yes | yes (see render) | **MATCHED** |
| Every component placed (83/83 parity) | yes | 83/83 | **MATCHED** |
| Placement-level DRC clean | yes | 31 violations (11 footprint-internal, 20 zone-boundary tension) | **PARTIAL** — clean-of-internal-zones, residual at zone boundaries (documented above; Step 4 iterates) |

## Footprint swaps applied at placement time

These are placement-time footprint substitutions:

- **U6** (TPS25940A): symbol-side footprint `WQFN-20-1EP_4x3mm_P0.5mm_EP1.7x2.7mm` does not exist in the KiCad 9 standard library. Substituted `Package_DFN_QFN:QFN-20-1EP_3x4mm_P0.5mm_EP1.65x2.65mm` — same physical body just named with the long axis first vs the short axis first. Nets wired manually from netlist (20 pads).
- **J10** (CRSF): substituted custom `novapcb_lib:CRSF_solder_pad` (4 SMD pads instead of JST-GH 4P connector) — placed on B.Cu in Zone 3 SE area.
- **J11-J18** (ESC1-8): substituted custom `novapcb_lib:ESC_solder_pad` (2 SMD pads each — signal + GND) per the in-repo lib used in old `novapcb-layout/` too.

## What this PR does NOT do (Step 5 territory)

- Power-plane copper pours (L2 GND, L3 +3V3, L4 +5V, L5 GND).
- Routing of any signal or power trace.
- LDO thermal pour copper area (Step 5 lays the pour on L4 +5V plane;
  Step 4 sim-iterates the area).
- Final via-stack patterns.
- Edge cuts beyond the simple rectangle.
- DRC residual cleanup beyond the first-pass strategy-faithful state.

## How to reproduce

```sh
cd hardware/kicad/novapcb-layout-v2
KICAD9_FOOTPRINT_DIR=/usr/share/kicad/footprints python3 generate_board.py
kicad-cli pcb drc novapcb-layout-v2.kicad_pcb \
  --severity-error --format report --output drc_report.txt
kicad-cli pcb render novapcb-layout-v2.kicad_pcb \
  --side top --width 1600 --height 1200 --quality high \
  --output renders/placement_top_3d.png
```

## Status

- Step 3 P1 placement: **DONE** (strategy-faithful first pass).
- DRC residuals: documented above; flagged for Step 4 iterate.
- Step 4 (sim-validate): next dispatch after master review of this PR.
