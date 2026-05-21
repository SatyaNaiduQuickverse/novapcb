"""
novapcb Phase 3d — barometer sheet (dual: DPS310 on I²C2 @ 0x76, LPS22HB on I²C1 @ 0x5C).

## Authority for this sheet

  - `firmware/hwdef-novapcb/hwdef.dat` — AUTHORITATIVE for the I²C pin map
    (per the Phase 3 hwdef-cited discipline). Lines cited inline below.
  - Infineon DPS310 datasheet (v01.02) — AUTHORITATIVE for chip pinout,
    supply pins, decoupling, I²C-mode tie-off (CSB high for I²C; SDO low
    for address 0x76). Pinout sourced via web research from Infineon's
    published datasheet (PDF parsing failed locally; pin map matches
    Bosch BMP280 LGA-8 family exactly — same package + identical pin
    assignments, confirmed by cross-reference with KiCad's BMP280 symbol).
  - Phase 2b lock: BARO DPS310 I2C:0:0x76, SDO tied GND (per
    `hwdef.dat:241-242`).

## hwdef.dat-cited authoritative pin map

| Net | MCU pin | Source line |
|---|---|---|
| I2C2_SCL | PB10 | 64: `PB10 I2C2_SCL I2C2` |
| I2C2_SDA | PB11 | 65: `PB11 I2C2_SDA I2C2` |
| I2C_ORDER | I2C2 first (bus index 0) | 57: `I2C_ORDER I2C2 I2C1` |
| BARO line | `BARO DPS310 I2C:0:0x76` | 242 |
| HAL_I2C_INTERNAL_MASK | 0 (both buses external) | 224 |

## DPS310 LGA-8 pinout (Infineon datasheet)

Same package + identical pin assignments as Bosch BMP280 (LGA-8 2×2.5 mm,
0.65 mm pitch, clockwise pin numbering). Using `Sensor_Pressure:BMP280`
KiCad symbol with `value="DPS310"` overrides — gives netlist-correct pin
NUMBERS (1-8 per datasheet) AND ERC-correct electrical pin TYPES
(`VDD/VDDIO` = power_in, `GND` = passive/power, `SDI/SDO` = bidirectional,
`SCK/CSB` = input). This addresses the master 3d refinement of 3c's
Conn_01xN-rename approach (connector pins are all passive → ERC can't
catch power-in / bidirectional rule violations).

| Pin | Name | Function | This-sheet wiring |
|---|---|---|---|
| 1 | GND | Ground | GND |
| 2 | CSB | Chip select (active low; high = I²C mode) | +3V3 (tied HIGH selects I²C mode per Infineon datasheet §6.2) |
| 3 | SDI | Serial data in (I²C: SDA) | I2C2_SDA |
| 4 | SCK | Serial clock (I²C: SCL) | I2C2_SCL |
| 5 | SDO | Serial data out / I²C address select (low=0x76, high=0x77) | GND (selects address 0x76 per `hwdef.dat:242` BARO line) |
| 6 | VDDIO | Digital I/O supply | +3V3 |
| 7 | GND | Ground | GND |
| 8 | VDD | Analog supply | +3V3 |

Phase 4 carry-forward: Infineon-DPS310-exact KiCad symbol + footprint
(currently using Bosch BMP280 KiCad symbol — pinout-identical but the
silkscreen will show "BMP280" in the auto-render; value override gives
the netlist + BOM correct name; Phase 4 production should ship a
proper DPS310-named symbol).

## I²C2 pull-up ownership

I²C buses need pull-up resistors to VDD (typically 4.7 kΩ for short
buses, 2.2 kΩ for longer or capacitively-loaded buses).

I²C2 carries:
  - DPS310 baro (on-board, this sheet) at 0x76
  - Possibly the external GPS+mag connector (Phase 3e), if Phase 4 layout
    wires the JST-GH 10P I²C lines to I²C2 rather than I²C1

**Decision: I²C2 pull-ups live on THIS sheet** (`baro_3d.py`), 4.7 kΩ each
on SDA + SCL to +3V3. Reasoning:
  - The DPS310 is the always-present on-board slave on I²C2 — pull-ups
    co-located with the always-present node is the cleanest topology.
  - Phase 3e (GPS+mag connector) will explicitly NOT add a second pair
    of I²C2 pull-ups — doubling pull-ups halves the effective resistance
    and over-drives the bus.
  - If Phase 4 layout decides to wire the external GPS+mag to I²C1
    instead (so I²C2 stays internal-only), I²C1 pull-ups land in Phase 3e
    with that connector. I²C2 pull-ups here are robust to either layout
    choice — they always cover the DPS310, and they coincidentally cover
    any external I²C2 slave too.
  - Phase 6d sim validates pull-up value adequacy for the actual bus
    capacitance (trace length + slave count); 4.7 kΩ is the standard
    starting point.

This is the master 3d.5 judgement call — flagged here for visibility.
"""

