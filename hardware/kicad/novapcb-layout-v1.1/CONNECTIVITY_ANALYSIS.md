# Connectivity Analysis — v1.1 R4 placement-strategy input (2026-05-22)

Per master 2026-05-22: Sai's call to redo placement routability-first.
Master does the placement strategy; this doc is the data input.

Board: 90 × 70 mm, 6-layer JLC06161H-7628, mounting holes M3 at the
4 corners (3, 3), (87, 3), (3, 67), (87, 67) — M3.05 hole + 6mm
keepout.

---

## 1. U1 (STM32H743VITx, LQFP-100) — pin-side map (current orient = 0°)

U1 center (41.0, 35.0). LQFP-100 pin sides:
- **N edge** (Y < 35, faces top of board): pins 76-100
- **E edge** (X > 41, faces right): pins 51-75
- **S edge** (Y > 35, faces bottom): pins 26-50
- **W edge** (X < 41, faces left): pins 1-25

### N side (pins 76-100, ~24 used)
```
 76 SWCLK
 77 BUZZER
 78 SDMMC1_D2
 79 SDMMC1_D3
 80 SDMMC1_CLK
 81 CAN1_RX
 82 CAN1_TX
 83 SDMMC1_CMD
 84 GPIO_CAN1_SILENT
 85 IMU2_GYR_CS
 86 GPS1_TX
 87 GPS1_RX
 88 SPI1_MOSI
 89 SPI3_SCK
 90 SPI3_MISO
 91 SPI3_MOSI
 92 I2C1_SCL
 93 I2C1_SDA
 94 BOOT0
 99 GND
100 +3V3
```
**Subsystems on N side:** SDMMC1 (D2/D3/CLK/CMD), CAN1 (RX/TX/SILENT),
SPI3 (SCK/MISO/MOSI), GPS1 (TX/RX), I2C1 (SCL/SDA), SPI1_MOSI (1 leg),
IMU2_GYR_CS (1 leg), buzzer, SWCLK, boot.

### E side (pins 51-75, ~17 used)
```
 51 IMU2_ACC_CS
 52 SPI2_SCK
 53 SPI2_MISO
 54 SPI2_MOSI
 59 MOT7
 60 MOT8
 63 USART6_TX
 64 USART6_RX
 65 SDMMC1_D0
 66 SDMMC1_D1
 68 USART1_TX
 69 USART1_RX
 70 USB_DM
 71 USB_DP
 72 SWDIO
 73 VCAP2
 74 GND
 75 +3V3
```
**Subsystems on E side:** SPI2 (full bus), IMU2_ACC_CS, MOT7/MOT8,
USART6 (CRSF), USART1 (TELEM), USB (DM/DP), SDMMC1_D0/D1, VCAP2,
SWDIO.

### S side (pins 26-50, ~14 used)
```
 26 GND
 27 +3V3
 29 SPI1_SCK
 30 SPI1_MISO
 31 HEATER_PWM
 34 MOT1
 35 MOT2
 41 IMU3_INT1
 46 I2C2_SCL
 47 I2C2_SDA
 48 VCAP1
 49 GND
 50 +3V3
```
**Subsystems on S side:** SPI1_SCK/MISO (2/3 of bus), MOT1/MOT2,
HEATER_PWM, IMU3_INT1, I2C2 (DPS310 baro), VCAP1.

### W side (pins 1-25, ~17 used)
```
  1 IMU3_CS
  4 IMU2_ACC_INT1
  5 IMU2_GYR_INT3
  6 VBAT
  9 IMU1_CS
 10 GND
 11 +3V3
 12 HSE_IN
 13 HSE_OUT
 14 NRST
 15 BATT_VOLTAGE_SENS
 16 BATT_CURRENT_SENS
 17 BATT2_VOLTAGE_SENS
 18 BATT2_CURRENT_SENS
 19 GND
 20 VREF_P
 21 +3V3A
 22 MOT3
 23 MOT4
 24 MOT5
 25 MOT6
```
**Subsystems on W side:** IMU CS lines (1, 9 — IMU1, IMU3), IMU2
interrupts (4, 5), HSE crystal (12, 13), BATT voltage/current sense
(2 channels), VREF_P, +3V3A, MOT3-MOT6 (4 motor outputs).

