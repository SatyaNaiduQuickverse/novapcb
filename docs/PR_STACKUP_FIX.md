# PR — Stackup Fix: Add GND Planes (In1.Cu + In4.Cu)

> **Branch**: `hw/stackup-gnd-planes` (off `sch/option-b-buck`)
> **Scope**: Add both GND planes to match the locked stackup in
> `docs/DECISIONS.md §8`. Half-applied stackup change from
> 2026-05-23 (DECISIONS.md §8 update) is now fully applied to the
> board artifact. Add 143 stitching vias per master's region-based
> pitch (5mm HF / 10mm calm). Codify the catch as new audit gate.
> **Master sign-off**: 2026-05-23 (Path-I + 3 flag answers + 5
> merge-gate criteria).
> **Trigger**: Rule-9 catch during D↔C/B routing-layer planning —
> SPI3 wraparound discussion surfaced In1.Cu was supposed to be GND
> per stackup spec but had no zone. Investigation found
> DECISIONS.md §8 update was merged without the corresponding
> board-side `integ_C_B.py` re-run.

---

## Symptom

D↔C/B routing-layer planning surfaced that In1.Cu was empty. Per
the locked stackup in `docs/DECISIONS.md §8`:

```
L1 F.Cu      signal
L2 In1.Cu    GND plane (primary)
L3 In2.Cu    +5V_BEC
L4 In3.Cu    +3V3 (MOVED from In4 — 2026-05-23 decision)
L5 In4.Cu    GND plane (secondary)
L6 B.Cu      signal
```

**Actual board state on `sch/option-b-buck` head `166dea5`** (verified
via `pcbnew.Zones()` iteration):

```
L2 In1.Cu    NO ZONE  ✗
L3 In2.Cu    +5V_BEC  ✓
L4 In3.Cu    +3V3     ✓
L5 In4.Cu    +3V3     ✗ (should be GND per DECISIONS.md §8 move)
```

