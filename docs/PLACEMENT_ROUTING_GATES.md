# PLACEMENT, ROUTING, SIM-VALIDATION & DRC GATES — novapcb v1.1+

> **Status:** governing process for ALL placement/routing work on novapcb,
> effective 2026-05-22. Sourced from the more-mature pcb.ai project;
> Gates 6 and 7 adapted for the FC context. Dispatched by master.
>
> **Rationale.** The one-shot place-everything-then-Freeroute approach is
> why R1..R4 routing became a saga. The sim-iteration phase (Phase 6
> thermal, EMI, SI) **WILL** drive placement/routing changes; with a
> one-shot route, each change is a multi-day re-grind. These 12 gates
> impose a subsystem-by-subsystem, gated workflow that makes each change
> a small, reviewable, recoverable PR.
>
> **Scope.** Every PR that touches `.kicad_pcb` placement, routing, OR
> cites a sim result as evidence must open and close all relevant gates
> in its description. Master audits at each gate; gate failures block
> merge regardless of how complete the rest of the PR looks. Sai
> sign-off is required for fab orders only (Phase 7b).
>
> **14 gates total:** 7 placement (1..7), 5 routing (8..12), 1
> sim-validation (13), 1 DRC (14). All apply at every
> placement/routing/integration PR scope where relevant.

---

## 0. Process model — INCREMENTAL INTEGRATION with continuous validation

> **Sai 2026-05-22 (verbatim direction).** The process is incremental
> integration with continuous validation — NOT "place all subsystems
> then route once." Conflicts surface early when only a few subsystems
> are present and are cheap to fix; not at the end where they cascade.

The flow per subsystem:

```
SKiDL netlist (immutable for v1.1)
   │
   ▼
SUBSYSTEM_CONTRACTS.md  ──── decompose into ~8 subsystems with
                             I/O contracts + CONFLICT-RISK rating
                             (low / high + aggressor/victim notes)
   │
   ▼
1. Place subsystem components properly, physics-reasoned, zero
   internal conflicts (Gates 1..7).
   │
   ▼
2. Classify by CONFLICT-RISK (per SUBSYSTEM_CONTRACTS).
      • LOW-conflict  = I/O connectors, USB (the connector itself),
                         CAN xcvr, microSD — don't strongly interfere
                         with neighbors.
      • HIGH-conflict = known aggressor↔victim pairs: power-section
                         switching+heat vs IMU island; ESC DShot edges
                         vs IMU; crystal vs sensitive sensors; CRSF
                         sub-GHz vs IMUs.
   │
   ▼
3. INTEGRATE INCREMENTALLY — grow the board subsystem by subsystem:
      a. Start from MCU_CORE (the hub).
      b. Add next subsystem ADJACENT to what's already integrated.
      c. Route the integration (cross-subsystem nets at this step).
      d. SIM the combination (thermal + EMI + SI for that step).
      e. If clean (all gates pass) → LOCK that subsystem.
      f. Otherwise: fix in this small two-subsystem context (not at
         end where it cascades).
      g. Add next subsystem. Repeat.
   │
   ▼
4. INTEGRATION ORDER (set by master after reading SUBSYSTEM_CONTRACTS):
      LOW-conflict subsystems first — they go in cleanly, accumulate
      placement context.
      HIGH-conflict subsystems ONE AT A TIME — each with sim-check
      after integration — so the aggressor↔victim pair under review
      shows up in isolation.
   │
   ▼
5. FULL-BOARD SIM SUITE at the very end — complete thermal / EMI /
   SI / structural — final validation + data.
```

**Why this:** R1..R4 was "place everything then Freeroute" — one-shot,
conflicts compounded, fixes cost days each. Incremental integration
keeps each step's blast radius bounded; the sim-iteration phase is
woven into the build, not a cliff at the end.

**Every step is gated.** Every integration step (one new subsystem
added to the locked stack) is held to the same 13 gates — including
the sim-validation gate (Gate 13). No subsystem locks without passing
all gates that apply at its scope.

Each subsystem PR + each integration-step PR is independently
revertible. Sims re-run per-subsystem-or-integration-step, never the
whole board until step 5.

---

## PLACEMENT GATES (7)

### Gate 1 — Bbox-overlap check (component-body, not pad)

Every PR that places or moves a component runs a body-intersection check
using `pcbnew.BOX2I::Intersects()` on the **footprint courtyard** (not
just pad-collision). Two parts whose pads don't touch but whose bodies
overlap is still a fab-blocker — the pick-and-place head can't physically
place a part on top of another, and the design will be rejected at DFM.

