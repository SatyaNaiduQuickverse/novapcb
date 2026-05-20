#!/usr/bin/env python3
"""
Phase 6e — UART signal integrity (TIER-1 PARTIAL — analytical rise-time
runnable now; routed-trace SI gates on Phase 4f).

UARTs on novapcb v1:
  - USART1 (telem): 115200 baud default, max ~921 kbaud
  - USART2 (GPS): 38400 / 115200 / up to 921 kbaud
  - USART6 (CRSF/ELRS): 420 kbaud (DECISIONS §4 — novapcb-specific)

Analytical: bit period at 420 kbaud = 1/420e3 = 2.38 µs. STM32H743 GPIO
default slew rate = ~10 ns rise/fall (datasheet medium-speed config). Bit
period >> 200× the edge → no edge-rate concern at the UART speeds we use.

LAYOUT-DEPENDENT (POST-4F):
  - External cable length on USART2 (GPS via J5 JST-GH 10P — up to 1m)
  - USART1 (telem) cable length via J3 (variable)
  - USART6 CRSF (J10 solder pads) — short, direct ELRS RX wiring

Pass criterion (SIMULATION_PLAN §6e):
  UART eye open at 420 kbaud + GPS 38.4 kbaud; no excessive ringing.
"""

import json
import subprocess
from pathlib import Path

HERE = Path(__file__).parent.resolve()
NGSPICE = str(Path.home()/"local/ngspice/usr/bin/ngspice")


def analytical_bit_period_vs_edge_rate(baud, edge_ns):
    """Verify bit period >> edge transition time."""
    t_bit = 1 / baud
    ratio = t_bit / (edge_ns * 1e-9)
    return {"baud": baud, "t_bit_us": round(t_bit * 1e6, 3),
            "edge_ns": edge_ns, "ratio": round(ratio, 0),
            "interpretation": "ratio > 10 = edges are tiny fraction of bit; eye stays wide open",
            "pass": ratio > 10}


def main():
    print("Phase 6e — UART rise-time analytical")
    results = {
        "tool": "analytical + ngspice for SI (scaffold)",
        "tier": "1 (analytical) / 2 (cable SI)",
        "checks": [],
    }

    for baud, label in [
        (38400, "GPS USART2 default"),
        (115200, "Telem USART1 default"),
        (420000, "CRSF USART6 (DECISIONS §4)"),
        (921600, "GPS USART2 high-speed"),
    ]:
        r = analytical_bit_period_vs_edge_rate(baud, edge_ns=10)
        results["checks"].append({"check": f"6e.{label}", "status": "PASS" if r["pass"] else "FAIL",
                                  "result": r, "notes": "STM32H743 GPIO medium-speed default ~10 ns edge"})
        print(f"  {label}: t_bit/t_edge = {r['ratio']}× ({'PASS' if r['pass'] else 'FAIL'})")

    results["layout_dependent_TODOs"] = [
        "Post-4F: simulate USART2 with 1m cable model (R + L + C distributed). Test eye opening at 921 kbaud (worst case).",
        "Post-4F: confirm CRSF J10 solder-pad to MCU PC6/PC7 route is short (<50mm) and away from DShot.",
    ]

    n_pass = sum(1 for c in results["checks"] if c["status"] == "PASS")
    results["summary"] = {"total": len(results["checks"]), "pass": n_pass}
    (HERE / "results.json").write_text(json.dumps(results, indent=2, default=str))
    print(f"  SUMMARY: {results['summary']}")


if __name__ == "__main__":
    main()
