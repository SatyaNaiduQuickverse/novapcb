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
