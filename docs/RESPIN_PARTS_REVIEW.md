# novapcb v1.1 — New Parts Review (R1 gate doc)

> **Purpose**: distinct R1 gate doc per master directive (Sai, 2026-05-21).
> Every new part for the v1.1 redundancy re-spin is vetted here BEFORE any
> part enters the schematic. Master reviews thoroughly; this is a hard gate.
>
> **Companion doc**: `docs/RESPIN_SCOPE.md` — overall scope, phases, sims.
>
> **Mandatory column**: ArduPilot driver support for IMU + baro. A sensor
> ArduPilot can't talk to is useless. Driver evidence cited from local
> `~/ardupilot/libraries/` source.

---

## 1. Inertial measurement units (IMUs)

Triple-IMU dissimilar, each on its own SPI bus.

### IMU1 — ICM-42688-P (kept from v1.0)

| Field | Value |
|---|---|
| MPN | ICM-42688-P |
| Vendor | TDK InvenSense |
| Package | LGA-14, 2.5 × 3.0 mm |
| Why chosen | Most-deployed ArduPilot IMU; already in v1.0 BOM; proven Pixhawk6X primary; high-rate (>32 kHz) low-noise gyro/accel. Sai/master Open-Q5: confirmed keep. |
| **ArduPilot driver** | **CONFIRMED** — `libraries/AP_InertialSensor/AP_InertialSensor_Invensensev3.cpp` (covers ICM-42688-P, ICM-40609, ICM-20649, IIM-42652, etc.). Active hwdef use: `Pixhawk6X/hwdef.dat` line `SPIDEV icm42688 SPI2 DEVID1 SP2_CS1 MODE3 2*MHZ 8*MHZ`. |
| JLC PCBA library | LCSC C1850418, JLC Extended |
| Voltage | 1.71–3.6V (signal+VDDIO compatible with 3.3V) |
| Interface | SPI mode 0/3, up to 24 MHz (capped at 8 MHz in ArduPilot read path) |
| Operating temp | −40 to +85°C |
| Current | ~0.55 mA typ (active 6-axis @ 1 kHz ODR) |
| Dissimilarity | Vendor: TDK; silicon family: InvenSense ICM-4xxxx |

### IMU2 — BMI088

| Field | Value |
|---|---|
| MPN | BMI088 (sold as gyro die + accel die in one component; both must be soldered) |
| Vendor | Bosch Sensortec |
| Package | Dual-die: accel LGA-14 (2.0×2.5 mm) + gyro LGA-16 (3.0×4.5 mm) |
| Why chosen | Pixhawk-class standard 2nd IMU; genuinely dissimilar vendor + dissimilar architecture (separate accel + gyro dies → fault-tolerance vs single-die 6-axis); MEMS structure differs from Invensense. |
| **ArduPilot driver** | **CONFIRMED** — `libraries/AP_InertialSensor/AP_InertialSensor_BMI088.cpp`. Active hwdef use: `Pixhawk6X/hwdef.dat` lines `SPIDEV bmi088_g SPI3 DEVID1 SP3_CS2 MODE3 10*MHZ 10*MHZ` + `SPIDEV bmi088_a SPI3 DEVID2 SP3_CS1 MODE3 10*MHZ 10*MHZ`. |
| **TWO chip-selects needed** | gyro CS + accel CS — accounted for in pin budget (5 free SPI + 45 free GPIO has room) |
| JLC PCBA library | **LCSC C194919** — single MPN for the dual-die-single-package BMI088 (master correction 2026-05-21: not two separate dies in two packages; one LGA-16 4.5×3.0mm 0.5mm pitch holding accel + gyro internally with two chip selects). Confirmed via easyeda2kicad pull → `hardware/kicad/novapcb/lib/bmi088.kicad_sym` + footprint `LGA-16_L4.5-W3.0-P0.50-BL`. JLC stock status verified-at-R2-checkout. |
| Voltage | 2.4–3.6V (compatible with 3.3V) |
| Interface | SPI mode 0/3 (both dies), up to 10 MHz |
| Operating temp | −40 to +85°C |
| Current | gyro ~5 mA + accel ~150 µA |
| Dissimilarity | Vendor: Bosch (distinct from TDK); architecture: independent dual-die accel+gyro (distinct from monolithic 6-axis) |

### IMU3 — LSM6DSV16X (CHANGED from LSM6DSO — driver-confirmed)

