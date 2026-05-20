# Simulation tool validation — novapcb (Phase 0.6 pivot Step 1)

> **Status**: pending. This file populates as each of the 3 EM/thermal tools (OpenEMS, Elmer FEM, Palace) builds + runs its validation case.
>
> **Mandate** (master 2026-05-20 + Sai's directive): each tool is only trustworthy once it reproduces a KNOWN answer from a TRUSTED source. Reference values must come from NAFEMS, NIST, IEEE, IPC, the tool maintainers' own docs, or canonical textbooks (Pozar — microwave/EM; Incropera — heat transfer). Not blogs or unverified forum posts.
>
> **Hard gate**: a tool that doesn't reproduce the known answer within tolerance is **NOT trusted** and must NOT be used on novapcb. No loosening of tolerance to make it pass; honest escalation only.

---

## Tolerances + meshing discipline

| Tool | Reference precision | Adopted tolerance | Rationale |
|---|---|---|---|
| OpenEMS (FDTD) | Hammerstad-Jensen accurate to ~1-2% for typical microstrip geometries | ±5% | FDTD numerical dispersion + finite mesh; standard published OpenEMS validations match analytical Z0 to 3-5% |
| Elmer (FEA, 1D conduction) | Closed-form exact | ±1% | 1D Laplace with linear T(x) is exactly representable by piecewise-linear FEA on the same mesh; any larger error = bug |
| Palace (FEM EM) | Palace project's bundled reference is from a converged adaptive run | ±5% on capacitance/eigenfrequency | Coarser mesh + uniform refinement vs Palace's adaptive reference |

**OpenEMS meshing rule (per master 2026-05-20)**: ≥10 cells per wavelength at the highest simulated frequency. Will be explicitly stated per validation case below.

---

## OpenEMS validation

### (1) Official tutorial — Microstrip Notch Filter

| Field | Value |
|---|---|
| Reference source | `openEMS/python/Tutorials/MSL_NotchFilter.py` (Liebig 2016-2023, OpenEMS project). Documented in the OpenEMS Python tutorials at <https://docs.openems.de/python/Tutorials/MSL_NotchFilter.html>. |
| Problem | Microstrip line with quarter-wave open stub. MSL: 50000µm length × 600µm width, substrate 254µm thick, εr=3.66. Stub: 12mm long. Expected: |S21| notch dip near stub quarter-wave resonance. |
| Reference notch freq | f_notch ≈ 3.7 GHz (quarter-wave on εr_eff ≈ 2.9 substrate; the tutorial documents the resulting trace at this frequency band) |
| f_max | 7 GHz |
| Mesh resolution | λ/50 at f_max = c0 / (7e9 × √3.66) / 50 = 449µm cell size → ≈ **15 cells/wavelength at 7 GHz**, well above the ≥10 cells/λ floor |
| Computed notch freq | _TBD_ |
| \|S21\| dip depth | _TBD_ |
| Tolerance | f_notch ±5% |
| Runtime | _TBD_ |
| **Status** | _PENDING — OpenEMS build in progress_ |

### (2) Microstrip Z₀ analytical cross-check — novapcb-specific

| Field | Value |
|---|---|
| Reference source | Hammerstad & Jensen (1980) "Accurate Models for Microstrip Computer-Aided Design", IEEE MTT-S Digest, pp. 407-409. Closed-form Z₀(W,h,εr) for single-ended microstrip. Cross-referenced to Pozar D.M., "Microwave Engineering" 4th ed., Wiley 2011, §3.8 "The Microstrip Transmission Line". Also IPC-2141 "Controlled Impedance Circuit Boards and High Speed Logic Design" (IPC, 1996; revised 2021) §5 for industry-standard PCB impedance formulas. |
| Problem | Microstrip line, same geometry as novapcb USB diff-pair (Phase 4d locked geometry): W=0.25mm, h=0.21mm, εr=4.3, t=0.035mm (1oz). 20mm length. |
| Analytical Z₀ | **70.19 Ω single-ended** (from Hammerstad-Jensen; verified in `sims/usb-diffpair-6b/run_6b.py` Tier-1) |
| f range | 100 MHz – 5 GHz; Z0 extracted from S11 at low end |
| Mesh resolution | 0.05mm in trace region → 10× finer than W (W=0.25mm = 5 cells); λ/50 at 5 GHz on εeff=3.14 = 851µm → ≈ **17 cells/wavelength**, above ≥10/λ floor |
| OpenEMS-computed Z₀ | _TBD_ |
| Tolerance | ±5% (i.e. Z₀ must land in 66.7 – 73.7 Ω) |
| Runtime | _TBD_ |
| **Status** | _PENDING_ |

---

## Elmer FEM validation

### Steady-state thermal — NAFEMS-T1-style 1D conduction

| Field | Value |
|---|---|
| Reference source | Closed-form 1D Laplace heat equation: T(x) = T_hot - (T_hot - T_cold) × x/L. Originally Fourier (1822) "Théorie analytique de la chaleur"; modern textbook citation: **Incropera & DeWitt, Fundamentals of Heat and Mass Transfer, 7th ed., Eq. 3.7**. Also the simplest case of **NAFEMS Thermal Benchmark T1** ("Heat conduction with prescribed temperature", NAFEMS Benchmark Tests for Thermal Analysis, NAFEMS 1990). NAFEMS is the international authority on FEA verification & validation. |
| Problem | 1m × 0.1m × 0.1m slab, k=1 W/m·K, T(x=0)=100°C, T(x=1m)=0°C, other faces adiabatic. |
| Reference T(x=0.5) | **50.000°C exactly** (closed-form) |
| Mesh | 10 elements along x × 1 along y (Elmer's ElmerGrid 2D, 4-node quads) |
| Solver | ElmerSolver HeatSolver, Linear System Direct = UMFPACK (SuiteSparse) |
| Elmer-computed T(x=0.5) | _TBD_ |
| Tolerance | ±1% (50.0 ±0.5°C) |
| Runtime | _TBD_ |
| **Status** | _PENDING — Elmer build in progress (rebuild w/o MUMPS due to ParMetis absent in Debian trixie main)_ |

---

## Palace validation

### Bundled example — Two-sphere capacitance matrix

| Field | Value |
|---|---|
| Reference source | Palace project documentation, `palace/docs/src/examples/spheres.md` ("Capacitance Matrix for Two Spheres"). Cites analytical solution from Smythe W.R., "Static and Dynamic Electricity" 3rd ed., McGraw-Hill 1968 (canonical EM text). Palace project also publishes verified converged-reference output in `palace/test/examples/ref/spheres/terminal-C.csv`. |
| Problem | Two conducting spheres, radii a=1cm, b=2cm, centers separated c=5cm; surrounding medium = vacuum. Solve electrostatic capacitance matrix. |
| Reference (Palace docs) | C[0][0] = 1.2374e-12 F, C[0][1] = C[1][0] = -4.7710e-13 F, C[1][1] = 2.4784e-12 F |
| Analytical (Smythe 1968) | Infinite series — matches Palace ref to <1% per Palace docs |
| Solver | Palace Electrostatic, BoomerAMG + GMRES; bundled `spheres.json` config + bundled `mesh/spheres.msh` |
| Palace-computed C-matrix | _TBD_ |
| Tolerance | ±5% on each matrix entry |
| Runtime | _TBD_ |
| **Status** | _PENDING — Palace build queued behind Elmer + OpenEMS_ |

---

## Validation gate summary

| Tool | Validation cases | All passed? | Trusted for novapcb? |
|---|---|---|---|
| OpenEMS | (1) Notch filter tutorial + (2) microstrip Z₀ vs Hammerstad-Jensen | _PENDING_ | _PENDING_ |
| Elmer FEM | NAFEMS-T1-style 1D conduction | _PENDING_ | _PENDING_ |
| Palace | Two-sphere capacitance matrix | _PENDING_ | _PENDING_ |

**A tool transitions from PENDING → TRUSTED only when all its validation cases pass within tolerance.** Anything else is reported as a CRITICAL finding + escalated; the tool is NOT used on novapcb.

---

## Reproducibility

All validation cases are scripted under `~/local/src/em-fem-builds/`:
- `validate_elmer_nafems.sh` — Elmer 1D conduction
- `validate_openems_hammerstad.py` — OpenEMS microstrip Z₀
- (OpenEMS notch tutorial uses the bundled `MSL_NotchFilter.py`)
- (Palace spheres uses bundled `palace/examples/spheres/spheres.json`)

Each script runs the validation, parses the result, prints PASS/FAIL with the computed-vs-reference comparison + runtime.
