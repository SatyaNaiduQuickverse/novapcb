#!/usr/bin/env python3
"""OpenEMS smoke-test — parallel-plate capacitor stored E-field.

Real FDTD simulation (not import-check). Configure a 10mm × 10mm × 1mm
parallel-plate capacitor in vacuum, apply DC bias 1V across plates, let the
field settle, measure E-field at the center. Compare to analytical:

  E_analytical = V / d = 1V / 1mm = 1000 V/m

PASS if |E_numerical - 1000| / 1000 < 5%.

Reports runtime (slow on Pi is fine).
"""
import os, sys, time
os.environ["LD_LIBRARY_PATH"] = os.path.expanduser("~/local/openems/lib") + ":" + os.environ.get("LD_LIBRARY_PATH","")
sys.path.insert(0, os.path.expanduser("~/local/openems/python"))

from CSXCAD import ContinuousStructure
from openEMS import openEMS
from openEMS.physical_constants import *
import numpy as np

SIM_PATH = "/tmp/openems_smoke"
os.makedirs(SIM_PATH, exist_ok=True)

# Parameters: 10mm × 10mm plates, 1mm gap, in vacuum
PLATE_W = 10  # mm
GAP = 1       # mm
F_MAX = 1e9   # Hz — drives mesh density (we don't care about HF here)

CSX = ContinuousStructure()
CSX.GetGrid().SetDeltaUnit(1e-3)  # mm units

# Lumped port between plates (creates the 1V bias)
FDTD = openEMS(NrTS=10000, EndCriteria=1e-4)
FDTD.SetCSX(CSX)
FDTD.SetGaussExcite(0.5e9, 0.5e9)
FDTD.SetBoundaryCond(["PML_8"]*6)

# Build the geometry: two plates + air box
plate_top = CSX.AddMetal("plate_top")
plate_top.AddBox(start=[-PLATE_W/2, -PLATE_W/2,  GAP/2], stop=[PLATE_W/2, PLATE_W/2, GAP/2])
plate_bot = CSX.AddMetal("plate_bot")
plate_bot.AddBox(start=[-PLATE_W/2, -PLATE_W/2, -GAP/2], stop=[PLATE_W/2, PLATE_W/2, -GAP/2])

# Lumped port between the two plates (centerline)
port = FDTD.AddLumpedPort(port_nr=1, R=50,
                          start=[0,0,-GAP/2], stop=[0,0,GAP/2], p_dir='z', excite=1.0)

# E-field probe at the geometric center (between the plates, on z-axis)
e_probe = CSX.AddDump("E_center", dump_type=0, dump_mode=2, file_type=1)  # 0=E-field, vtk
e_probe.AddBox([-1, -1, -0.1], [1, 1, 0.1])

# Mesh
mesh = CSX.GetGrid()
mesh.SetLines('x', np.linspace(-PLATE_W, PLATE_W, 30))
mesh.SetLines('y', np.linspace(-PLATE_W, PLATE_W, 30))
mesh.SetLines('z', np.linspace(-GAP*5, GAP*5, 30))
mesh.SmoothMeshLines('all', 0.5)

# Run
t0 = time.time()
FDTD.Run(SIM_PATH, verbose=2, cleanup=True)
elapsed = time.time() - t0
print(f"\n[openems-smoke] runtime: {elapsed:.1f}s")

# Read the E-field probe — find max |E_z| at center over time
import glob, os
vtk_files = sorted(glob.glob(f"{SIM_PATH}/E_center_*.vtk"))
if not vtk_files:
    print("[openems-smoke] FAIL — no E-field dumps")
    sys.exit(1)

# Parse the last vtk for steady-state E_z at center
import re
peak_Ez = 0.0
for vf in vtk_files[-5:]:
    with open(vf) as f:
        txt = f.read()
    m = re.search(r"VECTORS\s+\S+\s+\S+\s*\n((?:[-+\d.eE\s]+\n)+)", txt)
    if not m: continue
    vals = [float(v) for v in m.group(1).split()]
    # Vectors are (Ex,Ey,Ez) triples; take Ez (every 3rd starting at index 2)
    ezs = vals[2::3]
    peak_Ez = max(peak_Ez, max(abs(e) for e in ezs) if ezs else 0.0)

# 1V across 1mm = 1000 V/m
expected = 1000.0
err_pct = abs(peak_Ez - expected) / expected * 100
status = "PASS" if err_pct < 5.0 else "FAIL"
print(f"[openems-smoke] |E_z| at center: {peak_Ez:.1f} V/m  (expected ~1000)")
print(f"[openems-smoke] error: {err_pct:.2f}%  → {status}")
sys.exit(0 if status == "PASS" else 1)
