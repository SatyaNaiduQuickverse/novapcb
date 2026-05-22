#!/usr/bin/env python3
"""Gate 12 — per-step thermal sim, PARAMETERIZED v1.1 heat-source set.

REWRITTEN 2026-05-23 (master red-flag on prior 104°C result):

Prior version inherited from gate12_thermal_U1.py used scalar bare-FR4
k=0.3 W/m·K, BC h=10 on all 6 boundaries, T_amb=25°C, threshold=105°C
(silicon abs-max). That model is WRONG for novapcb because:

  (a) Real board has 6-layer copper stackup — anisotropic effective k
      (33.5 in-plane, 0.316 through-plane per THERMAL_BUDGET §3.1
      parallel-paths/series-rule), NOT bare-FR4.
  (b) Real worst case is sealed enclosure → only top + bottom convect,
      EDGES ARE ADIABATIC. h=5 W/m²·K master worst case.
  (c) Real worst-case ambient is drone-bay sealed = 50°C, NOT 25°C.
  (d) Design target per `sims/thermal-step4/STEP4_REPORT.md` is
      Tj ≤ 80°C with 5°C margin, NOT 105°C silicon abs-max.

Per master directive 2026-05-23:
  - Use STEP4-equivalent model (anisotropic k, h=5 top+bot only,
    adiabatic edges, T_amb=50°C).
  - Threshold = 80°C (design target with margin), not silicon abs-max.
  - VALIDATE the rewrite by reproducing STEP4 result on the same
    inputs (80×60 board, 4 heat sources) — MCU=75.2°C, LDO=69°C.

Per-step heat-source registry (auto-discovered from .kicad_pcb by
refdes; only on-board components contribute, parked = X >= 100):

  Step 1 (C only):       U1 (STM32H743) 0.7 W
  Step 2 (E added):      U1
  Step 3 (F added):      U1 (U5 ESD ~10mW, ignored)
  Step 4 (G added):      U1, U14 (CAN xcvr ~100mW)
  Step 5 (B added):      + U2 (AP2112K LDO ~595mW), U6 (eFuse ~18mW)
  Step 6 (A added):      + Q2 (P-FET ~6.5mW), Q3/Q4 (OR-FETs)
  Step 7 (D added):      + U13 (LP5907 IMU LDO ~50mW), Q5 (IMU heater)
  Step 8 (H added):      no new significant sources

`regression_step4` mode: runs against STEP4_REPORT.md inputs and
asserts MCU 75.2 / LDO 69 reproduce within ±2°C (mesh discretization
allowance). This is the Gate 13 validation requirement for the
rewrite — gate12 v2 isn't usable until regression passes.
"""
import os
import sys
import re
import subprocess
from dataclasses import dataclass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ELMER = os.path.join(os.path.expanduser("~"), "local", "elmer", "bin", "ElmerSolver")

CASE_DIR = os.path.join(HERE, "thermal")
CASE = os.path.join(CASE_DIR, "case.sif")


# ---------------------------------------------------------------
# STEP4-equivalent model parameters (master 2026-05-23)
# ---------------------------------------------------------------
# Material — anisotropic k per THERMAL_BUDGET §3.1:
#   in-plane k_xy = 33.5 W/m·K  (parallel-paths Cu + FR4)
#   through-plane k_z = 0.316 W/m·K (series Cu + FR4)
# Elmer "Heat Conductivity(3) = K_XY K_XY K_Z" tensor form.
K_XY = 33.5
K_Z = 0.316
RHO = 2500   # kg/m³, board average
CP = 800     # J/kg·K, board average

# BC — STEP4 worst case:
H_CONV = 5.0          # W/m²·K, top + bottom (sealed enclosure)
T_AMBIENT_C = 50.0    # °C, drone-bay worst case
# Edges (X-/X+/Y-/Y+) are ADIABATIC (no h_conv).

# Design target (NOT silicon abs-max):
T_J_TARGET_C = 80.0   # per STEP4_REPORT, Sai resilience mandate

# Board thickness
BOARD_H = 1.6e-3      # 1.6mm, JLC06161H stackup


