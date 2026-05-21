"""
novapcb Phase 3g — CRSF UART connector + USB-C receptacle sheet.

Two distinct blocks on one sheet:

  1. **CRSF block** — schematic-side: ELRS RX termination. Carries +5V +
     USART6_TX + USART6_RX + GND. Wired per Phase 2f lock (defaults.parm
     SERIAL7_PROTOCOL 23 + SERIAL7_BAUD 420; CRSF at 420 kbaud).

     **2026-05-20 Phase 4b option-θ (footprint, NOT schematic, change):**
     Phase 3g originally captured CRSF as a JST-GH 4-pin connector.
     Phase 4b layout discovered that 4× MP-pad JST-GH connectors plus the
     full peripheral set are geometrically over-constrained on the
     36×36mm board (verified: no no-MP JST-GH part exists in JST catalog;
     MatekH743 reference uses a different connector architecture). Master
     adjudicated to swap J10's PHYSICAL FOOTPRINT to a 4-pad solder array
     (CRSF_solder_pad in `hardware/kicad/novapcb-layout/lib/novapcb.pretty/`),
     same convention as ESC outputs. The NETLIST is unchanged — 4 pins
     wired identically: pin 1=5V, 2=TX, 3=RX, 4=GND. The schematic part
     stays Conn_01x04. This is a Phase 4 footprint swap (like the Phase
     4a ESC solder-pad swap), not a Phase 3 re-do. Pixhawk DS-009 cable
     compatibility is preserved for J3 (telem) / J4 (Mauch) / J5 (GPS+mag)
     which keep JST-GH; only J10 CRSF becomes a solder-pad termination
     (ELRS RX is semi-permanently installed so wire-solder is acceptable).

  2. **USB-C block** — USB 2.0 USB-C receptacle (HRO TYPE-C-31-M-12 from
     Phase 2.5 P0.4 inventory). Carries VBUS + GND + D+/D- diff pair +
     CC1/CC2 5.1k pulldowns (MANDATORY for device-side enumeration) +
     USBLC6-2P6 ESD protection on D+/D- (standard practice for external
     USB connector).

## Authority for this sheet

  - `firmware/hwdef-novapcb/hwdef.dat` — AUTHORITATIVE for the MCU pin map
    (USART6 + OTG_FS). Cited inline below.
  - `firmware/hwdef-novapcb/defaults.parm` — CRSF parameter lock
    (SERIAL7_PROTOCOL 23 + SERIAL7_BAUD 420; Phase 2f).
  - `DECISIONS.md §4` — external ELRS RX module on CRSF UART (locks novapcb
    v1 to CRSF). `DECISIONS.md §7` — JST-GH connector standard.
  - `DECISIONS.md §9` — USB VID/PID resolved 0x1209:0x5740 (Phase 2h).
  - USBLC6-2P6 datasheet (ST) — USB common-mode TVS + 24V clamp on D+/D-.
  - USB-C device-side requirements — CC1+CC2 each need a 5.1 kΩ Rd pulldown
    to GND to advertise as a UFP (downstream-facing port / sink); without
    Rd on CC, the host's Type-C detection won't enumerate the port at all.
    This is a HARD requirement, not a judgement call.

## hwdef.dat-cited authoritative pin map

| Net | MCU pin | hwdef.dat line |
|---|---|---|
| USART6_TX (CRSF TX from FC) | PC6 | 134: `PC6 USART6_TX USART6` |
| USART6_RX (CRSF RX to FC) | PC7 | 133: `PC7 USART6_RX USART6` |
| OTG_FS_DM (USB D-) | PA11 | 29: `PA11 OTG_FS_DM OTG1` |
| OTG_FS_DP (USB D+) | PA12 | 30: `PA12 OTG_FS_DP OTG1` |
| USB strings | `USB_STRING_MANUFACTURER "ArduPilot"` + `USB_STRING_PRODUCT "novapcb-v1"` | 12-13 |

`defaults.parm` lines 6 + 12: `SERIAL7_PROTOCOL 23` (RCIN) + `SERIAL7_BAUD 420`
(CRSF 420 kbaud).

## CRSF connector decision (crsf-connector fork)

**JST-GH 4-pin** (`SM04B-GHS-TB`) — per `DECISIONS.md §7` JST-GH standard +
ExpressLRS RP4TD wiring convention.

Pin order (worker-chosen, ELRS-standard):
  1. +5V (BEC rail — ELRS RX needs +5V supply)
  2. USART6_TX (FC → RX telemetry stream; CRSF is full-duplex over 2 wires)
  3. USART6_RX (RX → FC channel data + telemetry response)
  4. GND

CRSF is full-duplex over 2 wires (TX + RX); both lines route to the
connector per ELRS standard. Half-duplex single-wire CRSF (e.g.
inverted-S.Port) is NOT the novapcb config — DECISIONS §4 + Phase 2f
locked CRSF/ELRS specifically. Inversion / half-duplex flags absent
from hwdef.dat per Phase 2f grep (`grep RXINV|TXINV|HALF_DUPLEX` empty).

## USB-C decisions (usbc-cc-esd fork)

**CC1 + CC2 5.1 kΩ pulldowns to GND: MANDATORY.** Per USB-C spec, a
device (UFP / sink) must present Rd = 5.1 kΩ on CC pins for the host
(DFP / source) to detect the port and supply VBUS. Without Rd, the
host's Type-C state machine won't see the device. Two resistors (one
per CC) so the cable orientation is irrelevant — the host uses
whichever CC the cable connects.

**ESD protection: USBLC6-2P6 on D+/D- — CAPTURED.** Standard practice
for external USB connectors. CONFIDENCE_MAP row 12 (EMC/RF) is LOW
explicitly because external-cable ESD isn't otherwise protected;
adding the USBLC6 doesn't raise row 12 (still LOW pending real EMC
sim/review) but it removes the unprotected-D+/D- gap. The chip is
SOT-23-6, ~$0.10 BOM cost, near-mandatory on modern designs.

USB-C signaling: USB 2.0 D+/D- only (no USB 3.x SuperSpeed pairs).
Symbol = `Connector:USB_C_Receptacle_USB2.0_16P`. Footprint =
`Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12` (mid-mount,
Phase 2.5 P0.4 inventory). SBU1/SBU2 unused for USB 2.0 — leave NC
per datasheet.

## USB diff-pair impedance — Phase 4 layout constraint

D+/D- are a 90 Ω differential pair per USB 2.0 high-speed spec.
**This sheet just NETS them correctly** — actual diff-pair impedance
+ symmetric routing + length-matching is a Phase 4 layout constraint
+ Phase 6b sim (USB-CDC signal integrity).

The USBLC6 footprint placement is also Phase 4 layout (TVS array
needs to sit close to the connector, on the host side of the cable
ESD path).

## What this sheet does NOT do

  - Phase 4 PCB layout — USB diff-pair impedance, USBLC6 placement, USB-C
    receptacle keep-outs, CC resistor placement
  - Phase 6b sim — USB-CDC signal integrity at full-speed (12 Mbps)
  - Phase 9 bench — actual USB enumeration on the drone Pi, by-id resolve
  - VID/PID dedicated allocation — `DECISIONS §9` open follow-up
"""

