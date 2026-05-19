# Design phases — novapcb FC v1

> **This is the canonical execution plan.** All design-time work lives
> in one of the phases below. If a task doesn't fit a phase, raise the
> question rather than improvising — chat-only phase labels evaporate
> across sessions and across Pis. See CLAUDE.md §6.3 for the *hardware
> bring-up* phases that begin once a real PCB exists; this doc covers
> everything *before* that.

Status as of 2026-05-18: Phase 1 in PR review. Phase 0 closed.
Everything from Phase 2 onward unstarted.

## Phase 0 — Toolchain (DONE)

- KiCad 9.x installed on novarobotics64.
- ArduPilot cloned at `~/ardupilot` with submodules.
- MatekH743 reference builds clean (Task 3, 2026-05-18) — baseline.

## Phase 0.5 — Sim toolchain (DEFERRED — install just-in-time before Phase 6)

Per ENGINEERING_RIGOR.md and worker recommendation 2026-05-19, the sim toolchain install is deferred from Phase 0 until just before Phase 6 starts. This avoids paying apt/pip cost (and OpenEMS install-flakiness risk) for tools that won't be used for many hours of Phase 2-5 work.

Full tool list and acceptance criteria live in `docs/SIMULATION_PLAN.md` "Stage 0.5 prerequisite — sim toolchain install" section.

Acceptance: every tool's hello-world produces expected output; results committed to `sims/TOOLCHAIN.md`.

## Phase 1 — Identity fork (IN REVIEW)

- `firmware/hwdef-novapcb/` exists, forked from MatekH743.
- Board name = `novapcb-v1`, `APJ_BOARD_ID` set, `USB_VENDOR_STRING`
  starts with `ArduPilot`, `USB_PRODUCT_STRING` = `novapcb-v1`.
- Pin map, sensors, peripherals: unchanged from MatekH743 by design.
- Build hash baseline in `firmware/hwdef-novapcb/BUILD_BASELINE.md`.
- Acceptance: `./waf copter` clean; `arducopter.apj` reports the new
  board_id; diff confined to `firmware/`.

## Phase 2 — Pin map + sensor selection (NOT STARTED)

The largest phase. Each sub-phase = one PR. Each PR changes hwdef.dat
pins/driver lines and updates `BUILD_BASELINE.md` so the cumulative
delta from Phase 1 is diffable.

| Sub-phase | What changes in hwdef.dat | Acceptance |
|---|---|---|
| 2a — IMU primary | swap to ICM-42688-P; SPI bus + CS + DRDY pins | build clean; IMU driver loads in sim if testable |
| 2b — Barometer | swap to DPS310; I²C addr per SDO pin | build clean |
| 2c — Mag (external) | IST8310 over the GPS-port I²C; no internal mag | build clean |
| 2d — GPS port | UART for GPS + I²C for compass (Pixhawk-style header) | build clean |
| 2e — ESC outputs | 8 channels; PWM timer + DMA stream per H743 alt-func | build clean; verify pins are DShot-capable |
| 2f — CRSF UART | UART for external ELRS RX (5 V tolerant, half-duplex) | build clean |
| 2g — Power monitor | VBAT_PIN + CURRENT_PIN ADC for external Mauch | build clean |
| 2h — USB + SDMMC | finalize USB strings; SDMMC pins for microSD | build clean |
| 2-exit — strip Matek-only peripherals | drop drivers we don't use | flash budget headroom recovered |

Acceptance for the whole Phase 2: every sub-phase PR merged; final
hwdef.dat reflects v1's actual design (not MatekH743); cumulative
flash delta tracked in BUILD_BASELINE.md.

## Phase 2.5 — Footprint reality check (NEW, before Phase 3)

Per worker recommendation 2026-05-19. Doc-only KiCad sketch — placement only, no schematic. Catches "do all selected peripherals + connectors actually fit on 30.5 × 30.5 mm with M3 mounting holes?" CHEAP, before Phase 3 schematic decisions cascade.

Scope:
- Initialize a throwaway KiCad project (`hardware/kicad/footprint-check/` — gitignored once Phase 3 starts, only for this check)
- Drop footprints for: STM32H743V (LQFP-100), ICM-42688-P, DPS310, IST8310 (off-board via GPS header), USB-C connector, microSD socket, 4× JST-GH (per DECISIONS.md §7) for power/GPS/CRSF/I²C compass, 8× ESC pads (or JST-SH if connectorized), debug header
- Verify all fit within 30.5 × 30.5 mm outline with M3 mounting hole pattern preserved
- Document findings in `hardware/kicad/footprint-check/notes.md`

If layout doesn't fit:
- Reduce ESC connector type (JST-SH solder pads instead of JST-GH) OR
- Reduce peripheral set (drop microSD, route mag to GPS header only) OR
- Escalate to supermaster: form factor revisit (DECISIONS.md §2 may need v1 revision)

Acceptance: a placement plot showing all components fit, OR a documented constraint that forces a Phase 2.5 escalation.

## Phase 3 — Schematic in KiCad (NOT STARTED)

- `hardware/kicad/novapcb.kicad_pro` initialized.
- Hierarchical sheets per subsystem: MCU, IMU, baro+mag, GPS+CAN,
  USB+SD, ESC, power, debug header.
- Symbol library committed at `hardware/kicad/lib/` (in-repo, not
  global KiCad libs — reproducible on any clone).
- Net names mirror Phase 2's hwdef.dat pin assignments — the hwdef is
  the contract; the schematic just lays it out.
- Acceptance: ERC clean; schematic netlist consistent with hwdef.dat.

