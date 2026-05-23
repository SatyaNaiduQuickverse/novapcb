#!/usr/bin/env python3
"""U6 eFuse power routing — completes +5V_BEC → U6 → U2 chain.

Per master 2026-05-23 URGENT priority: U6 SKiDL netlist fix lands
(fix_u6_netlist.py) — now route the power path that was orphaned
because U6 pads were unassigned.

Chain:
  +5V_BEC plane (In2.Cu) → Q2.2 (already routed via PR #72/#74) →
  Q2 reverse-pol FET → Q2.3 (+5V_BEC_PROT) → U6 IN pins (9-13) →
  U6 OUT pins (3-8) → U2.1, U2.3 (+5V LDO input)

Master scope: "+5V_BEC plane via to U6.VIN; U6.VOUT trace to U2 LDO input"
(plus the upstream Q2 hop, which is the corrective fix path).

Routes:
1. +5V_BEC_PROT: Q2.3 (24.07, 21.50) → U6 east side pads (13, 12, 11)
   Short ~5mm F.Cu trace. U6 east pads at X=29.45, Y=18.25/18.75/19.25.
2. +5V: U6 west side pads (3, 4, 5, 6) → U2 (22.86, 24.05)
   U6 west pads at X=26.55, Y=17.75-19.25. Trace ~3mm to U2.1.
3. Bridge U6.3-8 (+5V net, 6 pads). Bridge U6.9-13 (+5V_BEC_PROT, 5 pads).
4. EFUSE_DVDT: U6.18 → C7
5. EFUSE_ILIM: U6.17 → R4 (currently parked — defer wiring)
6. EFUSE_OVP: U6.15 → R9+R10 divider (R9 placed at (39, 22))
7. EFUSE_EN: U6.14 → R7+R8 divider (R7 placed at (35, 22))
8. EFUSE_PGOOD: U6.2 → pull-up R5 (parked) + maybe MCU GPIO (defer)
9. EFUSE_FLT: U6.20 → pull-up R13 (placed at (43, 22)) + MCU GPIO (defer)

DEFER pull-ups R5 (parked) + IMON (test point). EFUSE_PGOOD/FLT
routing to MCU GPIO needs MCU pin mapping — defer.
"""
import os
import sys
import math
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")
F_CU = pcbnew.F_Cu
B_CU = pcbnew.B_Cu

W_PWR = 0.50
W_SIG = 0.20


def _mm(x): return pcbnew.FromMM(x)


def add_track(brd, x1, y1, x2, y2, net_obj, layer=F_CU, w_mm=W_PWR):
    t = pcbnew.PCB_TRACK(brd)
    t.SetStart(pcbnew.VECTOR2I(_mm(x1), _mm(y1)))
    t.SetEnd(pcbnew.VECTOR2I(_mm(x2), _mm(y2)))
    t.SetWidth(_mm(w_mm))
    t.SetLayer(layer)
    t.SetNet(net_obj)
    brd.Add(t)


def add_via(brd, x, y, net_obj):
    v = pcbnew.PCB_VIA(brd)
    v.SetPosition(pcbnew.VECTOR2I(_mm(x), _mm(y)))
    v.SetWidth(_mm(0.5))
    v.SetDrill(_mm(0.3))
    v.SetNet(net_obj)
    brd.Add(v)


def get_net(brd, name):
    nets = brd.GetNetsByName().asdict()
    for k, v in nets.items():
        kv = k.value() if hasattr(k, 'value') else str(k)
        if kv == name:
            return v
    return None


def get_pad_pos(brd, ref, pin):
    for fp in brd.GetFootprints():
        if fp.GetReference() == ref:
            for pad in fp.Pads():
                if pad.GetPadName() == pin:
                    p = pad.GetPosition()
                    return (p.x/1e6, p.y/1e6)
    return None


