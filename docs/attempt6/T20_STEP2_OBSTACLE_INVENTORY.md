# T20 Step 2 — Comprehensive corridor obstacle inventory (2026-06-02)

> Updated this session: full F.Cu + B.Cu obstacle scan across multiple Y-bands. SDMMC1-westward alone is INSUFFICIENT — corridor is multi-subsystem contested.

## USART1 corridor candidates (X=53-93)

### Y=31.5-33.5 (preferred — closest to USART1 MCU pin Y=32)
- **+5V L0 vertical** @(91.16, 35.23)→(91.16, 24.21) — crosses corridor
- **+5V L0 short** @(78.61, 34.18)→(78.61, 32.45) + (79.73, 32.45)→(78.61, 32.45)
- **SDMMC1_CLK L0** @(64.18, 32.35)→(54.57, 32.35) — known
- **SDMMC1_CLK L0 diag** @(83.64, 51.81)→(64.18, 32.35) — known
- **USBC_D_M_PRE L0** @(74.14, 31.95)→(78.50, 29.85) — USB-C diff pair (HANDS-OFF)
- **USB_DM L0** @(69.50, 31.33)→(71.86, 31.95) — USB hands-off
- **5 GND stitch vias** @X=58/73/78/83/88, Y=32-33 — PDN plane connectivity

### Y=44-50 (B.Cu under-MCU route tested in this session: DRC +42)
- Multiple SDMMC1 + I2C2 + sensor traces densely populate B.Cu under-MCU area

### Y=13-18 (N-edge tested this session)
- **BATT2_VOLTAGE_SENS L0** spans X=46.55-80.87 at Y=15.14 — full corridor block
- **CAN1_RX L0** spans X=49.40-91.50 at Y=16 — full corridor block
- **+5V L2 diagonal** (52, 7.93)→(72.57, 28.5) — crosses
- **CANH_NET cluster** X=93+ Y=13-18
- **MAUCH2_VBAT_PRE / CURR_PRE** X=80-89 Y=8-14
- **USART6_RX L0** X=54, Y=6-14

## Conclusion — structural multi-subsystem wall

Corridor is blocked by 5+ hands-off / structurally-fixed subsystems across ALL Y bands:
- USB diff pair (hands-off >5MHz)
- CAN bus (hands-off)
- BATT2 sense (frozen per A↔B-2/3 PR work)
- +5V power distribution
- SDMMC1 (hands-off >5MHz)
- GND plane stitching (PDN integrity)

Step 2 (SDMMC1 westward alone) cannot resolve. Need broader corridor work:

## Escalation options per master Attempt 6b/c/d

| # | Option | Cost | Cascade risk |
|---|---|---|---|
| 6b | Re-pin SDMMC1 to different MCU pins | hwdef.dat + re-route 6 nets | Sim 3 + per-net audit |
| 6c | Re-place J2 microSD elsewhere | re-route 6 SDMMC1 nets + R51-55 pullups + Sim 3 | High |
| 6d | Re-place J3 to less-walled XY | Tested 16 candidates last session — all walled +36 to +96 | KNOWN-WALL |
| 6e | Re-route USB diff pair (RECOMMEND VS) | hands-off + Sim 2 USB Z_diff re-validation | High; USB SI risk |
| 6f | Re-pin BATT2 sense to different ADC | hwdef.dat + re-route 4 sense traces | Lower |
| 6g | Re-pin CAN to different USART/CAN MCU pins | hwdef.dat + re-route CAN + transceiver | High |

## Recommendation

**Master/Sai decision required**: which of 6b/6c/6e/6f/6g to execute first.

6d already proven walled (last session 16 candidates).

Engineering rank:
1. **6f (BATT2 sense re-pin)** — cheapest; 4 small slow signals
2. **6e (USB diff pair re-route)** — high cost but if successful frees the most corridor space (USB occupies X=70-93 Y=29-33)
3. **6c (J2 re-place)** — most expensive; multi-net SDMMC1 + pullups re-route

## Multi-session WIP per master OK

Branch hw/t20-attempt6-sdmmc-westward updated with this analysis. No PCB changes committed this session — full corridor wall confirmed without modification.
