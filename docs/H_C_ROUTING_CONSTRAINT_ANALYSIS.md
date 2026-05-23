# H↔C Routing — Constraint Analysis (8 MOT* fanout + GND stitch)

> **Status**: DRAFT for master review. NO LAYOUT TOUCH until sign-off.
> **Branch**: `hw/h-c-routing` off `sch/option-b-buck` head `ea6d62f`
> (post #81 H placement merge).
> Sub-step: H↔C routing (8 DShot signals + GND return on J11.10).

---

## 1. Per-net cluster walk plan

Reference frames:
- J11 anchor (52.5, 80, 0°) — pad row at Y=78.15, X=46.875..58.125 at 1.25mm pitch
- MCU U1 (STM32H743VIT6 LQFP-100) — body 14×14mm centered at (45, 35), pin pitch 0.5mm
- In1.Cu = primary GND plane (full board X=0.5..104.5, Y=0.5..84.5) per DECISIONS §8
- In4.Cu = secondary GND plane (same extent)
- F.Cu primary signal layer

### Pre-existing obstacles in the fanout corridor (X=37..56, Y=42..78)

Surveyed via `pcbnew.LoadBoard().GetTracks()`:

| Y-band | F.Cu nets crossing | Density |
|---|---|---|
| 43..45 (MCU south skirt) | +3V3, I2C2_SDA/SCL, SPI1_MISO/MOSI/SCK | 6 nets |
| 50..52 (D-zone north skirt) | SPI1_MISO, SPI1_SCK | 2 nets |
| 60..62 | — | 0 nets (clear) |
| 70..72 | — | 0 nets (clear) |
| 75..77 (just N of J11) | — | 0 nets (clear) |

| MCU edge | Existing F.Cu nets |
|---|---|
| WEST edge X=35..38, Y=37..45 (MOT3-6 exit) | BATT_CURRENT_SENS, BATT2_VOLTAGE_SENS, BATT2_CURRENT_SENS |
| EAST edge X=51..56, Y=33..40 (MOT7-8 exit) | SPI2_MISO, SPI2_MOSI, SPI3_MISO |

**Net assessment**: corridor Y>52 is essentially clean. All density is
near the MCU edges (Y≤45) and the D-zone north skirt (Y=50..52).
DShot fanout will navigate around 6 nets at Y=43..45 then have a
clear shot south.

### Per-net plan

| Net | MCU pin (X, Y) | J11 pin (X, Y) | Planned F.Cu path | Est. length | In1.Cu GND beneath |
|---|---|---|---|---|---|
| MOT1 | U1.34 (43.00, 42.67) | J11.1 (46.875, 78.15) | S from MCU.34 → bend E gradually → S to J11.1 | ~38mm | Full coverage (In1 full-board) |
| MOT2 | U1.35 (43.50, 42.67) | J11.2 (48.125, 78.15) | S → gradual E → S to J11.2 | ~38mm | Full coverage |
| MOT3 | U1.22 (37.33, 39.50) | J11.3 (49.375, 78.15) | W exit clear of SENSE nets → S corridor X≈37..40 → E at Y=70+ → S to J11.3 | ~50mm | Full coverage |
| MOT4 | U1.23 (37.33, 40.00) | J11.4 (50.625, 78.15) | W exit → S corridor → E at Y=70+ → S to J11.4 | ~51mm | Full coverage |
| MOT5 | U1.24 (37.33, 40.50) | J11.5 (51.875, 78.15) | W exit → S corridor → E at Y=70+ → S to J11.5 | ~52mm | Full coverage |
| MOT6 | U1.25 (37.33, 41.00) | J11.6 (53.125, 78.15) | W exit → S corridor → E at Y=70+ → S to J11.6 | ~53mm | Full coverage |
| MOT7 | U1.59 (52.67, 37.00) | J11.7 (54.375, 78.15) | E exit clear of SPI2/SPI3 → S to J11.7 | ~43mm | Full coverage |
| MOT8 | U1.60 (52.67, 36.50) | J11.8 (55.625, 78.15) | E exit → S to J11.8 | ~43mm | Full coverage |

**Cluster-walk verdict**: every F.Cu DShot segment overlies the
full-board In1.Cu GND plane (PR #76). No In1 anti-pad gaps or splits
in the fanout corridor — In1 is single-net GND with no slots.

### Anti-pad / via clearance hot spots

Vias in the fanout corridor (Y=42..78, X=37..56) per current board:
- MCU C-zone vias (north of fanout, no conflict)
- +3V3_IMU rail vias from PR #78 in bridge column X=46..56, Y=50..65
  area — minimal density (4 vias)
- D-zone SPI vias from PR #77 at X≥56 (D's western edge) — east of MOT
  fanout column, no direct conflict

Per-trace clearance: standard `clearance ≥ 0.20mm` (project default).
Freerouting will respect via clearance automatically; manual review
post-route confirms no fanout trace passes within <0.30mm of any
existing via.

## 2. GND return path for J11.10

J11.10 (GND) sits on F.Cu at (58.125, 78.15). Need to bond to In1.Cu +
In4.Cu GND planes via stitching via(s).

### Coverage verified
- In1.Cu GND zone bbox (0.5, 0.5)..(104.5, 84.5) **COVERS J11.10** ✓
- In4.Cu GND zone bbox (0.5, 0.5)..(104.5, 84.5) **COVERS J11.10** ✓

### Plan
- Add 1× GND stitching via at approximately (59.0, 78.5) — 1mm SE of
  J11.10 pad center, outside pad clearance ring
  - Standard via: 0.6mm drill, 1.0mm pad (project default per
    netclass 'Default')
  - F.Cu landing pad → trace stub to J11.10 (short, ≤1mm)
  - Through-via touches In1.Cu (PRIMARY GND, return current home) +
    In4.Cu (secondary backup) + B.Cu landing pad
- Return-current loop: J11.10 pad → 1mm trace → via at (59.0, 78.5)
  → In1.Cu GND plane → return path under any DShot trace back to MCU pin

### Local loop area minimization
- 1mm trace + 1mm via offset = ~1mm² connection footprint
- No alternate via further away — single tight stitch keeps GND
  return short and tight
- If Freerouting drops its own via within 2mm of J11.10, accept it;
  otherwise add manually per the surgical-via pattern from PR #78

## 3. EMC keep-out from IMU SPI

D zone occupies X=56..86, Y=51..63. All 8 MOT* signal terminations at
X≤55.625 (J11.8 rightmost):

- **No MOT* trace enters D zone footprint** (verified by termination geometry)
- Closest approach is MOT6 fanout at X=53.125 — passes 2.875mm west
  of D west edge X=56 → meets the ≥3mm parallel-trace rule with
  margin (caveat: trace is N-to-S, IMU SPI is mostly inside D zone
  not running parallel along the bridge — perpendicular crossing where
  they meet, no significant length of parallelism)
- MOT7+8 from MCU east X=52.67 → J11.7/8 X=54.375/55.625 — closest
  approach ~3mm W of D west edge → meets ≥3mm rule
- IMU SPI lines (SPI1/2/3) are concentrated INSIDE D zone (X=56..86),
  none running through the MOT fanout column

**Verdict**: zero EMC keep-out violations expected. No parallel
SPI/DShot sections >5mm anywhere on the board.

## 4. Length budgeting (for record only)

DShot300/600 channels are independent — per-channel asynchronous, no
inter-channel skew constraint (per Phase 3f esc_3f.py inheritance from
MatekH743-bdshot).

| Net | Est. F.Cu length | DShot tolerance |
|---|---|---|
| MOT1 | ~38mm | ≪100mm ✓ |
| MOT2 | ~38mm | ✓ |
| MOT3 | ~50mm | ✓ |
| MOT4 | ~51mm | ✓ |
| MOT5 | ~52mm | ✓ |
| MOT6 | ~53mm (max) | ✓ |
| MOT7 | ~43mm | ✓ |
| MOT8 | ~43mm | ✓ |

Spread: 15mm (40% of mean 46mm) — irrelevant since no inter-channel
constraint. All paths well under any signal-integrity practical limit
(~100mm at 600 kbit/s + 5ns edge over F.Cu/GND microstrip).

**No length-matching DRU rule needed**. Documented for future reference.

## 5. NC pin J11.9

J11.9 (VDD_SERVO, Sai-ratified NC) — confirm post-routing:
- No trace touches J11.9 pad
- No via within pad clearance (0.20mm)
- Freerouting won't route to it because the pad has empty net (unbound)
- Visual confirmation in render after layout

## Routing approach

Per master directive + proven surgical-DSN pattern from PR #77/#78:

1. **Scoped DSN export**: 8 MOT* nets only (149 → 8 nets) using the
   established `integ_*_freeroute.py` pattern (scaffolded as
   `integ_h_freeroute.py` this sub-step)
2. **Freerouting CLI**: standard parameters (no time-kill per project
   memory; let SES write naturally)
3. **SES parse + apply**: custom parser pattern (KiCad 9 ImportSpecctraSES
   returns False on scoped DSN — established `apply_*_ses.py` workaround)
4. **GND stitching via** at J11.10: manual add post-Freerouting if not
   auto-dropped
5. **Per-net cluster walk** post-route: confirm In1.Cu GND continuous
   beneath every F.Cu segment

## Gates (5 master + 1 new)

1. DRC ≤ post-PR-#81 baseline (21 errors / 263 unconnected); expect:
   - Errors: 0 net new (8 simple routes shouldn't introduce DRC)
   - Unconnected: −9 (8 MOT* + 1 J11.10 GND closed)
2. STACKUP-SPEC-MATCH PASS (no zone touches)
3. MIRROR_PAIRS 11/11 (A zone untouched)
4. DECOUPLING unchanged (no new ICs; J11 still passive)
5. **NEW per-net check**: each MOT* net has continuous In1.Cu GND
   beneath full F.Cu path (codified as cluster-walk in PR doc)

## Decisions awaiting master sign-off

NONE significant — the geometry was already locked in the H placement
analysis. Specific implementation choices that don't need sign-off but
flagged for record:

- **GND stitching via offset**: 1mm SE of J11.10 pad center recommended
  (alternative: 1mm S, but SE allows shorter trace to In1/In4 planes
  with less interference with neighbor pads). Master can override with
  preferred placement before layout if needed.
- **Routing tool**: Freerouting (scoped DSN, proven pattern). Master
  can request manual-only if preferred but Freerouting saves ~2hr for
  8 simple nets.

## 5-gate verify plan (post-layout)

1. `kicad-cli pcb drc` — confirm errors ≤ 21 (post-PR-#81 baseline) + unconnected ≤ 254 (was 263 − 9)
2. `audit_layout_compliance.py` — STACKUP-SPEC-MATCH, MIRROR_PAIRS, DECOUPLING, ZONE-FILL all green
3. Per-net cluster walk (NEW gate 5): for each of 8 MOT* nets,
   - Walk every F.Cu segment endpoint
   - At each endpoint, check In1.Cu GND zone presence
   - Report continuous-coverage / discontinuity
4. Confirm J11.10 GND now connected (1 unconnected item closed)
5. Confirm J11.9 NC remains unconnected (no spurious trace)

---

**Awaiting master sign-off before layout execution.**
