#!/usr/bin/env python3
"""Gate 12 — per-subsystem thermal sim: U1 worst-case T_j (Step 1).

Per docs/PLACEMENT_ROUTING_GATES.md §Gate 12 + §Gate 13:
  - Use a tool that has been validated against a canonical benchmark
    (sims/validation/VALIDATION_RESULTS.md row #3: Elmer thermal, 0.00%
    vs 1D conduction analytical → PASS).
  - Convergence-clean run (mesh-refinement study).
  - Cross-check against an independent estimate (here: analytical
    Theta_ja closed-form).

Setup — Step 1 scope (only C placed; other subsystems off-board):
  - Geometry: 90 × 70 mm board, 2D (through-thickness conduction
    folded into convective BC).
  - Heat source: U1 at center (45, 35) dissipating P=0.5 W spread
    uniformly over the 14 × 14 mm LQFP-100 body.
  - Material: FR4 (k=0.3 W/m·K).
  - BCs: convective h=10 W/m²·K to T_ambient=25°C on the top + bottom
    surfaces (effective equivalent BC at all non-heat-source area).
  - Solve steady-state T(x,y); report T_max under U1.

Cross-check (analytical, independent):
  - Theta_ja for LQFP-100 on a 4-layer PCB (typical) ≈ 30-45 °C/W
    (ST datasheet DS12110 §6.1 thermal characteristics, JESD51-7
    test board). With P=0.5 W and T_ambient=25°C:
        T_j = 25 + 0.5 * Theta_ja  ≈  40-47.5 °C
  - This is for a populated board with planes; our Step 1 has no planes
    yet, so the FE sim will report a HIGHER (more pessimistic) T_j.
"""
import os
import sys
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ELMER = os.path.join(os.path.expanduser("~"), "local", "elmer", "bin", "ElmerSolver")

CASE = os.path.join(HERE, "thermal_U1", "case.sif")
CASE_DIR = os.path.join(HERE, "thermal_U1")


def gen_mesh(nx: int, ny: int, nz: int = 3) -> None:
    """Generate Elmer-native 3D hex mesh, NX × NY × NZ hexahedra.

    Board geometry: 90 × 70 × 1.6 mm. The 1.6mm thickness is resolved
    by NZ cells so top/bottom convective BCs can be applied to the
    z=0 and z=t_board surfaces.

    Boundaries:
      1 = z=0  (bottom face, convective to ambient)
      2 = z=t  (top face, convective to ambient)
      3 = x=0  (W edge)
      4 = x=L  (E edge)
      5 = y=0  (S edge)
      6 = y=W  (N edge)

    Body assignment:
      1 = U1 footprint volume (14×14×t_board centered at 45,35)
      2 = rest of board
    """
    out = os.path.join(CASE_DIR, "mesh")
    os.makedirs(out, exist_ok=True)
    LX, LY, LZ = 90.0e-3, 70.0e-3, 1.6e-3
    U_x0, U_x1 = 0.045 - 0.007, 0.045 + 0.007
    U_y0, U_y1 = 0.035 - 0.007, 0.035 + 0.007

    nxp1, nyp1, nzp1 = nx + 1, ny + 1, nz + 1
    n_nodes = nxp1 * nyp1 * nzp1

    def nid(i, j, k):
        return k * (nxp1 * nyp1) + j * nxp1 + i + 1

    # Nodes
    with open(f"{out}/mesh.nodes", "w") as f:
        for k in range(nzp1):
            for j in range(nyp1):
                for i in range(nxp1):
                    x = i * LX / nx
                    y = j * LY / ny
                    z = k * LZ / nz
                    f.write(f"{nid(i,j,k)} -1 {x:.8f} {y:.8f} {z:.8f}\n")

    # Hex elements (type 808 in Elmer)
    with open(f"{out}/mesh.elements", "w") as f:
        eid = 1
        for k in range(nz):
            for j in range(ny):
                for i in range(nx):
                    cx = (i + 0.5) * LX / nx
                    cy = (j + 0.5) * LY / ny
                    body = 1 if (U_x0 <= cx <= U_x1 and U_y0 <= cy <= U_y1) else 2
                    # 808: 8 corners, standard ordering
                    n0 = nid(i,   j,   k);    n1 = nid(i+1, j,   k)
                    n2 = nid(i+1, j+1, k);    n3 = nid(i,   j+1, k)
                    n4 = nid(i,   j,   k+1);  n5 = nid(i+1, j,   k+1)
                    n6 = nid(i+1, j+1, k+1);  n7 = nid(i,   j+1, k+1)
                    f.write(f"{eid} {body} 808 {n0} {n1} {n2} {n3} {n4} {n5} {n6} {n7}\n")
                    eid += 1

    # Boundary quad-faces (type 404)
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
    # bnd 3: x=0 (W); 4: x=L (E)
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
    # bnd 5: y=0 (S); 6: y=W (N)
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
          f"{len(bnd_lines)} bnd quads", flush=True)


