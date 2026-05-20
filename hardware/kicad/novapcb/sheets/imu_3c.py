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
SPI1_MOSI += mcu["PD7"]
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
P3V3 += imu[14]        # VDD (main supply)
P3V3 += imu[8]         # VDDIO (tied to VDD per datasheet §11.1 SPI-only circuit)
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
# 100 nF X7R on VDD (close to pin 14)
c_vdd_100n = Part("Device", "C", value="100nF", footprint=FP_C_0402)
c_vdd_100n.ref = "C41"
P3V3 += c_vdd_100n[1]
GND  += c_vdd_100n[2]

# 100 nF X7R on VDDIO (close to pin 8)
c_vddio_100n = Part("Device", "C", value="100nF", footprint=FP_C_0402)
c_vddio_100n.ref = "C42"
P3V3 += c_vddio_100n[1]
GND  += c_vddio_100n[2]

# 2.2 µF X5R bulk on VDD (parallel with C41)
c_vdd_bulk = Part("Device", "C", value="2.2uF", footprint=FP_C_0402)
c_vdd_bulk.ref = "C43"
P3V3 += c_vdd_bulk[1]
GND  += c_vdd_bulk[2]
