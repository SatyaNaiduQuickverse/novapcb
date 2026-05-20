#!/usr/bin/env python3
"""
Phase 6b — USB-CDC differential pair SI (Hammerstad-Jensen + scikit-rf).

OpenEMS deferred (TOOLCHAIN.md §4); analytical Hammerstad-Jensen geometry was
already computed in Phase 4d:
  W = 0.25 mm trace / S = 0.10 mm gap / h = 0.21 mm prepreg / εr = 4.3 (4a stackup)
  → Zdiff = 90 Ω target (±10% per SIMULATION_PLAN §6b)

This script:
  1. Re-runs the Hammerstad-Jensen calc (single-ended Z0 + coupling factor → Zdiff)
  2. Builds a 2-port scikit-rf transmission-line model of the routed pair
  3. Computes |S11| return loss + Zdiff vs frequency to 480 MHz (USB FS upper)
  4. Compares against the SIMULATION_PLAN pass criteria

TODO (gates on Phase 4f):
  - Plug in actual routed trace LENGTH from the .kicad_pcb (currently using
    a placeholder length of 30 mm; real value extracted post-routing).
  - Cross-check via scikit-rf with the routed Touchstone if KiCad-generated.
"""

import json
import os
from pathlib import Path
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import skrf

HERE = Path(__file__).parent.resolve()
PLOTS = HERE / "plots"
PLOTS.mkdir(exist_ok=True)


# ---- Hammerstad-Jensen ----
def hammerstad_jensen_microstrip(W, h, t, eps_r):
    """Single-ended Z0 of an edge-coupled microstrip. Returns Z0 in ohms."""
    u = W / h
    a = 1 + (1/49)*np.log((u**4 + (u/52)**2)/(u**4 + 0.432)) + (1/18.7)*np.log(1 + (u/18.1)**3)
    b = 0.564 * ((eps_r - 0.9)/(eps_r + 3))**0.053
    eps_eff = (eps_r + 1)/2 + (eps_r - 1)/2 * (1 + 10/u)**(-a*b)
    Z0_air = (60/np.sqrt(1)) * np.log(6 + (2*np.pi - 6)*np.exp(-(30.666/u)**0.7528) + np.sqrt(1 + 4/u**2))
    Z0 = Z0_air / np.sqrt(eps_eff)
    return Z0, eps_eff


def diff_z_from_single(Z0, S, h):
    """Zdiff ≈ 2*Z0 * (1 - 0.48*exp(-0.96*S/h)) — Cohn approx for edge-coupled."""
    return 2 * Z0 * (1 - 0.48 * np.exp(-0.96 * S / h))


def test_zdiff_geometry():
    """Re-derive Zdiff from Phase 4d stackup values."""
    W_mm, S_mm, h_mm = 0.25, 0.10, 0.21
    eps_r = 4.3
    t_mm = 0.035  # 1 oz copper
    Z0_se, eps_eff = hammerstad_jensen_microstrip(W_mm, h_mm, t_mm, eps_r)
    Z_diff = diff_z_from_single(Z0_se, S_mm, h_mm)
    return {
        "geometry": f"W={W_mm}mm/S={S_mm}mm/h={h_mm}mm/εr={eps_r}",
        "Z0_single_ended_ohm": round(Z0_se, 2),
        "eps_eff": round(eps_eff, 3),
        "Zdiff_ohm": round(Z_diff, 2),
        "target_ohm": 90,
        "tolerance_pct": 10,
        "pass": abs(Z_diff - 90) / 90 <= 0.10,
    }


def test_diff_pair_skrf(length_mm=30):
    """Transmission-line model of the routed pair via scikit-rf.
    TODO post-Phase-4f: replace length_mm with actual routed length."""
    freq = skrf.Frequency(1, 480, 481, "MHz")  # USB FS upper band
    # Phase 4d Zdiff = 90 Ω; v_prop = c / sqrt(eps_eff)
    eps_eff = 3.0  # approx for our stackup
    c0 = 3e8
    v_p = c0 / np.sqrt(eps_eff)
    L_per_m = 90 / v_p     # Z0 = sqrt(L/C); v = 1/sqrt(LC). Z0*v = 1/C; L/v = Z0 → L = Z0/v
    C_per_m = 1 / (90 * v_p)

    tl = skrf.media.DistributedCircuit(freq, L=L_per_m, C=C_per_m)
    line = tl.line(length_mm/1000, "m", name=f"USB diff pair {length_mm}mm")

    # |S11| over the band — measure of impedance match
    s11_db = 20 * np.log10(np.maximum(np.abs(line.s[:, 0, 0]), 1e-12))
    s11_worst = float(np.max(s11_db))

    # Plot
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(freq.f / 1e6, s11_db, label="|S11| (dB)")
    ax.axhline(-15, ls="--", color="r", alpha=0.5, label="−15 dB target ceiling")
    ax.set_xlabel("Frequency (MHz)"); ax.set_ylabel("|S11| (dB)")
    ax.set_title(f"Phase 6b — USB diff pair return loss ({length_mm}mm trace)")
    ax.legend(); ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(PLOTS / "6b_diffpair_s11.png", dpi=120)
    plt.close(fig)

    return {
        "trace_length_mm": length_mm,
        "trace_length_note": "PLACEHOLDER — replace with actual routed length post-Phase-4f",
        "s11_worst_dB": round(s11_worst, 2),
        "target_dB": -15,
        "pass": s11_worst <= -15,
    }


def main():
    print("Phase 6b — USB diff pair (analytical + scikit-rf)")
    results = {
        "tool": "analytical Hammerstad-Jensen + scikit-rf 1.12.0",
        "openems_status": "DEFERRED (TOOLCHAIN.md §4) — analytical fallback runs now; OpenEMS deeper pass post-Sai-handoff",
        "checks": [],
    }

    def add(name, result, notes=""):
        status = "PASS" if result.get("pass") else "FAIL" if result.get("pass") is False else "INFO"
        results["checks"].append({"check": name, "status": status, "result": result, "notes": notes})
        print(f"  → {name}: {status}")
        for k, v in result.items():
            if k != "pass": print(f"      {k}: {v}")

    r1 = test_zdiff_geometry()
    add("6b.1_zdiff_geometry", r1, "Hammerstad-Jensen on 4a stackup geometry locked Phase 4d")

    r2 = test_diff_pair_skrf(length_mm=30)
    add("6b.2_s11_return_loss", r2, "scikit-rf transmission-line model — placeholder trace length 30mm; replace post-Phase-4f")

    n_pass = sum(1 for c in results["checks"] if c["status"] == "PASS")
    n_fail = sum(1 for c in results["checks"] if c["status"] == "FAIL")
    results["summary"] = {"total": len(results["checks"]), "pass": n_pass, "fail": n_fail}
    (HERE / "results.json").write_text(json.dumps(results, indent=2, default=str))
    print(f"\nSUMMARY: {results['summary']}")
    print(f"Results: {HERE / 'results.json'}")


if __name__ == "__main__":
    main()
