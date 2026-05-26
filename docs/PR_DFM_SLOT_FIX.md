# PR — DFM check + IMU-slot flight-critical clearance fix

> Branch `hw/dfm-check` off `sch/option-b-buck` (449cdf1). Bundles: (1) the DFM
> checker tool adapted for novapcb-stepwise + its run, (2) the DFM report, (3) the
> IMU-slot shrink that fixes a merge-introduced flight-critical conflict.
> **Verdict: DFM PASS, 0 unexpected DRC, 0 copper-edge-clearance.**

## 1. What this PR does

1. **DFM checker** (`hardware/kicad/novapcb-stepwise/run_dfm_check.py`) — adapted
   from the layout-v2 version: stepwise board path, `.kicad_dru`-exception
   classification (kicad-cli ignores custom rules), min-feature capability scan.
2. **DFM report** (`docs/DFM_REPORT.md`) — JLC06161H verdict PASS; documents the
   flight-critical catch.
3. **IMU slot fix** — shrink the PR #108 slot from full-width (X42–83) to a clean
   SE-corner rectangle **X58.5–83.0, Y65.4–66.6** so it no longer overlaps the
   MOT3-6 fanout.

## 2. The catch (why this matters)

The IMU stress-relief slot (#108) and the MOT3-6 routing (#107) were each correct
**on their own branch**. #108's slot survey ran when no MOT routing existed; #107
routed MOT3-6 without the slot present. They merged cleanly in git — but the
result placed an **Edge.Cuts board cutout directly over four flight-critical
motor traces**. KiCad doesn't delete copper under a cut, so connectivity looked
fine; only `copper_edge_clearance` DRC (run during this DFM pass) exposed it.

This is the textbook case for why DFM runs on the **integrated** board, not per
branch. Caught before fab — exactly what the verification gates exist for (Rule 17).

## 3. The fix

| | Before (#108) | After |
|---|---|---|
| Slot X-span | 42.0 – 83.0 (with W-slot + bridge) | 58.5 – 83.0 (single rect) |
| Crosses MOT3-6? | yes (4 edge-clearance) | no (≥0.681 mm clear) |
| Bridges | yes (trace pass-throughs) | none needed |
| copper_edge_clearance DRC | 4 | **0** |

West edge is **X58.5**, not the literally-proposed X57.5: the board edge-clearance
constraint is **0.5 mm**, and MOT6 (line `x+y=122.8`) grazes the slot's top-left
corner — X57.5 gave only 0.327 mm, X58.0 still failed. X58.5 is the minimum east
shift that clears MOT6 by margin (0.681 mm). This is a 0.5 mm refinement within
master's approved option (a), not a re-scope.

**Honest scope note:** the slot is now a *partial* SE-corner flex break (24.5 mm),
not a full island isolation. Full slot scope → v2. Per master: ship minimal-but-
non-zero > revert a Sai-locked directive.

## 4. Prevention — survey on the target head, not the branch base

### 4.1 Root cause

A zone/cut survey was correct at survey time but stale at merge time, because the
target branch advanced (gained MOT routing) between survey and merge. Both PRs
passed their own gates; neither re-checked the *integrated* state.

### 4.2 Rule 22 corollary (proposed — for master to batch at Phase 7a)

> **Rule 22 (rectangle-clearance for zone-change surveys) — corollary:**
> For any PR that adds or moves an Edge.Cuts cut, copper pour boundary, or
> keepout, the rectangle-clearance survey **must run against the current merge
> TARGET HEAD, not just the branch base**. If the target branch advances between
> survey and merge, **re-run the rectangle-clearance check on the new head before
> merging**. A clean survey on a stale base is not evidence about the merged board.

This is the same class as the "verify the artifact, not the narrative" memory
(`feedback_doc_state_verify`): verify against current state, not a snapshot.

### 4.3 Merge-coordination lesson

When two in-flight branches both touch the same physical region (here: the IMU
island's south edge — one adds a cut, one adds routing), they are **not
independent** even if they touch disjoint file sections. The merge order
determines which sees the other. Mitigation:

- Flag region-overlapping branches to master before parallel dispatch.
- The branch merged **second** owns the integration re-check on the combined head
  (rectangle clearance for cuts; cluster walk for routing).
- DFM on the integrated board is the backstop — and is why it ran here.

## 5. Verification (5-gate + DFM)

- **Gate 1 — DRC ≤ baseline:** 12 kicad-cli flags, all `.kicad_dru`-covered
  (5 via_diameter + 5 drill via-in-pad family + 2 courtyard relaxations);
  **0 unexpected; 0 copper_edge_clearance** (was 4). GUI-DRC-authoritative = 0.
- **Gate 2 — STACKUP-SPEC-MATCH:** unaffected (Edge.Cuts + zone refill only; no
  layer/copper-spec change). 6-layer stackup intact.
- **Gate 3 — MIRROR_PAIRS:** unaffected (no component moves).
- **Gate 4 — DECOUPLING:** unaffected (no cap moves; IMU decap unchanged).
- **Gate 5 — per-net cluster walk:** MOT3-6 clear the slot by ≥0.681 mm (MOT6
  closest; MOT3/4/5 6–10 mm); MOT3-6 connectivity intact (not severed).
- **DFM:** PASS — all min-features within JLC06161H capability (track 0.100,
  via OD 0.450, drill 0.250, annular 0.100, TH 0.600).

## 6. Out-of-scope items surfaced (Rule 17, tracked not dropped)

- **MOT1/MOT2 unrouted** (0 tracks) + **STATUS "6/8" vs artifact "4/8"** — see
  `DFM_REPORT.md §4`. Pre-existing, not slot-caused. For master/Sai: route MOT1/2
  to reach 6/8, or correct STATUS to 4/8.
