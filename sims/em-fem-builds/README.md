# EM/Thermal build + validation scripts (Phase 0.6 pivot)

Source-build + validation scripts for Elmer FEM + OpenEMS + Palace on the Pi.
Per Phase 0.6 task contract (`tasks/phase-0.6-emi-thermal-tooling-pivot.yaml`).

## Build scripts
- `build_elmer.sh` — Elmer FEM, headless (no Qt/ElmerGUI), `WITH_Mumps=OFF` (libparmetis-dev not in Debian trixie main; UMFPACK fallback from SuiteSparse). Installs to `~/local/elmer/`.
- `build_openems.sh` — CSXCAD → openEMS → python_openEMS wrapper. Installs to `~/local/openems/`.
- `build_palace.sh` — Uses apt-installed libmfem-dev. Installs to `~/local/palace/`.

## Validation scripts (cited references in `sims/VALIDATION.md`)
- `validate_elmer_nafems.sh` — NAFEMS-T1-style 1D conduction; ref = Incropera Eq 3.7
- `validate_openems_hammerstad.py` — microstrip Z₀ vs Hammerstad-Jensen 1980 + IPC-2141 + Pozar
- `validate_palace_spheres.sh` — two-sphere capacitance vs Palace docs + Smythe 1968

## Reproduce
```bash
# (assumes apt prereqs already installed — see tasks/phase-0.6-... pass_criteria 0.6.1)
bash build_elmer.sh
bash build_openems.sh
bash build_palace.sh
bash run_all_validations.sh   # runs all 4 validation cases, reports PASS/FAIL
```

Build prefix: `~/local/{elmer,openems,palace}/`. Outside the repo (regenerable artifacts).