**Self-test requirement.** The verifier must be run against a known-bad
input (two parts deliberately overlapped) BEFORE running it on the real
PR — to prove the verifier can fail. A green verifier that has never
failed is unfalsifiable. The PR description must show the self-test
output.

**Acceptance:** the green output of the verifier on the actual PR + the
red output of the same verifier on the deliberate-bad self-test.

### Gate 2 — 3D-render PNG on every placement PR

Every PR that touches placement must attach `render_top.png` and
`render_bot.png` generated by `kicad-cli pcb render`. Master eyeballs
these at audit — many issues (component clearance, polarity marks
visible, MCU thermal pad orientation, connector mech access) are caught
visually that DRC misses.

**Acceptance:** both PNGs in the PR, rendered from HEAD of the PR
branch.

### Gate 3 — Component uniqueness in `.kicad_pcb`

Every component in the SKiDL netlist must appear in `.kicad_pcb`
**exactly once**, at a unique position (no two footprints at the same
coords, no missing refdes from the netlist). This counters the
`kinet2pcb` silent-drop trap that was caught multiple times in R1..R4 —
the tool reports success even when it silently dropped a component.

**Acceptance:** a `verify_uniqueness.py` run that parses the netlist
and the `.kicad_pcb` and reports `MATCHED N components, 0 missing, 0
duplicate`. The PR description quotes that line.

### Gate 4 — Trust the ARTIFACT, not the tool exit code

`place_board.py --verify` reports "0 unplaced, 0 overlaps". So does a
broken verifier. **Believe only what you can `grep` out of the
`.kicad_pcb`.** Every PR that claims a placement metric ("0 overlaps",
"N components placed", "X DRC clean") must produce that metric by
parsing the artifact itself, not by relying on the placer/router's exit
code.

**Acceptance:** the metric claim in the PR description is accompanied
by the exact `grep` / `python3 -c` command that produced it, run
against the PR's `.kicad_pcb`.

### Gate 5 — Subsystem-by-subsystem placement (one PR per subsystem)

Place one subsystem per PR. The subsystem is defined in
`SUBSYSTEM_CONTRACTS.md` with explicit I/O contracts (named input nets,
named output nets, assigned board zone, adjacency requirements vs. other
subsystems). **No PR places "all the rest of the components in one
sweep"** — that's what created the R1..R4 mess. Even the MCU core
(which feels like one block) is its own PR with its own gate evidence.

The PR description states:
- Which subsystem
- Which input nets enter the zone
- Which output nets leave the zone
- Which subsystems this one is adjacent to + why
- Components placed (refdes list)

**Acceptance:** PR is scoped to a single subsystem from
`SUBSYSTEM_CONTRACTS.md`; the contract terms above are quoted in the
description; the placement honors the assigned zone (verified via Gate
4 grep of footprint coords).

### Gate 6 — Anchor on real premium FC teardowns (FC-adapted)

Before placing **any** subsystem on novapcb v1.1, the PR's design
notes must reference at least **two** teardowns from premium flight
controllers in the same class — Pixhawk 6X (FMUv6X), mRo Control Zero
H7, Holybro Kakute H7 / Kakute H7 V2, Matek H743-Slim. The PR cites:

- Where the subsystem is placed on the reference board (image link or
  layer-by-layer photo)
- What adjacent subsystems flank it on the reference (EMI sensitivity)
- Any layout-specific notes the reference photographer / vendor docs
  call out (e.g. "isolated IMU board", "thermal vias under LDO",
  "GND-via fence around CRSF UART")

This is the FC-adapted version of the pcb.ai gate "anchor on real
hardware before committing an architecture." For us, real hardware =
shipping premium FCs that the surrounding Nova stack already validates
against.

**Acceptance:** the PR design notes cite ≥2 reference teardowns by
name + link, with the cited layout choice.

### Gate 7 — Thermal vias under power-dissipating parts (FC-adapted)

Every PR that places a power-dissipating part must include a thermal
via array under its exposed pad (or beside the part if no exposed
pad). Specifically for novapcb v1.1:

- **U2** (main +3V3 LDO, 250-500 mW typical): ≥9 thermal vias under
  the pad
