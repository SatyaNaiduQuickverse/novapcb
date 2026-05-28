#!/usr/bin/env python3
"""Per-net unconnected audit (Rule 23) — the inverse of verify-the-artifact for DRC.

A top-level "N unconnected items" DRC number is misleading when N is dominated by
intended-unrouted noise (plane-pour ratsnest + by-design-deferred nets). The TRUTH
is the PER-NET breakdown: every power/critical rail must be 0 unconnected before any
"routed" / "flight-routable" claim.

This tool: runs kicad-cli DRC, splits unconnected items by net, and classifies each:
  - PLANE-POUR NOISE: net has a filled zone (GND/+3V3/+5V_BEC) — its pads connect via
    the pour; the ratsnest line is an artifact, NOT a defect.
  - INTENDED-DEFERRED: explicitly tracked v2/by-design unrouted (MOT7/8, Telem, SWD).
  - REAL LATENT: everything else — a genuine routing gap. For power/critical nets this
    is a hard pre-freeze blocker.

Found the +3V3_IMU rail gaps AND the whole unrouted power tree (buck U2_FB/SW, MCU
VCAP/VDDA, +5V dist, eFuse) that the 213-unconnected top-level number hid (2026-05-26).

Usage: python3 scripts/audit_unconnected_per_net.py
"""
import json
import subprocess
import collections
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PCB = ROOT / "hardware/kicad/novapcb-stepwise/novapcb-stepwise.kicad_pcb"

# Nets explicitly unrouted by design (tracked deferrals — not defects).
# EFUSE_FLT/PGOOD: eFuse protection is autonomous; the status flags are MCU
# firmware-awareness only (no v1 fault-handling pipeline) — v2 defer per
# docs/EFUSE_STATUS_V1_DEFER.md, same pattern as Telem (USART1) / SWD.
INTENDED_DEFERRED = {"MOT7", "MOT8", "USART1_TX", "USART1_RX",
                     "SWDIO", "SWCLK", "SWO", "NRST",
                     "EFUSE_FLT", "EFUSE_PGOOD"}
# Specific PADS deferred to v2 even though the NET is otherwise working.
# C93.1: 4th-of-5 redundant +3V3_IMU decap on U8 BMI088 (v2-defer per
# docs/D5_3V3_IMU_DEFERRED_DECAPS.md; rail still has C91+C92+U8.11+U9.5+U9.8
# connected; IMU3 power retained; mid-band PDN Z impact ~5-10 mΩ within gate).
INTENDED_DEFERRED_PADS = {"C93.1"}
# Power/critical nets — a REAL unconnected here is a hard pre-freeze blocker.
POWER_CRITICAL_HINT = ("+5V", "+3V3", "VCAP", "VDD", "VREF", "VBAT", "U2_",
                       "EFUSE", "BOOT0", "USBC_CC", "_SENS")


def run_drc():
    out = "/tmp/audit_unconn_drc.json"
    subprocess.run(["kicad-cli", "pcb", "drc", "--severity-error", "--format",
                    "json", "--output", out, "--units", "mm", str(PCB)],
                   capture_output=True)
    return json.load(open(out))


def plane_nets():
    import pcbnew
    b = pcbnew.LoadBoard(str(PCB))
    return {z.GetNetname() for z in b.Zones()}, b


def net_copper(b, name):
    import pcbnew
    trk = sum(1 for t in b.GetTracks()
              if t.GetClass() == "PCB_TRACK" and t.GetNetname() == name)
    via = sum(1 for t in b.GetTracks()
              if t.GetClass() == "PCB_VIA" and t.GetNetname() == name)
    return trk, via


def main():
    d = run_drc()
    planes, b = plane_nets()
    netcount = collections.Counter()
    pad_deferred = 0
    import re
    for u in d.get("unconnected_items", []):
        nets = set()
        pads = set()
        for it in u.get("items", []):
            dd = it.get("description", "")
            if "[" in dd and "]" in dd:
                nets.add(dd[dd.find("[") + 1:dd.find("]")])
            m = re.match(r'Pad (\S+) \[[^]]+\] of (\S+) ', dd)
            if m:
                pads.add(f"{m.group(2)}.{m.group(1)}")
        # if any endpoint involves a deferred PAD, classify as deferred (not real-latent)
        if pads & INTENDED_DEFERRED_PADS:
            pad_deferred += 1
            continue
        for n in nets:
            netcount[n] += 1

    total = len(d.get("unconnected_items", []))
    noise = sum(c for n, c in netcount.items() if n in planes)
    deferred = sum(c for n, c in netcount.items() if n in INTENDED_DEFERRED)
    real = [(n, c) for n, c in netcount.items()
            if n not in planes and n not in INTENDED_DEFERRED]
    real.sort(key=lambda x: -x[1])

    print(f"=== per-net unconnected audit ({PCB.name}) ===")
    print(f"total unconnected:      {total}")
    print(f"  plane-pour noise:     {noise}  (zone nets {sorted(planes)} — not defects)")
    print(f"  intended-deferred:    {deferred}  (net-level: {sorted(n for n in INTENDED_DEFERRED if netcount.get(n,0)>0) or '—'})")
    print(f"  pad-deferred:         {pad_deferred}  (pad-level: {sorted(INTENDED_DEFERRED_PADS) or '—'})")
    print(f"  REAL LATENT:          {sum(c for _, c in real)}  across {len(real)} nets\n")
    if real:
        print(f"{'NET':18}{'unconn':>7}{'trk':>5}{'via':>5}  status")
        crit = 0
        for n, c in real:
            trk, via = net_copper(b, n)
            is_pwr = any(h in n for h in POWER_CRITICAL_HINT)
            state = "UNROUTED" if (trk == 0 and via == 0) else "partial-gap"
            tag = "  *** POWER/CRITICAL ***" if is_pwr else ""
            crit += 1 if is_pwr else 0
            print(f"{n:18}{c:>7}{trk:>5}{via:>5}  {state}{tag}")
        print(f"\n  {crit} power/critical nets with real unconnected.")
    verdict = "PASS" if not real else "FAIL"
    print(f"\nVERDICT: {verdict} — "
          + ("0 real latent unconnected; routed claim valid."
             if verdict == "PASS"
             else f"{sum(c for _,c in real)} real latent unconnected — NOT fully routed."))
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