## Phase 3.5 — Reference design audit (NEW, before Phase 4)

Before laying out copper, lift verbatim what's been proven. For each subsystem in CONFIDENCE_MAP.md, compare our schematic against ≥3 open-schematic FCs:

| Rule | Action |
|---|---|
| ≥3 references agree on a value/topology | Our design **must** match. No "improvement" without an explicit risk note. |
| References diverge | Pick one, document why. Diff becomes part of CONFIDENCE_MAP row evidence. |
| No reference exists | Subsystem is novel. Confidence drops to LOW automatically. |

Reference designs to compare against: MatekH743 (primary, since DECISIONS.md §2 v1 forks from it), Pixhawk6X (for parts where 6X happens to use similar single-PCB topology), Pixhawk6C, Mateksys H743-Slim.

Output: `docs/REFERENCE_AUDIT.md` with one section per subsystem. Becomes input to Phase 4 layout.

This single phase is probably worth more than half of the simulation regime — most novapcb subsystems are already solved problems and we shouldn't redesign them.

## Phase 4 — PCB layout (NOT STARTED)

- 30.5 × 30.5 mm outline, M3 mounting holes (DECISIONS.md §2 v1).
- 4-layer stackup (DECISIONS.md §8).
- IMU placement sits over the clean ground plane.
- USB-C connector edge-mount; microSD edge or under-mount as layout
  permits.
- JST-GH connectors per DECISIONS.md §7.
- Acceptance: DRC clean; 3D view inspected; mechanical envelope
  matches the planned mounting tray.

## Phase 5 — BOM finalization (NOT STARTED)

- `bom/v1.csv`: one row per line item with footprint, manufacturer
  part, alt parts, sourcing URL, last-checked price + date.
- Cost target: track against ~$70-100/board BOM (DIY).
- Every internal part number resolves to a real supplier with stock.
- Acceptance: every footprint in the schematic has a BOM row; total
  cost documented.

## Phase 6 — Simulation regime (NOT STARTED — GO/NO-GO GATE)

See `docs/SIMULATION_PLAN.md` for the per-subsystem detail. Phase 6 loops back to Phase 4 on any sim failure — that re-loop is expected, not a project failure (see ENGINEERING_RIGOR.md commitment #5).

Sub-phases (each its own PR, each writes to `sims/<subsystem>/`):

| Sub | Subsystem | Primary tool |
|---|---|---|
| 6a | Power tree | ngspice + PySpice |
| 6b | USB-CDC diff pair | KiCad impedance + OpenEMS |
| 6c | IMU SPI bus | ngspice + IBIS |
| 6d | I²C buses (baro / mag) | ngspice |
| 6e | UARTs (GPS, CRSF) | ngspice |
| 6f | SDMMC (SDR25) | ngspice + IBIS |
| 6g | ESC DShot outputs | ngspice + IBIS |
| 6h | VBAT divider + current sense | ngspice + noise analysis |
| 6i | Reverse polarity + ESD protection | ngspice transient |
| 6j | Thermal steady-state | Elmer FEM |
| 6k | EMC / clock-harmonic estimate | analytical Python + OpenEMS spot |
| 6l | ArduPilot SITL — functional regression | SITL |
| 6m | Manufacturability — DRC/ERC/DFM/BOM cross-check | KiCad + interactiveHtmlBom |

Every sub runs at three corners: nominal, hot (40 °C / max load), cold (0 °C / min VBAT). Monte Carlo (±10 %) on critical analog paths.

Acceptance: every sub-phase PR merged into main; CONFIDENCE_MAP.md updated cumulatively with evidence per row.

## Phase 6.5 — Forum review (NEW, mandatory for LOW-confidence rows)

Post schematic + sim results to ArduPilot Hardware forum and RC Groups Custom FC thread. **Mandatory** for every LOW-confidence subsystem in `CONFIDENCE_MAP.md`; optional for HIGH-confidence rows. Findings tracked per-subsystem; address before Phase 7.

Adds ~1 week. Costs zero dollars. Strong signal multiplier on LOW-confidence subsystems (currently: reverse-polarity protection, EMC, plus whatever else moves to LOW between now and Phase 6 close).

## Phase 7 — Fab order (NOT STARTED)

- Generate gerbers, drill, pick-and-place files.
- Place PCB order (default JLCPCB 4-layer, ~$20-50 for 5 boards).
- Place stencil order (~$20).
- Execute BOM (parts ordered).
- Acceptance: orders placed, tracking recorded, ETA on calendar.

## Phase 8 — Assembly (NOT STARTED)

- DIY hand-assembly (default for v1) or SMT-house (~$80-150/board).
- Continuity check on power rails BEFORE first power-up.
- Acceptance: ≥1 fully populated board; visual + multimeter pass.

## Phase 9 — Bring-up

CLAUDE.md §6.3 takes over from here (LED blink → … → free flight).

## Rules of progress

- Acceptance criteria above are not aspirational — they gate phase
  transitions. State explicitly what was checked (Rule 6).
- No phase skipping. Phase 3 needs Phase 2 closed. Phase 4 needs
  Phase 3 closed.
- One sub-phase = one PR. Branch naming:
  - firmware: `fw/hwdef-phase2<x>-<slug>`
  - layout: `hw/layout-<area>`
  - bom: `bom/<delta>`
- Work that doesn't fit a phase: raise in `docs/OPEN_QUESTIONS.md`,
  don't tack it on inside an existing phase.
- **This doc is the source of truth.** Chat-only phase labels do not
  count until they land here.