import skidl
from skidl import Part, Net

from sheets.common import (
    setup, n, FP_R_0402, FP_C_0402,
)
from sheets.mcu_3a import mcu

setup()


# ---- shared nets ----
GND      = n("GND")
P3V3     = n("+3V3")
I2C2_SCL = n("I2C2_SCL")
I2C2_SDA = n("I2C2_SDA")


# ---- MCU side: wire the I2C2 pins to the shared I2C2 nets ----
# hwdef.dat:64-65 — I2C2 pin assignments. Tying mcu PB10/PB11 to the shared
# nets HERE in 3d connects the MCU's I2C2 peripheral to the on-board baro +
# any external I2C2 slave from sheet 3e.
I2C2_SCL += mcu["PB10"]
I2C2_SDA += mcu["PB11"]


# ---- Barometer: DPS310 (LGA-8) ----
# Sensor_Pressure:BMP280 KiCad symbol — pinout-identical to DPS310 (both
# Bosch-/Infineon-family LGA-8 2x2.5 0.65mm pitch). Value override gives
# the netlist + BOM the correct "DPS310" name; Phase 4 ships a proper
# DPS310-named symbol (Phase 2.5 footprint inventory already noted that
# the Bosch_LGA-8 footprint is the geom-match used for fit check).
# Footprint inherited from the symbol's default
# (Package_LGA:Bosch_LGA-8_2x2.5mm_P0.65mm_ClockwisePinNumbering).
baro = Part(
    "Sensor_Pressure", "BMP280",
    footprint="Package_LGA:Bosch_LGA-8_2x2.5mm_P0.65mm_ClockwisePinNumbering",
    value="DPS310",
)
baro.ref = "U4"


# ---- pin connections (per DPS310 datasheet + Phase 2b I²C 0x76 lock) ----
# Pin 1 GND, Pin 7 GND (ground pins).
GND += baro[1]
GND += baro[7]

# Pin 2 CSB tied HIGH (to VDDIO/+3V3) → selects I²C mode per datasheet §6.2.
P3V3 += baro[2]

# Pin 3 SDI = I²C SDA (data line).
I2C2_SDA += baro[3]

# Pin 4 SCK = I²C SCL (clock line).
I2C2_SCL += baro[4]

# Pin 5 SDO tied LOW (to GND) → selects I²C address 0x76 per hwdef.dat:242
# BARO line. Phase 2b lock; SDO-high would select 0x77 (alternate address).
GND += baro[5]

# Pin 6 VDDIO = digital I/O supply (tied to VDD per typical operating circuit).
P3V3 += baro[6]

# Pin 8 VDD = analog supply.
P3V3 += baro[8]


# ---- decoupling caps (per DPS310 datasheet typical operating circuit) ----
# 100 nF X7R 0402 on VDD pin (close placement).
c_vdd = Part("Device", "C", value="100nF", footprint=FP_C_0402)
c_vdd.ref = "C51"
P3V3 += c_vdd[1]
GND  += c_vdd[2]

# 100 nF X7R 0402 on VDDIO pin (close placement).
c_vddio = Part("Device", "C", value="100nF", footprint=FP_C_0402)
c_vddio.ref = "C52"
P3V3 += c_vddio[1]
GND  += c_vddio[2]


# ---- I²C2 pull-up resistors (this sheet owns them per the docstring rationale) ----
# 4.7 kΩ to +3V3 on each of SDA + SCL. Standard starting value for short
# I²C buses with ≤4 slaves. Phase 6d sim validates against actual bus
# capacitance (trace length + slave count); 2.2 kΩ swap-in if needed.
r_sda = Part("Device", "R", value="4.7k", footprint=FP_R_0402)
r_sda.ref = "R11"
P3V3     += r_sda[1]
I2C2_SDA += r_sda[2]

r_scl = Part("Device", "R", value="4.7k", footprint=FP_R_0402)
r_scl.ref = "R12"
P3V3     += r_scl[1]
I2C2_SCL += r_scl[2]