---

## 2. Per-peripheral → U1 connections + side

For each peripheral: U1 sides its signals naturally exit from, sorted.

| Component | Pos (mm) | Layer | U1 side counts | Match? |
|---|---|---|---|---|
| **U3** ICM-42688-P (IMU1, SPI1) | (69, 25) | F.Cu | W:4 S:2 N:1 | **MISMATCH** — east of U1 but SPI1 pins are S+N |
| **U8** BMI088 (IMU2, SPI2) | (69, 35) | F.Cu | E:5 W:5 N:1 | OK — SPI2 on E side |
| **U9** LSM6DSV16X (IMU3, SPI3) | (69, 45) | F.Cu | N:3 W:3 S:1 | **MISMATCH** — SE of U1 but SPI3 all on N |
| **U4** DPS310 baro (I2C2, B.Cu) | (66.5, 30) | B.Cu | W:6 S:2 | **MISMATCH** — E of U1 but I2C2 on S |
| **U7** LPS22HB baro (I2C1) | (75, 30) | F.Cu | W:7 N:2 | **MISMATCH** — E of U1 but I2C1 on N |
| **J2** microSD (SDMMC1) | (20, 8.9) | F.Cu | N:4 W:3 E:2 | **BAD** — SW corner but SDMMC1 on N+E sides; routes span entire board |
| **J1** USB-C connector | (39.5, 65.8) | F.Cu | (USB_DM/DP via U5) | **MISMATCH** — N edge but USB_DM/DP on U1 E side |
| **U5** USBLC6 ESD | (32, 55) | F.Cu | E:2 W:1 | **MISMATCH** — NW of U1 but USB on E |
| **U14** TJA1051 CAN | (82.5, 35) | F.Cu | N:3 W:3 | **MISMATCH** — far E but CAN1 on N |
| **J20** CAN connector | (84.5, 50) | F.Cu | (via U14) | Acceptable — sits east of U14 |
| **Y1** 8 MHz HSE crystal | (52, 35) | F.Cu | W:4 (HSE_IN/OUT + GND) | **BAD** — east of U1 but HSE pins are W; trace must cross U1 body |
| **J5** GPS_MAG 10P | (55, 66.5) | F.Cu | N:5 W:2 | OK — N edge, GPS pins on U1 N side |
| **J3** TELEM 6P UART | (24, 66.5) | F.Cu | E:2 W:1 | MISMATCH — NW corner but USART1 on E |
| **J10** CRSF 4P UART | (74, 66.5) | F.Cu | E:2 W:1 | MISMATCH — NE corner but USART6 on E (close — could move east a tad) |
| **J11** ESC1 (MOT1) | (32, 3) | F.Cu | S:1 | OK — south edge, MOT1 on U1 S |
| **J12** ESC2 (MOT2) | (37, 3) | F.Cu | S:1 | OK |
| **J13** ESC3 (MOT3) | (42, 3) | F.Cu | W:1 | MISMATCH — south center but MOT3 on W |
| **J14** ESC4 (MOT4) | (47, 3) | F.Cu | W:1 | MISMATCH — south but MOT4 on W |
| **J15** ESC5 (MOT5) | (52, 3) | F.Cu | W:1 | MISMATCH — south but MOT5 on W |
| **J16** ESC6 (MOT6) | (57, 3) | F.Cu | W:1 | MISMATCH — south but MOT6 on W |
| **J17** ESC7 (MOT7) | (62, 3) | F.Cu | E:1 | OK-ish — south but MOT7 on E |
| **J18** ESC8 (MOT8) | (67, 3) | F.Cu | E:1 | OK-ish — south but MOT8 on E |
| **Q5** AO3400A heater FET | (65, 17) | F.Cu | S:1 | OK |
| **J4** MAUCH1 power 6P | (4, 18) | F.Cu | W:2 (GND only) | OK — W edge, power |
| **J19** MAUCH2 power 6P | (4, 52) | F.Cu | W:2 (GND only) | OK — W edge, power |
| **FB1** +3V3A ferrite | (30.5, 39.5) | F.Cu | W:2 | OK — W of U1, +3V3A on W side |
| **FB2** +3V3_IMU ferrite | (65.5, 52) | F.Cu | (powers U13 LDO for U13→U9) | OK |
| **U6** TPS25940A eFuse | (9, 36.5) | F.Cu | — | OK — power island W |
| **U11/U12** LM74700-Q1 OR-ing | (15.5, 28.5/47.5) | F.Cu | — | OK — power island W |
| **Q3/Q4** AO4262E N-FETs | (11, 28.5/47.5) | F.Cu | — | OK — power island W |
| **U2** AP2112K-3.3 LDO | (24, 27.5) | F.Cu | W:2 | OK |
| **U13** LP5907MFX-3.3 IMU LDO | (69, 52) | F.Cu | W:1 (GND only) | OK — feeds IMUs via FB2 |
| **J9** SWD 10P | (41, 7) | B.Cu | W:5 E:1 N:1 | OK — B.Cu under U1's south edge |

