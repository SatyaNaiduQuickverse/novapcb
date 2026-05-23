"""
novapcb Phase 3c — IMU sheet (ICM-42688-P on SPI1, polled mode).

Wires the ICM-42688-P IMU's SPI bus + power + decoupling. The MCU side of
the SPI bus (PA5/PA6/PD7/PC15) is the same Part instance imported from
sheets.mcu_3a — this sheet adds the SPI bus connections + the IMU itself.

## Authority for this sheet

  - `firmware/hwdef-novapcb/hwdef.dat` — AUTHORITATIVE for the SPI pin map
    (per the Phase 3 hwdef-authoritative discipline). Cited inline below.
  - TDK InvenSense ICM-42688-P datasheet (ds-000347 v1.6) — AUTHORITATIVE
    for the chip's pinout, supply pins, decoupling, reserved/NC pin
    handling. Sourced via web research (cited in PR body).
  - `docs/OPEN_QUESTIONS.md phase2a-1` — DRDY pin deferred (Pixhawk6X uses
    PA10 which conflicts with our USART1_RX); current state is polled mode.
    Per hwdef.dat:234, `IMU Invensensev3 SPI:icm42688 ROTATION_YAW_180` —
    no DRDY pin assigned.

## hwdef.dat-cited authoritative pin map

| Net | Pin | hwdef.dat line |
|---|---|---|
| SPI1_SCK | PA5 (MCU) | 36: `PA5 SPI1_SCK SPI1` |
| SPI1_MISO | PA6 (MCU) | 37: `PA6 SPI1_MISO SPI1` |
| SPI1_MOSI | PD7 (MCU) | 38: `PD7 SPI1_MOSI SPI1` |
| IMU1_CS | PC15 (MCU) | 39: `PC15 IMU1_CS CS` |
| SPIDEV | `icm42688 SPI1 DEVID1 IMU1_CS MODE3 2*MHZ 16*MHZ` | 203 |
| DMA isolation | `DMA_NOSHARE SPI1*` | 207 |

## ICM-42688-P pinout (LGA-14 2.5×3×0.91mm, 0.5mm pitch)

Per TDK ICM-42688-P datasheet ds-000347 v1.6 §10 (Pin Description) +
Figure 6 (LGA-14 Pin Out). Used here via a generic `Conn_01x14` symbol
with pins renamed per the datasheet (no exact `ICM-42688-P` symbol exists
in KiCad 9 standard libs — searched `Sensor_Motion.kicad_sym`, only
ICM-20602, ICM-20948, MPU-9250 present; per Phase 3c contract decision
fork `imu-symbol`, master pre_recommendation was 'generic LGA-14 with
correct pin mapping per the TDK datasheet'). Phase 4 production layout
needs a TDK-datasheet-exact KiCad symbol + footprint drawn (Phase 4
carry-forward per Phase 2.5 P1.5).

| Pin | Name | Function | This-sheet wiring |
|---|---|---|---|
| 1 | INT1 | Interrupt output (data-ready candidate) | testpoint net `IMU_INT1_TP` (DRDY deferred per OPEN_QUESTIONS phase2a-1) |
| 2 | RESV | Reserved | NC per datasheet §10 |
| 3 | RESV | Reserved | NC per datasheet §10 |
| 4 | GND | Ground | GND |
| 5 | RESV | Reserved | NC per datasheet §10 |
| 6 | RESV | Reserved | NC per datasheet §10 |
| 7 | AUX_DA | Auxiliary I²C SDA (OIS bridge) | NC per datasheet §10 (SPI-only operation, no aux I²C) |
| 8 | VDDIO | Digital I/O supply | +3V3 (tied to VDD per datasheet §11.1 typical SPI operating circuit) |
| 9 | SDO/AD0 | SPI MISO | SPI1_MISO |
| 10 | ~CS | SPI chip select (active low) | IMU1_CS |
| 11 | SCLK | SPI clock | SPI1_SCK |
| 12 | SDI | SPI MOSI | SPI1_MOSI |
| 13 | RESV | Reserved | NC per datasheet §10 |
| 14 | VDD | Main supply | +3V3 |

Decoupling per ICM-42688-P datasheet §11 (Typical Operating Circuit):
  - 100 nF X7R on VDD pin (close placement, ≤ 2 mm trace)
  - 100 nF X7R on VDDIO pin (close placement)
  - 2.2 µF X5R bulk on VDD (parallel with the 100 nF)

## What this sheet does NOT do

  - Phase 4 PCB layout (vibration-isolated placement, IMU thermal venting)
  - Phase 6c sim (SPI signal integrity at 16 MHz)
  - Phase 9 bench (gyro/accel calibration, self-test)
  - Custom KiCad symbol + TDK-exact footprint for ICM-42688-P (deferred to
    Phase 4 per Phase 2.5 P1.5 carry-forward — generic LGA-14 footprint
    used for Phase 2.5 fit check, generic Conn_01x14 symbol used here)
"""

