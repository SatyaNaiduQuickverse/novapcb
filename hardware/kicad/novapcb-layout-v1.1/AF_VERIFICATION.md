# AF verification of 16 re-mux swaps (master 2026-05-22 directive)

Verified against STM32H743 datasheet DS12110 Table 11 AF mapping
+ KiCad symbol library `MCU_ST_STM32H7:STM32H743VITx` pin numbers
(LQFP-100 package).

## STM32H743VITx LQFP-100 pin → port map (from KiCad symbol library)

Key pins:
- N side (pins 76-100): PA14/PA15 (76/77), PC10/PC11/PC12 (78/79/80),
  PD0-PD7 (81-88), PB3/PB4/PB5 (89/90/91), PB6/PB7 (92/93), PB8/PB9
  (95/96), PE0/PE1 (97/98)
- E side (pins 51-75): PB12-15 (51-54), PD8-PD15 (55-62), PC6-PC9
  (63-66), PA8-PA14 (67-72)
- S side (pins 26-50): PA4-PA7 (28-31), PC4/PC5 (32/33), PB0/PB1/PB2
  (34/35/36), PE7-PE15 (37-45), PB10/PB11 (46/47)
- W side (pins 1-25): PE2-PE6 (1-5), PC13-PC15 (7-9), PH0/PH1 (12/13),
  NRST (14), PC0-PC3 (15-18), PA0-PA3 (22-25)

## Per-swap verification

| # | Net | OLD pin | OLD port | NEW pin | NEW port | NEW AF feasible? | Verdict |
|---|---|---|---|---|---|---|---|
| 1 | SPI1_MOSI | 88 | PD7 | 31 | PA7 | AF5 SPI1_MOSI ✓ | **VALID** |
| 2 | SPI3_SCK | 89 | PB3 | 28 | PA4 | PA4 = SPI1_NSS/DAC_OUT1; **NO SPI3 AF** | **INVALID** |
| 3 | SPI3_MISO | 90 | PB4 | 32 | PC4 | PC4 = ETH_RXD1/ADC_IN4; **NO SPI3 AF** | **INVALID** |
| 4 | SPI3_MOSI | 91 | PB5 | 33 | PC5 | PC5 = ETH_RXD2/ADC_IN5; **NO SPI3 AF** | **INVALID** |
| 5 | I2C1_SCL | 92 | PB6 | 36 | PB2 | PB2 has no I2C1 AF | **INVALID** |
| 6 | I2C1_SDA | 93 | PB7 | 37 | PE7 | PE7 = UART7_RX; **NO I2C1 AF** | **INVALID** |
| 7 | GPS1_TX | 86 | PD5 (USART2_TX AF7) | 57 | PD10 | PD10 = FMC_D15 only; **NO USART AF** | **INVALID** |
| 8 | GPS1_RX | 87 | PD6 (USART2_RX AF7) | 58 | PD11 | PD11 = FMC_A16 only; **NO USART AF** | **INVALID** |
| 9 | MOT1 | 34 | PB0 (TIM3_CH3) | 86 | PD5 | PD5 = USART2_TX only; **NO TIMER AF** | **INVALID** |
| 10 | MOT2 | 35 | PB1 (TIM3_CH4) | 87 | PD6 | PD6 = USART2_RX only; **NO TIMER AF** | **INVALID** |
| 11 | MOT3 | 22 | PA0 (TIM2_CH1) | 89 | PB3 | PB3 = TIM2_CH2 AF1 ✓ | **VALID** |
| 12 | MOT4 | 23 | PA1 (TIM2_CH2) | 90 | PB4 | PB4 = no timer; **INVALID** | **INVALID** |
| 13 | MOT5 | 24 | PA2 (TIM5_CH3) | 91 | PB5 | PB5 = TIM3_CH2 AF2 ✓ | **VALID** |
| 14 | MOT6 | 25 | PA3 (TIM5_CH4) | 92 | PB6 | PB6 = TIM4_CH1 AF2 ✓ | **VALID** |
| 15 | MOT7 | 59 | PD12 (TIM4_CH1) | 93 | PB7 | PB7 = TIM4_CH2 AF2 ✓ | **VALID** |
| 16 | MOT8 | 60 | PD13 (TIM4_CH2) | 95 | PB8 | PB8 = TIM4_CH3 AF2 ✓ | **VALID** |