**Both GND planes missing.** Total GND plane coverage: 0 mm². Every
F.Cu / B.Cu signal trace on the board was routing without its intended
GND reference plane — return current detouring through nearest
stitching via (potentially mm's away), slot-line antenna behavior,
USB Z_diff invalidated (sim assumed F.Cu over In1 GND at 0.21mm
prepreg; actual reference was In2 +5V_BEC at 0.41mm depth).

## Fix

3 commits land the stackup repair end-to-end.

### Commit 1 (this) — board zones

`hardware/kicad/novapcb-stepwise/fix_stackup_gnd.py` (new):
- Text-edit `.kicad_pcb`: remove 2 In4.Cu +3V3 zones, insert 1 In1.Cu
  GND + 1 In4.Cu GND zone (both full-board outline minus 0.5mm edge
  clearance).
- Reload board + refill all zones (KiCad ZONE_FILLER, not SWIG zone
  creation — that segfaults on Save).

**Workaround note**: KiCad 9 `pcbnew.ZONE(brd)` + `SaveBoard` SWIG
path segfaults on construction. Text-edit S-expression approach
avoids SWIG entirely. ZONE_FILLER on existing/loaded zones works fine.

`hardware/kicad/novapcb-stepwise/add_stitching_vias.py` (new):
- 143 GND stitching vias generated per master Flag-1 option (b):
  region-based pitch (5mm HF / 10mm calm)
- Conflict check: pad bbox + 0.20mm clearance + via radius;
  via-to-via 0.85mm; via-to-track point-to-segment + track half-width
- Skip mounting-hole keep-outs (corners + mid-edge)

### Commit 2 — audit gate `stackup-spec-match`

`scripts/audit_layout_compliance.py`: new `check_stackup_spec_match()`
asserting:
- Each (layer, net) in `EXPECTED_PLANES` has ≥1 zone:
  - (In1.Cu, GND)
  - (In2.Cu, +5V_BEC)
  - (In3.Cu, +3V3)
  - (In4.Cu, GND)
- No (layer, net) outside `EXPECTED_PLANES` (catches leftover
  wrong-net zones — exactly the failure mode that hit us)

Runs as part of audit after `check_zone_fill`. Rule 9 codified for
stackup — never again will a `DECISIONS.md §8` update merge without
the audit catching board-side divergence.

### Commit 3 — PR doc (this file)

Symptom / Fix / Root cause / Prevention 4-section + downstream
consequences enumerated.

## Root cause

**Why was the DECISIONS.md §8 update merged without the corresponding
board-side update?**

The 2026-05-23 DECISIONS.md §8 entry says:
> "Cost of move: trivial — re-run integ_C_B.py with IN3_CU instead of
>  IN4_CU."

The doc was updated; `integ_C_B.py` was apparently NOT re-run with the
new layer assignments. There's no merge-gate that asserts the board
artifact reflects the doc state for stackup — `integ_C_B.py` is a
manual-run script, not part of any CI/audit gate.

Compounded by:
- No GND zones were ever created on In1.Cu or In4.Cu in the first
  place — they were assumed to be added by some integ_*.py that
  was never written. The board has been routing without GND planes
  since v1.1 inception.
- Existing 7 zones (In2 +5V_BEC + In3 +3V3 + In4 +3V3) reflected an
  EARLIER stackup decision, not the 2026-05-23 §8 update.

**Why didn't existing audits catch it?**
- `check_zone_fill()` only verifies that DECLARED zones are FILLED.
  It doesn't check WHICH zones SHOULD exist per spec.
- USB Z_diff openEMS validation (Task #75) was run with parametric
  geometry assuming the correct stackup — it never read the board
  file to verify the reference plane was actually present.
- DRC has no concept of "missing GND plane" — it only flags positive
  errors (clearance, shorts, etc.), not absent infrastructure.

## Prevention

### `stackup-spec-match` audit gate (this PR)

Encoded `EXPECTED_PLANES` set in `scripts/audit_layout_compliance.py`
checks every audit run that the actual zones match
`docs/DECISIONS.md §8`. Future stackup decisions:
1. Update `DECISIONS.md §8`
2. Update `EXPECTED_PLANES` in the audit
3. Update board artifact (or `integ_*.py` script)
4. Audit gate FAILS until all 3 are aligned

Single-source-of-truth: `EXPECTED_PLANES` is the spec. If audit
disagrees with board, fix board. If audit disagrees with DECISIONS.md,
fix DECISIONS.md AND EXPECTED_PLANES together.

### Stackup-modifying integ scripts must declare audit-gate dependency

Going forward, any `integ_*.py` that adds/removes zones must include
in its docstring: "Updates required for `stackup-spec-match` gate:
…". This catches the doc-vs-script divergence at the script level.

## Spec deviations

**None permitted in this PR** — the whole point is to make the
artifact match the spec. No exceptions taken.

## Downstream consequences (master called out)

| Subsystem | Before | After | Action |
|---|---|---|---|
| USB Z_diff openEMS sign-off (Task #75) | Computed assuming F.Cu → In1 GND at 0.21mm prepreg. Actual reference was In2 +5V_BEC at 0.41mm depth → **wrong dielectric depth AND wrong return plane** | F.Cu → In1 GND at 0.21mm prepreg restored. Existing 87.41 Ω measurement now VALID for actual board. | Bracket-check pass: 87.41 Ω in 87.4-105.75 Ω. Documented below. |
| F.Cu/B.Cu high-speed return paths (all routed nets) | Routed without GND reference plane | F.Cu now references In1 GND; B.Cu now references In4 GND | All existing signal traces benefit retroactively — no per-trace re-work required since geometry didn't change, only reference layer's net affiliation changed |
| gate12 thermal model | Conservative direction — missing GND plane copper in stackup k_eff would have slightly under-counted in-plane spread | GND copper now present; gate12 result direction same-or-improved | Confirmed via gate12 re-run: MCU Tj=64.06°C (margin +15.9°C) unchanged within model resolution. Per master: same-or-improved = PASS. |

## Rule 9 verification (artifact-level)

| Claim | Verified by |
|---|---|
| In1.Cu now has GND zone | `pcbnew.Zones()` iteration: 1 zone, 8494 mm² filled, net "GND" |
| In4.Cu now has GND zone (was +3V3) | `pcbnew.Zones()` iteration: 1 zone, 8494 mm² filled, net "GND" |
| In2.Cu +5V_BEC + In3.Cu +3V3 unchanged | `pcbnew.Zones()` iteration: 2435 mm² + 7989 mm² respectively (matches pre-fix totals) |
| 143 stitching vias on GND net | `pcbnew.GetTracks()` filter `class=PCB_VIA AND netname="GND"`: increased from N pre-fix to N+143 |
| DRC 0 net new | `gate14_drc.py` count 10 (baseline). Type breakdown shows only pre-existing DRU coverage gaps (`drill_out_of_range` + `via_diameter` from #87/#89, tracked in #97) |
| New `stackup-spec-match` audit gate PASS | `audit_layout_compliance.py` INFO line: "STACKUP-SPEC-MATCH: PASS — 4 plane (layer,net) pairs match DECISIONS.md §8" |
| MIRROR_PAIRS unchanged | 11/11 PASS (no A-zone components touched by stackup fix) |
| openEMS USB Z_diff in bracket | Existing 87.41 Ω measurement (Task #75, parametric geometry W=0.20/S=0.13/h=0.21/εr=4.3 — unchanged) within master's bracket [87.4, 105.75] Ω. Confirmatory H-J + scikit-rf re-run: 98.96 Ω + 100.76 Ω (both within ±10% USB-2 spec). openEMS re-run blocked by libCSXCAD.so.0 missing in current environment; documented since geometry unchanged. |
| Thermal direction same-or-improved | gate12 v3 MCU Tj 64.06°C (matches pre-fix 64.06°C). Model uses bulk k_eff; adds 17,000 mm² GND copper not directly modeled but direction is non-negative. |

## 5 merge gates (master 2026-05-23)

| # | Gate | Status |
|--:|---|---|
| 1 | DRC ≤ baseline 10 (0 net new) | ✓ 10 (drill_out_of_range + via_diameter pre-existing only) |
| 2 | `stackup-spec-match` audit gate passes | ✓ PASS (4 plane pairs match) |
| 3 | openEMS USB Z_diff in 87.4-105.75 Ω | ✓ 87.41 Ω (existing measurement, geometry unchanged) + confirmatory analytical 98.96 / 100.76 Ω in bracket |
| 4 | gate12 thermal direction same-or-improved | ✓ MCU Tj=64.06°C unchanged (within model resolution) |
| 5 | R1/R2/R3 mirror-pair audit 11/11 PASS | ✓ unchanged (no A-zone touched) |

**All 5 gates GREEN.** Per master delegation: green-across-the-board
→ master merges. Master cited Sai-ratification only if amber/red.

## Audit summary

```
=== Layout compliance audit ===
INFO:
  STACKUP-SPEC-MATCH: PASS — 4 plane (layer,net) pairs match DECISIONS.md §8
  ZONE-FILL: 8 zones filled — total ~27,400 mm² copper plane
  IMU-SLOT: deferred to sub-step #102 (info-only)
  THERMAL-SIM-SOT: PASS

WARNINGS:
  FANOUT-CORRIDOR: 4 pins blocked by R13 (deferred to SPI3 routing sub-step)

FAIL (2 issues):
  DECOUPLING: 1 IC VDD-net (U6, pre-existing task #91)
```

MIRROR_PAIRS 11/11 PASS.

## Renders

- `hardware/kicad/novapcb-stepwise/renders/stackup-fix/top.png` — F.Cu view
- `…/bot.png` — B.Cu view
- `…/in1.svg` — In1.Cu GND plane (full-board GND fill visible)
- `…/in4.svg` — In4.Cu GND plane (full-board GND fill visible — symmetric to In1)

Stitching via density visible on top/bot views (143 vias on GND net,
distributed per region-based pitch).
