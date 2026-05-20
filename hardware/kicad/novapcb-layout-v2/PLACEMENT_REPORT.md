# novapcb-layout-v2 — Step 3 P1-rev placement report

Strategy-driven placement per `docs/PLACEMENT_STRATEGY.md` (master-adjudicated PR #57), with the iter-1 zone-boundary courtyard/clearance residuals resolved via board growth per master PR #58 review (2026-05-21): "board size is FREE per Sai's dimension-freedom; grow until the placement is DRC-clean of courtyard/clearance. Step 4 must START from a geometrically valid placement."

Supersedes the dense 36×36 / 4-layer `hardware/kicad/novapcb-layout/` set aside in the 2026-05-20 sim-driven re-design pivot.

## Output artifacts

| File | Purpose |
|---|---|
| `novapcb-layout-v2.kicad_pcb` | Board scaffolding (6-layer, 62×42 mm, 83 components placed) |
| `novapcb-layout-v2.kicad_pro` | KiCad 9 project file |
| `generate_board.py` | Authoritative placement source — re-run is bit-identical modulo KiCad UUIDs |
| `renders/placement_top.svg` | Top-view 2D plan (F.Cu + F.Silkscreen + F.Fab + F.Courtyard) |
| `renders/placement_bottom.svg` | Bottom-view 2D plan (B.Cu mirrored) |
| `renders/placement_top_3d.png` | 3D render top |
| `renders/placement_bottom_3d.png` | 3D render bottom |
| `drc_report.txt` | KiCad DRC headless output (gitignored — regenerable) |

## Board parameters (vs strategy targets)

| Parameter | Strategy target | Realized (P1-rev) |
|---|---|---|
| Board outline | 50-55 × 35-40 mm (estimate, not cap) | **62 × 42 mm** (P1-iter1 was 55×40; grown +13% per master directive) |
| Area | 1750-2200 mm² (estimate) | **2604 mm²** (+18% over P1-iter1 2200) |
| Aspect ratio | 1.3 to 1.6 | **1.48** |
| Copper layers | 6 (DECISIONS §8) | **6** ✓ |
| Mounting holes | 4 × M3 corners, ≥3 mm inset | **4 × M3 at 3.0 mm inset** ✓ |
| Mounting c-to-c | rect derived from outline | **56 × 36 mm c-to-c** |
| Component count | 83 (netlist) | **83 placed** ✓ (parity: 72 F.Cu + 11 B.Cu) |

### Why the board grew from 55×40 to 62×42

P1-iter1 at 55×40 mm produced 20 zone-boundary courtyard/clearance violations that could not be cleared by component repositioning alone — each fix created a new tension elsewhere. The unlock master pointed out: PLACEMENT_STRATEGY explicitly says board size is OUTPUT of placement, not fixed input; 55×40 was an estimate. Growing to 62×42 (+7 mm long × +2 mm short) gives:

- N-edge connector cluster: 51 mm usable N edge for J3 (6P, 9 mm) + J5 (10P, 12 mm) + J1 USB-C (9 mm) + H4 corner mount → 21 mm of inter-component gaps instead of P1-iter1's 14 mm. Cleared all N-edge courtyard overlaps.
- Zone 1 width: 16 mm of usable Zone 1 for J4 Mauch + eFuse front-end cluster (Q2, D1, U6, 11 config R/C, U2 LDO, +5V/+3V3 bulks) instead of P1-iter1's 14 mm. Cleared the J4-MP-pad ↔ eFuse-config-network tensions.
- ESC strip: 46 mm usable S edge for 8 pads at 6.6 mm pitch instead of P1-iter1's 36 mm at 5.5 mm pitch. Cleared the J18 ↔ H2 mounting hole conflict.

Result: **all zone-boundary courtyard/clearance violations cleared.** Only the U3 IMU footprint-internal pad-clearance issues remain (see DRC residual section).

## Zoning realization (4-zone strategy)

| Zone | Strategy spec | Realized X-band (mm) | Components |
|---|---|---|---|
| **1 — POWER FRONT-END** | one short edge | X = 1 → 17 (grown +2 mm) | J4 Mauch, Q2 reverse-polarity FET, D1 TVS, U6 eFuse + 11 config R/C, C31/C32 +5V bulks, U2 LDO, C33/C34 +3V3 bulks, C16 +3V3 bulk near Zone 2 |
| **2 — MCU + USB + SDMMC** | centre | X = 18 → 42 (grown +1 mm) | U1 STM32H743 LQFP-100 (centred at 30, 20), Y1 crystal + C24/C25 load caps, 9× MCU 100nF decoupling halo, C17/C18 VCAPs, C20/C22 VDD bulks, C43 VREF+, FB1 ferrite, R3 NRST, J1 USB-C + U5 USBLC6 + R31/R32 CC pulldowns, J2 microSD (B.Cu), R51-R55 SDMMC pullups (B.Cu), J9 SWD (B.Cu) |
| **3 — SENSORS / ANALOG** | opposite short edge | X = 42 → 60 (grown +6 mm) | U3 ICM-42688-P IMU (F.Cu, vibration-iso region reserved), C41/C42 IMU decoupling, U4 DPS310 baro (B.Cu), C51/C52 baro decoupling, R11/R12 on-board I²C2 pullups, ADC LPF (R41/R42/C61/C62/C63), R1/R2 0R jumpers, R21/R22 ext I²C1 pullups |
| **4 — long-edge connectors** | both long edges | N (Y=37): J3 telem + J5 GPS+mag + J1 USB-C; S (Y=2.5): ESC pads J11-J18; SE (B.Cu): J10 CRSF | physically realized as labeled |

See `renders/placement_top_3d.png` for the rendered top view — the four zones are visibly separated with generous breathing room.

## DRC results — placement-clean except for IMU footprint

**14 violations, ALL footprint-internal on U3 ICM-42688-P. 0 placement-caused violations** (0 courtyard overlaps, 0 placement clearance issues, 0 zone-boundary tensions).

### U3 IMU LGA-14 pad-to-pad clearance (14 errors, footprint-internal)

The KiCad-stock `Package_LGA:LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y` footprint has pads sized 0.625 × 0.35 mm at 0.5 mm pitch — pad-edge-to-pad-edge = 0.15 mm in the pitch direction, below our 0.2 mm netclass clearance threshold. The KiCad footprint is based on the STMicro LSM6DS3TR-C datasheet (per its `descr` field), NOT the TDK ICM-42688-P.

**This is a footprint-geometry issue, not a placement issue** — repositioning U3 anywhere on the board does not change its internal pad-to-pad geometry. The fix is a corrected footprint, not a placement adjustment.

### Why the fix is not in this PR

Per `OPEN_QUESTIONS.md phase4a-1` (updated 2026-05-21 in the accompanying change): a focused attempt to resolve the footprint was made (research agent spent ~30 min reading TDK datasheet DS-000347 v1.5 + v1.6 + ICM-42605 DS-000292 + TDK AN-000262 PCB Design Guidelines, plus attempted vendor-lib downloads). **TDK does not publish the recommended PCB land pattern in the public ICM-42688-P datasheet** — Section 18 explicitly defers to controlled-distribution document AN-IVS-0002A-00 which is not on the public TDK CDN.

Two safe resolution paths exist; both require action outside this PR:
- **(a) Sai escalation**: request AN-IVS-0002A-00 from TDK (free, requires email) and extract the authoritative land pattern. Sai has the PDF tooling per master's directive.
- **(b) Vendor-lib import**: download the KiCad footprint from Ultra Librarian (`https://app.ultralibrarian.com/details/0a4080d3-d392-11ed-b159-0a34d6323d74/TDK-InvenSense/ICM-42688-P`) or SnapEDA (`https://www.snapeda.com/parts/ICM-42688-P/TDK/view-part/`) and record the source URL as the citation.

Both paths are listed in `OPEN_QUESTIONS phase4a-1` with the research findings. The IMU footprint correction is a **HARD must-resolve-before-fab** item (the IMU is the primary sensor — wrong pads = won't solder = dead board), but it is **not blocking on Step 3 P1 placement**, which is the scope of this PR.

### Unconnected items (210) — routing not done = Step 5 work; ignored at placement stage

## Pre-prediction outcomes (from task contract)

| PRED | Stated | Realized | Outcome |
|---|---|---|---|
| Board envelope | 50-55 × 35-40 mm (target estimate) | 62 × 42 mm | **EXCEEDED estimate by 11-13%** (per master directive: estimate not cap; grow until clean) |
| Aspect ratio | 1.3-1.6 | 1.48 | **MATCHED** |
| Mounting | 4 × M3 corners, ≥3 mm inset | 4 × M3 at 3.0 mm inset | **MATCHED** |
| Layer count | 6 (DECISIONS §8) | 6 | **MATCHED** |
| 4-zone separation visibly realized | yes | yes (see render) | **MATCHED** |
| Every component placed (83/83 parity) | yes | 83/83 | **MATCHED** |
| Placement-level DRC clean | 0 courtyard/clearance violations | **0 courtyard, 0 placement clearance**; 14 footprint-internal awaiting U3 footprint correction | **MATCHED at placement scope** (footprint correction is a separate workstream — Sai escalation) |

## Footprint swaps applied at placement time

- **U6 TPS25940A**: symbol-side footprint `WQFN-20-1EP_4x3mm_P0.5mm_EP1.7x2.7mm` does not exist in the KiCad 9 standard library. Substituted `Package_DFN_QFN:QFN-20-1EP_3x4mm_P0.5mm_EP1.65x2.65mm` — same physical body, axis-naming convention. Nets wired manually from netlist (20 pads).
- **J10 CRSF**: substituted custom `novapcb_lib:CRSF_solder_pad` (4 SMD pads instead of JST-GH 4P connector) — placed on B.Cu in Zone 3 SE.
- **J11-J18 ESC1-8**: substituted custom `novapcb_lib:ESC_solder_pad` (2 SMD pads each — signal + GND).

## What this PR does NOT do (Step 5 territory)

- Power-plane copper pours (L2 GND, L3 +3V3, L4 +5V, L5 GND)
- Trace routing (signal + power)
- LDO thermal pour copper area (Step 5 places on L4 +5V; Step 4 iterates the size)
- Final via-stack patterns
- Edge cuts beyond the simple rectangle
- U3 IMU footprint correction (Sai escalation per OPEN_QUESTIONS phase4a-1)

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

- Step 3 P1 placement: **DONE** (strategy-faithful, board grown to clear all zone-boundary tensions).
- DRC residuals: 14, all footprint-internal on U3 IMU; flagged in OPEN_QUESTIONS phase4a-1 for Sai escalation.
- Step 4 (sim-validate): can dispatch on this PR as it provides a geometrically valid placement (no pads overlap; no courtyards overlap; only the IMU's own internal pad geometry is wrong, which doesn't impede sim work since Elmer-FEM thermal + OpenEMS sims use net-level and footprint-level geometry, not individual sub-pitch pad gaps).
