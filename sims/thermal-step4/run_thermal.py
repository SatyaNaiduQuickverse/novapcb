#!/usr/bin/env python3
"""
Step 4 thermal FEA — Elmer 3D heat-conduction validation of the Step 3 P1
placement (novapcb-layout-v2: 62×42 mm 6-layer).

Per master 2026-05-21 directive: validate the placement against the physics.
PLACEMENT_STRATEGY predicted AP2112K LDO Tj ≤ 80°C at 50°C ambient with the
6-layer thermal pour. This FEA either confirms that or surfaces an
iteration target.

## Model

- 3D domain: 62 × 42 × 1.6 mm box (board)
- Effective in-plane k: anisotropic via copper-stack ratio (mostly Cu-dominated
  in plane, FR4-dominated through-plane)
- Heat sources: localized power deposit at component locations per
  THERMAL_BUDGET.md §1 (only U2 LDO + U1 MCU material; others < 1% of total
  and folded into ambient heating)
- Boundary conditions: natural-convection on top + bottom faces
  (h = 5 W/m²·K each surface, T_ambient = 50°C); adiabatic edges
- Steady-state solve

## Outputs

  Tj_LDO_C, Tj_MCU_C, T_board_avg_C, T_board_max_C
  results.json + plots
  validation report (PASS / FAIL vs PLACEMENT_STRATEGY prediction)

## Reproducibility

  python3 run_thermal.py
  (requires: ~/local/elmer/bin in PATH or this script's wrappers)
"""

import os
import sys
import subprocess
import json
from pathlib import Path

HERE = Path(__file__).parent.resolve()
WORK = HERE / "runs"
WORK.mkdir(parents=True, exist_ok=True)

ELMER_BIN = Path.home() / "local/elmer/bin"

# ---------- physical model parameters ----------

# Board geometry (m) — Sai Path B grown board (was 0.062 × 0.042 = 2604 mm²)
BOARD_L = 0.080   # X long axis (was 0.062 → +37%)
BOARD_W = 0.060   # Y short axis (was 0.042 → +48%)
BOARD_H = 0.0016  # Z thickness (1.6 mm)

# Materials — effective board thermal conductivity
# 6-layer stackup (JLC06161H): L1 1oz + L2 4oz + L3 4oz + L4 4oz + L5 4oz + L6 1oz
# Total Cu = 35+140+140+140+140+35 = 630 µm of Cu in 1600 µm total
# Per THERMAL_BUDGET §3.1: k_Cu = 401, k_FR4_inplane = 0.81, k_FR4_through = 0.29
# In-plane: parallel-paths rule of mixtures
#   k_xy = (t_Cu / t_total) × k_Cu + (t_FR4 / t_total) × k_FR4_inplane
#         = (630/1600) × 401 + (970/1600) × 0.81
#         = 0.394 × 401 + 0.606 × 0.81 = 158.0 + 0.49 = 158.5 W/m·K
# Through-plane: series rule (resistors in series)
#   k_z = t_total / (t_Cu / k_Cu + t_FR4 / k_FR4_through)
#       = 1.6e-3 / (0.63e-3/401 + 0.97e-3/0.29)
#       = 1.6e-3 / (1.57e-6 + 3.345e-3) ≈ 1.6e-3 / 3.347e-3 = 0.478 W/m·K
# Elmer doesn't directly accept anisotropic k via "Heat Conductivity";
# need to use full tensor form. For simplicity (first-pass), use the geometric
# mean of in-plane + through-plane:
#   k_eff = (k_xy² × k_z)^(1/3) = (158.5² × 0.478)^(1/3) = (12003)^(1/3) = 22.9 W/m·K
# This understates lateral spreading (real k_xy = 158 is much higher) but
# also undestates through-plane impedance. Acceptable for first-pass model;
# Phase 6.5 forum review or a more detailed model can refine.
K_XY = 33.5  # in-plane (real JLC06161H: 0.131mm Cu / 1.469mm FR4 parallel)
K_Z = 0.316  # through-plane (series rule)
RHO = 2500          # kg/m³ (board avg)
CP = 800            # J/kg·K (board avg)

# Convection
H_CONV = 5.0
T_AMBIENT = 50.0    # °C (drone-bay worst case per master 2026-05-21)

