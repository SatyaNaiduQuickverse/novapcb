# PR — H placement (1× JST-GH 10-pin ESC output, J11)

> **Branch**: `hw/h-placement-10pin` off `sch/option-b-buck` head `b5b6818`
> **Scope**: Placement-only. Single J11 connector replaces obsolete
> J11..J18 ESC_solder_pad parked layout. NO routing (H↔C DShot fanout
> is the next sub-step).
> **Master sign-off**: 2026-05-24 D1=a centered X=52.5, D2=a Y=80, D3=a rot 0°.
> Sub-step #107.

---

## Symptom

After PR #80 merged (1× JST-GH 10-pin schematic), the board file still
held the obsolete J11..J18 8-connector ESC_solder_pad layout (all
parked at X>100, never moved into final position). The board needed
synchronization to the new schematic + first-time placement of the
single connector at the master-signed-off anchor.

## Fix

`step7_place_H.py` (3-phase subprocess pattern, KiCad-9 SWIG-clean):

1. **Phase 1** (add): Pre-load
   `Connector_JST:JST_GH_SM10B-GHS-TB_1x10-1MP_P1.25mm_Horizontal`,
   remove J11..J18, add new J11 at `(52.5, 80, rot 0°)`.
2. **Phase 2** (nets): Parse `novapcb.net`, assign J11.1..J11.8 → MOT1..MOT8,
   J11.10 → GND. J11.9 (VDD_SERVO) + 2× MP (mech-post) pads unbound
   (intentional — Sai-ratified NC + mechanical-only respectively).
3. **Phase 3** (fill): Refill all 7 zones (J11.10 pad inclusion in
   GND zone-fill).

Each phase runs in its own subprocess to keep KiCad-9 SWIG state
clean — `FootprintLoad` is known to regress on cumulative SWIG state
after board mutations (workaround established in
`fix_option_b_footprints.py`).

### Final pad positions (verified post-Phase-3)

| Pin | Net | XY (mm) |
|---:|---|---|
| 1 | MOT1 | (46.875, 78.150) |
| 2 | MOT2 | (48.125, 78.150) |
| 3 | MOT3 | (49.375, 78.150) |
| 4 | MOT4 | (50.625, 78.150) |
| 5 | MOT5 | (51.875, 78.150) |
| 6 | MOT6 | (53.125, 78.150) |
| 7 | MOT7 | (54.375, 78.150) |
| 8 | MOT8 | (55.625, 78.150) |
| 9 | (NC — Sai) | (56.875, 78.150) |
| 10 | GND | (58.125, 78.150) |
| MP | — | (45.025, 81.350) |
| MP | — | (59.975, 81.350) |

All positions match the docs/H_PLACEMENT_CONSTRAINT_ANALYSIS.md plan
to ±0 (script computes from anchor + footprint geometry).

## Root cause

Phase 3f SKiDL used `Conn_01x02` × 8 placeholder. Phase 4 layout
auto-imported with `ESC_solder_pad` custom footprint (also placeholder),
parked all 8 at X>100 awaiting placement decisions. PR #80 collapsed
the topology to 1× 10-pin JST-GH (Pixhawk 6X FMU PWM OUT standard) per
DECISIONS.md §7. This PR is the layout-side application of that decision.

## Prevention

NO bug class to prevent — this is the routine "schematic merged →
layout follows" sub-step. The 3-phase subprocess pattern in
`step7_place_H.py` is the proven SWIG-clean workflow.

## Master's 5 gates — verification

