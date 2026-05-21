#!/usr/bin/env python3
"""
R4-PREP step 1: define net classes + net→class assignments in .kicad_pro.

Per master directive 2026-05-21:
  Power / USB_diffpair / IMU_SPI / CAN / DShot / default

Each class sets track_width / via_diameter / via_drill / clearance per its
electrical needs. KiCad uses these as the DRC defaults; the corrected JLC
ruleset (jlcpcb.kicad_dru) adds JLC-specific manufacturability constraints
on top.

Class parameters (mm):

| Class        | Track | Via D / drill | Clearance | Notes |
|---|---|---|---|---|
| Default      | 0.20  | 0.46 / 0.20   | 0.20      | sized to JLC ruleset min (annular 0.13) |
| Power        | 0.50  | 0.80 / 0.40   | 0.25      | 2A continuous capacity in 1oz outer |
| USB_diffpair | 0.18  | 0.46 / 0.20   | 0.20      | 94.4Ω microstrip (Phase 6b SI sim) |
| IMU_SPI      | 0.20  | 0.46 / 0.20   | 0.25      | extra clearance for crosstalk margin |
| CAN          | 0.20  | 0.46 / 0.20   | 0.20      | differential pair geometry |
| DShot        | 0.30  | 0.60 / 0.30   | 0.20      | motor output high-current pulses |

Net→class assignment is by net-name PATTERN (KiCad's regex matching).
"""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PRO_FILE = os.path.join(HERE, "novapcb-layout-v1.1.kicad_pro")

# All values in mm.
CLASSES = [
    {
        "name": "Default",
        "track_width": 0.20,
        "via_diameter": 0.46,
        "via_drill": 0.20,
        "clearance": 0.20,
        "diff_pair_gap": 0.20,
        "diff_pair_width": 0.20,
        "diff_pair_via_gap": 0.20,
        "microvia_diameter": 0.30,
        "microvia_drill": 0.10,
        "wire_width": 6.0,
        "bus_width": 12.0,
        "pcb_color": "rgba(0, 0, 0, 0.000)",
        "schematic_color": "rgba(0, 0, 0, 0.000)",
        "line_style": 0,
        "priority": 2147483647,
    },
    {
        "name": "Power",
        "track_width": 0.50,
        "via_diameter": 0.80,
        "via_drill": 0.40,
        "clearance": 0.20,    # matches Default; width gives current capacity, not extra spacing
        "diff_pair_gap": 0.25,
        "diff_pair_width": 0.50,
        "diff_pair_via_gap": 0.25,
        "microvia_diameter": 0.30,
        "microvia_drill": 0.10,
        "wire_width": 6.0,
        "bus_width": 12.0,
        "pcb_color": "rgba(255, 100, 100, 1.000)",
        "schematic_color": "rgba(255, 100, 100, 1.000)",
        "line_style": 0,
        "priority": 1,
    },
    {
        "name": "USB_diffpair",
        "track_width": 0.18,
        "via_diameter": 0.46,
        "via_drill": 0.20,
        "clearance": 0.20,
        "diff_pair_gap": 0.15,
        "diff_pair_width": 0.18,
        "diff_pair_via_gap": 0.20,
        "microvia_diameter": 0.30,
        "microvia_drill": 0.10,
        "wire_width": 6.0,
        "bus_width": 12.0,
        "pcb_color": "rgba(100, 200, 255, 1.000)",
        "schematic_color": "rgba(100, 200, 255, 1.000)",
        "line_style": 0,
        "priority": 2,
    },
    {
        "name": "IMU_SPI",
        "track_width": 0.20,
        "via_diameter": 0.46,
        "via_drill": 0.20,
        "clearance": 0.20,    # matches Default; crosstalk-margin handled by routing (segregation + GND fill)
        "diff_pair_gap": 0.20,
        "diff_pair_width": 0.20,
        "diff_pair_via_gap": 0.20,
        "microvia_diameter": 0.30,
        "microvia_drill": 0.10,
        "wire_width": 6.0,
        "bus_width": 12.0,
        "pcb_color": "rgba(255, 200, 100, 1.000)",
        "schematic_color": "rgba(255, 200, 100, 1.000)",
        "line_style": 0,
        "priority": 3,
    },
    {
        "name": "CAN",
        "track_width": 0.20,
        "via_diameter": 0.46,
        "via_drill": 0.20,
        "clearance": 0.20,
        "diff_pair_gap": 0.20,
        "diff_pair_width": 0.20,
        "diff_pair_via_gap": 0.20,
        "microvia_diameter": 0.30,
        "microvia_drill": 0.10,
        "wire_width": 6.0,
        "bus_width": 12.0,
        "pcb_color": "rgba(150, 255, 150, 1.000)",
        "schematic_color": "rgba(150, 255, 150, 1.000)",
        "line_style": 0,
        "priority": 4,
    },
    {
        "name": "DShot",
        "track_width": 0.30,
        "via_diameter": 0.60,
        "via_drill": 0.30,
        "clearance": 0.20,
        "diff_pair_gap": 0.20,
        "diff_pair_width": 0.30,
        "diff_pair_via_gap": 0.20,
        "microvia_diameter": 0.30,
        "microvia_drill": 0.10,
        "wire_width": 6.0,
        "bus_width": 12.0,
        "pcb_color": "rgba(255, 100, 255, 1.000)",
        "schematic_color": "rgba(255, 100, 255, 1.000)",
        "line_style": 0,
        "priority": 5,
    },
]

