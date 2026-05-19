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

## Phase 3 — Schematic in KiCad (NOT STARTED)

- `hardware/kicad/novapcb.kicad_pro` initialized.
- Hierarchical sheets per subsystem: MCU, IMU, baro+mag, GPS+CAN,
  USB+SD, ESC, power, debug header.
- Symbol library committed at `hardware/kicad/lib/` (in-repo, not
  global KiCad libs — reproducible on any clone).
- Net names mirror Phase 2's hwdef.dat pin assignments — the hwdef is
  the contract; the schematic just lays it out.
- Acceptance: ERC clean; schematic netlist consistent with hwdef.dat.

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

## Phase 6 — Manufacturability review (NOT STARTED — GO/NO-GO GATE)

- DRC + ERC clean and re-run.
- BOM ↔ footprint cross-check (no orphan components).
- Fab DFM check against the chosen fab's capability sheet
  (default: JLCPCB 4-layer).
- Power-rail review (decoupling, thermals, current capacity).
- Stack-up + impedance for any controlled-impedance nets (USB
  differential pair; SDMMC if applicable).
- Acceptance: **explicit checklist signed off by the user.** This is
  the real-money gate (Rule 7). No fab order without it.

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
