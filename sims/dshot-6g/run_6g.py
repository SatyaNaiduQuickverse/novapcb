#!/usr/bin/env python3
"""
Phase 6g — ESC DShot output SI (TIER-2, gates on Phase 4f).

DShot300/600 on 8 motor outputs (PB0/PB1/PA0/PA1/PA2/PA3/PD12/PD13 per
Phase 2e MatekH743-bdshot inheritance). DShot600 = 600 kbit/s bit rate;
DShot300 = 300 kbit/s. Each bit is a pulse 1.25/2.5 µs wide.

LAYOUT-DEPENDENT (POST-4F):
  - Trace lengths from MCU pin → J11-J18 ESC_solder_pad (Phase 4a custom footprint)
  - Trace impedance — single-ended (no specific Z0 target; 50Ω typical)
  - Length matching across 8 channels (not critical — each motor independent)
  - Crosstalk between adjacent DShot traces

Pass criterion (SIMULATION_PLAN §6g):
  DShot300/600 rise/fall + ringing within ESC tolerances. Specifically:
  - Rise/fall < 100 ns (DShot600 bit period 1.67 µs → edges are ~6%)
  - No ringing past 200 mV

Scaffold: ngspice transient harness with placeholder trace L/C.
"""

import json, subprocess
from pathlib import Path

HERE = Path(__file__).parent.resolve()
NGSPICE = str(Path.home()/"local/ngspice/usr/bin/ngspice")


def sim_dshot_edge(trace_L_nH, trace_C_pF, R_term=0):
    """Drive a DShot bit pulse through lumped trace into ESC input (~10pF + 10kΩ pulldown)."""
    nl = f"""* DShot600 bit edge — placeholder geometry
Vsrc src 0 PULSE(0 3.3 0 5n 5n 1u 1.67u)
Rdrv src tx 30
Ltr tx mid {trace_L_nH}n
Ctr mid 0 {trace_C_pF}p
Rterm mid rx {R_term}
Cesc rx 0 10p
Resc rx 0 10k
.TRAN 1n 200n
.CONTROL
run
meas tran v_max MAX v(rx) FROM=0 TO=50n
meas tran v_overshoot PARAM='v_max - 3.3'
print v_max v_overshoot
wrdata /tmp/dshot_6g.csv time v(rx) v(tx) v(src)
.ENDC
.END
"""
    Path("/tmp/dshot_6g.cir").write_text(nl)
    proc = subprocess.run([NGSPICE, "-b", "/tmp/dshot_6g.cir"], capture_output=True, text=True)
    return {"stdout_excerpt": "\n".join(l for l in proc.stdout.splitlines() if "v_max" in l.lower() or "overshoot" in l.lower())}


def main():
    print("Phase 6g — ESC DShot SI (SCAFFOLD)")
    results = {
        "tool": "ngspice 46 + IBIS estimate",
        "tier": 2,
        "checks": [],
    }

    for label, L, C in [
        ("short_5mm", 2.5, 0.5),    # MOT4-8 are short trace to J14-J18
        ("typical_15mm", 7.5, 1.5),
        ("long_30mm", 15, 3),       # MOT1-3 long N-to-S routes per Phase 4 handoff
    ]:
        r = sim_dshot_edge(trace_L_nH=L, trace_C_pF=C)
        results["checks"].append({
            "check": f"6g.scaffold_{label}",
            "status": "INFO",
            "result": r,
            "notes": f"Lumped trace L={L}nH/C={C}pF placeholder for ~{label.split('_')[1]} trace.",
        })

    results["layout_dependent_TODOs"] = [
        "Post-4F: extract per-motor trace length MOT1-MOT8 from routed board.",
        "Post-4F: re-run with extracted L/C for each channel; check overshoot < 200mV for all 8.",
        "Post-4F: crosstalk between MOT1+MOT2 (adjacent at MCU exit) and MOT4-8 (parallel down to south edge).",
        "If overshoot persists, consider 33Ω series R on each DShot line (Matek production design pattern — though Phase 3f notes NO series R on novapcb v1; revisit if 6g flags ringing).",
    ]
    results["summary"] = {"total": len(results["checks"]), "info": len(results["checks"])}
    (HERE / "results.json").write_text(json.dumps(results, indent=2, default=str))
    print("Scaffold ready. Re-run post-Phase-4f with extracted MOT trace parasitics.")


if __name__ == "__main__":
    main()
