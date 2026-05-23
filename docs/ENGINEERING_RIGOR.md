# Engineering rigor — non-negotiables

These commitments bind every Claude on every Pi working on novapcb. They exist to prevent quiet downscoping when the work gets hard.

## 1. The simulation regime is the plan, not a suggestion

Every sub-phase in `DESIGN_PHASES.md` Phase 6 runs. Skipping a sub-phase requires a PR to this file recording **what was skipped**, **when**, and **what risk was accepted**. No quiet downscoping in chat or commit messages.

## 2. Failing sims change the design, not the pass criteria

If a sim says "<5 % rail droop on load step" and the design droops 12 %, the design changes. Adjusting a pass criterion mid-project requires a PR with technical justification — not "we got tired of waiting."

## 3. Confidence ratings only go up by evidence

A row in `CONFIDENCE_MAP.md` moves from MEDIUM to HIGH because a sim passed, a reference audit matched, or a bench measurement landed. Never because it has been talked about enough.

## 4. Phase 7 (fab order) requires explicit user sign-off

No autonomous-merge authority for Phase 7 — supermaster's typed comment on the PR is the only path. Real-money gate.

## 5. Re-loops between Phase 4 and Phase 6 are expected

Sim failures route back to layout. Not a project failure. The failure mode is *avoiding* the re-loop by relaxing a spec.

## 6. Phase 6.5 forum review is mandatory for every LOW-confidence row

Every LOW-rated subsystem in `CONFIDENCE_MAP.md` goes through ArduPilot forum / RC Groups external review before Phase 7. Optional for HIGH-confidence rows.

## 7. Brutal honesty mode-locked — 4-section PR docs

Reports state what was checked AND what was not. "Looks clean" without enumeration is a Rule 6 violation. Pushback over flattery, explicit gaps over false coverage, "I don't know" over confident filler.

**4-section PR doc format** (adopted 2026-05-23 from pcb.ai master, ack'd by novapcb master):

Every PR description includes these four headings — even on a one-line fix:

1. **Symptom** — observed problem (DRC error / sim fail / unexpected number / user-reported bug). What you actually saw, not your interpretation.
2. **Fix** — what was changed (one to three bullets). The diff, in prose.
3. **Root cause** — WHY it broke (the underlying issue, not where the symptom surfaced). Cross-ref §12 above.
4. **Prevention** — how to avoid the next instance. New gate / audit rule / doc clarification / committed memory. If no preventive measure is possible, say so explicitly.

Augmented sections (when applicable):

5. **Spec deviations** (Rule 4) — every divergence from the approved spec: WHAT spec said, WHAT was built, WHY, WHO approved.
6. **Rule 9 verification** — artifact-level proof for any "DRC GREEN" claim: cluster walks, `GetFilledArea()` reads, gerber visual inspection. Tool exit code alone does not satisfy.
7. **Audit run** — `scripts/audit_layout_compliance.py` output summary; PR cannot be merged with NEW warnings.

PR without 1–4 = reviewer rejection. PR without 5–7 when applicable = reviewer rejection.

## 8. Task contracts gate sub-phase work

Every sub-phase has a YAML contract under `tasks/` declaring inputs, outputs, and pass criteria BEFORE work starts. Scope expansion without updating the contract first is a Rule 4 violation. See `docs/TASK_CONTRACTS.md`.

## 9. Hourly retrospectives are mandatory

Master + all active workers write short retrospectives on every hour boundary. Idle hours produce a one-line idle retro, not silence. Three consecutive idle retros trigger a user ping. See `docs/RETROSPECTIVES.md`.

## 10. Grep-then-state, never state-then-grep

Worker self-diagnosed pattern 2026-05-19: claiming numbers, file paths, or config values from memory before re-grounding state in the source. Fix: every assertion about external state (file contents, build hashes, PR diffs, JSONL paths) is preceded by a fresh grep / read / api-call, not a memory recall. Both master and worker bound by this.

## 11. Master merge-authority is bounded

Supermaster delegated bounded autonomous-merge authority to master 2026-05-19:

- IN (master merges if clean): doc-only PRs; Phase 2 sub-phase firmware PRs; this engineering-rigor PR; Phase 3 schematic init and per-sheet PRs.
- OUT (still escalates to supermaster): Phase 4 layout PRs; Phase 5 BOM; Phase 6 sims; Phase 6.5 forum review; Phase 7 fab order; post-initial-commit amendments to `ENGINEERING_RIGOR.md` / `COORDINATION.md` / `COMMUNICATION.md`; repo visibility flip; force-push to main.

Audit before merge always answers the three SOTA self-check questions (is this SOTA? are we being honest? can we do better?) and reports per-Rule-6 what was verified + what was not.

## 12. Root-cause discipline (Sai 2026-05-23)

> "If there is an issue we should think about the ROOT of the problem
> and not just a fix — or it gets uglier with time."

Every fix — for any issue (DRC violation, ERC error, sim failure,
routing plateau, unexpected result, failed gate) — MUST in its PR /
commit message state:

1. **Root cause** — traced to its origin, not just where the symptom
   surfaced.
2. **Root or stopgap** — does the fix REMOVE the root cause, or is it a
   stopgap?
3. **If a stopgap** — why a root fix isn't being done now, and the
   root cause logged to `docs/OPEN_QUESTIONS.md` for follow-up.

A stopgap is the rare, explicitly-justified exception — never the
default. Patches compound: a symptom-patch leaves the real cause in
place, and the issues it spawns are harder to fix than the original.

Master audits every fix PR for root-vs-patch. If the same class of
issue resurfaces after a "fix", the fix was a patch — go back to the
root.

### Patch instincts to recognize and resist

- "omit the feature" / "ship without the bridges"
- "accept with known violations" / "single-orientation USB-C for v1"
- "defer to v2" (when the v1 problem is the same root issue)
- "nudge one number" without understanding why the original was wrong

### Examples (committed history)

- **W=0.30/S=0.10 USB diff pair** — original spec was set by analytical
  H-J; never validated by 3D field solver. openEMS sign-off (2026-05-22)
  showed Z_diff = 70 Ω (below USB-2 -15% floor). Root fix: corrected
  geometry to W=0.20/S=0.13 (openEMS = 87.4 Ω); `docs/CONTROLLED_IMPEDANCE.md`
  rewritten with the openEMS-vs-analytical discrepancy explained.
  *Not* a stopgap (e.g., would have been "accept 70 Ω, USB might work").

- **F-zone routing whack-a-mole** — successive DRC fixes around U5
  each surfaced a new adjacent conflict. Root cause: F-zone placement
  was too tight (U5 IN the diff-pair Y corridor). Root fix: re-open
  Step 3, move U5 south. *Not* a stopgap (e.g., would have been
  Freerouting on the over-constrained region, which would have struggled
  the same way).

- **Bridges omitted** (PROPOSED but REJECTED by master) — would have
  been classic patch: USB-C cable works in only one orientation.
  Root fix: offset bridge vias OUTSIDE the 0.5mm-pitch pad field (option
  b). Kept both orientations functional.

## Modifying this file

Change to any commitment above requires:
- A PR to this file
- Technical justification in the PR description
- Explicit user approval in the PR

This is deliberately heavy. The point is durability — if commitments can be quietly edited, they aren't commitments.
