# MOT* Fanout Column — Actual Obstacle Survey

> **Status**: SURVEY for master sign-off (T3 focused approach).
> NO LAYOUT TOUCH.
> **Branch**: hw/t3-focused-survey.
> **Goal**: distinguish nets that ACTUALLY cross MOT3-6 / MOT7-8 columns
> from those that merely live in the same Y band.

---

## Columns surveyed

- **MOT3-6 F.Cu fanout column**: X=45.0..48.5, Y=43..78
  (MCU south pads at X=45.5/46.5/47.5/48.0 → J11.3-6 at Y=78)
- **MOT7-8 B.Cu N-edge column**: X=37.5..42.0, Y=27..78
  (N-edge MCU pads PB8/PB9 at X=41/41.5 → via → B.Cu south → J11.7/8)

## MOT3-6 column — actual blockers

### F.Cu blockers (CROSS the column)

| Net | Crossing | Type |
|---|---|---|
| **R12** pads | R12.1 (45.49, 46.5) +3V3, R12.2 (46.51, 46.5) I²C2_SCL | COMPONENT PADS — hard block on MOT3+MOT4 columns |
| **C51** pads | C51.1 (46.48, 47.5) +3V3, C51.2 (45.52, 47.5) GND | COMPONENT PADS — block MOT3+MOT4 |
| **I²C2_SCL** | 4 F.Cu segs around R12 area | tied to R12 — moves with R12 |
| **I²C2_SDA** | (52.51, 48.30)→(43.33, 48.30) horizontal | CROSSES ALL MOT3-6 columns at Y=48.3 |
| **SPI1_MOSI** | (52.73, 45.78)→(47.72, 45.78), (46.40, 44.45)→(42.35, 44.45) | crosses MOT3-6 at Y=44.45 + Y=45.78 |
| **SPI1_SCK** | (43.48, 50.41)→(56.70, 50.41) horizontal | CROSSES ALL MOT3-6 at Y=50.41 |
| **SPI1_MISO** | (59.17, 50.01)→(43.70, 50.01) horizontal | CROSSES ALL MOT3-6 at Y=50.01 |
| **IMU1_CS** | (46.40, 55.18)→(31.29, 40.07) + (58.48, 55.18)→(46.40, 55.18) | diagonal crosses at X=46.40 Y=55 |
| **IMU3_CS** | (30.89, 41.67)→(50.78, 61.56) | diagonal — crosses at (40.83, 51.62) — actually X=40.83 is OUTSIDE MOT3-6 column X=45.5-48.5 (border miss) |
| **IMU2_GYR_INT3** | (42.90, 31.58)→(50.99, 31.58) at Y=31.58 | only at Y=31.58 — NORTH of MOT pads at Y=42.67 — NOT IN PATH |

### B.Cu items in column (NO F.Cu conflict)

| Net | Status |
|---|---|
| IMU2_ACC_INT1 | B.Cu — MOT3-6 are F.Cu → DIFFERENT LAYER, NO CONFLICT |
| SPI3_MOSI | B.Cu — same — NO CONFLICT for F.Cu fanout |

### +3V3 vias in column

- (45.49, 46.5) +3V3 — at R12.1 pad position
- (46.48, 47.5) +3V3 — at C51 pad position
- I²C2_SCL via at (47.0, 44) + (47.5, 46.5) — tied to R12, moves with it

### Component pads in column (HARD blocks)

- **R12.1 / R12.2** at Y=46.5, X=45.49/46.51 — blocks MOT3 (X=45.5) + MOT4 (X=46.5)
- **C51.1 / C51.2** at Y=47.5, X=45.52/46.48 — blocks MOT3 + MOT4

## ACTUAL F.Cu blocker list (filtered) — 7 items

| # | Blocker | Required action |
|---|---|---|
| 1 | R12 (+3V3 + I²C2_SCL pad cluster) | MOVE to clear column (e.g., (41, 49.5)) |
| 2 | C51 (+3V3 + GND decap) | MOVE west of MOT3 column (e.g., (44, 47.5)) |
| 3 | I²C2_SDA Y=48.3 horizontal | RE-ROUTE: split F.Cu→B.Cu→F.Cu or move U-path |
| 4 | SPI1_MOSI 2 F.Cu segs at Y=44.45 + Y=45.78 | RE-ROUTE: shift Y or layer-split |
| 5 | SPI1_SCK Y=50.41 horizontal | RE-ROUTE: shift Y or layer-split |
| 6 | SPI1_MISO Y=50.01 horizontal | RE-ROUTE: shift Y or layer-split |
| 7 | IMU1_CS diagonal | RE-ROUTE (layer-split, perimeter, or shift X) |

**4 nets that do NOT need re-route** (originally feared but not actual blockers):
- IMU2_GYR_INT3 — at Y=31.58 only (far north of fanout)
- IMU3_CS — diagonal crosses at X=40.83, OUTSIDE MOT3-6 column X=45.5..48.5
- IMU2_ACC_INT1 — B.Cu only, different layer
- SPI3_MOSI — B.Cu only

## MOT7-8 N-edge column — actual blockers

### B.Cu items in column X=37.5..42 Y=27..78

| Net | Status |
|---|---|
| BATT_VOLTAGE_SENS | 1 B.Cu segment — single line |

### Vias in column

- +3V3 @ (39.02, 44.95)
- BATT_VOLTAGE_SENS @ (41.62, 36.11)
- 5× GND stitching vias

**MOT7-8 corridor is MOSTLY EMPTY.** Single B.Cu trace + 7 vias to dodge.

**Result: MOT7-8 layer-split N→S B.Cu traversal is feasible with minimal obstacles.**

## Summary

**MOT3-6 needs 7 corridor cleanups + 1 IMU3_CS scope-check** (border crossing — may be OK).
**MOT7-8 needs almost nothing — corridor essentially clear.**

## Decisions for sign-off

### MOT3-6 corridor cleanup plan

1. **Move R12** (currently 46.51, 46.5) to (41, 49.5) — west of MOT1+2 columns
2. **Move C51** (currently 46.48, 47.5) to (44, 49.5) — clear MOT3-4 path
3. **Re-route I²C2_SCL** to follow R12 new position (B.Cu split topology recommend)
4. **Re-route I²C2_SDA** to clear Y=48.3 horizontal — option: route west via U4 first, then to R11
5. **Re-route SPI1 SCK/MISO/MOSI** — shift Y bands or drop to B.Cu (B.Cu envelope has D-zone destination via problem — same as 2b)
6. **Re-route IMU1_CS** — drop to B.Cu south-perimeter (per 2b approach) OR keep F.Cu but shift X column

### MOT7-8 + IMU3_INT1 — proceed independently

These don't need MOT3-6 corridor cleanup. Can be a separate sub-PR.

### Recommend: T3 attempt 3 with this scope

- **Sub-attempt 3a**: MOT7-8 + IMU3_INT1 + GND stitch (clean corridor, expect easy)
- **Sub-attempt 3b**: R12 + C51 move + I²C2 re-route (3 components + 2 nets)
- **Sub-attempt 3c**: SPI1 (3 nets) clearing
- **Sub-attempt 3d**: IMU1_CS clearing
- **Sub-attempt 3e**: MOT3-6 fanout (with cleared corridor)

If 2b earlier failure for IMU1_CS B.Cu destination via persists, may need
alternate strategy for SPI1 (3c) + IMU1_CS (3d) — likely SHIFT F.Cu Y
band rather than drop to B.Cu (avoiding the D-zone destination via
problem).

---

**Awaiting master sign-off on 7-item cleanup list + sub-attempt sequence (3a-3e).**
