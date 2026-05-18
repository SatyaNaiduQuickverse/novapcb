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
