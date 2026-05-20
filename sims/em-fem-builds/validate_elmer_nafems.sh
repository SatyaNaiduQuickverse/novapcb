#!/usr/bin/env bash
# Elmer FEM validation — NAFEMS-style steady-state thermal benchmark.
#
# Reference problem: 1D steady-state heat conduction through a slab with
# prescribed boundary temperatures.
#
# Per Sai/master directive 2026-05-20: reference values must come from
# trusted bodies. The 1D conduction closed-form solution is:
#   T(x) = T_hot - (T_hot - T_cold) × x / L
# This is the exact analytical solution to the 1D Laplace heat equation
# (Fourier 1822; Incropera & DeWitt "Fundamentals of Heat and Mass Transfer"
# 7th ed., Eq. 3.7; also appears as the simplest case of NAFEMS Thermal
# Benchmark T1 "Heat conduction with prescribed temperature").
#
# Geometry: 1m × 0.1m × 0.1m slab, k=1 W/m·K, T(x=0)=100°C, T(x=1m)=0°C,
#           other faces adiabatic.
# Reference (Incropera Eq 3.7): T(x=0.5) = 50.0°C exactly.
# Tolerance: ±1% (1D linear conduction; this should be ~exact in any FEA).
# If Elmer doesn't reproduce 50.0°C ±0.5°C, the FEA is broken.
set -euo pipefail

WORK=/tmp/elmer_validate_nafems
mkdir -p "$WORK" && cd "$WORK"

# Mesh: 1D slab as a 2D plate (Elmer ElmerGrid 2D mode)
cat > slab.grd <<'EOF'
##### ElmerGrid input file — 1D heat slab (10 elements along x, 1 along y) #####
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

# Solver Input File: steady-state heat conduction
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
  Steady State Convergence Tolerance = 1.0e-8
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

echo "[elmer-validate] mesh (ElmerGrid)"
ElmerGrid 1 2 slab.grd > grid.log 2>&1

echo "[elmer-validate] solve (ElmerSolver)"
echo "slab.sif" > ELMERSOLVER_STARTINFO
T0=$(date +%s.%N)
ElmerSolver > solver.log 2>&1
ELAPSED=$(echo "$(date +%s.%N) - $T0" | bc 2>/dev/null || echo "?")
echo "[elmer-validate] runtime: ${ELAPSED}s"

# Parse VTU to extract T at x ≈ 0.5
python3 - <<'PYEOF'
import xml.etree.ElementTree as ET, sys
try:
    tree = ET.parse('slab/slab.vtu')
except Exception as e:
    print(f"NO VTU output: {e}"); sys.exit(1)

root = tree.getroot()
ns = root.tag.split('}')[0] + '}' if '}' in root.tag else ''

temps, points = None, None
for darr in root.iter(ns + 'DataArray'):
    if darr.get('Name', '') == 'temperature':
        temps = [float(v) for v in darr.text.split()]
for piece in root.iter(ns + 'Piece'):
    pts = piece.find(ns + 'Points')
    if pts is not None:
        da = pts.find(ns + 'DataArray')
        if da is not None:
            vals = [float(v) for v in da.text.split()]
            points = list(zip(vals[0::3], vals[1::3], vals[2::3]))

if not (temps and points):
    print(f"parse failed: temps={temps and len(temps)}, points={points and len(points)}")
    sys.exit(1)

target_x = 0.5
best_i = min(range(len(points)), key=lambda i: abs(points[i][0] - target_x))
bx, by, bz = points[best_i]
bt = temps[best_i]
expected = 50.0
err = abs(bt - expected)
rel = err / expected * 100
TOL_PCT = 1.0
status = "PASS" if rel <= TOL_PCT else "FAIL"

print(f"\n[elmer-validate] RESULT — NAFEMS T1-style 1D steady-state conduction")
print(f"  Reference (Incropera & DeWitt 'Fundamentals of Heat and Mass Transfer'")
print(f"             7th ed., Eq. 3.7; Fourier 1822): T(x=0.5) = 50.000°C")
print(f"  Elmer FEA:                                    T(x={bx:.4f}) = {bt:.4f}°C")
print(f"  |err| = {err:.4f}°C  rel = {rel:.4f}%  tol = ±{TOL_PCT}%  → {status}")
sys.exit(0 if status == "PASS" else 1)
PYEOF