- **U13** (+3V3_IMU LDO, ≤100 mW): ≥4 thermal vias
- **U6** (eFuse, full power path): ≥9 thermal vias
- **Q3/Q4** (OR-ing FETs, full 5V current): ≥4 thermal vias each
- **U1** (MCU, ≤500 mW under load): ≥9 thermal vias under exposed pad
- **U3/U8/U9** (IMUs, ≤10 mW each): not required but encouraged

The PR description quotes the via count per part as produced by a grep
of the `.kicad_pcb` near each footprint.

**Acceptance:** thermal via count per part listed in PR + via-array
visible in the Gate-2 3D render.

---

## ROUTING GATES (5)

### Gate 8 — Density-score multi-resolution

Every routing PR must report routing density at three resolutions:
- **Whole-board** (1 cell = whole board): single scalar
- **4-quadrant** (board split into 2×2): four scalars
- **Per-cluster** (16-30 cells across the dense regions): a heatmap

All three must pass the **0.85 threshold**. Whole-board alone hides
cluster hotspots — the R3 / R4 saga had whole-board=0.91 but cluster
hotspots peaking at 1.05+ that no one saw. The per-cluster check
exposes those.

**Acceptance:** the density JSON / heatmap PNG is in the PR. All values
≤ 0.85.

### Gate 9 — Pre-route smoke test with `-mp 5`

Before running a full `-mp 30` Freerouting pass, run a `-mp 5` smoke
test on the placement. This is a quick (~30-60 sec) preview — if `-mp
5` is at 50% routed, `-mp 30` will likely top out at 70-80% and waste
hours. If `-mp 5` is at 90%+, full `-mp 30` is worth running.

**Acceptance:** PR description includes the `-mp 5` smoke result line
(routed % + unconnected count), and a one-line justification for whether
to proceed to `-mp 30` or fix placement first.

### Gate 10 — Failing-net geographic mapping

When a routing pass leaves residuals, the PR must parse the
Freerouting log, extract incomplete-net endpoints, and map them onto
cluster cells from Gate 8. This surfaces **where** the routing failed
(usually a specific cluster), not just **how many** failed.

**Acceptance:** a `failing_nets.json` (per-net: net name, endpoint
coords, cluster cell) attached to the PR; the cluster cells with
failures highlighted on the Gate 8 heatmap.

### Gate 11 — Freerouting flag literacy

- `-mp N` = **N PASSES**, not "N minutes". A pass is a single
  optimization sweep; in production-typical board complexity ~30 passes
  is the convergence point.
- `-t SECS` = **time budget**. Use this when you want a hard cap on
  runtime (e.g. CI). It will terminate Freerouting before it finishes,
  yielding partial SES (or no SES if cut too short — see
  `feedback_no_timeout_kill_freerouting`).
- **SES is written only on natural completion.** A killed Freerouting
  process produces no SES. Timeouts must be safety nets at 2-3× expected
  runtime, NEVER guillotines.

Every routing PR description states which flags were used and why.

**Acceptance:** the PR description quotes the exact `freerouting` (or
wrapper) invocation; if a timeout was used, it justifies the value as
≥2× expected runtime; SES file presence is verified before "done" is
claimed.

### Gate 12 — Per-subsystem (and per-integration-step) thermal sim + per-cluster density before LOCK

Before any subsystem's placement is **locked** (i.e. before merging
that subsystem's placement PR onto `hw/v1.1-respin`), the PR must run:

- The Phase 6 thermal sim restricted to that subsystem's components
  (Elmer FEM, validated per `sims/validation/VALIDATION_RESULTS.md` —
  tools must already pass their benchmarks)
- The Gate 8 density check at per-cluster resolution within the
  subsystem's zone

Sim-suite failures (T_junction > spec, density > 0.85, EMI clearance
violated) block merge. The sim suite is re-run when a downstream
subsystem changes anything that affects the subsystem under review.

**Acceptance:** thermal map PNG + density heatmap PNG in the PR;
T_junction worst-case quoted; cluster density worst-case quoted; both
within spec. The PR explicitly states whether this is a single-subsystem
sim or an integration-step sim (subsystem-N added to the locked
1..N-1 stack).

---

## SIM-VALIDATION GATE (1)

### Gate 13 — Sim validation: tool validated + run convergence-clean (HARD GATE)

> **Sai 2026-05-22 (verbatim).** "No sim verdict is trusted until its
> tool is validated AND the run is convergence-clean."

