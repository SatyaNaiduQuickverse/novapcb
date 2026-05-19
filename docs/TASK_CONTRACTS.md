# Task contracts — input/output segregation per sub-phase

Every sub-phase in `DESIGN_PHASES.md` is a *task* with a contract: one YAML file under `tasks/` declaring inputs, outputs, and pass criteria. A Claude picking up a task reads ONLY the contract + the files it lists. Never the whole project.

## Why

The project doc set is growing. No single context window holds "all of novapcb" cleanly. Contracts give:

- **Bounded read load** per task — the Claude doing Phase 6c reads its contract + 3-4 files. Not all 9+ docs.
- **Bounded write surface** — writes only the files declared in `outputs`. No drive-by edits to unrelated files.
- **Cross-task isolation** — 6c's effect on 6f is whatever 6c's `outputs` say it is, not "everything 6c happened to touch."

## Contract schema

`tasks/<task-id>.yaml`:

```
id: phase-6c-imu-spi
phase: 6
subphase: 6c
title: "IMU SPI bus signal integrity"
status: not_started   # not_started | in_progress | in_review | done | failed
depends_on:
  - phase-2a-imu-swap
  - phase-3-schematic-imu-sheet
inputs:
  files:
    - firmware/hwdef-novapcb/hwdef.dat
    - hardware/kicad/sheets/imu.sch
  refs:
    - "ICM-42688-P datasheet"
    - docs/CONFIDENCE_MAP.md  # row 4
    - docs/SIMULATION_PLAN.md  # §6c
outputs:
  files_created:
    - sims/imu-spi/setup.cir
    - sims/imu-spi/results.md
    - sims/imu-spi/plots/*.png
  files_modified:
    - docs/CONFIDENCE_MAP.md  # row 4 evidence note only
  pr:
    title: "Phase 6c: IMU SPI signal integrity sim"
    branch: sim/6c-imu-spi
pass_criteria:
  - "Rise/fall < 5 ns at 20 MHz SPI clock"
  - "Setup/hold margin > 2 ns at H743 input pins"
  - "No ringing past 200 mV at receiver"
estimated_context_kb: 50
estimated_wallclock: "1-2 hours"
```

## How a Claude uses this

1. On task start: read `tasks/<id>.yaml`. Read every file in `inputs.files`. Update `status: in_progress` in a tiny commit on the task branch.
2. Do the work declared. No more, no less.
3. Write files in `outputs.files_created`. Edit only files in `outputs.files_modified`, only at the locations declared.
4. Open the PR per `outputs.pr`. Update `status: in_review`.
5. Final commit message: explicit per-criterion pass/fail report.

## Contract creation cadence

Master creates the YAML under `tasks/` BEFORE assigning the work. Template at `tasks/_TEMPLATE.yaml`. Sub-phase prompts reference the contract by ID; they don't re-state the contract inline.

## Scope expansion

If actual work exceeds the contract, the contract is updated FIRST as a separate tiny PR (~10 lines diff). Then the work continues. No silent scope creep.

## When NOT to use a contract

Doc-only PRs with diff <50 lines touching one file: no contract needed — the diff IS the contract. Use contracts for any task that creates files, modifies multiple files, or runs simulations.
