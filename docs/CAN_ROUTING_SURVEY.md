# CAN Routing — NE Corridor Survey (task #45)

> **Status**: SURVEY for master sign-off. NO LAYOUT TOUCH.
> **Branch**: hw/can-routing-v2 off sch/option-b-buck head 5b1d2b7.

---

## Net endpoints (5 nets)

| Net | MCU pad | Destination |
|---|---|---|
| CAN1_RX | U1.81 PD0 (48.50, 27.32) N edge | U14.4 (94.98, 23.43) |
| CAN1_TX | U1.82 PD1 (48.00, 27.32) N edge | U14.1 (93.02, 23.43) |
| GPIO_CAN1_SILENT | U1.84 PD3 (47.00, 27.32) N edge | U14.8 (93.02, 20.57) |
| CANH_NET | U14.7 (93.68, 20.57) | R45.1 (99.5, 21.82) + U15.1 (97, 27.95) + J20.2 (96.38, 9.15) |
| CANL_NET | U14.6 (94.33, 20.57) | R46.2 (99.5, 24.18) + U15.2 (97, 26.05) + J20.3 (97.62, 9.15) |
| CAN_TERM_MID | R45.2 (99.5, 20.18) ↔ R46.1 (99.5, 25.82) | (intra-pair link) |

3 MCU signals (RX/TX/SILENT) traverse ~46mm from MCU N edge (X=47-48.5)
to U14 (X=93-95). CAN bus (CANH/CANL) + termination are LOCAL to the
NE corner (X=93-99) — short routing.

## Rule 18 + 19 corridor survey (X=48..105 Y=0..30)

### Per-Y-band density (X=48..93 traverse zone)

| Y band | F.Cu crossings | B.Cu crossings | Status |
|---|---:|---:|---|
| Y=2 | 0 | 0 | **CLEAR** (board N edge) |
| Y=5 | 7 | 1 | busy (J20/U12/caps) |
| Y=8 | 9 | 1 | busy |
| Y=12 | 4 | 1 | moderate |
| **Y=16** | **0** | **1** | **NEARLY CLEAR** ✓ |
| **Y=20** | **0** | **1** | **NEARLY CLEAR** ✓ |
| Y=24 | 15 | 0 | busy (MCU N-pad fanout) |

### Key finding

**Y=16 and Y=20 horizontal lanes are nearly clear** (1 B.Cu crossing
each) across the X=48..93 traverse. The MCU N-pad fanout congestion is
at Y=24 (just north of pads at Y=27.32); the power-plane routing
(+5V_BEC_B 33 segs, +3V3_IMU_PRE 30 segs) is mostly at Y=5..12 (NW
corner) and Y=24.

### Existing routes in corridor (Rule 19)

Heavy nets: +5V_BEC_B (33), +3V3_IMU_PRE (30), +3V3_IMU (9),
BATT2_CURRENT_SENS (6), +3V3 (5), MAUCH2/USBC/HEATER/SPI3 (2-4 each).
But these concentrate at Y=5-12 + Y=24, NOT at Y=16-20.

### Component pads in corridor (Rule 18)

- U12 ORFET (70.85-73.15, 4-6) — NW, clear of Y=16-20 lane
- C14 (54.5, 29) — south of corridor
- R44 sense (84-85, 14.5) — at Y=14.5, just south of Y=16 lane — watch clearance
- J20 + R45/R46 + H2 mount — far NE corner

## Proposed routing approach

### 3 MCU signals (RX/TX/SILENT) via Y=16 + Y=20 clear lanes

- **CAN1_TX** U1.82 (48, 27.32) → N to Y=20 → E along Y=20 lane → U14.1 (93.02, 23.43)
- **CAN1_RX** U1.81 (48.5, 27.32) → N to Y=16 → E along Y=16 lane → U14.4 (94.98, 23.43)
- **GPIO_CAN1_SILENT** U1.84 (47, 27.32) → N to Y=18 → E → U14.8 (93.02, 20.57)

N-stubs from MCU pads (Y=27.32 → Y=16-20) cross the Y=24 busy band —
need to thread between MCU N-pad fanout routes at X=47-48.5. Per
focused survey, check exact X=47-48.5 column occupancy at Y=24.

3 lanes at Y=16/18/20 — 2mm spacing, clean.

R44 sense at (84-85, 14.5): Y=16 lane at X=84-85 is 1.5mm north of R44.
Trace at Y=16 vs R44 pad N edge Y~15 → 1mm clear. OK but verify.

### CAN bus (CANH/CANL) — local NE corner

Short routes U14 → R45/R46 → U15 → J20, all within X=93-99 Y=9-28.
CANH/CANL kept as loose pair (no controlled-Z needed at <50mm stub per
master earlier note; ~50-80Ω diff OK).

### Layer

All F.Cu preferred (Y=16-20 lanes are F.Cu-clear). The 1 B.Cu crossing
per lane is on B.Cu — doesn't conflict with F.Cu CAN traces.

## Decisions for sign-off

1. **Traverse lanes**: Y=16 (RX) / Y=18 (SILENT) / Y=20 (TX) horizontal
   F.Cu — recommend (cleanest bands per density survey)
2. **N-stub threading**: MCU pads → north through Y=24 busy band at
   X=47-48.5 — verify column clear at execution; may need 1mm X dodges
3. **CANH/CANL**: loose pair, F.Cu, NE-corner local
4. **Routing method**: manual (5 nets, clean lanes identified) — recommend
   over Freerouting (which OOMed on larger scope last session)

## Gates

- DRC ≤ baseline (18) + 3
- STACKUP-SPEC-MATCH PASS
- MIRROR_PAIRS unchanged
- DECOUPLING unchanged
- Unconnected: −5 (CAN1_RX/TX/SILENT + CANH + CANL close; CAN_TERM_MID intra-pair)
- Per-net cluster walk: F.Cu over In1 GND

---

**Awaiting master sign-off on Y=16/18/20 lane approach before execution.**
