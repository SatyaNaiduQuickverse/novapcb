# Step 0 — pin-side load check (master 2026-05-22 placement gate)

## Pin counts per U1 side, before vs after re-mux

| Side | Before | After re-mux | Limit | OK? |
|---|---|---|---|---|
| N | 21 (19 func + 2 power) | **21** (21 func + 2 power) | 25 | ✓ 4 headroom |
| E | 18 (16 func + 3 power) | **18** (16 func + 3 power) | 25 | ✓ 7 headroom |
| S | 13 (9 func + 5 power) | **17** (13 func + 5 power) | 25 | ✓ 8 headroom |
| W | 21 (18 func + 6 power) | **17** (14 func + 6 power) | 25 | ✓ 8 headroom |

All sides comfortably under 25. Total functional+power pins: 73 / 100.

## Re-mux moves applied

**Out of N (8 nets freed):**
- SPI1_MOSI (currently pin 88) → S
- SPI3_SCK (89), SPI3_MISO (90), SPI3_MOSI (91) → S
- I2C1_SCL (92), I2C1_SDA (93) → S
- GPS1_TX (86), GPS1_RX (87) → E

**Into N (8 nets added):**
- MOT1, MOT2, MOT3, MOT4, MOT5, MOT6, MOT7, MOT8 (all 8 ESC outputs)

**Out of W (4 freed):** MOT3-6 (pins 22-25)
**Out of E (2 freed):** MOT7, MOT8 (pins 59, 60)
**Out of S (2 freed):** MOT1, MOT2 (pins 34, 35) → all motors to N

Net change per side:
- N: -8 + 8 = 0 (still 21)
- E: -2 + 2 = 0 (still 18)
- S: -2 + 6 = +4 (13 → 17)
- W: -4 + 0 = -4 (21 → 17)

## SPI2 mux confirmation (per master query)

**STM32H743 LQFP-100, SPI2 alternate functions:**
- AF5 default: **PB13 (SCK) / PB14 (MISO) / PB15 (MOSI)** + PB12 or PB9 (NSS)
- AF mapping alternates for SPI2 (per RM0433 Table 8): PA9/PA10/PA12 conflict
  with USART1_TX/RX and USB OTG_FS_DP (which are pin-locked uses on this board)
- PI-port options (PI0/PI1/PI2/PI3) **not available on LQFP-100** (only on
  LQFP-176+/UFBGA-169)

**Verdict: SPI2 is effectively LOCKED to E side on LQFP-100** (PB13-15 only
usable option). Per master direction: place the SPI2 IMU (U8 BMI088) at the
**island's NE corner** nearest MCU-E and route SPI2 down.

## Re-mux feasibility notes (each new pin needs proper AF)

The COUNT check passes. The SPECIFIC pin assignment per re-mux must be
confirmed against the LQFP-100 column of DS12110 Table 11 (Alternate
Function Mapping). Candidates (subject to that confirmation):

**SPI1 → S side (need SCK/MISO/MOSI):**
- Currently SCK=PA5 (pin 29 S), MISO=PA6 (pin 30 S), MOSI=PA7 (pin 31 S — conflicts with HEATER_PWM)
- **Option:** keep PA5/PA6 as SCK/MISO, move HEATER_PWM off PA7, use PA7 for SPI1_MOSI (pin 31 S).
- OR move SPI1 entirely to PB3/PB4/PB5 (AF6) — pin numbers TBC.

**SPI3 → S side (need SCK/MISO/MOSI):**
- SPI3 AF6: PB3 (SCK) / PB4 (MISO) / PB5 (MOSI). On LQFP-100, PB3/4/5 are on S side region.
- OR SPI3 AF5: PC10/PC11/PC12 — but those are SDMMC1 pin-locked. **Not available.**
- **Option:** PB3/4/5 (need to confirm exact LQFP-100 pin numbers).

**I2C1 → S side (need SDA/SCL):**
- I2C1 AF4: PB6 (SCL) / PB7 (SDA) OR PB8 (SCL) / PB9 (SDA).
- PB6-PB9 on LQFP-100 are around the S-E boundary (pin numbers TBC).
- **Option:** PB6/PB7 likely on S side.

**GPS1 (USART/UART) → E side:**
- USART2: PA2 (TX) / PA3 (RX) — currently W side (pins 24/25 area).
- USART3: PB10/PB11 — S side (pins 46/47), currently used by I2C2 — conflict.
- UART4 / UART5 / UART7 / UART8 — various E-side options on LQFP-100.
- **Option:** UART4 (PD0/PD1) or UART7 (PA8/PA15 region) — TBC.

**8 MOT outputs → N side (need timer-capable GPIO):**
- Need timer channels for DShot. STM32H743 timers TIM1/2/3/4/5/8/15-17.
- TIM1: PA8 (CH1 — currently on E), PA9 (CH2 — used USART1), PA10 (CH3 — used USART1)
  → TIM1 isn't all-N.
- TIM4: PB6/PB7/PB8/PB9 (CH1-4) — but those become I2C1 in re-mux. Conflict.
- TIM3: PA6/PA7/PB0/PB1 (CH1-4) — mostly S side.
- For 8 motors we need 8 timer channels on N pins. **This is the
  trickiest — N side has limited timer channels.** Likely need a mix:
  - TIM3/TIM5 channels on N pins (PD12-PD15 = TIM4 CH1-4? — these are
    N-region pins) — PD12/PD13/PD14/PD15 = TIM4 CH1-4 ✓
  - Then 4 more motors need another timer with N pins.

**Action needed:** Detailed AF mapping per LQFP-100 column of DS12110
Table 11 must be done in the schematic-edit phase. The count check
passes, but final pin numbers per re-mux are subject to that
verification.

## Conflicts and watch-outs

1. **HEATER_PWM on PA7** — currently conflicts with SPI1_MOSI on the
   same pin if we move SPI1_MOSI to PA7. Need to relocate HEATER_PWM
   to a free pin first (e.g. PE7 or similar).
2. **I2C2 on PB10/PB11** (current S side) — must remain to not conflict
   with USART3.
3. **8 MOTs on N side timer-channel constraint** is the real risk; may
   force using 2 different timers + partial GPIO bit-banging for
   DShot. ArduPilot supports per-output timer assignment.

## Verdict

**GO for placement based on counts.** Detailed AF per-pin will be
validated in the schematic edit + ERC re-run that this re-mux requires.

Standing by for master "go ahead" before placing.
