#!/usr/bin/env python3
"""openEMS coupled-pair limit-case validation (Task #75 from master).

Per master 2026-05-23: "Limit-case idea (openEMS at very large S
approaches 2×Z_se) is a sound validation — DO it, plus Pozar table
lookup if feasible."

Validation strategy:
  1. Run openEMS coupled-pair at SEVERAL S values, including very large.
  2. At large S (S/h >> 1), coupling vanishes → Z_diff → 2 × Z_se.
  3. Z_se = 67.32 Ω (from Task 9, validated to H-J within 3.6%).
  4. Expected Z_diff at S→∞ = 134.6 Ω.
  5. If openEMS sweeps converge toward this value at large S, the
     setup is validated.
  6. At our actual S=0.13 (USB diff pair), openEMS measured 87.4 Ω.

Geometry held constant: W=0.20mm, h=0.21mm, εr=4.3, t=0.035mm.
"""
import os
import sys
import math
import tempfile

# Reuse sim_usb_zdiff.py's openems_coupled but parameterize S
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim_usb_zdiff as sim

# Sweep S values
S_values_mm = [0.13, 0.50, 1.00, 2.00]   # tight → loose

def run_at_S(S_mm):
    """Re-run sim_usb_zdiff's openems_coupled with overridden S."""
    sim.S_mm = S_mm
    sim.S = S_mm * 1e-3
    try:
        Z_T1, Z_T2, Z_diff = sim.openems_coupled()
        return Z_diff
    except Exception as e:
        return None, str(e)

def hj_se():
    """Z_se from Hammerstad-Jensen — validated to H-J."""
    return sim.hj_single_ended()

def main():
    print("=== openEMS coupled-pair limit-case validation ===\n")
    print(f"Geometry: W={sim.W_mm}mm, h={sim.H_mm}mm, εr={sim.EpR}, t={sim.T_mm}mm")
    print(f"Sweep S over: {S_values_mm} mm\n")
    
    Z_se = hj_se()
    Z_2se = 2 * Z_se
    print(f"Z_se (H-J validated) = {Z_se:.2f} Ω")
    print(f"Expected Z_diff at S→∞: 2×Z_se = {Z_2se:.2f} Ω\n")
    
    print(f"{'S (mm)':<8} {'S/h':<8} {'Z_diff (Ω)':<14} {'vs 2Z_se (%)':<14}")
    for S in S_values_mm:
        result = run_at_S(S)
        if isinstance(result, tuple):
            print(f"{S:<8.3f} {S/sim.H_mm:<8.2f} FAILED: {result[1]}")
            continue
        Z = result
        err = (Z - Z_2se) / Z_2se * 100
        print(f"{S:<8.3f} {S/sim.H_mm:<8.2f} {Z:<14.2f} {err:+8.1f}%")
    
    print(f"\n=== Verdict ===")
    print(f"If Z_diff INCREASES toward {Z_2se:.0f} Ω as S grows, openEMS setup is")
    print(f"correctly modeling coupled-pair physics → 87.4 Ω at S=0.13 is trustworthy.")
    return 0

if __name__ == "__main__":
    main()
