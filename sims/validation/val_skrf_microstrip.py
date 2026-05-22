#!/usr/bin/env python3
"""scikit-rf microstrip Z0 validation against IPC-2141 + Hammerstad-Jensen.

Test case: W=0.30mm, h=0.21mm, εr=4.3, t=35µm (1oz Cu)
"""
import skrf as rf
import math
from skrf.media import MLine

# scikit-rf MLine
freq = rf.Frequency(start=1, stop=1, npoints=1, unit='GHz')
W, H, T, EpR = 0.30e-3, 0.21e-3, 35e-6, 4.3
ms = MLine(frequency=freq, w=W, h=H, t=T, ep_r=EpR)
Z0_tool = ms.z0.real[0]

# IPC-2141 (most common engineering reference for microstrip):
# Z0 = 87/sqrt(εr+1.41) * ln(5.98h/(0.8W+t))   for W < 2h
Z0_ipc = 87/math.sqrt(EpR+1.41) * math.log(5.98*H/(0.8*W + T))

# Hammerstad-Jensen 1980 (with thickness correction):
# Effective W (Hammerstad):
W_eff = W + (T/math.pi) * (1 + math.log(2*H/T))
# εr_eff
e_eff = (EpR + 1)/2 + (EpR - 1)/2 * (1 + 12*H/W_eff)**(-0.5)
# Z0
if W_eff/H <= 1:
    Z0_hj = 60/math.sqrt(e_eff) * math.log(8*H/W_eff + W_eff/(4*H))
else:
    Z0_hj = 120*math.pi/math.sqrt(e_eff) / (W_eff/H + 1.393 + 0.667*math.log(W_eff/H+1.444))

# Wheeler 1965 (Wheeler's first formula — older but widely cited):
Z0_wh = 60/math.sqrt(EpR) * math.log(8*H/W + W/(4*H))

print(f"=== scikit-rf microstrip Z0 validation ===")
print(f"Geometry: W={W*1e3:.2f}mm, h={H*1e3:.2f}mm, t={T*1e6:.0f}µm, εr={EpR}")
print(f"")
print(f"Analytical references (multiple formulas):")
print(f"  IPC-2141                    = {Z0_ipc:.2f} Ω")
print(f"  Hammerstad-Jensen 1980     = {Z0_hj:.2f} Ω (with thickness)")
print(f"  Wheeler 1965               = {Z0_wh:.2f} Ω (lossless, no thickness)")
print(f"")
print(f"scikit-rf MLine             = {Z0_tool:.2f} Ω")
print(f"")
# Compare scikit-rf vs IPC-2141 (the standard engineering reference)
err = abs(Z0_tool - Z0_ipc) / Z0_ipc * 100
err_hj = abs(Z0_tool - Z0_hj) / Z0_hj * 100
print(f"Error vs IPC-2141: {err:.2f}%")
print(f"Error vs H-J 1980: {err_hj:.2f}%")
verdict = "PASS" if max(err, err_hj) < 5.0 else "FAIL"
print(f"Verdict: {verdict} (criterion <5% vs analytical)")