---

## 3. Component sizes (significant)

| Ref | Part | Size (mm) |
|---|---|---|
| U1 | STM32H743VIT6 LQFP-100 | 17.5 × 20.6 (body 14 + 2× courtyard) |
| J2 | microSD DM3AT | 15.8 × 24.1 — large |
| J1 | USB-C 2.0 receptacle | 10.7 × 12.4 |
| J20 | CAN_4P JST-GH | 9.5 × 9.5 |
| U14 | TJA1051TK/3 HVSON-8 | 10.2 × 12.6 |
| U11/U12 | LM74700-Q1 SOT-23-6 | 10.2 × 11.6 |
| U13 | LP5907MFX-3.3 SOT-23-5 | 12.4 × 11.6 |
| U6 | TPS25940A | 8.6 × 8.4 |
| U3 | ICM-42688-P LGA-14 | 32.1 × 6.1 (long axis horizontal) |
| U8 | BMI088 | 5.7 × 13.5 |
| U9 | LSM6DSV16X | 9.8 × 11.5 |
| U4 | DPS310 | 6.1 × 7.9 (B.Cu) |
| U7 | LPS22HB | 7.0 × 11.4 |
| U5 | USBLC6 SOT-23-6 | 10.2 × 6.5 |
| U2 | AP2112K-3.3 SOT-23-5 | 10.5 × 6.5 |
| Y1 | 8 MHz crystal 3225 | 4.2 × 6.6 |

### Reference-prefix counts (small parts)
- **C** (capacitors): 49
- **R** (resistors): 28
- **D** (TVS/ESD diodes): 10
- **Q** (FETs): 4 (Q2/Q3/Q4/Q5)
- **U** (ICs): 14
- **J** (connectors): 17
- **Y** (crystal): 1
- **FB** (ferrites): 2
- **H** (mounting holes): 4

---

## 4. Fixed constraints

### Board
- Outline: 0..90 X × 0..70 Y mm (90 × 70 mm).
- 4 corner mounting holes M3 (M3.05 + 6mm keepout) at:
  (3, 3), (87, 3), (3, 67), (87, 67).
- Stackup: 6-layer JLC06161H-7628 (L1 F.Cu / L2 GND / L3 +3V3 / L4 +5V / L5 GND / L6 B.Cu).

### Connector edge constraints (per `docs/INTERFACE_CONTRACT.md`)
- **USB-C J1**: must be at a board EDGE (currently N edge Y≈65). The
  USB-C through-hole pads/shell need direct access.
- **Power JST-GH (J4 MAUCH1, J19 MAUCH2)**: W edge (cable enters from
  side of airframe).
- **Telemetry J3, GPS J5, CRSF J10**: N edge (currently OK).
- **CAN J20**: edge accessible (currently E edge OK).
- **ESC pads J11-J18**: S edge (solder pads for motor wires).
- **microSD J2**: edge access required for card insertion (currently
  W edge near south); could move to any clean edge.
- **SWD J9**: B.Cu, anywhere accessible from bottom (currently center).