def main():
    print("=== U6 eFuse power routing ===", flush=True)
    brd = pcbnew.LoadBoard(PCB)

    n_5v = get_net(brd, "+5V")
    n_5v_bec_prot = get_net(brd, "+5V_BEC_PROT")
    n_dvdt = get_net(brd, "EFUSE_DVDT")
    n_en = get_net(brd, "EFUSE_EN")
    n_ovp = get_net(brd, "EFUSE_OVP")

    # U6 pad positions (with new netlist)
    print("U6 +5V (west) pads:")
    for pin in ["3", "4", "5", "6", "7", "8"]:
        p = get_pad_pos(brd, "U6", pin)
        print(f"  U6.{pin}: {p}")
    print("U6 +5V_BEC_PROT (east) pads:")
    for pin in ["9", "10", "11", "12", "13"]:
        p = get_pad_pos(brd, "U6", pin)
        print(f"  U6.{pin}: {p}")

    print(f"\n--- MUTATE: U6 routing ---", flush=True)

    # 1. +5V_BEC_PROT: Q2.3 → U6 east side
    # Trace width 0.30mm so clearance to U6.14 (EFUSE_EN, different net at Y=17.75)
    # passes 0.2mm rule (trace north edge at Y=18.10, pad south edge at Y=17.875 = 0.225mm).
    print("[1] +5V_BEC_PROT: Q2.3 → U6 east", flush=True)
    add_track(brd, 24.07, 21.50, 29.45, 21.50, n_5v_bec_prot, w_mm=0.30)
    add_track(brd, 29.45, 21.50, 29.45, 18.50, n_5v_bec_prot, w_mm=0.30)  # stop short of U6.13 center
    # Bridge U6.13/12/11 by connecting at the trace's south endpoint at Y=18.5
    # Actually each pad is at Y=18.25/18.75/19.25 separated by 0.5mm. Pads are
    # 0.25mm tall so span is small. Bridge with W=0.20 vertical at X=29.45.
    add_track(brd, 29.45, 18.50, 29.45, 19.25, n_5v_bec_prot, w_mm=0.20)
    # U6.10 (28.75, 19.95) + U6.9 (28.25, 19.95) — south edge bridge
    add_track(brd, 29.45, 19.25, 28.75, 19.95, n_5v_bec_prot, w_mm=0.20)
    add_track(brd, 28.75, 19.95, 28.25, 19.95, n_5v_bec_prot, w_mm=0.20)

    # 2. +5V: U6 west pads → U2.1 (via B.Cu — F.Cu blocked by Q2.3 +5V_BEC_PROT
    # at (24.07, 21.50) east-edge X=24.81 + U2.5 +3V3 at (25.14, 24.05) west-edge
    # X=24.48 — overlapping in X means no clean F.Cu corridor between them).
    print("[2] +5V: U6 west bridge → via → B.Cu → U2.1/U2.3", flush=True)
    # West bridge U6.3-6 (F.Cu, same-net touching OK)
    add_track(brd, 26.55, 17.75, 26.55, 19.25, n_5v, w_mm=0.20)
    add_track(brd, 26.55, 19.25, 27.25, 19.95, n_5v, w_mm=0.20)
    add_track(brd, 27.25, 19.95, 27.75, 19.95, n_5v, w_mm=0.20)
    # F.Cu stub from U6.3 west to via location in clear area
    # Via at (25.5, 17.75) — clearance to U6.2 (EFUSE_PGOOD adjacent Y=17.25) OK
    add_track(brd, 26.55, 17.75, 25.5, 17.75, n_5v, w_mm=0.30)
    add_via(brd, 25.5, 17.75, n_5v)
    # B.Cu trace from (25.5, 17.75) to U2.1 area at (22.86, 24.05)
    # B.Cu is mostly empty (just USB sliver + I2C2 sliver, far from this area)
    add_track(brd, 25.5, 17.75, 22.86, 24.05, n_5v, layer=B_CU, w_mm=0.30)
    # Via at U2.1 center (1.32mm pad easily accommodates 0.5mm via)
    add_via(brd, 22.86, 24.05, n_5v)
    # U2.1 ↔ U2.3 B.Cu bridge (avoid F.Cu through U2.2 GND)
    add_via(brd, 22.86, 25.95, n_5v)
    add_track(brd, 22.86, 24.05, 22.86, 25.95, n_5v, layer=B_CU, w_mm=0.30)

    # 3. EFUSE_DVDT routing DEFERRED — short route U6.18 → C7 conflicts
    # with R42 pads at Y=14.5. Would need B.Cu via, but U6.18 pad
    # (0.25 × 0.85mm) too narrow for 0.5mm via.

    pcbnew.SaveBoard(PCB, brd)
    print(f"\n  Saved {PCB}")
    print(f"\n  Deferred: EFUSE_EN/OVP/ILIM/PGOOD/FLT routing + R5/R12 parked-cap routing")
    return 0


if __name__ == "__main__":
    sys.exit(main())
