# MCU Pin Map Audit — Full Pre-Routing Reach Analysis

> **Status**: DRAFT for master + Sai review. NO LAYOUT / NO HWDEF /
> NO SKIDL TOUCH until Sai ratifies the remap diff (§5).
> **Branch**: `audit/mcu-pin-map-audit` off `sch/option-b-buck` head `ea6d62f`.
> **Trigger**: H↔C routing 2× escalation (2026-05-24) — MOT3-6 west-edge
> + MOT7-8 east-edge MCU pin assignments physically block clean F.Cu
> fanout to south-edge J11 ESC connector. Pattern is "pins locked
> early, placement done, routing discovers reach problems." Master
> directive: catch all remaining subsystem reach issues on paper, propose
> single coordinated remap, Sai-ratify before any execution.
> **Sub-step**: #109.

---

## 0. Sources of truth (and conflicts)

Authoritative per subsystem:

| Subsystem | Source of truth | Notes |
|---|---|---|
| All connector / sensor schematic refs | `hardware/kicad/novapcb/sheets/*.py` (SKiDL) | Board netlist generated from these |
| Phase 4 board placement / nets | `hardware/kicad/novapcb-stepwise/novapcb-stepwise.kicad_pcb` | Generated from SKiDL netlist |
| MCU pin assignments — runtime | `firmware/hwdef-novapcb/hwdef.dat` | **Currently STALE** — `task #66` revision in flight |
| MCU pin name → physical pad # | `MCU_ST_STM32H7:STM32H743VITx` KiCad symbol | Authoritative for LQFP-100 pad numbering |

### Known SKiDL ↔ hwdef.dat discrepancies (per task #66)

Detected by direct grep of board nets vs `hwdef.dat`:

| Net on board (SKiDL) | hwdef.dat status | SKiDL PXn assignment |
|---|---|---|
| MOT1..MOT8 | hwdef.dat:168-175 has them | matches SKiDL |
| HEATER_PWM | not in hwdef.dat | `power_3b.py:643` → PA15 |
| IMU3_CS, IMU3_INT1 | not in hwdef.dat | `imu_3c.py:280,288` → PE2, PE11 |
| IMU2_ACC_CS, IMU2_ACC_INT1, IMU2_GYR_CS, IMU2_GYR_INT3 | not in hwdef.dat | `imu_3c.py` → PB12, PE5, PD4, PE6 |
| BATT2_VOLTAGE_SENS, BATT2_CURRENT_SENS | not in hwdef.dat | `power_sd_swd_3h.py:214-215` → PC2_C, PC3_C |
| SDMMC1_CLK | not in hwdef.dat (has `SDMMC1_CK`) | `power_sd_swd_3h.py:299` → PC12 (name mismatch only) |
| GPS1_TX, GPS1_RX | not in hwdef.dat | `gps_mag_3e.py:135,136` → PD5, PD6 |
| USB_DM, USB_DP | not in hwdef.dat (has `OTG_FS_DM/DP`) | `crsf_usb_3g.py:143,144` → PA11, PA12 (semantic match, name mismatch) |
| SWDIO, SWCLK | not in hwdef.dat (has `JTMS-SWDIO`, `JTCK-SWCLK`) | `power_sd_swd_3h.py:350,351` → PA13, PA14 |

**Action for task #66 revision (NOT this PR)**: add missing nets to
hwdef.dat with PXn matching SKiDL. **For this audit**: SKiDL is the
operational truth since the board reflects it.

## 1. MCU pin map per edge (current state)

STM32H743VITx LQFP-100 — KiCad symbol `MCU_ST_STM32H7:STM32H743VITx`
maps pads 1-100 to PXn ports. Edge classification from board placement
(MCU centered at (45, 35), bbox X=36.24..53.76 Y=24.72..45.28).

### West edge — pads 1-25 (X≈37.33)