**Score: 6 VALID, 10 INVALID** out of 16 swaps.

## Structural infeasibility — "8 MOT → N" not implementable on LQFP-100

The N side (pins 76-100) only has these timer-channel-capable pins:
- PA15 (77) — TIM2_CH1 — currently BUZZER
- PB3 (89) — TIM2_CH2 — currently SPI3_SCK
- PB4 (90) — no general timer (UART4_TX AF8 only)
- PB5 (91) — TIM3_CH2 AF2
- PB6 (92) — TIM4_CH1 AF2
- PB7 (93) — TIM4_CH2 AF2
- PB8 (95) — TIM4_CH3 AF2 OR TIM10_CH1
- PB9 (96) — TIM4_CH4 AF2 OR TIM11_CH1

So **6 timer-capable pins** are theoretically available on N side
(PA15, PB3, PB5, PB6, PB7, PB8, PB9 — minus PB4 which lacks general
timer AF). That's 6-7, not 8. Plus 2 of these (PA15, PB3) currently
have other functions.

**To get 8 MOTs on N, we'd need to:**
- Free PA15 (currently BUZZER) → relocate BUZZER
- Free PB3 (currently SPI3_SCK) → SPI3 must move elsewhere
- Free PB4 (currently SPI3_MISO) → still no timer AF for PB4
- Use PB6/PB7 for MOT → conflict with I2C1

Even maximally reclaimed: PA15 + PB3 + PB5 + PB6 + PB7 + PB8 + PB9 =
7 channels, one short. **Cannot achieve 8 MOTs on N side.**

Also: PB6/PB7 are I2C1 pins — using them for MOTs requires I2C1 to
move elsewhere (and I2C1 only has AF4 on PB6/7 OR PB8/9 — also N).

## "SPI3 → S" and "I2C1 → S" are ALSO infeasible on LQFP-100

- **SPI3 AF6** on LQFP-100: only PB3/4/5 (N) or PC10/11/12 (N, SDMMC conflict).
  No S-side option.
- **I2C1 AF4** on LQFP-100: only PB6/7 (N) or PB8/9 (N). No S-side option.

## Conclusion

Master's re-mux plan has fundamental AF feasibility issues on the
STM32H743VIT6 LQFP-100 package:
- SPI1 → S: ✓ feasible (PA5/6/7)
- SPI3 → S: ✗ infeasible (no S-side AF)
- I2C1 → S: ✗ infeasible (no S-side AF)
- 8 MOTs → N: ✗ infeasible (only 6-7 N-side timer pins, conflicts with
  I2C1/SPI3 even if those move)
- GPS1 → E: partially feasible (e.g. PD8/PD9 = USART3 on E)
- HEATER_PWM off PA7: ✓ feasible (move to PA15 or PB10 etc.)

## Recommended next steps for master

**Option A — accept the constraints + revise re-mux:**
- SPI1 → S ✓
- SPI3 stays on N (PB3/4/5) — already on right side
- I2C1 stays on N (PB6/7) — already on right side
- Sensor island can still be on S — SPI3/I2C1 traces run N→S (~30mm)
- MOTs partial-N (e.g. 4 on N: PA15/PB3/PB5/PB6 if I2C1 moves to PB8/9; PB7/PB8/PB9 for 3 more = 7) + 1 elsewhere
- OR keep MOTs on current sides (W/S/E) and accept the existing layout

**Option B — escalate to BGA package:**
- STM32H743VGT6 (LQFP-100) → STM32H743IIT6 (LQFP-176) or H743BIT6 (LQFP-208)
- LQFP-176 has many more AF options on each side
- Significant cost + PCB redesign impact

**Option C — keep current SKiDL pin assignments, just re-place
components per the regional strategy:**
- Sensor island on S — accept SPI3/I2C1 traces run from MCU N to island
  S (~30mm — long but routable)
- ESC pads on N — accept MOT traces run from MCU sides to N (long)
- Validate: does the placement-only fix route well enough?

This is what Freerouting on my (AF-invalid) re-muxed PCB will tell us.
If it routes well, then the placement strategy is sound; just need to
keep the EXISTING net topology (no re-mux).

Standing by for master's call.
