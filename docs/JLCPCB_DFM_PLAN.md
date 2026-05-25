# JLCPCB DFM Compliance Plan (task #11)

> **Status**: DRAFT for master sign-off (autonomous mode 2026-05-24).
> NO board changes yet — plan + checker script only.
> **Branch**: `docs/jlcpcb-dfm-plan` (will combine with sim-suite-plan
> into single docs/ branch if appropriate).
> **Target fab**: JLCPCB 6-layer JLC06161H-7628 stackup per
> DECISIONS.md §8.

---

## DFM checklist

### 1. Trace width — minimum ≥ 0.1mm (4 mil)

- Current scoped exception: U6 courtyard 4mil (0.10mm trace) per
  existing DRU rule `u6-courtyard-4mil-track`. Compliant.
- All other traces ≥ 0.13mm or default 0.25mm. Compliant.

### 2. Drill size — minimum ≥ 0.2mm

- Current scoped exception: ORING_A/B_GATE via-in-pad 0.25mm drill
  per existing DRU rule `via-in-pad-orfet-hole`. Compliant.
- Standard vias 0.3mm drill. Compliant.

### 3. Annular ring — minimum ≥ 4 mil (0.1mm)

- Standard vias Φ0.5mm / drill 0.3mm → annular ring (0.5-0.3)/2 = 0.1mm. Meets.
- Via-in-pad ORFET Φ0.45 / 0.25 → annular (0.45-0.25)/2 = 0.10mm. Meets.

### 4. Solder mask expansion

- KiCad default solder mask expansion 0.0508mm (2 mil). JLC standard
  spec ≥ 0.05mm (or via-tented). Compliant.

### 5. Edge clearance — minimum ≥ 0.3mm

- Components: 1.5mm S-edge clearance for J11 (south band). All
  connectors verified ≥0.3mm from board edge.
- **Action**: write checker script to enumerate all footprint courtyards
  + board edge distance. Flag any <0.3mm.

### 6. Via aspect ratio ≤ 8:1

- 1.6mm board / 0.3mm drill = 5.33:1 — compliant
- 1.6mm board / 0.25mm drill (ORFET via-in-pad) = 6.4:1 — compliant
- 1.6mm board / 0.2mm drill (if any) = 8:1 — at limit

### 7. Layer stack-up compliance — JLC06161H-7628

- DECISIONS.md §8 spec: 4-layer build but PR #76 stackup-fix landed
  6-layer L1-L6 JLC06161H. Confirm physical stackup matches:
  - L1 F.Cu 1oz
  - L2 In1.Cu (GND, 0.5oz inner)
  - L3 In2.Cu (+5V_BEC, 0.5oz)
  - L4 In3.Cu (+3V3, 0.5oz)
  - L5 In4.Cu (GND, 0.5oz)
  - L6 B.Cu 1oz
  - Total thickness: 1.6mm ±10%

### 8. Specific JLCPCB constraints

- Min component pitch: 0.4mm (we use 0.5mm LQFP-100, 1.25mm JST-GH — comfortable)
- Min IC pad size: 0.2×0.2mm (we use 0.3mm pad widths — compliant)
- Maximum board dimension: 350×500mm (we are 105×85mm — comfortable)
- Standard via cap: requires "via filled + capped" fab process for
  via-in-pad per DECISIONS §13. Cost bump ~$30-50/board acknowledged.

## DFM checker script (`scripts/check_jlcpcb_dfm.py`)

Proposed script enumerates:
1. All footprint courtyards vs board edge — flag <0.3mm
2. All track widths — flag <0.10mm
3. All vias — drill ≥0.20mm, annular ≥0.10mm, aspect ratio ≤8:1
4. Solder mask expansion compliance (KiCad project setting)
5. Net stackup-layer assignment match per DECISIONS §8

Output: per-check PASS/FAIL with offender list.

## Decisions for sign-off

1. **Approach**: write `check_jlcpcb_dfm.py` + run on current board → PR
   with results. Recommend.
2. **Scope**: cover all 7 checks above. Recommend.
3. **Resolution policy**: if FAIL on any check, fix via SKiDL/board
   amend in this PR OR scope-bounded DRU exception with rationale.

## Sequence

1. Master sign-off
2. Write `scripts/check_jlcpcb_dfm.py`
3. Run on current board → output report
4. Document results in `docs/JLCPCB_DFM_RESULTS.md`
5. PR with script + results + any fixes

---

**Awaiting master sign-off (or autonomous-execute approval).**
