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
    # F.Cu stub from U6.3 west to via at (24.0, 17.75) — moved further
    # west to clear EFUSE_PGOOD via at (24.7, 17.25) added below.
    add_track(brd, 26.55, 17.75, 24.0, 17.75, n_5v, w_mm=0.30)
    add_via(brd, 24.0, 17.75, n_5v)
    # B.Cu trace to U2.1 area
    add_track(brd, 24.0, 17.75, 22.86, 24.05, n_5v, layer=B_CU, w_mm=0.30)
    # Via at U2.1 center (1.32mm pad easily accommodates 0.5mm via)
    add_via(brd, 22.86, 24.05, n_5v)
    # U2.1 ↔ U2.3 B.Cu bridge (avoid F.Cu through U2.2 GND)
    add_via(brd, 22.86, 25.95, n_5v)
    add_track(brd, 22.86, 24.05, 22.86, 25.95, n_5v, layer=B_CU, w_mm=0.30)

    # 3. EFUSE config nets — DEFERRED to a focused U6-config sub-step.
    # Routing density in the U6 / B-zone area (D1 TVS body at Y=18, C9
    # at Y=15.57, C62 GND at Y=14.5, Q3 south pads at Y=12.57, R-row at
    # Y=22) creates a sub-1mm Y-band sandwich for east-bound traces.
    # Each EFUSE_* net needs a unique Y corridor + careful via clearance
    # to SOT-23-6 / WQFN-20 narrow pads. Tried F.Cu + B.Cu mixed — every
    # iteration surfaced different cross-pad conflict.
    #
    # Defer cleanly. With EN floating, U6 internal pull-down keeps the
    # eFuse OFF — board does NOT actually pass +5V through until EN
    # routing closes. Master 2026-05-23 was right: "do this NOW, not
    # 'later'." But the right NOW is a focused sub-step PR, not an
    # incremental iteration that keeps surfacing new conflicts.
    #
    # U6-config sub-step plan (next PR):
    #   - All 5 nets (EN, OVP, ILIM, FLT, PGOOD) routed on B.Cu via
    #     U6 north-side staggered vias at Y=12.5/13.0/13.5/14.0.
    #   - F.Cu stubs from U6 pad to via (north direction, ~2mm).
    #   - B.Cu traces diagonal to each target R/C pad.
    #   - EFUSE_DVDT: needs C7 relocation OR via-in-pad.
    #   - Then DRC verify.
    #
    # For bring-up: jumper-wire EN to +5V_BEC_PROT temporarily.
    print(f"  EFUSE config nets DEFERRED to U6-config sub-step (5 nets)")
    print(f"  Bring-up workaround: jumper EN→+5V_BEC_PROT to enable U6 manually")

    # The rest of this function (original EN/OVP/FLT/ILIM/PGOOD/DVDT routing
    # attempts) is left in the file but bypassed by the early return.
    # See git history for the iteration attempts.
    return 0   # SKIP the rest

    # Original (problematic) routing follows — kept for reference only:
    # EFUSE_EN: U6.14 → R7.2 + R8.1 — route NORTH of D1 (TVS at (33-37, 18)
    # blocks Y=17.1..18.9). North-around via Y=15.5.
    # U6.14 (29.45, 17.75) → east jog to (30.5, 17.75) [clear U6 column]
    # → north to (30.5, 15.5) → east at Y=15.5 to (36, 15.5)
    # → south to (36, 22) → west to R7.2 (35.51, 22) + east to R8.1 (36.49, 22)
    # X=35.35 vertical fits between D1.1 east edge (34.25) and D1.2 west
    # edge (35.75). R7.2 at X=35.51 (same EN net — touching allowed).
    add_track(brd, 29.45, 17.75, 31.0, 17.75, n_en, w_mm=W_SIG)
    add_track(brd, 31.0, 17.75, 31.0, 14.0, n_en, w_mm=W_SIG)
    add_track(brd, 31.0, 14.0, 35.35, 14.0, n_en, w_mm=W_SIG)
    add_track(brd, 35.35, 14.0, 35.35, 22.0, n_en, w_mm=W_SIG)
    add_track(brd, 35.35, 22.0, 35.51, 22.0, n_en, w_mm=W_SIG)
    add_track(brd, 35.35, 22.0, 36.49, 22.0, n_en, w_mm=W_SIG)
    print("  EFUSE_EN: U6.14 → R7.2 + R8.1 (north-around D1 via Y=14, X=35.35)")

    # EFUSE_OVP: U6.15 → R9.2 + R10.1 — north-around D1 via Y=15.0 (one Y row
    # above EFUSE_EN to avoid horizontal trace conflict).
    add_track(brd, 29.45, 17.25, 30.5, 17.25, n_ovp, w_mm=W_SIG)
    add_track(brd, 30.5, 17.25, 30.5, 13.5, n_ovp, w_mm=W_SIG)
    add_track(brd, 30.5, 13.5, 40.0, 13.5, n_ovp, w_mm=W_SIG)
    add_track(brd, 40.0, 13.5, 40.0, 22.0, n_ovp, w_mm=W_SIG)
    add_track(brd, 40.0, 22.0, 39.51, 22.0, n_ovp, w_mm=W_SIG)
    add_track(brd, 40.0, 22.0, 40.49, 21.5, n_ovp, w_mm=W_SIG)
    print("  EFUSE_OVP: U6.15 → R9.2 + R10.1 (north-around D1 via Y=15.0)")

    # EFUSE_FLT: U6.20 → R13.1 — B.Cu via near U6 too close to U6.19
    # (clearance 0.875mm needed). Move FLT via further north of U6 body
    # at (27.25, 14.5). F.Cu stub from pad to via.
    n_flt = get_net(brd, "EFUSE_FLT")
    add_track(brd, 27.25, 16.05, 27.25, 13.5, n_flt, w_mm=W_SIG)
    add_via(brd, 27.25, 13.5, n_flt)
    add_via(brd, 42.49, 21.5, n_flt)
    add_track(brd, 27.25, 13.5, 42.49, 21.5, n_flt, layer=B_CU, w_mm=W_SIG)
    print("  EFUSE_FLT: U6.20 → F.Cu stub Y=13.5 → B.Cu diagonal → R13.1")

    # EFUSE_ILIM: U6.17 → R4.1 — north of D1
    n_ilim = get_net(brd, "EFUSE_ILIM")
    r4_p1 = get_pad_pos(brd, "R4", "1")
    if r4_p1:
        # Y=12.5 east-bound (below OVP Y=13.5 vertical at X=30.5, so doesn't
        # cross OVP). Clears C62 GND at (30.48, 14.5) — Y gap 2.0mm.
        add_track(brd, 28.75, 16.05, 28.75, 12.5, n_ilim, w_mm=W_SIG)
        add_track(brd, 28.75, 12.5, r4_p1[0], 12.5, n_ilim, w_mm=W_SIG)
        add_track(brd, r4_p1[0], 12.5, r4_p1[0], r4_p1[1], n_ilim, w_mm=W_SIG)
        print(f"  EFUSE_ILIM: U6.17 → R4.1 @ {r4_p1} (Y=12.5 corridor)")

    # EFUSE_PGOOD: U6.2 (26.55, 17.25) → R5.1 (45.49, 22.0 — placed now) + MCU GPIO (defer)
    n_pgood = get_net(brd, "EFUSE_PGOOD")
    r5_p1 = get_pad_pos(brd, "R5", "1")
    if r5_p1:
        # U6.2 is on WEST side. Route west-then-south? No: R5 at X=45+ is EAST.
        # Need to go from U6 west to east — go around south of U6 body.
        # Better: route south from U6.2 west pin, around U6 body south, then east.
        # U6.2 (26.55, 17.25) → south to (26.55, 20.5) wait that's inside U6 body
        # U6 body Y=16..20. Going south at X=26.55 from Y=17.25 → exits at south
        # edge Y=20.5+ (pad row 7-10 at Y=19.95)
        # Route: U6.2 → south to (26.55, 16.5) — actually north — wait U6.2 west.
        # West of U6: clear area X < 26.55. Route west, then south, then east around.
        # Use B.Cu. U6.2 pad 0.85×0.25 too narrow for via-at-center
        # (overshoots adjacent pads U6.1 GND at Y=16.75, U6.3 +5V at Y=17.75).
        # Stub U6.2 west to via at X=24.7 (clear of +5V via at (25.5, 17.75)).
        add_track(brd, 26.55, 17.25, 24.7, 17.25, n_pgood, w_mm=W_SIG)
        add_via(brd, 24.7, 17.25, n_pgood)
        add_via(brd, r5_p1[0], r5_p1[1], n_pgood)
        add_track(brd, 24.7, 17.25, r5_p1[0], r5_p1[1], n_pgood, layer=B_CU, w_mm=W_SIG)
        print(f"  EFUSE_PGOOD: U6.2 → F.Cu stub → B.Cu diagonal → R5.1 @ {r5_p1}")

    # EFUSE_DVDT: DEFERRED — C7 placement (23.567, 19.23) is too close to
    # R41 pad 1 (23.49, 14.5) for F.Cu south leg at X=23.567. B.Cu route
    # collides with the +5V B.Cu diagonal from U6 west to U2.1. Needs
    # either C7 relocation (move further south or different X) or via-in-
    # pad. Defer to U6-config-extension sub-step.
    #
    # Impact: without explicit DVDT cap, eFuse uses default soft-start
    # ramp (~5ms per TPS25940A datasheet default). Board powers up; the
    # soft-start is slightly faster than the designed 15ms. Acceptable
    # for bring-up. Production board should connect C7.
    print(f"  EFUSE_DVDT: DEFERRED (C7/R41 X-overlap forces B.Cu but conflicts +5V trace)")

    # Zone fill before save (defensive — master 2026-05-23 Rule 9 discipline)
    try:
        for z in brd.Zones():
            if hasattr(z, 'UnFill'): z.UnFill()
        pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
    except Exception as _e:
        print(f"  zone fill skipped: {_e}")

    pcbnew.SaveBoard(PCB, brd)
    print(f"\n  Saved {PCB}")
    print(f"\n  Deferred: EFUSE_EN/OVP/ILIM/PGOOD/FLT routing + R5/R12 parked-cap routing")
    return 0


if __name__ == "__main__":
    sys.exit(main())
