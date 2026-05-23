# IMU Stress-Relief Slot — Up-Front Constraint Analysis

> **Status**: DRAFT for master review. NO LAYOUT TOUCH per master
> 2026-05-23. Branch `hw/imu-slot-polygon` off `sch/option-b-buck`
> head `ba7e28c`. Sub-step #102 (deferred from D placement).
> **Stakes**: HIGH — board-geometry change (Edge.Cuts cutout) that
> would break existing routes from PR #77 (D-routing) + PR #78
> (+3V3_IMU rail). Paper review > layout patch rounds.

---

## 1. Slot purpose

U-kerf cutout in board substrate to **mechanically isolate the IMU
island** (D zone X=56..86 Y=51..63) from board flex / vibration paths
caused by:
- Mounting-hole bolt torque + thermal cycling
- Frame vibration during flight (motor RPM, prop imbalance)
- ESC switching shock loads

Reference designs: Pixhawk 6X uses a SEPARATE IMU PCB mechanically
isolated (v2 mech target for novapcb). v1 emulates this with the
slot + bridge pattern. mRo Control Zero, Matek H743-Slim use similar
slot-around-IMU-island geometry.

Isolation mechanism: slot creates a flex break in the substrate so
mechanical strain from the main board doesn't transfer to the IMU
mounting plane. The bridge(s) provide controlled mechanical coupling
+ electrical signal paths.

## 2. Slot geometry — master's proposed reference

Per master 2026-05-23 D-placement-analysis doc + sub-step kickoff:

- **W cut**: vertical, X≈54, Y=33..63 (creates west isolation)
- **E cut**: vertical, X≈88, Y=33..63 (mirror east)
- **N span**: horizontal Y≈33, X=54..88, with BRIDGES (gaps) at
  specific X-positions where traces + mechanical attachment exist
- Slot width: 1-2 mm (JLC fab minimum + tolerance)
- Bridge widths: ≥3 mm each for mechanical integrity
- Slot is OPEN at SOUTH (no S cut) — D zone connects to south of
  board through Y=63 free area

Inverted-U shape opening downward. D zone isolated on N/W/E; bridges
on N at chosen X-positions.

**Bridge column agreed in prior PRs**: X=63±5mm (i.e., X=58..68) —
established as the single trace-crossing channel in D placement
analysis (b282006), reaffirmed in PR #77 + PR #78 (post-route bridge
census 6/14).

## 3. Existing-route impact analysis — CRITICAL FINDING

Survey of routes crossing the proposed slot boundary (per the 4
slot-line segments, excluding the bridge gap X=58..68):

| Slot segment | F.Cu nets crossing | B.Cu nets crossing | Total |
|---|---|---|---|
| W cut (X=54, Y=33..63) | IMU1_CS, IMU2_ACC_CS, IMU3_CS, IMU3_INT1, SPI1_MISO, SPI1_SCK, SPI2_MISO, SPI2_MOSI, SPI2_SCK (9) | HEATER_PWM, IMU2_ACC_INT1, IMU2_GYR_CS, IMU2_GYR_INT3, SPI1_MOSI, SPI3_MISO, SPI3_MOSI (7) | **16** |
| E cut (X=88, Y=33..63) | (none) | (none) | **0** |
| N span W-half (Y=33, X=54..58) | (none) | SPI3_SCK (1) | **1** |
| N span E-half (Y=33, X=68..88) | (none) | +3V3_IMU (1) | **1** |

**18 net crossings total outside the bridge** (W cut + N span outside
bridge column). These are all routes from PR #77 (D-routing) + PR #78
(+3V3_IMU) — every D-target net plus +3V3_IMU.

### Root cause of impact

D-routing PR #77 was run with Freerouting WITHOUT the slot as a
constraint. Routes took shortest paths from MCU (centered at X=45) to
D zone (X=56..86 Y=51..63) — many crossing X=54 directly.

PR #77 deliberately routed SPI3 via wraparound past R13 — but other
nets took direct paths because R13 wasn't in their way.

Bridge column X=63±5mm was reserved per analysis #100 + verified
post-PR by census (6/14 net slots used). But the OTHER nets weren't
constrained to use only the bridge — they took faster direct paths.

### Impact classification

| Category | Count | Action required |
|---|---:|---|
| PRESERVED (cross only at bridge X=58..68 within Y=33) | 6 | none — already use bridge correctly (the 6/14 census) |
| **NEEDS RE-ROUTE** (cross W cut at X=54) | **16** | route through bridge column X=58..68 OR wrap around N (Y<33) — re-route effort moderate to high |
| NEEDS RE-ROUTE (cross N span outside bridge) | 2 | shift north-crossing X to within bridge column — minor edit |

