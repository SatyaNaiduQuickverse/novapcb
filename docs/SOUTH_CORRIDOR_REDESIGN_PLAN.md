# South Corridor Full Redesign Plan (T3)

> **Status**: DRAFT for master sign-off (Sai picked T3 2026-05-24).
> NO LAYOUT TOUCH until sign-off.
> **Branch**: `hw/south-corridor-redesign` off sch/option-b-buck head 482acd3.
> **Trigger**: H↔C 7 escalations + Sai rejection of (κ) defer:
> "bro without motors there is no FC."
> **Goal**: open Y=43..51 corridor for MOT3-6 fanout while preserving
> all existing function.

---

## 1. Corridor inventory (verified via pcbnew)

### Nets with segments in Y=43..51 X=37..56 (8 nets + GND vias)

| Net | F.Cu segs | B.Cu segs | Vias | Source PR |
|---|---:|---:|---:|---|
| +3V3 | 3 | 0 | 8 | PR #76 (MCU decap stubs + plane vias) |
| I²C2_SCL | 7 | 1 | 2 | PR #73 (MCU PB10 → U4 BARO) |
| I²C2_SDA | 8 | 1 | 2 | PR #73 |
| IMU2_ACC_INT1 | 0 | 3 | 0 | PR #77 (B.Cu only — already non-conflicting w/ F.Cu MOT) |
| SPI1_MISO | 3 | 0 | 0 | PR #77 (MCU PA6 → IMU1) |
| SPI1_MOSI | 9 | 2 | 1 | PR #77 (MCU PA7 → IMU1) |
| SPI1_SCK | 5 | 0 | 0 | PR #77 (MCU PA5 → IMU1) |
| SPI3_MOSI | 0 | 5 | 0 | PR #77 (B.Cu wraparound — already non-conflicting) |
| GND | — | — | 3 | stitching vias |

### Anchor components in corridor (CANNOT MOVE — they're E-subsystem placements)

| Ref | Position | Function |
|---|---|---|
| U4 BARO | (43.5, 47.5) | I²C2 endpoint (DPS310) |
| U7 LPS22HB | (55, 47) | I²C1 sensor |
| R11 (4.7k pull) | (52.5, 46.5) | I²C2_SDA pull-up |
| R12 (4.7k pull) | (46.5, 46.5) | I²C2_SCL pull-up |
| C12, C13, C17, C51, C52, C72 | Y=44.95-49 various X | MCU/sensor decap |

**R11/R12 CAN MOVE** (passive pulls), as established in H↔C 5th escalation
(η path explored).

### New nets needing this corridor

