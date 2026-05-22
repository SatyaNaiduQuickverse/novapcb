#!/usr/bin/env python3
"""openEMS single-line Z₀ at W=0.20mm (Task #79).

Master 2026-05-23 refinement: primary limit-case target = 2×openEMS-
single-line at SAME GEOMETRY as the coupled pair (W=0.20). Task 9
validated openEMS at W=0.30 (53.99 Ω vs H-J 56.01 Ω, 3.6%). Need
single-line at W=0.20 to match the coupled-pair sweep — provides
cleaner primary target than 2×H-J (134.6 Ω) secondary cross-check.
"""
import os, sys, tempfile
import numpy as np
from CSXCAD import ContinuousStructure
from openEMS import openEMS
from openEMS.physical_constants import C0

W_mm = 0.20
H_mm = 0.21
T_mm = 0.035
EpR  = 4.3

W = W_mm * 1e-3
H = H_mm * 1e-3
T = T_mm * 1e-3

unit = 1e-3
MSL_LEN = 25.0
f_max = 2e9
NRTS = 30000

Sim_Path = os.path.join(tempfile.gettempdir(), "openems_single_w020")
os.makedirs(Sim_Path, exist_ok=True)
for fn in os.listdir(Sim_Path):
    p = os.path.join(Sim_Path, fn)
    if os.path.isfile(p): os.remove(p)

FDTD = openEMS(NrTS=NRTS, EndCriteria=1e-4)
FDTD.SetGaussExcite(f_max/2, f_max/2)
FDTD.SetBoundaryCond(['PML_8','PML_8','MUR','MUR','PEC','MUR'])

CSX = ContinuousStructure()
FDTD.SetCSX(CSX)
mesh = CSX.GetGrid()
mesh.SetDeltaUnit(unit)

res_far = C0/(f_max * np.sqrt(EpR))/unit/30
dy_strip = W_mm / 8.0

dx = 0.5
mesh.AddLine('x', np.arange(-MSL_LEN, MSL_LEN + dx/2, dx))

# Single trace at Y=0
y_fine = np.arange(-W_mm/2 - 1.0, W_mm/2 + 1.0 + dy_strip/2, dy_strip)
mesh.AddLine('y', y_fine)
mesh.AddLine('y', [-10.0, 10.0])
mesh.SmoothMeshLines('y', res_far)

mesh.AddLine('z', np.linspace(0, H_mm, 6))
mesh.AddLine('z', np.array([0.5, 1.0, 2.0, 4.0]))
mesh.SmoothMeshLines('z', res_far)

substrate = CSX.AddMaterial('FR4', epsilon=EpR)
substrate.AddBox([-MSL_LEN, -10.0, 0], [MSL_LEN, 10.0, H_mm])
pec = CSX.AddMetal('PEC')

# Excited port (left) + terminated port (right)
FEED_SHIFT = 2.0
MEAS_SHIFT = 15.0
port_l = FDTD.AddMSLPort(1, pec,
    [-MSL_LEN, -W_mm/2, H_mm], [0, W_mm/2, 0],
    'x', 'z', excite=1, FeedShift=FEED_SHIFT, Feed_R=50,
    MeasPlaneShift=MEAS_SHIFT, priority=10)
port_r = FDTD.AddMSLPort(2, pec,
    [MSL_LEN, -W_mm/2, H_mm], [0, W_mm/2, 0],
    'x', 'z', Feed_R=50, MeasPlaneShift=MEAS_SHIFT, priority=10)

print(f"Running openEMS single-line at W={W_mm}mm (NrTS={NRTS})...", flush=True)
FDTD.Run(Sim_Path, cleanup=True, verbose=1)

f_test = np.array([0.5e9, 1.0e9, 1.5e9])
port_l.CalcPort(Sim_Path, f_test)
Z = abs(port_l.Z_ref)
for f, z in zip(f_test, Z):
    print(f"  f = {f/1e9:.1f} GHz: Z_se = {z:.3f} Ω")
print(f"\nZ_se @ 1 GHz = {Z[1]:.3f} Ω")
print(f"2 × Z_se     = {2*Z[1]:.3f} Ω  ← primary limit target")