import skidl
from skidl import Part, Net

from sheets.common import setup, n, FP_R_0402
from sheets.mcu_3a import mcu

setup()


# ---- shared nets ----
GND       = n("GND")
P3V3      = n("+3V3")
P5V       = n("+5V")
USART6_TX = n("USART6_TX")  # MCU PC6 → CRSF connector
USART6_RX = n("USART6_RX")  # CRSF connector → MCU PC7
USB_DM    = n("USB_DM")     # MCU PA11 → USB-C D- (post-ESD)
USB_DP    = n("USB_DP")     # MCU PA12 → USB-C D+ (post-ESD)


# ---- MCU side: USART6 + OTG_FS pins ----
# hwdef.dat:133-134 — USART6 RX/TX
USART6_RX += mcu["PC7"]
USART6_TX += mcu["PC6"]
# hwdef.dat:29-30 — OTG_FS D-/D+
USB_DM    += mcu["PA11"]
USB_DP    += mcu["PA12"]


# ====================================================================
# CRSF block — JST-GH 4-pin connector for ExpressLRS RX
# ====================================================================

crsf_conn = Part(
    "Connector_Generic", "Conn_01x04",
    footprint="Connector_JST:JST_GH_SM04B-GHS-TB_1x04-1MP_P1.25mm_Horizontal",
    value="CRSF_4P",
)
crsf_conn.ref = "J10"   # J10 (new). J1-J9 reserved per Phase 2.5 sketch + Phase 3e/3h
                        # convention (J1=USB-C, J2=microSD, J3=telem placeholder, J4=power,
                        # J5=GPS [3e], J6=CAN, J7/J8=ESC stubs replaced by J11-J18 [3f],
                        # J9=SWD [3h]). J10 is the first free ref above the 2.5 sketch's
                        # planning numbers; J11-J18 are motor pads (3f).

# Pin map (ELRS-standard wiring):
P5V       += crsf_conn[1]   # +5V supply to RX
USART6_TX += crsf_conn[2]   # FC TX → RX telemetry channel
USART6_RX += crsf_conn[3]   # RX channel-data → FC
GND       += crsf_conn[4]


