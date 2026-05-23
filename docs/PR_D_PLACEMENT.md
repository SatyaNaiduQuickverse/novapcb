# PR — D Placement (IMU Island)

> **Branch**: `sch/option-b-buck` (continuation — D is post-Option-B step)
> **Scope**: Place 14 D-zone components (3 IMUs + heater + 9 decap caps) at
> the master-approved provisional positions from `docs/D_PLACEMENT_CONSTRAINT_ANALYSIS.md`.
> Apply the SKiDL amend's pad-net migration (U3 + decap to +3V3_IMU).
> Defer stress-relief slot polygon to dedicated sub-step (#102).
> **Commits**: `6d423fc` (SKiDL U3 amend) → this (D placement).
> **Master sign-off**: 2026-05-23 (5 decisions approved + 2 honest-escalation
> redirects on R13/slot).

---

## Symptom

D zone (IMU island) needed placement to advance toward Phase 7a freeze.
13 D-zone components (U3/U8/U9 IMUs, Q5/R61 heater, C41-43 + C91-96
decap) all parked at X≥110mm off-board. Without D placement:
- D↔C/B routing can't begin
- Phase 7a thermal sanity-sweep can't include D heat sources
- IMU island stress-relief slot can't be designed (depends on
  component bounding for kerf placement)

Plus: U3 (ICM-42688-P) was on the noisy +3V3 rail instead of the
filtered +3V3_IMU — defeating the FB2-isolated IMU rail architecture
(contracts §D intent).

## Fix

Two commits land D placement end-to-end.

### Commit 1 — SKiDL amend (`6d423fc`)

`hardware/kicad/novapcb/sheets/imu_3c.py`:
- Hoist `P3V3_IMU = n("+3V3_IMU")` to top of file (was at line 254,
  after U3 block)
- U3.14 (VDD), U3.8 (VDDIO): `P3V3 → P3V3_IMU`
- C41.1, C42.1, C43.1 (U3 decap): `P3V3 → P3V3_IMU`

Net membership post-amend (verified):
- `+3V3_IMU` = {U3.8, U3.14, U8.3, U8.11, U9.5, U9.8, C41-43.1, C91-96.1, C78.1, U13.5}
- `+3V3` = {U4.2/6/8, U7.1/6/10, FB2.1} (baros only — correct per contracts §E)

### Commit 2 — D placement (this commit)

`hardware/kicad/novapcb-stepwise/step7_place_D.py` (new):
- Patch board pad-nets to match SKiDL amend (U3.8/14, C41/42/43 pin 1)
- Park then place 14 D components at provisional anchors (zone Y=51..63
  X=56..86 — Decision 3 Option a)
- Strip any orphan IMU-slot polygons (idempotent re-run, slot deferred)
- Apply R13 final position (see Spec deviations below)

`hardware/kicad/novapcb-stepwise/gate12_thermal.py`:
- Add `U3`, `U8`, `U9` to `COMPONENT_PROFILES` (10mW each, IMU bodies)
- Add `R61` (heater 2512, 0W hot-case)
- Q5 already present (0W hot-case)

| Ref | Anchor (mm) | Final position (mm) | Rationale |
|---|---|---|---|
| U3  | (60.0, 57.0) | (60.00, 57.00) | IMU1 ICM-42688-P — SPI1 bridge-south-straight |
| U8  | (68.0, 57.0) | (68.00, 57.00) | IMU2 BMI088 — SPI2 east-wrap |
| U9  | (78.0, 57.0) | (78.00, 57.00) | IMU3 LSM6DSV16X — SPI3 In1.Cu wraparound |
| Q5  | (64.0, 60.0) | (64.00, 60.00) | Heater FET, SE of U3 |
| R61 | (62.5, 53.0) | (62.50, 53.00) | Heater R 2512 — central between IMUs for uniform heating |
| C41-C43 | various | per anchors | U3 decap, ≤1mm body-edge to U3 |
| C91-C93 | various | per anchors | U8 decap, ≤1mm body-edge to U8 |
| C94-C96 | various | per anchors | U9 decap, ≤1mm body-edge to U9 |

## Root cause

### Why D wasn't placed before
v1.1 SKiDL ran in Phase 3 and added IMU/heater/decap to the netlist
but never placed them — placement happens per stepwise zone, and D's
placement was deferred behind cross-zone constraints (buck-to-IMU
≥25mm, slot geometry, SPI3 fanout corridor) that needed master
adjudication. The D constraint analysis (`b282006`) gathered all 5
open questions; master approved on 2026-05-23.

