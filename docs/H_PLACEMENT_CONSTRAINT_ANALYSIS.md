# H (ESC Outputs) Placement — Up-Front Constraint Analysis

> **Status**: DRAFT for master review. NO LAYOUT TOUCH per master
> 2026-05-24 directive (slot retrofit failures reinforced "constraint
> work BEFORE layout pays 10:1").
> Branch `hw/h-placement` off `sch/option-b-buck` head `c35dee1`.
> Sub-step: H placement (placement only — H↔C routing is separate).

---

## 1. I/O contract

### 8 DShot channels — MCU pin map (verified from current netlist)

| Net | MCU pin | XY (mm) | Edge | Timer (per `esc_3f.py`) | BDSHOT |
|---|---|---|---|---|---|
| MOT1 | U1.34 | (43.00, 42.67) | **SOUTH** | TIM3_CH3 | ✓ |
| MOT2 | U1.35 | (43.50, 42.67) | SOUTH | TIM3_CH4 | — |
| MOT3 | U1.22 | (37.33, 39.50) | **WEST** | TIM2_CH1 | ✓ |
| MOT4 | U1.23 | (37.33, 40.00) | WEST | TIM2_CH2 | — |
| MOT5 | U1.24 | (37.33, 40.50) | WEST | TIM5_CH3 | ✓ |
| MOT6 | U1.25 | (37.33, 41.00) | WEST | TIM5_CH4 | — |
| MOT7 | U1.59 | (52.67, 37.00) | **EAST** | TIM4_CH1 | ✓ |
| MOT8 | U1.60 | (52.67, 36.50) | EAST | TIM4_CH2 | — |

Edge distribution: 2 SOUTH + 4 WEST + 2 EAST. **Not uniform** — south
is the natural exit toward H zone but only 2 of 8 pins are there.
West (4 pins) and east (2 pins) need to wrap south during fanout.

DShot600 = 600 kbit/s, ~5-10ns edge rate, ~100MHz spectral content
from harmonics. Moderate-EMI; not differential.

### 8 connector destinations — **format flag for master**

**Current SKiDL netlist** (`esc_3f.py:152-154` + footprint inventory):
- Footprint = `ESC_solder_pad` (CUSTOM, 2-pin solder pads, hand-soldered wires)
- NOT JST-GH per master assumption in directive

`esc_3f.py` comment line 49: *"Production ESC wires are hand-soldered
to the pads — standard"*. This is intentional from Phase 3-4 design.

Footprint dimensions:
- Body bbox: 9.66 × 6.96mm (silkscreen-inclusive)
- Pad: 2.00 × 1.50mm, 2 pads at 2.5mm Y-spacing
- Courtyard: 3.05 × 4.95mm

DECISIONS.md §7 specifies **JST-GH** as the project connector standard.
SKiDL uses solder-pad. **Flag for master**: which is the v1 spec?

Options:
- (i) Stay with solder-pads (current netlist) — minimum BOM, hand-soldering
  acceptable for prototype/low-volume, harness flexible
- (ii) Amend SKiDL to JST-GH per §7 — adds 8× connector cost, requires
  matched harness on airframe, but cleaner field-serviceability
- (iii) Mix: JST-GH for primary 4 channels, solder pad for backup 4

**My recommendation: (i) keep solder pads** — current netlist is
self-consistent, ESC solder pads are common in FC market (Matek, T-Motor
F7, BetaFPV), and JST-GH would be schema-level scope creep for what's
ostensibly a placement-only sub-step. If master wants JST-GH for v1,
that's a separate SKiDL amend PR before H placement.

### 8 channels × 2 pads (signal + GND) = 16 net endpoints

GND pads tie into the existing In1.Cu / In4.Cu GND planes (no separate
GND routing needed — short trace stub from each ESC pad-2 to plane
stitching via).

## 2. Zone candidates

After D placement at Y=51..63 X=56..86, remaining real estate:

| Zone | X range | Y range | Area (mm²) | Suitability |
|---|---|---|---|---|
| South band | 0..105 | 65..85 | **2100** | ✓ Standard FC ESC exit, motor leads point south toward airframe |
| East band | 88..105 | 0..85 | 1445 | △ Connectors face east — works if airframe has east-side motor harness, atypical |
| SE corner | 88..105 | 65..85 | 340 | ✗ Too small for 8 connectors |
| West band | 0..15 | 30..85 | 825 | ✗ Already populated with A/B/J4 connectors |

**Recommendation: south band Y=65..85**.
- 8 connectors at ~13mm pitch (X = 10, 22, 34, 46, 58, 71, 83, 95)
- ESC courtyard 3.05 × 4.95mm → at 13mm pitch, ~10mm clearance between courtyards
- Y centered at Y=75 (mid of band) → south edge Y=85 has 7.5mm clear to courtyard south Y=77.5

### Corner mounting-hole keep-out check
- H3 at (3.25, 81.75), H4 at (101.75, 81.75) — 6mm keep-out radius
- Leftmost connector at X=10, courtyard X=8.5..11.5 — H3 at X=3.25 + 6mm = X≤9.25 keep-out reach. 10mm OK.
- Rightmost at X=95, courtyard X=93.5..96.5 — H4 at X=101.75 - 6mm = X≥95.75 keep-out. 96.5 > 95.75 → INSIDE keep-out by 0.75mm. **TIGHT** — shift rightmost connector to X=93 or compress pitch slightly.

### Mid-edge mounting-hole keep-out (Y=42.5)
- South band Y=65..85, mid-edge keep-out at Y=42.5 — no overlap. ✓

## 3. Connector orientation + harness exit direction

Per standard FC convention, motor leads exit SOUTH (toward airframe
motor mount). Connectors oriented with pad-1 (signal) NORTH (board
interior) + pad-2 (GND) SOUTH (board edge side).

For `ESC_solder_pad` (2-pin solder-pad): pads vertical (pad 1 at Y_low,
pad 2 at Y_high = +2.5mm). For south-exit, place footprint at Y=75
unrotated — pad 1 at Y=75 (signal, north side), pad 2 at Y=77.5 (GND,
south side closer to board edge).

Wire soldered to each pad exits sideways (perpendicular to pad-pad
axis). Direction depends on wire bend. Typical: wires bent 90° south
after soldering, exit board's south edge.

## 4. MCU fanout corridor planning

For each of 8 DShot pins, F.Cu fanout from MCU edge to H zone Y=75:

| Net | Start | End-target | Path | Length est. |
|---|---|---|---|---|
| MOT1 | (43.00, 42.67) | (10..95, 75) | SOUTH straight | ~32-50mm |
| MOT2 | (43.50, 42.67) | ditto | SOUTH straight | ~32-50mm |
| MOT3 | (37.33, 39.50) | south wrap from WEST | W-then-S | ~40-65mm |
| MOT4 | (37.33, 40.00) | ditto | ~40-65mm |
| MOT5 | (37.33, 40.50) | ditto | ~40-65mm |
| MOT6 | (37.33, 41.00) | ditto | ~40-65mm |
| MOT7 | (52.67, 37.00) | south wrap from EAST | E-then-S | ~40-60mm |
| MOT8 | (52.67, 36.50) | ditto | ~40-60mm |

WEST exit pins (MOT3-6) need most wrap effort. Routing: F.Cu west to
X=37, then south to Y=75, then east as needed to reach connector.

**D-zone keep-out**: D is at X=56..86 Y=51..63. WEST DShot fanout
naturally avoids D (going south at X<37, then east at Y>63). MOT1+MOT2
from south MCU edge cross Y=42.67 → Y=75 — they pass through Y=51..63 at
X=43-44 — WEST of D zone (D west at X=56). ✓ no conflict.
EAST fanout (MOT7+8) at X=52.67 → south to Y=75 — passes Y=51..63 at
X=52.67, also WEST of D (X<56). ✓.

**No DShot trace enters D zone footprint** if all fanout stays at X<56
or X>86. Verifying:
- All connectors at X=10..95 → MOT_N traces end at X∈[10, 95]
- If any connector at X∈[56, 86], MOT trace would have to wrap around D
  during last 30mm. Solvable but tedious — better to place no connectors
  in X=56..86 range.

**Connector X-placement under D-keep-out constraint**:
- D X-extent: 56..86
- Available H X-bands: 0..56 (west of D) + 86..105 (east of D)
- 8 connectors fit easily in 56 + 19 = 75mm of usable south-band X
- Suggested: 4 connectors at X=10, 20, 30, 40 (west band) + 4 at X=90,
  100... NO wait east band only X=86..105 = 19mm = max 2 connectors at
  10mm pitch. Doesn't work.

**Revised**: don't avoid D X-range strictly. DShot traces CAN cross
D zone if routed on B.Cu (under D zone with In4.Cu GND between).
B.Cu has space south of D zone (Y>63 — connectors are at Y=75).

So fanout strategy:
- MOT1, MOT2 (SOUTH pins): F.Cu south through Y=42..75 → connector
- MOT3-6 (WEST pins): F.Cu west to X=37, then south to Y=63 (D north edge clear),
  then B.Cu under D OR F.Cu around D west
- MOT7-8 (EAST pins): F.Cu east to X=52, then south... but east of D needs traversal

Detailed fanout planning is the H↔C routing step (separate PR per
master sequencing).

## 5. Length budgeting

DShot600 = 600 kbit/s, edge rate ~5-10ns. **Length skew tolerance: ±20%
of average is typical safe** for asynchronous parallel channels.

If average trace length is 50mm → ±20% = ±10mm tolerance. With fanout
distances 32-65mm above, max-min = 33mm = 66% of mean — too wide if
strict.

But DShot **channels are independent** (not bus-synchronized like SPI).
Each channel's timing matters only relative to that ESC's clock recovery
window, not to other channels. So absolute length tolerance is loose —
just keep all traces under ~150mm for signal integrity.

**No special length-matching constraints** for DShot. Don't over-engineer.

## 6. EMI keep-out from D zone IMU island

DShot edge rate 5-10ns → spectral content to ~100MHz. IMU SPI also has
edges at ~20-30ns (5MHz SCK) → spectral content to ~50MHz. Overlap
region 50-100MHz where DShot harmonics could couple to IMU SPI.

Mitigation:
- DShot F.Cu traces ≥3mm from IMU SPI F.Cu traces in parallel sections
- Cross perpendicular where unavoidable
- In1.Cu GND below F.Cu DShot (continuous below MCU south-edge fanout — verified by audit STACKUP-SPEC-MATCH after PR #76)
- In4.Cu GND below B.Cu DShot if used

D zone X=56..86 Y=51..63 has dense routing (SPI1/2/3 from PR #77 + +3V3_IMU
from PR #78). DShot fanout MUST avoid F.Cu segments in this region —
acceptable to cross on B.Cu (under D, In4.Cu GND between).

## 7. Power for ESC connector pinout

Per `esc_3f.py:6`: *"no power passthrough (ESCs powered directly from
battery via separate harness)"*. Signal + GND only (matches solder-pad
2-pin layout). No +5V_BEC at ESC connector.

This is the STANDARD multirotor topology — ESCs powered directly from
battery, FC sends only PWM/DShot signal + GND reference. Saves traces
and avoids high-current paths from FC to ESC.

No change needed.

## 8. Mirror analysis

8 ESC connectors arranged along south edge — all **SINGLE_INSTANCE**
per R3 (each connector serves unique motor channel). EXEMPT from
MIRROR_PAIR symmetry.

Structural-asymmetry note: connector spacing should be UNIFORM unless
specific reason (e.g., MOT1 paired with MOT2 to TIM3 — physically
adjacent on south PCB edge mirrors timer pairing — natural grouping).

Proposed pairing groups by timer (per `esc_3f.py:21-28`):
- TIM3: MOT1+MOT2 (PB0+PB1)
- TIM2: MOT3+MOT4 (PA0+PA1)
- TIM5: MOT5+MOT6 (PA2+PA3)
- TIM4: MOT7+MOT8 (PD12+PD13)

Connectors grouped by timer = 4 pairs of 2, with tighter spacing
within-pair and looser between pairs. Optional aesthetic — not
mechanically required. Simpler: uniform 12mm pitch across all 8.

**Recommend uniform spacing** (R3 structural-asymmetry doctrine
defaults: SINGLE_INSTANCE bucket is exempt, no need to enforce structure).

## 9. Decisions awaiting master sign-off

1. **Connector format**: SKiDL has `ESC_solder_pad` (current); DECISIONS.md
   §7 specifies JST-GH. Which is v1 spec?
   - (i) Keep solder-pads (recommend — netlist matches, smaller scope)
   - (ii) Amend SKiDL to JST-GH (separate PR first, then re-do H placement)
   - (iii) Mix
   Recommend **(i)** — clarify §7 to allow ESC-style solder pads or
   amend §7 to say "JST-GH except ESC outputs which use solder pads".

2. **Zone choice**: south band Y=65..85 (recommend) vs east band X=88..105?
   Recommend south.

3. **Connector spacing**: uniform 12mm pitch (recommend) vs timer-paired
   grouping (4 pairs, tighter within-pair)?
   Recommend uniform.

4. **Connector X-range**: full board X=10..95 (8 connectors at 12mm
   pitch) OR avoid X=56..86 strictly (D-zone keep-out, fits only 6)?
   Recommend full X=10..95 — DShot fanout can cross D on B.Cu where
   needed.

5. **Right-edge connector at X=95**: courtyard X=93.5..96.5 INSIDE H4
   mounting keep-out (X≥95.75). Options:
   - (a) Shift rightmost connector to X=93 (courtyard X=91.5..94.5 — 1.25mm clear)
   - (b) Compress 8-connector pitch to fit in X=10..93 (11.86mm pitch)
   - (c) Shift everyone left + use X=8..93
   Recommend **(a)** — simplest, only affects rightmost connector.

## Proposed placement (provisional — pending §9 decisions)

Assuming (i) solder-pad + south band + uniform pitch + (a) right-shift:

| Ref | Anchor (X, Y) | Rotation |
|---|---|---|
| J11 (MOT1) | (10.0, 75.0) | 0° |
| J12 (MOT2) | (21.86, 75.0) | 0° |
| J13 (MOT3) | (33.71, 75.0) | 0° |
| J14 (MOT4) | (45.57, 75.0) | 0° |
| J15 (MOT5) | (57.43, 75.0) | 0° |
| J16 (MOT6) | (69.29, 75.0) | 0° |
| J17 (MOT7) | (81.14, 75.0) | 0° |
| J18 (MOT8) | (93.0, 75.0) | 0° |

Pitch: (93 - 10) / 7 = 11.86mm. All 8 connectors fit within H4 keep-out
boundary. Each connector's silkscreen extent ~4.83mm half-width →
neighbor clearance (11.86 − 4.83×2) = 2.2mm — adequate for fanout via
between.

## Mechanical / footprint check
- ESC_solder_pad courtyard 3.05×4.95mm → comfortable spacing
- Mid-edge mounting hole keep-outs at Y=42.5 — H zone Y=65..85 no conflict
- Board south edge at Y=85, courtyard south at Y=77.5 → 7.5mm board edge clearance ✓

---

**Awaiting master sign-off on §9 decisions before layout execution.**
