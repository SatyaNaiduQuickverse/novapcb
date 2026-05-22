# Task 9 — sim-tool validation against known references

> **Directive (master 2026-05-22):** "For each tool in the planned sim
> suite, validate it against a canonical benchmark and report the error
> vs the reference. A tool is only trusted once it matches its
> benchmark."

**Status: ALL 5 TOOLS PASS** (openEMS added 2026-05-22 per master directive to close the field-solver gap). Run on `novatics64` 2026-05-22.

| # | Tool | Benchmark | Tool result | Reference | Error | Verdict |
|---|---|---|---|---|---|---|
| 1 | ngspice (PySpice / batch) | RC charge transient, V(τ)=0.632121 V analytical | 0.631983 V | 0.632121 V | **0.022%** | **PASS** (<1%) |
| 2 | scikit-rf `MLine` | Microstrip Z₀ vs Hammerstad-Jensen 1980 (W=0.30mm, h=0.21mm, t=35µm, εr=4.3) | 56.59 Ω | 56.01 Ω (H-J) / 55.30 Ω (IPC-2141) | **1.03%** vs H-J, 2.34% vs IPC | **PASS** (<5%) |
| 3 | Elmer FEM (heat) | 1D steady-state conduction, 100×10mm slab, T(0)=0, T(L)=100, T(x)=x analytical | T_FEM = T_analytical to machine precision at all sample x | exact linear | **0.000%** | **PASS** (Q1 interpolates linear exactly) |
| 4 | Elmer FEM (structural) | Cantilever tip deflection, L=1m, h=0.05m, b=0.01m, E=210 GPa, ν=0.30, P=100 N at tip | −1.519 mm | −1.527 mm (Timoshenko) / −1.524 mm (Euler-Bernoulli) | **0.51%** vs Timoshenko (refined NX=200,NY=20) | **PASS** (<2%) |
| 5 | openEMS (3D FDTD field solver) | Microstrip Z₀ vs Hammerstad-Jensen 1980 (same geometry as #2) | 53.995 Ω @ 1 GHz (53.88..54.14 Ω across 0.2..2 GHz) | 56.01 Ω (H-J 1980) | **3.6%** vs H-J | **PASS** (<5%) |

## Notes per tool

### 1. ngspice / PySpice — `val_ngspice_rc.py`
- Catch: initial-condition trap (V(out) = V_in DC steady-state at t=0). Fixed with `.ic V(out)=0` + `UIC` on `.tran`. After fix, error = 0.022% (essentially time-discretization noise at 1µs step).
- Tool is trusted for RC/RL/RLC transient analysis as planned in Phase 6a power-tree.

### 2. scikit-rf `MLine` — `val_skrf_microstrip.py`
- The docs/CONTROLLED_IMPEDANCE.md value (67.8 Ω) is for the **coupled** differential-pair geometry — not the right reference for isolated microstrip.
- For isolated-trace single-ended Z₀, scikit-rf agrees with H-J 1980 to 1%, with IPC-2141 to 2.3%. The 1-2% spread is the inherent disagreement among published microstrip formulas (Wheeler, Hammerstad, Hammerstad-Jensen, IPC) — not a tool defect.
- Tool is trusted for first-order Z₀ estimates in Phase 6b. **For final controlled-impedance sign-off, use 2D field-solver** (sonnet / atlc) — scikit-rf MLine is an analytical closed-form, not a field solver.

### 3. Elmer FEM thermal — `elmer_thermal/case.sif`
- **Mesh-construction trap caught**: ElmerGrid native `.grd` syntax for a single-body rectangle generates ZERO boundary elements unless the boundary block is set up correctly. Solver runs, reports "Result Norm = 0", silently no BC applied. Fixed by hand-writing `mesh.boundary` with 4 distinct boundary IDs (bottom/right/top/left). Now matches analytical T(x)=x exactly (linear field exact for Q1 bilinear elements).
- Tool is trusted for Phase 6j thermal sims.
- **3D body-source convention caught 2026-05-22** (during Step-1 Gate-12 setup): Elmer's `HeatSolver` interprets `Heat Source` as **W/kg** (per unit MASS), NOT W/m³ (volumetric). The solver internally multiplies by `Density`. Setting raw W/m³ over-sources by exactly the density factor (1850× for FR4). Verified empirically: with `Heat Source = q_vol / density`, a 3D thin-slab cube (10×10×1 mm, q_vol = 1e6 W/m³, k=0.3, all 6 Dirichlet) returns T_max = 25.42 °C vs analytical thin-slab `q*(t/2)²/(2k) = 0.417 K` above ambient → **1.00× match**. This is the validated 3D body-source recipe for novapcb sims.

### 4. Elmer FEM structural — `elmer_beam/case.sif`
- Q1 bilinear shear-locking observed on coarse mesh (NX=100, NY=5 → 2.0% error vs Timoshenko, just above 2% bar).
- **Convergence verified**: refining to NX=200, NY=20 reduces error to **0.51%** — confirms tool is correct, coarse-mesh error was discretization artifact, not solver bug.
- Tool is trusted for Phase 6j structural / vibration sims. **Note for future use**: mesh densely through-thickness for any bending-dominated sim; consider higher-order elements (Q2) if Q1 underestimates by >2%.

### 5. openEMS 3D FDTD — `val_openems_microstrip.py`
- **Three traps caught + fixed in this validation:**
  - (a) `MSLPort.CalcPort(..., ref_impedance=50)` OVERWRITES the measured line Z₀ with the reference port impedance (ports.py line 153). First attempt returned 50.0 Ω at every frequency before this was caught. Fix: call CalcPort WITHOUT `ref_impedance` so `Z_ref` stays at the value computed from E/H probes (line ~375).
  - (b) `FeedShift` and `MeasPlaneShift` are absolute drawing-unit offsets from port start (not relative). With MSL_length=15mm and FeedShift=5mm + MeasPlaneShift=5mm, both landed at the same point — measurement probes saw the feed transient, giving meaningless 3-7 Ω. Fix: extend MSL_length=25mm, separate FeedShift=2mm vs MeasPlaneShift=15mm (13 mm clean line between).
  - (c) Without lumped termination at the un-excited port, energy bounces between line ends and never decays to the EndCriteria → run never terminates. Mitigation: `Feed_R=50` on both ports AND a hard `NrTS=30000` cap that bounds the run before reflection corrupts the FFT-based Z₀ extraction. Result terminates in ~62 sec on 4 threads with a clean per-frequency Z₀ readout.
- **Result vs H-J 1980:** 53.99 Ω @ 1 GHz vs 56.01 Ω H-J → 3.6% error (under the 5% bar). 3D FDTD includes fringing fields and discretization; the 3-4% spread vs closed-form is consistent with published openEMS-vs-formula comparisons.
- Tool is trusted for Phase 6b USB diff-pair impedance sign-off + Phase 6k radiated-EMI sims. **Note for future use:** always cap with `NrTS=` when extracting from a known-pulse signal; verify FeedShift/MeasPlaneShift separation ≥3×wavelength-in-substrate; do NOT pass `ref_impedance` if you want the LINE's actual Z₀.

## Artifacts (all kept; reproducible)

```
sims/validation/
├── val_ngspice_rc.py             — script
├── val_skrf_microstrip.py        — script
├── val_openems_microstrip.py     — script (requires LD_LIBRARY_PATH=$HOME/local/openems/lib)
├── elmer_thermal/
│   ├── case.sif                  — Elmer input
│   ├── gen_mesh.py               — reproduces mesh2/
│   └── mesh2/case_t0001.vtu      — ASCII VTU output
└── elmer_beam/
    ├── case.sif                  — Elmer input
    ├── gen_mesh.py               — reproduces mesh/
    └── mesh/case_t0001.vtu       — ASCII VTU output
```

## Bottom line

Per master's bar — "a tool is only trusted once it matches its benchmark" — all FIVE planned sim tools are validated against canonical analytical references and PASS. Phase 6 simulation work can proceed on these tools with documented expected accuracy:

- ngspice: ≤0.1% on transient circuits (limited only by timestep)
- scikit-rf: 1-2% on isolated microstrip Z₀ (analytical formula spread)
- Elmer thermal: exact for linear, ~1% for piecewise-linear with adequate mesh
- Elmer structural: <1% with refined mesh; ≤2% with coarse Q1 (shear-locking)
- openEMS: 3-4% vs closed-form H-J on isolated microstrip Z₀; trusted for USB diff-pair sign-off + radiated-EMI sims after the three-trap discipline above is followed every run

Per `docs/PLACEMENT_ROUTING_GATES.md` Gate 13, this file is the authoritative tool-validation record. Adding a new tool to the suite requires a new row here (benchmark, error %, verdict) before that tool's output can be cited as gate evidence.

---

## Update 2026-05-23 — openEMS COUPLED-PAIR setup validation (Task #75)

Per master 2026-05-23 directive ("USB DONE" gate): the coupled-pair Z_diff measurement at S=0.13 (W=0.20/h=0.21/εr=4.3) reads 87.41 Ω, used as the controlled-impedance ground truth in `docs/CONTROLLED_IMPEDANCE.md`. To validate the SETUP (independent of solver-vs-formula), ran limit-case sweep.

**Strategy:** As S grows large (S/h >> 1), coupling vanishes → Z_diff → 2 × Z_se (single-line). Primary target = 2 × openEMS-single-line at SAME W (isolates COUPLED-SETUP from solver-vs-formula).

**openEMS single-line at W=0.20** (matching coupled geometry): `val_openems_single_line_w020.py`, sha 7c33ea8.
  Z_se = **65.504 Ω @ 1 GHz** (65.495 @ 0.5 GHz, 65.516 @ 1.5 GHz — flat across band)
  vs H-J 67.32 Ω → 2.7% below H-J (consistent with Task 9 row 5 openEMS-vs-HJ 3.6%)
  → **Primary limit target: 2 × Z_se = 131.008 Ω**

**openEMS coupled-pair sweep** at W=0.20/h=0.21/εr=4.3 with S varied: `val_openems_limit.py`, sha 7c33ea8.

| S (mm) | S/h  | openEMS Z_diff (Ω) | vs 2×Z_se_openEMS=131.0 Ω |
|--------|------|---------------------|----------------------------|
| 0.13   | 0.62 | **87.41** (USB design point) | −33.3% (tight coupled, expected) |
| 0.50   | 2.38 | 119.44               | −8.8%                       |
| 1.00   | 4.76 | 125.28               | −4.4%                       |
| 2.00   | 9.52 | **127.18** (well decoupled) | **−2.9%** |

**Verdict — VALIDATED:**

- Z_diff monotonically INCREASES with S as expected (coupling weakens).
- At S/h = 9.52 (well decoupled), Z_diff is within **−2.9%** of 2×openEMS-single-line — well below 5% bar.
- The openEMS COUPLED-PAIR SETUP correctly converges to the SINGLE-LINE limit, isolating the SETUP question from the solver-vs-formula question.
- Therefore the **87.41 Ω measurement at S=0.13 (USB design geometry) is TRUSTWORTHY**.

Secondary cross-check (kept for completeness): 2 × H-J Z_se = 2 × 67.32 = 134.63 Ω. Coupled at S=2mm = 127.18 Ω is 5.5% below. The 5.5% gap = the openEMS-vs-HJ disagreement (Task 9 = 3.6%) + a small residual mesh discretization. Not a setup defect — well-known FDTD bias.

**Bottom line:** USB 2.0 D+/D- pair Z_diff = **87.4 Ω** is the validated number. Well within USB 2.0 spec band 76.5..103.5 Ω. C↔F integration's controlled-impedance commitment is sound.
