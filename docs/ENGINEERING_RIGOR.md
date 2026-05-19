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

## 7. Brutal honesty mode-locked

Reports state what was checked AND what was not. "Looks clean" without enumeration is a Rule 6 violation. Pushback over flattery, explicit gaps over false coverage, "I don't know" over confident filler.

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

## Modifying this file

Change to any commitment above requires:
- A PR to this file
- Technical justification in the PR description
- Explicit user approval in the PR

This is deliberately heavy. The point is durability — if commitments can be quietly edited, they aren't commitments.