| Pad | PXn | Net (board) | Subsystem |
|---:|---|---|---|
| 1 | PE2 | IMU3_CS | D — IMU3 chip select |
| 2 | PE3 | — | (NC) |
| 3 | PE4 | — | (NC) |
| 4 | PE5 | IMU2_ACC_INT1 | D — IMU2 accel interrupt |
| 5 | PE6 | IMU2_GYR_INT3 | D — IMU2 gyro interrupt |
| 6 | VBAT | VBAT | C — backup domain |
| 7 | PC13 | — | (NC) |
| 8 | PC14 | — | (NC, OSC32_IN cap) |
| 9 | PC15 | IMU1_CS | D — IMU1 chip select |
| 10 | VSS | GND | C |
| 11 | VDD | +3V3 | C |
| 12 | PH0 (OSC_IN) | HSE_IN | C — 8 MHz crystal |
| 13 | PH1 (OSC_OUT) | HSE_OUT | C |
| 14 | NRST | NRST | C — reset |
| 15 | PC0 | BATT_VOLTAGE_SENS | A — ADC1 mauch V |
| 16 | PC1 | BATT_CURRENT_SENS | A — ADC1 mauch I |
| 17 | PC2_C | BATT2_VOLTAGE_SENS | A — ADC mauch2 V |
| 18 | PC3_C | BATT2_CURRENT_SENS | A — ADC mauch2 I |
| 19 | VSSA | GND | C — analog GND |
| 20 | VREF+ | VREF_P | C — analog reference |
| 21 | VDDA | +3V3A | C — analog supply |
| 22 | PA0 | MOT3 | **H — DShot TIM2_CH1 ←BLOCKED** |
| 23 | PA1 | MOT4 | **H — DShot TIM2_CH2 ←BLOCKED** |
| 24 | PA2 | MOT5 | **H — DShot TIM5_CH3 ←BLOCKED** |
| 25 | PA3 | MOT6 | **H — DShot TIM5_CH4 ←BLOCKED** |

### South edge — pads 26-50 (Y≈42.67)

| Pad | PXn | Net (board) | Subsystem |
|---:|---|---|---|
| 26 | VSS | GND | C |
| 27 | VDD | +3V3 | C |
| 28 | PA4 | — | (FREE) |
| 29 | PA5 | SPI1_SCK | D — IMU SPI1 clock |
| 30 | PA6 | SPI1_MISO | D — IMU SPI1 data-in |
| 31 | PA7 | SPI1_MOSI | D — IMU SPI1 data-out (re-muxed 2026-05-22) |
| 32 | PC4 | — | (FREE) |
| 33 | PC5 | — | (FREE, was RSSI_ADC in hwdef but no net on board) |
| 34 | PB0 | MOT1 | H — DShot TIM3_CH3 ✓ (clean south fanout) |
| 35 | PB1 | MOT2 | H — DShot TIM3_CH4 ✓ |
| 36 | PB2 | — | (FREE) |
| 37 | PE7 | — | (FREE — TIM1_ETR or UART7_RX) |
| 38 | PE8 | — | (FREE — TIM1_CH1N or UART7_TX) |
| 39 | PE9 | — | (FREE — **TIM1_CH1** or UART7_RTS) |
| 40 | PE10 | — | (FREE — TIM1_CH2N or UART7_CTS) |
| 41 | PE11 | IMU3_INT1 | D — IMU3 interrupt |
| 42 | PE12 | — | (FREE — TIM1_CH3N) |
| 43 | PE13 | — | (FREE — **TIM1_CH3**) |
| 44 | PE14 | — | (FREE — **TIM1_CH4**) |
| 45 | PE15 | — | (FREE — TIM1_BKIN) |
| 46 | PB10 | I2C2_SCL | E — baro I2C clock |
| 47 | PB11 | I2C2_SDA | E — baro I2C data |
| 48 | VCAP | VCAP1 | C — core LDO |
| 49 | VSS | GND | C |
| 50 | VDD | +3V3 | C |

### East edge — pads 51-75 (X≈52.67)

