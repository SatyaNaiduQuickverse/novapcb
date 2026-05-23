# Master Process Rules — committed, reviewable, evergreen

> **Status**: rules adopted from pcb.ai master + extended by novapcb master
> 2026-05-23. Evergreen — applies to every PR, every sub-phase, every
> integration step. Failure to follow = grounds for PR rejection.
>
> See also: `docs/ENGINEERING_RIGOR.md` for design-quality commitments,
> `docs/PLACEMENT_ROUTING_GATES.md` for the 14 numbered placement/routing/DRC
> gates, and `CLAUDE.md` §7 for working-style rules.

---

## Rule 1 — Read before acting

Before committing, restructuring, or picking a target directory, survey the
related repos. If the target is ambiguous, ask — don't guess. Specific
applications:

- For thermal sims: literal exec command MUST be documented (script path,
  CLI args, env vars). If not documented, that's a gate finding —
  reproducibility is gate-zero.
- For commit references: re-state the sha + branch + remote.

## Rule 2 — Document the contract before writing code

For features crossing system boundaries (USB / I²C / SPI / GPIO / network /
IPC / ROS topic): write or update a contract doc (`docs/INTERFACE_CONTRACT.md`
or feature-specific) BEFORE writing code. Code follows the doc, not the
reverse.

## Rule 3 — Never invent technical specifics from training data

Pin maps, baud rates, register addresses, GATT UUIDs, packet layouts — pull
from project files (`docs/INTERFACE_CONTRACT.md`, `~/drone_handoff/PROMPT.md`,
source code, datasheets). If the number can't be sourced, say "I don't know
this — where should I look?" Don't pattern-match plausible numbers; in this
domain that's how drones crash.

## Rule 4 — Match scope to the request — DISCLOSE SPEC DEVIATIONS

Implementation may diverge from spec when geometry / DRC / fab capability
demand. EVERY deviation must be disclosed in the PR doc:

- WHAT the spec said
- WHAT was actually built
- WHY they differ
- WHO approved (master sign-off if outside normal scope)

Examples of deviations to disclose:
- Component position differs from approved placement
- DRU rule relax adopted for routing
- Fab-process bump required
- Net deferred to a later sub-step

A PR without spec-deviation disclosure is incomplete.

## Rule 5 — For UI / build / hardware changes, actually RUN it

Type-checking and tests verify CORRECTNESS, not FEATURE correctness. Specific
for novapcb:
- KiCad changes: open project, run DRC, run ERC, look at 3D view.
- Firmware: flash to hardware.
- Doc changes: verify referenced files exist at the cited paths.

If you can't run the check, say so explicitly — don't claim success you
didn't verify.

## Rule 6 — Self-validate, the user does not review technical details

Before declaring a task done:
1. Run build/DRC/ERC/tests/lint as applicable.
2. Read diff line-by-line.
3. Cross-check against `INTERFACE_CONTRACT` / `DECISIONS` for wire-level
   constraints.
4. State explicitly in final message what was checked.
5. If a step was skipped, say which and why.

## Rule 7 — Confirm before destructive / shared-state actions

Authorization for one push is not authorization for the next. Confirm
before:
- `git push --force`, `git reset --hard`, `gh repo delete`, `git clean -fdx`
- Branch deletion (local or remote)
- Modifying CI / GitHub Actions / branch protection
- Anything sent to a phone / drone / remote service
- Fab orders

PR doc 4-section requirement (adopted 2026-05-23 from pcb.ai):
- **Symptom**: what was broken / observed
- **Fix**: what was changed
- **Root cause**: why it was broken (the underlying issue, not the symptom)
- **Prevention**: how to avoid the next instance

## Rule 8 — Redo, don't mitigate

When a constraint genuinely conflicts with the design, the right move is to
redo the design, not pile on mitigations:
- 4 fab exceptions in a single region = stop, escalate, consider re-place.
- Routing iteration count > 3 on one conflict = stop, escalate, consider
  placement change.