import skidl
from skidl import Part, Net

from sheets.common import (
    setup, n, FP_R_0402, FP_C_0402, FP_C_0805,
)
from sheets.mcu_3a import mcu

setup()


# ---- shared nets ----
GND       = n("GND")
P3V3      = n("+3V3")
# +3V3_IMU is the FB2-isolated rail dedicated to the IMU island (sourced
# by U13 LP5907 LDO in power_3b.py). Defined early so U3 (this sheet)
# can use it; U8/U9 (later in this file) also use it.
# Corrective amend 2026-05-23 (master sign-off): U3 (ICM-42688-P) moved
# from P3V3 to P3V3_IMU per contracts §D. Original assignment was a
# netlist oversight — schematic intent has always been "all IMUs on the
# filtered rail" but U3 was on P3V3 directly. EMI isolation consistency
# fix; no design-intent change.
P3V3_IMU  = n("+3V3_IMU")
SPI1_SCK  = n("SPI1_SCK")
SPI1_MISO = n("SPI1_MISO")
SPI1_MOSI = n("SPI1_MOSI")
IMU1_CS   = n("IMU1_CS")


# ---- MCU side: wire the four SPI1 pins to the shared SPI nets ----
# hwdef.dat:36-39 — SPI1 pin assignments. By tying mcu's PA5/PA6/PD7/PC15
# pins to the shared nets HERE in 3c, the IMU on the other side of those
# nets is electrically connected to the MCU.
SPI1_SCK  += mcu["PA5"]
SPI1_MISO += mcu["PA6"]
SPI1_MOSI += mcu["PA7"]   # was PD7 (pin 88, N); re-muxed to PA7 (pin 31, S) per master 2026-05-22
IMU1_CS   += mcu["PC15"]


# ---- IMU: ICM-42688-P (LGA-14) ----
# Generic Conn_01x14 symbol with pins renamed per the ICM-42688-P datasheet.
# Production footprint: see Phase 4 carry-forward note above. Phase 2.5
# placement-fit used the generic `Package_LGA:LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y`
# footprint; that's also used here so the netlist's reference matches.
imu = Part(
    "Connector_Generic", "Conn_01x14",
    footprint="Package_LGA:LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y",
    value="ICM-42688-P",
)
imu.ref = "U3"

# Pin renames per TDK datasheet §10 (Pin Description) + Figure 6.
# After rename, schematic readability + netlist pin labels reflect the actual
# chip pinout. Pin NUMBERS (1-14) are the load-bearing facts for the netlist
# — they match the ICM-42688-P LGA-14 datasheet pin numbering exactly.
imu_pin_names = {
    1:  "INT1",
    2:  "RESV2",
    3:  "RESV3",
    4:  "GND",
    5:  "RESV5",
    6:  "RESV6",
    7:  "AUX_DA",
    8:  "VDDIO",
    9:  "SDO",
    10: "~{CS}",
    11: "SCLK",
    12: "SDI",
    13: "RESV13",
    14: "VDD",
}
for pin_num, pin_name in imu_pin_names.items():
    imu[pin_num].name = pin_name