# Net→class pattern assignments. KiCad's netclass_patterns uses regex.
PATTERNS = [
    # Power class — all power rails
    {"pattern": "GND",        "netclass": "Power"},
    {"pattern": "+3V3",       "netclass": "Power"},
    {"pattern": "+3V3A",      "netclass": "Power"},
    {"pattern": "+3V3_IMU",   "netclass": "Power"},
    {"pattern": "+3V3_IMU_PRE", "netclass": "Power"},
    {"pattern": "+5V",        "netclass": "Power"},
    {"pattern": "+5V_BEC",    "netclass": "Power"},
    {"pattern": "+5V_BEC_A",  "netclass": "Power"},
    {"pattern": "+5V_BEC_B",  "netclass": "Power"},
    {"pattern": "+5V_BEC_PROT", "netclass": "Power"},
    {"pattern": "VBAT",       "netclass": "Power"},
    {"pattern": "VREF_P",     "netclass": "Power"},
    {"pattern": "VCAP1",      "netclass": "Power"},
    {"pattern": "VCAP2",      "netclass": "Power"},

    # USB diff pair — controlled impedance
    {"pattern": "USB_DM",       "netclass": "USB_diffpair"},
    {"pattern": "USB_DP",       "netclass": "USB_diffpair"},
    {"pattern": "USBC_D_M_PRE", "netclass": "USB_diffpair"},
    {"pattern": "USBC_D_P_PRE", "netclass": "USB_diffpair"},

    # IMU SPI buses
    {"pattern": "SPI1_*",  "netclass": "IMU_SPI"},
    {"pattern": "SPI2_*",  "netclass": "IMU_SPI"},
    {"pattern": "SPI3_*",  "netclass": "IMU_SPI"},
    {"pattern": "IMU1_CS", "netclass": "IMU_SPI"},
    {"pattern": "IMU2_ACC_CS", "netclass": "IMU_SPI"},
    {"pattern": "IMU2_GYR_CS", "netclass": "IMU_SPI"},
    {"pattern": "IMU3_CS", "netclass": "IMU_SPI"},

    # CAN bus
    {"pattern": "CANH_NET", "netclass": "CAN"},
    {"pattern": "CANL_NET", "netclass": "CAN"},
    {"pattern": "CAN_TERM_MID", "netclass": "CAN"},

    # DShot / motor outputs — TIM2/3/4/5 channels going to ESC pads
    # (motor PWM net names follow MOT1..MOT8 or PWM1..PWM8 convention in hwdef;
    # here they are the J11..J18 ESC pad nets which need wider traces for current)
    # ESC pad net names from the netlist are "Net-(J11-Pad1)" style — regex matches that
    {"pattern": "Net-\\(J1[1-8]-Pad1\\)", "netclass": "DShot"},
]


def main():
    with open(PRO_FILE) as f:
        pro = json.load(f)

    ns = pro["net_settings"]
    ns["classes"] = CLASSES
    ns["netclass_patterns"] = PATTERNS
    # Clear netclass_assignments so patterns take effect (assignments override patterns)
    ns["netclass_assignments"] = {}

    with open(PRO_FILE, "w") as f:
        json.dump(pro, f, indent=2)

    print(f"Wrote {len(CLASSES)} net classes + {len(PATTERNS)} patterns to {os.path.basename(PRO_FILE)}")
    for c in CLASSES:
        print(f"  {c['name']:15s} track={c['track_width']:.2f}  via={c['via_diameter']:.2f}/{c['via_drill']:.2f}  clear={c['clearance']:.2f}")


if __name__ == "__main__":
    main()
