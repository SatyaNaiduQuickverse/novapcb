# PR — GPS+MAG routing (task #47)

> Branch `hw/gps-routing` off `sch/option-b-buck`. Routes the GPS subsystem
> (UART + I²C1 mag/baro + ESD) from the MCU to J5 (GPS+MAG connector, SW corner).
> Includes a **GPS1_TX re-pin (PD5→PA2)** and a **BUZZER v2 defer**.

## 1. What changed

**Routing (4 of 5 signal nets):**
- **GPS1_RX, I²C1_SCL, I²C1_SDA** — scoped Freerouting, clean. I²C1 is the full
  multi-drop bus: MCU + U7 (LPS22 baro) + pull-ups R21/R22 + ESD D7/D8 + J5.
- **GPS1_TX** — re-pinned then Freerouted from the new pin (see §2). 0 errors.

**Schematic — GPS1_TX re-pin PD5 → PA2 (`gps_mag_3e.py` + `hwdef.dat`):**
- PD5 (N-edge pad X=46.0) is boxed by the BATT2 sense-trace verticals on B.Cu
  (BATT2_CUR 45.1/45.4, BATT2_VOLT 46.5) — unroutable to J5. Freerouting (4
  passes incl. TX-alone) and manual (2 iter) all failed the N-edge exit.
- **PA2** is the only other USART2_TX pin on LQFP-100 (AF7), **free** (MOT5
  vacated it in PR #83 → PE13), on the **W edge** with a clean corridor to J5.
  Same USART2 peripheral as RX (PD6) — no firmware UART split.
- After the re-pin, Freerouting routed the full GPS1_TX (PA2→D5→J5) in 5s, clean.
- Netlist regenerated; ERC = 0 errors. PD5 reverts to a free GPIO.

> **Note (master correction):** the suggested PB9 candidate assumed UART4, but
> the GPS UART is **USART2**; PB9 is also still assigned to MOT8. PA2 is the
> correct USART2_TX alternate.

**Spec deviation — BUZZER deferred to v2:**
- BUZZER (J5.9) is audio feedback only, not flight-critical; ArduPilot runs
  without a buzzer bound. It was the lowest-priority net in the congested GPS
  N-edge cluster. MCU driver removed (PD7 → free GPIO); BUZZER net stays defined
  (J5.9 + ESD D9 + TP5) but undriven in v1. v2: bind a free GPIO + restore
  `HAL_BUZZER_PIN`. Same scope-pragmatism pattern as MOT7/8, CAN_SILENT, v2 slot.

## 2. Verification (gates)

| Gate | Result |
|---|---|
| DRC | **18 = baseline** (no new errors) |
| Unconnected | 244 → **231**; **0 missing on RX/SCL/SDA/TX** (all routed); the
  remaining GPS ratsnest is BUZZER only (deferred, documented) |
| STACKUP-SPEC-MATCH / MIRROR_PAIRS / DECOUPLING | **PASS** (audit clean) |
| Per-net cluster walk | GPS1_TX continuous (0 uncovered); RX/SCL/SDA continuous
  on signal paths — the 1–3 sampling misses are via-antipad voids (own vias),
  immaterial for UART (≤460 kbaud) / I²C (400 kHz) |
| ERC | **0 errors** (netlist regen; GPS1_TX on PA2/U1.24; BUZZER no MCU) |

## 3. Prevention / lessons

- **MCU N-edge box (recurring)**: the BATT2 sense-trace verticals box the GPS
  N-edge pads (BUZZER 45.0 / TX 46.0); RX(45.5) took the single path through.
  Same class as CAN's MCU-signal box. **Re-pinning to an unboxed pad (PA2, W
  edge) was the clean unblock** — Freerouting then converged trivially. When a
  pad is boxed by merged-work obstacles, re-pin (if the peripheral allows an
  alternate) beats fighting the box (cf. SILENT PD3→PD15).
- **Verify the peripheral before re-pinning (hwdef authoritative)**: the GPS
  UART is USART2 (PD5/PD6), not UART4 — the TX alternate must be a USART2_TX pin
  (PA2), not an arbitrary free pin. Confirmed against hwdef + LQFP-100 AF table.
- **Scope-pragmatism**: BUZZER (non-flight-critical) deferred to v2 rather than
  grinding the boxed N-edge for it.