Total: **18 nets need re-routing** to comply with master's proposed
slot geometry. That's most of the D-routing work undone.

## 4. Zone impact

Slot is a board-substrate cutout (Edge.Cuts) — removes copper on ALL
layers in the slot footprint.

Slot footprint dimensions (master proposal):
- W cut: 2mm wide × 30mm tall = 60 mm²
- E cut: 2mm wide × 30mm tall = 60 mm²
- N span: 34mm wide × 2mm tall × (1 − bridge_fraction)
  with bridge X=58..68 (10mm) → 24mm cut at Y=33
  = 48 mm² (24mm × 2mm slot width)
- **Total slot area ≈ 168 mm²**

Zone coverage drop:

| Zone | Pre-slot | Post-slot (est) | Drop |
|---|---:|---:|---:|
| In1.Cu GND | 8494 mm² | 8326 mm² | -2.0% |
| In2.Cu +5V_BEC | 2435 mm² | ~2435 mm² | ~0% (south of slot) |
| In3.Cu +3V3 | 7989 mm² | ~7821 mm² | -2.1% |
| In4.Cu GND | 8494 mm² | 8326 mm² | -2.0% |

**GND coverage drop 2%** — small enough that return-current integrity
is preserved for routes crossing the BRIDGE. Bridge GND coverage on
In1 + In4 at X=58..68 Y=32..34 is intact (~20 mm²).

### Return-current bridge check
For each NEEDS-RE-ROUTE net, its new path must:
- Cross slot ONLY at bridge X=58..68 Y=33
- Have In1.Cu GND continuous beneath if F.Cu
- Have In4.Cu GND continuous beneath if B.Cu

Bridge GND coverage at X=58..68 Y=32..34 = ~20 mm² per layer (10mm
bridge × 2mm tall). Sufficient for return currents at ≤30mA per net.

## 5. Audit-gate updates needed

