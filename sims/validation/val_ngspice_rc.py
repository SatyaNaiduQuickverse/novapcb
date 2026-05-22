#!/usr/bin/env python3
"""Ngspice RC transient validation against analytical V(t) = V0*(1-exp(-t/RC)).

Reference: V(τ=RC) = 0.632121 V0 (textbook).
Tool: ngspice direct via subprocess.
"""
import subprocess, os, re

NETLIST = """RC charge transient validation
V1 in 0 PULSE(0 1 0 1e-9 1e-9 10 20)
R1 in out 1k
C1 out 0 1u
.ic V(out)=0
.tran 1e-6 5e-3 UIC
.print tran V(out)
.end
"""

ref_voltage_at_tau = 0.632121
tau = 1e-3   # R=1k, C=1u → RC=1ms

with open("/tmp/val_rc.cir", "w") as f: f.write(NETLIST)

# Run ngspice batch
result = subprocess.run(["ngspice", "-b", "/tmp/val_rc.cir"],
                          capture_output=True, text=True, timeout=30)
output = result.stdout

# Parse "<index>\t<time>\t<V(out)>" data rows, find closest to tau=1e-3
v_at_tau, t_at_tau, best_dt = None, None, 1e9
for line in output.split("\n"):
    parts = line.split()
    if len(parts) < 3: continue
    try:
        idx = int(parts[0]); t = float(parts[1]); v = float(parts[2])
    except ValueError:
        continue
    dt = abs(t - tau)
    if dt < best_dt:
        best_dt = dt; v_at_tau = v; t_at_tau = t

print(f"=== ngspice RC transient validation ===")
print(f"Test: V_in=1V, R=1kΩ, C=1µF → τ=1ms")
print(f"Reference V(τ) = {ref_voltage_at_tau:.6f} V (analytical)")
if v_at_tau is not None:
    error = abs(v_at_tau - ref_voltage_at_tau) / ref_voltage_at_tau * 100
    print(f"ngspice  V(τ) = {v_at_tau:.6f} V")
    print(f"Error   = {error:.4f}%")
    verdict = "PASS" if error < 1.0 else "FAIL"
    print(f"Verdict: {verdict} (criterion <1% error)")
else:
    print(f"!! Could not parse V(τ) from ngspice output")
    print("Sample output:\n" + output[-500:])