# ---- SPI bus connections (IMU side) ----
SPI1_MISO += imu[9]    # SDO = MISO
IMU1_CS   += imu[10]   # ~CS
SPI1_SCK  += imu[11]   # SCLK
SPI1_MOSI += imu[12]   # SDI = MOSI


# ---- power + ground connections ----
# Corrective amend 2026-05-23: VDD/VDDIO moved P3V3 → P3V3_IMU per
# contracts §D + master sign-off. All 3 IMUs on FB2-isolated rail for
# clean EMI environment.
P3V3_IMU += imu[14]    # VDD (main supply)
P3V3_IMU += imu[8]     # VDDIO (tied to VDD per datasheet §11.1 SPI-only circuit)
GND  += imu[4]         # GND


# ---- reserved / NC pins (per datasheet §10 — leave unconnected) ----
# Pins 2, 3, 5, 6, 7, 13 are reserved (or AUX_DA for OIS, unused here).
# Datasheet §10: "RESV pins should be left disconnected (NC)."
# Pin 7 AUX_DA: "Auxiliary I2C SDA; leave NC if OIS bridge not used."
# SKiDL 2.2.3 has no module-level NC sentinel; explicit-NC is "don't connect."
# ERC will emit "unconnected pin" warnings for pins 2/3/5/6/7/13 — these are
# EXPECTED + correct per the ICM-42688-P datasheet, not real defects.


# ---- INT1 / DRDY handling (per OPEN_QUESTIONS phase2a-1 deferral) ----
# DRDY pin assignment is open per `docs/OPEN_QUESTIONS.md phase2a-1`
# (Pixhawk6X uses PA10 for SPI-IMU DRDY which conflicts with our USART1_RX).
# `hwdef.dat:234` runs the IMU in polled mode (no DRDY pin assigned).
# Capture INT1 as a testpoint net so a future v1.x can route it to whatever
# pin Phase 2a-rev2 picks; for now it floats on the IMU side + has a
# layer-1 pad on the PCB (Phase 4 layout).
IMU_INT1_TP = Net("IMU_INT1_TP")
IMU_INT1_TP += imu[1]


# ---- decoupling caps (per ICM-42688-P datasheet §11 Typical Operating Circuit) ----
# All U3 decap on P3V3_IMU (per 2026-05-23 corrective amend — was P3V3).
# 100 nF X7R on VDD (close to pin 14)
c_vdd_100n = Part("Device", "C", value="100nF", footprint=FP_C_0402)
c_vdd_100n.ref = "C41"
P3V3_IMU += c_vdd_100n[1]
GND  += c_vdd_100n[2]

# 100 nF X7R on VDDIO (close to pin 8)
c_vddio_100n = Part("Device", "C", value="100nF", footprint=FP_C_0402)
c_vddio_100n.ref = "C42"
P3V3_IMU += c_vddio_100n[1]
GND  += c_vddio_100n[2]

# 2.2 µF X5R bulk on VDD (parallel with C41)
c_vdd_bulk = Part("Device", "C", value="2.2uF", footprint=FP_C_0402)
c_vdd_bulk.ref = "C43"
P3V3_IMU += c_vdd_bulk[1]
GND  += c_vdd_bulk[2]


