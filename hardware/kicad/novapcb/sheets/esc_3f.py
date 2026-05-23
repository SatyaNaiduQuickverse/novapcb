"""
novapcb Phase 3f — ESC outputs sheet (8 DShot channels on 1× JST-GH 10-pin
connector, Pixhawk 6X FMU PWM OUT convention).

Wires the 8 motor output pins (Phase 2e bdshot-locked) to a SINGLE
10-pin JST-GH connector matching the Pixhawk 6X baseboard FMU PWM
OUT port (8 sig + 1 VDD_SERVO + 1 GND). No series resistors per
MatekH743-bdshot inheritance; no power passthrough on novapcb (ESCs
powered directly from the main battery — pin 9 VDD_SERVO is kept
physically present for harness compatibility but is **unconnected**
on novapcb, see "esc-connector-type fork" below for ratification).

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

**1× JST-GH 1x10 horizontal** — Pixhawk 6X FMU PWM OUT standard.

Reasoning:
  - `DECISIONS.md §7` (locked 2026-05-18) mandates JST-GH (Pixhawk
    family) for ALL FC connectors — "matches every harness on the
    existing airframe; bring-up must not also require re-crimping
    cables." The motivation is literal: an existing Pixhawk-family
    harness must plug into novapcb unchanged.
  - **Competitor reference**: Pixhawk 6X (Holybro), Cube Orange+ (CubePilot),
    Jetson Orin Nano + Baseboard (NXP, ARK) all use **2× 10-pin JST-GH**
    PWM OUT ports (FMU + IO, 8 channels each). novapcb is FMU-only so
    only the FMU port is implemented — 1× 10-pin JST-GH.
  - Pinout (Pixhawk 6X DS-002 / DS-009 FMU PWM OUT):
    | Pin | Net          | Role |
    |---:|--------------|------|
    | 1  | MOT1         | DShot ch 1 signal (3.3V logic) |
    | 2  | MOT2         | DShot ch 2 |
    | 3  | MOT3         | DShot ch 3 |
    | 4  | MOT4         | DShot ch 4 |
    | 5  | MOT5         | DShot ch 5 |
    | 6  | MOT6         | DShot ch 6 |
    | 7  | MOT7         | DShot ch 7 |
    | 8  | MOT8         | DShot ch 8 |
    | 9  | VDD_SERVO    | NC on novapcb (kept for harness compat — see below) |
    | 10 | GND          | Return |
  - **Pin 9 VDD_SERVO handling** — Pixhawk-standard pin for analog servo
    power injection (typically 5V from a separate BEC). novapcb runs
    DShot ESCs only (powered directly from main battery), so this rail
    is unused on the FC side. Pin kept physically present (10-pin
    connector matches harness mate) but **unconnected in SKiDL** —
    ERC will emit "unconnected pin" warning per project convention
    (see imu_3c.py:170 — explicit-NC is the accepted SKiDL 2.2.3
    pattern). Awaiting Sai sign-off on alternative (b: tie to GND for
    defined harness potential) — see PR doc.
  - Horizontal (right-angle / side-entry) variant: motor leads exit
    parallel to south board edge — same convention as other JST-GH
    connectors on this design.
  - Footprint: `Connector_JST:JST_GH_SM10B-GHS-TB_1x10-1MP_P1.25mm_Horizontal`
    (KiCad 9 stock).

Single connector ref **J11** (drops J12..J18 — those refs are now free
for future use). Schematic models the connector as
`Connector_Generic:Conn_01x10` for netlist clarity.

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


# ---- motor output connector (1× JST-GH 1x10 = Pixhawk 6X FMU PWM OUT) ----
# Single 10-pin JST-GH matching the Pixhawk 6X / Cube Orange+ / Jetson
# Baseboard PWM OUT port convention. Pin assignment (DS-002 / DS-009):
#   pin 1..8 = MOT1..MOT8 (DShot signal, 3.3V logic)
#   pin 9    = VDD_SERVO  (Pixhawk-standard pin for analog servo power;
#                          NC on novapcb — see "esc-connector-type fork"
#                          in docstring above; awaiting Sai sign-off
#                          NC-vs-tie-to-GND)
#   pin 10   = GND (return)
#
# Ref J11 (J1-J9 already in use: J1 USB-C, J2 microSD, J3 telem,
# J4 power, J5 GPS, J6 CAN/aux, J7 ESC1-4 stub, J8 ESC5-8 stub, J9 SWD).
# Earlier 8-per-motor topology (J11..J18) collapses to single J11; J12..J18
# refs are now free for future use.
esc_conn = Part(
    "Connector_Generic", "Conn_01x10",
    footprint="Connector_JST:JST_GH_SM10B-GHS-TB_1x10-1MP_P1.25mm_Horizontal",
    value="ESC_OUT",
)
esc_conn.ref = "J11"

for idx in range(1, 9):
    mot_nets[idx] += esc_conn[idx]   # pin 1..8 = MOT1..MOT8 signal

# pin 9 VDD_SERVO: NC — explicit no-bind per project SKiDL convention
# (imu_3c.py:170). ERC will emit "unconnected pin" warning — EXPECTED.
# If Sai ratifies (b) tie-to-GND: add `GND += esc_conn[9]` here.

GND += esc_conn[10]   # pin 10 = GND return