### IMU stress-relief slot
Current: single closed-polygon U-shape slot around the 3-IMU island
(U3/U8/U9 region, X~60-80, Y~22-50), with a 10mm bridge centered at
Y=35. This isolates the IMUs from board flex. Slot is REQUIRED by
prior decision; bridge location is movable.

### Power-zone needs
- Power input region (J4, J19, U6, U11, U12, Q3, Q4, big caps): wide
  GND/+5V routing. Currently in the W block ~ X<25.
- LDO U2 (3.3V) needs to feed every IC. Currently at (24, 27.5).
- IMU isolated 3.3V: FB2 + U13 separate.

### Thermal sources
- U6 TPS25940A eFuse (current limiting)
- Q3/Q4 AO4262E N-FETs (OR-ing pass)
- Q5 AO3400A heater FET (IMU heater)
- U1 MCU (~~250 mA peak)

None of these are catastrophic but plan ground pour for heat spreading.

---

## 5. Brutally honest WHY-CONGESTION read

### Primary issue: MicroSD location vs SDMMC1 pin location
- **J2 microSD at (20, 8.9)** — far SW corner.
- **SDMMC1 signals exit U1 from N side** (D2/D3/CLK/CMD on pins
  78-80, 83) **plus E side** (D0/D1 on pins 65, 66).
- Result: 6 SDMMC traces must cross from MCU N/E edges all the way
  to SW corner. The SDMMC1_CLK trace alone is ~50mm. These cross
  the busy MCU south region, the power region, and the ESC channels.

### Secondary issue: HSE crystal Y1 placement
- **Y1 at (52, 35)** — E of U1 by 11mm.
- **HSE_IN/OUT on U1 W side** (pins 12, 13).
- HSE trace from W edge to Y1 must either go S-around-MCU (~30mm) or
  N-around-MCU (~25mm). Crystal lines must be SHORT (≤5mm typically).
- This is broken; Y1 should be 1-2mm west of U1.

### Tertiary issue: IMU island location vs SPI/CS pin distribution
- All 3 IMUs (U3/U8/U9) clustered at X=69, Y=25/35/45 — E of U1.
- **SPI1 pins are S+N** (pin 29, 30 S; pin 88 N) — U3 should be S or N.
- **SPI3 pins all N** (pins 89-91) — U9 should be N.
- **Only SPI2 (U8) matches** — SPI2 on E side.
- IMU CS lines (pins 1, 9 = IMU3/IMU1) on W side — IMUs are on E,
  so CS lines route around U1.

### Quaternary issue: ESC pad allocation vs MOT pin sides
- ESC pads J11-J18 in row at S edge.
- MOT1/MOT2 on S side ✓; MOT7/MOT8 on E side (OK from S row);
  **MOT3-MOT6 on W side** (pins 22-25) — these 4 motors must route
  from W edge down to S row at X=42-57. Long routes through center.

### Quinary: CAN cluster
- U14 at (82.5, 35) — far E.
- **CAN1 pins on N side** of U1 (81, 82, 84).
- CAN_TX/RX/SILENT route from N edge east-around to U14. They could
  exit MCU N edge directly into TJA1051 if U14 were NE of U1.

### Sixth: USB-C path
- **J1 at N edge**, signals must reach U5 (USBLC6 NW of MCU at (32, 55))
  then route to **U1 USB_DM/DP on E side** (pins 70, 71).
- Path: J1 N → U5 NW → cross center → U1 E side. Long traversal.
- Either move U5 to NE corner near MCU's E side, or change MCU USB
  pin assignment (USB is hard-fixed to pins 70/71 unfortunately —
  STM32H743 USB OTG_FS is dedicated).

---

## 6. Pin-mux flexibility flags

STM32H743 lets us re-assign most peripherals. What CAN move:
- **SPI1**: pins (PA5/PA6/PA7) currently mapped; alternate pin sets
  include PA5/PA6/PA7, PB3/PB4/PB5, PG11/PG12/PG13. Could relocate
  to E side near U3 IMU.
