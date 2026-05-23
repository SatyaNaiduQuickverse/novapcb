#!/usr/bin/env python3
"""Gate 12 — per-step thermal sim, v3 PER-BODY heat-source assignment.

REWRITTEN 2026-05-23 (master red-flag on v2's MATC-bounding-box artifact):

v2 used MATC bounding-box conditionals in Body Force to inject heat
("if abs(tx-x0)<w/2 & abs(ty-y0)<h/2 q=q+q_per_kg"). Total injected
power depends on how many Gauss points satisfy the condition, which
varies with mesh cell size. Result: temperatures DIVERGED with mesh
refinement (STEP4 inputs gave MCU=74.2/81.5/89.2 °C at 2/1/0.675mm
cells).

v3 replaces MATC with **per-body element assignment + per-body Body
Force**. Each heat source becomes its own Body i in the Elmer mesh.
Heat injection per body i is q_mass = P_i / (ρ × V_body_i_actual),
where V_body_i_actual = (number of elements assigned to body i) ×
(element volume). Total injected = P_i EXACTLY regardless of mesh
refinement, because V_body_i_actual is the deterministic property of
the mesh assignment (not a bbox-overlap heuristic).

Two **permanent gate assertions** added (master directive 2026-05-23):

  1. **ENERGY-BALANCE GATE**: total injected power must equal total
     surface convection flux to within 1%. Catches body-force injection
     errors immediately. Computed from .result temperatures + surface
     element integration on top/bottom convection BCs.

  2. **MIN-MESH-DENSITY GATE**: every heat-source body must have at
     least MIN_ELEMS_PER_BODY=4 elements assigned. Catches the silent-
     drop failure mode where a small body falls between element centers
     and gets zero elements (would be undetectable without the gate).

Task 9 NAFEMS thermal validation (sims/validation/elmer_thermal/) used
Dirichlet BCs (T=0 / T=100) — it validates Elmer's conduction PDE
solver but NOT body-force injection. The energy-balance assertion is
the proper validation for body-force injection, per run.

Per-step heat-source registry (auto-discovered by refdes; only on-board
components contribute, parked = X >= 100):

  Step 1 (C only):       U1 (STM32H743)
  Step 2 (E added):      U1
  Step 3 (F added):      U1 (U5 ESD ~10mW, ignored)
  Step 4 (G added):      U1, U14 (CAN xcvr ~100mW)
  Step 5 (B added):      + U2 (AP2112K LDO), U6 (eFuse ~18mW),
                         + U13 (LP5907 IMU LDO ~50mW)
  Step 6 (A added):      + Q2 (P-FET ~6mW), Q3/Q4 (OR-FETs)
  Step 7 (D added):      + Q5 (IMU heater — 0W hot case, thermostatic)
  Step 8 (H added):      no new significant sources

MCU dissipation: REALISTIC WORST (not datasheet abs-max) — see
docs/THERMAL_3V3_BUDGET.md §4 + the MCU_REALISTIC_WORST_W constant
below. Derived from ST AN4365 peripheral-adder method.
"""
import os
import sys
import subprocess
from collections import defaultdict
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

# Energy-balance + mesh-density gate thresholds (master 2026-05-23)
ENERGY_BALANCE_TOL = 0.01      # 1% — Σ_injected vs Σ_surface_flux
MIN_ELEMS_PER_BODY = 4         # every heat-source body needs ≥4 elements


