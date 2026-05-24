# H↔C Corridor-Clear Survey (Y=44..48 X=37..56)

> **Status**: DRAFT for master sign-off (autonomous mode 2026-05-24).
> NO LAYOUT TOUCH yet.
> **Trigger**: H↔C MOT* routing 3rd Freerouting attempt failed on
> existing-route obstacles. Master 2026-05-24 selected (α) corridor-clear
> over (γ) DRU exceptions / (δ) cluster manual.
> **Branch**: `hw/h-c-routing-corridor-clear` (to be created off
> sch/option-b-buck head b842db8 after sign-off).

---

## 1. Survey — obstacles in MCU south fanout corridor

Corridor: **X=37..56, Y=44..48** (4mm tall band south of MCU south edge
Y=42.67, where MOT3-6 fanout from new pins PE9/PE11/PE13/PE14 needs
to traverse).

### F.Cu segments crossing corridor

| Net | Segment | Source PR |
|---|---|---|
| +3V3 | (52.60, 42.67) → (52.60, 45.00) — short stub to body decap | PR #70-#73 C-zone |
| +3V3 | (39.50, 43.48) → (39.02, 44.95) — short stub to body decap via | PR #70-#73 C-zone |
| **I2C2_SCL** | 6 F.Cu segments — east bend Y=45.5..47.8 + diagonals | PR #73 C↔E I2C2 routing |
| **I2C2_SDA** | 6 F.Cu segments — Y=47.3..48.3 + short connectors | PR #73 |
| SPI1_MISO | (41.00, 47.31) → (41.00, 42.67) + diagonal to (43.70, 50.01) | PR #77 D↔C/B |
| **SPI1_MOSI** | 6 F.Cu segments — Y=45.78 horizontal + diagonals at Y=44.45 | PR #77 D↔C/B |
| **SPI1_SCK** | 4 F.Cu segments — Y=44.54..47.50 vertical column at X=40.50/40.56 | PR #77 |

### B.Cu segments crossing corridor

| Net | Segment | Source PR |
|---|---|---|
| I2C2_SCL | (47.00, 44.00) → (47.50, 46.50) — vertical short via stub | PR #73 |
| I2C2_SDA | (52.00, 44.00) → (52.00, 47.30) — vertical via stub | PR #73 |
| **IMU2_ACC_INT1** | 3 B.Cu segments — long diagonals through corridor | PR #77 |
| SPI3_MOSI | 3 B.Cu segments — diagonals (48.89, 44.99)→(48.89, 44.42)→(44.06, 39.59) | PR #77 D↔C/B wraparound |

### Per-net layer summary