# ====================================================================
# v1.1 redundancy re-spin — IMU2 (BMI088) on SPI2 + IMU3 (LSM6DSV16X) on SPI3
# ====================================================================
# Per docs/RESPIN_SCOPE.md + RESPIN_PARTS_REVIEW.md (Sai/master adjudicated
# 2026-05-21): triple-IMU dissimilar with 3 vendors:
#   IMU1 = ICM-42688-P (TDK) — above, on SPI1 (unchanged)
#   IMU2 = BMI088 (Bosch) — single LGA-16 package containing accel + gyro
#          dies, on SPI2 with two chip selects (one per die)
#   IMU3 = LSM6DSV16X (STMicroelectronics) — LGA-14, on SPI3
#
# Pin maps below are AUTHORITATIVE per easyeda2kicad-pulled symbols
# (master directive 2026-05-21: verified-symbol path over training data):
#   - BMI088: LCSC C194919 → hardware/kicad/novapcb/lib/bmi088.kicad_sym
#     LGA-16 4.5×3.0mm 0.5mm pitch
#   - LSM6DSV16XTR: LCSC C5267406 → lib/lsm6dsv16x.kicad_sym
#     LGA-14 3.0×2.5mm 0.5mm pitch
#
# Both IMUs run from +3V3_IMU (LP5907 ultra-low-noise rail per power_3b.py
# v1.1 additions), NOT main +3V3, for noise isolation from digital coupling.
#
# Pin-budget reality (hwdef.dat 2026-05-21 + master pin-conflict adjudication):
#   - SPI2 SCK/MISO/MOSI = PB13/PB14/PB15 (hwdef.dat:80-82, locked)
#   - SPI3 SCK/MISO/MOSI = PB3/PB4/PB5 (hwdef.dat:85-87, locked)
#   - Chip selects (repurposed from unused v1.0 hwdef CS reservations):
#       IMU2 ACC_CS (BMI088 pin 5 CSB2) = PB12 (was MAX7456_CS — no MAX7456 in BOM)
#       IMU2 GYR_CS (BMI088 pin 14 CSB1) = PD4 (was EXT_CS1 — generic ext-CS)
#       IMU3 CS (LSM6DSV16X pin 12)     = PE2 (was EXT_CS2 — generic ext-CS)
#   - INT pins (free GPIOs per hwdef.dat survey):
#       IMU2 ACC_INT1 (BMI088 pin 16) = PE5 (free; EXTI capable)
#       IMU2 GYR_INT3 (BMI088 pin 12) = PE6 (free; EXTI capable)
#       IMU3 INT1     (LSM6DSV16X pin 4) = PE11 (free)
#     Other INTs (ACC_INT2 pin 1, GYR_INT4 pin 13, IMU3 INT2 pin 9) are
#     captured as testpoint nets — DRDY-via-INT is a polled-or-event-driven
#     ArduPilot choice handled in firmware; for now hwdef polls all three.
#
# hwdef.dat revision (separate task, NOT in R1 scope) will add:
#   PB12 IMU2_ACC_CS CS
#   PD4  IMU2_GYR_CS CS
#   PE2  IMU3_CS CS
#   SPIDEV bmi088_a SPI2 DEVID1 IMU2_ACC_CS MODE3 10*MHZ 10*MHZ
#   SPIDEV bmi088_g SPI2 DEVID2 IMU2_GYR_CS MODE3 10*MHZ 10*MHZ
#   SPIDEV lsm6dsv16x SPI3 DEVID1 IMU3_CS MODE3 2*MHZ 10*MHZ
#   IMU BMI088 SPI:bmi088_a SPI:bmi088_g ROTATION_NONE  (final rotation TBD)
#   IMU LSM6DSV SPI:lsm6dsv16x ROTATION_NONE


# Shared rails for IMU2+IMU3 — both on the clean +3V3_IMU rail.
# (P3V3_IMU now defined at top of file alongside P3V3 — see 2026-05-23
# amend that moved U3 from P3V3 to P3V3_IMU.)

# SPI2 nets for IMU2 (BMI088).
SPI2_SCK   = n("SPI2_SCK")
SPI2_MISO  = n("SPI2_MISO")
SPI2_MOSI  = n("SPI2_MOSI")
IMU2_ACC_CS = n("IMU2_ACC_CS")
IMU2_GYR_CS = n("IMU2_GYR_CS")

