#!/usr/bin/env python3
"""Gate 12 — per-step thermal sim, PARAMETERIZED v1.1 heat-source set.

Replaces the U1-only gate12_thermal_U1.py per master RF-2 directive
2026-05-23 (HARD GATE before B integration PR): gate12 must accept a
parameterized heat-source list so each step adds the components that
have been placed.

For Steps 1-4 the active set is U1-only (same as the old script). For
Step 5 (B integration) U2 (AP2112K-3.3 main LDO) is added — first
real new heat source. Per-step list:

  Step 1 (C only):       U1 (STM32H743)              0.5 W
  Step 2 (E added):      U1                          0.5 W
  Step 3 (F added):      U1                          0.5 W (U5 ESD: ~10mW, ignored)
  Step 4 (G added):      U1, U14 (CAN xcvr TJA1051)  ~0.6 W
  Step 5 (B added):      + U2 (AP2112K LDO)          + 0.5 W
  Step 6 (A added):      + U6 (eFuse), Q3/Q4 (OR-FETs), U11/U12 (BEC inputs)
  Step 7 (D added):      + U13 (LP5907 IMU LDO), Q5 (IMU heater dissipator)
  Step 8 (H added):      no new significant sources

Same Elmer 3D thin-slab FE (90 × 70 × 1.6 mm FR4 bare board, no copper
planes) used for the U1-only version — validated 1.00× vs 1D analytical
in commit 71 (`sims/validation/VALIDATION_RESULTS.md` row #3).

Heat Source convention: W/kg (per unit MASS). Elmer multiplies by
Density. Setting raw W/m³ over-sources by the density factor. See the
1.00× validation reference for the lesson.
"""
import os
import sys
import re
import subprocess
from dataclasses import dataclass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ELMER = os.path.join(os.path.expanduser("~"), "local", "elmer", "bin", "ElmerSolver")

CASE = os.path.join(HERE, "thermal", "case.sif")
CASE_DIR = os.path.join(HERE, "thermal")


@dataclass
class HeatSource:
    """A discrete heat-source volume on the board."""
    name: str       # e.g. "U1", "U2"
    x_mm: float     # body center X (mm)
    y_mm: float     # body center Y (mm)
    body_x_mm: float  # body extent X (mm)
    body_y_mm: float  # body extent Y (mm)
    power_W: float


# ---------------------------------------------------------------
# Per-component thermal profile registry — single source of truth.
# All numbers traceable to:
#   - U1 STM32H743VIT6 LQFP-100: ST DS12110, body 14x14mm, P_max 0.5W at 480MHz
#   - U2 AP2112K-3.3 SOT-25: Diodes datasheet, body 2.9x1.6mm,
#     worst-case 1.7V drop × ~300mA = 0.51W → use 0.5W
#   - U13 LP5907MFX-3.3 SOT-23-5: TI datasheet, body 2.9x1.6mm,
#     IMU rail ~20mA × 1.7V drop = 0.034W → use 0.05W (rounded up)
#   - U14 TJA1051TK/3 VSON-8: NXP datasheet, body 3x3mm, typ 100mW
#   - U6 TPS25946 (eFuse, ~SOT-23-6): TI, normal-mode ~50mW
#   - Q3/Q4 OR-FETs: standard SO-8 MOSFET, ~50mW each typical
#   - Q5 IMU heater: TBD (heater is the SIM PURPOSE — sized by output)
# ---------------------------------------------------------------
COMPONENT_PROFILES = {
    "U1":  dict(body_x=14.0, body_y=14.0, power_W=0.50),   # STM32H743 LQFP-100
    "U2":  dict(body_x=2.9,  body_y=1.6,  power_W=0.50),   # AP2112K main LDO
    "U6":  dict(body_x=2.9,  body_y=1.6,  power_W=0.05),   # eFuse normal mode
    "U11": dict(body_x=3.0,  body_y=3.0,  power_W=0.05),   # OR-ing FET / BEC input
    "U12": dict(body_x=3.0,  body_y=3.0,  power_W=0.05),
    "U13": dict(body_x=2.9,  body_y=1.6,  power_W=0.05),   # LP5907 IMU LDO
    "U14": dict(body_x=3.0,  body_y=3.0,  power_W=0.10),   # TJA1051 CAN xcvr
    "Q3":  dict(body_x=5.0,  body_y=4.0,  power_W=0.05),   # OR-FET SO-8
    "Q4":  dict(body_x=5.0,  body_y=4.0,  power_W=0.05),
    "Q5":  dict(body_x=3.0,  body_y=1.5,  power_W=0.30),   # IMU heater (initial estimate)
}


