"""
novapcb Phase 3j (v1.1) — CAN bus sheet (FDCAN1 only on LQFP-100).

Adds the CAN transceiver + connector + ESD + jumper-selectable termination
for the single CAN port on FDCAN1. 2nd CAN (FDCAN2) is NOT routable on
LQFP-100 with the 3-IMU plan — see docs/RESPIN_SCOPE.md §2 and master
adjudication 2026-05-21 for the v2/LQFP-144-repackage deferral.

## Authority for this sheet

  - `firmware/hwdef-novapcb/hwdef.dat` — AUTHORITATIVE for FDCAN1 pin map:
    hwdef.dat:144  `PD0 CAN1_RX CAN1`
    hwdef.dat:145  `PD1 CAN1_TX CAN1`
    hwdef.dat:146  `PD3 GPIO_CAN1_SILENT OUTPUT PUSHPULL SPEED_LOW LOW GPIO(70)`
  - NXP TJA1051TK/3 datasheet TJA1051 rev 6 §6 (pinning) — chip pin map
  - NXP PESD2CAN datasheet TVS array — CAN ESD protection
  - Pixhawk Connector Standard DS-009 — 4-pin JST-GH CAN connector pinout
  - docs/RESPIN_PARTS_REVIEW.md §5 — part vetting

## hwdef-cited pin map

| Net | MCU pin | hwdef.dat line |
|---|---|---|
| CAN1_RX | PD0 | 144 |
| CAN1_TX | PD1 | 145 |
| GPIO_CAN1_SILENT | PD3 | 146 |

## TJA1051TK/3 pin map (NXP DS rev 6 §6)

| Pin | Name | Function | This-sheet wiring |
|---|---|---|---|
| 1 | TXD | Transmit data input | CAN1_TX (from MCU PD1) |
| 2 | GND | Ground | GND |
| 3 | VCC | 5V supply | +5V |
| 4 | RXD | Receive data output | CAN1_RX (to MCU PD0) |
| 5 | VIO | I/O voltage reference | +3V3 (for 3.3V MCU logic) |
| 6 | CANL | CAN bus low | CANL_NET (to connector pin 2) |
| 7 | CANH | CAN bus high | CANH_NET (to connector pin 3) |
| 8 | S | Standby mode select | GPIO_CAN1_SILENT (MCU PD3 — software-controlled silent) |

The TJA1051TK/3 (the /3 variant) provides a separate VIO pin so the
logic-level interface to the MCU is at 3.3V while the bus VCC is 5V.
This gives better noise margin than a 3.3V-only transceiver and is the
master-approved choice (2026-05-21).

Pin 8 S = standby: HIGH → standby (transceiver dormant), LOW → normal
mode. Wired to PD3 which hwdef.dat:146 already declares as
GPIO_CAN1_SILENT — ArduPilot can put the bus in silent mode via this
GPIO. Default state LOW (active per hwdef PUSHPULL LOW).

## JST-GH 4P CAN connector pinout (Pixhawk DS-009)

| Pin | Signal | Wiring |
|---|---|---|
| 1 | VCC +5V | +5V |
| 2 | CAN_H | CANH_NET (post-ESD) |
| 3 | CAN_L | CANL_NET (post-ESD) |
| 4 | GND | GND |

Standard Pixhawk 4-pin CAN connector — interchangeable with DroneCAN,
UAVCAN, Cube-style ecosystem.

## Bus termination (jumper-selectable)

Per master directive 2026-05-21: 120Ω termination jumper-selectable
per CAN port. Whether the FC terminates depends on its bus position
(end-of-bus = terminate; mid-bus = don't terminate).

Topology: two adjacent solder pads with a 120Ω 0603 between them and
a cuttable trace from CAN_H/CAN_L through the resistor. Default
DELIVERED state = terminated (jumper closed, resistor in circuit).
User cuts the trace if FC is not at end-of-bus.

Net: TERM_BETWEEN — a small mid-net node between R_TERM and the
through-trace. The R_TERM resistor sits between CAN_H and CAN_L; the
jumper is a 0Ω 0603 in series. To OPEN the termination, user removes
the 0Ω jumper.

## ESD on CAN bus (PESD2CAN)

The CAN connector is external + can see long cables → ESD risk on
CANH/CANL is real. PESD2CAN is the NXP CAN-bus-specific TVS array:
24V standoff (above the 5V CAN signal range), ~25 pF capacitance
(acceptable up to ~1 Mbps classical CAN; FD-CAN 5 Mbps SI verified at
R6 sim if SD demands it).

Placement: between connector pin 2/3 and the rest of the trace, near
the connector body (Phase 4 placement requirement).

## What this sheet does NOT do

  - Phase 4 PCB layout — short CANH/CANL pair routing with matched
    impedance + ESD-at-connector placement + termination jumper layout
  - R6 sim: CAN-bus SI eye diagram + ESD impulse response
  - Phase 9 bench: real CAN device handshake (e.g., AP_Periph CAN GPS
    or compass)

## What was DEFERRED to v2

  - 2nd CAN port (FDCAN2) — LQFP-100 pin reality blocks all FDCAN2
    alternates with the 3-IMU plan. Defer to v2 with STM32H743ZG
    LQFP-144 repackage. CAN is future-proofing (Nova drone uses zero
    CAN today); 1 port already provides headroom.
"""

import skidl
from skidl import Part, Net

from sheets.common import setup, n, FP_R_0402, FP_C_0402
from sheets.mcu_3a import mcu

setup()


