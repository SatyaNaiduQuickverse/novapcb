#!/usr/bin/env python3
"""gate12 architecture sweep — 3 configurations for Sai decision doc.

Per master 2026-05-23 directive: quantify the recommendation with actual
numbers, not just 'achievable'.

  A. 115×100mm + LDO (642mW)        — bigger board alone
  B. 105×85mm + buck (25mW for U2)  — schematic change alone
  C. 110×90mm + buck (25mW for U2)  — both, master recommendation

All sweeps use ACTUAL component positions from current board (Q3 at 27,10
etc), NOT the planned positions that gave the LOCK 73.98 artifact.
"""
import os, sys, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate12_thermal as g12
import pcbnew

PCB = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "novapcb-stepwise.kicad_pcb")
brd = pcbnew.LoadBoard(PCB)
sources_LDO = g12.get_active_heat_sources(brd)

# Buck variant: clone source list, replace U2's power
sources_BUCK = []
for s in sources_LDO:
    if s.name == "U2":
        sources_BUCK.append(g12.HeatSource(
            name=s.name, x_mm=s.x_mm, y_mm=s.y_mm,
            body_x_mm=s.body_x_mm, body_y_mm=s.body_y_mm,
            power_W=0.025,  # TPS62177 buck at ~85% efficiency → 25mW vs LDO 642mW
        ))
    else:
        sources_BUCK.append(s)

configs = [
    ("A. 115×100 + LDO", sources_LDO, 0.115, 0.100, "swp_A_115_LDO"),
    ("B. 105×85 + buck", sources_BUCK, 0.105, 0.085, "swp_B_105_BUCK"),
    ("C. 110×90 + buck", sources_BUCK, 0.110, 0.090, "swp_C_110_BUCK"),
]

print("=== gate12 architecture sweep for Sai ===\n")
results = []
for label, srcs, L, W, case in configs:
    P_tot = sum(s.power_W for s in srcs) * 1000
    print(f"\n--- {label}  (board {L*1000:.0f}×{W*1000:.0f}, P={P_tot:.0f}mW) ---")
    r = g12.run(srcs, board_L_m=L, board_W_m=W, case_label=case)
    if "error" in r:
        print(f"  ERROR: {r['error']}")
        continue
    eb = r["energy_balance"]
    print(f"  Energy balance: {eb['rel_err_pct']:+.2f}% {'PASS' if eb['pass'] else 'FAIL'}")
    case_dir = os.path.join(g12.CASE_DIR, case)
    Tj_data = {}
    for s in srcs:
        Tj = g12.sample_Tj(case_dir, s)
        margin = g12.T_J_TARGET_C - Tj
        Tj_data[s.name] = (Tj, margin)
        print(f"  Tj_{s.name:<6} = {Tj:.2f}°C  margin {margin:+.1f}°C  {'PASS' if margin>0 else 'FAIL'}")
    results.append((label, L*1000, W*1000, P_tot, Tj_data))

print("\n=== Summary table for Sai decision doc ===\n")
print(f"{'Config':<22} {'Size':<10} {'P_tot':<8} {'MCU':<8} {'U6':<8} {'Q3':<8} {'Q4':<8} {'U2':<8}")
print("-" * 90)
for label, L, W, P, Tj in results:
    line = f"{label:<22} {L:.0f}×{W:.0f}      {P:.0f}mW"
    for k in ("U1", "U6", "Q3", "Q4", "U2"):
        if k in Tj:
            t, m = Tj[k]
            line += f" {t:.1f}({m:+.1f})"
        else:
            line += "    -    "
    print(line)