def gen_sif(power_W: float = 0.5) -> None:
    """Generate the .sif for a 3D thin-slab thermal model.

    Geometry: 90 × 70 × 1.6 mm FR4 board.
    Heat source: P=0.5W spread volumetrically over the 14×14×1.6mm
    region beneath U1 (body 1). Rest of board = body 2.
    BCs:
      bnd 1 (z=0, bottom):  Heat Transfer Coefficient h=10, T_ext=298.15
      bnd 2 (z=t, top):     Heat Transfer Coefficient h=10, T_ext=298.15
      bnd 3..6 (edges):     Heat Transfer Coefficient h=10, T_ext=298.15
        (real edges have smaller convective area but small h on FR4
         edges is fine as an upper-bound boundary effect)
    """
    A_U = 0.014 * 0.014
    t_board = 1.6e-3
    k_FR4 = 0.3              # W/m·K
    rho_FR4 = 1850.0         # kg/m³  (needed because Elmer HeatSource is W/kg, see note)
    h_conv = 10.0            # W/m²·K natural convection
    T_amb = 298.15           # K
    q_vol_U1 = power_W / (A_U * t_board)   # W/m³ intended
    # Elmer's HeatSolver expects Heat Source in W/kg (per unit MASS), then
    # internally multiplies by Density. Verified empirically against 1D
    # thin-slab analytical: with HS = q_vol / density, FE matches to 1.00×.
    # Setting HS = q_vol directly over-sources by a factor of `density`.
    q_HS_per_kg = q_vol_U1 / rho_FR4

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

Body 1
  Equation = 1
  Material = 1
  Body Force = 1
End

Body 2
  Equation = 1
  Material = 1
End

Material 1
  Heat Conductivity = {k_FR4}
  Density = {rho_FR4}
  Heat Capacity = 1000.0
End

Body Force 1
  Heat Source = {q_HS_per_kg:.6e}
End

Equation 1
  Active Solvers(2) = 1 2
End

Solver 1
  Equation = Heat Equation
  Procedure = "HeatSolve" "HeatSolver"
  Variable = Temperature
  Linear System Solver = Direct
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
    """Run ElmerSolver, parse the VTU, return max T (Kelvin)."""
    import subprocess
    r = subprocess.run([ELMER, "case.sif"], cwd=CASE_DIR,
                       capture_output=True, text=True, timeout=300)
    if "Result Norm" not in r.stdout:
        print("  ElmerSolver tail:")
        print(r.stdout[-1500:])
        return None
    # Parse VTU
    vtu = os.path.join(CASE_DIR, "mesh", "case_t0001.vtu")
    if not os.path.exists(vtu):
        print(f"  WARN: no VTU at {vtu}")
        return None
    with open(vtu) as f: txt = f.read()
    m = re.search(r'<DataArray[^>]*Name="temperature"[^>]*>([\d\s\.\-eE+]+)</DataArray>',
                   txt)
    if not m: return None
    temps = list(map(float, m.group(1).split()))
    return max(temps)