Two prerequisites that BOTH must be met for any sim verdict to count
toward gate acceptance (Gates 7 thermal-vias, 12 thermal+density,
or any Phase 6 sub-phase result):

**13.a — Tool pre-validated against a canonical benchmark.**

Every sim tool used on novapcb has a documented validation record in
`sims/validation/VALIDATION_RESULTS.md` showing it matches an
independent analytical / experimental reference within a published
tolerance. Status as of 2026-05-22:

| Tool | Benchmark | Error | Status |
|---|---|---|---|
| ngspice (PySpice) | RC transient (analytical V(τ)) | 0.022% | VALIDATED |
| scikit-rf MLine | microstrip Z₀ vs H-J 1980 | 1.03% | VALIDATED (1st-order only — see openEMS) |
| Elmer FEM thermal | 1D conduction analytical | 0.000% | VALIDATED |
| Elmer FEM structural | cantilever, Timoshenko | 0.51% | VALIDATED |
| openEMS FDTD | microstrip Z₀ vs H-J 1980 | 3.6% | VALIDATED (2026-05-22) |

If a new tool is introduced, its validation row lands in
`VALIDATION_RESULTS.md` **before** it is used in a gate decision. The
PR that introduces it cites the benchmark, the tool's result, the
reference value, the error %.

**13.b — Run convergence-clean.**

Every sim run cited as gate evidence shows:
- **Convergence check.** Mesh-refinement study (or equivalent
  discretization-independence check). Cite ≥2 mesh densities and the
  delta in the quantity of interest. If the delta is too large,
  refine and re-run. (Q1 shear-locking lesson — caught in Task 9 at
  NX=100/NY=5 = 2.0%; refined to NX=200/NY=20 = 0.51%. Discretization
  artifact, NOT tool error. Discipline always.)
- **Boundary conditions correct.** Stated explicitly in the PR: which
  edges are clamped / fixed / radiating / lossy / open / matched.
  Sanity-check that BCs reproduce the analytical case if applicable.
- **Cross-check against independent estimate.** Either an analytical
  closed-form (e.g. H-J microstrip), a second tool (e.g. scikit-rf
  parallel to openEMS), or a published reference (NAFEMS thermal,
  IPC for impedance). If only ONE tool is available, that's flagged
  honestly — verdict carries less weight until the second
  cross-check is added.

**Quick-and-dirty sims are NOT acceptable** for gate evidence. A 5%-
mesh-coarse run that "looks right" doesn't pass Gate 13.b. The
incremental-integration sims (per-subsystem, per-integration-step) are
held to this same standard — they are not exempt because they're
small.

**Acceptance:** PR description includes both the tool's
`VALIDATION_RESULTS.md` row (or link to it) and a one-paragraph
"convergence + BC + cross-check" note for the run. Reviewable in <2
minutes.

---

---

## DRC GATE (1)

### Gate 14 — KiCad DRC — 0 violations on-board (HARD GATE, mandatory for any PR touching .kicad_pcb)

