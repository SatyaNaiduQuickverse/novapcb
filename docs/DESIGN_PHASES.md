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

## Phase 0.5 — Sim toolchain (IN PROGRESS — PR open 2026-05-20)

Just-in-time install per ENGINEERING_RIGOR.md (originally deferred from Phase 0). Now landing while Sai routes Phase 4 GUI residual + before Phase 6.

**Outcome (per `sims/TOOLCHAIN.md`)**: 8 of 10 SIMULATION_PLAN tools installed userspace (no sudo); 3 NEEDS-SUDO-HANDOFF; 1 deferred-with-analytical-fallback (OpenEMS); 1 skipped (LTspice/Wine per master directive).

**Phase 6 reachability**: ~85% — 10 of 13 sub-phases fully unblocked; 2 partial-with-analytical-fallback (6b USB diff pair, 6k EMC); 1 Sai-handoff-pending (6j thermal via Elmer FEM).

**Installed userspace**: numpy 2.4.5, scipy 1.17.1, matplotlib 3.10.9 (inherited from venv-ardupilot) + PySpice 1.5, scikit-rf 1.12.0, kicost 1.1.20, InteractiveHtmlBom 2.11.1 (pip user) + ngspice 46, libngspice0 46 (dpkg-deb extract from Debian arm64 .deb to `~/local/ngspice/`).

**Sai-handoff list** (apt installs needing sudo): gerbv, octave, elmerfem-csc (source-build or PPA needed). One-liner in `sims/TOOLCHAIN.md §8`.

**Deferred-with-fallback**: OpenEMS — not in apt anywhere; source-build chain (Boost + VTK + Qt + tinyxml + CGAL + fparser + HDF5 + CSXCAD) infeasible in Phase 0.5 budget. Analytical Hammerstad-Jensen + scikit-rf transmission-line model covers Phase 6b/6k v1 SI; OpenEMS becomes deeper-validation pass post-Phase-9 when Sai grants sudo.

Full per-tool smoke-test results + reproducible install paths: `sims/TOOLCHAIN.md`.

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

## Phase 3 — Schematic in KiCad (3a-3i DONE — 2026-05-20; SCHEMATIC CAPTURE COMPLETE)

Phase 3i (telem JST-GH 6P connector — USART1) added as 8-sheet-breakdown omission fix caught by Phase 3-exit A2 hwdef-completeness check (master adjudication: NEEDS-FIX). Plus Phase 3-exit CLOSED-decision: CAN1 deliberately omitted from v1 — Nova drone uses zero CAN peripherals; hwdef CAN1 retained as harmless firmware capability for future v1.x/v2 expansion. See `docs/OPEN_QUESTIONS.md` "CLOSED phase3exit-can" entry.

## Phase 3-exit — Re-audit + carry-forward consolidation (DONE 2026-05-20)

Phase 3 close-out audit per the Phase 2-exit pattern. See `docs/PHASE3_AUDIT.md` for the structured report (Parts A re-audit + B Phase-4 carry-forward consolidation + C 08:00 retro fold).

Result: **0 Cat-B real omissions.** A1 cold rebuild + ERC + guard PASS; A2 hwdef-completeness PASSES CLEAN (63 hwdef-assigned MCU pins → 46 connected + 25 Cat-A intentional cruft + 3 Cat-C deliberate v1-omit CAN); A3 CONFIDENCE_MAP 14/14 rows coherent; A4 OPEN_QUESTIONS consistent. 7 Phase 4 carry-forward items consolidated (symbols, footprints, trace routing); 11 DEFER-to-Phase-6.5/6-sim items passed through; Mauch HS-200-LV 9.0/60.6 calibration PRIORITY-flagged for Phase 9 bench.

After this phase merges, **Phase 3 is fully closed** (3a-3i + 3.5 + 3-exit). Phase 4 (PCB layout) opens with its own P0 routing-approach investigation (master 06:00 heads-up).

## Phase 3.5 — Reference design audit (DONE 2026-05-20)

Cross-check the schematic against available reference designs + resolve accumulated carry-forward / cross-check / deferred flags. See `docs/REFERENCE_AUDIT.md` for the structured report (one section per of 14 CONFIDENCE_MAP subsystems).

Result: **No NEEDS-FIX items.** 9 subsystems OK-AS-IS, 3 subsystems DEFER-TO-Phase-6.5 (5V-input protection, external-connector ESD, EMC/RF coupling — no schematic-level reference obtainable, external EE review at Phase 6.5 is the honest resolution), 1 subsystem DEFER-TO-Phase-6j (thermal — layout-dependent), 1 subsystem with PRIORITY-for-Phase-9-bench flag (Mauch HS-200-LV calibration values 9.0/60.6 — web-research-sourced; per-unit calibration card refines). Plus 7 Phase 4 carry-forward items (symbols, footprints, trace routing) consolidated.

BMP280-as-DPS310 pin-identity (Phase 3d stand-in) re-verified ×3 sources (Infineon DPS310 datasheet + Bosch BMP280 datasheet + KiCad BMP280 symbol pin map) — all 8 pins match exactly. NOT a NEEDS-FIX.

