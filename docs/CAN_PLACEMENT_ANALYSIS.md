# CAN Bus Subsystem — Placement + Routing Constraint Analysis

> **Status**: DRAFT for master sign-off (autonomous mode 2026-05-24).
> NO LAYOUT TOUCH until sign-off.
> **Branch**: TBD (likely `hw/can-placement-routing` off post-H↔C-merge head).
> **Sub-step**: queued behind H↔C routing (task #110).

---

## 1. Component inventory (per can_3j.py)

| Ref | Part | Footprint | Pads | Function |
|---|---|---|---|---|
| U14 | TJA1051TK/3 | HVSON-8 (3×3mm, EP) | 8+EP | CAN transceiver |
| U15 | PESD2CAN | SOT-23-3 (2.9×1.3mm) | 3 | TVS ESD protection |
| R45 | 120Ω 0603 | R_0603 | 2 | Bus termination |
| R46 | 0Ω 0603 | R_0603 | 2 | Termination jumper |
| C83 | 100nF 0402 | C_0402 | 2 | U14.VCC decap |
| C84 | 100nF 0402 | C_0402 | 2 | U14.VIO decap |
| J20 | JST-GH 4P | SM04B-GHS-TB horizontal | 4+2MP | Pixhawk CAN connector |

## 2. Net contract (5 nets)

| Net | Source | Target |
|---|---|---|
| CAN1_RX | MCU PD0 (pad 81 N, X=48.5 Y=27.32) | U14.4 |
| CAN1_TX | MCU PD1 (pad 82 N, X=48.0 Y=27.32) | U14.1 |
| GPIO_CAN1_SILENT | MCU PD3 (pad 84 N, X=47.0 Y=27.32) | U14.8 |
| CANH_NET | U14.7 → R45 → U15.1 → J20.2 | (TVS-protected) |
| CANL_NET | U14.6 → R46 → U15.2 → J20.3 | (TVS-protected) |

Plus power: +5V → U14.3 + J20.1 + C83; +3V3 → U14.5 + C84; GND ubiquitous.

## 3. Zone candidates

East band X=88..105 mostly empty (only Mauch2 J19 + sense R44/C82 at NW corner Y=5..18). Free for CAN block.

### Candidate A: NE corner (recommend)
- U14 + U15 + termination at (~94-100, 20-30)
- J20 at NE corner (~98, 5) — same Y as J3/J5 (north band)
- Pros: short fanout from MCU N pads (CAN1_RX/TX/SILENT) to U14
- Cons: shares N band with other connectors (J2 microSD, J3 telem, J5 GPS)

### Candidate B: East mid
- U14 + J20 at east mid (X=95-100, Y=40-50)
- Pros: clear of north band cluster
- Cons: longer fanout from MCU N pads (need to wrap east-then-south)

**Recommend: NE corner.** Standard Pixhawk convention + short fanout.

## 4. Proposed placement (provisional pending sign-off)

| Ref | Anchor (X, Y) | Rotation | Rationale |
|---|---|---|---|
| U14 | (94, 22) | 0° | South of CAN connector, between MCU N pads and J20 |
| U15 | (96, 27) | 0° | Between U14 and J20, on the CAN-bus signal path |
| R45 | (99, 22) | 90° | Termination, east of U14 |
| R46 | (99, 24) | 90° | Jumper, just south of R45 (forms 2-resistor termination block) |
| C83 | (92, 22) | 0° | U14.VCC decap, west of U14 (≤3mm from pin 3) |
| C84 | (92, 23) | 0° | U14.VIO decap, west of U14 (≤3mm from pin 5) |
| J20 | (97, 5) | 0° | NE corner south of board edge, harness exits north |

### Mounting + mid-edge keep-out verification
- North mid mounting hole at Y=42.5 — no conflict (CAN block is Y=5..30)
- Corner hole H2 at (101.75, 3.25) — keep-out Y<9.25 reaches J20 area; J20 at Y=5 may be tight. **Check at layout time.**

## 5. Fanout reach (Rule 18 + 19)

### Rule 18 (track + component pads)

For each net, MCU pad → U14/J20 pad:

| Net | MCU pad XY | U14 pad XY | Path | Est. length |
|---|---|---|---|---|
| CAN1_RX | (48.5, 27.32) N | (94, 22) approx U14.4 | NE diagonal | 50mm |
| CAN1_TX | (48.0, 27.32) N | (93, 22) U14.1 | NE diagonal | 50mm |
| GPIO_CAN1_SILENT | (47.0, 27.32) N | (96, 22) U14.8 | NE diagonal | 53mm |

### Rule 19 (existing routed nets in corridor)

Corridor: X=48..96 Y=22..28 (NE diagonal band from MCU N edge to U14 area).

Existing routes in this corridor (post-PR #83 merge):
- TBD survey needed — check for any +3V3 / +5V / SDMMC1 / SPI3 / CAN traces already in NE band

**Pre-flight before layout**: enumerate all routed nets in X=48..100 Y=20..30 corridor + count trace lanes vs available width.

## 6. Power for CAN connector

J20.1 = +5V (Pixhawk standard, allows downstream devices to draw FC's 5V). Power-only pad — no MCU signal.

## 7. Mirror analysis

CAN subsystem = SINGLE_INSTANCE per R3 (one CAN port). EXEMPT from MIRROR_PAIR.

## 8. Decisions for sign-off

1. Zone: NE corner (recommend) vs east-mid
2. U14 anchor (94, 22) — flexible ±3mm
3. J20 anchor (97, 5) — flexible to dodge H2 mounting hole
4. R45/R46 termination rotation 90° (recommend) vs 0° — preference

## 9. Gates plan

Same 5-gate template:
1. DRC ≤ baseline (post-H↔C-merge)
2. STACKUP-SPEC-MATCH PASS
3. MIRROR_PAIRS 11/11
4. DECOUPLING: C83 within 3mm of U14.3, C84 within 3mm of U14.5
5. Cluster walk: CAN1_RX/TX/SILENT F.Cu over In1 GND; CANH/CANL routed with controlled impedance (target ~60Ω diff per CAN spec)

---

**Awaiting master sign-off (after H↔C MOT* routing PR lands).**
