# Remaining Real-Estate Map (post-GPS-placement)

> **Status**: DRAFT for master sign-off (autonomous mode 2026-05-24).
> Generated AFTER GPS PR #86 (J5 at SW corner 15, 75) committed —
> baseline `hw/gps-placement-routing` head 334477b.
> **Purpose**: Per master 2026-05-24 directive — enumerate available
> zones for CRSF / Telem / SWD / Buzzer placement BEFORE layout. Avoid
> repeating GPS NW-band-density miss.

Methodology: `pcbnew.LoadBoard().GetFootprints()` enumeration per
zone (artifact-verified, not prose-planned). Rule 18 + Rule 19 applied.

---

## Zone summary

| Zone | Area (mm²) | Status | Recommended for |
|---|---:|---|---|
| **N-middle** (X=40..65 Y=0..15) | 375 | **EMPTY** ✓ | TELEM or SWD |
| **W-edge** (X=0..15 Y=15..60) | 675 | **EMPTY** ✓ | (large open area) |
| **N-far-east** (X=65..85 Y=0..15) | 300 | Occupied by B subsystem (Q4 + U12 + C75/76/81/R43/R44) — NO room | — |
| **SW-corner** (X=0..40 Y=60..85) | 1000 | OCCUPIED by GPS (just placed) | (GPS) |
| **S-band-east-of-J11** (X=62..85 Y=63..85) | 506 | **EMPTY** ✓ | CRSF or follow-up |
| **E-band Y=14..30 above SWD** (CAN block) | 240 | OCCUPIED by CAN (U14, U15, R45, R46, C83, C84) | — |
| **E-band Y=34..42** (below USB-C above TELEM) | 120 | **EMPTY** ✓ | TELEM connector |
| **E-band Y=45..55** (below TELEM above microSD) | 150 | **EMPTY** ✓ | (small, ~15×10mm) |

## Detailed enumeration

### N-middle (X=40..65 Y=0..15) — EMPTY 375mm²
- Status: no components present
- Fanout reach to MCU N pads (X=39..50, Y=27.32): 15-25mm — short
- **Best fit for SWD or TELEM**: both are NE-corner candidates per
  original analysis. SWD pin sources are PA13 east (pad 72) + PA14
  north (pad 76) — N-middle places SWD close to PA14 with PA13 ~15mm
  reach east.

### W-edge (X=0..15 Y=15..60) — EMPTY 675mm²
- Status: no components present (large open!)
- Available for follow-up future expansion
- Fanout reach to MCU: ~25-50mm to W edge pads (X=37.33)
- **Recommended fit**: Buzzer / spare TPs / future I/O expansion. None
  of CRSF/Telem/SWD natural here (their pins are mostly N+E).

### N-far-east (X=65..85 Y=0..15) — OCCUPIED 300mm²
Mauch2 J19 + B-subsystem (Q4 OR-FET, U12 LM74700, decap caps,
sense R43/R44). FULL. Connector pin density already tight.
- **Not available** for new placement.

### SW-corner (X=0..40 Y=60..85) — POST-GPS, OCCUPIED 1000mm²
Just-placed GPS:
- J5 @ (15, 75)
- D5-D9 ESDs @ X=24, Y=67-75
- R21/R22 I²C pulls @ X=27, Y=71-73
- TP1-TP5 test pads @ Y=62, X=10-22
- H3 mount @ (3.25, 81.75) Φ6 keep-out
- **Remaining clear space**: roughly X=32..40 Y=60..85 (~200mm² triangle
  shape, irregular). Small, not great for more connectors.

### S-band-east-of-J11 (X=62..85 Y=63..85) — EMPTY 506mm²
J11 ESC connector @ (52.5, 80) X=44..61. Area east of J11 down to
J2 microSD X-extent (87) is CLEAR.
- 23×22mm available
- Mid-edge mounting hole Y=42.5 — NOT in this band (Y>62)
- **Recommended for nothing critical** — far from MCU (>40mm to
  any pin), better for spare TPs / future I/O

### E-band CAN block (X=88..103 Y=14..30) — OCCUPIED 240mm²
Just-placed CAN. FULL.

### E-band Y=34..42 (X=88..103 Y=34..42) — EMPTY 120mm²
Between USB-C J1 (Y=24-36) and planned TELEM (Y=42).
- 15×8mm available
- **Best fit for TELEM**: J3 (9.5×12mm bbox) just fits with tight
  margins. TELEM pin sources PA9/PA10 East pads — ~10mm reach.