# ---- shared nets ----
GND  = n("GND")
P3V3 = n("+3V3")
P5V  = n("+5V")

# FDCAN1 nets (hwdef.dat:144-146).
CAN1_RX             = n("CAN1_RX")
CAN1_TX             = n("CAN1_TX")
GPIO_CAN1_SILENT    = n("GPIO_CAN1_SILENT")

CAN1_RX          += mcu["PD0"]
CAN1_TX          += mcu["PD1"]
GPIO_CAN1_SILENT += mcu["PD3"]


# ---- TJA1051TK/3,118 transceiver (U14) ----
# Symbol+footprint pulled via easyeda2kicad from LCSC C124020 — HVSON-8
# (3.0×3.0mm with EXPOSED PAD), NOT TSSOP-8 (master correction 2026-05-21:
# NXP naming -T = SO8, -TK = HVSON8). Pin 9 EP must be soldered to GND for
# thermal performance per NXP DS rev 6 §11.
u14 = Part(
    "tja1051", "TJA1051TK_3,118",   # easyeda2kicad sanitizes "/" → "_" in symbol names
    footprint="tja1051:HVSON-8_L3.0-W3.0-P0.65-BL-EP",
    value="TJA1051TK/3",
)
u14.ref = "U14"

# CAN bus nets — pre-ESD (transceiver side) and post-ESD (connector side).
CANH_NET = Net("CANH_NET")
CANL_NET = Net("CANL_NET")

CAN1_TX           += u14[1]   # pin 1: TXD
GND               += u14[2]   # pin 2: GND
P5V               += u14[3]   # pin 3: VCC = +5V
CAN1_RX           += u14[4]   # pin 4: RXD
P3V3              += u14[5]   # pin 5: VIO = +3V3
CANL_NET          += u14[6]   # pin 6: CANL
CANH_NET          += u14[7]   # pin 7: CANH
GPIO_CAN1_SILENT  += u14[8]   # pin 8: S = standby/silent control
GND               += u14[9]   # pin 9: EP (exposed pad) — tie to GND for thermal + ESD


# ---- TJA1051 decoupling (per NXP DS table 17 'Application information') ----
# 100 nF on VCC pin 3 + 100 nF on VIO pin 5.
c_u14_vcc = Part("Device", "C", value="100nF", footprint=FP_C_0402)
c_u14_vcc.ref = "C83"
P5V += c_u14_vcc[1]
GND += c_u14_vcc[2]

c_u14_vio = Part("Device", "C", value="100nF", footprint=FP_C_0402)
c_u14_vio.ref = "C84"
P3V3 += c_u14_vio[1]
GND  += c_u14_vio[2]


# ---- PESD2CAN,215 ESD protection (U15) ----
# Symbol+footprint pulled via easyeda2kicad from LCSC C75176 — SOT-23-3
# (NOT SOT-143; master correction 2026-05-21: Nexperia PESD2CAN,215 ships
# in 3-pin SOT-23). Per Nexperia PESD2CAN datasheet (DS rev 7) §6 pin
# config (standard 3-pin SOT-23 TVS array layout):
#   pin 1 = I/O1 (one bidirectional CAN bus line)
#   pin 2 = I/O2 (other bidirectional CAN bus line)
#   pin 3 = GND (common cathode of TVS pair)
# CAN_H vs CAN_L assignment to I/O1 vs I/O2 is symmetric (bidirectional TVS).
u15 = Part(
    "pesd2can", "PESD2CAN,215",
    footprint="pesd2can:SOT-23-3_L2.9-W1.3-P1.90-LS2.4-BR",
    value="PESD2CAN",
)
u15.ref = "U15"

CANH_NET += u15[1]   # pin 1: I/O1 = CANH
CANL_NET += u15[2]   # pin 2: I/O2 = CANL
GND      += u15[3]   # pin 3: GND (common cathode)


# ---- Termination: 120Ω 0603 with jumper-selectable disconnect ----
# Topology: CANH_NET ── R_TERM (120Ω) ── R_TERM_JUMPER (0Ω jumper) ── CANL_NET
# Default delivered state: jumper INSTALLED → bus terminated.
# To DISABLE termination: remove or cut the 0Ω jumper R_TERM_JUMPER.
# Physical layout (R2/R3 phase): place the 120Ω + jumper adjacent so the
# user can identify + manipulate easily.

TERM_MID = Net("CAN_TERM_MID")   # between R_TERM (120Ω) and R_TERM_JUMPER (0Ω)

r_term = Part(
    "Device", "R",
    value="120R",
    footprint="Resistor_SMD:R_0603_1608Metric",
)
r_term.ref = "R45"
CANH_NET += r_term[1]
TERM_MID += r_term[2]

r_term_jumper = Part(
    "Device", "R",
    value="0R",
    footprint="Resistor_SMD:R_0603_1608Metric",
)
r_term_jumper.ref = "R46"
TERM_MID += r_term_jumper[1]
CANL_NET += r_term_jumper[2]


# ---- JST-GH 4P CAN connector (J20) ----
# Pixhawk DS-009 4-pin CAN connector.
can_conn = Part(
    "Connector_Generic", "Conn_01x04",
    footprint="Connector_JST:JST_GH_SM04B-GHS-TB_1x04-1MP_P1.25mm_Horizontal",
    value="CAN_4P",
)
can_conn.ref = "J20"

P5V      += can_conn[1]   # pin 1: VCC +5V
CANH_NET += can_conn[2]   # pin 2: CAN_H
CANL_NET += can_conn[3]   # pin 3: CAN_L
GND      += can_conn[4]   # pin 4: GND