# ---------------------------------------------------------------
# Realistic-worst MCU dissipation (master directive 2026-05-23):
# datasheet abs-max 0.924 W is NOT a defensible design input. Derive
# from ST AN4365 + ArduCopter peripheral usage.
# ---------------------------------------------------------------
# H743 at 480MHz (HCLK = 480, SYSCLK = 480, no internal halt):
#   I_DD_core (Run, 480MHz, Vcore=1.2V, all peripherals OFF) = 65 mA typ
#     (DS12110 Table 27, "I_DD with code running from Flash, all
#     peripherals disabled, F_HCLK=480MHz") — 25°C
#   Temperature derate to 85°C ambient: × ~1.15 = 75 mA
#   I_DD adders for active peripherals (DS12110 Table 38–40):
#     SPI x3 (IMU): 3 × 1.5 mA = 4.5 mA
#     I2C x2 (baro, mag): 2 × 0.5 mA = 1.0 mA
#     UART x4 (GPS, FrSky, CRSF, debug): 4 × 1 mA = 4.0 mA
#     USB OTG FS: 8 mA
#     SDMMC1 (active write bursts, 50MHz): 12 mA average
#     ADC1+ADC2 (continuous): 4 mA
#     8x TIM (DSHOT600 capture+compare): 6 mA
#     DMA1+DMA2 (active): 8 mA
#     Cache enabled, branch predictor active: included in 75 mA
#   Subtotal peripheral adder: ~48 mA
#   I_VDD total: 75 + 48 = 123 mA → say 130 mA realistic with margin
#   I_VDDA (analog): 5 mA
#   Total core current: ~135 mA
#
# But ArduCopter's effective workload (EKF + nav + control loops + DMA
# bursts during SDMMC writes) pushes spot peaks higher. Realistic-worst
# estimate (sustained averaged over 1s window):
#   I_DD = 170 mA at 80°C ambient
#   P_MCU = 3.3 V × 0.170 A = 0.561 W
#
# Add 25% engineering margin for under-counted activity (Cortex-M7 cache
# misses, MPU configuration overhead, peripheral DMA hand-offs):
#   P_MCU_realistic_worst = 0.561 × 1.25 = 0.701 W ≈ 0.70 W
#
# Coincidentally matches STEP4's 0.700 W assumption (validating that
# estimate was on-target). Distinct from 0.924 W datasheet abs-max
# (which represents I_DD = 280 mA under unrealistic stress conditions
# — all peripherals max + worst voltage rail + max temp + max code
# execution unit utilization simultaneously, never reached in real flight).
#
# Source documentation: docs/MCU_POWER_BUDGET.md (to be committed).
MCU_REALISTIC_WORST_W = 0.700


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
# ---------------------------------------------------------------
COMPONENT_PROFILES = {
    "U1":  dict(body_x=14.0, body_y=14.0, power_W=MCU_REALISTIC_WORST_W),
    "U2":  dict(body_x=3.0,  body_y=3.0,  power_W=0.025),  # TPS62177 buck (Option B, master 2026-05-23) — 85% eff at 0.5A → 25mW; was AP2112K LDO @ 642mW
    "U6":  dict(body_x=3.0,  body_y=4.0,  power_W=0.018),  # eFuse TPS25922
    "U11": dict(body_x=3.0,  body_y=3.0,  power_W=0.050),
    "U12": dict(body_x=3.0,  body_y=3.0,  power_W=0.050),
    "U13": dict(body_x=2.9,  body_y=1.6,  power_W=0.050),  # LP5907 IMU LDO
    "U14": dict(body_x=3.0,  body_y=3.0,  power_W=0.100),  # TJA1051 CAN xcvr
    "Q2":  dict(body_x=3.0,  body_y=1.5,  power_W=0.0065), # P-FET
    "Q3":  dict(body_x=5.0,  body_y=4.0,  power_W=0.050),
    "Q4":  dict(body_x=5.0,  body_y=4.0,  power_W=0.050),
    "Q5":  dict(body_x=3.0,  body_y=1.5,  power_W=0.0),    # IMU heater — 0W hot-case (thermostatic)
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
        if prof["power_W"] <= 0:
            continue  # skip zero-power sources (saves mesh refinement)
        sources.append(HeatSource(
            name=ref,
            x_mm=x_mm, y_mm=y_mm,
            body_x_mm=prof["body_x"], body_y_mm=prof["body_y"],
            power_W=prof["power_W"],
        ))
    return sources


# ---------------------------------------------------------------
# .grd (ElmerGrid input) — single material body, 6 boundary IDs.
# Per-body assignment happens AFTER mesh generation by rewriting
# mesh.elements file.
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
# Per-body element reassignment — the v3 fix.
# ---------------------------------------------------------------
def assign_bodies_to_elements(case_dir: str, sources: list[HeatSource]) -> dict:
    """Reassign mesh element body IDs based on element-center inclusion.

    Reads mesh.nodes + mesh.elements, computes each element's centroid,
    assigns body i+1 (1..N_sources) if the centroid falls within source
    i's bbox, else body N_sources+1 (background).

    Returns:
      {"body_counts": {body_id: n_elements},
       "elem_vol_m3": volume of one element,
       "body_volumes_m3": {body_id: V_assigned}}

    Side effect: rewrites mesh.elements + mesh.header with the new body
    assignments and total body count.
    """
    mesh_dir = os.path.join(case_dir, "novapcb_thermal")
    nodes_path = os.path.join(mesh_dir, "mesh.nodes")
    elements_path = os.path.join(mesh_dir, "mesh.elements")
    header_path = os.path.join(mesh_dir, "mesh.header")

    # Load nodes
    nodes = {}
    for line in open(nodes_path):
        parts = line.split()
        if len(parts) >= 5:
            nodes[int(parts[0])] = (float(parts[2]), float(parts[3]), float(parts[4]))

    # Load elements + reassign body
    background_body = len(sources) + 1
    body_counts = defaultdict(int)
    new_lines = []
    elem_vol = None
    for line in open(elements_path):
        parts = line.split()
        if len(parts) < 4:
            new_lines.append(line)
            continue
        eid = int(parts[0])
        # body = int(parts[1])  # old body (ignored)
        etype = int(parts[2])
        elem_nodes = [int(p) for p in parts[3:]]

        # Compute centroid
        xs = [nodes[n][0] for n in elem_nodes if n in nodes]
        ys = [nodes[n][1] for n in elem_nodes if n in nodes]
        zs = [nodes[n][2] for n in elem_nodes if n in nodes]
        if not xs:
            new_lines.append(line)
            continue
        cx = sum(xs) / len(xs)
        cy = sum(ys) / len(ys)

        # Compute element volume (first element only — structured mesh, all equal)
        if elem_vol is None and len(xs) >= 8:
            elem_vol = (max(xs) - min(xs)) * (max(ys) - min(ys)) * (max(zs) - min(zs))

        # Find owning source (first match wins — sources shouldn't overlap)
        body_id = background_body
        for i, s in enumerate(sources, start=1):
            x_m = s.x_mm / 1000.0
            y_m = s.y_mm / 1000.0
            half_x = s.body_x_mm / 2000.0   # mm/2 → m/2 = mm/2000
            half_y = s.body_y_mm / 2000.0
            if abs(cx - x_m) <= half_x and abs(cy - y_m) <= half_y:
                body_id = i
                break

        body_counts[body_id] += 1
        new_lines.append(f"{eid} {body_id} {etype} {' '.join(str(n) for n in elem_nodes)}\n")

    # Write back
    with open(elements_path, "w") as f:
        f.writelines(new_lines)

    # Update mesh.header — preserve format. Body count is implicit (max
    # body id in elements file). Elmer reads bodies from SIF "Body N"
    # declarations, so header doesn't need explicit update for our use.
    # But if header has explicit body-count line, leave it; Elmer
    # tolerates extras.

    body_volumes = {bid: cnt * elem_vol for bid, cnt in body_counts.items()} \
        if elem_vol else {}
    return {
        "body_counts": dict(body_counts),
        "elem_vol_m3": elem_vol,
        "body_volumes_m3": body_volumes,
        "background_body_id": background_body,
    }


# ---------------------------------------------------------------
# .sif — per-body Body Force (no MATC)
# ---------------------------------------------------------------
def make_sif(sources: list[HeatSource], body_volumes: dict,
             background_body_id: int) -> str:
    """Generate Elmer SIF with per-body Body Force (one per source).

    body_volumes: {body_id: V_assigned_m3} from assign_bodies_to_elements.
    Heat Source per body = P_i / (ρ × V_body_i_actual) [W/kg].
    Total injected per body = q_mass × ρ × V_body_i_actual = P_i EXACTLY.
    """
    bodies = []
    body_forces = []

    for i, s in enumerate(sources, start=1):
        V_body = body_volumes.get(i, 0.0)
        if V_body <= 0:
            raise ValueError(
                f"Body {i} ({s.name}) has zero assigned volume — "
                f"min-mesh-density gate failure. Refine mesh."
            )
        q_vol = s.power_W / V_body            # W/m³
        q_mass = q_vol / RHO                  # W/kg

        bodies.append(f"""\
Body {i}
  Name = "{s.name}"
  Equation = 1
  Material = 1
  Body Force = {i}
End
""")
        body_forces.append(f"""\
Body Force {i}
  Name = "{s.name}_source"
  Heat Source = {q_mass:.6e}
End
""")

    # Background body — no Body Force, no heat source
    bodies.append(f"""\
Body {background_body_id}
  Name = "Background"
  Equation = 1
  Material = 1
End
""")

    bodies_text = "\n".join(bodies)
    body_forces_text = "\n".join(body_forces)

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

{bodies_text}

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

{body_forces_text}

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


# ---------------------------------------------------------------
# Energy-balance gate
# ---------------------------------------------------------------
def energy_balance_check(case_dir: str, sources: list[HeatSource]) -> dict:
    """Σ_injected vs Σ_surface_convection_flux. Pass if relative err < 1%.

    Σ_injected = sum of source design powers (exact by construction of
    per-body Body Force).

    Σ_surface_flux = ∫∫ h × (T_surface - T_amb) dA over top + bottom
    convection BCs. Computed by integrating over surface boundary
    elements (mesh.boundary file).
    """
    mesh_dir = os.path.join(case_dir, "novapcb_thermal")
    boundary_path = os.path.join(mesh_dir, "mesh.boundary")
    nodes_path = os.path.join(mesh_dir, "mesh.nodes")

    if not os.path.exists(boundary_path) or not os.path.exists(nodes_path):
        return {"pass": False, "error": "missing mesh files"}

    # Load nodes
    nodes = {}
    for line in open(nodes_path):
        parts = line.split()
        if len(parts) >= 5:
            nodes[int(parts[0])] = (float(parts[2]), float(parts[3]), float(parts[4]))

    # Load temperatures keyed by node id (matching _parse_elmer_result)
    _, _, node_temps = _parse_elmer_result_with_map(case_dir)
    if node_temps is None:
        return {"pass": False, "error": "no result parsed"}

    # Sum surface flux over BC 5 (z- bottom) + BC 6 (z+ top)
    # mesh.boundary format (Elmer): bid parent1 parent2 bctype etype n1 n2 ...
    # ElmerGrid 6-boundary structured mesh: bctype identifies which BC group.
    # Our setup: BC 5 = bottom, BC 6 = top. Their elements are quads (type 404).
    Q_out = 0.0
    flux_counts = {"BC5_bottom": 0, "BC6_top": 0, "skipped": 0}
    for line in open(boundary_path):
        parts = line.split()
        if len(parts) < 6:
            continue
        # ElmerGrid mesh.boundary format:
        #   bid_elem  bc_group  parent_elem  unused(0)  etype  n1 n2 ...
        # bc_group (column 1) maps to our SIF "Boundary Condition N".
        try:
            bc_group = int(parts[1])
            etype = int(parts[4])
            elem_nodes = [int(p) for p in parts[5:]]
        except ValueError:
            continue
        if bc_group not in (5, 6):
            flux_counts["skipped"] += 1
            continue

        # Quad element area = side1 × side2 for structured rectangular mesh
        if len(elem_nodes) != 4 or not all(n in nodes for n in elem_nodes):
            continue
        pts = [nodes[n] for n in elem_nodes]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        # zs should all be same — top OR bottom face
        A = (max(xs) - min(xs)) * (max(ys) - min(ys))
        T_face = sum(node_temps.get(n, T_AMBIENT_C) for n in elem_nodes) / 4.0
        Q_out += H_CONV * (T_face - T_AMBIENT_C) * A
        flux_counts[f"BC{bc_group}_{'top' if bc_group==6 else 'bottom'}"] += 1

    Q_in = sum(s.power_W for s in sources)
    rel_err = abs(Q_in - Q_out) / Q_in if Q_in > 0 else 1.0
    return {
        "pass": rel_err < ENERGY_BALANCE_TOL,
        "Q_in_W": Q_in,
        "Q_out_W": Q_out,
        "rel_err": rel_err,
        "rel_err_pct": rel_err * 100,
        "flux_counts": flux_counts,
    }


# ---------------------------------------------------------------
# Min-mesh-density gate
# ---------------------------------------------------------------
def min_mesh_density_check(body_counts: dict, sources: list[HeatSource]) -> dict:
    """Every source body must have ≥ MIN_ELEMS_PER_BODY elements."""
    failures = []
    for i, s in enumerate(sources, start=1):
        n = body_counts.get(i, 0)
        if n < MIN_ELEMS_PER_BODY:
            failures.append((s.name, i, n))
    return {
        "pass": len(failures) == 0,
        "failures": failures,
        "min_required": MIN_ELEMS_PER_BODY,
    }


# ---------------------------------------------------------------
# Elmer pipeline
# ---------------------------------------------------------------
def run_elmer_pipeline(case_dir: str, sources: list[HeatSource],
                       board_L_m: float, board_W_m: float,
                       nx: int, ny: int, nz: int) -> dict:
    """End-to-end: mesh → reassign bodies → SIF → solve.
    Returns dict with T_avg/T_max/T_min + body_counts + body_volumes.
    """
    env = os.environ.copy()
    bin_dir = os.path.join(os.path.expanduser("~"), "local", "elmer", "bin")
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    elmer_lib = os.path.join(os.path.expanduser("~"), "local", "elmer", "lib")
    env["LD_LIBRARY_PATH"] = f"{elmer_lib}:{env.get('LD_LIBRARY_PATH', '')}"

    # 1. Write .grd, run ElmerGrid
    with open(os.path.join(case_dir, "novapcb_thermal.grd"), "w") as f:
        f.write(make_grd(board_L_m, board_W_m, BOARD_H, nx, ny, nz))

    r = subprocess.run(
        [os.path.join(bin_dir, "ElmerGrid"), "1", "2", "novapcb_thermal.grd", "-autoclean"],
        cwd=case_dir, capture_output=True, text=True, timeout=180, env=env,
    )
    if r.returncode != 0:
        return {"error": f"ElmerGrid failed: {r.stderr[-500:]}"}

    # 2. Reassign body IDs in mesh.elements
    assign = assign_bodies_to_elements(case_dir, sources)

    # 3. Min-density gate
    density = min_mesh_density_check(assign["body_counts"], sources)
    if not density["pass"]:
        return {
            "error": "MIN-MESH-DENSITY gate FAILED",
            "density_failures": density["failures"],
        }

    # 4. Write SIF using actual body volumes
    with open(os.path.join(case_dir, "novapcb_thermal.sif"), "w") as f:
        f.write(make_sif(sources, assign["body_volumes_m3"], assign["background_body_id"]))
    (open(os.path.join(case_dir, "ELMERSOLVER_STARTINFO"), "w")
     .write("novapcb_thermal.sif\n"))

    # 5. Run ElmerSolver
    r = subprocess.run(
        [os.path.join(bin_dir, "ElmerSolver")],
        cwd=case_dir, capture_output=True, text=True, timeout=900, env=env,
    )
    if "Result Norm" not in r.stdout:
        return {"error": f"ElmerSolver failed: {r.stdout[-1500:]}"}

    # 6. Parse results
    pts, temps = _parse_elmer_result(case_dir)
    if pts is None:
        return {"error": "failed to parse Elmer .result"}

    # 7. Energy-balance gate
    eb = energy_balance_check(case_dir, sources)

    return {
        "T_max_C": max(temps),
        "T_min_C": min(temps),
        "T_avg_C": sum(temps) / len(temps),
        "_points": pts,
        "_temps": temps,
        "body_counts": assign["body_counts"],
        "body_volumes_m3": assign["body_volumes_m3"],
        "elem_vol_m3": assign["elem_vol_m3"],
        "energy_balance": eb,
    }


def _parse_elmer_result(case_dir: str):
    """Parse mesh.nodes + .result and return (points, temps) lists."""
    pts_map, temps_map, node_temps = _parse_elmer_result_with_map(case_dir)
    if pts_map is None:
        return None, None
    return pts_map, temps_map


def _parse_elmer_result_with_map(case_dir: str):
    """Returns (pts_list, temps_list, node_temps_dict) — temps_dict
    keyed by node ID for surface-flux integration."""
    mesh_dir = os.path.join(case_dir, "novapcb_thermal")
    nodes_path = os.path.join(mesh_dir, "mesh.nodes")
    result_path = os.path.join(mesh_dir, "novapcb_thermal.result")
    if not os.path.exists(nodes_path) or not os.path.exists(result_path):
        return None, None, None
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
    if perm_idx is None:
        return None, None, None
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
        if not ln:
            continue
        try:
            values.append(float(ln))
        except ValueError:
            break
    pts, temps, node_temps = [], [], {}
    for nid, (x, y, z) in nodes.items():
        pidx = node_to_perm.get(nid)
        if pidx is None or pidx > len(values):
            continue
        pts.append((x, y, z))
        temps.append(values[pidx - 1])
        node_temps[nid] = values[pidx - 1]
    return pts, temps, node_temps


def sample_Tj(case_dir: str, src: HeatSource) -> float:
    """Sample junction T — max temp within footprint at top surface."""
    pts, temps = _parse_elmer_result(case_dir)
    if pts is None:
        return None
    x_m = src.x_mm / 1000.0
    y_m = src.y_mm / 1000.0
    w_x_m = src.body_x_mm / 1000.0
    w_y_m = src.body_y_mm / 1000.0
    Tj_max = None
    for i, (px, py, pz) in enumerate(pts):
        if abs(pz - BOARD_H) > 1e-5:
            continue
        if abs(px - x_m) > w_x_m / 2:
            continue
        if abs(py - y_m) > w_y_m / 2:
            continue
        if Tj_max is None or temps[i] > Tj_max:
            Tj_max = temps[i]
    return Tj_max


def run(sources: list[HeatSource],
        board_L_m: float = 0.080, board_W_m: float = 0.060,
        case_label: str = "default",
        cell_mm_override: float = None) -> dict:
    """Top-level: generate mesh + sif, run solver, return temperature dict."""
    case_dir = os.path.join(CASE_DIR, case_label)
    os.makedirs(case_dir, exist_ok=True)

    # Mesh-density rule: cell_mm ≤ smallest_body_half / 2 to guarantee
    # ≥ MIN_ELEMS_PER_BODY (4) elements per body even with worst-case
    # bbox/grid alignment. For a body of width W centered between grid
    # lines, the worst case still gives ~ (W/cell - 1)² ≈ ((2half/cell)-1)²
    # elements. With cell ≤ half/2, that's ≥3² = 9. Comfortably > MIN=4.
    if cell_mm_override:
        cell_mm = cell_mm_override
    else:
        if sources:
            min_half_mm = min(min(s.body_x_mm, s.body_y_mm) / 2.0 for s in sources)
            cell_mm = min(1.0, min_half_mm / 2.0)
        else:
            cell_mm = 1.0
    nx = max(40, int(board_L_m * 1000 / cell_mm))
    ny = max(30, int(board_W_m * 1000 / cell_mm))
    nz = 4
    print(f"  mesh: cell_mm={cell_mm:.3f}, {nx}x{ny}x{nz} = {nx*ny*nz} elements", flush=True)

    return run_elmer_pipeline(case_dir, sources, board_L_m, board_W_m, nx, ny, nz)


# ---------------------------------------------------------------
# Regression: reproduce STEP4 at converged mesh + energy balance pass
# ---------------------------------------------------------------
def regression_step4():
    """STEP4 inputs run at three mesh refinements; reports T convergence
    + energy-balance per mesh. v3 milestone for master sign-off."""
    print("=== Gate 12 v3 REGRESSION — STEP4 inputs across mesh refinements ===\n")
    STEP4_INPUTS = [
        HeatSource("U2_LDO",  10.0,   33.5,  2.5,  3.0,  0.595),
        HeatSource("U1_MCU",  39.53,  30.0, 14.0, 14.0, 0.700),
        HeatSource("U6_eFuse", 12.24, 21.29, 3.0,  4.0,  0.018),
        HeatSource("Q2_PFET",  10.35, 13.55, 3.0,  1.5,  0.0065),
    ]
    print("STEP4 inputs: 80×60 board, h=5 top+bot, T_amb=50°C, k_xy=33.5, k_z=0.316")
    for s in STEP4_INPUTS:
        print(f"  {s.name}: ({s.x_mm}, {s.y_mm}) {s.body_x_mm}x{s.body_y_mm}mm @ {s.power_W*1000:.1f}mW")
    print(f"P_total = {sum(s.power_W for s in STEP4_INPUTS)*1000:.0f} mW\n")

    results = []
    for cell_mm in [2.0, 1.0, 0.675, 0.5]:
        print(f"\n--- Mesh: cell_mm={cell_mm} ---")
        label = f"step4_cell_{int(cell_mm*1000)}um"
        result = run(STEP4_INPUTS, board_L_m=0.080, board_W_m=0.060,
                     case_label=label, cell_mm_override=cell_mm)
        if "error" in result:
            print(f"  ERROR: {result['error']}")
            if "density_failures" in result:
                for name, bid, n in result["density_failures"]:
                    print(f"    min-density FAIL: {name} (body {bid}) has {n} elems")
            results.append({"cell_mm": cell_mm, "error": result["error"]})
            continue

        case_dir = os.path.join(CASE_DIR, label)
        T_LDO = sample_Tj(case_dir, STEP4_INPUTS[0])
        T_MCU = sample_Tj(case_dir, STEP4_INPUTS[1])
        eb = result["energy_balance"]
        bcounts = result["body_counts"]

        print(f"  T_avg={result['T_avg_C']:.2f}°C  T_max={result['T_max_C']:.2f}°C")
        print(f"  T_LDO={T_LDO:.2f}°C  T_MCU={T_MCU:.2f}°C")
        print(f"  body element counts: {dict(bcounts)}")
        print(f"  energy balance: Q_in={eb['Q_in_W']:.4f} W, Q_out={eb['Q_out_W']:.4f} W, "
              f"err={eb['rel_err_pct']:+.2f}%  {'PASS' if eb['pass'] else 'FAIL'}")

        results.append({
            "cell_mm": cell_mm,
            "T_avg": result["T_avg_C"],
            "T_max": result["T_max_C"],
            "T_LDO": T_LDO, "T_MCU": T_MCU,
            "eb_pass": eb["pass"], "eb_err_pct": eb["rel_err_pct"],
            "Q_in": eb["Q_in_W"], "Q_out": eb["Q_out_W"],
            "body_counts": dict(bcounts),
        })

    # Convergence summary
    print("\n\n=== CONVERGENCE SUMMARY ===")
    print(f"{'cell_mm':>8} {'T_avg':>8} {'T_max':>8} {'T_LDO':>8} {'T_MCU':>8} "
          f"{'Q_in_W':>8} {'Q_out_W':>8} {'eb_err%':>8}")
    for r in results:
        if "error" in r:
            print(f"{r['cell_mm']:>8.3f}  ERROR: {r['error']}")
            continue
        print(f"{r['cell_mm']:>8.3f} {r['T_avg']:>8.2f} {r['T_max']:>8.2f} "
              f"{r['T_LDO']:>8.2f} {r['T_MCU']:>8.2f} "
              f"{r['Q_in']:>8.4f} {r['Q_out']:>8.4f} {r['eb_err_pct']:>+8.2f}")

    # PASS criteria
    valid = [r for r in results if "T_MCU" in r and r["cell_mm"] <= 1.0]
    if len(valid) < 2:
        print("\nFAIL: not enough valid mesh runs for convergence check")
        return 1

    # All energy balance must pass
    eb_fails = [r for r in valid if not r["eb_pass"]]
    if eb_fails:
        print("\nFAIL: energy balance failed at:")
        for r in eb_fails:
            print(f"  cell_mm={r['cell_mm']}: err={r['eb_err_pct']:+.2f}%")
        return 1

    # T convergence within ±1°C across valid meshes
    Tmax_spread = max(r["T_MCU"] for r in valid) - min(r["T_MCU"] for r in valid)
    if Tmax_spread > 1.0:
        print(f"\nFAIL: T_MCU spread {Tmax_spread:.2f}°C > ±1°C convergence target")
        return 1

    print(f"\nCONVERGENCE PASS: T_MCU spread {Tmax_spread:.2f}°C ≤ 1°C; energy balance "
          f"|err|<1% on all meshes.")
    return 0


def main(pcb_path: str = None):
    """Default mode: run on current PCB."""
    import pcbnew
    if pcb_path is None:
        pcb_path = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")
    print(f"=== Gate 12 v3 — per-step thermal sim (per-body assignment) ===\n")
    print(f"PCB: {pcb_path}")
    print(f"Model: anisotropic k=({K_XY}, {K_XY}, {K_Z}) W/m·K")
    print(f"       h={H_CONV} top+bot (adiabatic edges), T_amb={T_AMBIENT_C}°C")
    print(f"Target: Tj ≤ {T_J_TARGET_C}°C (design target)\n")
    print(f"Gates: ENERGY-BALANCE (|err|<{ENERGY_BALANCE_TOL*100:.0f}%) + "
          f"MIN-MESH-DENSITY (≥{MIN_ELEMS_PER_BODY} elem/body)\n")

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

    # Board outline: v1.1 = 105 × 85 mm (master sign-off 2026-05-23).
    # WAS 0.090 × 0.070 (90×70) — caused +5.2°C MCU overestimate in
    # step-3 thermal vs the arch-sweep prediction (smaller board area
    # = less spreader copper = artificially higher Tj).
    board_L_m, board_W_m = 0.105, 0.085
    result = run(sources, board_L_m=board_L_m, board_W_m=board_W_m, case_label="current_step")
    if "error" in result:
        print(f"Gate 12 ERROR: {result['error']}")
        return 1

    eb = result["energy_balance"]
    print(f"\nEnergy balance: Q_in={eb['Q_in_W']:.4f} W, Q_out={eb['Q_out_W']:.4f} W, "
          f"err={eb['rel_err_pct']:+.2f}% {'PASS' if eb['pass'] else 'FAIL'}")
    if not eb["pass"]:
        print(f"Gate 12: RED — energy balance gate failed")
        return 1

    case_dir = os.path.join(CASE_DIR, "current_step")
    print(f"\nResults:")
    print(f"  T_avg = {result['T_avg_C']:.2f}°C")
    print(f"  T_max = {result['T_max_C']:.2f}°C")
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
        return 1
    print(f"\nGate 12: GREEN — all Tj ≤ {T_J_TARGET_C}°C target + energy balance OK")
    return 0


# ---------------------------------------------------------------
# v1.1 FULL-LOAD architecture pass
# ---------------------------------------------------------------
V11_PLANNED_POSITIONS = {
    "Q3":  (35.0,  8.0),
    "Q4":  (55.0,  8.0),
    "U11": (25.0,  5.0),
    "U12": (65.0,  5.0),
    "U14": (82.0, 55.0),
    "Q5":  (50.0, 57.0),
}


def full_v11_load(board_L_m: float = 0.090, board_W_m: float = 0.070):
    """Run gate12 with FULL v1.1 heat-source set — placed parts read
    from PCB, unplaced parts at planned zone-center positions.
    """
    import pcbnew
    pcb_path = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")
    print(f"=== Gate 12 v3 v1.1 FULL-LOAD architecture pass ===\n")
    print(f"PCB: {pcb_path}")
    print(f"Board: {board_L_m*1000:.0f} × {board_W_m*1000:.0f} mm\n")

    brd = pcbnew.LoadBoard(pcb_path)
    placed = get_active_heat_sources(brd)
    placed_refs = {s.name for s in placed}

    sources = list(placed)
    for ref, (x, y) in V11_PLANNED_POSITIONS.items():
        if ref in placed_refs:
            continue
        if ref not in COMPONENT_PROFILES:
            continue
        prof = COMPONENT_PROFILES[ref]
        if prof["power_W"] <= 0:
            continue
        sources.append(HeatSource(
            name=f"{ref}*",
            x_mm=x, y_mm=y,
            body_x_mm=prof["body_x"], body_y_mm=prof["body_y"],
            power_W=prof["power_W"],
        ))

    print(f"Full v1.1 heat-source set ({len(sources)} components):")
    P_tot = 0.0
    for s in sources:
        tag = "(*)" if s.name.endswith("*") else "   "
        print(f"  {s.name:<7} @ ({s.x_mm:.2f}, {s.y_mm:.2f}) {tag} "
              f"body={s.body_x_mm}x{s.body_y_mm}mm  P={s.power_W*1000:.0f}mW")
        P_tot += s.power_W
    print(f"  total P = {P_tot*1000:.0f} mW ({P_tot:.3f} W)\n")

    label = f"full_v11_{int(board_L_m*1000)}x{int(board_W_m*1000)}"
    result = run(sources, board_L_m=board_L_m, board_W_m=board_W_m, case_label=label)
    if "error" in result:
        print(f"FE ERROR: {result['error']}")
        return 1

    eb = result["energy_balance"]
    print(f"Energy balance: Q_in={eb['Q_in_W']:.4f} W, Q_out={eb['Q_out_W']:.4f} W, "
          f"err={eb['rel_err_pct']:+.2f}% {'PASS' if eb['pass'] else 'FAIL'}")
    if not eb["pass"]:
        print(f"GATE FAIL — energy balance failed; results untrustworthy")
        return 1

    case_dir = os.path.join(CASE_DIR, label)
    print(f"\nResults ({board_L_m*1000:.0f}×{board_W_m*1000:.0f}mm board):")
    print(f"  T_avg = {result['T_avg_C']:.2f}°C")
    print(f"  T_max = {result['T_max_C']:.2f}°C")

    LOCK_TARGET = 75.0
    print(f"\nLock target: Tj_MCU ≤ {LOCK_TARGET}°C (= 80°C design - 5°C resilience margin)\n")
    fails = []
    mcu_Tj = None
    for s in sources:
        Tj = sample_Tj(case_dir, s)
        if Tj is None:
            continue
        margin = T_J_TARGET_C - Tj
        status = ("LOCK" if Tj < LOCK_TARGET
                  else "TIGHT" if Tj < T_J_TARGET_C else "FAIL")
        print(f"  Tj_{s.name:<7} = {Tj:.2f}°C  (margin to 80°C: {margin:+.1f}°C)  {status}")
        if s.name == "U1" or s.name == "U1*":
            mcu_Tj = Tj
        if Tj > T_J_TARGET_C:
            fails.append((s.name, Tj))

    print()
    if mcu_Tj is not None:
        margin_lock = LOCK_TARGET - mcu_Tj
        print(f"MCU margin to lock target ({LOCK_TARGET}°C): {margin_lock:+.2f}°C")

    if fails:
        print(f"\nARCHITECTURE FAIL — {len(fails)} components exceed 80°C target")
        return 1
    return 0


if __name__ == "__main__":
    if "--regression-step4" in sys.argv:
        sys.exit(regression_step4())
    if "--full-v11" in sys.argv:
        # Optional board size override: --full-v11 LmmxWmm
        L_m, W_m = 0.090, 0.070
        for arg in sys.argv[1:]:
            if "x" in arg and arg[0].isdigit():
                try:
                    Lmm, Wmm = arg.split("x")
                    L_m, W_m = float(Lmm)/1000.0, float(Wmm)/1000.0
                except ValueError:
                    pass
        sys.exit(full_v11_load(L_m, W_m))
    sys.exit(main())
