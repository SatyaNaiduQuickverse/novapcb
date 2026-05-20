#!/usr/bin/env python3
"""
Phase 6f — SDMMC bus SI (TIER-2, gates on Phase 4f).

SDMMC1 runs at 12.5 MHz max (Phase 2h STM32_SDC_MAX_CLOCK = 12.5e6).
6 lines: CLK + CMD + D0-D3 (4-bit SDIO).

Critical: clock skew between CLK and D0-D3 lines at 12.5 MHz → 80 ns bit
period; tolerance ~10 ns. Trace skew across 4 data lines < 2 ns target.

LAYOUT-DEPENDENT (POST-4F):
  - Trace lengths CMD/D0/D1/D2/D3/CLK from MCU F.Cu via to J2 microSD on B.Cu
  - Skew between all 6 lines (longest - shortest)
  - 47kΩ pullup R51-R55 placement on B.Cu — load capacitance impact

Pass criterion (SIMULATION_PLAN §6f):
  Clock skew <2 ns across 4 data lines at 12.5 MHz SDMMC clock.

Scaffold: harness exists, plug routed lengths post-4f.
"""

import json, subprocess
from pathlib import Path

HERE = Path(__file__).parent.resolve()
NGSPICE = str(Path.home()/"local/ngspice/usr/bin/ngspice")


def trace_delay_estimate(length_mm, eps_eff=3.0):
    """T_pd ≈ length / v_p; v_p = c / sqrt(eps_eff). For our 4a stackup eps_eff ~3 →
    v_p ≈ 173 mm/ns. So 1mm trace ≈ 5.8 ps delay."""
    v_p = 3e8 / (eps_eff ** 0.5) * 1000  # mm/s
    return length_mm / v_p  # seconds


def main():
    print("Phase 6f — SDMMC SI (SCAFFOLD)")
    results = {
        "tool": "ngspice 46 + analytical (scaffold; routed lengths post-Phase-4f)",
        "tier": 2,
        "checks": [],
    }

    # Placeholder: assume MCU at (X=15-25, Y=11-18) on F.Cu, J2 at (18, 9) on B.Cu.
    # Trace lengths PLACEHOLDER pending Phase 4f extraction; based on placement
    # they should be 10-25mm with via transitions.
    placeholder_lengths_mm = {
        "CLK":  15,
        "CMD":  17,
        "D0":   18,
        "D1":   19,
        "D2":   16,
        "D3":   17,
    }
    delays = {k: trace_delay_estimate(v) for k, v in placeholder_lengths_mm.items()}
    data_delays_ns = [v * 1e9 for k, v in delays.items() if k.startswith("D")]
    skew_ns = max(data_delays_ns) - min(data_delays_ns)

    results["checks"].append({
        "check": "6f.scaffold_skew_estimate",
        "status": "INFO" if skew_ns < 2 else "FAIL",
        "result": {
            "placeholder_lengths_mm": placeholder_lengths_mm,
            "delays_ps": {k: round(v * 1e12, 2) for k, v in delays.items()},
            "data_skew_ns": round(skew_ns, 3),
            "target_ns": 2,
            "pass": skew_ns < 2,
        },
        "notes": "Placeholder lengths. Post-4F: extract real lengths from routed novapcb-layout.kicad_pcb (use python+pcbnew to get net.GetNetname + iterate tracks).",
    })

    results["layout_dependent_TODOs"] = [
        "Post-4F: extract actual trace lengths for SDMMC1_CLK/CMD/D0-D3 from novapcb-layout.kicad_pcb.",
        "Post-4F: full SI sim with 47kΩ pullups R51-R55 as B.Cu loads + IBIS-estimate driver model for MCU SDIO pins.",
        "Phase 6m: cross-check J2 microSD pad placement vs DM3AT-SF-PEJM5 datasheet land pattern (ICM-42688 phase4a-1 pattern of footprint verification).",
    ]
    n_info = sum(1 for c in results["checks"] if c["status"] == "INFO")
    n_pass = sum(1 for c in results["checks"] if c["status"] == "PASS")
    n_fail = sum(1 for c in results["checks"] if c["status"] == "FAIL")
    results["summary"] = {"total": len(results["checks"]), "pass": n_pass, "fail": n_fail, "info": n_info}
    (HERE / "results.json").write_text(json.dumps(results, indent=2, default=str))
    print(f"  placeholder data-line skew: {skew_ns:.3f} ns (target <2 ns)")
    print(f"  SUMMARY: {results['summary']}")


if __name__ == "__main__":
    main()
