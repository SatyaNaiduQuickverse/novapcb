# Routing track (B) — signal-net batches by region (master 2026-05-22)

Per master direction for the vision-loop residual close. Each batch = ~6-8
nets in one board region. Corridor renders per net + coord JSON for
master to vision-propose.

## Batch B1 — North edge (USB area + UART)  [6 nets]
- USBC_D_M_PRE (3 pads: J1.A7, J1.B7, U5.3) — controlled-impedance pair
- USBC_D_P_PRE (3 pads: J1.A6, J1.B6, U5.1) — controlled-impedance pair
- USBC_CC1 (J1.A5 ↔ R31.1)
- USBC_CC2 (J1.B5 ↔ R32.1)
- GPS1_RX (D6.1 ↔ U1.87)
- USART6_TX (D13.1 ↔ U1.63)

## Batch B2 — MCU west microSD + SPI1  [6 nets]
- SDMMC1_CMD (R51.2 ↔ U1.83)
- SDMMC1_D0 (R52.2 ↔ U1.65)
- SDMMC1_D3 (R55.2 ↔ U1.79)
- SPI1_SCK (U1.29 ↔ U3.11)
- SPI1_MISO (U1.30 ↔ U3.9)
- SPI1_MOSI (U1.88 ↔ U3.12)

## Batch B3 — MCU east IMU SPI3 + chip-selects  [6 nets]
- SPI3_SCK (U1.89 ↔ U9.13)
- SPI3_MISO (U1.90 ↔ U9.1)
- SPI3_MOSI (U1.91 ↔ U9.14)
- IMU1_CS (U1.9 ↔ U3.10)
- IMU2_GYR_CS (U1.85 ↔ U8.5)
- IMU3_CS (U1.1 ↔ U9.12)

## Batch B4 — CAN + IMU interrupts  [5 nets]
- CAN1_RX (U1.81 ↔ U14.4)
- CAN1_TX (U1.82 ↔ U14.1)
- GPIO_CAN1_SILENT (U1.84 ↔ U14.8)
- IMU2_GYR_INT3 (U1.5 ↔ U8.12)
- IMU3_INT1 (U1.41 ↔ U9.4)

## Batch B5 — South edge motors + heater  [5 nets]
- MOT1 (J11.1 ↔ U1.34)
- MOT2 (J12.1 ↔ U1.35)
- MOT5 (J15.1 ↔ U1.24)
- HEATER_PWM (Q5.1 ↔ U1.31)
- VCAP1 (C17.1 ↔ U1.48)

## Batch B6 — HSE crystal + GND + +3V3A trace + +3V3 stitch leftovers  [7 nets]
- HSE_IN (U1.12 ↔ Y1.1)
- HSE_OUT (U1.13 ↔ C25.1)
- GND (U1.19 ↔ U1.74) — pad-to-pad stitch
- +3V3A (FB1.2 → C19.1) — from (A) fine-stitch failure
- +3V3 stitch leftovers (if (A) reports stuck): R53.1, R54.1, U1.100

## Batch B7 (audit) — 1-pad residuals
- VREF_P, SPI2_MISO, I2C1_SCL, I2C1_SDA
- Likely already partly routed; render context to verify

## Per-corridor output
- `corridors/batch_BN/corridor_<net>.png` — F.Cu + B.Cu side-by-side,
  90 px/mm, crosshair+label pads
- `corridors/batch_BN/index.json` — pads list + bbox + obstacles list

Total ~36 nets across 6-7 batches.
