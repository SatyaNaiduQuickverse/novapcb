"""
novapcb Phase 3i — telemetry UART connector sheet (USART1 on JST-GH 6P).

Phase 3-exit A2 hwdef-completeness check (2026-05-20) caught that USART1
TX/RX (PA9/PA10) was defined in hwdef.dat:113-114 but had no novapcb
connector — the Phase 3 8-sheet breakdown (3a-3h) missed it. Master
adjudication: NEEDS-FIX, add as Phase 3i (separate small sub-phase
following the CRSF sheet pattern).

Telem is a standard Pixhawk-class port + the conventional GCS-attach
point for Phase 9 bring-up (independent of the USB-CDC primary link).
novapcb's identity as a functional Pixhawk/CubeOrange+ drop-in
(`CLAUDE.md §0/§1`) requires it.

## Authority for this sheet

  - `firmware/hwdef-novapcb/hwdef.dat:113-114` — USART1 TX/RX
    (PA9/PA10). AUTHORITATIVE per hwdef-cited discipline.
  - Pixhawk Connector Standard DS-009 (`pixhawk/Pixhawk-Standards`
    GitHub, canonical) — TELEM JST-GH 6-pin connector pinout
    (web-confirmed 2026-05-20).
  - `DECISIONS.md §7` — JST-GH connector standard.

## hwdef.dat-cited authoritative pin map

| Net | MCU pin | Source line |
|---|---|---|
| USART1_TX (FC → peripheral) | PA9 | 114: `PA9  USART1_TX USART1` |
| USART1_RX (peripheral → FC) | PA10 | 113: `PA10 USART1_RX USART1` |

USART1 CTS/RTS hardware flow control: NOT defined in hwdef.dat (grep
empty for `USART1_CTS` / `USART1_RTS`). Per master's `telem-connector`
fork pre_recommendation, the 6-pin Pixhawk-standard footprint is still
used (for mechanical compatibility with standard Pixhawk telem cables),
with CTS/RTS pins as NC on the FC side. Software flow control is
sufficient for telem-radio + GCS use cases.

## Pixhawk DS-009 TELEM 6-pin JST-GH pinout

| Pin | Signal | Voltage | Wiring |
|---|---|---|---|
| 1 | VCC | +5V | → +5V rail |
| 2 | TX (from FC) | +3V3 logic | USART1_TX → MCU PA9 |
| 3 | RX (to FC) | +3V3 logic | USART1_RX → MCU PA10 |
| 4 | CTS (Clear to Send) | +3V3 logic | NC (hwdef does not assign USART1_CTS) |
| 5 | RTS (Request to Send) | +3V3 logic | NC (hwdef does not assign USART1_RTS) |
| 6 | GND | — | GND |

Standard Pixhawk telem cable will work — peripheral side (e.g. SiK
radio) crosses TX/RX + CTS/RTS at the cable end.

## What this sheet does NOT do

  - Phase 4 PCB layout — connector placement (typical bottom edge with
    other JST-GH ports per Phase 2.5 sketch J3 location)
  - Phase 6.5 forum review — ESD on the telem connector (joins
    Mauch/CRSF/GPS in the row 12 deferred-ESD pile)
  - Phase 9 bench — actual telem-radio attach + GCS connection
"""

import skidl
from skidl import Part, Net

from sheets.common import setup, n
from sheets.mcu_3a import mcu

setup()


# ---- shared nets ----
GND       = n("GND")
P5V       = n("+5V")
USART1_TX = n("USART1_TX")   # MCU PA9 → telem peripheral (RX side)
USART1_RX = n("USART1_RX")   # telem peripheral (TX side) → MCU PA10


# ---- MCU side: wire USART1 TX/RX to shared nets ----
# hwdef.dat:113-114 — USART1 RX/TX
USART1_TX += mcu["PA9"]
USART1_RX += mcu["PA10"]


# ---- Telem JST-GH 6-pin connector (Pixhawk DS-009 TELEM standard) ----
telem_conn = Part(
    "Connector_Generic", "Conn_01x06",
    footprint="Connector_JST:JST_GH_SM06B-GHS-TB_1x06-1MP_P1.25mm_Horizontal",
    value="TELEM_6P",
)
telem_conn.ref = "J3"   # J3 reserved per Phase 2.5 sketch for the telem connector

# Pin assignments per DS-009 TELEM 6-pin standard.
P5V       += telem_conn[1]   # VCC +5V (peripheral supply)
USART1_TX += telem_conn[2]   # FC TX → peripheral RX (cable crosses)
USART1_RX += telem_conn[3]   # peripheral TX → FC RX
# Pin 4 CTS: NC (USART1 CTS not assigned in hwdef.dat — software flow control)
# Pin 5 RTS: NC (USART1 RTS not assigned in hwdef.dat)
GND       += telem_conn[6]   # GND


# ---- ESD on telem TX/RX (v1.1 redundancy re-spin) ----
# Per docs/RESPIN_SCOPE.md + RESPIN_PARTS_REVIEW.md §3:
# Bidirectional TVS to GND on each external signal line. Placement
# (Phase 4 layout): immediately adjacent to the connector body so the
# clamp fires before the surge reaches MCU GPIO.
#
# Part: ESD7L5.0DT5G (onsemi, SOT-723) — 5V standoff (>3.3V signal),
# ~0.5pF capacitance (negligible at telem rates ≤ 921600 baud), bidirectional.
# JLC library status verified at R2 footprint phase per scope §7 q8.
#
# Symbol: Device:D_TVS (bidirectional generic), pin 1 = signal, pin 2 = GND.

esd_tx = Part("Device", "D_TVS",
              value="ESD7L5.0DT5G",
              footprint="Diode_SMD:D_SOD-723")
esd_tx.ref = "D11"
USART1_TX += esd_tx[1]
GND       += esd_tx[2]

esd_rx = Part("Device", "D_TVS",
              value="ESD7L5.0DT5G",
              footprint="Diode_SMD:D_SOD-723")
esd_rx.ref = "D12"
USART1_RX += esd_rx[1]
GND       += esd_rx[2]