- **MOT3-6** F.Cu south fanout from MCU pads (45.5, 46.5, 47.5, 48 at Y=42.67) → J11.3-6 at Y=78
- **MOT7-8** N-edge layer-split (not in this corridor)
- **IMU3_INT1** PE11→PB2 short F.Cu (new pin per PR #83)
- **J11.10 GND stitching via** (not in this corridor)

## 2. Lane allocation strategy

### Constraint: U4 BARO + I²C2 traces are F.Cu-mandated (U4 pads on F.Cu)

Cannot move I²C2 to B.Cu fully — U4 pads at Y=47.8 are F.Cu surface
mounts. Last few mm to U4 must be F.Cu.

### Layer-split strategy

**F.Cu retains**:
- MOT1-6 fanout (4 new + MOT1+2 existing south-edge):
  - MOT1 PB0 X=43 → J11.1
  - MOT2 PB1 X=43.5 → J11.2
  - MOT3 PE9 X=45.5 → J11.3
  - MOT4 PE11 X=46.5 → J11.4
  - MOT5 PE13 X=47.5 → J11.5
  - MOT6 PE14 X=48 → J11.6
- I²C2 last 3-5mm to U4 BARO (mandated, but body of trace can be B.Cu)
- IMU3_INT1 short F.Cu stub from PB2 pad 36 (44, 42.67) before via to B.Cu
- +3V3 stubs (NOT relocatable — body decap)

**B.Cu (drop existing F.Cu)**:
- SPI1 SCK/MISO/MOSI: high-speed signals, B.Cu over In4.Cu GND is
  electrically equivalent to F.Cu over In1.Cu GND — same Z0, same SI.
- IMU1_CS, IMU2_GYR_CS, IMU3_CS: slow GPIO chip-selects, B.Cu fine.
- I²C2 SCL/SDA body of trace: B.Cu via to F.Cu just before U4.

**B.Cu retains**:
- SPI3_MOSI wraparound (PR #77) — unchanged
- IMU2_ACC_INT1 (PR #77) — unchanged

### Move R11/R12 pulls

- R11 (52.5, 46.5) → (52.5, 49.5) — south of D-zone north line Y=51 conflict
- R12 (46.5, 46.5) → (46.5, 49.5) — south to clear MOT4 column X=46.5

I²C2_SCL re-route to new R12 position; I²C2_SDA to new R11.

### Resulting lane allocation in Y=43..51 corridor

| Lane Y | Layer | Net assignment |
|---|---|---|
| Y=43.5 | F.Cu | MOT3 + MOT4 + MOT5 + MOT6 horizontal bend if needed |
| Y=44.0 | F.Cu | (MOT north pad transitions) |
| Y=44.5 | F.Cu | C12/C17/C13 cap row (existing — keep) |
| Y=45.0 | (empty F.Cu after re-route) | available for MOT bends |
| Y=45.5 | (empty F.Cu after re-route) | available |
| Y=46.5 | F.Cu | R11/R12 OLD positions (vacated after move) |
| Y=47.0 | F.Cu | U7 north pads (keep) |
| Y=47.5 | F.Cu | U4 BARO pads (keep) |
| Y=48.0-48.5 | F.Cu | I²C2 last-leg to U4 (B.Cu→F.Cu via in this region) |
| Y=49.0 | F.Cu | C52/C72 cap row (existing — keep) + R11/R12 new positions |
| Y=49.5-50.5 | (mostly empty) | MOT3-6 south-sweep transitions |
| Y=50.5-51 | F.Cu | D-zone north margin |

**B.Cu lane allocation Y=43..51 corridor**:
- IMU1_CS, IMU2_GYR_CS, IMU3_CS — 3 perimeter routes from MCU N/W pads
  to IMU island, taking SE diagonal paths
- SPI1_SCK, MISO, MOSI — south fan from MCU S pads (X=40.5-41.5)
  to IMU1 SPI bus
- Existing SPI3_MOSI + IMU2_ACC_INT1 — unchanged

## 3. Per-net redesign plan (rough — refined at execution)

| Net | Old layer | New layer | New path summary |
|---|---|---|---|
| MOT1 | (new) | F.Cu | South sweep + east bend → J11.1 |
| MOT2 | (new) | F.Cu | Same pattern, slightly east |
| MOT3 | (new) | F.Cu | Pad 39 (X=45.5) → south → east → J11.3 |
| MOT4 | (new) | F.Cu | Pad 41 (X=46.5) → south past now-moved R12 → J11.4 |
| MOT5 | (new) | F.Cu | Pad 43 (X=47.5) → south → J11.5 |
| MOT6 | (new) | F.Cu | Pad 44 (X=48) → south → J11.6 |
| MOT7 | (new) | F.Cu→B.Cu→F.Cu | N edge layer-split (not in corridor) |
| MOT8 | (new) | F.Cu→B.Cu→F.Cu | N edge layer-split (not in corridor) |
| IMU3_INT1 | (new) | F.Cu→B.Cu→F.Cu | PB2→via→B.Cu SE→via→U9 |
| SPI1_SCK | F.Cu (corridor) | B.Cu (corridor) | South via, B.Cu to IMU1 |
| SPI1_MISO | F.Cu | B.Cu | Same |
| SPI1_MOSI | F.Cu | B.Cu | Same |
| IMU1_CS | F.Cu diagonal | B.Cu diagonal | South via from PC15, B.Cu SE to IMU1 |
| IMU2_GYR_CS | B.Cu (already) | B.Cu (re-routed to free lanes) | Adjust path |
| IMU3_CS | F.Cu diagonal | B.Cu | Drop to B.Cu, route to U9 in D-zone |
| I²C2_SCL | F.Cu corridor | F.Cu (mostly) + short B.Cu link | New R12 position south; F.Cu to U4 |
| I²C2_SDA | F.Cu | F.Cu (mostly) + short B.Cu link | New R11 position south |
| IMU2_ACC_INT1 | B.Cu | B.Cu | KEEP unchanged |
| SPI3_MOSI | B.Cu | B.Cu | KEEP unchanged |

## 4. Cluster walk plan

Per Rule 9: every F.Cu segment overlies In1.Cu GND (continuous full-board
post PR #76); every B.Cu segment overlies In4.Cu GND (continuous full-board
post PR #76).

**Risk areas requiring per-net walk**:
- B.Cu IMU CS new routes — verify In4.Cu GND coverage along entire path
- B.Cu SPI1 new routes — same
- F.Cu I²C2 short last-leg — verify In1.Cu GND below

## 5. Decisions for sign-off

1. **Layer-split scope**: 5 nets drop to B.Cu (SPI1 × 3 + IMU CS × 3 → 6
   nets actually). Confirm.
2. **R11/R12 move to Y=49.5**: confirm direction (south vs east)
3. **I²C2 split topology**: F.Cu→B.Cu→F.Cu via stub at U4 vs all F.Cu
   with re-routing. Recommend split for cleaner corridor.
4. **IMU3_INT1 routing**: same B.Cu wraparound pattern as old IMU3_INT1
   route from PR #77, but starting from PB2 pad 36 instead of PE11 pad 41.
5. **MOT1+MOT2 path strategy**: south straight from pads X=43/43.5, slight
   east bend before J11.1/J11.2. Should be cleanest F.Cu path.

## 6. Expected gates after T3

- DRC: ≤ baseline +5 (corridor full redesign produces transient errors;
  resolve before commit)
- STACKUP-SPEC-MATCH: PASS
- MIRROR_PAIRS 11/11: A zone untouched
- DECOUPLING: unchanged
- **Unconnected: -10** (8 MOT + 1 IMU3_INT1 + 1 GND stitch closed)
- **Per-net cluster walk**: every redesigned net has documented GND
  reference + path

## 7. Execution plan (post-sign-off)

**Step A**: `clear_south_corridor.py` removes ALL existing tracks/vias
on the 8 corridor nets (preserving GND vias).

**Step B**: Move R11/R12 to (52.5/46.5, 49.5).

**Step C**: Add new routes per per-net plan above, working in
sub-batches:
  - C.1 SPI1 (3 nets) re-route on B.Cu
  - C.2 IMU CS (3 nets) re-route on B.Cu
  - C.3 I²C2 (2 nets) re-route F.Cu + short B.Cu detour
  - C.4 MOT3-6 (4 nets) F.Cu south fanout in cleared corridor
  - C.5 MOT1-2 F.Cu south fanout
  - C.6 MOT7-8 N-edge layer-split
  - C.7 IMU3_INT1 PB2 re-route
  - C.8 J11.10 GND stitching via

**Step D**: Refill zones, DRC, audit, render.

**Step E**: 4-section PR doc + per-net cluster walk + Rule 9 verify
for every redesigned net.

---

**Awaiting master sign-off on §5 decisions before execution.**
