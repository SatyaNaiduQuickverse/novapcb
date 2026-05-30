# DFM report — novapcb-stepwise (pre-Phase-7a)

> Fab target: **JLCPCB 6-layer JLC06161H** (7628 prepreg), advanced tier.
> Tool: `hardware/kicad/novapcb-stepwise/run_dfm_check.py` (adapted from the
> layout-v2 checker). Run on branch `hw/dfm-check` off `sch/option-b-buck`
> (head 449cdf1). **Verdict: PASS.**

## 0. TL;DR

The board is manufacturable on JLC06161H. Every kicad-cli DRC flag is a known,
documented `.kicad_dru` exception; all minimum features clear the JLC capability
floor. **One flight-critical regression was caught and fixed in this PR** (the
merge-introduced IMU-slot-over-MOT-fanout conflict — §3). Two connectivity items
(MOT1/2/7/8 unrouted) are pre-existing and out of this PR's scope; flagged in §4.

## 1. DRC — kicad-cli vs GUI authority

`kicad-cli pcb drc` does **not** apply the project `.kicad_dru` custom rules (no
CLI flag exists for it), so it over-reports every via-in-pad / fab-exception that
the GUI DRC passes. The checker re-classifies these.

| | count |
|---|---|
| kicad-cli total (error severity) | 12 |
| → DRU-covered exceptions | 12 |
| → **unexpected** | **0** |
| copper_edge_clearance | **0** |

**GUI-DRC-authoritative error count = 0.** The 12 DRU-covered flags:

| Type | Count | Nets / scope | .kicad_dru rule |
|---|---|---|---|
| `via_diameter` | 5 | ORING_A_GATE, ORING_B_GATE, +5V_BEC×2, EFUSE_ILIM | via-in-pad-*-diameter |
| `drill_out_of_range` | 5 | same 5 via-in-pads | via-in-pad-*-hole / u6-extended-*-hole |
| `courtyards_overlap` | 2 | SOT-23-6 U11/U12 + WQFN U6 relaxations | u11-u12-fanout / u6-courtyard |

All are scope-bounded and documented in `novapcb-stepwise.kicad_dru` +
`docs/DECISIONS.md §13` (via-filled-and-capped + 4mil fab process). The GUI DRC
(which applies `.kicad_dru`) is the authority for the Phase 7a freeze.

## 2. Minimum-feature capability scan

Actual board minimums vs JLC06161H advanced-tier floor:

| Feature | Actual | JLC floor | OK |
|---|---|---|---|
| Min track width | 0.100 mm | 0.09 mm | ✅ |
| Min via diameter | 0.450 mm | 0.40 mm | ✅ |
| Min via drill | 0.250 mm | 0.15 mm | ✅ |
| Min via annular | 0.100 mm | 0.09 mm | ✅ |
| Min through-hole drill | 0.600 mm | 0.20 mm | ✅ |

The 0.45 OD / 0.25 drill via-in-pads (ORFET gates, +5V_BEC ORFET output,
EFUSE config exits) are within capability but **require JLC's vias-filled-and-
capped process** (~$30–50/board) — already captured in `DECISIONS.md §13`.

## 3. Flight-critical catch — IMU slot over MOT3-6 fanout (FIXED in this PR)

The IMU stress-relief slot (PR #108, task #50) was surveyed and cut on its own
branch when **no MOT routing existed**. T3-partial (PR #107) then routed the
MOT3-6 fanout. The two branches merged cleanly in git but the merge put the
**Edge.Cuts slot directly over the MOT3-6 fanout column** — a board cutout under
flight-critical motor traces. KiCad does not auto-delete copper under a cut, so
the data model showed the nets *connected*; only the `copper_edge_clearance` DRC
exposed it (4 violations: MOT3/MOT4/MOT5/MOT6 vs the slot edges).

This is a fabrication-stage defect: the routed traces would be cut where the slot
removes board material. **Caught by DFM, not by either branch's own gate.**

**Fix (master-approved, option (a) "shrink to SE-corner"):** the full-width slot
(X42–83) was replaced with a clean SE-corner slot **X58.5–83.0, Y65.4–66.6**
(24.5 mm, single closed rectangle, no bridges — no copper crosses it).

- West edge set to **X58.5** (not the literally-proposed X57.5): MOT6 B.Cu runs
  along the line `x+y=122.8` and grazes the slot's top-left corner. The board
  `copper_edge_clearance` constraint is **0.5 mm** (not 0.2), so X57.5 left only
  0.327 mm and X58.0 still failed (0.327 mm). X58.5 gives **0.681 mm** copper
  clearance — the minimum east shift that satisfies the 0.5 mm rule with margin.
- Post-fix: **0 copper_edge_clearance**. MOT3-6 clear the slot by ≥0.681 mm
  (MOT6 closest; MOT3/4/5 at 6–10 mm). MOT3-6 connectivity intact (not severed).

**Mechanical-isolation note (honest scope):** the slot is now a *partial*
SE-corner flex-break (24.5 mm on the dominant N-S axis), **not** a full island
isolation. The full slot scope is inherited by v2 (placement-aware from the
start). Per master: ship the minimal-but-non-zero flex break + document the
tradeoff > revert a Sai-locked directive.

## 4. Connectivity inventory (informational)

**2026-05-30 refresh (Rule-9 verify-the-artifact):** the original §4 (MOT1/2 unrouted, 4/8 motors) was correct at this PR's commit but stale by HEAD 65419e3. Current artifact state:

- **MOT1 / MOT2** — **ROUTED** in PR #117 (task #55, south-edge PB0/PB1 TIM3 → J11.1/J11.2). 6/8 motors functional in v1 as documented in STATUS / HANDOFF / CLAUDE.md §1.1.
- **MOT7 / MOT8** — unrouted *by design* (Sai option D in DECISIONS §3: hwdef declares all 8 PWM channels; v1 ships 6/8 functional; MOT7/8 retained at hwdef level for v2 / future octocopter retrofit).

**Doc-artifact alignment restored.** No reporting gap remains.

— original §4 text preserved below for traceability —

DRC ratsnest: MOT1, MOT2, MOT7, MOT8 unrouted (0 tracks each, verified in both current head and the pre-fix backup — **not** caused by the slot). MOT7/MOT8 unrouted by design (Sai option D). MOT1/MOT2 unrouted; T3-partial (PR #107) routed MOT3-6 only. Doc-vs-artifact discrepancy flagged for master/Sai. (RESOLVED 2026-05-30: PR #117 routed MOT1/2 — see refresh block above.)

## 5. Board feature inventory

| | as of DFM report | as of HEAD 65419e3 |
|---|---|---|
| Footprints | 131 | 131 |
| Pads | 573 | 573 |
| Tracks | 783 | 1023 (post-MOT1/2 route + Phase 4d-redux power tree) |
| Vias | 288 | 333 (post-stitching maturation) |
| Zones | 7 | 7 |
| Stackup | 6-layer (F / In1 GND / In2 +5V_BEC / In3 +3V3 / In4 GND / B) | unchanged |

## 6. Verdict

**PASS** — manufacturable on JLC06161H. 0 unexpected DRC, 0 copper-edge-clearance
(flight-critical regression fixed), all min-features within capability. Residual
open items (MOT1/2 routing + the STATUS 6/8 vs 4/8 note) are tracked in §4 for
master/Sai, not part of the DFM manufacturability verdict.
