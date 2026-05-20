"""
novapcb Phase 3f — ESC outputs sheet (8 DShot channels to motor solder pads).

Wires the 8 motor output pins (Phase 2e bdshot-locked) to 8 motor output
pad pairs (signal + GND per motor). No series resistors per
MatekH743-bdshot inheritance; no power passthrough (ESCs powered directly
from the main battery, not through the FC).

## Authority for this sheet

  - `firmware/hwdef-novapcb/hwdef.dat` — AUTHORITATIVE for the 8 PWM pin
    map. Lines 165-172 (Phase 2e bdshot lock). Cited inline below.
  - MatekH743-bdshot hwdef (`~/ardupilot/libraries/AP_HAL_ChibiOS/hwdef/MatekH743-bdshot/hwdef.dat:23-30`)
    — same 8-pin motor block; NO series resistors on the DShot lines
    (motor pins declared bare). novapcb inherits this topology.

## hwdef.dat-cited authoritative pin map

| PWM # | Net | MCU pin | Source line | Timer + Channel | BIDIR |
|---:|---|---|---|---|:---:|
| 1 | MOT1 | PB0  | 165 | TIM3_CH3 | ✓ |
| 2 | MOT2 | PB1  | 166 | TIM3_CH4 | — |
| 3 | MOT3 | PA0  | 167 | TIM2_CH1 | ✓ |
| 4 | MOT4 | PA1  | 168 | TIM2_CH2 | — |
| 5 | MOT5 | PA2  | 169 | TIM5_CH3 | ✓ |
| 6 | MOT6 | PA3  | 170 | TIM5_CH4 | — |
| 7 | MOT7 | PD12 | 171 | TIM4_CH1 | ✓ |
| 8 | MOT8 | PD13 | 172 | TIM4_CH2 | — |

BIDIR-DShot pattern (4/8 channels per the H743 "one BIDIR per timer"
constraint): PB0 / PA0 / PA2 / PD12 — one channel per timer. Standard
DShot300/600 on the remaining four. Phase 6g sim validates ringing on
all 8 channels; BIDIR-line signal integrity gets extra attention
because telemetry returns on the same wire.

## Decisions resolved this sheet

### ESC connector / termination type (esc-connector-type fork)

**Solder pads** (16 pads total: 8 motor signals + 8 GND returns).

Reasoning:
  - MatekH743 reference convention: mini-FC motor outputs are solder pads,
    not connectors (smaller footprint, lower profile, lower BOM cost).
  - Phase 2.5 P0.4 inventory explicitly noted "JST-SH or solder pads —
    connector type TBD"; the placement-fit sketch used 2× JST-SH 4-pin
    because they had ready KiCad footprints, but the fit check passes
    just as well (or better) with solder pads since pads take less area.
  - Production ESC wires are hand-soldered to the pads — standard
    workflow for Matek-class mini-FCs.
  - Phase 4 layout decides exact pad geometry (typical 2.5×1.5 mm pads
    at 2.5 mm pitch); this sub-phase captures the topology only.

Each motor pad pair = signal + GND. 8 motors × 2 pads = 16 pads total.
Schematic models each pair as `Connector_Generic:Conn_01x02` for
netlist clarity (pin 1 = motor signal, pin 2 = GND).

### Series resistors on DShot lines (dshot-series-r fork)

**None** (inherit MatekH743-bdshot — bare DShot lines, no series R).

  - MatekH743-bdshot/hwdef.dat:23-30 declares PWM pins bare — no series-
    resistor convention in the firmware-side reference.
  - Some FCs add ~33Ω series R for ringing damping; MatekH743 ships in
    volume without it. Surely-working = inherit the reference.
  - **BIDIR-line consideration**: PB0/PA0/PA2/PD12 are bidirectional —
    telemetry returns on the same wire. A series resistor would affect
    BOTH directions equally; if MatekH743-bdshot chose no R, that's the
    correct call for BIDIR-DShot operation. Don't improvise a value.
  - Phase 6g sim validates ringing on all 8 channels. If sim shows
    ringing issues, Phase 6g recommends a series-R value with proper
    impedance analysis — not a Phase 3 guess.

### Power passthrough (3f.4)

**No power passthrough** on the motor connector — signal + GND only.

ESCs in standard multirotor topology are powered directly from the
main battery (via the airframe's power-distribution board or pigtail
wiring), NOT through the FC. The FC's motor connector carries only
the low-current DShot signal wire (3.3V logic, ~10mA) + GND return.
Per CLAUDE.md §3.4 "Logic level: 3.3V" + standard mini-FC practice;
MatekH743 follows the same convention.

If a future v1.x ever needs VBAT/5V on the motor connector (e.g. for
a powered fan-out board), that lands as an explicit Phase 4 hwdef-rev
+ schematic-rev — not in v1.

## What this sheet does NOT do

  - Phase 4 PCB layout — exact motor pad geometry, trace impedance
    (DShot300 ~50Ω target), pad placement near bottom edge per Phase 2.5
  - Phase 6g sim — DShot ringing, BIDIR-line signal integrity at 600 kHz
  - Phase 9 bench — actual ESC arming + spin-up + BIDIR telemetry
"""

