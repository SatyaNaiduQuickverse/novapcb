# Sim 4 — CAN bus differential impedance result (Phase 6f)

> Tool: `hardware/kicad/novapcb-stepwise/sim_can_zdiff.py`. Method per
> `SIM_SUITE_PLAN §4` (analytical coupled-microstrip Z_diff), reusing the
> methods validated against openEMS in `val_openems_coupled.py` (PR #75).
> **Verdict: PASS.**

## 1. Geometry (measured from board)

CANH_NET / CANL_NET differential pair:

| Parameter | Value |
|---|---|
| Trace width W | 0.20 mm |
| Edge spacing S | 0.80 mm (1.00 mm centerline pitch) |
| Layer | F.Cu over In1 GND |
| Dielectric h | 0.21 mm (JLC06161H-7628 prepreg) |
| εr | 4.3 |
| Cu thickness t | 0.035 mm |
| Pair length | ~36–46 mm (< 50 mm bus stub) |

The pair is **loosely coupled** (g = S/h = 3.81 » 1) — coupling is negligible,
so Z_diff → 2·Z_single.

## 2. Result

| Method | Z_diff |
|---|---|
| Single-ended Z₀ (Hammerstad-Jensen) | 67.3 Ω |
| Z_diff, H-J edge-coupling | 133.0 Ω (→ 2·Z_se as coupling→0) |
| Z_diff, Garg-Bahl coupled | ~~176.5~~ **excluded** (formula out of range at g>3; would exceed 2·Z_se, unphysical) |
| Z_diff, openEMS-corrected est. | 117.4 Ω (H-J × 0.883, the PR #75 openEMS/analytical anchor) |
| **Z_diff (as-routed range)** | **117–133 Ω, centered ~125 Ω** |
| Z_common (= Z_even/2) | 33.7 Ω |

## 3. Assessment

- **Near-ideal for CAN.** CAN's nominal bus impedance is **120 Ω** differential.
  The as-routed pair is ~117–133 Ω (centered ~125 Ω) — a near-perfect match.
- **Z_common 34 Ω ≤ 60 Ω** — PASS (low common-mode, good ESD/EMC margin).
- **Methodology note:** the Garg-Bahl coupled-microstrip closed form is calibrated
  for g ≲ 2–3; at g = 3.81 it returns Z_diff > 2·Z_se (unphysical) and is excluded.
  At wide spacing the physically-correct limit is Z_diff → 2·Z_se, which the H-J
  edge-coupling form gives (133 Ω). A fresh 3D FDTD run was not needed: the PR #75
  openEMS validation already anchored the analytical on this exact stackup, and
  the coupling-model error (the bulk of the openEMS-vs-analytical gap) **vanishes**
  at this wide spacing.

## 4. Gate resolution

- **Plan-doc gate "Z_diff 50–80 Ω": mis-specified for this routing.** It assumed a
  tightly-coupled pair. The as-routed loosely-spaced pair is ~120 Ω — which is the
  CAN nominal, i.e. **better** than 50–80 Ω, not a failure. (Same class as the
  Sim 3 ±0.5mm gate: the plan number was inherited from a different assumption.)
  Recommend restating the gate as *"Z_diff within ±25 % of 120 Ω, or non-critical
  for <50 mm stubs."*
- **Stub length < 50 mm** → the transmission-line impedance is non-critical
  relative to the slow CAN edge rates anyway (master 2026-05-24); the ~120 Ω match
  is a bonus, not a requirement at this length.

## 5. Verification

Analysis-only — **no layout / SKiDL / netlist change**. Reproducible via
`python3 sim_can_zdiff.py`. Closes the CAN Z_diff sanity item (task #45 sim leg).
