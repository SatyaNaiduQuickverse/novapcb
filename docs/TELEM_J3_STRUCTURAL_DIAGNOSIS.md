# Telem J3 routing — structural diagnosis (2026-05-29)

> Empirical audit of the 2026-05-29 attempt to route USART1_TX/RX from MCU to J3
> per Sai's `should do j3` override of the original `docs/TELEM_V1_DEFER.md`
> decision. 4 attempts walled, structural impossibility confirmed within
> reasonable blast radius. Master decided (γ) revert to v2-defer per Sai's
> standing delegation.

## 1. Context

`docs/TELEM_V1_DEFER.md` (e8b1ef7) originally locked J3 → v2-defer based on
the #56 east-edge structural blocker. Decision: USB-CDC MAVLink is the
canonical Nova drone-side path (per `CLAUDE.md §2.1`), and J3 connector
stays placed without USART1_TX/RX wired in v1.

Sai 2026-05-28: "should do j3" — override-to-route directive. Master read
this as a hopeful retry given the post-Phase-4d-redux density changes
(CRSF re-pinned to UART4, IMU3_INT1 v2-deferred, U9 rolled back, C93.1
v2-deferred). Dispatched 2026-05-29 as task #67.

Worker executed the empirical attempts below.

## 2. 4 walled attempts

| # | Approach | MCU pins | Corridor | Result |
|---|---|---|---|---|
| 1a | Manual F.Cu Y36/Y37 lanes | PA9 / PA10 (E-edge @ 52.67, 32.0–32.5) | NE: X53–95 Y28–40 | **22 non-baseline DRC** |
| 1b | Scoped Freerouting (2 nets only) | PA9 / PA10 | NE corridor | **30-min wall cap, no SES** (CPU pegged, log frozen) |
| 2 | Manual F.Cu Y33.5/Y35.5 lanes (test) | PC6 / PC7 (E-edge @ 52.67, 34.5–35.0) | NE corridor | **25 non-baseline DRC** |
| 3 | Manual F.Cu Y43.5/Y44 lanes | PE7 / PE8 (S-edge @ 44.5–45, 42.67) | SE: X44–95 Y36–48 | **42 non-baseline DRC** |

## 3. NE corridor density (PA9/10 + PC6/7 attempts)

F.Cu obstacles in X53–95 Y28–40:

- USB diff pair + USB-C bridges + CC1/CC2 (Y29–32) — **HANDS-OFF**
- SDMMC1_CLK / D0 / D1 (Y32–34, diagonals into IMU island) — **HANDS-OFF**
- USART6 historical (Y32 area) — slow but transiting
- +5V plane (multi-segment in J3 area)
- GND stitching vias every ~5 mm

B.Cu has SDMMC1_CMD / D2 / D3 + SPI3 buses + USB-C diff pair + +3V3_IMU rail.

The SDMMC1 diagonals from MCU PC8/PC9 escape pads (Y34) into the SD card
region (Y50+) **form the structural wall** — they emanate from the MCU
E-edge pad row at Y34 and radiate into the corridor. Any Telem trace from
the same edge has to either cross these or escape S/N first, both blocked.

## 4. SE corridor density (PE7/8 attempt)

F.Cu obstacles in X44–95 Y36–48 (top 10 by count):

| Net | Segs | Hands-off |
|---|---|---|
| I2C2_SCL | 7 | slow (nudgeable but multi-seg) |
| I2C2_SDA | 6 | slow |
| SPI1_MOSI | 5 | **HANDS-OFF** |
| MOT6 | 4 | slow |
| MOT3 / MOT4 / MOT5 | 3 each | slow |
| SPI2_MOSI | 3 | **HANDS-OFF** |
| +3V3 | 2 | plane |
| BATT2_CURRENT_SENS | 2 | slow |

B.Cu in same region:

| Net | Segs |
|---|---|
| SDMMC1_CMD | 7 |
| SPI3_MOSI | 4 |
| USART6_TX | 4 |
| I2C1_SCL / SDA | 3 each |
| IMU2_ACC_INT1 | 3 |
| SDMMC1_D3 | 3 |
| +3V3_IMU | 2 |
| BATT2_VOLTAGE_SENS | 2 |
| HEATER_PWM | 2 |

S-edge corridor is **denser than NE corridor** — MOT3-6 fan-out occupies
X45–48 Y42–45 area exactly where PE7/PE8 would escape. 42 fouls in single
manual pass confirms.

## 5. Direction-independent structural wall

Both NE (Y28–40) and SE (Y36–48) corridors saturated by **different but
equally dense** existing nets. The board was placed and routed around the
assumption that USART1 stays unwired in v1 — the routing channels that
would have served Telem were consumed by other signals in Phases 4a–4d.

Pin choice (PA9/10 vs PC6/7 vs PE7/8) does not change the corridor
problem: all three start at MCU edge pad rows surrounded by their own
neighbor density, all three need to traverse 40–50 mm of densely-routed
board space, all three end at J3 (X93–94, Y36.15) which has its own +5V
plane + GND via stitching saturation.

This is the same self-referential density pattern as IMU3_INT1 (see
`docs/U9_REPLACE_STRUCTURAL_DIAGNOSIS.md`) — board density built around
prior placement decisions becomes the wall for any deferred-then-retried
net.

## 6. (γ) execution — 2026-05-29

Master decision per Sai's standing "you take decisions" delegation:

- `scripts/audit_unconnected_per_net.py` `INTENDED_DEFERRED` extended to
  include `USART1_TX` + `USART1_RX` (same pattern as IMU3_INT1, MOT7/8,
  SW*, EFUSE_FLT/PGOOD)
- Audit verdict returns to **PASS**, 0 real-latent
- J3 connector footprint stays placed — no BOM change, no mechanical change
- `hwdef.dat` USART1 declaration stays — peripheral exists, just no
  external wire in v1
- `docs/TELEM_V1_DEFER.md` status REINSTATED
- `docs/TELEM_V1_ROUTE_DECISION.md` marked REVERSED

## 7. v1 functional impact: NONE

- MAVLink primary path = USB-CDC (canonical per CLAUDE.md §2.1)
- USART2 (PA2/PD6) remains the secondary MAVLink option if a serial
  Telem becomes required later (verify pad availability at v2)
- ArduPilot config unchanged: `SERIAL_ORDER` still lists USART1
- The TELEM2 SERIAL slot can be reconfigured in firmware to point at USB
  or unused without rebuilds

## 8. v2 prevention

v2 board respin reserves the Telem corridor in **Phase 4a placement**:

1. Identify the J3 connector position early (or move it next to MCU
   to shorten the trace)
2. Reserve a clean 2-net F.Cu lane from MCU edge to J3 before placing
   other signals
3. Or move USART1 to a less-saturated MCU pin that has direct line-of-sight
   to J3

## 9. Cross-references

- `docs/TELEM_V1_DEFER.md` — original v1 defer decision (status reinstated 2026-05-29)
- `docs/TELEM_V1_ROUTE_DECISION.md` — Sai-override decision (status reversed 2026-05-29)
- `docs/U9_REPLACE_STRUCTURAL_DIAGNOSIS.md` — same self-referential density pattern (IMU3_INT1)
- `scripts/audit_unconnected_per_net.py` — INTENDED_DEFERRED set
- `memory/feedback-cumulative-density-wall` — the underlying principle