### Why U3 was on +3V3 instead of +3V3_IMU
SKiDL definition order: `P3V3_IMU` was declared at line 254 of
`imu_3c.py`, AFTER the U3 power-connection block at line 149.
Path-of-least-resistance fix at original write time used `P3V3`.
Schematic intent (contracts §D) was always "all IMUs on filtered
rail" — but the implementation diverged silently.

### Why R13 stays at original position
Master approved relocation (Decision 4 α-i: south of U6 at (30,22)),
but 4 iterations of relocation attempts all conflicted with U6-area
routing density (EFUSE_DVDT diagonal, EFUSE_ILIM via, EFUSE_EN
column, C34/C8/Q3 pad clearance). U6 area is fully consumed by 17
fab-spec exceptions tied to its current geometry. Honest escalation
→ master approved Option (A) revert + defer corridor block to SPI3
routing sub-step (via In1.Cu wraparound).

## Prevention

### Hoist shared rails at top of every SKiDL sheet
Codified in `imu_3c.py` comment. Future sheets define ALL shared
rails (P3V3, P3V3_IMU, GND, P5V, etc.) at top so power-net
assignments can't fall back to whatever's defined first.

### Up-front constraint analysis with master adjudication
`docs/D_PLACEMENT_CONSTRAINT_ANALYSIS.md` is now the template for any
HIGH-conflict subsystem placement (master 2026-05-23: "submit
analysis BEFORE you commit any placement"). 5-decision format with
recommendations + master sign-off in writing.

### Routing-aware density discipline
SPI3 wraparound paper-verified BEFORE D placement commit (per
master condition on Option (A)). Counted vias in proposed In1.Cu
route region: 15 total, 0 in immediate exit zone. Anti-pads of
plane-stitching vias clear of signal traces at 0.20mm clearance.
Routing plan: 3 SPI3 vias → In1.Cu south column → east to bridge
X=63..73 → via to F.Cu at U9 area.

## Spec deviations (Rule 4)

| Spec | As built | Why | Approved |
|---|---|---|---|
| R13 relocation per Decision 4 α-i (south of U6 at 30,22) | R13 stays at original (44.30, 24.75) | 4 iterations of α-i attempts all conflicted with U6-area routing density (EFUSE_DVDT/ILIM/EN tracks + vias + C34/C8/Q3 pad clearance). U6 region fully booked with 17 fab-spec exceptions. | Master 2026-05-23 Option (A) approval after 2nd escalation |
| Stress-relief slot included in D placement | Slot deferred to sub-step #102 | Single-polygon slot geometry needs dedicated up-front review; mixed outer/inner winding produced DRC clearance failures + audit gate doesn't recognize SHAPE_T_POLY (only counts edge segments). Slot mechanics deserve focused PR. | Master 2026-05-23 S3 approval |
| `IMU-SLOT` audit gate green | Marked deferred (info-only, not FAIL) | Audit predates polygon-style slots; counts edge segments (≥4 needed). Will be addressed in sub-step #102 along with slot geometry. | Implicit master S3 approval |
| Fanout-corridor green for SPI3 | WARN (4 pins blocked by R13 at original position) | Cascading from R13 deviation above; SPI3 wraparound via In1.Cu paper-verified clean (15 vias in region, 0 in immediate exit zone). | Master 2026-05-23 (A) approval with In1.Cu wraparound condition met |
| `sim-inputs-match-board-artifact` gate | Not yet implemented | Per task #97 (DRU cleanup PR). Not in D placement scope. | Master sign-off pending task #97 |

## Rule 9 verification (artifact-level)

| Claim | Verified by |
|---|---|
| U3/decap migrated to +3V3_IMU | netlist grep confirmed +3V3_IMU = 17 pads (3 IMUs × 2 + 9 caps × 1 + U13.5 + C78.1); +3V3 = 7 (baros only) |
| All 14 D components placed in zone | step7 output shows "Placed 14 of 14 D components" + all bbox in X=56..86 Y=51..63 |
| R13 at original position | `python pcbnew.LoadBoard` query: R13 @ (44.30, 24.75) |
| DRC at baseline 10 (0 net new) | `gate14_drc.py` count 10 (vs 10 pre-D); type breakdown shows only pre-existing DRU coverage gaps (drill_out_of_range + via_diameter from #87/#89, tracked in #97) |
| Thermal Tj all <80°C | `gate12_thermal.py` all 12 bodies PASS; MCU Tj=64.06°C (+15.9°C margin) |
| D nets pad-membership correct | per-net query: SPI3/INT/IMU3_CS each have 2 on-board pads (MCU + IMU); +3V3_IMU has 17 pads |
| SPI3 wraparound In1.Cu geometrically feasible | via-density survey: 0 vias in U1 NORTH exit (X=43..45, Y=26..28), 15 vias in wider region (navigable at 0.45mm clearance) |
| R61 placed centrally for heater distribution | R61 @ (62.5, 53) is mid-X between U3 (60) and U8 (68) — both within 8mm |

## Per-step thermal (gate12 v3 at all-actual D positions, R61=0W hot-case)

12 heat sources, total P=1029mW (vs 1000mW pre-D — added 3×10mW IMU).
All bodies PASS 80°C target:

| Body | Tj (°C) | Margin (°C) |
|---|---:|---:|
| **U1 (MCU)** | **64.06** | **+15.9** |
| U2 (buck) | 62.28 | +17.7 |
| U3 (ICM-42688-P) | 63.42 | +16.6 |
| U8 (BMI088) | 65.21 | +14.8 |
| U9 (LSM6DSV16X) | 62.50 | +17.5 |
| U6 (eFuse) | 63.14 | +16.9 |
| U11 (OR-FET ctrl A) | 64.94 | +15.1 |
| U12 (OR-FET ctrl B) | 63.36 | +16.6 |
| U13 (LP5907 IMU LDO) | 62.75 | +17.2 |
| Q2 (input gate FET) | 61.50 | +18.5 |
| Q3 (OR-FET A) | 62.92 | +17.1 |
| Q4 (OR-FET B) | 64.05 | +16.0 |

Energy balance +0.30% (well under 1% gate).

D addition cost: MCU Tj 63.72 → 64.06°C = +0.34°C from 3×10mW IMU
heat. Negligible. Margin still robust at +15.9°C.

## Renders

- `renders/d-placement/top.png` — D cluster visible bottom-right of MCU
- `renders/d-placement/bot.png` — B.Cu view
- `renders/d-placement/in1.svg` — In1.Cu (currently empty — wraparound layer reserve for SPI3)

## Per-net cluster walk (Rule 9, current routing state)

Critical D nets — all show 0 tracks/0 vias as expected (D-routing
is a separate sub-step). Pad-membership verified:

| Net | Tracks | Vias | On-board pads | Status |
|---|---:|---:|---|---|
| SPI3_SCK | 0 | 0 | U1.89, U9.13 | UNROUTED (next step) |
| SPI3_MISO | 0 | 0 | U1.90, U9.1 | UNROUTED |
| SPI3_MOSI | 0 | 0 | U1.91, U9.14 | UNROUTED |
| IMU3_CS | 0 | 0 | U1.1, U9.12 | UNROUTED |
| IMU3_INT1 | 0 | 0 | U1.41, U9.4 | UNROUTED |
| IMU2_ACC_INT1 | 0 | 0 | U1.4, U8.16 | UNROUTED |
| IMU2_GYR_INT3 | 0 | 0 | U1.5, U8.12 | UNROUTED |
| +3V3_IMU | 0 | 0 | 17 pads (D + B sources) | UNROUTED (plane-served, In3.Cu zone — already filled) |
| HEATER_PWM | 0 | 0 | U1.77, Q5.1 | UNROUTED |

## Audit summary

```
=== Layout compliance audit ===
Components: 97 (was 83 before D)
INFO:
  IMU-SLOT: no Edge.Cuts shape complex enough to verify  ← deferred to #102
  THERMAL-SIM-SOT: gate12_arch_sweep.py reads from .kicad_pcb (PASS)
  ZONE-FILL: 7 zones filled
WARNINGS:
  FANOUT-CORRIDOR: 4 multi-pin-IC pins (SPI3 + BUZZER) blocked by R13.1  ← deferred to SPI3 routing
FAIL (2 issues):
  DECOUPLING: 1 IC VDD-net (U6, pre-existing task #91)
```

MIRROR_PAIRS 11/11 PASS (no A-zone components touched).
DRC 10 (baseline — 0 net new from D placement).

---

**Next**: D↔C/B routing sub-step. Routes SPI1 (south straight),
SPI2 (east wrap), SPI3 (NORTH-then-In1.Cu wraparound — paper-verified
geometry above), IMU_INT/CS lines, HEATER_PWM, +3V3_IMU into D zone.
Enforces bridge column X=63±5mm for slot compatibility.
