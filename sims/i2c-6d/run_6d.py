#!/usr/bin/env python3
"""
Phase 6d — I²C bus simulation (baro DPS310 + GPS+mag external).

Two I²C buses on novapcb (per hwdef.dat + Phase 3 schematic):
  - I2C2 (PB10 SCL / PB11 SDA) — on-board DPS310 baro, pullups R11/R12 = 4.7kΩ
  - I2C1 (PB6 SCL / PB7 SDA)  — external GPS+mag via J5 JST-GH 10P, pullups R21/R22 = 4.7kΩ

Tool: ngspice subprocess (PySpice doesn't expose AC magnitude — same workaround as 6a).
Inputs: schematic-level (pullup R + bus capacitance) — bus C from trace length
gates on Phase 4f for the precise number; this sub-phase uses an UPPER-BOUND
estimate (50 pF for on-board, 200 pF for external cable) to verify the pullup
choice is correct.

Pass criterion (I²C-spec): rise time ≤ 300 ns at 400 kHz, ≤ 1000 ns at 100 kHz.
"""

import json, subprocess
from pathlib import Path
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).parent.resolve()
PLOTS = HERE / "plots"; PLOTS.mkdir(exist_ok=True)

NGSPICE = str(Path.home()/"local/ngspice/usr/bin/ngspice")


def i2c_rise_time(R_pull_ohm, C_bus_pF, V_pull=3.3, V_th=0.7*3.3):
    """Analytical rise time for I²C bus: pure RC charging from 0 → V_th."""
    tau = R_pull_ohm * C_bus_pF * 1e-12
    t_rise = -tau * np.log(1 - V_th/V_pull)
    return t_rise  # seconds


def sim_i2c_rise(R_pull, C_bus, label):
    """ngspice transient: RC charging on release of open-drain pull-down."""
    nl = f"""* I2C bus rise-time sim {label}
Vpull pullnet 0 3.3
Rpull pullnet sda {R_pull}
Cbus sda 0 {C_bus}p
* Open-drain switch: closed (pull-down active) for first 1us, then open
S1 sda 0 ctrl 0 sw
.MODEL sw SW(VT=1.5 RON=10 ROFF=1G)
Vctrl ctrl 0 PULSE(3 0 1u 1n 1n 10u 20u)
.TRAN 1n 5u
.CONTROL
run
* Find time when v(sda) crosses 0.7*Vdd = 2.31V
meas tran t_rise WHEN v(sda)=2.31 RISE=1
print t_rise
wrdata /tmp/i2c_rise_{label}.csv time v(sda)
.ENDC
.END
"""
    nl_path = f"/tmp/i2c_rise_{label}.cir"
    Path(nl_path).write_text(nl)
    proc = subprocess.run([NGSPICE, "-b", nl_path], capture_output=True, text=True)
    # Parse t_rise from stdout
    t_rise_s = None
    for line in proc.stdout.splitlines():
        if "t_rise" in line.lower() and "=" in line:
            try:
                t_rise_s = float(line.split("=")[1].split()[0])
                break
            except (IndexError, ValueError):
                pass

    # Also load the V(sda) trace for plot
    csv = f"/tmp/i2c_rise_{label}.csv"
    if Path(csv).exists():
        d = np.loadtxt(csv)
        t = d[:, 0]; v = d[:, 3] if d.shape[1] > 3 else d[:, 1]
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.plot(t * 1e6, v, label=f"V(SDA) — Rpull={R_pull}Ω, Cbus={C_bus}pF")
        ax.axhline(2.31, ls="--", color="r", alpha=0.5, label="0.7×Vdd = 2.31V")
        ax.axhline(3.3, ls=":", color="k", alpha=0.3, label="3.3V")
        ax.set_xlabel("time (µs)"); ax.set_ylabel("V(SDA)")
        ax.set_title(f"I²C rise time — {label}")
        ax.legend(); ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(PLOTS / f"6d_i2c_rise_{label}.png", dpi=120)
        plt.close(fig)
    return t_rise_s


def main():
    print("Phase 6d — I²C rise-time sim")
    results = {"tool": "ngspice 46 (userspace .deb extract)", "checks": []}

    def add(name, result, notes=""):
        status = "PASS" if result.get("pass") else "FAIL" if result.get("pass") is False else "INFO"
        results["checks"].append({"check": name, "status": status, "result": result, "notes": notes})
        print(f"  → {name}: {status}", result)

    # Spec: 400 kHz I²C requires t_rise ≤ 300 ns.
    # I2C2 on-board baro: R_pull=4.7kΩ, C_bus ≤ 50 pF (short on-board trace)
    t_an1 = i2c_rise_time(4700, 50)
    t_sp1 = sim_i2c_rise(4700, 50, "i2c2_baro")
    add("6d.1_i2c2_baro_4.7k_50pF",
        {"analytical_ns": round(t_an1*1e9, 1),
         "simulated_ns": round(t_sp1*1e9, 1) if t_sp1 else None,
         "target_ns_400kHz": 300,
         "pass": t_an1 < 300e-9},
        "On-board I2C2 DPS310 — R11/R12 = 4.7kΩ; bus C ≤50pF upper bound. Layout refines C post-4f.")

    # I2C1 external GPS+mag: R_pull=4.7kΩ, C_bus ≤ 200 pF (cable ~1m up to GPS)
    t_an2 = i2c_rise_time(4700, 200)
    t_sp2 = sim_i2c_rise(4700, 200, "i2c1_gps")
    add("6d.2_i2c1_external_4.7k_200pF",
        {"analytical_ns": round(t_an2*1e9, 1),
         "simulated_ns": round(t_sp2*1e9, 1) if t_sp2 else None,
         "target_ns_400kHz": 300,
         "pass": t_an2 < 300e-9},
        "External I2C1 GPS+mag — cable C dominates; R21/R22 = 4.7kΩ. If FAIL, lower R to 2.2kΩ or run 100kHz only.")

    # Bus capacitance budget — what's the max C for 400 kHz with our 4.7kΩ pullup?
    # t_rise = R*C*ln(1/(1-0.7)) = R*C*1.2; for t_rise=300ns: C_max = 300n/(4700*1.2) = 53 pF
    c_max = 300e-9 / (4700 * 1.2)
    add("6d.3_bus_cap_budget_400kHz",
        {"R_pullup_ohm": 4700,
         "C_max_pF_for_400kHz": round(c_max * 1e12, 1),
         "interpretation": "With 4.7kΩ pullups, I²C bus cap budget for 400kHz operation is ~53 pF. On-board I2C2 stays within this; external I2C1 GPS+mag cable may not — defer to 100kHz if needed.",
         "pass": True},
        "Bus cap budget analysis")

    n_pass = sum(1 for c in results["checks"] if c["status"] == "PASS")
    results["summary"] = {"total": len(results["checks"]), "pass": n_pass}
    (HERE / "results.json").write_text(json.dumps(results, indent=2, default=str))
    print(f"\nSUMMARY: {results['summary']}")


if __name__ == "__main__":
    main()
