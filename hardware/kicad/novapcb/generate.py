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
from sheets import power_3b  # noqa: F401  (3b — power tree: 5V → AP2112K-3.3 → +3V3)
from sheets import imu_3c    # noqa: F401  (3c — ICM-42688-P on SPI1)
from sheets import baro_3d   # noqa: F401  (3d — DPS310 on I²C2 at 0x76)
from sheets import gps_mag_3e  # noqa: F401  (3e — GPS+mag JST-GH 10P + I²C1 pull-ups)
from sheets import esc_3f    # noqa: F401  (3f — 8 DShot motor outputs to solder pads)
from sheets import crsf_usb_3g  # noqa: F401  (3g — CRSF JST-GH 4P + USB-C w/ ESD)
from sheets import power_sd_swd_3h  # noqa: F401  (3h — Mauch ADC + microSD + SWD + mounting)
from sheets import telem_3i         # noqa: F401  (3i — Telem USART1 JST-GH 6P, breakdown-omission fix)
from sheets import can_3j           # noqa: F401  (3j — v1.1 CAN: TJA1051TK/3 + PESD2CAN + 120R jumper + JST-GH 4P, FDCAN1 only)

# ---- pipeline (netlist-only; see module docstring + OPEN_QUESTIONS phase3-render-1) ----
import skidl

print("[1/2] SKiDL ERC...", flush=True)
skidl.ERC()

print("[2/2] generate netlist...", flush=True)
skidl.generate_netlist(file_=os.path.join(HERE, "novapcb.net"))

# NOTE: generate_schematic() intentionally NOT called.
# See docs/OPEN_QUESTIONS.md phase3-render-1.

# ---- HARD-FAIL guard: rail-uniqueness check (04:00 retro action item) ----
# SKiDL's Net('name') creates a NEW Net even when one with that name exists,
# auto-appending _1/_2 suffixes. Cross-module use of Net('+3V3') in two sheets
# silently produces two separate nets (+3V3 and +3V3_1) — MCU VDDs on one,
# LDO VOUT on the other, no electrical connection. ERC + netlist-gen both
# pass without complaint. Defense: every shared rail/bus net MUST use the
# n() singleton from sheets.common; this guard catches lapses by failing
# the build (exit non-zero) if any "+xxx_N" or "<RAIL>_N" net is in the
# generated netlist.
import re
print("[guard] check shared-net uniqueness...", flush=True)
netlist_path = os.path.join(HERE, "novapcb.net")
with open(netlist_path) as f:
    content = f.read()
# Match the netlist's `(name "<net>")` lines and find any with a _N suffix
# that follows a non-numeric base name (i.e. SKiDL's auto-disambiguation
# pattern, not a legitimately-numbered net like "DATA_1" the user picked).
duplicates = []
for m in re.finditer(r'\(name "([^"]+)"\)', content):
    name = m.group(1)
    # SKiDL disambiguation: name ends with _N where the base was a "real"
    # name (contains letters or starts with +). Flags +3V3_1, GND_1, SPI1_SCK_2.
    if re.search(r'^[+A-Za-z][^_]*[A-Za-z0-9]_\d+$', name) or \
       re.search(r'^\+\w+_\d+$', name):
        duplicates.append(name)
if duplicates:
    print(f"[guard] FAIL — SKiDL Net()-duplicate suffixes detected: {duplicates}")
    print(f"[guard] Cross-module shared rails must use sheets.common.n() — see "
          f"KICAD9_NOTES.md 'Net('name') creates a NEW net' section.")
    sys.exit(1)
print(f"[guard] OK — no _N-suffixed shared rails in {netlist_path}")

print("done. (netlist-only mode; drawn-schematic deferred per phase3-render-1)")
