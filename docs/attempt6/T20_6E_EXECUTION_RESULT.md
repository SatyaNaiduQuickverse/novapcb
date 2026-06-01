# T20 6e — USB diff pair re-route execution result (2026-06-02, late session)

> Sai pick (a) executed per master 2026-06-02 dispatch. Empirical: 6e alone insufficient — south detour corridor has independent blockers.

## Execution

Removed 5 USB_DM + USB_DP F.Cu corridor segments (Y=30.5-32 zone). Added south detour:
- USB_DM via (52.67, 31.5) → (52.67, 22.0) → (71.86, 22.0) → (71.86, 31.95) F.Cu W=0.20mm
- USB_DP via (52.67, 31.0) → (52.67, 22.5) → (71.86, 22.5) → (71.86, 30.05) F.Cu W=0.20mm
  (S=0.5mm diff spacing maintained for Z₀ continuity per Sim 2 baseline)

USART1_TX/RX routed in now-freed Y=31-33 corridor.

**Result**: DRC +52 cascade (29 → 81).

## Why 6e alone insufficient

Y=22 south detour corridor blocked by:
- **CAN1_RX/TX L0** @Y=22 X=48-49 (CAN bus, frozen PR #99)
- **BATT2_CURRENT_SENS L0** @Y=21.20 X=45-79
- **USART6_TX L2** @X=45.91 vertical Y=21.81-37.14
- **+5V L2 diagonal** (52, 7.93)→(72.57, 28.5)
- **I2C2_SDA L0** various Y=22-26
- Several zone clearance issues

## Combined-attack required

6e + 6f (BATT2) + CAN re-route + USART6 re-pin needed simultaneously to free a continuous south corridor for USB pair. Single-subsystem moves insufficient.

OR: implement USB south detour at DIFFERENT Y where fewer simultaneous blockers exist (Y=14? requires 6f BATT2; Y=8? requires moving J19 Mauch2 inputs).

## Sim 2 contract — UNTESTED

Cannot run Sim 2 Z₀ validation because the DRC cascade prevents the routing from being valid. Sim 2 contract pending DRC-clean re-route.

## Escalation request

Per master "multi-session OK" + Sai "no defers":
- (1) Authorize combined 6e+6f+CAN attack — major surgery with Sim 1+2+5 cascade re-validation
- (2) Pursue 6c J2 re-place + 6e USB pair to free area
- (3) Other Sai-level relief (board growth, IMU island shift, etc.)

PCB reverted pristine. Multi-session WIP on hw/t20-attempt6-sdmmc-westward branch.
