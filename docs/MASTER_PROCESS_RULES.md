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

**Rule 9 corollary — gate on the ELECTRICAL margin, not the paper-spec tightness.**
A match/skew/clearance gate inherited as a fixed number may be far tighter than
the physics requires. When a converged result "fails" such a gate, compute the
actual margin from first principles before re-working:
- microSD SDMMC1 @ 48 MHz (CAN/microSD routing, 2026-05-26): the inherited
  ±0.5mm (then ±5/±10mm) length-match gate vs reality — 25.9mm skew = 180 ps =
  9% of the ~2000 ps setup/hold window → **91% timing margin remaining**. The
  paper-spec "FAIL" was not an electrical fail; the Freerouting result was
  accepted rather than re-routing 3 nets through a dense corridor for a
  marginal, already-ample improvement.
Set match/skew gates from clock + setup/hold math; accept an auto-route within
the electrical margin even if it exceeds the spec-doc number. Re-derive per
interface — a higher-speed v2 bus needs its own (tighter) budget.

(Master + worker, 2026-05-26 — microSD routing.)

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

## Rule 18 — Fanout-reach audits enumerate TRACKS AND COMPONENT PADS

When auditing whether a net can fan out from MCU pin to a destination
connector / sensor, **both existing tracks AND component pads in the
corridor are physical obstacles**. Track-only surveys miss decap
halos, sensor pads, crystal pads, connector pads — all of which block
routing at DRC clearance distance.

Caught in H↔C 2× escalation 2026-05-24: original analysis surveyed
fanout corridor for tracks (found clean), missed 8 caps + crystal +
R2 at MCU west edge (X=33..37 Y=25..50) that physically blocked MOT3-6
F.Cu fanout. Spent 3 routing iterations + 4 hours discovering this.

**Checklist for every up-front fanout analysis:**
1. Survey all F.Cu / B.Cu tracks in corridor (start..end)
2. Survey all component pads in corridor (footprint + footprint bbox)
3. Survey existing vias in corridor (intersect all layers)
4. State the corridor clearance budget vs net width + clearance × N nets

(Master, 2026-05-24.)

## Rule 19 — Fanout-reach audits also enumerate EXISTING ROUTED NETS

Rule 18 + 19 are siblings: Rule 18 covers component obstacles; Rule 19
covers ROUTING obstacles. A net that can geometrically reach its
destination but must cross dense existing routing has the same problem
as one blocked by component pads. The corridor must have ENOUGH SPACE
for the new nets to thread between the existing ones.

Caught in pin-remap PR 3rd routing iteration 2026-05-24: after MCU
pin remap moved MOT3-6 from west-edge to south-edge pads (Rule 18
constraints satisfied), routing STILL failed because existing
I2C2 SCL/SDA (E-going to baro) + SPI1 MISO/MOSI/SCK (S-going to IMU)
traces at Y=44..48 constrict the south corridor that 6 new MOT* nets
+ 1 IMU3_INT1 needed to traverse.

**Checklist additions to Rule 18:**
5. Enumerate all routed nets currently in the corridor (by net name + path)
6. Compute total trace lane count in narrowest cross-section vs
   available width × (track + clearance)
7. Flag any cross-section that cannot accommodate the planned new
   nets without re-routing existing — escalate before commit

When the constraint isn't met, options (in order of preference):
- (a) Pick a different fanout corridor (different MCU pin set, different
  destination, different layer)
- (b) Re-route the existing constricting nets to vacate the corridor
  (touches their PRs — regression risk; coordinate with original sub-step)
- (c) Accept layer-split with documented DRU exceptions if both fail

(Master, 2026-05-24 — pin-remap PR 3rd-iteration failure was the source.)

## Rule 18 refinement — "component pads" means EVERY pad-class obstacle

The CAN routing PR (2026-05-26) hit the Rule-18 gap THREE more times because
surveys still under-enumerated. "Component pads" must be read literally as
**all pad-class and through-class obstacles**, by FOOTPRINT REFERENCE:
- footprint pads — including 2-pad passive filters (**ferrite beads** like FB2,
  whose body looked like "a +3V3 via" until the survey mis-read it)
- **vias** — signal vias AND **GND-stitch via grids** from the plane PRs
  (a "clear lane" by track count plowed a 4-via GND grid row)