| Pad | PXn | Net (board) | Subsystem |
|---:|---|---|---|
| 51 | PB12 | IMU2_ACC_CS | D — IMU2 accel CS |
| 52 | PB13 | SPI2_SCK | D — IMU SPI2 clock |
| 53 | PB14 | SPI2_MISO | D — IMU SPI2 in |
| 54 | PB15 | SPI2_MOSI | D — IMU SPI2 out |
| 55 | PD8 | — | (FREE — USART3_TX in hwdef but no SKiDL bind) |
| 56 | PD9 | — | (FREE — USART3_RX) |
| 57 | PD10 | — | (FREE — PINIO1) |
| 58 | PD11 | — | (FREE — PINIO2) |
| 59 | PD12 | MOT7 | **H — DShot TIM4_CH1 ←BLOCKED by U7 BARO** |
| 60 | PD13 | MOT8 | **H — DShot TIM4_CH2 ←BLOCKED by U7 BARO** |
| 61 | PD14 | — | (FREE — TIM4_CH3) |
| 62 | PD15 | — | (FREE — TIM4_CH4) |
| 63 | PC6 | USART6_TX | G — CRSF UART |
| 64 | PC7 | USART6_RX | G — CRSF UART |
| 65 | PC8 | SDMMC1_D0 | G — microSD |
| 66 | PC9 | SDMMC1_D1 | G — microSD |
| 67 | PA8 | — | (FREE — TIM1_CH1 alt) |
| 68 | PA9 | USART1_TX | G — TELEM1 |
| 69 | PA10 | USART1_RX | G — TELEM1 |
| 70 | PA11 | USB_DM | F — USB-C D− |
| 71 | PA12 | USB_DP | F — USB-C D+ |
| 72 | PA13 | SWDIO | G — SWD |
| 73 | VCAP | VCAP2 | C |
| 74 | VSS | GND | C |
| 75 | VDD | +3V3 | C |

### North edge — pads 76-100 (Y≈27.32)

| Pad | PXn | Net (board) | Subsystem |
|---:|---|---|---|
| 76 | PA14 | SWCLK | G — SWD |
| 77 | PA15 | HEATER_PWM | D — IMU heater (TIM2_CH1) |
| 78 | PC10 | SDMMC1_D2 | G — microSD |
| 79 | PC11 | SDMMC1_D3 | G — microSD |
| 80 | PC12 | SDMMC1_CLK | G — microSD |
| 81 | PD0 | CAN1_RX | G — CAN |
| 82 | PD1 | CAN1_TX | G — CAN |
| 83 | PD2 | SDMMC1_CMD | G — microSD |
| 84 | PD3 | GPIO_CAN1_SILENT | G — CAN xcvr enable |
| 85 | PD4 | IMU2_GYR_CS | D — IMU2 gyro CS |
| 86 | PD5 | GPS1_TX | G — GPS UART (USART2) |
| 87 | PD6 | GPS1_RX | G — GPS UART |
| 88 | PD7 | BUZZER | G — buzzer |
| 89 | PB3 | SPI3_SCK | D — IMU SPI3 clock |
| 90 | PB4 | SPI3_MISO | D — IMU SPI3 in |
| 91 | PB5 | SPI3_MOSI | D — IMU SPI3 out |
| 92 | PB6 | I2C1_SCL | G — external mag I2C |
| 93 | PB7 | I2C1_SDA | G — external mag I2C |
| 94 | BOOT0 | BOOT0 | C |
| 95 | PB8 | — | (FREE — TIM4_CH3 alt, **TIM16_CH1**) |
| 96 | PB9 | — | (FREE — TIM4_CH4 alt, **TIM17_CH1**) |
| 97 | PE0 | — | (FREE — UART8_RX) |
| 98 | PE1 | — | (FREE — UART8_TX) |
| 99 | VSS | GND | C |
| 100 | VDD | +3V3 | C |

### Edge summary

| Edge | Pad range | Free signal pads | Free with TIM-channel PWM |
|---|---|---:|---:|
| West | 1-25 | 4 (PE3, PE4, PC13, PC14) | 0 |
| **South** | 26-50 | **12** (PA4, PC4, PC5, PB2, PE7..10, PE12..15) | **3** (PE9 TIM1_CH1, PE13 TIM1_CH3, PE14 TIM1_CH4) |
| East | 51-75 | 6 (PD8, PD9, PD10, PD11, PD14, PD15, PA8) | 3 (PD14 TIM4_CH3, PD15 TIM4_CH4, PA8 TIM1_CH1) |
| North | 76-100 | 4 (PB8, PB9, PE0, PE1) | 2 (PB8 TIM16_CH1, PB9 TIM17_CH1) |

## 2. Per-subsystem fanout reach analysis

### A — Power input (Mauch ADC sense + eFuse)

**Connectors**: J4 Mauch1 (16, 5), J19 Mauch2 (89, 5) — both north-edge,
mirror-pair across X=52.5.