| Field | Value |
|---|---|
| MPN | LSM6DSV16X |
| Vendor | STMicroelectronics |
| Package | LGA-14, 2.5 × 3.0 mm |
| Why chosen | Preserves 3-vendor dissimilarity (TDK + Bosch + STM). LSM6DSV is the variant **ArduPilot has a driver for** — LSM6DSO does NOT have a driver (verified). DSV adds HAODR mode for high-accuracy 8 kHz ODR + dedicated FIFO compression. |
| **ArduPilot driver** | **CONFIRMED 2026-05-21** — `libraries/AP_InertialSensor/AP_InertialSensor_LSM6DSV.cpp` + `.h`. Header declares `enum class LSM6DSV_Type { LSM6DSV16X }`. Active hwdef use: `Pixhawk6C/hwdef.dat`. Driver banner comment: *"driver for ST LSM6DSV16X IMU. Uses HAODR mode-1 for high-accuracy ODR (1000-8000 Hz) and continuous FIFO for burst reads."* |
| **LSM6DSO rejection evidence** | `grep -rln "LSM6DSO\|lsm6dso" ~/ardupilot/libraries/` returns ZERO matches. Hard-fail on Sai's #1 rule. Master adjudication: do not force LSM6DSO. |
| JLC PCBA library | **LCSC C5267406** (LSM6DSV16XTR, tape-and-reel standard orderable) — confirmed via easyeda2kicad pull → `hardware/kicad/novapcb/lib/lsm6dsv16x.kicad_sym` + footprint `LGA-14_L3.0-W2.5-P0.50-BR`. JLCPCB also lists this die under **C42388605** (separate JLC-PCBA assembly part number) — R2 reconciles which C-number is the actual JLCPCB assembly tier. Both refer to the same LSM6DSV16X silicon per master 2026-05-21. Fallback: IIM-42652 (TDK, same Invensensev3 driver, 2-vendor outcome). |
| Voltage | 1.71–3.6V (compatible with 3.3V) |
| Interface | SPI mode 0/3, MIPI I3C-compatible, up to 10 MHz |
| Operating temp | −40 to +85°C |
| Current | ~0.7 mA (active 6-axis); ~5 nA power-down |
| Dissimilarity | Vendor: STMicroelectronics (distinct from TDK + Bosch); silicon: STM MEMS proprietary process |

**Dissimilarity verdict (3 IMUs)**: genuine 3-vendor coverage with 3 distinct MEMS process families and 3 distinct AP driver code-paths. A vendor-wide fault (silicon errata, packaging issue) still leaves 2 good IMUs. ✓ master criterion met.

---

## 2. Barometers

Dual baro dissimilar; vendor-corrected per master Rule-17.

### Baro1 — DPS310 (kept from v1.0; VENDOR CORRECTED)

| Field | Value |
|---|---|
| MPN | DPS310 |
| Vendor | **Infineon Technologies** (RULE-17 CORRECTION 2026-05-21 — previously labeled Bosch in error) |
| Package | LGA-8, 2.0 × 2.5 mm |
| Why chosen | Best-in-class noise floor (~0.06 Pa RMS @ 16x oversample = 0.5 cm altitude resolution); ArduPilot-supported via the shared DPS280 driver (DPS3xx family). Carry-forward from v1.0. |
| **ArduPilot driver** | **CONFIRMED** — `libraries/AP_Baro/AP_Baro_DPS280.cpp` (covers DPS280/DPS310/DPS368/DPS422). |
| JLC PCBA library | LCSC C220330 (verify-at-R2) |
| Voltage | 1.7–3.6V |
| Interface | I2C @ 400 kHz / SPI |
| Operating temp | −40 to +85°C |
| Dissimilarity | Vendor: Infineon; sensing tech: dual-MEMS pressure cell |

### Baro2 — LPS22HB (NEW; bus: I2C1, adjudicated 2026-05-21)

