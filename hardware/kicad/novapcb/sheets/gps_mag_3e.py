"""
novapcb Phase 3e — GPS + external-mag connector sheet (JST-GH 10-pin Pixhawk standard).

Captures the connector wiring only — the GPS module and the external
IST8310/RM3100 mag chips are OFF-board (they live on the GPS daughter
module). 3e wires the connector pins to the MCU per the Pixhawk 10-pin
GPS connector standard + the hwdef pin map.

## Authority for this sheet

  - `firmware/hwdef-novapcb/hwdef.dat` — AUTHORITATIVE for MCU pin map.
    Cited inline below.
  - Pixhawk Connector Standard DS-009 (pixhawk/Pixhawk-Standards GitHub)
    — AUTHORITATIVE for the 10-pin GPS connector pin ORDER. Researched
    via web (master 3e.2 cited "Pixhawk Adapter Board" + PX4 GPS
    documentation; pixhawk/Pixhawk-Standards repo is the canonical
    source).
  - `baro_3d.py` — establishes I²C2 pull-up ownership (DPS310 always-present
    slave); THIS sheet's I²C1 pull-ups land here per the same ownership
    pattern.

## hwdef.dat-cited authoritative pin map

| Net | MCU pin | Source line |
|---|---|---|
| GPS1 USART2_TX | PD5 | 117: `PD5 USART2_TX USART2` |
| GPS1 USART2_RX | PD6 | 118: `PD6 USART2_RX USART2` |
| I2C1_SCL | PB6 | 60: `PB6 I2C1_SCL I2C1` |
| I2C1_SDA | PB7 | 61: `PB7 I2C1_SDA I2C1` |
| BUZZER | PA15 | 179: `PA15 BUZZER OUTPUT GPIO(32) LOW` (GPIO via 3a) |
| SAFETY_SW / SAFETY_LED | NOT ASSIGNED in hwdef | see "Safety switch" section |

## Pixhawk 10-pin GPS Connector Standard (DS-009)

Per pixhawk/Pixhawk-Standards `DS-009 Pixhawk Connector Standard.pdf`
(GitHub, canonical) + cross-confirmed via PX4 + Holybro GPS module
docs:

| Pin | Signal | Voltage | This-sheet wiring |
|---|---|---|---|
| 1 | VCC | +5V | +5V (BEC rail, sourced by Phase 3h power-monitor connector) |
| 2 | UART TX (from FC) | +3V3 logic | GPS1_TX → MCU PA2 (USART2_TX; repinned PD5→PA2 task #47) |
| 3 | UART RX (to FC) | +3V3 logic | GPS1_RX → MCU PD6 (USART2_RX) |
| 4 | I²C SCL | +3V3 logic | I2C1_SCL → MCU PB6 |
| 5 | I²C SDA | +3V3 logic | I2C1_SDA → MCU PB7 |
| 6 | SAFETY SWITCH INPUT | +3V3 logic | SAFETY_SW testpoint (hwdef-unassigned; see below) |
| 7 | SAFETY LED OUTPUT | +3V3 logic | SAFETY_LED testpoint (hwdef-unassigned; see below) |
| 8 | +3V3 | +3V3 | +3V3 rail (LDO output) |
| 9 | BUZZER | +3V3 logic | BUZZER → MCU PA15 (hwdef.dat:179) |
| 10 | GND | GND | GND |

The GPS module on the cable end provides: GPS UART (pin 2/3), external
mag I²C (pin 4/5 → IST8310 0x0E or RM3100 0x20), safety switch + LED
(pin 6/7), buzzer driver (pin 9). VCC (pin 1) and 3V3 (pin 8) are
separate rails because some modules need both (5V for the GPS chip
itself, 3V3 for the mag + level translator).

## I²C bus decision (gps-i2c-bus fork)

Decision: **GPS connector uses I²C1** (separate from baro's I²C2).

Reasoning:
  - Cable faults on the external I²C bus (long cable, EMI exposure) are
    isolated from the on-board baro.
  - Phase 4 layout can route both buses cleanly without sharing.
  - I²C ALL_EXTERNAL designator from Phase 2c COMPASS lines covers BOTH
    buses (HAL_I2C_INTERNAL_MASK 0); the external compass driver probes
    both for the IST8310/RM3100 chip. So either bus works at the firmware
    level — the choice is electrical/SI.

I²C1 pull-ups (4.7 kΩ each on SDA + SCL to +3V3) land on THIS sheet per
the 3d ownership rule (always-present-slave or always-present-bus-side
co-located with pull-ups). The GPS module on the cable end provides
the I²C SLAVE; novapcb is the I²C MASTER on this bus; pull-ups on the
master side are the standard pattern. Phase 6d sim validates pull-up
value against actual bus capacitance.

## Safety switch + safety LED (safety-switch fork)

Decision: **Connector pins captured as testpoints; MCU side hwdef-unassigned**.

`hwdef.dat` does NOT assign safety-switch or safety-LED pins (grep'd —
no SAFETY_SW or SAFETY_LED definitions). The Pixhawk connector standard
still carries these pins on cable pins 6 + 7, so the connector
schematic captures them; they route to test pads on the PCB and a
future hwdef revision (v1.x) can wire them to MCU GPIOs if needed. Do
not invent an MCU pin assignment.

If a user uses a GPS module with safety switch + LED, those features
will be ELECTRICALLY NON-FUNCTIONAL until the testpoint pads are
wired (Phase 4 layout decision) and a hwdef.dat revision assigns the
MCU pins (Phase 2-rev work).

## ESD on external connector (3e.5)

The GPS connector is the longest external-cable surface on novapcb (up
to 1 m of GPS cable). ESD on the I²C lines + UART lines + buzzer line
is a real concern. CONFIDENCE_MAP row 12 (EMC/RF coupling) is LOW
explicitly because this kind of external-cable ESD isn't yet protected.

**Decision this sheet: ESD protection NOT captured (deferred).**

  - 5-channel TVS arrays on the I²C + UART lines would be the standard
    addition; flagged for Phase 3.5 reference audit (cross-check
    MatekH743 + Pixhawk6X protection topology if sourceable) + Phase 6.5
    forum review + Phase 6k EMC sim.
  - CONFIDENCE_MAP row 12 stays LOW; no paper-only addition can raise
    it without real review.
"""