- **SPI2**: PB13/14/15 or PA9/PA12, etc. Current E side works for U8.
- **SPI3**: PB3/4/5 or PC10/11/12. Could move SPI3 pins from N→E
  to bring closer to U9.
- **USART1**: PA9/10 or PB6/7 or PB14/15. Move to wherever J3 sits.
- **USART6**: PC6/7 or PG14/9. Move to match J10.
- **CAN1 (FDCAN1)**: PD0/PD1 or PA11/12 or PB8/9. Could move from N
  to E (closer to U14 if we keep its current spot, or to N if U14
  moves).
- **I2C1**: PB6/7 or PB8/9. Move to wherever the baro lands.
- **I2C2**: PB10/11 or PF0/1. Same.
- **SDMMC1**: pins are MOSTLY hardwired (PC8-PC12 for data lines on
  H743). Limited mux — D0-D3 stay on PC8-PC11, CLK on PC12, CMD on
  PD2. So **SDMMC1 pin location is FIXED** — the microSD card must
  move to be near these pins, not the reverse.
- **USB**: PA11/PA12 — **FIXED** (E side).
- **HSE**: PH0/PH1 — **FIXED** (W side).

### Implication: SDMMC1, USB, HSE are pin-locked
- microSD MUST be NE-ish (close to pins 78-83 on N + pins 65/66 on E).
- USB-C path: J1 → U5 → U1's PA11/PA12 (E side) — U5 should be on
  the E side under or adjacent to MCU's E edge.
- HSE crystal MUST be 1-3mm west of U1.

### Implication: SPI1/SPI3/I2C1/CAN/USART can co-optimize
These are pin-muxable. Master can pick the side that keeps wires
SHORT and lets each peripheral sit on the right side of MCU.

---

## 7. Summary for placement strategy

**Must keep current side:**
- ESC pads J11-J18 (S edge — physical wires exit)
- Power JST-GH J4, J19 (W edge)
- USB-C J1 (any edge; currently N — fine)
- microSD J2 (any edge but must be near U1 N or E)
- CAN J20 (any edge)
- SWD J9 (B.Cu, anywhere)
- Mounting holes (corners, fixed)

**Re-place candidates:**
- microSD J2: SW → **NE** (near U1 pins 78-83) or N edge near U1
- Y1 HSE crystal: E → **W of U1** (1-3mm west of pins 12/13)
- U3 IMU1: E → **S or N of U1** (match SPI1 pins) — or pin-mux SPI1
- U9 IMU3: SE → **N of U1** (match SPI3 pins) — or pin-mux SPI3
- U14 CAN: far E → **NE of U1** (match CAN1 pins on N) — or pin-mux
- U7 baro: E → **N of U1** (match I2C1) — or pin-mux I2C1 to E
- U4 baro (B.Cu): E → **S of U1** (match I2C2)
- U5 USBLC6: NW → **E or NE of U1** (next to USB pins 70/71)
- ESC connectors J13-J16: south middle — **could spread W to match
  MOT3-6 on U1 W side** OR pin-mux MOT3-6 to S/E pin set

**Critical constraint flag:** SDMMC1, USB, HSE are pin-locked. The
SDMMC1 N+E pin spread is unavoidable — microSD MUST sit at the NE.

---

## 8. EMI map — aggressors vs victims

### AGGRESSORS (switching / noisy / source of EMI)
| Source | Loc (mm) | Notes |
|---|---|---|
| **8× ESC outputs (MOT1..MOT8)** | J11-J18 @ S edge (X=32..67, Y=3) | DShot300/600 = 300/600 kbit/s digital pulse, edges ~5ns → harmonics ≥100 MHz |
| **MCU U1 SDMMC1 lines** | N+E sides of U1 | SDMMC1_CLK at ~50MHz during card I/O, 6 fast-edge data lines |
| **MCU U1 SPI buses** | SPI1 S+N, SPI2 E, SPI3 N | ~10-20MHz clocks during xfer (lower aggressor than SDMMC) |
| **MCU U1 USB** | E side (pins 70, 71) | USB 2.0 full-speed 12 Mbps, harmonics to ~100 MHz |
| **HSE crystal Y1 + load caps** | currently (52, 35) | 8MHz fundamental + 16/24/32 MHz harmonics, plus 480MHz PLL output radiation |
| **Power input + eFuse U6** | W block (9, 36.5) | TPS25940A switching/inrush events; current spikes during arming |
| **OR-ing FETs Q3/Q4** | W block (11, 28.5) and (11, 47.5) | switching during power source transitions; ~1µs edges |
| **Heater PWM Q5+R61** | NE (65-71, 17) | AO3400A switching ~1kHz PWM into R61 heater (low-frequency but high di/dt edges) |
| **CAN bus U14 + J20** | E (82, 35-50) | 1Mbit/s CAN bus, ~50ns edges; differential, but radiates |
| **CRSF UART J10** | NE (74, 66.5) | 420 kbaud, lower priority |