# Heat sources (W) and locations (m) — coordinates from current PLACEMENT
# in generate_board.py for the 85×62 grown board.
HEAT_SOURCES = {
    "U2_LDO":  {"x_mm": 10.0, "y_mm": 33.5, "footprint_mm": (2.5, 3.0),  "power_W": 0.595},
    "U1_MCU":  {"x_mm": 39.53, "y_mm": 30.00, "footprint_mm": (14.0, 14.0), "power_W": 0.700},
    "U6_eFuse": {"x_mm": 12.24, "y_mm": 21.29, "footprint_mm": (3.0, 4.0),  "power_W": 0.018},
    "Q2_PFET":  {"x_mm": 10.35, "y_mm": 13.55, "footprint_mm": (3.0, 1.5),  "power_W": 0.0065},
}

# ---------- mesh ----------

# Hex mesh resolution — 2 mm per cell (~consistent with prior baseline)
N_X = 40    # 85 mm / 43 ≈ 2 mm per cell
N_Y = 30    # 62 mm / 31 = 2 mm per cell
N_Z = 4     # 1.6 mm / 4 = 0.4 mm per cell

def make_grd():
    """Generate ElmerGrid .grd input for a 3D box mesh.

    Format: single 1×1×1 subcell with Subcell Sizes = full board dimensions,
    subdivided into N_X × N_Y × N_Z hex elements via Element Divisions.
    """
    return f"""\
##### ElmerGrid input: novapcb 62×42×1.6 mm 6-layer board #####
Version = 210903
Coordinate System = Cartesian 3D
Subcell Divisions in 3D = 1 1 1
Subcell Sizes 1 = {BOARD_L}
Subcell Sizes 2 = {BOARD_W}
Subcell Sizes 3 = {BOARD_H}
Material Structure in 2D
  1
End
Materials Interval = 1 1
Boundary Definitions
# type     out      int     edge
  1        -1        1        1
  2        -2        1        1
  3        -3        1        1
  4        -4        1        1
End
Numbering = Horizontal
Element Degree = 1
Element Innernodes = False
Triangles = False
Element Divisions 1 = {N_X}
Element Divisions 2 = {N_Y}
Element Divisions 3 = {N_Z}
"""

def make_sif():
    """Generate Elmer SIF for steady-state heat conduction with body sources
    + convection BCs.

    Heat source expressed as a Variable Coordinate body force using MATC:
    each component's footprint contributes its W/m³ within its rectangular
    bounding box.
    """
    # Build MATC heat-source expression.
    # IMPORTANT: Elmer Heat Equation expects "Heat Source" in W/kg
    # (volumetric source = ρ · Heat Source). Convert q_vol [W/m³] to
    # W/kg by dividing by RHO.
    src_pieces = []
    for name, hs in HEAT_SOURCES.items():
        x = hs["x_mm"] / 1000.0  # convert to m
        y = hs["y_mm"] / 1000.0
        w_x = hs["footprint_mm"][0] / 1000.0
        w_y = hs["footprint_mm"][1] / 1000.0
        vol = w_x * w_y * BOARD_H
        q_vol = hs["power_W"] / vol       # W/m³
        q_mass = q_vol / RHO              # W/kg (Elmer units)
        cond = (f"if (abs(tx(0)-{x:.5f})<{w_x/2:.5f} & "
                f"abs(tx(1)-{y:.5f})<{w_y/2:.5f}) q=q+{q_mass:.3e};")
        src_pieces.append(cond)
    matc = "q=0; " + " ".join(src_pieces) + " q"

    return f"""\
Header
  Mesh DB "." "novapcb_thermal"
End

Simulation
  Coordinate System = "Cartesian 3D"
  Simulation Type = Steady State
  Steady State Max Iterations = 30
  Output File = "novapcb_thermal.result"
  Post File = "novapcb_thermal.vtu"
  Output Intervals = 1
End

Body 1
  Equation = 1
  Material = 1
  Body Force = 1
End

Equation 1
  Active Solvers(1) = 1
End

Solver 1
  Equation = "Heat Equation"
  Variable = "Temperature"
  Procedure = "HeatSolve" "HeatSolver"
  Linear System Solver = "Iterative"
  Linear System Iterative Method = "BiCGStab"
  Linear System Max Iterations = 500
  Linear System Convergence Tolerance = 1.0e-9
  Linear System Preconditioning = "ILU0"
  Steady State Convergence Tolerance = 1.0e-7
End

Material 1
  Density = {RHO}
  Heat Conductivity(3) = {K_XY} {K_XY} {K_Z}
  Heat Capacity = {CP}
End

Body Force 1
  Heat Source = Variable Coordinate
    Real MATC "{matc}"
End

Boundary Condition 1
  Name = "X- edge (adiabatic)"
  Target Boundaries(1) = 1
End

Boundary Condition 2
  Name = "X+ edge (adiabatic)"
  Target Boundaries(1) = 2
End

Boundary Condition 3
  Name = "Y- edge (adiabatic)"
  Target Boundaries(1) = 3
End

Boundary Condition 4
  Name = "Y+ edge (adiabatic)"
  Target Boundaries(1) = 4
End

Boundary Condition 5
  Name = "Z- bottom (convection to ambient)"
  Target Boundaries(1) = 5
  Heat Transfer Coefficient = {H_CONV}
  External Temperature = {T_AMBIENT}
End

Boundary Condition 6
  Name = "Z+ top (convection to ambient)"
  Target Boundaries(1) = 6
  Heat Transfer Coefficient = {H_CONV}
  External Temperature = {T_AMBIENT}
End
"""