> **Master 2026-05-22 (process fix after #67 audit miss):**
> "I accepted PR #67 (C↔E integration) WITHOUT a DRC run. 'Gate 4 GREEN
> — 7 tracks parse-verified' means the tracks EXIST in the file, NOT
> that they are DRC-clean. From here every integration audit includes
> the DRC result."

**Every** PR that touches `.kicad_pcb` (placement, routing, integration,
plane stitching, anything) must run `kicad-cli pcb drc` and report the
result. Two acceptance criteria:

**14.a — Zero "real" on-board violations.**

Filter the DRC report to **on-board** items only (any item whose
coordinate has X < 100 mm and Y < 100 mm — excludes the parked-area at
X ≥ 110 mm in the stepwise board). Of those, **zero** of every
category EXCEPT `unconnected_items`:
- `tracks_crossing`, `shorting_items`, `clearance`, `hole_clearance`,
  `drill_out_of_range`, `via_diameter`, `solder_mask_bridge`,
  `courtyards_overlap`, `copper_edge_clearance`, `starved_thermal`,
  `invalid_outline`, etc. — **zero**.

**14.b — `unconnected_items` are honest.**

`unconnected_items` are acceptable ONLY if they correspond to power
nets (+3V3, GND, +5V, +3V3A, etc.) that the cross-subsystem routing
PR will fill via plane zones, OR to signal nets explicitly deferred to
a later integration step (per `SUBSYSTEM_CONTRACTS.md`). The PR
description lists each unconnected net by name and which future
step/plane will satisfy it.

**Reproducible command:**
```bash
kicad-cli pcb drc --severity-error --format report \
  --output /tmp/drc.txt --units mm <board>.kicad_pcb
```

**Acceptance:** PR description includes the DRC summary line ("Found N
violations / N unconnected items") and the on-board / off-board /
unconnected breakdown from a parser (the PRs after 2026-05-22 use the
filter snippet in `hardware/kicad/novapcb-stepwise/gate14_drc.py`).

**Reviewer behavior:** if a PR claims a gate is GREEN without a DRC
run, the gate has NOT been verified — request the DRC output.
"Parse-verified" (tracks exist in the file) is **not** "DRC-clean".

---

## Lifecycle A — single-subsystem placement PR

```
Branch off hw/v1.1-respin
   │
   ▼
Place subsystem components (Gate 5)
   │
   ▼
Verify uniqueness + zone (Gates 3, 4)
   │
   ▼
Body-intersection check (Gate 1) + self-test
   │
   ▼
Thermal vias placed (Gate 7)
   │
   ▼
3D render top + bot (Gate 2)
   │
   ▼
Reference teardown notes (Gate 6)
   │
   ▼
Density smoke at per-cluster within zone (Gate 8 partial)
   │
   ▼
Internal routing (Gates 9, 10, 11)
   │
   ▼
Subsystem thermal + final density (Gate 12)  ──── uses Gate 13's
                                                 validated tools
                                                 + convergence-clean run
   │
   ▼
Master audits ALL applicable gates → merge → LOCK
```

## Lifecycle B — integration-step PR (subsystem-N added to locked 1..N-1)

```
Branch off hw/v1.1-respin (with subsystems 1..N-1 already locked)
   │
   ▼
Route the new cross-subsystem nets between N and the locked stack
(Gates 9, 10, 11 — partial scope: only the new nets at this step)
   │
   ▼
Density check at integration boundary (Gate 8 — per-cluster, the
seam between N and its neighbor)
   │
   ▼
SIM the combination:
   • Thermal for the union of N's components + immediate neighbor
   • EMI: aggressor↔victim pair specific to the conflict-risk pairing
   • SI: any new diff pair or sensitive trace crossing the seam
   (Gates 12 + 13 — convergence-clean, validated tools)
   │
   ▼
If any conflict (T_j over spec, EMI margin <6dB, SI eye closed) →
fix HERE (in the small 2-subsystem context, not at the end).
If clean → LOCK the integration.
   │
   ▼
Master audits → merge → LOCK subsystem N + its integration boundary
```

Locked subsystems and locked integration boundaries are immutable for
the rest of the design unless explicitly re-opened by master. Later
subsystems route THROUGH locked zones via short escape traces from the
locked boundary; they do not redo locked work.

---

## What this supersedes

The R1..R4 routing saga (commits up to `dfb0bba`) is **superseded**, not
salvaged. The 89%-routed `.kicad_pcb` and the interactive close-out
plan are reference material only. New work starts from a clean
placement on `hw/v1.1-respin` after `SUBSYSTEM_CONTRACTS.md` is
master-approved.

What IS preserved:
- The SKiDL netlist (sheets/*.py), including the v1.1 re-mux
  (SPI1_MOSI=PA7, HEATER_PWM=PA15, BUZZER=PD7)
- Parts and footprints (`hardware/kicad/novapcb/lib/`)
- The Phase 6 sim tools, all validated against benchmarks
  (`sims/validation/VALIDATION_RESULTS.md`)
- The locked decisions in `docs/DECISIONS.md`

What is NOT preserved:
- Any placement coordinates from R1..R4
- Any routing from R1..R4
- Any of the post-FR3 tooling (A* router, plane stitch, etc.) — those
  served their purpose; the new flow doesn't need them

---

## Glossary

- **`-mp N`**: Freerouting CLI flag for "maximum N optimization passes"
- **SES**: Specctra Session file — Freerouting's output format
- **DRC**: Design Rule Check (electrical)
- **Cluster**: a 16-30 cell square region of the board, used for
  density measurement at higher resolution than 4-quadrant
- **Subsystem**: a logically grouped set of components with a shared
  I/O contract, as defined in `SUBSYSTEM_CONTRACTS.md`
- **Lock**: a placement/routing PR that has passed all 12 gates and
  been merged — its coordinates are immutable thereafter

---

— end of PLACEMENT_ROUTING_GATES.md —