# SPI3 nets for IMU3 (LSM6DSV16X).
SPI3_SCK   = n("SPI3_SCK")
SPI3_MISO  = n("SPI3_MISO")
SPI3_MOSI  = n("SPI3_MOSI")
IMU3_CS    = n("IMU3_CS")

# MCU side wiring — SPI2 + SPI3 pins per hwdef.dat:80-87.
SPI2_SCK    += mcu["PB13"]
SPI2_MISO   += mcu["PB14"]
SPI2_MOSI   += mcu["PB15"]
IMU2_ACC_CS += mcu["PB12"]   # repurposed from MAX7456_CS (no MAX7456 in v1.0 BOM)
IMU2_GYR_CS += mcu["PD4"]    # repurposed from EXT_CS1 (was unused)

SPI3_SCK    += mcu["PB3"]
SPI3_MISO   += mcu["PB4"]
SPI3_MOSI   += mcu["PB5"]
IMU3_CS     += mcu["PE2"]    # repurposed from EXT_CS2 (was unused)

# IMU INT nets (free GPIOs).
IMU2_ACC_INT1 = n("IMU2_ACC_INT1")
IMU2_GYR_INT3 = n("IMU2_GYR_INT3")
IMU3_INT1     = n("IMU3_INT1")
IMU2_ACC_INT1 += mcu["PE5"]
IMU2_GYR_INT3 += mcu["PE6"]
IMU3_INT1     += mcu["PE11"]


# --------------------------------------------------------------------
# IMU2: BMI088 (single LGA-16, accel die + gyro die)
# --------------------------------------------------------------------
# Symbol: bmi088:BMI088 (easyeda2kicad C194919). Pin map verified at
# 2026-05-21 against ST .kicad_sym output — see comment block below.
#
# BMI088 LGA-16 pinout — AUTHORITATIVE per Bosch DS001 §7.1 Table 14 (page 52)
# cross-checked against the easyeda2kicad-pulled bmi088.kicad_sym symbol (C194919).
# Datasheet also confirms via Figure 8 SPI connection diagram (page 53):
#   CSB_ACCEL → pin 14 (CSB1) ; CSB_GYRO → pin 5 (CSB2)
# This corrects an earlier (uncommitted) swap: pin 5 is GYRO CS, pin 14 is ACCEL CS.
#
#   pin 1: INT2  — accel INT2 (testpoint)
#   pin 2: NC    — leave unconnected per datasheet
#   pin 3: VDD   — analog+digital supply → +3V3_IMU
#   pin 4: GNDA  — analog ground → GND
#   pin 5: CSB2  — **GYRO** chip select (active low) → IMU2_GYR_CS
#   pin 6: GNDIO — digital ground → GND
#   pin 7: PS    — protocol select; LOW = SPI, HIGH = I2C → GND (SPI mode)
#   pin 8: SCL/SCK — SPI clock shared → SPI2_SCK
#   pin 9: SDA/SDI — SPI MOSI shared → SPI2_MOSI
#   pin 10: SDO2 — **GYRO** SPI MISO → SPI2_MISO (tied with SDO1 — CS multiplex)
#   pin 11: VDDIO — digital I/O supply → +3V3_IMU
#   pin 12: INT3 — gyro INT3 → IMU2_GYR_INT3
#   pin 13: INT4 — gyro INT4 (testpoint; DRDY candidate)
#   pin 14: CSB1 — **ACCEL** chip select (active low) → IMU2_ACC_CS
#   pin 15: SDO1 — **ACCEL** SPI MISO → SPI2_MISO (tied with SDO2)
#   pin 16: INT1 — accel INT1 → IMU2_ACC_INT1

imu2 = Part(
    "bmi088", "BMI088",
    footprint="bmi088:LGA-16_L4.5-W3.0-P0.50-BL",
    value="BMI088",
)
imu2.ref = "U8"

# Power + ground.
P3V3_IMU += imu2[3]   # VDD (accel)
P3V3_IMU += imu2[11]  # VDDIO
GND      += imu2[4]   # GNDA (accel)
GND      += imu2[6]   # GNDIO