# ---- ESD on CRSF TX/RX (v1.1 redundancy re-spin) ----
# Per docs/RESPIN_SCOPE.md + RESPIN_PARTS_REVIEW.md §3: bidirectional TVS
# to GND on each external CRSF UART line. CRSF runs at 420 kbaud — well
# within ESD7L5.0DT5G's ~0.5pF / 5V-standoff envelope.
esd_crsf_tx = Part("Device", "D_TVS",
                   value="ESD7L5.0DT5G",
                   footprint="esd7l50:SOT-723_L1.2-W0.8-P0.40-LS1.2-BR")
esd_crsf_tx.ref = "D13"
USART6_TX += esd_crsf_tx[1]
GND       += esd_crsf_tx[2]

esd_crsf_rx = Part("Device", "D_TVS",
                   value="ESD7L5.0DT5G",
                   footprint="esd7l50:SOT-723_L1.2-W0.8-P0.40-LS1.2-BR")
esd_crsf_rx.ref = "D14"
USART6_RX += esd_crsf_rx[1]
GND       += esd_crsf_rx[2]


# ====================================================================
# USB-C block — USB 2.0 receptacle + CC pulldowns + ESD protection
# ====================================================================

# USB-C receptacle. USB 2.0 only (no SuperSpeed pairs).
usbc = Part(
    "Connector", "USB_C_Receptacle_USB2.0_16P",
    footprint="Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
    value="USB-C_2.0",
)
usbc.ref = "J1"   # J1 reserved Phase 2.5 USB-C; same designator

# Pre-ESD D+/D- nets (the receptacle side of the ESD protection — TVS
# sits between connector pins and the MCU pins).
USBC_D_P_PRE = Net("USBC_D_P_PRE")   # USB-C side of D+
USBC_D_M_PRE = Net("USBC_D_M_PRE")   # USB-C side of D-

# Receptacle pin map (per Connector:USB_C_Receptacle_USB2.0_16P symbol):
#   GND: A1, A12, B1, B12 (4 pins) + S1 shield
#   VBUS: A4, A9, B4, B9 (4 pins)
#   CC1: A5;  CC2: B5
#   D+: A6 + B6 (paralleled for orientation flip);  D-: A7 + B7
#   SBU1: A8;  SBU2: B8 (NC for USB 2.0)
for gp in ("A1", "A12", "B1", "B12", "S1"):
    GND += usbc[gp]
for vp in ("A4", "A9", "B4", "B9"):
    P5V += usbc[vp]   # VBUS = +5V from USB host (bench bring-up only per CLAUDE.md §3.6)

USBC_D_P_PRE += usbc["A6"]
USBC_D_P_PRE += usbc["B6"]
USBC_D_M_PRE += usbc["A7"]
USBC_D_M_PRE += usbc["B7"]

# CC1 / CC2 pins — get their 5.1k Rd pulldowns below.
CC1 = Net("USBC_CC1"); CC1 += usbc["A5"]
CC2 = Net("USBC_CC2"); CC2 += usbc["B5"]

# SBU1/SBU2: leave NC for USB 2.0 (Phase 2.5/3g doesn't use SBU; alt-mode would).


# ---- CC1 + CC2 5.1k pulldowns (MANDATORY for UFP enumeration) ----
r_cc1 = Part("Device", "R", value="5.1k", footprint=FP_R_0402)
r_cc1.ref = "R31"
CC1 += r_cc1[1]
GND += r_cc1[2]

r_cc2 = Part("Device", "R", value="5.1k", footprint=FP_R_0402)
r_cc2.ref = "R32"
CC2 += r_cc2[1]
GND += r_cc2[2]


# ---- USBLC6-2P6 ESD protection on D+/D- ----
# ST USBLC6-2P6 — USB common-mode TVS + 24V clamp. SOT-23-6 package.
# Pin map (per KiCad symbol verified 2026-05-20):
#   pin 1 = I/O1 (D+ host side, from USB-C connector)
#   pin 2 = GND
#   pin 3 = I/O2 (D- host side, from USB-C connector)
#   pin 4 = I/O2 (D- device side, to MCU)
#   pin 5 = VBUS (clamp reference)
#   pin 6 = I/O1 (D+ device side, to MCU)
esd = Part(
    "Power_Protection", "USBLC6-2P6",
    footprint="Package_TO_SOT_SMD:SOT-23-6",
    value="USBLC6-2P6",
)
esd.ref = "U5"

USBC_D_P_PRE += esd[1]   # D+ from connector
GND          += esd[2]   # GND
USBC_D_M_PRE += esd[3]   # D- from connector
USB_DM       += esd[4]   # D- to MCU (post-ESD)
P5V          += esd[5]   # VBUS clamp reference
USB_DP       += esd[6]   # D+ to MCU (post-ESD)