def get_active_heat_sources(brd) -> list[HeatSource]:
    """Read PCB, return heat sources for currently-placed components.

    Components are only included if their refdes is in COMPONENT_PROFILES
    AND the footprint is placed on the visible board area (X < 100mm —
    the parking convention in step* scripts puts un-placed parts at X >= 100).
    """
    import pcbnew  # local import — only needed at runtime, not at module load
    sources = []
    for fp in brd.GetFootprints():
        ref = fp.GetReference()
        if ref not in COMPONENT_PROFILES:
            continue
        p = fp.GetPosition()
        x_mm, y_mm = p.x / 1e6, p.y / 1e6
        if x_mm >= 100:   # parked / not yet placed on visible board
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
# Mesh + .sif generation (parameterized over heat-source list)
# ---------------------------------------------------------------
def gen_mesh(sources: list[HeatSource], nx: int, ny: int, nz: int = 3) -> None:
    """Hex mesh, NX × NY × NZ. Each heat-source gets its own body ID
    (body 1, 2, 3, ...). The rest of the board is body 0 (last+1).

    The mesh assigns each hex element to the body whose footprint
    bounding box contains the element's center. If multiple footprints
    overlap an element (placement collision), the LATER one in the list
    wins — placement gates 1/2 should prevent overlap.
    """
    out = os.path.join(CASE_DIR, "mesh")
    os.makedirs(out, exist_ok=True)
    LX, LY, LZ = 90.0e-3, 70.0e-3, 1.6e-3

    nxp1, nyp1, nzp1 = nx + 1, ny + 1, nz + 1
    n_nodes = nxp1 * nyp1 * nzp1

    def nid(i, j, k):
        return k * (nxp1 * nyp1) + j * nxp1 + i + 1

    bg_body = len(sources) + 1   # background = last body ID

    # Nodes
    with open(f"{out}/mesh.nodes", "w") as f:
        for k in range(nzp1):
            for j in range(nyp1):
                for i in range(nxp1):
                    x = i * LX / nx
                    y = j * LY / ny
                    z = k * LZ / nz
                    f.write(f"{nid(i,j,k)} -1 {x:.8f} {y:.8f} {z:.8f}\n")

    # Hex elements (type 808). Body assignment per element center.
    with open(f"{out}/mesh.elements", "w") as f:
        eid = 1
        for k in range(nz):
            for j in range(ny):
                for i in range(nx):
                    cx = (i + 0.5) * LX / nx
                    cy = (j + 0.5) * LY / ny
                    body = bg_body  # default to background
                    for idx, src in enumerate(sources, start=1):
                        x0 = (src.x_mm - src.body_x_mm/2) * 1e-3
                        x1 = (src.x_mm + src.body_x_mm/2) * 1e-3
                        y0 = (src.y_mm - src.body_y_mm/2) * 1e-3
                        y1 = (src.y_mm + src.body_y_mm/2) * 1e-3
                        if x0 <= cx <= x1 and y0 <= cy <= y1:
                            body = idx
                            break
                    n0 = nid(i,   j,   k);    n1 = nid(i+1, j,   k)
                    n2 = nid(i+1, j+1, k);    n3 = nid(i,   j+1, k)
                    n4 = nid(i,   j,   k+1);  n5 = nid(i+1, j,   k+1)
                    n6 = nid(i+1, j+1, k+1);  n7 = nid(i,   j+1, k+1)
                    f.write(f"{eid} {body} 808 {n0} {n1} {n2} {n3} {n4} {n5} {n6} {n7}\n")
                    eid += 1

    # Boundary faces — same as U1-only version (all 6 sides with same h)
    bnd_lines = []
    bid = 1
    # bnd 1: z=0 (bottom)
    for j in range(ny):
        for i in range(nx):
            n0 = nid(i,   j,   0); n1 = nid(i+1, j,   0)
            n2 = nid(i+1, j+1, 0); n3 = nid(i,   j+1, 0)
            bnd_lines.append(f"{bid} 1 {j*nx + i + 1} 0 404 {n0} {n1} {n2} {n3}"); bid += 1
    # bnd 2: z=t (top)
    base = (nz-1) * nx * ny
    for j in range(ny):
        for i in range(nx):
            n0 = nid(i,   j,   nz); n1 = nid(i+1, j,   nz)
            n2 = nid(i+1, j+1, nz); n3 = nid(i,   j+1, nz)
            bnd_lines.append(f"{bid} 2 {base + j*nx + i + 1} 0 404 {n3} {n2} {n1} {n0}"); bid += 1
    # bnd 3, 4: x=0 (W), x=L (E)
    for k in range(nz):
        for j in range(ny):
            parent_w = k*nx*ny + j*nx + 1
            n0 = nid(0, j,   k); n1 = nid(0, j+1, k)
            n2 = nid(0, j+1, k+1); n3 = nid(0, j,   k+1)
            bnd_lines.append(f"{bid} 3 {parent_w} 0 404 {n0} {n1} {n2} {n3}"); bid += 1
            parent_e = k*nx*ny + j*nx + nx
            n0 = nid(nx, j,   k); n1 = nid(nx, j+1, k)
            n2 = nid(nx, j+1, k+1); n3 = nid(nx, j,   k+1)
            bnd_lines.append(f"{bid} 4 {parent_e} 0 404 {n3} {n2} {n1} {n0}"); bid += 1
    # bnd 5, 6: y=0 (S), y=W (N)
    for k in range(nz):
        for i in range(nx):
            parent_s = k*nx*ny + i + 1
            n0 = nid(i,   0, k);   n1 = nid(i+1, 0, k)
            n2 = nid(i+1, 0, k+1); n3 = nid(i,   0, k+1)
            bnd_lines.append(f"{bid} 5 {parent_s} 0 404 {n3} {n2} {n1} {n0}"); bid += 1
            parent_n = k*nx*ny + (ny-1)*nx + i + 1
            n0 = nid(i,   ny, k);   n1 = nid(i+1, ny, k)
            n2 = nid(i+1, ny, k+1); n3 = nid(i,   ny, k+1)
            bnd_lines.append(f"{bid} 6 {parent_n} 0 404 {n0} {n1} {n2} {n3}"); bid += 1

    with open(f"{out}/mesh.boundary", "w") as f:
        for line in bnd_lines: f.write(line + "\n")
    with open(f"{out}/mesh.header", "w") as f:
        f.write(f"{n_nodes} {nx*ny*nz} {len(bnd_lines)}\n2\n404 {len(bnd_lines)}\n808 {nx*ny*nz}\n")
    print(f"  mesh: {nx}x{ny}x{nz} = {nx*ny*nz} hex, {n_nodes} nodes, "
          f"{len(bnd_lines)} bnd quads, {len(sources)} source bodies + 1 bg", flush=True)