REFERENCE_AUDIT.md also includes a "Candidate topologies for Phase 6.5 review" section (per master 07:00 cross-review "audit deep" emphasis) — researched candidate ESD + reverse-polarity-protection menus so Phase 6.5 starts with options rather than blank. Worker did NOT silently add any of these to the schematic (master 3e.5 directive holds: don't silently add non-inherited topology).

- **Mode: netlist-only** per Phase 3a Rule-13 escalation #1 + `OPEN_QUESTIONS.phase3-render-1`. SKiDL `generate_schematic()` doesn't scale past trivial circuits (hangs on the MCU sheet); per-sub-phase delivery is Python source + netlist + SKiDL ERC. Drawn schematic deferred to a dedicated investigation scheduled before Phase 6.5 forum review (NOT blocking Phase 3.5/4/5/6, which consume the netlist).
- Project at `hardware/kicad/novapcb/` (master-confirmed in P0 adjudication item 4). `novapcb.kicad_pro` held until Phase 4 / drawn-schematic landing.
- Per-sheet sub-phases via modular SKiDL Python (`sheets/mcu_3a.py`, `sheets/power_3b.py`, ...). Each 3x sub-phase = one sheet = one PR, mirroring Phase 2 cadence.
- Sub-phase breakdown (per `hardware/kicad/PHASE3_P0_REPORT.md §P0.6` approved by master): 3a MCU+clock+reset+decoupling+scaffold, 3b power tree, 3c IMU SPI, 3d baro I²C, 3e GPS+mag JST-GH 10P, 3f ESC outputs, 3g CRSF UART + USB-C, 3h power monitor + microSD + SWD + mounting.
- hwdef.dat is the AUTHORITATIVE pin map. Each 3x sub-phase grep'd hwdef.dat for that sheet's pin assignments; schematic ↔ hwdef mismatch = Rule-13 stop (per `feedback_hwdef_authoritative_for_schematic` discipline).
- Library strategy: standard KiCad 9 libs at `/usr/share/kicad/symbols/` + `/usr/share/kicad/footprints/`, referenced via committed `sym-lib-table` + `fp-lib-table`. No in-repo `lib/` needed unless a sub-phase surfaces a missing symbol.
- Acceptance per sub-phase: SKiDL ERC clean (peripheral-pin warnings expected until all sheets ship); netlist parses; hwdef pin assignments match.

### Phase 3.5 rule (recorded for posterity)

Before laying out copper, lift verbatim what's been proven. For each subsystem in CONFIDENCE_MAP.md, compare against ≥3 open-schematic FCs:

| Rule | Action |
|---|---|
| ≥3 references agree on a value/topology | Our design **must** match. No "improvement" without an explicit risk note. |
| References diverge | Pick one, document why. Diff becomes part of CONFIDENCE_MAP row evidence. |
| No reference exists | Subsystem is novel — confidence stays LOW + routes to Phase 6.5 forum review (external EE eyes ARE a form of reference review). |

Reference availability honest report (per the actual 3.5 audit): MatekH743 full schematic NOT obtainable (Matek doesn't publish; ArduPilot tree has only hwdef). Pixhawk6X / FMUv6X published as DS-012 but H753-based + 2-board pattern (partial applicability). ArduPilot hwdefs across the H743 family provide pin maps but not full schematics. Component datasheet typical-app-circuits used as proxy where appropriate. Where references genuinely weren't obtainable, subsystems routed to Phase 6.5 as the honest answer — no faked cross-checks.

## Phase 4 — PCB layout (P0 + 4a DONE; 4b-4f IN PROGRESS)

Phase 4 P0 (routing-approach investigation) merged 2026-05-20 — see `hardware/kicad/PHASE4_P0_REPORT.md`. Recommendation: **(c) hybrid** (placement + Freerouting bulk + scripted critical-net hand-route) with documented **(d) supermaster GUI** fallback. Toolchain (kinet2pcb + pcbnew + Java 25 + Freerouting v2.2.4) validated headless on the real novapcb netlist via 3-iteration scale-test.

Sub-phases per the P0.6-approved breakdown:

| Sub | Title | Status |
|---|---|---|
| 4a | Footprints + 4-layer stackup + DRC ruleset + closed outline | **DONE 2026-05-20** — `hardware/kicad/novapcb-layout/` (board scaffolding ready for placement; 70/70 footprints final; 36×36mm closed outline; 4× M3 at 30.5 c-to-c; 8 net classes incl. Power/USB_diffpair/IMU_SPI/SDMMC/DShot; DRC rules within JLCPCB 4-layer capability). Phase 4a-1 ICM-42688-P land pattern is HARD carry-forward per `OPEN_QUESTIONS.md` phase4a-1. |
| 4b | Component placement (per Phase 2.5 sketch + Phase 3 hierarchy) | **DONE 2026-05-20 (4b-rev applied per master adjudication)** — `hardware/kicad/novapcb-layout/` 70 components positioned with per-group routing-aware reasoning + finer-precision pass. **18 DRC violations residual** (down from 87 first-pass; 79% reduction); bounded + specific list flagged for Phase 4c plane-pour re-check + supermaster GUI fine-tune of irreducibles. microSD + DPS310 baro on B.Cu (structural fit on 36×36). |
| 4c | Plane definition + 4b residual fix (B + C-modified) + option-θ (J10 CRSF → solder pads) | **DONE 2026-05-20 — 0 DRC errors.** 7 zones (In1.Cu GND solid + In2.Cu +3V3 dominant / +5V band / VBAT small / +3V3A tiny + B.Cu GND fill); unconnected_items 193 → 0 ✓. 4b shorts resolved via path-B (R51-R55 to B.Cu) + path-C-modified (H1-H4 pads 6.4mm→3.6mm). Phase 4b architectural over-constraint discovered + verified (4× MP-pad JST-GH not viable on 36×36; no no-MP variant exists; MatekH743 uses different connector mix). Master option-θ: J10 CRSF → 4-pad solder array (`novapcb_lib:CRSF_solder_pad`); DECISIONS §7 preserved for J3/J4/J5. ⚠️ SUPERMASTER REVIEW for J10 footprint change. |
| 4d | Critical-net hand-routing (USB diff pair, IMU SPI, SDMMC, Mauch ADC filter) | **Rule 13 stop — DONE w/ scope reduction** — 3 iter (53→81→6 DRC) confirmed headless scripted Manhattan routing infeasible on dense 36×36 placement. **Delivered**: J2 microSD off-board pad fix (was Y=-1.73 → Y=1.27 on-board); USB 90Ω geometry computed (Hammerstad-Jensen W=0.25/S=0.10 → 91.6Ω); KICAD9_NOTES.md API-measure + headless-limits disciplines. Routing escalated for 4e Freerouting test before committing to (d) GUI fallback. Master 4d-decision: don't pre-commit to A; run Freerouting first. |
| 4e | Freerouting autoroute pass (whole board, net-class-guided) | IN PROGRESS — running on real placement + planes (vs P0 scatter test). Falsifiable prediction: 75-85% completion (~5-10 nets incomplete); USB diff pair likely scoped GUI residual. |
| 4f | DRC clean + schematic parity + gerber/drill export | NOT STARTED |
| 4-exit | Re-audit + Phase 5 carry-forward (Phase 2/3-exit pattern) | NOT STARTED |

- 36 × 36 mm board outline, 30.5 × 30.5 mm c-to-c M3 mounting (DECISIONS §2 v1).
- 4-layer stackup (DECISIONS §8); F.Cu (signal) / In1.Cu (GND plane) / In2.Cu (power split) / B.Cu (signal).
- IMU placement sits over the clean ground plane.
- USB-C connector edge-mount; microSD edge or under-mount as layout permits.
- JST-GH connectors per DECISIONS §7.
- Acceptance: DRC clean; 3D view inspected; mechanical envelope matches the planned mounting tray.

## Phase 5 — BOM finalization (IN PROGRESS — PR open 2026-05-20)

- `bom/novapcb-bom.csv`: 34 rows covering 70 components — refdes, qty, value,
  footprint, MPN, manufacturer, LCSC#, JLCPCB type (basic/extended), datasheet,
  last-checked date, alt-part, assembled-yes/no flag.
- `bom/SOURCING_NOTES.md`: fab-target choice (JLCPCB per fork resolution),
  two-sided SMT assembly callout (B.Cu carries J2 + J9 + U4 + R51-R55),
  ICM-42688-P footprint carry-forward (OPEN_QUESTIONS phase4a-1), Mauch
  DF-13→JST-GH adapter procurement note (external), solder-pad land
  patterns (J10/J11-J18/H1-H4) explained as PCB-only.
- Cost target: ~25 assembled line items; ~19 JLCPCB-basic + ~6 extended;
  estimated one-time extended-part loading fee ~$18-24; per-board BOM cost
  feeds into Phase 7 fab-quote workflow.
- Acceptance: 70 netlist refdes all accounted for in CSV; every assembled
  non-passive has real MPN + LCSC# + datasheet URL; no sole-source / no
  long-lead items.

**Sai-decision flags blocking fab order** (defer to Phase 7):
- ICM-42688-P footprint (phase4a-1) — must close before fab.
- Surface finish (ENIG recommended for LGA-14 / LGA-8 sensors).
- Quantity, soldermask, lead-free vs leaded.

## Phase 5-exit — task contract closure (PENDING)

After Sai's GUI routing pass + Phase 4f gerber export land, Phase 5 task
contract closes alongside Phase 4-exit re-audit. Decision-fork
`fab-target` resolved JLCPCB.

## Phase 6 — Simulation regime (IN PROGRESS — 6l first sub-phase, PR open 2026-05-20)

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
| 6l | ArduPilot SITL — functional regression | SITL | **DONE 2026-05-20** — PR open; 18/18 PASS incl. CLAUDE.md §4.1 pitch-sign no-double-flip; layout-independent |
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