import skidl
from skidl import Part, Net

from sheets.common import (
    setup, n, FP_R_0402,
)
from sheets.mcu_3a import mcu

setup()


# ---- shared nets ----
GND      = n("GND")
P3V3     = n("+3V3")
P5V      = n("+5V")
I2C1_SCL = n("I2C1_SCL")
I2C1_SDA = n("I2C1_SDA")
GPS1_TX  = n("GPS1_TX")    # FC → GPS (from MCU PA2 / USART2_TX; repinned from PD5)
GPS1_RX  = n("GPS1_RX")    # GPS → FC (to MCU PD6)
BUZZER   = n("BUZZER")     # MCU PA15 GPIO output


# ---- MCU side: wire GPS UART + I2C1 + buzzer pins to shared nets ----
# USART2 GPS1 TX/RX. TX remapped PD5->PA2 (2026-05-26, task #47): PD5 (N-edge
# pad X=46.0) is boxed by the BATT2 sense-trace verticals (B.Cu 45.1/45.4/46.5)
# — unroutable to J5 (Freerouting 4 passes + manual all fail the N-edge exit).
# PA2 is the only other USART2_TX pin on LQFP-100 (AF7), free since MOT5 vacated
# it (PR #83 -> PE13), and on the W edge with a near-empty corridor to J5 SW.
# Same UART2 peripheral as RX (PD6) — no firmware split. (master-approved repin.)
GPS1_TX  += mcu["PA2"]
GPS1_RX  += mcu["PD6"]
# hwdef.dat:60-61 — I²C1
I2C1_SCL += mcu["PB6"]
I2C1_SDA += mcu["PB7"]
# BUZZER MCU driver DEFERRED to v2 (2026-05-26, task #47): the GPS N-edge
# cluster is congested and BUZZER (audio feedback only, not flight-critical)
# was the lowest-priority net. ArduPilot runs without a buzzer bound. The
# BUZZER net stays defined (J5.9 + ESD D9 + TP5) but is NOT driven by the MCU
# in v1 — PD7 reverts to a free GPIO. v2: bind a free GPIO to drive BUZZER.
# (was: BUZZER += mcu["PD7"])  — master-approved v2 defer.


# ---- testpoints (hwdef-unassigned safety pins) ----
SAFETY_SW_TP  = Net("SAFETY_SW_TP")
SAFETY_LED_TP = Net("SAFETY_LED_TP")


