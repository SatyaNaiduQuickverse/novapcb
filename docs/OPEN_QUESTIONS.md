# Open questions

All v1 scoping decisions are in `DECISIONS.md`. Add new open questions here as they arise.

## v2-1. FMUv6X mechanical drop-in (deferred from `DECISIONS.md §2`)

v1 is a functional drop-in only (single-PCB, Pixhawk-standard 30.5 × 30.5 mm M3, requires a new mounting tray on the airframe). v2 is the mechanical drop-in against the Holybro Pixhawk 6X — FMUv6X form factor, two-board (FMU + isolated IMU on vibration mounts), exact 6X connector pin-out and footprint so the existing airframe accepts novapcb in place of the 6X without any mechanical change.

**What still has to be decided for v2 (not blocking v1):**

- Exact FMUv6X mechanical envelope (read from the Pixhawk Autopilot v6X Reference Standard, not from training-data memory — Rule 3).
- IMU isolation board: ICM-42688-P × 3 (or ICM-42688-P + BMI088 + ICM-20649 like the stock 6X) on a sub-board with rubber isolators? Or a flex-cable mounted daughterboard?
- Connector pin-out: the 6X uses a fixed set of JST-GH connectors on specified pins (UART/CAN/GPS/etc.); v2 must match the 6X carrier expectations.
- FMU/IMU interconnect: SPI bus + DMA stream choice between FMU and IMU board.
- Whether v2 shares any v1 PCB sources or starts as a fresh layout.

**Reference:** ArduPilot `libraries/AP_HAL_ChibiOS/hwdef/Pixhawk6X/hwdef.dat` is the source of truth for the 6X pin-out / peripheral mapping; v2 hwdef forks from there.

## phase2a-1. IMU DRDY pin (deferred from Phase 2a, `INTERFACE_CONTRACT.md §3.5`)

Phase 2a locked the primary IMU as ICM-42688-P on SPI1 (CS = `IMU1_CS` / PC15) in polled mode. ArduPilot supports interrupt-driven fast-sample mode if a DRDY (data-ready) input pin is wired and declared in `hwdef.dat`. DRDY allows tighter loop rates and lower jitter on the IMU thread; novapcb v1 ships without one.

**Why deferred, not picked now:**

- Pixhawk6X uses `PA10` for `SP2_DRDY2` (ArduPilot `libraries/AP_HAL_ChibiOS/hwdef/Pixhawk6X/hwdef.dat:129`). On our MatekH743-derived hwdef, `PA10` is already `USART1_RX` (telem2). Direct port impossible.
- Picking another H743 GPIO autonomously violates Rule 3 (no inventing technical specifics) — needs a grounded choice against (a) free pins on the H743 in our current pin map, (b) interrupt-line availability (DRDY needs EXTI), and (c) a future PCB routing constraint we don't have yet (Phase 4).
- MatekH743 in production runs ICM-42688-P polled successfully. So polled is a known-working fallback, not a hack.

**What needs to happen before this can resolve:**

- Decide whether v1 needs DRDY at all (depends on the target loop rate; ArduCopter default 1 kHz IMU thread is fine polled on H7).
- If yes, identify a free H743 GPIO that (a) is interrupt-capable, (b) doesn't conflict with Phase 2b–2h or 2-exit, (c) routes cleanly on the Phase 4 PCB layout.
- Re-do Phase 2a as 2a-rev2 with the DRDY pin in `hwdef.dat`.

**Options (placeholder, not chosen):**

- (a) Stay polled (current). Lowest risk; no rework if v1 ships fine.
- (b) Add DRDY on a yet-to-pick GPIO, plus `define HAL_DEFAULT_INS_FAST_SAMPLE 1` is already on — confirm fast-sample works with DRDY too.
- (c) Wait until Phase 4 PCB layout reveals which pins are physically convenient, then circle back.

**Recommendation:** (a) polled for v1; revisit only if we see IMU-thread jitter in bring-up (Phase 9).

## phase2exit-1. MAX7456 analog OSD chip — populate on novapcb v1 schematic?

Raised 2026-05-20 (Phase 2-exit cruft inventory). Inherited from MatekH743 reference.

