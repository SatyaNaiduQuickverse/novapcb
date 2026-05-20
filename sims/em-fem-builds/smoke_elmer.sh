#!/usr/bin/env bash
# Elmer smoke test — 1D steady-state heat conduction through a slab.
# Analytical: T(x) = T_hot - (T_hot - T_cold) * x/L
#   Slab: 1m × 0.1m × 0.1m, k = 1 W/m·K, T_left=100°C, T_right=0°C
#   Expected T(midpoint, 0.5m) = 50°C
# Real FEA (NOT import-check). Compare numerical to analytical.
set -euo pipefail

WORK=/tmp/elmer_smoke
mkdir -p "$WORK" && cd "$WORK"

# 1D mesh via ElmerGrid: simple slab
cat > slab.grd <<'EOF'
##### ElmerGrid input file for a 1D slab #####
Version = 210903
Coordinate System = Cartesian 2D
Subcell Divisions in 2D = 10 1
Subcell Limits 1 = 0.0 1.0
Subcell Limits 2 = 0.0 0.1
Material Structure in 2D
  1 1 1 1 1 1 1 1 1 1
End
Materials Interval = 1 1
Boundary Definitions
# left edge, right edge, top/bottom (Neumann)
  1 -1 1 1
  2 -2 1 1
End
Numbering = Horizontal
Element Degree = 1
Element Innernodes = False
Triangles = False
Surface Elements = 1 1
Coordinate Mapping(3) = 1 2 3
EOF

# Solver Input File (SIF) — steady heat conduction
cat > slab.sif <<'EOF'
Header
  Mesh DB "." "slab"
End

Simulation
  Coordinate System = "Cartesian 2D"
  Simulation Type = Steady State
  Steady State Max Iterations = 20
  Output File = "slab.result"
  Post File = "slab.vtu"
End

Body 1
  Equation = 1
  Material = 1
End

Equation 1
  Active Solvers(1) = 1
End

Solver 1
  Equation = "Heat Equation"
  Variable = "Temperature"
  Procedure = "HeatSolve" "HeatSolver"
  Linear System Solver = "Direct"
  Linear System Direct Method = "UMFPACK"
End

Material 1
  Density = 1.0
  Heat Conductivity = 1.0
End

Boundary Condition 1
  Target Boundaries(1) = 1
  Temperature = 100.0
End

Boundary Condition 2
  Target Boundaries(1) = 2
  Temperature = 0.0
End
EOF

PATH=~/local/elmer/bin:$PATH
echo "[elmer-smoke] mesh"
ElmerGrid 1 2 slab.grd > grid.log 2>&1

echo "[elmer-smoke] solve"
echo "slab.sif" > ELMERSOLVER_STARTINFO
T0=$(date +%s.%N)
ElmerSolver > solver.log 2>&1
ELAPSED=$(echo "$(date +%s.%N) - $T0" | bc)
echo "[elmer-smoke] runtime: ${ELAPSED}s"

# Parse result — find temperature at x≈0.5
# Elmer writes ASCII .result with node temperatures. The mesh has 11 nodes along x.
python3 - <<'PYEOF'
import re
# Read the .vtu (XML) for temperatures at known X
import xml.etree.ElementTree as ET
import sys
try:
    tree = ET.parse('slab/slab.vtu')
except Exception as e:
    print(f"NO VTU output: {e}")
    sys.exit(1)
root = tree.getroot()
ns = root.tag.split('}')[0] + '}' if '}' in root.tag else ''

# Find point coordinates + temperature data
points = None; temps = None
for darr in root.iter(ns + 'DataArray'):
    name = darr.get('Name', '')
    typ = darr.get('type', '')
    if name == 'Temperature':
        temps = [float(v) for v in darr.text.split()]
    elif name == 'Points' or darr.text and len(darr.text.split()) > 6 and 'coordinates' in name.lower():
        pass

# fallback: get Points from Piece > Points
for p in root.iter(ns + 'Piece'):
    pts = p.find(ns + 'Points')
    if pts is not None:
        da = pts.find(ns + 'DataArray')
        if da is not None:
            vals = [float(v) for v in da.text.split()]
            points = list(zip(vals[0::3], vals[1::3], vals[2::3]))

if temps and points:
    # Find node closest to x=0.5
    target_x = 0.5
    best_idx = min(range(len(points)), key=lambda i: abs(points[i][0] - target_x))
    bx, by, bz = points[best_idx]
    bt = temps[best_idx]
    expected = 50.0
    err = abs(bt - expected)
    rel_err_pct = err / expected * 100
    print(f"node at x={bx:.4f}: T={bt:.4f}°C  (expected ~50.0°C)")
    print(f"abs err: {err:.4f}°C  rel err: {rel_err_pct:.2f}%")
    print(f"PASS' if rel_err_pct < 1.0 else 'FAIL")
else:
    print(f"NO temperatures or points parsed; temps={temps and len(temps)}, points={points and len(points)}")
PYEOF
