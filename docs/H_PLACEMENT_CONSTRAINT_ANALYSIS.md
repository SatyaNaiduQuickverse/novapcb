# H (ESC Outputs) Placement — Up-Front Constraint Analysis (10-pin rev)

> **Status**: DRAFT for master review. NO LAYOUT TOUCH until master
> sign-off.
> **Branch**: `hw/h-placement-10pin` off `sch/option-b-buck` head `b5b6818`
> (PR #80 merged — single 10-pin J11 JST-GH).
> **Supersedes**: the obsolete 8× 2-pin analysis on the abandoned
> `hw/h-placement` branch (sha 87fc1e0). Geometry fundamentally
> different: 1 connector, not 8.
> Sub-step #107.

---

## 1. I/O contract

### Schematic (PR #80 merged, sch/option-b-buck head b5b6818)

Single 10-pin JST-GH connector **J11** with Pixhawk 6X FMU PWM OUT
pinout. Locked per master 2026-05-24:

| J11 pin | Net | MCU source | MCU XY (mm) | Edge | Timer | BDSHOT |
|---:|---|---|---|---|---|---|
| 1 | MOT1 | U1.34 | (43.00, 42.67) | SOUTH | TIM3_CH3 | ✓ |
| 2 | MOT2 | U1.35 | (43.50, 42.67) | SOUTH | TIM3_CH4 | — |
| 3 | MOT3 | U1.22 | (37.33, 39.50) | WEST | TIM2_CH1 | ✓ |
| 4 | MOT4 | U1.23 | (37.33, 40.00) | WEST | TIM2_CH2 | — |
| 5 | MOT5 | U1.24 | (37.33, 40.50) | WEST | TIM5_CH3 | ✓ |
| 6 | MOT6 | U1.25 | (37.33, 41.00) | WEST | TIM5_CH4 | — |
| 7 | MOT7 | U1.59 | (52.67, 37.00) | EAST | TIM4_CH1 | ✓ |
| 8 | MOT8 | U1.60 | (52.67, 36.50) | EAST | TIM4_CH2 | — |
| 9 | VDD_SERVO | — | — | — | — | NC (Sai-ratified) |
| 10 | GND | — | — | — | — | plane stitch |

**Pin order LOCKED** — master directive: MOT1..MOT8 → J11.1..J11.8 is
Pixhawk standard, harness compatibility (DECISIONS.md §7 "no
re-crimping" lock). Don't swap at the connector OR the schematic.

Escape hatches if reachability proves impossible (master priority order):
1. **Layer split** (F.Cu + B.Cu via In4 GND ref — SPI3-wraparound pattern from PR #77)
2. **hwdef.dat MCU-pin remap** (firmware side; coordinates with task #66)
3. **Schematic re-map** (last resort — changes source of truth)

### Footprint geometry (verified via `pcbnew.FootprintLoad`)

`Connector_JST:JST_GH_SM10B-GHS-TB_1x10-1MP_P1.25mm_Horizontal`:

- Courtyard: **17.01 × 6.45 mm** (X=±8.51, Y=−3.23..+3.23 about anchor)
- 10 signal pads on Y=−1.85 (1.25mm pitch, X=−5.625..+5.625)
- 2 mechanical posts at (±7.475, +1.35), 1.0×2.7mm
- Body bbox (silk+pad+ref text): 43.49 × 9.50 mm — silkscreen ref/value
  text drives the wider bbox; courtyard 17.01 × 6.45 is the
  layout-meaningful number
- **Wire entry SOUTH of anchor** (pads on the north side, mech posts +
  cable mate on the south side) — natural fit for south-edge mounting

## 2. Zone candidate

Single-connector geometry collapses the prior 8-connector zone debate.
Remaining options:

| Zone | Anchor (X, Y) | Courtyard span | Fit |
|---|---|---|---|
| **South band Y≈80** (recommend) | (52.5, 80) | X=44.0..61.0, Y=76.77..83.23 | Standard FC motor exit, harness exits south toward airframe |
| North band Y≈30 | (52.5, 30) | rejected — collides with C zone (MCU) | ✗ |
| East band X≈97 | (97, 42.5) (rotated 90°) | length 17mm > available 17mm — tight | △ atypical exit dir |

**Recommend south band, anchor Y=80.**
- South board edge Y=85 — courtyard south edge at Y=83.23 → 1.77mm
  board-edge clearance (matches the 1.5..2mm convention used by
  existing south-edge JST-GH on this design)
- North side of courtyard at Y=76.77 — clear of D zone south edge (Y=63)
  by ~13.77mm
- Mid-edge mounting holes at Y=42.5 — no Y overlap with H zone

## 3. Connector orientation + harness exit direction

`Horizontal` (side-entry / right-angle) variant. Pads face NORTH
(toward MCU); mech posts + wire entry face SOUTH (toward board edge).

Rotation: **0°** (canonical). Anchor at (52.5, 80):
- Pads pin 1..10 at Y=78.15, X=46.875..58.125 (signal-entry side)
- Mech posts at Y=81.35, X=45.025 + 59.975 (cable-mate side)
- Wire harness exits south past Y=85 board edge

This matches every other south-facing JST-GH on the design (telem 3i,
power 3h) — same anchor convention, same rotation.

## 4. MCU fanout corridor planning (REACHABILITY MAP)

Centered placement at X_anchor = 52.5 puts pin midline at X=52.5.
MCU edge distribution maps naturally:

| Net | MCU pin (X, Y) | J11 pin (X, Y) | ΔX | ΔY | F.Cu path |
|---|---|---|---|---|---|
| MOT1 | (43.00, 42.67) | J11.1 (46.875, 78.15) | +3.88 | +35.48 | S-then-E |
| MOT2 | (43.50, 42.67) | J11.2 (48.125, 78.15) | +4.63 | +35.48 | S-then-E |
| MOT3 | (37.33, 39.50) | J11.3 (49.375, 78.15) | +12.05 | +38.65 | W-edge → S → E |
| MOT4 | (37.33, 40.00) | J11.4 (50.625, 78.15) | +13.30 | +38.15 | W-edge → S → E |
| MOT5 | (37.33, 40.50) | J11.5 (51.875, 78.15) | +14.55 | +37.65 | W-edge → S → E |
| MOT6 | (37.33, 41.00) | J11.6 (53.125, 78.15) | +15.80 | +37.15 | W-edge → S → E |
| MOT7 | (52.67, 37.00) | J11.7 (54.375, 78.15) | +1.71 | +41.15 | E-edge → S (near-straight) |
| MOT8 | (52.67, 36.50) | J11.8 (55.625, 78.15) | +2.96 | +41.65 | E-edge → S |
| GND | plane stitch | J11.10 (58.125, 78.15) | — | — | via to In1/In4 GND |

### Reachability check (per master directive)

- **All 8 MOT* paths are F.Cu-feasible** at this centered anchor — no
  layer split required, no firmware remap required. Worst case is MOT6
  at 53mm total path (12mm west-to-east + 38mm north-to-south); DShot600
  tolerates ≪100mm comfortably.
- **No crossings**: ordering MOT1→MOT8 left-to-right at the connector
  matches the natural east-bias of MCU pin XYs (MOT3-6 at X=37.33 are
  westmost; MOT7-8 at X=52.67 are eastmost; MOT1-2 at X≈43 are middle).
  Fanout order matches connector pin order — no crossover required.
- **D-zone clearance**: D occupies X=56..86 Y=51..63. All 8 MOT*
  paths terminate at connector pin X≤55.625 (J11.8 is the rightmost
  signal). Only J11.9 (NC) at X=56.875 and J11.10 (GND) at X=58.125
  sit at X>56 — and at Y=78.15, well clear of D zone Y=51..63. Vertical
  N-to-S fanout traces pass through Y=51..63 corridor at X≤55.625, all
  WEST of D zone. **Zero D-zone trace conflicts**.
- **No GND-island risk**: GND on J11.10 ties via stitching via to In1.Cu
  + In4.Cu GND planes (continuous post-PR #76 stackup fix).

### Cluster-walk readiness (master 9-rule gate)

For each F.Cu DShot trace:
- F.Cu trace overlies In1.Cu GND plane (primary GND) — continuous
  post-PR #76. Verify with `audit_layout_compliance.py
  STACKUP-SPEC-MATCH` gate (already passes baseline).
- No segments cross In1.Cu split-plane voids (none exist; In1 is
  full-board GND pour per DECISIONS §8).
- 5ns DShot edge → return current concentrated under trace; In1.Cu
  GND continuity = clean return path.

## 5. Length budgeting

DShot600 = 600 kbit/s, edge rate ~5-10ns. Channels are independent
(per-ESC clock recovery), so absolute length matters only for SI not
inter-channel skew.

- Min trace: MOT7 at ~43mm
- Max trace: MOT6 at ~53mm
- Spread: 10mm (~21% of mean)
- All <60mm — safe for 100Ω char impedance F.Cu over GND
- **No length-matching constraint** per project convention (matches
  D-routing PR #77 approach for SPI buses which DO need length-match;
  DShot does not)

## 6. EMI keep-out from D-zone IMU island

DShot edge 5-10ns → spectral content to ~100MHz; IMU SPI edges at
~20-30ns → ~50MHz. Coupling band 50-100MHz where parallel DShot/SPI
sections would worry the gyro noise floor.

- D zone X=56..86 Y=51..63 has dense F.Cu+B.Cu routes (post PR #77 + #78)
- All 8 MOT* fanout terminates at X≤55.625 (J11.8) — **WEST of D zone**
- Fanout from WEST/EAST MCU edges to connector takes the **column
  X=37..56** for the long N-to-S leg — entirely WEST of D zone
- **No parallel DShot/SPI segments** at the analysis level; closest
  approach is MOT6 fanout passing at X≈53 just west of D west edge X=56
  (~3mm spacing — meets the ≥3mm parallel rule)
- MOT3-6 routes will cross D-zone north edge (Y≈51) at X=37..53; this
  is the bridge column already used by D↔C SPI routes from PR #77 —
  must verify bridge-column density after layout

### Bridge-column pre-flight (per master pattern from D-routing)

Per master memory: bridge column X=63±5mm (D-routing convention).
For H placement, the relevant bridge column is X=37..56 (between west
edge & D zone west). Reused by:
- MOT3-6 F.Cu fanout (north-south, 4 traces)
- Existing PR #77 D↔C/B routes (HEATER_PWM, SPI3 wraparound)

Pre-flight census (will run as Gate 0 before layout): count tracks
already crossing Y=50..52 in X=37..56. If ≤10 silent proceed, 11-12
flag, >12 escalate (looser than D-routing bridge X=63±5 because this
column is wider).

## 7. Power for the ESC connector pinout

Per esc_3f.py:67 + PR #80: no FC-side power on this connector.
- J11.9 VDD_SERVO = NC (Sai-ratified)
- J11.10 GND = via to In1/In4 GND planes

ESCs powered directly from main battery via airframe distribution.
The FC sends only 3.3V DShot signal + GND reference. Matches Pixhawk
6X FMU port convention.

**No +5V_BEC trace to this connector**.

## 8. Mirror analysis

Single connector — SINGLE_INSTANCE per R3, exempt from MIRROR_PAIR
symmetry.

Structural-asymmetry note: a single 17mm-wide connector at board
midline X=52.5 is naturally symmetric about the board centerline
(board X=0..105 → midline X=52.5). No structural reason to offset.

**No mirror pair to enforce, no structural asymmetry to document.**

## 9. Decisions awaiting master sign-off

### D1 — X-anchor placement
- (a) **CENTERED at X=52.5** (recommend) — natural fanout balance,
  pin 1 (MOT1) west and pin 8 (MOT8) east matches MCU edge distribution
- (b) Offset west (X=42.5) — straightens MOT3-6 fanout but pushes
  MOT7-8 into ugly backwards east-to-west fanout
- (c) Offset east (X=62.5) — pushes connector into D-zone X-range and
  makes MOT1-2 fanout longer
- (d) East band rotated 90° (X≈97, Y=42.5) — rejected as atypical
  harness exit + tight fit

**Recommend (a) centered.** No master decision needed if (a) accepted.

### D2 — Y-anchor placement
- (a) **Y=80** (recommend) — 1.77mm board-edge clearance, 13.77mm to D-zone
- (b) Y=78 — 3.77mm board-edge clearance, looser south margin but
  reduces fanout length by 2mm

Recommend **(a) Y=80** for consistency with the FC south-edge
convention (other JST-GH south connectors at Y=80 ± 1mm).

### D3 — Rotation
- (a) **0°** (recommend, default canonical) — pads N, mech posts S
- (b) 180° — pads S, mech posts N — wire exits NORTH (wrong direction)

Recommend **(a) 0°**. Trivial.

## Proposed placement (provisional pending D1-D3 sign-off)

| Ref | Anchor (X, Y) | Rotation | Footprint |
|---|---|---|---|
| J11 | (52.5, 80.0) | 0° | Connector_JST:JST_GH_SM10B-GHS-TB_1x10-1MP_P1.25mm_Horizontal |

Pad positions (post-rotation, anchor 52.5, 80):
- J11.1 (MOT1): (46.875, 78.15)
- J11.2 (MOT2): (48.125, 78.15)
- J11.3 (MOT3): (49.375, 78.15)
- J11.4 (MOT4): (50.625, 78.15)
- J11.5 (MOT5): (51.875, 78.15)
- J11.6 (MOT6): (53.125, 78.15)
- J11.7 (MOT7): (54.375, 78.15)
- J11.8 (MOT8): (55.625, 78.15)
- J11.9 (VDD_SERVO NC): (56.875, 78.15) — NC, no trace
- J11.10 (GND): (58.125, 78.15) — stitch via to In1/In4 GND
- Mech posts: (45.025, 81.35) + (59.975, 81.35)

## Mechanical / footprint check
- Courtyard 17.01 × 6.45 mm fits in south band Y=65..85 with 1.77mm S edge clearance
- Mid-edge mounting holes Y=42.5 — no overlap
- Corner mounting holes H3/H4 at (3.25 / 101.75, 81.75) — courtyard X=44..61, far from both (>40mm)
- D zone X=56..86 Y=51..63 — no Y overlap with H zone; X overlap with J11.9/J11.10 OK since these are at Y=78.15

## 5-gate verify plan (post-layout, before push)

1. Audit baseline preserved (DRC stays at 10, STACKUP-SPEC-MATCH PASS, MIRROR_PAIRS 11/11)
2. J11 placed at agreed anchor + rotation
3. Each MOT* net cluster-walk: F.Cu trace + In1.Cu GND continuous below
4. No DRC increase on neighboring D zone routes (PR #77/#78 preserved)
5. Thermal re-run gate12 (J11 = passive connector, ~0W; no thermal delta expected — confirm)

---

**Awaiting master sign-off on D1-D3 before layout execution.**
