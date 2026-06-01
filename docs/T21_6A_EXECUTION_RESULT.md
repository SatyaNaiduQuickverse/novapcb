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