# Protocol select: tie LOW for SPI 4-wire mode.
GND += imu2[7]

# SPI bus (shared SCK + MOSI; both MISO lines tied to same MCU MISO —
# CS multiplexes which die drives the line at any moment, standard
# 4-wire SPI practice).
SPI2_SCK  += imu2[8]    # SCL/SCK
SPI2_MOSI += imu2[9]    # SDA/SDI
SPI2_MISO += imu2[10]   # SDO2 (accel MISO)
SPI2_MISO += imu2[15]   # SDO1 (gyro MISO) — tied with pin 10

# Chip selects — per Bosch DS001 Table 14 + Figure 8:
#   pin 5  = CSB2 = GYRO chip select
#   pin 14 = CSB1 = ACCEL chip select
# (Names CSB1/CSB2 follow the same numeric ordering as SDO1/SDO2 — both
# tagged "1" belong to the ACCEL die, both tagged "2" belong to the GYRO die.
# Confirmed via datasheet Figure 8 SPI connection diagram.)
IMU2_GYR_CS += imu2[5]    # CSB2 = gyro CS
IMU2_ACC_CS += imu2[14]   # CSB1 = accel CS

# Interrupts.
IMU2_ACC_INT1 += imu2[16]   # accel INT1
IMU2_GYR_INT3 += imu2[12]   # gyro INT3

# Testpoint INTs (ACC_INT2, GYR_INT4) — captured for future hwdef revision.
BMI088_ACC_INT2_TP = Net("BMI088_ACC_INT2_TP")
BMI088_GYR_INT4_TP = Net("BMI088_GYR_INT4_TP")
BMI088_ACC_INT2_TP += imu2[1]    # accel INT2
BMI088_GYR_INT4_TP += imu2[13]   # gyro INT4 (DRDY candidate per Bosch DS001)

# Pin 2 NC — leave unconnected per Bosch BMI088 DS001 §7.1.

# Decoupling per Bosch BMI088 DS001 §7.3 typical operating circuit:
#   - 100 nF X7R on VDD pin 3 (close placement, ≤2mm trace)
#   - 100 nF X7R on VDDIO pin 11 (close placement)
#   - 1 µF X7R on VDD (parallel bulk)
c_bmi_vdd = Part("Device", "C", value="100nF", footprint=FP_C_0402)
c_bmi_vdd.ref = "C91"
P3V3_IMU += c_bmi_vdd[1]
GND      += c_bmi_vdd[2]

c_bmi_vddio = Part("Device", "C", value="100nF", footprint=FP_C_0402)
c_bmi_vddio.ref = "C92"
P3V3_IMU += c_bmi_vddio[1]
GND      += c_bmi_vddio[2]

c_bmi_bulk = Part("Device", "C", value="1uF", footprint=FP_C_0402)
c_bmi_bulk.ref = "C93"
P3V3_IMU += c_bmi_bulk[1]
GND      += c_bmi_bulk[2]


# --------------------------------------------------------------------
# IMU3: LSM6DSV16X (LGA-14)
# --------------------------------------------------------------------
# Symbol: lsm6dsv16x:LSM6DSV16XTR (easyeda2kicad C5267406). Pin map:
#   pin 1: SDO/SA0 — SPI MISO (in 4-wire SPI mode) → SPI3_MISO
#   pin 2: SDx/AH1/Qvar1 — aux SPI MISO / analog hub / Qvar — NC (no aux features used)
#   pin 3: SCx/AH2/Qvar2 — aux SPI clock / analog hub / Qvar — NC
#   pin 4: INT1 — primary data-ready / wake interrupt → IMU3_INT1
#   pin 5: Vdd_IO — digital I/O supply → +3V3_IMU
#   pin 6: GND → GND
#   pin 7: GND → GND
#   pin 8: Vdd — main supply → +3V3_IMU
#   pin 9: INT2 — secondary interrupt (testpoint)
#   pin 10: OCS_Aux — aux SPI chip select — NC
#   pin 11: SDO_Aux — aux SPI MISO — NC
#   pin 12: CS — primary chip select → IMU3_CS
#   pin 13: SCL — SPC (SPI clock) → SPI3_SCK
#   pin 14: SDA — SDI (SPI MOSI in 4-wire mode) → SPI3_MOSI

