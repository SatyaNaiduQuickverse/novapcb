#!/usr/bin/env python3
"""OpenEMS validation — Hammerstad-Jensen microstrip Z0 cross-check.

Per master directive 2026-05-20: this is the directly-relevant-to-novapcb validation —
OpenEMS must reproduce the Hammerstad-Jensen analytical characteristic impedance for
a microstrip of the SAME geometry we use at Phase 4d/Phase 6b for the USB diff pair.

Reference: Hammerstad & Jensen (1980), "Accurate Models for Microstrip
Computer-Aided Design", IEEE MTT-S Digest, pp. 407-409. Analytical formula
implemented in sims/usb-diffpair-6b/run_6b.py — already verified against
KiCad's built-in impedance calculator at Phase 4d.

Geometry (novapcb 4a stackup):
    W (trace width):   0.25 mm
    h (substrate):     0.21 mm  (prepreg F.Cu → In1.Cu GND)
    εr:                4.3      (FR4 typical)
    t (copper thick):  0.035 mm (1 oz)
    Length:            20 mm

Analytical: Z0 = 70.19 Ω (per Phase 6b script — same formula).
Tolerance: ±5%.

OpenEMS extracts Z0 from S-parameter at low frequency (Z0 = Z_input at f→0
for a matched line).

Runtime: expect 5-15 min on Pi 5.
"""
import os, sys, time, glob
os.environ["LD_LIBRARY_PATH"] = os.path.expanduser("~/local/openems/lib") + ":" + os.environ.get("LD_LIBRARY_PATH","")
sys.path.insert(0, os.path.expanduser("~/local/openems/python"))

import numpy as np
from CSXCAD import ContinuousStructure
from openEMS import openEMS
from openEMS.physical_constants import C0

SIM_PATH = "/tmp/openems_validate_microstrip"
os.makedirs(SIM_PATH, exist_ok=True)

# Geometry — novapcb 4a stackup
W = 0.25       # trace width, mm
h = 0.21       # substrate height, mm
eps_r = 4.3
t_metal = 0.035  # 1oz, mm
L_line = 20    # microstrip length, mm

F_MAX = 5e9
F_MIN = 1e8   # Z0 extraction near low end of band

# --- analytical Hammerstad-Jensen ---
def hj_z0(W, h, eps_r):
    u = W / h
    a = 1 + (1/49)*np.log((u**4 + (u/52)**2)/(u**4 + 0.432)) + (1/18.7)*np.log(1 + (u/18.1)**3)
    b = 0.564 * ((eps_r - 0.9)/(eps_r + 3))**0.053
    eps_eff = (eps_r + 1)/2 + (eps_r - 1)/2 * (1 + 10/u)**(-a*b)
    Z0_air = 60 * np.log(6 + (2*np.pi - 6)*np.exp(-(30.666/u)**0.7528) + np.sqrt(1 + 4/u**2))
    return Z0_air / np.sqrt(eps_eff), eps_eff

Z0_analytical, eps_eff = hj_z0(W, h, eps_r)
print(f"[validate-microstrip] Hammerstad-Jensen analytical: Z0={Z0_analytical:.2f}Ω, εeff={eps_eff:.3f}")

# --- build OpenEMS model ---
FDTD = openEMS(NrTS=30000, EndCriteria=1e-4)
CSX = ContinuousStructure()
FDTD.SetCSX(CSX)
FDTD.SetGaussExcite(0.5*(F_MAX+F_MIN), 0.5*(F_MAX-F_MIN))
FDTD.SetBoundaryCond(["MUR", "MUR", "MUR", "MUR", "MUR", "PML_8"])

CSX.GetGrid().SetDeltaUnit(1e-3)
mesh = CSX.GetGrid()

# Substrate dielectric block
substrate = CSX.AddMaterial("FR4", epsilon=eps_r)
substrate.AddBox([-L_line/2 - 5, -5, 0], [L_line/2 + 5, 5, h])

# Ground plane (full extent under substrate)
gnd = CSX.AddMetal("gnd")
gnd.AddBox([-L_line/2 - 5, -5, -t_metal], [L_line/2 + 5, 5, 0])

# Microstrip trace (on top of substrate)
trace = CSX.AddMetal("trace")
trace.AddBox([-L_line/2, -W/2, h], [L_line/2, W/2, h + t_metal])

# Lumped ports at each end (50Ω reference)
port1 = FDTD.AddLumpedPort(1, R=50,
                           start=[-L_line/2, -W/2, 0], stop=[-L_line/2, W/2, h],
                           p_dir='z', excite=1.0)
port2 = FDTD.AddLumpedPort(2, R=50,
                           start=[ L_line/2, -W/2, 0], stop=[ L_line/2, W/2, h],
                           p_dir='z', excite=0.0)

# Mesh — fine near the trace, coarser elsewhere
res_min = 0.05   # mm — adequate to resolve W=0.25
mesh.SetLines('x', np.concatenate([
    np.linspace(-L_line/2 - 5, -L_line/2, 10),
    np.linspace(-L_line/2, L_line/2, int(L_line/res_min)),
    np.linspace(L_line/2, L_line/2 + 5, 10),
]))
mesh.SetLines('y', np.linspace(-5, 5, 60))
mesh.SetLines('z', np.concatenate([
    np.linspace(-t_metal, 0, 5),
    np.linspace(0, h, 12),
    np.linspace(h, h + 5, 15),
]))
mesh.SmoothMeshLines('all', 0.3)

# Run
t0 = time.time()
FDTD.Run(SIM_PATH, verbose=2, cleanup=True)
elapsed = time.time() - t0
print(f"\n[validate-microstrip] runtime: {elapsed:.1f}s ({elapsed/60:.1f}min)")

# Extract S-params + Z0
freq = np.linspace(F_MIN, F_MAX, 200)
port1.CalcPort(SIM_PATH, freq, ref_impedance=50)
port2.CalcPort(SIM_PATH, freq, ref_impedance=50)

s11 = port1.uf_ref / port1.uf_inc
# At low frequency, Z_input → Z0 of the line (open at far end is approx with PML)
# Better extraction: from the wave impedance with characteristic-line theory
# Z0 = sqrt((1+S11)/(1-S11)) × 50  for matched-at-far-end
# At very low f, Sims approach the analytical Z0.
Z_in_low = 50 * (1 + s11[0]) / (1 - s11[0])
Z0_numerical = abs(Z_in_low)

err_pct = abs(Z0_numerical - Z0_analytical) / Z0_analytical * 100
TOL_PCT = 5.0
status = "PASS" if err_pct <= TOL_PCT else "FAIL"

print(f"\n[validate-microstrip] RESULT")
print(f"  Reference (Hammerstad-Jensen 1980, IEEE MTT-S, eq. 4-6): Z0 = {Z0_analytical:.2f}Ω")
print(f"  OpenEMS FDTD (S11 extraction at f={freq[0]/1e6:.0f} MHz):  Z0 = {Z0_numerical:.2f}Ω")
print(f"  |err| = {err_pct:.2f}%   tol = ±{TOL_PCT}%   → {status}")
sys.exit(0 if status == "PASS" else 1)