| Net | F.Cu segments | B.Cu segments | Action proposed |
|---|---:|---:|---|
| +3V3 | 2 | 0 | KEEP (short body-decap stubs; not relocatable) |
| I2C2_SCL | 6 | 1 | **RELOCATE** — south to Y=50+ or different layer |
| I2C2_SDA | 6 | 1 | **RELOCATE** — south to Y=50+ or different layer |
| SPI1_MISO | 2 | 0 | RELOCATE-MINIMAL — shift east by 2mm |
| SPI1_MOSI | 6 | 0 | **RELOCATE** — major source of corridor density |
| SPI1_SCK | 4 | 0 | RELOCATE-MINIMAL — shift west to X=39 |
| IMU2_ACC_INT1 | 0 | 3 | KEEP (B.Cu only; MOT3-6 F.Cu fanout doesn't conflict with B.Cu existing routes) |
| SPI3_MOSI | 0 | 3 | KEEP (B.Cu only; same reason) |

## 2. Per-net re-route plan

### I2C2_SCL + I2C2_SDA — south detour around D-zone north

**Current**: I2C2 routes MCU PB10/PB11 (pads 46/47 S at X=49/49.5) →
U10 baro at (89, 22) — east-going across X=44..67 in Y=44..48 band.

**Proposal**: re-route via Y=50+ (south of D-zone north edge Y=51).
Specifically:
- I2C2_SCL/SDA exit MCU S at Y=42.67, go south to Y=51 (clear of D-zone),
  then east through bridge column X=64..68 between A-power south and D-zone,
  then NE to U10 baro
- ~5mm net longer path but clears corridor

**Layer**: F.Cu (consistent with existing layer).

**Risk**: I2C2 is slow signal (≤400 kHz), no SI concern with extra length.

### SPI1_MOSI + SPI1_MISO + SPI1_SCK — minor shifts

**Current**: SPI1 SCK PA5 (pad 29), MISO PA6 (pad 30), MOSI PA7 (pad 31)
— south MCU pads at X=40.5..41.5 going north-south then east to IMU1.

**Proposal**:
- SPI1_SCK at X=40.56 → shift west to X=39.0 (clears MOT1 fanout column at
  X=42-43)
- SPI1_MISO at X=41.00 → shift west to X=39.5
- SPI1_MOSI horizontal at Y=45.78 → shift south to Y=49 (clears MOT3-6
  fanout south sweep that would cross Y=45.78)

**Layer**: F.Cu (consistent).

**Risk**: SPI1 is high-speed (up to 50MHz to ICM-42688). Longer path
adds inductance but ±2mm shift is within SI margin (~10 ohm reactance
@ 50MHz; trivial).

## 3. Existing routes that DON'T need to move

- **+3V3 stubs** (2 short segments): tied to body decap, can't move
- **IMU2_ACC_INT1 B.Cu** (3 segments): on B.Cu; MOT3-6 F.Cu fanout
  doesn't conflict with B.Cu (different layer). MOT7-8 B.Cu south leg
  may need to avoid this — verify at MOT routing.
- **SPI3_MOSI B.Cu wraparound** (3 segments): same logic. KEEP.

## 4. After-corridor-clear: route MOT* in cleared space

After re-routes above land:
- F.Cu Y=44..48 X=37..56 nearly EMPTY (only the 2 short +3V3 stubs)
- **MOT3-6 F.Cu fanout** from S pads (X=45.5..48 Y=42.67) south through
  cleared Y=44..48 to J11.3-6 — straight south sweeps, no obstacles
- **MOT7-8** N-edge pads (PB8/PB9) → via → B.Cu south past MCU body →
  via → F.Cu to J11.7-8
- **IMU3_INT1** PE11→PB2 — short F.Cu from MCU pad 36 (S, X=44) to
  U9 IMU3 sensor in D-zone
- **J11.10 GND stitching via** at (59.0, 78.5) + 1mm F.Cu stub

## 5. Expected gates after full sub-step

- DRC: ≤ baseline +3 (corridor re-routes may briefly disturb 1-3 errors;
  resolve before commit)
- STACKUP-SPEC-MATCH: PASS
- MIRROR_PAIRS: unchanged (none affected)
- DECOUPLING: unchanged (no new ICs)
- **Unconnected: −10** (closes 8 MOT + 1 IMU3_INT1 + 1 GND stitch)
- Per-net cluster walk (Rule 9): each MOT* + IMU3_INT1 + each moved
  I2C2/SPI1 net over In1 GND (F.Cu) / In4 GND (B.Cu)
- **NEW: corridor-clear regression test**: re-run cluster walk for
  PR #73 (I2C2) + PR #77 (SPI1) moved nets — confirm no regression

## 6. Decisions for sign-off

1. **Detour direction for I2C2** — south of D-zone (recommend, ≥3mm
   clear) vs other layer (B.Cu would conflict with existing IMU2_ACC_INT1
   B.Cu in corridor)
2. **SPI1 shift magnitude** — 2mm west for SCK/MISO + ~3mm south for
   MOSI horizontal (recommend conservative shift)
3. **Acceptance of moved I2C2 latency** — adds ~5mm path → ~80ps at 0.5C
   FR4. At 400 kHz I²C bit time 2.5µs, negligible (~0.003%).
4. **Acceptance of SPI1 SI delta** — moved SPI1_MOSI Y=45.78→Y=49 adds
   ~3mm; reactance ~0.6 nH; at 50MHz ω=314e6 rad/s, Z=0.19 Ω. Negligible.

## 7. Execution plan (post-sign-off)

**Step 1: corridor clear**
- Custom script `clear_corridor.py` removes the listed F.Cu segments
- New segments added per re-route plan above
- Cluster walk + DRC verify after each net's re-route

**Step 2: route MOT***
- Existing `route_pin_remap.py` style — manual placement of MOT3-6 + MOT7-8
  + IMU3_INT1 + J11.10 GND stitch
- DRC verify

**Step 3: full audit + PR**
- 5-gate verify + per-net cluster walk
- 4-section PR doc + Rule 19 demonstration (which existing routes moved)

---

**Awaiting master sign-off on §6 decisions before corridor-clear execution.**