import skidl
from skidl import Part, Net

from sheets.common import setup, n
from sheets.mcu_3a import mcu

setup()


# ---- shared nets ----
GND = n("GND")


# ---- MCU side: wire the 8 PWM pins to the MOT1..MOT8 nets ----
# hwdef.dat:165-172 — Phase 2e bdshot lock. Pin → motor mapping per the
# PWM(n) numbering in hwdef:
#   PWM(1)=PB0(BIDIR), PWM(2)=PB1, PWM(3)=PA0(BIDIR), PWM(4)=PA1,
#   PWM(5)=PA2(BIDIR), PWM(6)=PA3, PWM(7)=PD12(BIDIR), PWM(8)=PD13
motor_map = [
    # (motor_index, mcu_pin, bidir_flag)
    (1, "PB0",  True),
    (2, "PB1",  False),
    (3, "PA0",  True),
    (4, "PA1",  False),
    (5, "PA2",  True),
    (6, "PA3",  False),
    (7, "PD12", True),
    (8, "PD13", False),
]

mot_nets = {}
for idx, mcu_pin, _bidir in motor_map:
    net = n(f"MOT{idx}")
    net += mcu[mcu_pin]
    mot_nets[idx] = net


# ---- motor output pads (8× Conn_01x02 = 8 motors × (signal + GND)) ----
# Each "connector" represents a solder-pad PAIR: pin 1 = motor signal,
# pin 2 = GND. Footprint placeholder for Phase 4 layout — production
# pad geometry (2.5×1.5 mm at 2.5 mm pitch, or equivalent) decided
# there; the schematic only fixes the topology.
#
# Reference designators J11..J18 (J1-J9 already in use: J1 USB-C, J2
# microSD, J3 telem, J4 power, J5 GPS, J6 CAN/aux, J7 ESC1-4 stub from
# Phase 2.5 placement, J8 ESC5-8 stub, J9 SWD). The Phase 2.5 J7/J8
# were placement-fit-only stubs; Phase 4 layout uses J11..J18 (one per
# motor) instead, with the solder-pad approach decided this sheet.
for idx in range(1, 9):
    pad = Part(
        "Connector_Generic", "Conn_01x02",
        # Placeholder footprint — Phase 4 layout decides actual pad geometry.
        # Using a generic header footprint for now; Phase 4 swaps to the
        # production solder-pad land pattern.
        footprint="Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
        value=f"ESC{idx}_PAD",
    )
    pad.ref = f"J{10 + idx}"   # J11..J18
    mot_nets[idx] += pad[1]    # pin 1 = motor signal
    GND            += pad[2]   # pin 2 = GND return