# ====================================================================
# v1.1 redundancy re-spin — IMU dual-baro: 2nd barometer on I²C1.
# ====================================================================
# Per docs/RESPIN_SCOPE.md + RESPIN_PARTS_REVIEW.md (Sai/master adjudicated
# 2026-05-21): a second, vendor-dissimilar barometer on an independent I²C
# bus for redundancy.
#
#   - Baro2: LPS22HB (STMicroelectronics, HCLGA-10 2×2mm 0.5mm pitch)
#   - Bus: I²C1 (PB6/PB7) — physical-package fact: I²C3_SDA = PC9 is locked
#     to SDMMC1_D1 (Phase 2h, INTERFACE_CONTRACT.md microSD section);
#     I²C4 alternates blocked by PWM/non-LQFP-100 pins. On LQFP-100 only
#     I²C1 + I²C2 are physically available. Master 2026-05-21 adjudication.
#   - Address: 0x5C (SA0 tied LOW per datasheet)
#   - ArduPilot driver: AP_Baro_LPS2XH.cpp — WHOAMI 0xB1 case explicit
#     (libraries/AP_Baro/AP_Baro_LPS2XH.cpp line for LPS22HB_WHOAMI).
#
# Pull-ups for I²C1 already land in gps_mag_3e.py (R21/R22) — DO NOT add
# more pull-ups here (doubling halves effective resistance and over-drives
# the bus, exactly the rationale 3d's docstring already warns about).
#
# ## LPS22HB pinout (per ST DS11211 + KiCad Sensor_Pressure:LPS22HB symbol,
#    which extends LPS25HB with identical pinout):
#
# | Pin | Name | Function | Wiring |
# |---|---|---|---|
# | 1 | Vdd_IO | Digital I/O supply | +3V3 (tied to VDD per datasheet typical I²C circuit) |
# | 2 | SCL | I²C clock | I2C1_SCL |
# | 3 | GND | Ground | GND |
# | 4 | SDA | I²C data | I2C1_SDA |
# | 5 | SA0 | I²C address select (low=0x5C, high=0x5D) | GND (selects 0x5C) |
# | 6 | ~CS | Chip select (high=I²C, low=SPI) | +3V3 (selects I²C mode) |
# | 7 | INT_DRDY | Data-ready interrupt output | testpoint (DRDY not assigned in hwdef v1.0; future hwdef revision can wire) |
# | 8 | GND | Ground | GND |
# | 9 | GND | Ground | GND |
# | 10 | VDD | Main supply | +3V3 |
#
# Decoupling per ST datasheet typical operating circuit:
#   - 100 nF X7R on VDD pin (pin 10)
#   - 100 nF X7R on Vdd_IO pin (pin 1)
#
# Footprint: HLGA-10 2×2mm 0.5mm pitch (override of LPS25HB's default
# 2.5×2.5 0.6mm footprint — LPS22HB is the smaller variant).

# Wire I²C1 nets on the MCU side IF NOT ALREADY DONE by another sheet.
# gps_mag_3e.py already wires PB6/PB7 to I2C1_SCL/I2C1_SDA — but the n()
# singleton fetcher means we just need the same net names here and the
# electrical connection holds; do NOT re-bind PB6/PB7 to mcu (Part-side
# pins can be net-bound from only one place; SKiDL handles multi-bind but
# best practice is single-bind per pin).
I2C1_SCL = n("I2C1_SCL")
I2C1_SDA = n("I2C1_SDA")

baro2 = Part(
    "Sensor_Pressure", "LPS22HB",
    footprint="Package_LGA:ST_HLGA-10_2x2mm_P0.5mm_LayoutBorder3x2y",
    value="LPS22HB",
)
baro2.ref = "U7"   # U6 = eFuse (power_3b); U7 next free in U-series

# Power + ground.
P3V3 += baro2[10]   # VDD
P3V3 += baro2[1]    # Vdd_IO (tied to VDD per ST typical I²C circuit)
GND  += baro2[3]    # GND
GND  += baro2[8]    # GND
GND  += baro2[9]    # GND

# I²C lines.
I2C1_SCL += baro2[2]   # SCL
I2C1_SDA += baro2[4]   # SDA

# Mode + address selects.
GND  += baro2[5]    # SA0 = GND → I²C address 0x5C
P3V3 += baro2[6]    # ~CS high → I²C mode (NOT SPI)

# DRDY interrupt — testpoint only (no MCU pin assigned in hwdef v1.0;
# future hwdef revision can route to a free GPIO for hardware DRDY).
LPS22HB_INT_TP = Net("LPS22HB_INT_TP")
LPS22HB_INT_TP += baro2[7]

# Decoupling caps per ST DS11211 typical operating circuit.
c_vdd_b2 = Part("Device", "C", value="100nF", footprint=FP_C_0402)
c_vdd_b2.ref = "C71"
P3V3 += c_vdd_b2[1]
GND  += c_vdd_b2[2]

c_vddio_b2 = Part("Device", "C", value="100nF", footprint=FP_C_0402)
c_vddio_b2.ref = "C72"
P3V3 += c_vddio_b2[1]
GND  += c_vddio_b2[2]
