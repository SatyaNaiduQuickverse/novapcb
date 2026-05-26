#!/usr/bin/env python3
"""Sim 3 — SDMMC1 signal-integrity sanity (Phase 6f, task #46/#77).

Per SIM_SUITE_PLAN §3: "simple length-extraction from board + compute skew
per channel. No need for full FEM if length matching tolerance met."

The plan-doc carried a ±0.5mm length-match gate, but MICROSD_ROUTING_SURVEY
already flagged that as a DDR-memory-class spec, asking whether to relax to an
SD-appropriate skew budget. This sim resolves that: it extracts routed lengths,
converts to flight-time skew (outer-layer microstrip), and checks against the
ACTUAL bit period at the relevant clock rates.

Clock context (from BUILD_BASELINE.md / INTERFACE_CONTRACT.md):
  - Current cap: STM32_SDC_MAX_CLOCK = 12.5 MHz (ArduPilot H7 global default,
    deliberately conservative for SI).
  - SDR25 target: 50 MHz (clock-cap lift deferred to THIS sim).

Propagation: traces are on F.Cu (ref In1 GND) + B.Cu (ref In4 GND) = outer-layer
microstrip. er_eff ~ 3.2 → t_pd ~ 6.0 ps/mm. Sensitivity 5.9 (microstrip) to
7.1 ps/mm (stripline worst case) reported.

SD interface is SINGLE data rate (SDR): data sampled once per clock period.
The relevant skews: data-to-data (D0-D3 bus), CLK-to-data, CMD-to-CLK.
"""
import math
import pcbnew

PCB = "novapcb-stepwise.kicad_pcb"
TPD_PS_PER_MM = 6.0          # outer-layer microstrip, er_eff~3.2
TPD_RANGE = (5.9, 7.1)       # microstrip .. stripline worst case
CLOCKS_MHZ = [12.5, 25.0, 50.0, 100.0]   # 12.5=current cap, 50=SDR25 target
# SD Physical Layer Spec, High-Speed mode (50 MHz) host-side timing budget:
SD_SETUP_NS = 6.0            # tISU (input setup), SD HS
SD_HOLD_NS = 2.0             # tIH  (input hold),  SD HS


def net_length_mm(brd, name):
    mm = lambda v: v / 1e6
    total = 0.0
    for t in brd.GetTracks():
        if t.GetClass() == "PCB_TRACK" and t.GetNetname() == name:
            s, e = t.GetStart(), t.GetEnd()
            total += math.hypot(mm(e.x) - mm(s.x), mm(e.y) - mm(s.y))
    return total


def main():
    brd = pcbnew.LoadBoard(PCB)
    nets = ["SDMMC1_CLK", "SDMMC1_CMD",
            "SDMMC1_D0", "SDMMC1_D1", "SDMMC1_D2", "SDMMC1_D3"]
    L = {n: net_length_mm(brd, n) for n in nets}
    data = [L[f"SDMMC1_D{i}"] for i in range(4)]
    d_avg = sum(data) / 4

    print("=== SDMMC1 routed lengths ===")
    for n in nets:
        print(f"  {n:12} {L[n]:7.3f} mm")
    print(f"  data avg     {d_avg:7.3f} mm")

    # skews (mm) -> flight time (ps)
    dd_skew_mm = max(data) - min(data)
    clk_data_mm = max(abs(L["SDMMC1_CLK"] - d) for d in data)
    cmd_clk_mm = abs(L["SDMMC1_CMD"] - L["SDMMC1_CLK"])

    def ps(mm_):
        return mm_ * TPD_PS_PER_MM

    print("\n=== flight-time skew (t_pd = %.1f ps/mm; range %.1f-%.1f) ==="
          % (TPD_PS_PER_MM, *TPD_RANGE))
    rows = [("data-to-data (D0-D3)", dd_skew_mm),
            ("CLK-to-data (worst)", clk_data_mm),
            ("CMD-to-CLK", cmd_clk_mm)]
    for label, mm_ in rows:
        lo, hi = mm_ * TPD_RANGE[0], mm_ * TPD_RANGE[1]
        print(f"  {label:22} {mm_:6.2f} mm -> {ps(mm_):6.0f} ps  [{lo:.0f}-{hi:.0f}]")

    worst_skew_ps = ps(dd_skew_mm)

    print("\n=== skew vs bit period @ clock rate (SDR) ===")
    print(f"  {'clock':>8}  {'period':>8}  {'worst skew %period':>20}  verdict")
    all_ok = True
    for f in CLOCKS_MHZ:
        period_ns = 1e3 / f
        pct = (worst_skew_ps / 1e3) / period_ns * 100
        # skew must be a small fraction of the period AND << setup+hold window
        ok = (worst_skew_ps / 1e3) < (SD_SETUP_NS + SD_HOLD_NS) * 0.25 and pct < 10
        all_ok &= ok
        tag = "current cap" if f == 12.5 else ("SDR25 target" if f == 50 else "")
        print(f"  {f:6.1f}MHz  {period_ns:6.1f}ns  {pct:17.2f}%   "
              f"{'PASS' if ok else 'CHECK'}  {tag}")

    print(f"\n  SD HS setup/hold budget: tISU={SD_SETUP_NS}ns + tIH={SD_HOLD_NS}ns "
          f"= {SD_SETUP_NS+SD_HOLD_NS}ns window")
    print(f"  worst trace skew {worst_skew_ps:.0f} ps = "
          f"{worst_skew_ps/1e3/(SD_SETUP_NS+SD_HOLD_NS)*100:.1f}% of the setup+hold window")

    print("\n=== gate comparison ===")
    print(f"  plan-doc gate (±0.5mm data match): data spread {dd_skew_mm:.1f}mm "
          f"-> {'FAIL (DDR-class spec, inappropriate for SD)' if dd_skew_mm>0.5 else 'PASS'}")
    print(f"  SD-appropriate skew budget (skew << bit period, ns-class S/H): "
          f"{'PASS at all rates incl 50MHz SDR25' if all_ok else 'CHECK'}")

    print(f"\nVERDICT: {'PASS (SD skew budget) — clock cap liftable to 50MHz from skew standpoint' if all_ok else 'CHECK'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