Each individual mitigation is justifiable; the accretion is the signal.

## Rule 9 — Trust the ARTIFACT, not the tool exit code

DRC GREEN is necessary but not sufficient. Verify the ARTIFACT (the gerber,
the pcbnew net connectivity, the simulation output), not just the tool exit
code.

Specific patterns master has caught (2026-05-23):
- Net "logically connected" per KiCad ≠ "physically routed" → cluster-walker
  on pads+tracks+vias.
- Zone "declared" ≠ "filled" → `pcbnew.Zone.GetFilledArea() > 0`.
- DRC "track has unconnected end" at T-junction → KiCad pedantic; verify
  via gerber visual inspection.
- Thermal sim "MCU=73.98°C" claim ≠ reproducible → run on actual board, not
  planned positions. (Caught 2026-05-23 — board sized on unreproducible
  claim.)

Per Rule 9: artifact-level verification is mandatory for any claim that
gates downstream work.

## Rule 10 — Comments are for non-obvious WHY, not WHAT

Don't comment `// read CRSF channel` above `read_crsf_channel()`. Do comment
the hidden constraint, vendor quirk, regulatory limit, or past-bug
prevention.

## Rule 11 — Memory hygiene

If the user corrects you, save the rule and the WHY. If user confirms a
non-obvious call, save that too. Save when a pattern emerges across
multiple iterations.

Don't save:
- Ephemeral task state (use task list).
- Things derivable from code / git.
- Things already in CLAUDE.md.

## Rule 12 — Communicate tightly

- End-of-turn: 1-2 sentences. What changed, what's next.
- Working: one sentence at find/change-direction/blocker. Brief beats silent.
- Don't narrate internal deliberation. State results.
- File:line references for navigability.

## Rule 13 — Stop and ask when ambiguous

If "go ahead" has 3 plausible meanings, pick the most likely and STATE
which one before acting — give the user one round to redirect cheaply.

Pre-Rule-13 grep: before drafting an option-set, grep DECISIONS /
INTERFACE_CONTRACT / OPEN_QUESTIONS. Often the answer is pinned and
reframes the option-set.

## Rule 14 — Never bypass safety / quality checks

No `git commit --no-verify`. No `--skip-tests`. No `// @ts-ignore` without
reason. If a hook fails, diagnose; don't bypass.

## Rule 15 — Don't write code the user didn't ask for

If user asks "what do you think about X", that is a discussion, not
permission to implement X. Discuss in 2-3 sentences with recommendation.
Implement only after user agrees.

## Rule 16 — Be careful with auto-memory in shared contexts

Personal preferences belong in memory; project rules belong in committed
docs. CLAUDE.md is the line between the two.

## Rule 17 — No loose threads

Every loose end gets pulled and resolved before the design is called done —
never deferred without explicit tracking, never waved off as "probably
fine" or "the fab handles it", never compromised to hit a schedule. (Sai,
2026-05-21.)

---

## How rules apply to PR docs

EVERY PR description includes:

1. **Symptom** — observed problem (Rule 7 4-section)
2. **Fix** — what was changed
3. **Root cause** — why it broke
4. **Prevention** — how to avoid next time
5. **Spec deviations** (Rule 4) — every divergence from spec
6. **Rule 9 verification** — artifact-level proof (cluster walks, zone fill,
   gerber visual, etc.)
7. **Audit run** — `scripts/audit_layout_compliance.py` summary

PR without these = reviewer rejection.

---

## Cross-references

- Design phases: `docs/DESIGN_PHASES.md`
- Engineering rigor commitments: `docs/ENGINEERING_RIGOR.md`
- Placement/routing/DRC gates: `docs/PLACEMENT_ROUTING_GATES.md`
- Subsystem contracts: `docs/SUBSYSTEM_CONTRACTS.md`
- Locked v1 decisions: `docs/DECISIONS.md`
- Open questions: `docs/OPEN_QUESTIONS.md`
- Working-style rules (Claude session bootstrap): `CLAUDE.md` §7
