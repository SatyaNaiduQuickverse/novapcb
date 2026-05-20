#!/usr/bin/env python3
"""
novapcb top-level SKiDL assembler — netlist-only mode (Phase 3a-3 Rule-13).

Imports each sheet module in order, then runs SKiDL ERC + generates the
netlist. The drawn schematic (.kicad_sch / PDF) is INTENTIONALLY NOT
generated per-sub-phase: SKiDL `generate_schematic()` does not scale to
the MCU sheet (hangs on auto-router; P0 smoke test was 2-component only,
under-validated this). The drawn-schematic rendering is tracked as
docs/OPEN_QUESTIONS.md `phase3-render-1` — dedicated investigation +
resolution before Phase 6.5 forum review (NOT blocking Phase 3.5/4/5/6,
which consume the netlist directly).

Usage:
    python3 generate.py

Produces (in this directory):
    novapcb.net           — KiCad netlist (load-bearing artifact for Phase 4)
    generate.erc          — SKiDL ERC report
    generate.log          — SKiDL build log (also has tag warnings, harmless)
    generate_sklib.py     — SKiDL library cache (gitignored)
"""

import os
import sys

# Make sheets/ importable regardless of CWD.
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# common.setup() runs at import-time inside each sheet module; this also
# triggers the SKiDL backend selection. Importing the MCU sheet declares U1 + nets.
from sheets.common import setup
setup()

# ---- import each sheet in order ----
# Sheet imports are side-effecting: declaring Part() / Net() instances adds
# them to SKiDL's default Circuit. Adding a new sheet = add an import here.
from sheets import mcu_3a   # noqa: F401  (3a — MCU + clock + reset + decoupling)
# from sheets import power_3b  # 3b — power tree (to land after 3a merges)
# from sheets import imu_3c    # 3c — ICM-42688-P
# from sheets import baro_3d   # 3d — DPS310
# from sheets import gps_3e    # 3e — GPS+mag JST-GH 10P
# from sheets import esc_3f    # 3f — 8 ESC outputs
# from sheets import crsf_usb_3g  # 3g — CRSF UART + USB-C
# from sheets import power_mon_sd_swd_3h  # 3h — Mauch ADC + microSD + SWD + mounting

# ---- pipeline (netlist-only; see module docstring + OPEN_QUESTIONS phase3-render-1) ----
import skidl

print("[1/2] SKiDL ERC...", flush=True)
skidl.ERC()

print("[2/2] generate netlist...", flush=True)
skidl.generate_netlist(file_=os.path.join(HERE, "novapcb.net"))

# NOTE: generate_schematic() intentionally NOT called.
# See docs/OPEN_QUESTIONS.md phase3-render-1.

print("done. (netlist-only mode; drawn-schematic deferred per phase3-render-1)")