imu3 = Part(
    "lsm6dsv16x", "LSM6DSV16XTR",
    footprint="lsm6dsv16x:LGA-14_L3.0-W2.5-P0.50-BR",
    value="LSM6DSV16X",
)
imu3.ref = "U9"

# Power + ground.
P3V3_IMU += imu3[5]   # Vdd_IO
P3V3_IMU += imu3[8]   # Vdd
GND      += imu3[6]
GND      += imu3[7]

# SPI bus.
SPI3_MISO += imu3[1]    # SDO → MISO
IMU3_CS   += imu3[12]   # ~CS
SPI3_SCK  += imu3[13]   # SCL/SPC
SPI3_MOSI += imu3[14]   # SDA/SDI

# Primary interrupt.
IMU3_INT1 += imu3[4]

# Pin 9 INT2 testpoint.
LSM6DSV_INT2_TP = Net("LSM6DSV_INT2_TP")
LSM6DSV_INT2_TP += imu3[9]

# Aux SPI features (pins 2, 3, 10, 11) — explicitly NC per ST DS13818 §3.1.
# ArduPilot driver does not exercise the aux SPI / analog hub / Qvar
# features; leaving them floating is correct (datasheet permits this).

# Decoupling per ST LSM6DSV16X DS13818 §7 application info:
#   - 100 nF on Vdd (pin 8)
#   - 100 nF on Vdd_IO (pin 5)
#   - 10 nF on Vdd (high-freq parallel)
c_lsm_vdd = Part("Device", "C", value="100nF", footprint=FP_C_0402)
c_lsm_vdd.ref = "C94"
P3V3_IMU += c_lsm_vdd[1]
GND      += c_lsm_vdd[2]

c_lsm_vddio = Part("Device", "C", value="100nF", footprint=FP_C_0402)
c_lsm_vddio.ref = "C95"
P3V3_IMU += c_lsm_vddio[1]
GND      += c_lsm_vddio[2]

c_lsm_hf = Part("Device", "C", value="10nF", footprint=FP_C_0402)
c_lsm_hf.ref = "C96"
P3V3_IMU += c_lsm_hf[1]
GND      += c_lsm_hf[2]


# --------------------------------------------------------------------
# Move IMU1 (ICM-42688-P) onto the clean +3V3_IMU rail too
# --------------------------------------------------------------------
# v1.1 enhancement: route IMU1's VDD + VDDIO + decoupling to +3V3_IMU so
# all three IMUs share the LP5907-isolated low-noise rail. This is a net
# rename only — IMU1's existing C41/C42/C43 caps move from +3V3 → +3V3_IMU.
# Reasoning: noise isolation is asymmetric otherwise — IMU2/3 would have
# better noise floor than IMU1.
#
# IMPORTANT: This is done by overriding the existing P3V3 connections on
# imu[14] (VDD) and imu[8] (VDDIO) — but SKiDL Net.connect adds to the
# existing net, doesn't replace. Instead, leave imu (IMU1) connections
# alone; the rail-rename happens at PCB-layout time by tying +3V3_IMU =
# +3V3 if needed. For the netlist topology at R1, leave IMU1 on +3V3.
# Phase R3 placement can revisit if IMU1 isolation becomes a concern.
#
# Decision: defer IMU1 rail-migration to R3 / Phase 6h ADC-noise sim
# decision. v1.1 R1 schematic keeps IMU1 on +3V3 (unchanged); IMU2 + IMU3
# on +3V3_IMU. If the LP5907 capacity (250mA) is exhausted by all 3 IMUs
# (very unlikely — each ~5mA active), the sim catches it.