### E-band Y=45..55 (X=88..103 Y=45..55) — EMPTY 150mm²
Between TELEM and microSD J2 (starts Y=58).
- 15×10mm available
- **Best fit for nothing critical** — small, between TELEM + microSD
- Could host CRSF ESD diodes if CRSF goes E-band

## Proposed zone assignments

| Subsystem | Zone | Anchor | Rationale |
|---|---|---|---|
| **TELEM (J3)** | E-band Y=38 | (95, 38) | Closest to PA9/PA10 pads, fits Y=34..42 gap |
| **CRSF (J10)** | N-middle Y=8 | (54, 8) | PC6/PC7 MCU east-edge — N-middle gives ~10mm reach, short |
| **SWD (J9)** | N-middle Y=8 | (45, 8) | PA13 east + PA14 north — N-middle has short reach to both. Adjacent to CRSF but SWD bbox 8.63×10.27mm — fits with CRSF in N-middle Y=0..15 |
| **Buzzer test pad** | W-edge Y=22 | (12, 22) | Already covered by TP5 in GPS — no new buzzer placement needed |

**Combined N-middle layout** (CRSF + SWD both in X=40..65 Y=0..15):
- SWD J9 @ (45, 8) — bbox X=40.7-49.3 Y=2.9-13.1
- CRSF J10 @ (54, 8) — bbox X=49.9-58.1 Y=2.8-13.2

Adjacency: 1mm gap between SWD east (49.3) and CRSF west (49.9) — tight
but feasible with courtyard clearance check.

OR space them out: SWD @ (42, 8) + CRSF @ (57, 8) — 6mm gap.

## Per-subsystem fanout reach (Rule 19 quick check)

### TELEM @ (95, 38) — fits Y=34..42 gap
- PA9 pad 68 E (52.67, 32.5) → J3.2 ~(94, 36): NE diagonal ~42mm
- PA10 pad 69 E (52.67, 32) → J3.3 ~(94, 37): NE diagonal ~42mm
- Existing routes in corridor X=53..94 Y=32..38: USB-C diff (PA11/12 → J1)
  + CAN signals (PD0/PD1/PD3 → CAN block at Y=22). Crowded N band — verify
  at placement time.

### SWD @ (45, 8) — fits N-middle
- PA13 pad 72 E (52.67, 30.5) → J9.2 SWDIO ~(43.5, 7): NW ~25mm
- PA14 pad 76 N (51, 27.32) → J9.4 SWCLK ~(44.5, 9): NW ~20mm
- NRST pad 14 W (37.33, 35.5) → J9.10 NRST ~(46.5, 7): NE long ~30mm
- Existing N-middle Y=0..15 X=40..65: empty per survey above. Clean fanout
  expected.

### CRSF @ (54, 8) — fits N-middle east half
- PC6 pad 63 E (52.67, 34) → J10.2 USART6_TX ~(53.5, 7): N short ~27mm
- PC7 pad 64 E (52.67, 34.5) → J10.3 USART6_RX ~(54.5, 7): N short ~28mm
- Plus ESD TVS for TX/RX: standard practice, ~2 SOT-723 packages within 5mm of J10 pads
- Existing corridor X=52..54 Y=8..34: mostly empty (E edge tracks SPI2/IMU2 are at X=54.5+).
  Clean.

## Decisions for sign-off

1. **TELEM anchor (95, 38)** — recommend; ±2mm flex
2. **SWD anchor (45, 8)** — recommend; ±3mm flex; verify against PA13 east + PA14 north + NRST west fanout
3. **CRSF anchor (54, 8)** — recommend; ±3mm flex
4. **SWD vs CRSF order in N-middle**: SWD west (45) + CRSF east (54) keeps SWD close to PA14 (51, 27.32). Confirm.
5. **Buzzer**: already covered by TP5 — no separate placement needed.

## After sign-off

Parallel execution branches:
- `hw/telem-placement-routing` — J3 at E-band Y=38
- `hw/swd-placement-routing` — J9 at N-middle (45, 8)
- `hw/crsf-placement-routing` — J10 at N-middle (54, 8)

If CRSF J10 schema is still `CRSF_solder_pad` on board (per board state),
needs SKiDL re-sync to `Connector_JST:JST_GH_SM04B-GHS-TB_1x04-1MP_P1.25mm_Horizontal`
which schema already has. Net topology unchanged.

---

**Awaiting master sign-off on §"Decisions for sign-off" before subsystem layout execution.**