| Gate | Expected | Result |
|---|---|---|
| 1. DRC ≤ baseline 10 + 0 net new | 0 new errors | **−13 net** (baseline 34 errors → 21 errors). Removed J11..J18 parked off-board courtyards eliminated more issues than the new J11 introduced. |
| 2. STACKUP-SPEC-MATCH PASS | PASS | **PASS** — all 4 plane (layer,net) pairs intact per DECISIONS.md §8 |
| 3. MIRROR_PAIRS 11/11 | 11/11 | **11/11 intact** — H placement didn't touch any A subsystem mirror pair member (J11 ≠ J4/J19 pair members; H subsystem is SINGLE_INSTANCE per R3) |
| 4. DECOUPLING J11 no decap requirement | exempt | **Exempt** — J11 is passive connector (no IC VDD). Only pre-existing DECOUPLING fail is U6 (task #91, unchanged by this PR). |
| 5. H-FANOUT-REACHABILITY (nice-to-have) | paper-verify | **Paper-verified** in `docs/H_PLACEMENT_CONSTRAINT_ANALYSIS.md §4` — all 8 MOT* paths F.Cu-feasible at this anchor; no layer split, no firmware remap. Codification deferred to follow-up. |

### DRC delta breakdown

| Category | Baseline | Post-step7 | Δ |
|---|---:|---:|---:|
| keepout area error | 1 | 0 | −1 |
| netclass 'Default' error | 19 | 13 | −6 |
| courtyard error | 10 | 5 | −5 |
| solder-mask min width error | 4 | 3 | −1 |
| silk warning | 109 | 93 | −16 |
| silk text height warning | 12 | 4 | −8 |
| board setup warning | 1 | 1 | 0 |
| **Total** | **156** | **119** | **−37** |
| **Unconnected items** | 269 | 263 | **−6** |

All reductions trace to removal of 8 PARKED J11..J18 ESC_solder_pad
footprints (their off-board courtyards + silkscreen overlapped panel
edges and produced spurious errors).

### Audit gates — preserved

```
=== Layout compliance audit ===
Components: 99 (was 106 = -7 for 8 removed + 1 added)
STACKUP-SPEC-MATCH: PASS — 4 plane (layer,net) pairs
ZONE-FILL: 7 zones filled — total 26832 mm² (unchanged)
DECOUPLING fail: U6 (pre-existing #91)
FANOUT-CORRIDOR warning: R13 (pre-existing slot-deferral consequence)
```

### Per-net F.Cu reachability paper-verify

| Net | MCU pin (X, Y) | J11 pin (X, Y) | F.Cu path (planned) | Length est. |
|---|---|---|---|---|
| MOT1 | (43.00, 42.67) | J11.1 (46.875, 78.15) | S then E ~3.88mm | ~36mm |
| MOT2 | (43.50, 42.67) | J11.2 (48.125, 78.15) | S then E ~4.63mm | ~36mm |
| MOT3 | (37.33, 39.50) | J11.3 (49.375, 78.15) | W-edge → S → E ~12.05mm | ~50mm |
| MOT4 | (37.33, 40.00) | J11.4 (50.625, 78.15) | W-edge → S → E ~13.30mm | ~51mm |
| MOT5 | (37.33, 40.50) | J11.5 (51.875, 78.15) | W-edge → S → E ~14.55mm | ~52mm |
| MOT6 | (37.33, 41.00) | J11.6 (53.125, 78.15) | W-edge → S → E ~15.80mm | ~53mm |
| MOT7 | (52.67, 37.00) | J11.7 (54.375, 78.15) | E-edge → S near-straight | ~43mm |
| MOT8 | (52.67, 36.50) | J11.8 (55.625, 78.15) | E-edge → S | ~43mm |

All paths < 60mm. DShot600 tolerates ≪100mm. Max spread MOT7 vs MOT6
= 10mm (~21% of mean) — acceptable per project length-matching policy
(DShot channels are independent; no skew constraint).

All paths terminate at X ≤ 55.625 — WEST of D zone west edge X=56.
Zero D-zone trace conflicts.

## Spec deviations (Rule 4)

NONE. Layout follows analysis exactly. All 3 master-signed decisions
(D1/D2/D3) baked into script anchor + rotation.

## Rule 9 verification (artifact-level)

| Claim | Verified by |
|---|---|
| J11 placed at (52.5, 80) rot 0° | `pcbnew.LoadBoard(...).GetFootprints()['J11'].GetPosition()` returns (52500000, 80000000) nm |
| J12..J18 removed from board | `[f.GetReference() for f in brd.GetFootprints() if f.GetReference() in ('J12','J13','J14','J15','J16','J17','J18')]` returns `[]` |
| J11 footprint = JST_GH_SM10B-GHS-TB | `j11.GetFPID().GetLibItemName()` returns `'JST_GH_SM10B-GHS-TB_1x10-1MP_P1.25mm_Horizontal'` |
| Pin 1..8 = MOT1..MOT8 | per-pad `pad.GetNetname()` for pin '1'..'8' returns MOT1..MOT8 respectively |
| Pin 10 = GND | `pad.GetNetname()` for pin '10' returns 'GND' |
| Pin 9 NC (Sai-ratified) | `pad.GetNetname()` for pin '9' returns `''` (intentional NC per project SKiDL convention `imu_3c.py:170`) |
| MP posts unbound | both MP pads return `''` (mechanical only) |
| 7 zones refilled | `brd.Zones()` returns 7 items, total area 26832 mm² (matches baseline) |
| Audit baseline preserved | `python3 scripts/audit_layout_compliance.py` returns same 2 FAILS (U6 #91 + R13 fanout) as pre-step7 baseline |
| DRC favorable | `kicad-cli pcb drc` reports 21 errors (was 34) + 263 unconnected (was 269) |

## After this lands

PR-C (next sub-step) — **H↔C routing**:
- Fanout 8 MOT* F.Cu traces MCU TIM pins → J11.1..J11.8
- Add stitching via at/near J11.10 to bond GND pad to In1/In4 GND planes
  (closes the 1 GND unconnected — distinct from the 8 MOT* routing
  unconnecteds)
- Cluster-walk each F.Cu DShot trace for continuous In1.Cu GND ref
- DRC ≤ post-step7 (21 errors) + 0 net new

Plus master's nice-to-have:
- H-FANOUT-REACHABILITY codification as new audit gate (deferred per
  master directive — non-blocker)

## Files changed

| File | Change |
|---|---|
| `hardware/kicad/novapcb-stepwise/step7_place_H.py` | NEW — 3-phase H placement script |
| `hardware/kicad/novapcb-stepwise/novapcb-stepwise.kicad_pcb` | J11..J18 removed; new J11 placed at (52.5, 80) with JST-GH 10-pin footprint; zones refilled |
| `hardware/kicad/novapcb-stepwise/renders/step7_H_top.png` | NEW — visual confirmation top side |
| `hardware/kicad/novapcb-stepwise/renders/step7_H_bot.png` | NEW — visual confirmation bottom side |
| `docs/PR_H_PLACEMENT_10PIN.md` | NEW — this PR doc |

## Test plan

- [x] step7_place_H.py runs clean all 3 phases (subprocess pattern)
- [x] J11 at (52.5, 80, 0°) verified
- [x] J12..J18 absent from board
- [x] J11 footprint = JST_GH_SM10B-GHS-TB
- [x] Pin 1..8 = MOT1..MOT8, pin 10 = GND, pin 9 NC, MP unbound
- [x] DRC ≤ baseline (favorable: −13 errors)
- [x] STACKUP-SPEC-MATCH PASS
- [x] MIRROR_PAIRS 11/11 intact
- [x] DECOUPLING — no new fail (U6 #91 only, pre-existing)
- [x] Top/bot rendered
- [ ] **Next sub-step**: H↔C DShot fanout routing + GND stitching via