def main():
    print("=== Gate 12 — U1 worst-case T_j ===\n", flush=True)
    print("Step 1 scope: only C placed. No copper plane yet (planes are\n"
          "cross-subsystem nets, added after all subsystems are placed).\n"
          "Two estimates: (a) analytical Theta_ja from ST DS12110 §6.1\n"
          "(JESD51-7 4-layer reference board with planes); (b) Elmer 3D\n"
          "thin-slab FE bare-FR4 (no planes — worst-case bound). Both\n"
          "must show ample margin to T_j_spec = 105°C.\n\n"
          "Note 2026-05-22: the Elmer 3D body-source convention is\n"
          "**Heat Source = W/kg** (per unit MASS), not W/m³. Elmer\n"
          "internally multiplies by Density. Verified against 1D thin-\n"
          "slab analytical (q*(t/2)²/(2k)) to 1.00× match. Setting raw\n"
          "W/m³ over-sources by the density factor.\n", flush=True)

    # ---- (a) Analytical (primary) ----
    print("[1/3] Primary: analytical Theta_ja per ST DS12110 §6.1", flush=True)
    Theta_ja_min = 30.0   # °C/W; LQFP-100 JESD51-7 4-layer (best published)
    Theta_ja_max = 45.0   # °C/W; LQFP-100 2-layer / sparse plane
    P_U1 = 0.5            # W (STM32H743 at 480 MHz worst case)
    Tj_an_min = 25.0 + P_U1 * Theta_ja_min
    Tj_an_max = 25.0 + P_U1 * Theta_ja_max
    Tj_max_spec = 105.0   # STM32H7 industrial T_j max
    print(f"  Theta_ja = {Theta_ja_min}..{Theta_ja_max} °C/W (LQFP-100, ST DS12110)", flush=True)
    print(f"  P_U1     = {P_U1} W (worst case 480 MHz)", flush=True)
    print(f"  T_amb    = 25 °C", flush=True)
    print(f"  T_j (analytical) = {Tj_an_min:.1f}..{Tj_an_max:.1f} °C", flush=True)
    print(f"  T_j spec max     = {Tj_max_spec} °C", flush=True)
    margin = Tj_max_spec - Tj_an_max
    print(f"  Margin to spec   = {margin:.1f} °C (worst-case analytical)", flush=True)

    # ---- (b) Elmer 3D FE (bare FR4) ----
    print("\n[2/3] Elmer 3D thin-slab FE (bare FR4, no copper plane)", flush=True)
    fe_results = []
    for (nx, ny, nz) in [(30, 24, 3), (60, 48, 5), (90, 72, 7)]:
        os.makedirs(CASE_DIR, exist_ok=True)
        import shutil
        mesh_dir = os.path.join(CASE_DIR, "mesh")
        if os.path.exists(mesh_dir): shutil.rmtree(mesh_dir)
        gen_mesh(nx, ny, nz)
        gen_sif(power_W=P_U1)
        Tk = run()
        if Tk is None:
            print(f"  mesh {nx}x{ny}x{nz}: RUN FAILED", flush=True)
            return 1
        Tc = Tk - 273.15
        fe_results.append((nx*ny*nz, Tc))
        print(f"  {nx*ny*nz:>7} hex → T_max = {Tc:.2f} °C", flush=True)

    coarse, fine = fe_results[-2][1], fe_results[-1][1]
    delta_pct = abs(fine - coarse) / max(abs(fine - 25.0), 1e-9) * 100
    converged = delta_pct < 5.0
    print(f"  mesh convergence (medium→fine): {delta_pct:.2f}%  "
          f"{'CONVERGED (<5%)' if converged else 'not yet — needs further refinement'}", flush=True)

    Tj_FE_bare = fine
    print(f"\n  Bare-FR4 FE result: T_j = {Tj_FE_bare:.1f} °C")
    print(f"  Analytical (planes): T_j = {Tj_an_max:.1f} °C (LOWER — copper plane spreads heat)")
    print(f"  The cross-subsystem +3V3 / GND planes (added in the cross-\n"
          f"  subsystem routing PR) will bring the FE result down toward\n"
          f"  the analytical range. Step 1 is bare-FR4 worst-case.", flush=True)

    # ---- (c) Verdict ----
    print(f"\n[3/3] Verdict", flush=True)
    Tj_for_verdict = max(Tj_FE_bare, Tj_an_max)  # worst case of the two
    margin_v = Tj_max_spec - Tj_for_verdict
    if margin_v > 30:
        verdict = "GREEN — T_j worst-case has ample margin to spec"
    elif margin_v > 10:
        verdict = "YELLOW — T_j margin tight"
    else:
        verdict = "RED — T_j marginal"
    print(f"  Worst-case T_j (FE-bare or analytical-planes) = {Tj_for_verdict:.1f} °C", flush=True)
    print(f"  Spec max T_j = {Tj_max_spec} °C  →  margin = {margin_v:.1f} °C", flush=True)
    print(f"  Gate 12: {verdict}", flush=True)
    print(f"\nGate 13 cite — Elmer thermal tool VALIDATED:", flush=True)
    print(f"  • Row 3 (1D linear T): 0.00% vs analytical", flush=True)
    print(f"  • 3D body-source convention (HS = W/kg, NOT W/m³): "
          f"1.00× match vs thin-slab analytical (verified 2026-05-22)", flush=True)
    print(f"  Mesh convergence: {delta_pct:.2f}% medium→fine "
          f"({'OK' if converged else 'flag — refine before merge'}).", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
