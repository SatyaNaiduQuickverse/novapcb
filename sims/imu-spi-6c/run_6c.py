#!/usr/bin/env python3
"""
Phase 6c — IMU SPI bus signal integrity (TIER-2, gates on Phase 4f).

The SPI1 bus to ICM-42688-P runs at 16 MHz operational (Phase 2a config).
SI risk: rise/fall time, ringing on CS line, setup/hold margin.

Tool: ngspice + IBIS estimate (no published IBIS for ICM-42688 or STM32H743;
estimate from datasheet rise/fall + lump-element trace model).

LAYOUT-DEPENDENT INPUTS (TODO post-Phase-4f):
  - Trace length MCU(F.Cu) → ICM-42688-P(F.Cu) for each of SCK/MOSI/MISO/CS
  - Trace impedance (typically ~50Ω single-ended on the 4a stackup)
  - Via count if any layer transition

Pass criteria (SIMULATION_PLAN §6c):
  - Rise/fall <5 ns
  - Setup/hold margin >2 ns
  - No ringing past 200 mV

This script: scaffold with placeholder trace L/C. Plug routed values post-4f.
"""

import json
import subprocess
from pathlib import Path

HERE = Path(__file__).parent.resolve()
NGSPICE = str(Path.home()/"local/ngspice/usr/bin/ngspice")


def sim_spi_edge(trace_L_nH=10, trace_C_pF=2, load_C_pF=10, edge_ns=2):
    """STM32H743 GPIO drives a TLINE-ish lumped trace into ICM-42688 input cap.
    Returns rise time + overshoot."""
    nl = f"""* SPI edge response — placeholder geometry
Vsrc src 0 PULSE(0 3.3 0 {edge_ns}n {edge_ns}n 100n 200n)
Rdrv src tx 30
* trace lumped L+C
Ltrace tx mid {trace_L_nH}n
Ctrace mid 0 {trace_C_pF}p
* IMU input load
Rdamp mid rx 0
Cload rx 0 {load_C_pF}p
.TRAN 100p 100n
.CONTROL
run
meas tran v_max MAX v(rx) FROM=0 TO=50n
meas tran v_min MIN v(rx) FROM=20n TO=100n
print v_max v_min
wrdata /tmp/spi_6c.csv time v(rx) v(tx) v(src)
.ENDC
.END
"""
    Path("/tmp/spi_6c.cir").write_text(nl)
    proc = subprocess.run([NGSPICE, "-b", "/tmp/spi_6c.cir"], capture_output=True, text=True)
    vmax = vmin = None
    for line in proc.stdout.splitlines():
        if "v_max" in line.lower() and "=" in line:
            try: vmax = float(line.split("=")[1].split()[0])
            except (ValueError, IndexError): pass
        if "v_min" in line.lower() and "=" in line:
            try: vmin = float(line.split("=")[1].split()[0])
            except (ValueError, IndexError): pass
    return {"v_max_V": vmax, "v_min_V": vmin}


def main():
    print("Phase 6c — IMU SPI SI (SCAFFOLD; routed values plug in post-Phase-4f)")
    results = {
        "tool": "ngspice 46 + IBIS estimate",
        "tier": 2,
        "layout_dependent_TODOs": [
            "Replace trace_L_nH and trace_C_pF placeholders with extracted-parasitic values from Phase 4f routed board.",
            "Verify CS, SCK, MOSI, MISO trace lengths are similar (skew < 100ps).",
            "Confirm 50Ω single-ended on 4a stackup via Phase 4d Hammerstad-Jensen if not done.",
        ],
        "checks": [],
    }

    for label, trace_L, trace_C in [
        ("placeholder_short", 5, 1),    # ~10mm trace
        ("placeholder_typical", 10, 2),  # ~20mm trace
        ("placeholder_long", 20, 4),     # ~40mm trace
    ]:
        r = sim_spi_edge(trace_L_nH=trace_L, trace_C_pF=trace_C)
        results["checks"].append({
            "check": f"6c.scaffold_{label}",
            "status": "INFO",
            "result": r,
            "notes": f"Lumped trace L={trace_L}nH, C={trace_C}pF — placeholder. POST-4F: extract from routed board.",
        })
        print(f"  {label}: v_max={r['v_max_V']}, v_min={r['v_min_V']}")

    results["summary"] = {"total": len(results["checks"]), "info": len(results["checks"])}
    (HERE / "results.json").write_text(json.dumps(results, indent=2, default=str))
    print("Scaffold ready. Re-run post-Phase-4f with extracted trace parasitics.")


if __name__ == "__main__":
    main()