def gen_sif(sources: list[HeatSource]) -> None:
    """Generate .sif with one Body Force per heat source.

    Heat Source = W/kg per Elmer convention. q_HS_per_kg = q_vol / density.
    """
    t_board = 1.6e-3
    k_FR4 = 0.3
    rho_FR4 = 1850.0
    h_conv = 10.0
    T_amb = 298.15

    # Bodies: 1..N for sources, N+1 = background. All same material (FR4).
    body_sections = []
    body_force_sections = []
    for idx, src in enumerate(sources, start=1):
        A = (src.body_x_mm * 1e-3) * (src.body_y_mm * 1e-3)
        q_vol = src.power_W / (A * t_board)   # W/m³
        q_HS_per_kg = q_vol / rho_FR4
        body_sections.append(
            f"Body {idx}\n"
            f"  Equation = 1\n"
            f"  Material = 1\n"
            f"  Body Force = {idx}\n"
            f"End\n"
        )
        body_force_sections.append(
            f"Body Force {idx}\n"
            f"  Heat Source = {q_HS_per_kg:.6e}  ! W/kg — Elmer multiplies by Density\n"
            f"End\n"
        )
    bg_body = len(sources) + 1
    body_sections.append(
        f"Body {bg_body}\n"
        f"  Equation = 1\n"
        f"  Material = 1\n"
        f"End\n"
    )

    sif = f"""Header
  Mesh DB "." "mesh"
End

Simulation
  Coordinate System = Cartesian 3D
  Simulation Type = Steady State
  Steady State Max Iterations = 1
  Output Intervals = 1
  Output File = "case.result"
End

{''.join(body_sections)}

Material 1
  Heat Conductivity = {k_FR4}
  Density = {rho_FR4}
  Heat Capacity = 1000.0
End

{''.join(body_force_sections)}

Equation 1
  Active Solvers(2) = 1 2
End

Solver 1
  Equation = Heat Equation
  Procedure = "HeatSolve" "HeatSolver"
  Variable = Temperature
  Linear System Solver = Iterative
  Linear System Iterative Method = CG
  Linear System Preconditioning = ILU0
  Linear System Convergence Tolerance = 1e-10
  Linear System Max Iterations = 1000
  Steady State Convergence Tolerance = 1e-08
End

Solver 2
  Exec Solver = After Simulation
  Equation = "result output"
  Procedure = "ResultOutputSolve" "ResultOutputSolver"
  Output File Name = "case"
  Output Format = "vtu"
  Binary Output = Logical False
  Ascii Output = Logical True
End

Boundary Condition 1
  Target Boundaries(6) = 1 2 3 4 5 6
  Heat Flux BC = Logical True
  Heat Transfer Coefficient = {h_conv}
  External Temperature = {T_amb:.4f}
End

Initial Condition 1
  Temperature = {T_amb:.4f}
End
"""
    os.makedirs(CASE_DIR, exist_ok=True)
    with open(CASE, "w") as f:
        f.write(sif)