Current `IMU-SLOT` audit gate: info-only ("no Edge.Cuts shape complex
enough to verify"). Make it ACTIVE per master directive:

```python
def check_imu_slot():
    # 1. Slot polygon present on Edge.Cuts
    # 2. No signal traces cross slot boundary outside bridge gap
    # 3. Bridge widths >= 3mm each (mechanical integrity)
    # 4. GND return-current path: each bridge has GND on >=1 inner layer
```

New audit checks:
- Slot polygon vertex count > 4 (rectangles ≤ 4)
- For each (F.Cu, B.Cu) net crossing the slot polygon, verify only at
  bridge X-coordinates (configurable list)
- For each bridge, verify width ≥3mm
- For each bridge, verify In1.Cu and/or In4.Cu zone fill present in
  bridge footprint

## 6. Thermal impact

Slot reduces board copper area by ~3% (slot area / total area).
Lower copper = slightly less in-plane heat spreading.

Direction: MCU Tj likely +0.1-0.5°C (conservative). Negligible vs
current +15.9°C margin.

Predicted re-run: MCU Tj 64.06°C → 64.1-64.5°C. Action: re-run
gate12 post-slot to confirm direction. Not a blocker.

## 7. Options analysis (the real ask)

Given 18 nets need re-routing for master's proposed geometry, four
paths forward:

### (A) Re-route 18 D nets to use only N-span bridge
- Effort: ~2-4 hours (full re-run of Freerouting with slot as obstacle,
  manual cleanup for any wraparounds)
- Result: master's proposed geometry achieved
- Risk: bridge column saturation — 6 nets already + 18 more = 24 nets
  in 14-slot capacity (master's earlier threshold). EXCEEDS CAPACITY.
- Verdict: **Bridge X=58..68 (10mm) cannot handle 24 nets** at standard
  trace+clearance. Would need WIDER bridge (≥15-20mm) or MULTIPLE bridges.

### (B) Revise slot — multiple bridges to absorb existing routes
- Keep W cut + E cut + N span topology
- Add bridges at X positions matching existing route columns
- Survey shows F.Cu west-side routes use X=37.33-46.50 column (MCU
  west edge fanout); B.Cu west routes use X=43-50 column
- Need bridges at: (1) X=37..47 — MCU west fanout, (2) X=58..68
  (existing bridge), (3) X=83..88 (if any east routes used)
- 2-3 bridges total. Each ≥3mm wide.
- Effort: minimal re-route (most nets fit through new bridges)
- Risk: more bridges = less mechanical isolation. Mechanically
  acceptable if 3 bridges total (still significantly stiffer than
  no slot)

### (C) Revise slot — W cut moved INWARD to X=56 (D zone west edge)
- W cut at X=56 (right at D west edge) instead of X=54
- All routes that currently end inside D at X≥56 with their last
  segment NOT crossing X=56 boundary already... hmm but most routes
  END at IMU pads which are at X=60+. The TRANSIT into D crosses
  X=56 too. Same problem.
- Doesn't help.

### (D) Skip W cut entirely — U-shape opens WEST instead of SOUTH
- Slot = E cut (X=88 Y=33..63) + N span (Y=33 X=63..88) + S cut
  (Y=63 X=63..88) — three sides
- D zone open to WEST (no W cut) — all west-entry routes preserved
- E/S/N cuts isolate east + south + north sides
- Loses west-side mechanical isolation (board flex from west would
  reach D via the X=56..63 connection)
- Less ideal mechanically but vastly less rework
- Probably acceptable since main flex direction is BENDING (Y-axis,
  not X-axis lateral)

### (E) Defer slot to v2 (no slot in v1)
- v1 ships without IMU mechanical isolation
- Rely on rubber-foot mounting + foam damping for vibration isolation
- Accepted tradeoff for FC v1 (this is what many low-end FCs do)
- v2 (FMUv6X mechanical drop-in) gets full Pixhawk-style isolation
- Effort: 0
- Risk: degraded IMU noise floor under vibration (gyro/accel pickup
  motor harmonics)
- Mitigation: software-side digital low-pass filter in ArduPilot

## 8. Recommendation

**(B) Revise slot — multiple bridges**: 3 bridges at X=37..47 + X=58..68
+ X=83..88 (if needed for any east routes that turn out to exist when
we look more carefully). 2 bridges if east-side count is 0 (it is per
survey).

Reasoning:
- Preserves master's slot architecture intent (3-sided isolation +
  bridge crossings)
- Minimizes re-route work (most nets fit existing column patterns)
- Mechanical isolation only slightly degraded vs 1-bridge (3 bridges
  total, ~10-15mm bridge area, vs 10mm with 1 bridge)
- 14-slot trace bandwidth preserved per bridge (each bridge holds
  ~14 nets in F+B layers)

Alternative: **(D) Skip W cut** if mechanical analysis shows board
flex is primarily Y-axis (which is intuitive for prop-mounted FC).
Simpler, but loses mechanical isolation in one dimension.

NOT recommended:
- (A) — exceeds single-bridge capacity, would need bridge widening
  anyway
- (C) — same root problem as (A)
- (E) — loses vibration isolation entirely

## 9. Decisions awaiting master sign-off

1. **Slot architecture**: which of (A)/(B)/(C)/(D)/(E)? Recommend (B).
2. **If (B) — bridge positions + counts**: my proposal: X=37..47
   (MCU west fanout) + X=58..68 (existing) + optionally X=83..88
   (east fanout). 2-3 bridges total.
3. **Slot width tolerance**: 1mm vs 2mm? 1mm = better mechanical
   isolation (more flex break); 2mm = fab-tolerance friendly. JLC
   minimum slot width is 0.8mm.
4. **Bridge minimum width**: 3mm proposed (master directive). Confirm
   or adjust (4mm gives more mech margin)?
5. **Audit gate strictness**: just verify polygon presence + bridge
   widths, or also verify no-trace-crosses-slot-outside-bridge?
   Recommend strict (catch routes that bypass bridges).
6. **If (B) — re-route plan**: even with 2-3 bridges, some routes may
   not naturally use them. Need to RE-RUN Freerouting with slot as
   obstacle? Or selective manual re-route of the routes that don't
   currently fit any bridge column?

## 10. Open after sign-off

If master approves (B) + bridge plan:
- Implement Edge.Cuts polygon for slot
- Re-run audit + verify no slot-boundary trace crossings outside bridges
- Update `IMU-SLOT` audit gate to active per §5
- DRC + audit + thermal + render
- PR doc 4-section

If master picks (D) or (E), much simpler — just adjust slot geometry
or skip + document.

---

**No layout touch until master sign-off on §9 decisions.**

---

# Amendment — master 2026-05-23 decisions baked in

## All 6 decisions confirmed

| # | Decision | Choice |
|---|---|---|
| D1 | Slot architecture | **(D) U-opens-west** — preserves PR #77/#78 routes, v1 mech-isolation is "add if no churn" not load-bearing |
| D2 | Bridge placement for N-span crossings | Primary X=58..68 + per-net judgment for the 2 misfits |
| D3 | Slot width | 1mm |
| D4 | Bridge min width | 3mm |
| D5 | Audit gate strictness | STRICT (4 criteria, FAIL not WARN) |
| D6 | Re-route approach | SELECTIVE MANUAL (preserve PR #77/#78 routes, manual re-route 2 misfits) |

## Final slot geometry (D + decisions)

```
Slot lines (Edge.Cuts polygons, 1mm width):
- N span: Y=33, X=53..88, with BRIDGE GAP at X=58..68 (10mm wide)
  → 2 sub-segments: (53..58) west of bridge, (68..88) east of bridge
- E cut:  X=88, Y=33..65 (vertical)
- S span: Y=65, X=53..88 (no bridge — south of board has no connections)
Open west: X=53 west edge has no slot cut — D zone connects to board
  via X=53..56 (3mm coupling band).

Bridge:
- X=58..68 (10mm wide) at Y=33
- Minimum mechanical width 3mm verified
- GND coverage In1.Cu + In4.Cu present at bridge (8494mm² zones cover X=58..68 Y=32..34)
```

D zone (X=56..86 Y=51..63) sits inside the ⊏ enclosure. Open mouth on
west (X=53 line). North connection only through bridge X=58..68.

## Per-net plan for the 2 N-span crossings

Exact crossing X-coordinates (post-survey):

1. **SPI3_SCK** (B.Cu) — segment (73.90, 50.56) → (50.57, 27.23) crosses Y=33 at **X=56.34**
   - Currently in N-span W-half (X<58, outside bridge)
   - Plan: **manual re-route, shift +1.66mm east** to cross at X=58 (bridge west edge)
   - Effort: replace 1 segment endpoint OR insert intermediate vertex at (58, 33) — minor edit
   - Approach: delete the existing crossing segment, replace with a 2-segment path that detours via X=58 at Y=33

2. **+3V3_IMU** (B.Cu) — segment (65.93, 27.92) → (75.00, 37.00) crosses Y=33 at **X=71.01**
   - Currently in N-span E-half (X>68, outside bridge)
   - Plan: **manual re-route, shift -3.01mm west** to cross at X=68 (bridge east edge)
   - Effort: similar — insert detour vertex at (68, 33) via 2-segment replacement
   - Approach: same as SPI3_SCK pattern

Both crossings are MINOR shifts (1.66mm and 3.01mm). No layer changes needed.

## Layout execution sequence (resumed per master 2026-05-23)

1. Define slot polygon on Edge.Cuts (3 sub-polygons: N-W-half + N-E-half + E + S — actually 3 separate Edge.Cuts polylines/segments since slot opens west)
   - Alternative: 1 closed polygon for the ⊏ shape with proper vertex ordering
2. Re-fill all zones (UnFill → Fill → SaveBoard) — slot cuts copper everywhere
3. Manually re-route SPI3_SCK + +3V3_IMU crossings (use existing B.Cu, just shift X via intermediate vertex)
4. gate12 thermal sanity re-run (expect +0.1-0.5°C MCU rise, conservative)
5. Audit gate flip: `IMU-SLOT` info-only → ACTIVE with 4 STRICT criteria per D5

## Updated audit gate spec (D5 STRICT)

```python
def check_imu_slot():
    # STRICT criteria — all 4 must PASS, else FAIL the gate (not WARN)
    # 1. Slot polygon present on Edge.Cuts at the (D)-architecture coords:
    #    N-W (53..58, 33), N-E (68..88, 33), E (88, 33..65), S (53..88, 65)
    # 2. No signal traces cross slot outside the defined bridge X=58..68
    #    (iterate all PCB_TRACK on F.Cu/B.Cu; for each crossing slot line,
    #    require X in [58, 68] at Y=33 crossing)
    # 3. Bridge width >= 3mm at all measured cross-sections
    # 4. GND coverage continuity: each bridge has In1.Cu or In4.Cu zone
    #    fill area >= bridge_width × 1mm beneath the bridge footprint
```

## 5 master merge gates (mapping to this PR)

1. DRC ≤ baseline 10 (0 net new) — verify slot doesn't introduce edge-clearance fails
2. STACKUP-SPEC-MATCH PASS (unchanged — no zone net/layer changes)
3. MIRROR_PAIRS 11/11 PASS (no A-zone touched)
4. DECOUPLING unchanged (no D-zone caps touched)
5. **NEW: IMU-SLOT ACTIVE PASS** (4 criteria above)

---

**Ready for layout execution.** Next commits on this branch:
- Slot polygon + zone refill
- 2 manual re-routes (SPI3_SCK + +3V3_IMU)
- Audit gate update
- PR doc

