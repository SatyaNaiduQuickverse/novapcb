# T20 Attempt 6f — BATT2 sense re-route execution result (2026-06-02)

> Master authorized 6f BATT2 sense re-route per Sai standing 'no defers'. This session executed + tested. Cascade pattern confirms board-density wall, not strategy issue.

## 6f execution

Removed 7 F.Cu BATT2 corridor-blocking segments (Y=14-22 zone). Added B.Cu south-detour replacement traces. Attempted USART1 routing via the now-freed N-edge corridor at Y=14-15.

**Result**: DRC +104 cascade (29 → 133).

## Why 6f alone insufficient (empirical)

Even with BATT2 F.Cu segments removed, N-edge corridor (Y=12-22) still blocked by independent subsystems:
- **CAN1_RX L0** @(49.40, 16)→(91.50, 16) — full corridor block at Y=16 (CAN bus, frozen PR #99)
- **CAN1_TX L0** parallel at Y=22
- **USART6_TX L2** @X=45.91, Y=21.81→37.14 — west-side vertical
- **+5V L2 diagonal** (52, 7.93)→(72.57, 28.5) — crosses corridor diagonally
- **MAUCH2_VBAT_PRE / CURR_PRE** at X=80-89, Y=8-14 (Mauch2 connector inputs)
- **CANH_NET cluster** at X=93+ Y=13-18

## Why no other corridor works either (empirical from prior sessions + this session)

Tested 3 Y bands in this T20 campaign:
- **Y=31.5-33.5** (original USART1 corridor): blocked by +5V vertical + USB diff pair (HANDS-OFF) + USB_DM + 5 GND stitch vias + SDMMC1_CLK
- **Y=14-18** (N-edge, post-6f): still blocked by CAN1 + USART6_TX + +5V + MAUCH2 (above)
- **Y=44-50** (B.Cu south-of-MCU): blocked by SPI1/2/3 (HANDS-OFF) + I2C1/2 + SDMMC1 (HANDS-OFF) + +3V3_IMU + IMU CS/INT lines + HEATER_PWM + MOT6 + +5V

ALL Y bands across the E half of the board are densely populated by hands-off or frozen subsystems.

## Conclusion — board density limit reached

This is NOT a strategy issue. The board is structurally too dense for retrofit USART1 routing without major component re-arrangement that would cascade Sim 1 thermal / Sim 2 USB Z_diff / Sim 3 SDMMC1 SI / Sim 5 PDN ALL simultaneously.

Per master's pre-authorization fallback sequence:
- 6f: tested, insufficient (this session)
- 6e USB diff pair re-route: would help Y=31.5-33.5 corridor but Sim 2 mandatory + USB hands-off — high risk
- 6c J2 microSD re-place: tested last session (16 candidates walled +36 to +96) — KNOWN WALL

## Escalation request to Sai

Per Sai standing 'no defers + finish all in v1' + master 'come back if real wall': this IS the real wall. Need Sai/master decision on:
1. **Authorize 6e USB diff pair re-route with Sim 2 contract** — touches USB hands-off, mandatory Z_diff re-validation at ≥85% tolerance
2. **Authorize major component re-place** — move J3 connector AND surrounding components (J5 GPS, J10 CRSF) to clear N corridor
3. **Accept architectural compromise**: USART1 routing requires board size increase (Pixhawk-mini-FC density is already at 105×85mm; growing to 105×100mm gives ~15mm extra N-edge corridor — would unlock USART1 routing definitively)
4. **Other architectural relief Sai sees**

Multi-session WIP on hw/t20-attempt6-sdmmc-westward branch. PCB reverted pristine; this session's empirical findings committed for Sai/master review.