### VICTIMS (sensitive / quiet wanted)
| Victim | Loc (mm) | Sensitivity |
|---|---|---|
| **IMU1 ICM-42688-P (U3)** | (69, 25) | accel ±0.5mg, gyro ±0.01dps — needs quiet SPI + isolated 3V3 |
| **IMU2 BMI088 (U8)** | (69, 35) | dual-die accel+gyro, similar |
| **IMU3 LSM6DSV16X (U9)** | (69, 45) | similar |
| **Baro DPS310 (U4)** | (66.5, 30) B.Cu | pressure µbar resolution — sensitive to thermal AND EMI |
| **Baro LPS22HB (U7)** | (75, 30) | same |
| **ADC: BATT_VOLTAGE_SENS, BATT_CURRENT_SENS, ×2 (BATT2)** | U1 W pins 15-18 | 16-bit ADC, sensing power-rail noise |
| **ADC: VREF_P** | U1 W pin 20 | analog reference |
| **USB 2.0 diff pair (USBC_D_M/P_PRE)** | J1 (39, 66) → U5 (32, 55) → U1 E (70, 71) | needs 94.4Ω diff, quiet GND reference |
| **+3V3A analog rail** | FB1 (30.5, 39.5) | feeds VREF_P and analog references |
| **+3V3_IMU rail** | FB2 (65.5, 52) + U13 LDO (69, 52) | feeds the 3 IMUs from filtered supply |

### EMI separation rules (for placement weighting)
- Keep **DShot motor lines** away from **IMUs and baros** by ≥10 mm or
  with a GND-via fence between.
- Keep **HSE crystal** ≥10mm from analog ADC pins / VREF_P.
- Keep **SDMMC1 CLK trace** routed AWAY from IMU SPI buses (different
  side or under solid GND plane).
- Keep **USB diff pair** routed direct over solid GND with no via
  stitches near other-net inductors.
- Keep **heater Q5+R61** away from baros (thermal AND EMI both bad).
- Keep **power-input region** (J4/J19/U6/Q3/Q4/U11/U12) clustered W —
  the high di/dt is naturally far from RHS sensors.
- **+3V3A** (analog) should reach VREF_P with the shortest trace and
  no crossing under digital tracks.

### Current placement violations
- **HSE Y1 at (52, 35)** is 14mm from baros U4/U7 — too close given
  Y1 has 8MHz fundamental + harmonics.
- **U14 CAN xcvr at (82.5, 35)** is right next to baros U7 (75, 30)
  and U9 IMU (69, 45) — CAN edges very close to sensors.
- **HEATER_PWM net from U1.31** runs across the board (~30mm trace
  ending at Q5 at (65, 17)) — crosses any number of sensor lines.
- **ESC pads (J11-J18) at S edge** are 22-30mm from the IMU island at
  (69, 35) — borderline OK, but MOT3-6 must route through the MCU
  S region close to SPI1 and I2C2.

---

## 9. Thermal map — heat sources + power figures

Estimated power dissipation at nominal operating conditions. Worst
case is hover/flight (peak motors + telemetry + SDMMC + sensors).