def run() -> float:
    """Run ElmerSolver, return max T (Kelvin) from VTU."""
    r = subprocess.run([ELMER, "case.sif"], cwd=CASE_DIR,
                       capture_output=True, text=True, timeout=600)
    if "Result Norm" not in r.stdout:
        print("  ElmerSolver tail:")
        print(r.stdout[-1500:])
        return None
    vtu = os.path.join(CASE_DIR, "mesh", "case_t0001.vtu")
    if not os.path.exists(vtu):
        print(f"  WARN: no VTU at {vtu}")
        return None
    with open(vtu) as f: txt = f.read()
    m = re.search(r'<DataArray[^>]*Name="temperature"[^>]*>([\d\s\.\-eE+]+)</DataArray>', txt)
    if not m: return None
    temps = list(map(float, m.group(1).split()))
    return max(temps)


def main(pcb_path: str = None):
    import pcbnew
    if pcb_path is None:
        pcb_path = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")
    print(f"=== Gate 12 — per-step thermal sim (v1.1 parameterized) ===\n")
    print(f"PCB: {pcb_path}", flush=True)

    brd = pcbnew.LoadBoard(pcb_path)
    sources = get_active_heat_sources(brd)

    if not sources:
        print("  no heat sources detected — skipping FE run")
        return 0

    print(f"\nActive heat sources for this step:")
    P_tot = 0.0
    for s in sources:
        print(f"  {s.name:<6} @ ({s.x_mm:.2f}, {s.y_mm:.2f})  body={s.body_x_mm}x{s.body_y_mm}mm  P={s.power_W*1000:.0f}mW")
        P_tot += s.power_W
    print(f"  total P = {P_tot*1000:.0f} mW\n", flush=True)

    print(f"[1/2] Generate mesh + .sif", flush=True)
    NX, NY, NZ = 90, 70, 3
    gen_mesh(sources, NX, NY, NZ)
    gen_sif(sources)

    print(f"[2/2] Run ElmerSolver", flush=True)
    T_max_K = run()
    if T_max_K is None:
        print(f"  Gate 12: RED — FE run failed")
        return 1

    T_max_C = T_max_K - 273.15
    Tj_spec = 105.0   # STM32H7 industrial T_j max (most-constrained component)
    margin = Tj_spec - T_max_C
    print(f"  T_max  = {T_max_C:.2f} °C")
    print(f"  T_spec = {Tj_spec} °C")
    print(f"  margin = {margin:.1f} °C")
    if margin > 0:
        print(f"  Gate 12: GREEN")
        return 0
    else:
        print(f"  Gate 12: RED — T_max exceeds spec")
        return 1


if __name__ == "__main__":
    sys.exit(main())