# ---- JST-GH 10-pin connector ----
# Connector_Generic:Conn_01x10 is the schematic-level generic 10-pin connector
# (all pins PASSIVE — appropriate for a physical connector). PCB footprint is
# the JST_GH_SM10B-GHS-TB horizontal already verified in Phase 2.5 P0.4.
gps_conn = Part(
    "Connector_Generic", "Conn_01x10",
    footprint="Connector_JST:JST_GH_SM10B-GHS-TB_1x10-1MP_P1.25mm_Horizontal",
    value="GPS_MAG_10P",
)
gps_conn.ref = "J5"

# Pin assignments per Pixhawk DS-009 Connector Standard (cited in docstring).
# Pin numbers 1-10 are the connector physical pin numbering.
P5V           += gps_conn[1]   # VCC +5V
GPS1_TX       += gps_conn[2]   # UART TX from FC to GPS
GPS1_RX       += gps_conn[3]   # UART RX from GPS to FC
I2C1_SCL      += gps_conn[4]   # I²C SCL (external compass bus)
I2C1_SDA      += gps_conn[5]   # I²C SDA (external compass bus)
SAFETY_SW_TP  += gps_conn[6]   # safety switch input (testpoint; hwdef-unassigned)
SAFETY_LED_TP += gps_conn[7]   # safety LED output (testpoint; hwdef-unassigned)
P3V3          += gps_conn[8]   # +3V3 (separate from VCC pin 1's +5V)
BUZZER        += gps_conn[9]   # buzzer driver (MCU PA15 GPIO)
GND           += gps_conn[10]  # ground


# ---- I²C1 pull-ups (4.7 kΩ each to +3V3) ----
# Master side (novapcb) co-located with the bus, per the 3d ownership rule.
# Phase 6d sim validates value vs actual bus capacitance.
r_sda = Part("Device", "R", value="4.7k", footprint=FP_R_0402)
r_sda.ref = "R21"
P3V3     += r_sda[1]
I2C1_SDA += r_sda[2]

r_scl = Part("Device", "R", value="4.7k", footprint=FP_R_0402)
r_scl.ref = "R22"
P3V3     += r_scl[1]
I2C1_SCL += r_scl[2]


# ---- ESD on GPS+I2C+BUZZER external lines (v1.1 redundancy re-spin) ----
# Per docs/RESPIN_SCOPE.md + RESPIN_PARTS_REVIEW.md §3:
# Bidirectional TVS to GND on the long-cable signal lines (GPS connector
# = up to 1m external cable, highest ESD exposure on the board).
#
# Lines protected: GPS_TX, GPS_RX, I2C1_SCL, I2C1_SDA, BUZZER (and the
# v1.1 also has LPS22HB on I2C1 internally — the ESD here protects both
# the external bus consumers and U7 from cable surges).
#
# SAFETY_SW + SAFETY_LED are testpoint-only (hwdef-unassigned per docstring)
# — ESD on them at this revision is not required since no MCU pin is wired.
#
# Part: ESD7L5.0DT5G (onsemi). 5V standoff > 3.3V signal, ~0.5pF cap acceptable
# at 400 kHz I2C + 115200 baud GPS UART.

for ref, net_obj in (("D5", GPS1_TX),
                     ("D6", GPS1_RX),
                     ("D7", I2C1_SCL),
                     ("D8", I2C1_SDA),
                     ("D9", BUZZER)):
    esd = Part("Device", "D_TVS",
               value="ESD7L5.0DT5G",
               footprint="esd7l50:SOT-723_L1.2-W0.8-P0.40-LS1.2-BR")
    esd.ref = ref
    net_obj += esd[1]
    GND     += esd[2]


# ---- Test pads (master 2026-05-24 sign-off: 5× Φ1.5mm) ----
# Standard Pixhawk practice — exposed test pads near J5 for Phase 9
# bench bring-up + factory test access. SAFETY_SW/LED have no MCU pin
# (hwdef-unassigned) so test pads are the ONLY way to verify those
# signals; remaining 3 are quick-probe access to common debug signals.
for ref, net_obj, label in (
    ("TP1", SAFETY_SW_TP,  "SAFETY_SW"),
    ("TP2", SAFETY_LED_TP, "SAFETY_LED"),
    ("TP3", GPS1_TX,       "GPS_TX"),
    ("TP4", I2C1_SCL,      "I2C1_SCL"),
    ("TP5", BUZZER,        "BUZZER"),
):
    tp = Part(
        "Connector", "TestPoint",
        value=label,
        footprint="TestPoint:TestPoint_Pad_D1.5mm",
    )
    tp.ref = ref
    net_obj += tp[1]