| Source | Loc (mm) | Spec | Nominal | Peak |
|---|---|---|---|---|
| **U1 STM32H743VITx (MCU)** | (41, 35) | 400 MHz Cortex-M7, 240+ MHz buses, multiple peripherals | ~0.4 W (vec/FPU + DSP active + 4 SPI + SDMMC) | ~0.6 W (turbo + USB transfer + full IPC) |
| **U2 AP2112K-3.3 LDO** | (24, 27.5) | 5V→3.3V drop, feeds MCU + most ICs | ~0.20 W (dropout 1.7V × 120 mA load) | ~0.34 W (250 mA peak) |
| **U13 LP5907MFX-3.3 (IMU LDO)** | (69, 52) | Filtered 3.3V for IMUs | ~0.05 W (1.7V × 30 mA) | ~0.10 W (60 mA) |
| **U6 TPS25940A (eFuse)** | (9, 36.5) | 25 mΩ Rds(on) pass FET, 6A trip | ~0.025 W typ (1A) | ~0.625 W (5A continuous trip threshold) |
| **Q3 AO4262E (OR-ing N-FET A)** | (11, 28.5) | 6.5 mΩ × I² | ~0.026 W (2A) | ~0.16 W (5A) |
| **Q4 AO4262E (OR-ing N-FET B)** | (11, 47.5) | same | same | same |
| **U11/U12 LM74700-Q1** | (15.5, 28.5)/(15.5, 47.5) | active-OR-ing controller | ~0.01 W each | ~0.01 W |
| **Q5 AO3400A (heater FET)** | (65, 17) | switches R61 heater | ~0 W (PWM low duty) | ~0.05 W |
| **R61 (heater resistor)** | (71, 17) | TBD value, marked `TBD_SIM_OUT` — needs spec! | depends — typ. 0.5-1W for IMU heating | up to 2W if used for cold-start IMU warming |
| **HSE crystal Y1 + load caps** | (52, 35) | active oscillator drive | negligible | <10 mW |
| **3 IMUs (U3, U8, U9)** | (69, 25/35/45) | 3-5 mA each | <0.05 W combined | <0.1 W |
| **2 baros (U4, U7)** | (66.5, 30) B.Cu / (75, 30) | <1 mA each | negligible | negligible |
| **TJA1051 CAN xcvr (U14)** | (82.5, 35) | 50 mA peak when CAN active | ~0.05 W | ~0.20 W (high CAN traffic) |

### Total system power
- **Idle:** ~0.5 W (MCU + LDOs + sensors)
- **Hover:** ~0.8 W
- **Stress:** ~1.5 W (peak transient through eFuse + Q3/Q4 + MCU + telemetry)

### Hottest spots (need spreading + thermal vias)
1. **U2 AP2112K LDO** — 0.34W in a SOT-23-5. ~80°C rise without
   copper pour. Currently at (24, 27.5). Wants thermal pour S + W.
2. **U6 TPS25940A eFuse** — 0.625W trip case. HVSON-8, big pad.
   Currently at (9, 36.5). Wants pour.
3. **Q3+Q4 AO4262E** — 0.16W each peak. SOIC-8 with thermal pad.
   Currently at (11, 28.5) and (11, 47.5).
4. **U1 MCU** — 0.6W spread over 14×14mm body. Less critical (pin
   pads themselves spread the heat into PCB). Avoid heat clustering
   underneath.
5. **R61 heater** — TBD W. Heater is INTENTIONALLY hot (target IMU
   warming). Should sit NEAR but not UNDER the IMU island. Currently
   at (71, 17) — 8mm SW of U3 IMU. OK distance for radiative coupling
   but baros (U4, U7) are similarly close — may detect heater pulses.

### Placement constraints from thermal
- **U2 LDO**, **U6 eFuse**, **Q3/Q4 FETs** — keep clustered in W
  block (current placement OK); provide large copper pour + thermal
  vias to inner GND plane.
- **U13 IMU LDO** — small power, can stay near U9 IMU current loc.
- **R61 heater** — should be physically CLOSE to but not directly
  ABOVE the IMUs (intentional heat coupling, but localized).
- **NO** hot components clustered under U1 MCU (avoid additional
  heating of CPU silicon).

---

## 10. Data files

Full peripheral-pin map JSON in `connectivity_data.json`.

