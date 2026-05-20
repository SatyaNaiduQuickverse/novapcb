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

## Phase 2.5 — Footprint reality check (DONE 2026-05-20)

Per worker recommendation 2026-05-19. Doc-only KiCad sketch — placement only, no schematic. Catches "do all selected peripherals + connectors actually fit on the Pixhawk-standard mini-FC form factor?" CHEAP, before Phase 3 schematic decisions cascade.

Form factor (clarified 2026-05-20 P1.1 escalation; see `CLAUDE.md §1` + `DECISIONS.md §2`): **board outline 36 × 36 mm**, **mounting holes 30.5 × 30.5 mm c-to-c M3** (Pixhawk-standard pattern; matches MatekH743 reference).

Scope:
- KiCad project at `hardware/kicad/footprint-check/` (committed per `P0_REPORT.md §P0.3`, NOT throwaway — Phase 3 references it).
- `generate.py` (pcbnew API script, authoritative source) places: STM32H743VIT6 (LQFP-100), ICM-42688-P (generic LGA-14 for Phase 2.5; custom TDK-precision deferred to Phase 4), DPS310 (Bosch LGA-8 geom-match), USB-C HRO mid-mount, microSD Hirose DM3AT push-push, 4× JST-GH (telem 6P, GPS combined 10P, power 6P, CAN/aux 4P) per `DECISIONS.md §7`, 2× JST-SH 4P for 8 ESC outputs, SWD 2x5 1.27mm on bottom layer.
- IST8310/RM3100 are EXTERNAL (on GPS module) — not placed on novapcb per `CLAUDE.md §3.5`.
- MAX7456 is deferred (`OPEN_QUESTIONS.phase2exit-1`, recommendation: omit) — not placed.
- DRC + categorical violation report via `kicad-cli pcb drc`.

Result: **fit confirmed plausible.** Area density ~56% (660 mm² components / 1168 mm² usable). Coarse sketch DRC has 197 violations across 16 categories — itemized in `notes.md` with Phase 2.5 / Phase 4 attribution. Phase 4 layout work needs sub-mm precision on specific tight spots (microSD vs MCU+IMU vertical clearance, JST-GH 10-pin vs M3 keep-outs, USB-C mid-mount cable-egress overhang). None of the three fallback options (reduce connector type, reduce peripheral set, escalate form factor) was triggered.

Two doc clarifications landed in the Phase 2.5 PR (master adjudicated, supermaster-visibility flagged): KiCad 8→9 in `CLAUDE.md §6.1` + `§10.2` (escalation #1); 30.5×30.5 board-vs-hole-spacing disambiguation in `CLAUDE.md §1` + `DECISIONS.md §2` (escalation #2).

## Phase 3 — Schematic in KiCad (3a-3e DONE — 2026-05-20)

- **Mode: netlist-only** per Phase 3a Rule-13 escalation #1 + `OPEN_QUESTIONS.phase3-render-1`. SKiDL `generate_schematic()` doesn't scale past trivial circuits (hangs on the MCU sheet); per-sub-phase delivery is Python source + netlist + SKiDL ERC. Drawn schematic deferred to a dedicated investigation scheduled before Phase 6.5 forum review (NOT blocking Phase 3.5/4/5/6, which consume the netlist).
- Project at `hardware/kicad/novapcb/` (master-confirmed in P0 adjudication item 4). `novapcb.kicad_pro` held until Phase 4 / drawn-schematic landing.
- Per-sheet sub-phases via modular SKiDL Python (`sheets/mcu_3a.py`, `sheets/power_3b.py`, ...). Each 3x sub-phase = one sheet = one PR, mirroring Phase 2 cadence.
- Sub-phase breakdown (per `hardware/kicad/PHASE3_P0_REPORT.md §P0.6` approved by master): 3a MCU+clock+reset+decoupling+scaffold, 3b power tree, 3c IMU SPI, 3d baro I²C, 3e GPS+mag JST-GH 10P, 3f ESC outputs, 3g CRSF UART + USB-C, 3h power monitor + microSD + SWD + mounting.
- hwdef.dat is the AUTHORITATIVE pin map. Each 3x sub-phase grep'd hwdef.dat for that sheet's pin assignments; schematic ↔ hwdef mismatch = Rule-13 stop (per `feedback_hwdef_authoritative_for_schematic` discipline).
- Library strategy: standard KiCad 9 libs at `/usr/share/kicad/symbols/` + `/usr/share/kicad/footprints/`, referenced via committed `sym-lib-table` + `fp-lib-table`. No in-repo `lib/` needed unless a sub-phase surfaces a missing symbol.
- Acceptance per sub-phase: SKiDL ERC clean (peripheral-pin warnings expected until all sheets ship); netlist parses; hwdef pin assignments match.

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