def run_elmer():
    """Run the FEA pipeline: ElmerGrid → ElmerSolver → parse VTU."""
    case_dir = WORK / "case_h5"
    case_dir.mkdir(parents=True, exist_ok=True)

    (case_dir / "novapcb_thermal.grd").write_text(make_grd())
    (case_dir / "novapcb_thermal.sif").write_text(make_sif())
    (case_dir / "ELMERSOLVER_STARTINFO").write_text("novapcb_thermal.sif\n")

    env = os.environ.copy()
    env["PATH"] = f"{ELMER_BIN}:" + env.get("PATH", "")

    print(f"[1/3] mesh", flush=True)
    r = subprocess.run(["ElmerGrid", "1", "2", "novapcb_thermal.grd"],
                       cwd=case_dir, env=env, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"ERROR mesh:\n{r.stdout}\n{r.stderr}")
        return None

    print(f"[2/3] solve (h_conv={H_CONV} W/m²K, T_amb={T_AMBIENT} °C)", flush=True)
    r = subprocess.run(["ElmerSolver"],
                       cwd=case_dir, env=env, capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        print(f"ERROR solve:\n{r.stdout[-2000:]}\n{r.stderr}")
        return None

    print(f"[3/3] parse mesh.nodes + .result", flush=True)
    return parse_elmer_result(case_dir / "novapcb_thermal")


def parse_elmer_result(case_subdir):
    """Read temperature field from Elmer's text .result + mesh.nodes files.

    mesh.nodes format: `node_id  -1  x  y  z`
    .result format: ASCII; after "Perm:" line lists permutation map
    (node_id → perm_index), then values are written in perm-index order.

    Returns dict with summary stats + per-component Tj.
    """
    import numpy as np

    nodes_path = case_subdir / "mesh.nodes"
    result_path = case_subdir / "novapcb_thermal.result"

    if not nodes_path.exists() or not result_path.exists():
        print(f"  missing mesh.nodes or .result in {case_subdir}")
        return None

    # Parse mesh.nodes
    nodes = {}
    for line in open(nodes_path):
        parts = line.split()
        if len(parts) >= 5:
            nid = int(parts[0])
            x, y, z = float(parts[2]), float(parts[3]), float(parts[4])
            nodes[nid] = (x, y, z)
    n_nodes = len(nodes)

    # Parse .result for temperature values
    lines = open(result_path).read().splitlines()
    # Find "Perm:" line + count of entries
    perm_idx = None
    for i, ln in enumerate(lines):
        if ln.strip().startswith("Perm:"):
            perm_idx = i
            break
    if perm_idx is None:
        print(f"  no Perm: line in .result")
        return None

    # Read permutation: pairs of (node_id, perm_index)
    perm_count = int(lines[perm_idx].split()[1])
    node_to_perm = {}
    for k in range(perm_count):
        toks = lines[perm_idx + 1 + k].split()
        if len(toks) < 2: continue
        nid = int(toks[0]); pidx = int(toks[1])
        node_to_perm[nid] = pidx

    # Values follow the perm map, in perm-index order (1-indexed by Elmer)
    val_start = perm_idx + 1 + perm_count
    values = []
    for ln in lines[val_start:]:
        ln = ln.strip()
        if not ln: continue
        try:
            values.append(float(ln))
        except ValueError:
            break

    # Build (x, y, z, T) array
    pts = []
    temps = []
    for nid, (x, y, z) in nodes.items():
        pidx = node_to_perm.get(nid)
        if pidx is None or pidx > len(values): continue
        # values are 1-indexed → index pidx-1
        T = values[pidx - 1]
        pts.append((x, y, z))
        temps.append(T)
    points = np.array(pts)
    temps = np.array(temps)

    print(f"  mesh nodes: {n_nodes}, parsed temps: {len(temps)}, T range {temps.min():.1f} .. {temps.max():.1f}")

    results = {
        "n_nodes": len(points),
        "T_board_avg_C": float(temps.mean()),
        "T_board_max_C": float(temps.max()),
        "T_board_min_C": float(temps.min()),
    }

    for name, hs in HEAT_SOURCES.items():
        x = hs["x_mm"] / 1000.0
        y = hs["y_mm"] / 1000.0
        # find nodes within the component footprint at the top (z ≈ board height)
        w_x = hs["footprint_mm"][0] / 1000.0
        w_y = hs["footprint_mm"][1] / 1000.0
        mask = ((np.abs(points[:, 0] - x) < w_x/2) &
                (np.abs(points[:, 1] - y) < w_y/2) &
                (np.abs(points[:, 2] - BOARD_H) < 1e-5))
        if mask.sum() > 0:
            t_local = float(temps[mask].max())
            results[f"Tj_{name}_C"] = t_local
        else:
            results[f"Tj_{name}_C"] = None
            print(f"  WARN: no top-face nodes within {name} footprint")

    return results


def main():
    print("="*64)
    print("Step 4 thermal FEA — Elmer 3D heat-conduction")
    print(f"  Board:     {BOARD_L*1000}×{BOARD_W*1000}×{BOARD_H*1000} mm 6-layer")
    print(f"  k_eff:     {K_XY} W/m·K (geom mean of in-plane + through-plane)")
    print(f"  h_conv:    {H_CONV} W/m²K per surface (top + bot)")
    print(f"  T_ambient: {T_AMBIENT} °C")
    print(f"  Heat sources:")
    for name, hs in HEAT_SOURCES.items():
        print(f"    {name}: {hs['power_W']:.4f} W at ({hs['x_mm']}, {hs['y_mm']}) mm "
              f"over {hs['footprint_mm'][0]}×{hs['footprint_mm'][1]} mm")
    print("="*64)

    results = run_elmer()
    if results is None:
        sys.exit(1)

    print()
    print("="*64)
    print(f"RESULTS")
    print("="*64)
    for k, v in results.items():
        if v is None: continue
        if isinstance(v, float):
            print(f"  {k:25s} = {v:.2f}")
        else:
            print(f"  {k:25s} = {v}")

    # Validate vs PLACEMENT_STRATEGY prediction
    tj_ldo = results.get("Tj_U2_LDO_C")
    tj_mcu = results.get("Tj_U1_MCU_C")
    print()
    print("="*64)
    print(f"VALIDATION vs PLACEMENT_STRATEGY §3.4 prediction")
    print("="*64)
    if tj_ldo is not None:
        target = 80.0
        delta = tj_ldo - target
        status = "PASS" if tj_ldo <= target else "FAIL"
        print(f"  LDO Tj: actual {tj_ldo:.1f} °C vs prediction ≤ {target} °C → {status}"
              f" ({delta:+.1f} °C vs target)")
        results["validation_ldo"] = status
    if tj_mcu is not None:
        target = 85.0
        delta = tj_mcu - target
        status = "PASS" if tj_mcu <= target else "FAIL"
        print(f"  MCU Tj: actual {tj_mcu:.1f} °C vs prediction ≤ {target} °C → {status}"
              f" ({delta:+.1f} °C vs target)")
        results["validation_mcu"] = status

    # Save results
    (WORK / "results.json").write_text(json.dumps(results, indent=2))
    print(f"\nresults saved to {WORK / 'results.json'}")


if __name__ == "__main__":
    main()