| Field | Value |
|---|---|
| MPN | LPS22HBTR |
| Vendor | STMicroelectronics |
| Package | HCLGA-10, 2.0 × 2.0 mm |
| Why chosen | 2nd vendor for redundancy; ArduPilot-supported via LPS2XH driver; common, low cost, low noise (0.75 Pa RMS); independent I2C bus from Baro1. |
| **ArduPilot driver** | **CONFIRMED 2026-05-21** — `libraries/AP_Baro/AP_Baro_LPS2XH.cpp` line `#define LPS22HB_WHOAMI 0xB1` + explicit case `case LPS22HB_WHOAMI: _lps2xh_type = BARO_LPS22H;`. Header declares `BARO_LPS22H = 0` in enum. |
| JLC PCBA library | LCSC C247196 (verify-at-R2 — Extended tier expected) |
| Voltage | 1.7–3.6V |
| Interface | I2C / SPI (we use I2C @ 400 kHz on **I2C1 PB6/PB7** — I2C3_SDA=PC9 conflicts with SDMMC1_D1 on LQFP-100; only I2C1+I2C2 physically available; master adjudication 2026-05-21 preserves bus+vendor dissimilarity). Address 0x5C (SDO low). |
| Operating temp | −40 to +85°C |
| Dissimilarity | Vendor: STM (distinct from Infineon); sensing tech: piezoresistive Wheatstone bridge (vs DPS310's capacitive dual-cell — genuine architectural difference) |

**Dissimilarity verdict (2 baros)**: 2 vendors, 2 sensing principles, 2 independent I2C buses. A vendor-wide fault leaves 1 good baro. ✓ master criterion met.

---

## 3. ESD protection arrays

Pending verify-at-R2 on standoff/capacitance/JLC stock per master.

### ESD7L5.0DT5G — GPS/CRSF/Telem/I2C lines

| Field | Value |
|---|---|
| MPN | ESD7L5.0DT5G |
| Vendor | onsemi |
| Package | SOD-723 (single-line bidirectional TVS — multiple footprints used to cover all lines) |
| Standoff voltage (V_RWM) | **5.0V** — above 3.3V signal level (will NOT clamp normal signals) ✓ |
| Capacitance | typ 0.5 pF (datasheet) — negligible at 420 kbaud CRSF and 400 kHz I2C ✓ |
| Clamping voltage @ 1A | ~12V — below MCU GPIO absolute max (4.0V) is the concern; needs series limit. R2 verifies typical via clamp curve vs MCU ABS_MAX. |
| JLC PCBA library | verify-at-R2 (expected Extended tier; onsemi parts are well-stocked) |
| Acceptance | **conditional on R2 verify** of: stock status + clamp@1kV IEC 61000-4-2 below GPIO ABS_MAX |
| Lines protected | GPS_TX, GPS_RX, I2C_SCL, I2C_SDA, BUZZER, SAFETY_SW, TELEM_TX, TELEM_RX, CRSF_TX, CRSF_RX (10 lines → 10× single-line footprints OR consider USBLC6-like 4-channel arrays per cluster — R2 layout decides) |

### PESD2CAN — CAN bus ESD

| Field | Value |
|---|---|
| MPN | PESD2CAN |
| Vendor | NXP / Nexperia |
| Package | SOT-143 (3 pins, 2 lines + GND) |
| Why chosen | CAN-bus-specific TVS designed for ISO 11898-2 differential clamp; CAN_H/CAN_L threshold balanced for dominant/recessive. Pixhawk-standard. |
| Standoff voltage | 24V (above CAN signal range) |
| Capacitance | typ 25 pF (acceptable up to 1 Mbps CAN; FD-CAN 5 Mbps verify SI in CAN-bus extension sim at R6) |
| JLC PCBA library | verify-at-R2 |
| Quantity | 1 per CAN port = 2 footprints |

---

## 4. IMU heater + clean supply

### Heater control FET — AO3400

| Field | Value |
|---|---|
| MPN | AO3400A |
| Vendor | Alpha & Omega Semiconductor |
| Package | SOT-23-3 |
| Type | N-channel logic-level MOSFET |
| V_GS(th) | typ 0.9V (1.4V max) — switches fully with 3.3V GPIO |
| R_DS(on) @ 4.5V | typ 22 mΩ — negligible heat in the FET |
| I_D continuous | 5.7 A (way above heater current; we'll run ~50–200 mA) |
| JLC PCBA library | **JLC Basic** (most-used N-FET in JLC PCBA) ✓ |
| Why chosen | de facto JLC Basic-tier N-FET; cheap; well-characterized; logic-level threshold |

### Heater resistor — value + package TBD

| Field | Value |
|---|---|
| Specification | **Value + package = OUTPUT of Tier-1-sim (b) IMU-heater thermal model**. NOT guessed here. |
| Master flag 2026-05-21 | 100Ω 0805 on 5V → ~0.25 W exceeds 0.125 W 0805 rating — package undersized. |
| Expected range | likely 2512 ~1 W (or small array of 0805/1206), once sim sizes the needed thermal injection. |
| Why TBD | Heater wattage is a function of (board copper area + ambient + IMU thermal mass + setpoint). FEM thermal model (Elmer) outputs the required W; package follows. |
| Final part | locked at R6 sim conclusion, before R7 DFM check. |

### IMU clean LDO — LP5907MFX-3.3

| Field | Value |
|---|---|
| MPN | LP5907MFX-3.3 |
| Vendor | Texas Instruments |
| Package | SOT-23-5 |
| Output | 3.3V, 250 mA max |
| **Noise** | **6.5 µVRMS** (10 Hz – 100 kHz) — ultra-low-noise key spec for IMU rail |
| PSRR | 82 dB @ 1 kHz |
| Dropout | 120 mV @ 100 mA |
| JLC PCBA library | LCSC **C57769**, JLC Extended ✓ |
| Why chosen | Lowest-noise LDO in JLC library at this current; well below MEMS gyro/accel ADC noise floor; isolates IMU rail from main +3V3 digital coupling. |
| Input | from main +3V3 via ferrite bead (FB) — typical 60Ω @ 100 MHz, e.g. BLM18PG600 |

---

## 5. CAN transceivers + termination

### TJA1051TK/3

| Field | Value |
|---|---|
| MPN | TJA1051TK/3 |
| Vendor | NXP Semiconductors |
| Package | TSSOP-8 |
| Why chosen | Robust 5V-supply CAN transceiver with 3.3V-compatible logic (the `/3` variant explicitly). Pixhawk-standard; better noise immunity than 3.3V-only parts; sleep + standby modes. |
| Supply | 5V (V_CC) — derived from main +5V rail |
| Logic level | 3.3V or 5V (V_IO pin) — wired to 3.3V for our MCU |
| Bus rate | 1 Mbps classical CAN, 5 Mbps FD-CAN ✓ (matches STM32H743 FDCAN1/2 capability) |
| Operating temp | −40 to +150°C (AEC-Q100 grade option) |
| JLC PCBA library | verify-at-R2 (commonly stocked; expected Extended tier) |
| Per-port termination | **120Ω 0603 jumper-selectable** (master directive 2026-05-21): two solder pads with a 120Ω chip resistor in series with a cuttable trace. Default closed = terminate; cut = no terminate. Independent per port. |
| Quantity | **1 transceiver** (FDCAN1 only) — adjudicated 2026-05-21. FDCAN2 alternates on LQFP-100 all conflict with SPI2/SPI3/I2C1 once IMUs claim them (PB5/PB6/PB12/PB13). Pin-budget claim of "2 free FDCAN" was optimistic; LQFP-100 physical reality = 1 CAN. **2nd CAN port deferred to v2 (LQFP-144 H743ZG repackage)**. CAN is future-proofing — Nova drone uses zero CAN today, so 1 port already provides headroom. Same package decision as MatekH743 (1 CAN, LQFP-100). |

---

## 6. Power-input redundancy

### LM74700-Q1 ideal-diode controller

| Field | Value |
|---|---|
| MPN | LM74700-Q1 (or LM74700, automotive vs commercial grade) |
| Vendor | Texas Instruments |
| Package | SOT-23-6 (or MSOP-8 variant — datasheet has both) |
| Function | Drives an external N-channel back-to-back MOSFET pair as a near-zero-drop diode (forward drop ~20 mV at typical currents) |
| Supply range | 3.2 – 65V (covers 4S–6S LiPo VBAT) |
| Reverse-bias blocking | 65V max |
| JLC PCBA library | verify-at-R2 (TI auto parts usually JLC Extended) |
| Why chosen | Lossless diode-OR-ing of two BEC inputs; no Schottky losses; auto-switchover when one input falls. Validated by Tier-1-sim (a) power-failover transient. |
| Companion FET | external dual N-FET (one per controller, two per board). Part TBD at schematic phase — common-drain Vth-compatible part, e.g., FDS6680A or similar. R2 footprint phase picks final FET MPN. |
| Quantity | 2 (one per power input) |

### 2nd JST-GH 6P connector

| Field | Value |
|---|---|
| Connector | JST-GH 6-pin (matches J4 on v1.0 — Mauch-style monitored-power) |
| Pinout | VBAT, GND, VCC_5V, I_sense, V_sense, ID (or per the Pixhawk monitored-power schema in `docs/INTERFACE_CONTRACT.md`) |
| Why this style | Master directive 2026-05-21 — consistent with J4; supports a 2nd full monitored BEC, not a bare 5V splice. NOT a bare 2-pin pad. |
| Footprint | existing JST-GH 6P footprint from v1.0 library — reuse |

---

## 7. Acceptance gate checklist

Before this doc passes R1, master verifies:

- [ ] **IMU drivers verified by file:line citation** (✓ done above for all 3 IMUs)
- [ ] **Baro drivers verified by file:line citation** (✓ done above for both)
- [ ] **Dissimilarity argument explicit** (3 vendors / 3 process families for IMUs; 2 vendors / 2 sensing techs for baros)
- [ ] **All non-sensor parts have JLC library status flagged** (verify-at-R2 where uncertain)
- [ ] **Heater resistor value/package marked TBD-from-sim** (not guessed)
- [ ] **DPS310 vendor corrected to Infineon** (Rule-17)
- [ ] **CAN termination per-port jumper-selectable** explicitly called out
- [ ] **2nd power input = JST-GH 6P mirror of J4** explicitly called out
- [ ] **ESD7L5.0DT5G acceptance conditional on R2 verify** (standoff/cap/JLC) — not pre-locked

When master signs off, branch `hw/v1.1-respin` begins R1 schematic edit. The schematic phase touches only the LOCKED parts; heater resistor pad placeholder reserves area (no value committed until R6 sim).

---

**Authorized**: Sai 2026-05-21 (autonomous execution via master). Master gate: parts-review review BEFORE schematic edit. Schematic + ERC pinged for R1 gate.