@dataclass
class HeatSource:
    name: str
    x_mm: float
    y_mm: float
    body_x_mm: float
    body_y_mm: float
    power_W: float


# ---------------------------------------------------------------
# Per-component thermal profile registry
# Powers match STEP4 + master's RF-2 v1.1 set.
# ---------------------------------------------------------------
COMPONENT_PROFILES = {
    "U1":  dict(body_x=14.0, body_y=14.0, power_W=0.700),  # STM32H743 worst case (STEP4 uses 0.700, not 0.500)
    "U2":  dict(body_x=2.5,  body_y=3.0,  power_W=0.595),  # AP2112K LDO (STEP4)
    "U6":  dict(body_x=3.0,  body_y=4.0,  power_W=0.018),  # eFuse TPS25922 (STEP4)
    "U11": dict(body_x=3.0,  body_y=3.0,  power_W=0.05),
    "U12": dict(body_x=3.0,  body_y=3.0,  power_W=0.05),
    "U13": dict(body_x=2.9,  body_y=1.6,  power_W=0.05),   # LP5907 IMU LDO
    "U14": dict(body_x=3.0,  body_y=3.0,  power_W=0.10),   # TJA1051 CAN xcvr
    "Q2":  dict(body_x=3.0,  body_y=1.5,  power_W=0.0065), # P-FET (STEP4)
    "Q3":  dict(body_x=5.0,  body_y=4.0,  power_W=0.05),
    "Q4":  dict(body_x=5.0,  body_y=4.0,  power_W=0.05),
    "Q5":  dict(body_x=3.0,  body_y=1.5,  power_W=0.30),   # IMU heater
}


def get_active_heat_sources(brd) -> list[HeatSource]:
    """Read PCB, return HeatSource list for currently-placed components."""
    sources = []
    for fp in brd.GetFootprints():
        ref = fp.GetReference()
        if ref not in COMPONENT_PROFILES:
            continue
        p = fp.GetPosition()
        x_mm, y_mm = p.x / 1e6, p.y / 1e6
        if x_mm >= 100:
            continue
        prof = COMPONENT_PROFILES[ref]
        sources.append(HeatSource(
            name=ref,
            x_mm=x_mm, y_mm=y_mm,
            body_x_mm=prof["body_x"], body_y_mm=prof["body_y"],
            power_W=prof["power_W"],
        ))
    return sources


# ---------------------------------------------------------------
# .grd (ElmerGrid input) — STEP4-style: 1 body, 6 boundary IDs
# ---------------------------------------------------------------
def make_grd(board_L_m: float, board_W_m: float, board_H_m: float,
             nx: int, ny: int, nz: int) -> str:
    return f"""\
##### ElmerGrid input: novapcb thermal #####
Version = 210903
Coordinate System = Cartesian 3D
Subcell Divisions in 3D = 1 1 1
Subcell Sizes 1 = {board_L_m}
Subcell Sizes 2 = {board_W_m}
Subcell Sizes 3 = {board_H_m}
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
Element Divisions 1 = {nx}
Element Divisions 2 = {ny}
Element Divisions 3 = {nz}
"""


# ---------------------------------------------------------------
# .sif (Elmer Solver Input File)
# ---------------------------------------------------------------
def make_sif(sources: list[HeatSource]) -> str:
    """Generate Elmer SIF. Heat sources via MATC bounding-box expression.

    Elmer Heat Equation expects Heat Source in W/kg (per unit MASS).
    q_mass = q_vol / RHO where q_vol = P / (body_x * body_y * board_H).
    """
    src_pieces = []
    for src in sources:
        x = src.x_mm / 1000.0
        y = src.y_mm / 1000.0
        w_x = src.body_x_mm / 1000.0
        w_y = src.body_y_mm / 1000.0
        vol = w_x * w_y * BOARD_H
        q_vol = src.power_W / vol
        q_mass = q_vol / RHO
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
  Active Solvers(2) = 1 2
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

Solver 2
  Exec Solver = After Simulation
  Equation = "result output"
  Procedure = "ResultOutputSolve" "ResultOutputSolver"
  Output File Name = "novapcb_thermal"
  Output Format = "vtu"
  Binary Output = Logical False
  Ascii Output = Logical True
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

