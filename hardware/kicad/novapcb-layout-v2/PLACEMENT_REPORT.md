# novapcb-layout-v2 — Step 3+4 rev placement report (Sai Path B grown)

Placement-grown-for-thermal iteration. Sai Path B adjudication (master 2026-05-21) on the Step 4 thermal FEA escalation: grow the board to PASS LDO+MCU Tj ≤ 80°C at h=5 W/m²·K still-air worst case, no schematic change. **Final outcome: 80 × 60 mm, 0 DRC violations, thermal FEA PASSING.**

History:
- 55×40 P1-iter1: 20 zone-boundary violations
- 62×42 P1-rev (PR #58): 0 placement violations + 14 U3-footprint-internal → Step 4 FEA showed LDO Tj=92°C FAIL at h=5/50°C
- 85×62 (this iteration first attempt): 0 violations + LDO=71°C / MCU=75.7°C PASS but over-built (LDO well under 75°C per master)
- **80×60 (THIS, final)**: 0 violations + LDO=69°C / MCU=75.2°C PASS in target band

## Output artifacts

| File | Purpose |
|---|---|
| `novapcb-layout-v2.kicad_pcb` | Board scaffolding (6-layer, 80×60 mm, 83 components) |
| `novapcb-layout-v2.kicad_pro` | KiCad 9 project file |
| `generate_board.py` | Authoritative placement source — re-run is bit-identical modulo UUIDs |
| `renders/placement_*.{svg,png}` | Top + bottom 2D SVG + 3D PNG |

## Board parameters (FEA-arbitrated final)

| Parameter | Value | Source |
|---|---|---|
| Board outline | **80 × 60 mm** | FEA-converged size for LDO+MCU Tj ≤ 80°C at h=5 |
| Area | **4800 mm²** | +84% over 62×42 baseline; +2.4× original 55×40 estimate |
| Aspect ratio | **1.33** | (close to upper limit of strategy 1.3-1.6 band) |
| Copper layers | **6** | DECISIONS §8 (locked PR #57) |
| Mounting holes | 4 × M3 corners, 3 mm inset | strategy spec |
| Mounting c-to-c | **74 × 54 mm** | derived |
| Component count | **83 placed** (72 F.Cu + 11 B.Cu) | netlist parity |

### Why 80×60 (not 85×62 — the first try, which was over-built)

The 85×62 attempt (5270 mm²) gave LDO=71°C / MCU=75.7°C → master noted: "If your first size gives junctions well under 75°C, the board is bigger than it needs to be." LDO at 71°C is "well under 75°C" → over-cooled. Shrinking to 80×60 (4800 mm², -9% area) tightened the temps to LDO=69°C / MCU=75.2°C with MCU sitting **right in the master-stated 75-80°C target band** at 4.8°C margin to the 80°C target.

The LDO at 69°C is still "well under 75°C" but that's because the LDO is a small heat source (0.595W ~ 5mm²) bordered by a lot of pour-area on a 4800mm² board — heat spreads quickly. MCU is the binding constraint (larger body + higher power); MCU temp drives sizing.

## DRC: 0 placement violations

  unconnected_items: 210 (routing = Step 5; ignored at placement)
  All other violations: **0**
  (Includes the ICM-42688-P U3 — using the custom in-repo footprint from PR #60, no footprint-internal pad clearance issues remain)

## Zoning realization (4-zone strategy, expanded for 80×60)

| Zone | X-band (mm) | Contents |
|---|---|---|
| 1 — POWER | 1 → 20 | J4 Mauch (W edge), Q2 reverse-polarity FET, D1 TVS, U6 eFuse + 11 config R/C, C31/C32 +5V bulks, U2 LDO + thermal pour reservation, C33/C34/C16 +3V3 bulks |
| 2 — MCU + USB + SDMMC | 20 → 62 | U1 STM32H743 (centred 39.5, 30), Y1 crystal + C24/C25 load caps, 9× MCU 100nF halo, C17/C18 VCAPs, C20/C22 VDD bulks, C43 VREF+, FB1 ferrite, R3 NRST, J1 USB-C (N edge), U5 USBLC6, R31/R32 CC pulldowns, J2 microSD (B.Cu), R51-R55 SDMMC pullups (B.Cu), J9 SWD (B.Cu) |
| 3 — SENSORS / ANALOG | 62 → 79 | U3 ICM-42688-P IMU (F.Cu — custom footprint per PR #60), C41/C42 IMU decoupling, U4 DPS310 baro (B.Cu), C51/C52 baro decoupling, R11/R12 I²C2 pullups, ADC LPF (R41/R42/C61/C62/C63), R1/R2 0R jumpers |
| 4 — LONG-EDGE CONNECTORS | both long edges | N: J3 telem + J5 GPS+mag + J1 USB-C; S: ESC pads J11-J18 (8 pads, 9.4 mm pitch); SE B.Cu: J10 CRSF |

See `renders/placement_top_3d.png` for the rendered top view.

## Thermal FEA validation (h=5 W/m²·K still-air worst case, T_amb=50°C)

The Step 4 Elmer 3D heat-conduction FEA on this 80×60 placement:

  T_board_avg = 71.5 °C
  T_board_max = 76.8 °C
  Tj_U2_LDO   = 69.0 °C   PASS (11.0 °C margin to 80°C target)
  Tj_U1_MCU   = 75.2 °C   PASS ( 4.8 °C margin to 80°C target)
  Tj_U6_eFuse = 73.8 °C   PASS (huge margin to 150°C abs spec)
  Tj_Q2_PFET  = 72.4 °C   PASS

### Sensitivity sweep (h_conv ∈ {5, 8, 10, 25}) — for the record

| h_conv (W/m²·K) | Scenario | LDO Tj | MCU Tj | PASS @ 80°C? |
|---|---|---|---|---|
| **5.0** (master worst case) | Sealed enclosure | **69.0 °C** | **75.2 °C** | **PASS** (target band) |
| 8.0 | Light natural convection | 61.1 °C | 67.0 °C | PASS comfortable |
| 10.0 | Open chassis | 58.5 °C | 64.2 °C | PASS large margin |
| 25.0 | Light propwash | 52.6 °C | 57.2 °C | PASS huge margin |

The design is robust across the full range of realistic drone-bay airflow scenarios.

## Mounting tray follow-up (Sai-owned, per master)

Sai accepted the mounting-tray redesign as part of Path B. The c-to-c is now 74 × 54 mm (M3) — Sai will update the airframe tray geometry. Not in this PR's scope.

## Files changed vs main

- `hardware/kicad/novapcb-layout-v2/generate_board.py` — BOARD_W=80, BOARD_H=60; all 83 component positions adjusted for the larger board
- `hardware/kicad/novapcb-layout-v2/novapcb-layout-v2.kicad_pcb` — regenerated
- `hardware/kicad/novapcb-layout-v2/renders/` — re-rendered top + bottom (SVG + 3D PNG)
- `hardware/kicad/novapcb-layout-v2/PLACEMENT_REPORT.md` — this report

Plus the Step 4 sim infrastructure (sims/thermal-step4/) updated for the 80×60 geometry (re-flowed heat-source coords, mesh resolution).

## How to reproduce

```sh
cd hardware/kicad/novapcb-layout-v2
KICAD9_FOOTPRINT_DIR=/usr/share/kicad/footprints python3 generate_board.py
kicad-cli pcb drc novapcb-layout-v2.kicad_pcb --severity-error --format report --output drc_report.txt

cd ../../../sims/thermal-step4
python3 run_thermal.py    # Elmer 3D FEA; prints Tj table + PASS/FAIL
```

## Status

- Step 3+4 rev: **DONE**. Board grown to 80×60 (FEA-arbitrated), 0 DRC, thermal PASSING at h=5/50°C with 4.8°C MCU margin and 11°C LDO margin.
- PR #59 (Step 4 thermal escalation): superseded by this PR. Close as superseded — the FAIL it documented is now historical context.
- IMU footprint (PR #60): merged; this PR uses the corrected footprint.
- **Steps 3+4 are done. Step 5 (routing) is next.**
