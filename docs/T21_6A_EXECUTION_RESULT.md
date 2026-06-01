# T21 Attempt 6a — F.Cu narrow + B.Cu direct (2026-06-02)

> Master pre-think Attempt 6a: F.Cu narrow corridor + 0.15mm SWD trace.

## Execution

Routed all 3 SWD nets (SWDIO/SWCLK/NRST) from MCU pads to J9 (B.Cu at 15,35) via:
- F.Cu short stub from MCU pad to F.Cu→B.Cu via (offset +0.7mm SE of pad)
- B.Cu direct trace to J9 pad at 0.15mm width (SWD slow signal allows)

**Result**: DRC +71 cascade (29 → 100). Same structural wall as T20.

## Same finding as T20

The B.Cu under-MCU corridor is densely populated with hands-off SPI buses + I2C + SDMMC1 + power/IMU routes (per T20 obstacle inventory § south-of-MCU). SWD's 35mm B.Cu run can't avoid them.

## Conclusion

T20 + T21 both confirm: v1 105×85mm board is at structural density limit for retrofit of any new 30-50mm routing. The remaining options are the SAME as T20 escalation matrix (component re-place OR board size growth).

Per Sai 'no defers' + master 'come back if real wall': escalation request consolidated with T20.

Multi-session WIP on hw/t21-swd-reroute branch. PCB reverted pristine.

## Attempt 6c — J9 re-place + B.Cu route

Tested 10 J9 candidate XY positions. ALL cascade. Best result: (20, 45) at DRC +52. Same density wall as 6a — B.Cu under-MCU and SW corner densely populated.

Master directive 2026-06-02: pursue T20 6e (Sai pick (a)) FIRST. T21 stays parallel only when T20 6e in WIP commit-wait state.

## Attempt 6a v2 — F.Cu Y=44 lanes + B.Cu drop near J9

Tested: 3 SWD lanes at Y=44.0/44.4/44.8 F.Cu (0.15mm width slow signal), drop via at J9 X-position, B.Cu to J9 pad.

**Result**: DRC +112 cascade (29 → 141).

Y=44 corridor saturated by IMU island routing (SPI1/2/3 + I2C1/2 + +3V3_IMU + IMU CS/INT lines). Same pattern as T20 south-of-MCU Y=48-55 scan from prior session.

## Consolidated T21 finding

| Attempt | Strategy | DRC delta |
|---|---|---|
| 6a v1 | F.Cu narrow + B.Cu direct 0.15mm | +71 |
| 6a v2 | F.Cu south Y=44 lanes + B.Cu drop | +112 |
| 6c | J9 re-place (10 candidates) | +52 best |

ALL T21 attempts cascade. Same structural wall as T20 — board density saturated; SWD's 3-net 30+mm routing impossible without major component re-arrangement or board growth.

## Convergence with T20

Both T20 (USART1 routing) and T21 (SWD routing) confirm the SAME structural board-density limit. Cannot solve T21 in isolation; requires the same architectural relief Sai is currently re-deciding for T20.
