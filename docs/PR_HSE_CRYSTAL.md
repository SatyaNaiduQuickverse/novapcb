# PR — HSE crystal optimization: Y1 rotation + caps + IMU1_CS off-crystal + p2/p4 grounding (task #26)

> Branch `hw/hse-cap-optimization` off `sch/option-b-buck`. Full crystal-pocket
> re-layout: relocates the HSE load caps to ≤1.5 mm of Y1, routes the
> (previously unrouted) HSE_IN/HSE_OUT, moves the IMU CS verticals west to open
> the pocket, takes IMU1_CS off the crystal body, and grounds Y1's case pads.
> **Layout only — no schematic / netlist change.**

## 1. What changed

**Y1 crystal rotated 180° (rot90 → rot270, center unchanged at 33.04,34.75):**
- A quartz crystal in OSC mode is a symmetric 2-terminal device — the OSC_IN/OUT
  labels are MCU-side, the crystal doesn't care which terminal is which. The
  180° rotation swaps which pad faces which MCU pin, **uncrossing** HSE_IN/HSE_OUT
  (MCU pin order N→S is HSE_IN/HSE_OUT; pre-rotation the crystal pads were the
  opposite, forcing a crossing). Electrically neutral (no f/amplitude/startup/
  load change); no schematic change (pad nets unchanged, only positions rotate).

**HSE load caps placed ≤1.5 mm of their crystal terminals (was 4–5.5 mm):**
- C24 (HSE_IN) → (32.20,31.80), 1.5 mm from Y1 HSE_IN pad (NW).
- C25 (HSE_OUT) → (35.25,36.00) rot270, 1.4 mm from Y1 HSE_OUT pad (SE).
- Both **outside** the Y1 courtyard (the earlier ≤0.8 mm scan was an artifact —
  it measured to crystal *pads*, but Y1's body is 1.74–34.34 mm wide, so sub-mm
  spots were inside the can). ≤1.5 mm is the honest clean value, well within the
  ≤3 mm ST AN2867 target.

**HSE_IN / HSE_OUT routed on F.Cu (were 0 tracks — unrouted):**
- HSE_OUT: U1.13 → C25 → Y1 SE pad. Clean F.Cu.
- HSE_IN: U1.12 → gate (between Y1 GND pad p4 and the +3V3 via) → west lane →
  Y1 NW pad + C24 tap. **The gate was previously blocked by IMU1_CS** (see below).

**IMU1_CS taken off the crystal (ST AN2867) + IMU CS verticals moved west:**
- IMU1_CS had an F.Cu segment running at Y34.75 **straight under the crystal
  body** (X31.67→34.48) — a foreign switching net under the oscillator. Rerouted
  to B.Cu (shielded by the In1 GND plane) for the crystal crossing, surfacing in
  the opened west gap, bent **south of p4** so p4 can be grounded.
- IMU3_CS vertical 30.89 → **29.4**, IMU1_CS vertical 31.29 → **29.8** (Rule 20:
  slow GPIO, no length constraint). This opens the crystal's west edge so
  IMU1_CS can surface cleanly **and** clears the gate for HSE_IN.
- 2 GND stitching vias relocated west (29,32)+(30,40) → (28.3,32)+(28.7,40) to
  clear the shifted verticals.

**Y1 case-GND pads (p2/p4) grounded (pre-existing defect, fixed here):**
- With no outer-layer GND pours, Y1's case pads were floating (no via to the GND
  plane) — an EMC defect. Added GND vias on p2 and p4 (p4 placed clear of the
  IMU1_CS B.Cu that passes south of it).

## 2. Why this was one atomic PR (channel-sharing, not procedural coupling)

HSE_IN and IMU1_CS-off-crystal are **physically inseparable**: HSE_IN routes
through the exact gate that IMU1_CS occupied. Reverting the IMU1_CS reroute
re-blocks HSE_IN (proven — that is why HSE was never routed). A functional
crystal needs HSE_IN, so the IMU1_CS move had to land in the same PR. Same
pattern as CAN PR #99 (route + FB2 move + remaps all atomic when dependencies
are physical).

## 3. Verification (5-gate)

| Gate | Result |
|---|---|
| DRC | **0 new violations** (apples-to-apples vs HEAD-refilled baseline 31; this board = 21, all 21 pre-existing J/mounting/power = task #97 set). Re-layout **resolved 8** baseline violations. Crystal/W-margin area = **0** violations. |
| STACKUP-SPEC-MATCH | **PASS** (4 plane (layer,net) pairs match DECISIONS.md §8) |
| MIRROR / DECOUPLING / audit | **PASS** — all layout-compliance checks clean (no new warnings) |
| Connectivity | HSE_IN, HSE_OUT, IMU1_CS, IMU3_CS **all fully connected** (0 ratsnest each; IMU reroutes intact end-to-end) |
| Cluster walk | Crystal Pierce loop (Y1+C24+C25) over **solid In1 GND** ✓. HSE transport traces graze the gate-crossing void — see Prevention §2. |

## 4. Prevention / engineering notes

1. **Crystal Pierce loop integrity** — Y1 + C24 + C25 sit over **solid In1 GND**.
   This is the SI-critical resonant feedback path and it is properly grounded.
2. **HSE_IN/OUT gate-crossing** — the ~1.5 mm MCU↔crystal transport routes over
   the +3V3 decap region (X34.6–36) where In1/In4 GND are voided (In3 carries
   +3V3 there). Acceptable at 8 MHz fundamental: the +3V3 plane provides AC
   return via plane capacitance + bulk decaps. It is the **only** MCU→crystal
   path (saturated pocket — verified on all four sides). Comparable to production
   single-board FC HSE routing (e.g. Pixhawk 6X).
3. **GND void 40%→76% (in the X34.6–36 box) explanation** — benign zone-fill
   recomputation: relocating the GND stitching vias west removed their anti-pads
   from the In3 +3V3 plane, so +3V3 filled into the freed area (including the
   gate region), raising the GND void *from HSE's perspective*. **In1 GND total
   area is essentially unchanged** (8379→8372 mm², one continuous polygon). No
   real plane gap; not a defect.
4. **ST AN2867 compliance** — no foreign switching net under the crystal body
   (the IMU1_CS reroute goal — achieved; it is now on B.Cu, shielded by In1 GND).
5. **Rule 18/19/20** — fanout-corridor + existing-route surveys before routing;
   passive/slow-GPIO mobility used (IMU CS verticals, stitching vias) to open the
   pocket rather than fighting it.
6. **Rule 9 self-correction (process note)** — an earlier "split IMU1_CS to a
   follow-up" plan was geometrically impossible (HSE_IN/IMU1_CS share the gate).
   Caught by verifying the artifact (channel geometry) rather than reasoning from
   prose. Single atomic PR is the correct response to physical coupling.

## 5. Spec deviations

- **Cap distance** — ≤1.5 mm achieved (not the optimistic ≤0.8 mm), because the
  caps must clear the Y1 courtyard. Still well inside the ≤3 mm ST target.
- None other. No schematic / netlist change; ERC unaffected.