**RECOMMENDATION: omit.** MAX7456 is analog-FPV-FC hardware; novapcb is a Pixhawk-class autopilot replacement (`CLAUDE.md §0` / `§1`) and Pixhawk-class boards have no onboard analog OSD. Nova drone video is fully digital (Pi Camera / Hailo, `§2.1`); no analog video path exists. When Phase 3 schematic confirms "no MAX7456", a follow-up PR strips the 5 hwdef lines (PB12 CS, SPIDEV osd, OSD_ENABLED, HAL_OSD_TYPE_DEFAULT, ROMFS_WILDCARD fonts) — frees ~10-30 KB flash.

Keeping the hwdef lines until then costs ~10-30 KB flash + zero runtime risk.

**Resolution path:** Phase 3 schematic init explicitly states whether novapcb has a MAX7456 chip populated. If "no" (master near-certain recommendation), a follow-up firmware PR strips the 5 lines listed above. If "yes" (would need an explicit reason against the recommendation), hwdef stays as-is and the chip drives the SPI2 OSD line.

## phase3-render-1. Phase 3 drawn-schematic rendering

Raised 2026-05-20 (Phase 3a Rule-13 stop — escalation #1 on `tasks/phase-3a-mcu.yaml`).

**Problem.** SKiDL `generate_schematic()` auto-router does not scale past trivial circuits. On the 3a MCU sheet (STM32H743VITx LQFP-100 + 27 components / ~30 nets, with 95 unconnected peripheral pins on the MCU), it hangs in the router retry loop for 11+ minutes with no output produced. SKiDL `generate_netlist()` works instantly and cleanly (22 KB netlist, 0 errors). The Phase 3 Part 0 smoke test was only 2 components — it validated that the API EXISTS but did NOT validate that it SCALES. Both worker and master under-validated. (Captured as shared P0 miss for the next retro: investigation-phase smoke tests must be realistically scaled to the actual workload, not toy-sized.)

**Why it matters.** A human-readable schematic is needed for **Phase 6.5 forum review** — EEs expect a schematic. Phases 3.5 / 4 / 5 / 6 do NOT need it; they consume the netlist directly (which works). So the drawn-schematic problem is bounded: it blocks Phase 6.5, nothing earlier.

**Resolution path.** Dedicated investigation + resolution scheduled IN the Phase 3.5–6 window (BEFORE Phase 6.5 prep), evaluating:

- **(a)** SKiDL router flags / timeout / hierarchical-subcircuit options — does SKiDL's auto-router have a "place-only, don't route" mode? Does breaking into hierarchical subcircuits help?
- **(b)** kicad-skip programmatic placement — but note: kicad-skip itself is an auto-place/route problem, the same hard thing `generate_schematic()` fails at; front-loading it is premature until (a) and (c) are evaluated.
- **(c)** One-time manual KiCad-GUI layout pass from the netlist — open the netlist in eeschema GUI, hand-tidy the placement, render PDF via kicad-cli. Bounded human effort; produces highest-quality schematic for forum review.
- **(d)** Per-small-sheet generation — the MCU sheet hangs, but small peripheral sheets (a few components each) may route fine. Generate per-sheet PDFs + concatenate.

**Decision criteria:** whichever option (a)/(b)/(c)/(d) produces a forum-quality schematic with bounded effort, ranked by (i) reproducibility, (ii) developer effort, (iii) reviewer quality. (c) is the safest fallback (any-time-of-day a GUI Claude or supermaster can do it); (a)/(d) are the most attractive if they work.

**Not blocking.** Phase 3.5 (reference-design audit) and Phase 4 (PCB layout) both consume the SKiDL-generated netlist, which works. Phase 5 (BOM) consumes the netlist + parts metadata. Phase 6 (sims) takes the netlist + footprint placements. The drawn-schematic gap blocks Phase 6.5 specifically.

**Owner / when:** dedicated task scheduled within the Phase 3.5–6 window. Not blocking Phase 3 sub-phase advance (netlist-only mode is the agreed Phase 3 deliverable; see `tasks/phase-3a-mcu.yaml` escalation_log entry #1).

## phase4a-1. ICM-42688-P land pattern — HARD must-resolve-before-Phase-6m

Raised 2026-05-20 (Phase 4a — master adjudication of the `icm42688p-footprint` decision fork).

**Status:** Phase 4a-4d **accept** the KiCad-generic `Package_LGA:LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y` footprint. Body, pitch, and pad-count/arrangement are TDK-spec-matched per Phase 2.5 P0.4. Pad sizes are IPC-7351 nominal. Placement (4b) and routing topology (4c/4d) depend on pad LOCATIONS which the generic gets right — so Phase 4 does NOT stall on this.

**Must-resolve before Phase 6m (manufacturability / DFM check):** verify pad dimensions against the TDK ds-000347 recommended land pattern. The ICM-42688-P is the **primary IMU** — the most flight-critical sensor on the board. A leadless-IC land pattern with wrong pad dimensions = poor or failed solder joints on a part that can't be hand-inspected. IPC-7351-generic is production-grade and probably fine, but "probably fine" is not the bar for the primary IMU on a board going to fab.

**Same re-verification applies to all leadless-IC footprints (LGA/QFN — IMU + DPS310) before fab; leaded packages (LQFP-100 + SOT-23) are lower-risk and Phase 2.5 P0.4 already cited KiCad-standard exact matches for those.**

**Resolution path (worker action — attempt near-term, ideally before Phase 4e so IMU SPI critical-net hand-routing uses final pads):**

- **(a) SnapEDA / UltraLibrarian vendor-verified footprint** — known sources for ICM-42688-P, free download. If verifiable + KiCad-9-compatible, swap the footprint in a small follow-up PR.
- **(b) Targeted single-page fetch of the datasheet's land-pattern figure** — narrower than the full 60-page PDF that timed out in Phase 4a WebFetch.
- **(c) An open-source FC project's datasheet-derived ICM-42688-P KiCad footprint** — well-traveled chip used on many FCs; somebody's likely committed a quality footprint.
- **(d) SUPERMASTER session with PDF tooling** — extract dimensions directly from ds-000347; SUPERMASTER REVIEW flag if none of (a)/(b)/(c) work headlessly.

**This is HARD carry-forward, not a soft "confirm at 6.5."** A leadless IMU footprint must not reach fab on a generic stand-in. Track it through Phase 4 sub-phases until resolved.

**Why HARD:**

- IMU is flight-critical (vibration sensing → attitude control → flight stability)
- Leadless package = no visual solder inspection on assembled board
- IPC-7351-generic ≠ TDK-recommended — generic may be wider (more tolerant) or narrower (potentially insufficient solder joint) than the part designer recommended

**Raised by:** Phase 4a `decision_forks_watched.icm42688p-footprint` resolution + master 2026-05-20 adjudication.

---

# Closed decisions (recorded here for traceability)

## CLOSED phase3exit-can. CAN: novapcb v1 deliberately ships no CAN connector / transceiver

**Decided 2026-05-20** (Phase 3-exit A2 escalation; master adjudication).

novapcb v1 deliberately ships **no CAN connector / transceiver**. The Nova drone uses zero CAN peripherals (GPS via UART, power via analog Mauch, ESCs via DShot, mag via I²C). Adding CAN would require an external CAN transceiver IC + 120 Ω termination + connector + board area — an unvalidated sub-circuit for a feature the target drone doesn't use. Per Rule 4 (match scope) + don't-design-for-hypothetical-futures discipline.

The `hwdef.dat` CAN1 definition (`hwdef.dat:147-149`: PD0/PD1 CAN1 + PD3 GPIO_CAN1_SILENT) is **RETAINED as harmless firmware capability** — if a future v1.x or v2 adopts a CAN peripheral (DroneCAN gimbal, smart battery, ESC telemetry-via-CAN), the firmware side is already in place and adding the transceiver + connector then is a contained change.

This decision resolves the Phase 2-exit Part B Item 6 pointer ("Phase 3 decides whether CAN connector is populated") cleanly. Phase 3 (now, at 3-exit) decides: **don't populate**.

**Why this is a CLOSED entry not an OPEN one:** it's a deliberate v1 feature-scope decision, not an unresolved question. It belongs here for traceability + so a future Claude sees the reasoning, but it's not awaiting any action.
