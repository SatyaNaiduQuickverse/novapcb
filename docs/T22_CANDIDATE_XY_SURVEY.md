# T22 / T21 candidate XY survey (master 2026-06-01)

> Parsed 133 footprint positions from novapcb-stepwise.kicad_pcb.

## Key fixed component positions

| Ref | X (mm) | Y (mm) |
|---|---|---|
| J1 | 83.8 | 30.0 |
| J10 | 54.0 | 8.0 |
| J11 | 52.5 | 80.0 |
| J19 | 89.0 | 5.0 |
| J2 | 95.0 | 67.0 |
| J20 | 97.0 | 11.0 |
| J3 | 95.0 | 38.0 |
| J4 | 16.0 | 5.0 |
| J5 | 15.0 | 75.0 |
| J9 | 15.0 | 35.0 |
| U1 | 45.0 | 35.0 |
| U11 | 33.0 | 5.0 |
| U12 | 72.0 | 5.0 |
| U13 | 60.0 | 26.0 |
| U2 | 24.0 | 25.0 |
| U6 | 28.0 | 18.0 |

## Clear grid cells (≥5mm from any footprint)

Found 165 clear cells (5x5 mm grid, ≥5mm from any footprint).

Top 20 most-clear cells:

| X | Y | Clear radius (mm) |
|---|---|---|
| 70 | 80 | 17.5 |
| 70 | 75 | 15.2 |
| 75 | 80 | 14.9 |
| 45 | 65 | 14.4 |
| 40 | 65 | 14.3 |
| 5 | 45 | 14.1 |
| 65 | 75 | 13.5 |
| 40 | 75 | 13.2 |
| 35 | 60 | 13.0 |
| 40 | 70 | 13.0 |
| 5 | 50 | 13.0 |
| 40 | 80 | 12.5 |
| 45 | 70 | 12.5 |
| 65 | 80 | 12.5 |
| 25 | 50 | 12.4 |
| 75 | 75 | 12.1 |
| 15 | 50 | 12.0 |
| 20 | 50 | 12.0 |
| 10 | 50 | 12.0 |
| 5 | 15 | 11.9 |

## T22.4 J11 re-place candidates

Current: (52.5, 80.0). Goal: shift to free S edge for TVS placement.

| XY | Δ from current | Clear radius |
|---|---|---|
| (45, 65) | (-7.5, -15.0) | 14.4mm |
| (40, 65) | (-12.5, -15.0) | 14.3mm |
| (65, 75) | (+12.5, -5.0) | 13.5mm |
| (40, 75) | (-12.5, -5.0) | 13.2mm |
| (40, 70) | (-12.5, -10.0) | 13.0mm |
| (45, 70) | (-7.5, -10.0) | 12.5mm |
| (40, 60) | (-12.5, -20.0) | 11.4mm |
| (45, 60) | (-7.5, -20.0) | 11.2mm |
| (50, 65) | (-2.5, -15.0) | 10.6mm |
| (60, 70) | (+7.5, -10.0) | 10.5mm |

## T22.5 J2 re-place candidates

Current: (95.0, 67.0). Goal: small Δ to open ESD/SDMMC1 corridor.

| XY | Δ from current | Clear radius |
|---|---|---|
| (90, 80) | (-5.0, +13.0) | 10.8mm |
| (85, 80) | (-10.0, +13.0) | 10.0mm |
| (95, 75) | (+0.0, +8.0) | 8.0mm |
| (95, 55) | (+0.0, -12.0) | 7.8mm |
| (90, 55) | (-5.0, -12.0) | 7.2mm |
| (95, 80) | (+0.0, +13.0) | 7.0mm |
| (90, 75) | (-5.0, +8.0) | 6.4mm |
| (85, 75) | (-10.0, +8.0) | 5.1mm |

## T21 J9 re-place candidates near MCU SW

U1 MCU center: (45.0, 35.0). J9 needs <20mm from MCU SW for short SWD route.

| XY | Dist from MCU | Clear radius |
|---|---|---|
| (30, 45) | 18.0mm | 5.4mm |
| (25, 35) | 20.0mm | 6.6mm |
| (25, 40) | 20.6mm | 7.5mm |
| (25, 45) | 22.4mm | 9.6mm |
| (20, 35) | 25.0mm | 5.0mm |
| (20, 40) | 25.5mm | 7.1mm |
| (20, 45) | 26.9mm | 11.2mm |