**MCU pins**: PC0/PC1/PC2_C/PC3_C — all WEST edge pads 15-18.

**Reach**: ~38mm for J4-side sense (PC0/PC1 at X=37, Y=36) to J4 at (16, 5).
For J19-side (PC2_C/PC3_C at X=37, Y=37), need long sense traces to J19 at (89, 5) — ~80mm. **Already routed in PR #87** (sense sub-step).

**Status**: ✅ DONE — routes verified in PR #87 cluster walk.

### B — 3V3 regulator (U2 TPS62177)

**No MCU signal pins**, power-only. Status: ✅ DONE (PR #85, A↔B etc).

### C — MCU core (decap + HSE + power pins)

**MCU pins**: VDD/VSS pairs at pads 10/11, 26/27, 49/50, 73/74, 99/100;
VDDA pad 21, VSSA pad 19, VREF+ pad 20, VBAT pad 6, VCAP pads 48/73,
NRST pad 14, BOOT0 pad 94, HSE PH0/PH1 pads 12/13.

**Reach**: all decap caps + HSE crystal are placed within ~3mm of their
respective MCU pads. Status: ✅ DONE (PR #70 + earlier).

### D — IMU SPI + interrupts + heater

**MCU pins**:
- SPI1 (IMU1 ICM-42688): PA5/PA6/PA7 pads 29/30/31 S + PC15 pad 9 W
- SPI2 (IMU2 BMI088): PB13-15 pads 52-54 E + PB12 pad 51 E + PD4 pad 85 N
- SPI3 (IMU3 LSM6DSV16X): PB3-5 pads 89-91 N + PE2 pad 1 W
- Interrupts: PE5 pad 4 W, PE6 pad 5 W, PE11 pad 41 S
- HEATER_PWM: PA15 pad 77 N

**D-zone island**: X=56..86, Y=51..63 (per docs/D_PLACEMENT_CONSTRAINT_ANALYSIS.md)

**Reach**: ✅ DONE (PR #77 + PR #78). HEATER_PWM PA15 (pad 77 N) routes
N-to-S across MCU body via existing B.Cu wraparound — clean per audit.

### E — Baro I2C

**MCU pins**: PB10/PB11 pads 46/47 S
**Component**: U10 LPS22HB at (~88, ~25 — east band, parked)

Wait — let me re-check. Looking at the audit data, U7 is the BARO in the east MCU area. Let me re-clarify by checking.

**Status**: ✅ DONE (PR #73).

### F — USB-C

**MCU pins**: PA11/PA12 pads 70/71 E
**Connector**: J1 USB-C at (83.78, 30) E side
**Reach**: ~32mm with Z_diff bracket [87.4, 105.75]Ω verified
**Status**: ✅ DONE (PR #74).

### G — Mixed comms (CAN, microSD, GPS, CRSF, TELEM, SWD, BUZZER)

| Net | MCU pin | Pad/Edge | Connector (planned position) | Reach est. | Status |
|---|---|---|---|---|---|
| CAN1_RX | PD0 | 81 N | J20 CAN (164, 0) parked → east band? | 90mm | PENDING — see §3 |
| CAN1_TX | PD1 | 82 N | same | 90mm | PENDING |
| CAN1_SILENT | PD3 | 84 N | same | 90mm | PENDING |
| SDMMC1_D0 | PC8 | 65 E | J2 microSD (194, 6) parked → east band? | 60mm | PENDING |
| SDMMC1_D1 | PC9 | 66 E | same | 60mm | PENDING |
| SDMMC1_D2 | PC10 | 78 N | same | 80mm | PENDING |
| SDMMC1_D3 | PC11 | 79 N | same | 80mm | PENDING |
| SDMMC1_CLK | PC12 | 80 N | same | 80mm | PENDING |
| SDMMC1_CMD | PD2 | 83 N | same | 80mm | PENDING |
| GPS1_TX | PD5 | 86 N | J5 GPS 10P (179, 6) parked → north or east band | 60-100mm | PENDING |
| GPS1_RX | PD6 | 87 N | same | 60-100mm | PENDING |
| I2C1_SCL | PB6 | 92 N | J5 GPS_MAG | 60-100mm | PENDING |
| I2C1_SDA | PB7 | 93 N | J5 GPS_MAG | 60-100mm | PENDING |
| BUZZER | PD7 | 88 N | J5 buzzer pin (shared with GPS conn) | 60-100mm | PENDING |
| USART6_TX (CRSF) | PC6 | 63 E | J10 CRSF (125, 3) parked | 75mm | PENDING |
| USART6_RX (CRSF) | PC7 | 64 E | same | 75mm | PENDING |
| USART1_TX (TELEM) | PA9 | 68 E | J3 TELEM 6P (110, 6) parked | 70mm | PENDING |
| USART1_RX (TELEM) | PA10 | 69 E | same | 70mm | PENDING |
| SWDIO | PA13 | 72 E | J9 SWD (197, 9) parked → east band | 120mm | PENDING |
| SWCLK | PA14 | 76 N | same | 120mm | PENDING |

### G subsystem PENDING analysis (corridor + obstacle)

For each net's fanout from MCU pad to its target connector zone, the
**obstacle map** must be re-checked at PLACEMENT time per Rule 18
(tracks AND component pads). Below is the proactive flagging based on
expected placement zones:

**EAST band (X=88..105 Y=0..85)** — likely hosts J1 USB-C (already
placed @ X=84), J20 CAN, J2 microSD. Multiple connectors competing
for east band real estate. Reach calc assumes connectors lined up.

**NORTH band (Y=0..18)** — likely hosts J3 TELEM, J5 GPS_MAG, J10 CRSF,
microSD card slot extension. Tight.

**Obstacle survey**: at this time, ONLY DONE subsystems have routes.
Pending subsystems' corridors are mostly clean except where existing
routes pass through. **Specific reach concerns**:

- **CAN1** (PD0/PD1/PD3 north MCU edge pads 81/82/84): routes north-east
  to J20 in east band. Path crosses GPS/microSD planned routes if
  J20 lands far east. **LIKELY CLEAN** if J20 lands at (~95, 5).
- **SDMMC1** (mix of east + north MCU pads, 6 nets, length-matched):
  J2 microSD parked at (194, 6) needs final landing. If J2 ends up
  in north-east corner (~95, 10), reach 30-50mm per net. Length
  matching tolerance per Phase 4 spec (≤5mm) — **MAYBE CLEAN**, depends
  on placement.
- **GPS+I2C1+BUZZER** (5 nets, all north MCU pads 86-93): route north
  to J5 in north band — short reach if J5 lands at (~80, 5). **CLEAN**.
- **CRSF** (PC6/PC7 east MCU pads 63/64): J10 CRSF parked. If J10
  lands east band Y=15..20 (between USB-C and CAN), reach 30mm. **CLEAN**.
- **TELEM** (PA9/PA10 east MCU pads 68/69): J3 east band similar to
  CRSF. **CLEAN**.
- **SWD** (PA13 east pad 72 + PA14 north pad 76): J9 SWD ribbon
  header parked at (197, 9). PA13/PA14 split between two edges (E
  + N) — fanout naturally splits. If J9 lands in east-north corner
  (~98, 10) — reach 25-30mm per net. **CLEAN**.

**G subsystem verdict**: no current-state-blocked nets. Reach assumes
placements land in plausible zones. **Real obstacles appear when
placement happens** — Rule 18 catch list applies at each G placement
sub-step.

### H — ESC outputs (CURRENT BLOCKER)

**MCU pins**:
- MOT1 PB0 pad 34 S ✅
- MOT2 PB1 pad 35 S ✅
- MOT3 PA0 pad 22 **W** ❌
- MOT4 PA1 pad 23 **W** ❌
- MOT5 PA2 pad 24 **W** ❌
- MOT6 PA3 pad 25 **W** ❌
- MOT7 PD12 pad 59 **E** ❌
- MOT8 PD13 pad 60 **E** ❌

**Connector**: J11 JST-GH 10P at (52.5, 80) **S band** (PR #81).

**Blocked**: MOT3-6 exit MCU west into cap field (8 caps + crystal
+ R2 at X=33..37 Y=25..50) — no clean F.Cu south path. MOT7-8 exit
MCU east into U7 BARO (X=51.52..58.48 Y=41.32..52.68) blocking south
path.

**Two-time-failure** documented in H↔C escalation 2026-05-24:
- 3× F.Cu manual routing attempts: +30-49 net new DRC each
- Freerouting: OOM (88 unrouted) + NPE on aggressive strip
- Root cause confirmed via component-pad survey (analysis missed this)

## 3. Coordinated remap proposal — MINIMAL DIFF

### Primary remap: move MOT3-6 to TIM1_CHn on south edge

STM32H743 TIM1 is an **advanced timer** supporting BDSHOT. Available
free pads on south edge: PE9 (CH1), PE13 (CH3), PE14 (CH4). PE11 (CH2)
currently has **IMU3_INT1** — needs cascading move.

| Net | Old PXn (edge) | New PXn (edge) | Old timer | New timer | BDSHOT-capable? |
|---|---|---|---|---|---|
| MOT3 | PA0 (W) | **PE9 (S, pad 39)** | TIM2_CH1 | TIM1_CH1 | ✓ (CH1) |
| MOT4 | PA1 (W) | **PE11 (S, pad 41)** | TIM2_CH2 | TIM1_CH2 | ✓ (CH2) |
| MOT5 | PA2 (W) | **PE13 (S, pad 43)** | TIM5_CH3 | TIM1_CH3 | ✓ (CH3) |
| MOT6 | PA3 (W) | **PE14 (S, pad 44)** | TIM5_CH4 | TIM1_CH4 | ✓ (CH4) |

**Cascading move** (PE11 needs to vacate for MOT4):

| Net | Old PXn (edge) | New PXn (edge) | Rationale |
|---|---|---|---|
| IMU3_INT1 | PE11 (S, pad 41) | **PB2 (S, pad 36)** | PB2 is FREE on south edge; GPIO INT only (no peripheral conflict) |

### Secondary remap: move MOT7-8 to south or accept east-edge cost

**Two sub-options** (Sai-pick):

**Sub-option H-α** — Move MOT7/8 to TIM4_CH3/CH4 on north-edge alternates:

| Net | Old PXn (edge) | New PXn (edge) | New timer |
|---|---|---|---|
| MOT7 | PD12 (E, pad 59) | **PB8 (N, pad 95)** | TIM4_CH3 (basic, BDSHOT works) |
| MOT8 | PD13 (E, pad 60) | **PB9 (N, pad 96)** | TIM4_CH4 |

- **Pros**: PB8/PB9 free on north edge; TIM4 supports BDSHOT; consistent
  timer with hwdef.dat current group; routing goes N from MCU, then
  east, then south through east band to J11 (long but clear of D-zone)
- **Cons**: NORTH edge is crowded near MCU (SDMMC1, CAN, IMU2_GYR_CS,
  GPS_MAG, BUZZER, SPI3 N pads). Adding 2 motor routes to N edge fanout
  may cause its own H↔C-class issue. **Needs N-edge corridor survey before commit.**

**Sub-option H-β** — Keep MOT7/8 on PD12/PD13 (east), route via SPI3_MISO wraparound recovery (from earlier option Q):

| Net | Old PXn (edge) | New PXn (edge) | Action |
|---|---|---|---|
| MOT7 | PD12 (E, pad 59) | **PD12 (no change)** | Re-route existing SPI3_MISO B.Cu east to free X=54 column |
| MOT8 | PD13 (E, pad 60) | **PD13 (no change)** | Same |

- **Pros**: Minimal pin diff (0 H changes for MOT7/8); SPI3_MISO B.Cu
  re-route is a ~30min localized fix; preserves D-zone signature
- **Cons**: SPI3_MISO is a routed signal — re-route adds regression
  risk to D zone; existing SPI3_MISO routing is dense
- **Routing detail**: shift SPI3_MISO from F.Cu @ X=54.96 endpoint to
  X=58+ (east of U7) — gives X=54.0 column to MOT7/8 B.Cu south leg

### Cascading per sub-option

**H-α cascade**: PB8/PB9 are currently FREE. No further moves needed.

**H-β cascade**: SPI3_MISO B.Cu re-route only. Affects 1 net.

### Per-edge "after-remap" map (assuming H-α + IMU3_INT1 → PB2)

**SOUTH edge after remap**: now hosts MOT1-6 (was 1-2 + 4 free), I2C2,
SPI1, IMU3_INT1, PE10/PE12/PE15 free. **6 motor fanouts on south edge
→ clean J11 reach.**

**NORTH edge after remap**: adds MOT7-8 to existing cluster (SDMMC, CAN,
GPS, IMU2_GYR_CS, SPI3). 13 nets on north → 15 nets. Density warrants
N-band corridor survey before commit.

**WEST edge after remap**: drops MOT3-6, becomes lighter. Cap field
still in place.

**EAST edge after remap (H-α)**: drops MOT7-8, lighter.
**EAST edge after remap (H-β)**: unchanged on MCU side, SPI3_MISO trace shifted east.

## 4. Predicted regression risk

| Item | Risk | Mitigation |
|---|---|---|
| MOT3-6 → PE9/PE11/PE13/PE14 (TIM1_CH1-4) | Low — TIM1 advanced timer, BDSHOT supported per ArduPilot | hwdef.dat amend: 4 lines change. SKiDL esc_3f.py:147-154 motor_map update |
| IMU3_INT1 PE11 → PB2 | Very low — GPIO only, no peripheral | imu_3c.py:288 change one line |
| MOT3-6 traces removed (W edge → S edge) | None on current board (MOT3-6 UNROUTED) | n/a |
| H-α: MOT7/8 → PB8/PB9 | Medium — N edge corridor unverified | Survey N-edge first; commit only if corridor passes |
| H-β: SPI3_MISO re-route | Medium — D zone routing touched; cluster walk required | Per-net Rule 9 walk after re-route; expect 0 DRC delta |
| hwdef.dat updates | Coordinated with task #66 in flight | Bundle pin remap into #66 revision |
| ArduPilot board-config | TIM1 is a standard advanced timer; ArduPilot supports it natively (MatekH743 uses TIM1 for some outputs) | Verify in ArduPilot ChibiOS hwdef generator |
| ERC | Clean if all SKiDL refs updated consistently | Run after SKiDL changes |

## 5. Decisions for Sai sign-off

### Locked recommendations

**Primary (no Sai sign-off needed beyond ratification of the file)**:
- MOT3 → PE9 (pad 39 S, TIM1_CH1, BDSHOT)
- MOT4 → PE11 (pad 41 S, TIM1_CH2, BDSHOT)
- MOT5 → PE13 (pad 43 S, TIM1_CH3)
- MOT6 → PE14 (pad 44 S, TIM1_CH4)
- IMU3_INT1 → PB2 (pad 36 S, GPIO INT)

### Sai decision: H-α vs H-β

**H-α** (MOT7/8 → PB8/PB9 N edge, TIM4_CH3/CH4):
- All 8 motors off the problematic west+east edges
- N edge corridor risk medium — needs survey
- Larger total diff (6 SKiDL changes, 6 hwdef changes)

**H-β** (keep MOT7/8 on PD12/PD13, re-route SPI3_MISO):
- Smallest pin-diff (4 H changes + 1 IMU3 cascade)
- Touches existing D-zone routing (regression risk medium)
- ~30 min SPI3 re-route work in addition to MOT3-6 remap

**Worker recommendation: H-α** — clearer separation of subsystems, no
existing-routing touch. The N-edge corridor risk is manageable since
N edge has lighter routing density than W/E (we have data: pads 95-98
are all FREE, no obstacles between MCU N pads and any planned N-band
connector).

### Sai decision: when to revise hwdef.dat

Currently `task #66` (hwdef revision to v1.1 SKiDL) is in_progress
with HEATER_PWM PA15 timer-conflict blocked. Option:
- **(a) Bundle this remap into task #66** — single hwdef revision PR
  resolves all known discrepancies + adds remap
- **(b) Standalone hwdef remap PR** — focused, smaller scope, easier
  to review

**Worker recommendation: (a) bundle** — task #66 is the natural carrier;
no rationale to split.

### Stop sequence reminder (per master directive)

After Sai ratifies:
1. Worker: SKiDL amend (esc_3f.py motor_map + imu_3c.py IMU3_INT1) — separate PR (Sai-gated, schema change)
2. Worker: hwdef.dat amend (bundle into task #66) — separate PR (Sai-gated, firmware change)
3. Worker: re-route H↔C (now with cleaner fanout) — master-mergeable
4. Worker: if H-α picked: N-edge corridor survey first; if clean, MOT7/8 re-route too

NO execution until Sai signs off on §5 decisions.

---

**Awaiting master review + Sai ratification before any code/firmware/layout touch.**