- **PTH holes** — e.g. connector shield/mount pads (J1 USB-C shield PTH at
  Y=34.32 blocked a routing lane on ALL layers)
- long MCU pads — LQFP-100 pads are **1.6 mm long**; a via could not fit
  between the pad north-edge and an adjacent track (0.86 mm < 0.9 mm)

Survey method: enumerate every FOOTPRINT with a pad in the window (not by net,
not by feature class), plus all vias, plus the GND-fill grid. Pure track
inventory misses all of the above.

(Master + worker, 2026-05-26 — CAN routing.)

## Rule 20 — Move the passive before moving the trace

When a routing problem is caused by a **passive-component obstruction**
(resistor, capacitor, ferrite bead, ESD/TVS diode — non-active filter/
protection parts), evaluate **moving the passive BEFORE** re-routing the
trace, layer-splitting, or adding DRU exceptions. A passive's position is
rarely load-bearing on net topology; it is mechanically movable, especially
in non-critical RF/corner areas. Moving one 2-pad part is far lower risk than
a re-route cascade through already-merged work.

Evidence (all this project): R11/R12 I²C pulls (pin-remap prep), FB2 IMU-rail
ferrite (CAN — keystone blocker over the peripheral-locked RX pad), R45/R46
CAN termination (flip 180° fixed the TERM_MID tangle), U15 CAN ESD (reposition
opened the bus daisy). Each unblocked a problem that resisted trace-level
fixes.

Order of preference when a passive blocks: (1) move/reorient the passive +
re-route its short legs + re-verify its rail; (2) re-route the signal; (3)
layer-split; (4) DRU exception. Always re-verify the moved passive's own net
(e.g. FB2 move required a +3V3_IMU rail cluster-walk).

(Master proposed + worker formalized, 2026-05-26 — CAN routing.)

## Symmetry refinements (pcb.ai R1/R2/R3 — adopted 2026-05-23)

Reinforcement of the existing "symmetry as explicit transforms" rule
(Rule 2). pcb.ai master delivered three refinements 2026-05-23 caught
during PR-A4-integrate review. Adopted into novapcb's audit script +
docs same day.

### R1 — 3-bucket quadrant-balance classifier

Replace the flat "≤2 NW/NE/SW/SE component-count delta" check with three
buckets that match how components actually relate to placement intent:

- **MIRROR_PAIR bucket** — named pair components mirrored across the
  board midline (novapcb: 11 pairs listed in
  `scripts/audit_layout_compliance.py:A_MIRROR_PAIRS`). Subject to the
  strict ≤0.5mm pair-delta rule (R2 below).
- **SINGLE_INSTANCE bucket** — components with NO mirror partner BY
  DESIGN (MCU, USB, eFuse, IMU island, single connectors, etc).
  **EXEMPT** from symmetry — central-spine placement is correct by
  function. Forcing mirror would break electrical role.
- **AUTO bucket** — generic debris (IC decoupling, pull resistors,
  test points). **WARN-only** with structural reason required in PR
  doc when quadrant counts imbalance.

Why: one flat threshold misses real channel asymmetry while flagging
acceptable debris imbalance.

### R2 — Mirror-pair symmetry has ZERO threshold relaxation

For MIRROR_PAIR bucket: pair-delta MUST be ≤0.5mm (novapcb spec; pcb.ai
uses ≤2 component-count delta for their CHANNEL bucket — semantics
identical: mirror is the CONTRACT). If a mirror pair deviates, REDO
without hesitation — this is what makes per-pair/per-channel sims
compose to whole-board. Don't trade it away for debris-balance metrics.

`scripts/audit_layout_compliance.py:check_a_symmetry()` enforces this
as a HARD FAIL (raised from WARN 2026-05-23 per pcb.ai R2 adoption).

### R3 — Structural-asymmetry doctrine

When components have NO mirror partner BY DESIGN (unique-net debug TPs,
single-instance IC decoupling, RESET/BOOT0 pulls), forcing mirror would
violate the decoupling/passive-distance rule (≤8mm from parent IC) which
BREAKS electrical function.

Accept structural asymmetry. Document the reason in PR doc. Do NOT
contort placement to satisfy unattainable balance. Engineering reality
> visual aesthetic.

Cross-ref: `scripts/audit_layout_compliance.py:SINGLE_INSTANCE` is the
explicit exempt list for novapcb (~20 refs as of 2026-05-23).

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