! Edges 1-4: ADIABATIC (no h_conv)
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

! Faces 5 (bottom), 6 (top): convection
Boundary Condition 5
  Name = "Z- bottom (convection)"
  Target Boundaries(1) = 5
  Heat Transfer Coefficient = {H_CONV}
  External Temperature = {T_AMBIENT_C}
End

Boundary Condition 6
  Name = "Z+ top (convection)"
  Target Boundaries(1) = 6
  Heat Transfer Coefficient = {H_CONV}
  External Temperature = {T_AMBIENT_C}
End
"""


def run_elmer(case_dir: str) -> dict:
    """Run ElmerGrid → ElmerSolver pipeline; return parsed temperatures."""
    env = os.environ.copy()
    bin_dir = os.path.join(os.path.expanduser("~"), "local", "elmer", "bin")
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    elmer_lib = os.path.join(os.path.expanduser("~"), "local", "elmer", "lib")
    env["LD_LIBRARY_PATH"] = f"{elmer_lib}:{env.get('LD_LIBRARY_PATH', '')}"

    # Run ElmerGrid: .grd → mesh
    r = subprocess.run(
        [os.path.join(bin_dir, "ElmerGrid"), "1", "2", "novapcb_thermal.grd", "-autoclean"],
        cwd=case_dir, capture_output=True, text=True, timeout=120, env=env,
    )
    if r.returncode != 0:
        return {"error": f"ElmerGrid failed: {r.stderr[-500:]}"}

    # Run ElmerSolver
    (open(os.path.join(case_dir, "ELMERSOLVER_STARTINFO"), "w")
     .write("novapcb_thermal.sif\n"))
    r = subprocess.run(
        [os.path.join(bin_dir, "ElmerSolver")],
        cwd=case_dir, capture_output=True, text=True, timeout=600, env=env,
    )
    if "Result Norm" not in r.stdout:
        return {"error": f"ElmerSolver failed: {r.stdout[-1500:]}"}

    # Parse Elmer .result + mesh.nodes (NOT the VTU — Elmer's VTU writer
    # outputs Points in node-id order but DataArrays in perm-index order,
    # which mismatches standard VTK convention. .result + perm map is
    # reliable; STEP4's parser uses this and it round-trips correctly).
    pts, temps = _parse_elmer_result(case_dir)
    if pts is None:
        return {"error": "failed to parse Elmer .result"}
    return {
        "T_max_C": max(temps), "T_min_C": min(temps),
        "T_avg_C": sum(temps)/len(temps),
        "_points": pts, "_temps": temps,
    }


def _parse_elmer_result(case_dir: str):
    """Parse mesh.nodes + .result and return (points, temps) lists.

    Returns (None, None) on failure.
    """
    mesh_dir = os.path.join(case_dir, "novapcb_thermal")
    nodes_path = os.path.join(mesh_dir, "mesh.nodes")
    result_path = os.path.join(mesh_dir, "novapcb_thermal.result")
    if not os.path.exists(nodes_path) or not os.path.exists(result_path):
        return None, None
    nodes = {}
    for line in open(nodes_path):
        parts = line.split()
        if len(parts) >= 5:
            nodes[int(parts[0])] = (float(parts[2]), float(parts[3]), float(parts[4]))
    lines = open(result_path).read().splitlines()
    perm_idx = None
    for i, ln in enumerate(lines):
        if ln.strip().startswith("Perm:"):
            perm_idx = i
            break
    if perm_idx is None: return None, None
    perm_count = int(lines[perm_idx].split()[1])
    node_to_perm = {}
    for k in range(perm_count):
        toks = lines[perm_idx + 1 + k].split()
        if len(toks) >= 2:
            node_to_perm[int(toks[0])] = int(toks[1])
    val_start = perm_idx + 1 + perm_count
    values = []
    for ln in lines[val_start:]:
        ln = ln.strip()
        if not ln: continue
        try: values.append(float(ln))
        except ValueError: break
    pts, temps = [], []
    for nid, (x, y, z) in nodes.items():
        pidx = node_to_perm.get(nid)
        if pidx is None or pidx > len(values): continue
        pts.append((x, y, z))
        temps.append(values[pidx - 1])
    return pts, temps


def sample_Tj(case_dir: str, src: HeatSource) -> float:
    """Sample junction T at a component — MAX temp within footprint at top surface.

    Matches STEP4 sampling convention: filter nodes within component
    footprint bounding box AND at top face (z ≈ BOARD_H), take MAX.
    Uses Elmer .result file (NOT VTU — Elmer's VTU writer has a
    point-order vs perm-order mismatch bug).
    """
    pts, temps = _parse_elmer_result(case_dir)
    if pts is None: return None
    x_m = src.x_mm / 1000.0
    y_m = src.y_mm / 1000.0
    w_x_m = src.body_x_mm / 1000.0
    w_y_m = src.body_y_mm / 1000.0
    Tj_max = None
    for i, (px, py, pz) in enumerate(pts):
        if abs(pz - BOARD_H) > 1e-5: continue
        if abs(px - x_m) > w_x_m / 2: continue
        if abs(py - y_m) > w_y_m / 2: continue
        if Tj_max is None or temps[i] > Tj_max:
            Tj_max = temps[i]
    return Tj_max


def run(sources: list[HeatSource],
        board_L_m: float = 0.080, board_W_m: float = 0.060,
        case_label: str = "default") -> dict:
    """Top-level: generate mesh + sif, run solver, return temperature dict."""
    case_dir = os.path.join(CASE_DIR, case_label)
    os.makedirs(case_dir, exist_ok=True)

    # Match STEP4 mesh density (~2mm/cell)
    nx = max(20, int(board_L_m * 1000 / 2))
    ny = max(15, int(board_W_m * 1000 / 2))
    nz = 4

    with open(os.path.join(case_dir, "novapcb_thermal.grd"), "w") as f:
        f.write(make_grd(board_L_m, board_W_m, BOARD_H, nx, ny, nz))
    with open(os.path.join(case_dir, "novapcb_thermal.sif"), "w") as f:
        f.write(make_sif(sources))

    return run_elmer(case_dir)


def regression_step4():
    """REGRESSION TEST: reproduce STEP4_REPORT.md numbers.

    Inputs: 80×60 board, 4 heat sources at the STEP4 positions/powers.
    Expected: MCU Tj ≈ 75.2°C, LDO Tj ≈ 69.0°C, Board Tavg ≈ 71.5°C, Tmax ≈ 76.8°C.
    Tolerance: ±2°C (mesh discretization + parameterization differences).
    """
    print("=== Gate 12 REGRESSION — reproduce STEP4_REPORT ===\n")
    STEP4_INPUTS = [
        HeatSource("U2_LDO",  10.0,   33.5, 2.5,  3.0,  0.595),
        HeatSource("U1_MCU",  39.53,  30.0, 14.0, 14.0, 0.700),
        HeatSource("U6_eFuse", 12.24, 21.29, 3.0,  4.0,  0.018),
        HeatSource("Q2_PFET",  10.35, 13.55, 3.0,  1.5,  0.0065),
    ]
    print("STEP4 inputs: 80×60 board, h=5 top+bot, T_amb=50°C, k_xy=33.5, k_z=0.316")
    for s in STEP4_INPUTS:
        print(f"  {s.name}: ({s.x_mm}, {s.y_mm}) {s.body_x_mm}x{s.body_y_mm}mm @ {s.power_W*1000:.1f}mW")

    result = run(STEP4_INPUTS, board_L_m=0.080, board_W_m=0.060, case_label="regression_step4")
    if "error" in result:
        print(f"\n  REGRESSION FAILED: {result['error']}")
        return 1

    case_dir = os.path.join(CASE_DIR, "regression_step4")
    T_LDO = sample_Tj(case_dir, STEP4_INPUTS[0])  # U2_LDO
    T_MCU = sample_Tj(case_dir, STEP4_INPUTS[1])  # U1_MCU
    T_avg = result["T_avg_C"]
    T_max = result["T_max_C"]

    print(f"\nResults:")
    print(f"  T_avg = {T_avg:.2f}°C  (STEP4 71.5°C, tol ±2°C)")
    print(f"  T_max = {T_max:.2f}°C  (STEP4 76.8°C, tol ±2°C)")
    print(f"  T_LDO = {T_LDO:.2f}°C  (STEP4 69.0°C, tol ±2°C)")
    print(f"  T_MCU = {T_MCU:.2f}°C  (STEP4 75.2°C, tol ±2°C)")

    targets = [("T_avg", T_avg, 71.5), ("T_max", T_max, 76.8),
               ("T_LDO", T_LDO, 69.0), ("T_MCU", T_MCU, 75.2)]
    fails = []
    for name, got, expected in targets:
        err = got - expected
        if abs(err) > 2.0:
            fails.append((name, got, expected, err))

    if fails:
        print(f"\nREGRESSION FAILED:")
        for name, got, expected, err in fails:
            print(f"  {name}: got {got:.2f} vs expected {expected:.2f} (err {err:+.2f}°C, > ±2°C)")
        return 1
    print(f"\nREGRESSION PASS: gate12 v2 reproduces STEP4 within ±2°C.")
    return 0


def main(pcb_path: str = None):
    """Default mode: run on current PCB."""
    import pcbnew
    if pcb_path is None:
        pcb_path = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")
    print(f"=== Gate 12 — per-step thermal sim (v2, STEP4-model) ===\n")
    print(f"PCB: {pcb_path}")
    print(f"Model: anisotropic k=({K_XY}, {K_XY}, {K_Z}) W/m·K,")
    print(f"       h=5 top+bot (adiabatic edges), T_amb=50°C")
    print(f"Target: Tj ≤ {T_J_TARGET_C}°C (design target, not silicon abs-max)\n")

    brd = pcbnew.LoadBoard(pcb_path)
    sources = get_active_heat_sources(brd)

    if not sources:
        print("  no heat sources detected — skipping FE run")
        return 0

    print(f"Active heat sources for this step:")
    P_tot = 0.0
    for s in sources:
        print(f"  {s.name:<6} @ ({s.x_mm:.2f}, {s.y_mm:.2f})  body={s.body_x_mm}x{s.body_y_mm}mm  P={s.power_W*1000:.0f}mW")
        P_tot += s.power_W
    print(f"  total P = {P_tot*1000:.0f} mW\n")

    # Use current board size (read from edge cuts) or default 90×70
    board_L_m, board_W_m = 0.090, 0.070  # will derive from board outline in future
    result = run(sources, board_L_m=board_L_m, board_W_m=board_W_m, case_label="current_step")
    if "error" in result:
        print(f"Gate 12 ERROR: {result['error']}")
        return 1

    case_dir = os.path.join(CASE_DIR, "current_step")
    T_max = result["T_max_C"]
    T_avg = result["T_avg_C"]

    # Per-component Tj
    print(f"\nResults (k_eff anisotropic, plane-equivalent):")
    print(f"  T_avg = {T_avg:.2f}°C")
    print(f"  T_max = {T_max:.2f}°C")
    fails = []
    for s in sources:
        Tj = sample_Tj(case_dir, s)
        margin = T_J_TARGET_C - Tj
        status = "PASS" if margin > 0 else "FAIL"
        print(f"  Tj_{s.name:<6} = {Tj:.2f}°C  (target {T_J_TARGET_C}°C, margin {margin:+.1f}°C)  {status}")
        if margin <= 0:
            fails.append((s.name, Tj))

    if fails:
        print(f"\nGate 12: RED — {len(fails)} component(s) exceed Tj target")
        for name, Tj in fails:
            print(f"  {name}: {Tj:.2f}°C > {T_J_TARGET_C}°C")
        return 1
    print(f"\nGate 12: GREEN — all Tj ≤ {T_J_TARGET_C}°C target")
    return 0


if __name__ == "__main__":
    if "--regression-step4" in sys.argv:
        sys.exit(regression_step4())
    sys.exit(main())
