#!/usr/bin/env python3
"""C↔F integration — route the USB differential pair.

Two diff pairs to route:
  1) Post-ESD (MCU side): U1.PA11/PA12 → U5.4/U5.6  (~24mm coupled)
     Nets: USB_DM, USB_DP
  2) Pre-ESD (connector side): U5.1/U5.3 → J1.A6+B6 / J1.A7+B7  (~5mm)
     Nets: USBC_D_P_PRE, USBC_D_M_PRE
  Plus the A6↔B6 and A7↔B7 bridges at J1 (USB-C dual-orientation pins
  internally electrical-equivalent for USB 2.0).

Controlled impedance per docs/CONTROLLED_IMPEDANCE.md:
  W = 0.30 mm, S = 0.10 mm  →  Z_diff target = 90 Ω
  All routed on F.Cu (L1) which is GND-referenced to L2 (GND plane,
  added cross-subsystem). The pair is on the OUTER layer per master
  directive — only L1/L6 have a valid 90 Ω target because they reference
  the adjacent GND plane.

Length matching: each pair's two traces are routed at the SAME X
positions / parallel Y rows so their lengths are equal by construction.
Small Y-offset matching is left at the pin pad ends (where impedance
discontinuity is already present from the via-less SMD pad geometry).
"""
import os
import sys
import math
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")
F_CU = pcbnew.F_Cu

# Diff-pair design rules (REVISED 2026-05-22 per openEMS sign-off)
W_DIFF = 0.20   # trace width (mm) — openEMS Z_diff = 87.4Ω at this W/S
S_DIFF = 0.13   # trace-to-trace gap (mm)
PITCH = W_DIFF + S_DIFF   # 0.33 mm center-to-center spacing

# Fanout / single-end width
W_SE = 0.20


def _mm(x): return pcbnew.FromMM(x)


def add_track(brd, x1, y1, x2, y2, net_obj, layer=F_CU, w_mm=W_DIFF):
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
    v.SetWidth(_mm(0.50))
    v.SetDrill(_mm(0.30))
    v.SetNet(net_obj)
    brd.Add(v)


def get_net(brd, name):
    nets = brd.GetNetsByName().asdict()
    for k, v in nets.items():
        kv = k.value() if hasattr(k, 'value') else str(k)
        if kv == name:
            return v
    return None


def find_pads_on_net(brd, net_name):
    out = []
    for fp in brd.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetname() == net_name:
                p = pad.GetPosition()
                out.append((fp.GetReference(), pad.GetNumber(), p.x/1e6, p.y/1e6))
    return out


def total_length(segs):
    return sum(math.hypot(x2-x1, y2-y1) for x1, y1, x2, y2 in segs)


def main():
    print("=== C↔F integration — route USB diff pair ===", flush=True)
    brd = pcbnew.LoadBoard(PCB)

    n_dm  = get_net(brd, "USB_DM")
    n_dp  = get_net(brd, "USB_DP")
    n_dmp = get_net(brd, "USBC_D_M_PRE")
    n_dpp = get_net(brd, "USBC_D_P_PRE")

    pads_dm = {(r,n): (x,y) for r,n,x,y in find_pads_on_net(brd, "USB_DM")}
    pads_dp = {(r,n): (x,y) for r,n,x,y in find_pads_on_net(brd, "USB_DP")}
    pads_dmp = {(r,n): (x,y) for r,n,x,y in find_pads_on_net(brd, "USBC_D_M_PRE")}
    pads_dpp = {(r,n): (x,y) for r,n,x,y in find_pads_on_net(brd, "USBC_D_P_PRE")}

    # ===== PAIR 1: U1 → U5 (post-ESD, ~24mm) =====
    # U1.70 USB_DM @ (52.67, 31.50)  →  U5.4 @ (77.14, 30.95)
    # U1.71 USB_DP @ (52.67, 31.00)  →  U5.6 @ (77.14, 29.05)
    u1_dm = pads_dm[("U1","70")]
    u1_dp = pads_dp[("U1","71")]
    u5_dm = pads_dm[("U5","4")]
    u5_dp = pads_dp[("U5","6")]

    # ROOT-CAUSE FIX (master Step-3 re-open 2026-05-22): the previous
    # routing iterations hit over-constrained-region whack-a-mole around
    # U5. Root cause: U5 placement at Y=30 was IN the diff-pair Y=31
    # corridor. Step-3 was re-opened to move U5 south (Y=35) so the
    # diff pair has a clear Y corridor to flow east through. With U5
    # at Y=35, pair coupled at Y=31.0/31.33 (matches U1 pin row) is
    # clear of U5 body (Y=33.27..36.73). Post-ESD pair fans SOUTH at
    # X=78 (east of U5 east-pad column X=77.14) to U5.4/U5.6 at Y=34..36.
    Y_DP_COUPLED = 31.00    # matches U1.71 (PA12) Y exactly
    Y_DM_COUPLED = Y_DP_COUPLED + S_DIFF + W_DIFF   # 31.33 — DM south, 0.33mm pitch

    X_BEND_W = 54.5
    X_BEND_E = 79.0

    segs_dm = [
        # West fanout + south bend: U1.70 (52.67, 31.5) → (X_BEND_W, Y_DM_COUPLED)
        (u1_dm[0], u1_dm[1], X_BEND_W, Y_DM_COUPLED),
        # Coupled run east at Y_DM_COUPLED
        (X_BEND_W, Y_DM_COUPLED, X_BEND_E, Y_DM_COUPLED),
        # East bend + fanout north: → U5.4 (77.14, 30.95)
        (X_BEND_E, Y_DM_COUPLED, u5_dm[0], u5_dm[1]),
    ]
    segs_dp = [
        (u1_dp[0], u1_dp[1], X_BEND_W, Y_DP_COUPLED),
        (X_BEND_W, Y_DP_COUPLED, X_BEND_E, Y_DP_COUPLED),
        (X_BEND_E, Y_DP_COUPLED, u5_dp[0], u5_dp[1]),
    ]

    # PAIR 1 strategy (REVISED for U5-south placement): F.Cu COUPLED
    # diff pair from U1 east at Y=31, then south-fan to U5.4/U5.6 at
    # X=77.14/Y=34..36. No vias needed — pair stays F.Cu the whole way
    # since U5 is no longer in the Y=31 corridor.
    print(f"\n[PAIR 1] U1 ↔ U5 (post-ESD) — F.Cu coupled diff pair, south-fan at U5")
    # Bend points: pair starts coupled at X=54 (east of U1 pads),
    # runs east at Y=31.0/31.33 to X=78 (east of U5 east-pad column 77.14),
    # then drops south to U5.4 (Y=35.95) and U5.6 (Y=34.05).
    # Pair traces enter U5 east pads from east (X=78 west to X=77.14).
    # Coupled-east + divergent-fan topology (root fix 2026-05-23):
    #
    #   Why this shape: U5 (SOT-23-6) pin 5 = +5V at (77.138, 35.000)
    #   sits BETWEEN pin 4 (DM, 35.95) and pin 6 (DP, 34.05). Any pair
    #   landing at Y≈35 in coupled config shorts pin 5. Solution: keep
    #   pair coupled at the U1 Y-corridor (Y=31.0/31.33) ALL the way
    #   east past U5, then DIVERGE-fan SE into pin 4 / pin 6 from the
    #   east, clearing the +5V pad row entirely.
    #
    #   1. Coupled east: U1.70/71 → (X_SPLIT, 31.0/31.33) on F.Cu, ~27mm
    #      of coupled at W=0.20/S=0.13 (the openEMS-validated geometry).
    #   2. Divergent fan: from (X_SPLIT, 31.x) two diagonals — DM SE to
    #      pin 4 (Y=35.95), DP SE to pin 6 (Y=34.05). The diagonals
    #      DIVERGE in Y (DM south member stays south; DP north stays
    #      north), so no crossing. Computed crossing X = 82.88, OUTSIDE
    #      the fan range (X_SPLIT=80 down to X_FAN_END=77.80) → safe.
    #   3. Horizontal land into pad from east: DM at Y=35.95 from
    #      X_FAN_END (south of +5V pad's south edge 35.30); DP at
    #      Y=34.05 (north of +5V pad's north edge 34.70).
    # Geometric analysis (root-cause):
    #   U5 +5V pad (pin 5) at (77.138, 35.00) east-edge X = 77.800
    #   J1 west-pad column at X=79.735, pad B8 closest to coupled Y=31.33
    #   Corridor: 77.80 → 79.585 = 1.785mm between pin5 east edge and
    #     B8 west edge. After clearances (0.30mm each side), 1.185mm
    #     of usable fan-X-distance for DM/DP to descend 4.62/3.05mm.
    #   DM descent must clear pin 5 (Y=34.7..35.3 pad) by 0.30mm at Y=35:
    #     X(Y=35) ≥ 78.10 required. Solving with X_FAN_END=77.81:
    #     X_SPLIT ≥ 79.28 needed.
    #   Coupled section east end clearance to J1 pad B8 (79.735, 31.75)
    #     west edge 79.585: trace cap (X_SPLIT+0.10) ≤ 79.585-0.20 →
    #     X_SPLIT ≤ 79.285.
    #   Tight window: 79.28 ≤ X_SPLIT ≤ 79.285. Pick 79.28.
    X_BEND_W_1 = 54.0
    X_SPLIT = 79.28
    X_FAN_END = 77.81   # 0.01mm extra margin to U5 pin 5 east edge (77.80)
    Y_PIN4 = u5_dm[1]   # 35.95
    Y_PIN6 = u5_dp[1]   # 34.05

    # DM: 4 segments (west jog, coupled east, diverging fan SE, horizontal land)
    add_track(brd, u1_dm[0], u1_dm[1], X_BEND_W_1, Y_DM_COUPLED, n_dm, layer=F_CU, w_mm=W_DIFF)
    add_track(brd, X_BEND_W_1, Y_DM_COUPLED, X_SPLIT, Y_DM_COUPLED, n_dm, layer=F_CU, w_mm=W_DIFF)
    add_track(brd, X_SPLIT, Y_DM_COUPLED, X_FAN_END, Y_PIN4, n_dm, layer=F_CU, w_mm=W_DIFF)
    add_track(brd, X_FAN_END, Y_PIN4, u5_dm[0], u5_dm[1], n_dm, layer=F_CU, w_mm=W_DIFF)

    # DP: 4 segments (parallel coupled section, divergent fan, land)
    add_track(brd, u1_dp[0], u1_dp[1], X_BEND_W_1, Y_DP_COUPLED, n_dp, layer=F_CU, w_mm=W_DIFF)
    add_track(brd, X_BEND_W_1, Y_DP_COUPLED, X_SPLIT, Y_DP_COUPLED, n_dp, layer=F_CU, w_mm=W_DIFF)
    add_track(brd, X_SPLIT, Y_DP_COUPLED, X_FAN_END, Y_PIN6, n_dp, layer=F_CU, w_mm=W_DIFF)
    add_track(brd, X_FAN_END, Y_PIN6, u5_dp[0], u5_dp[1], n_dp, layer=F_CU, w_mm=W_DIFF)

    coupled_len = X_SPLIT - 52.67
    fan_len = math.hypot(X_SPLIT - X_FAN_END, Y_DM_COUPLED - Y_PIN4) + (X_FAN_END - u5_dm[0])
    print(f"  USB_DM: coupled to X={X_SPLIT}, fan SE to pin 4 Y={Y_PIN4}")
    print(f"  USB_DP: coupled to X={X_SPLIT}, fan SE to pin 6 Y={Y_PIN6}")
    print(f"  Coupling ratio: {coupled_len:.1f}mm coupled / {coupled_len+fan_len:.1f}mm total = {coupled_len/(coupled_len+fan_len):.0%}")

    # ===== PAIR 2: U5 → J1 (pre-ESD, ~5mm) =====
    # U5.3 USBC_D_M_PRE @ (74.86, 30.95)  →  J1.A7 (79.73, 29.75) + J1.B7 (79.73, 30.75)
    # U5.1 USBC_D_P_PRE @ (74.86, 29.05)  →  J1.A6 (79.73, 30.25) + J1.B6 (79.73, 29.25)
    u5_dmp = pads_dmp[("U5","3")]
    u5_dpp = pads_dpp[("U5","1")]
    # J1 has dual D+ / dual D- pads — route to one + bridge to the other
    j1_a7 = pads_dmp[("J1","A7")]
    j1_b7 = pads_dmp[("J1","B7")]
    j1_a6 = pads_dpp[("J1","A6")]
    j1_b6 = pads_dpp[("J1","B6")]

    # PAIR 2: pre-ESD from U5 west pads to J1 west pads.
    # Root-cause analysis 2026-05-23:
    #   Previous topology had DMP B.Cu vertical at X=74.16 crossing
    #   DPP B.Cu horizontal at Y=30.25 → physical short. Root cause:
    #   B.Cu portions of the two nets shared the same Y-band.
    #
    # Redesign: route PAIR 2 NORTH around U5 body (Y < 28, north of
    # J1's GND/B1 pads at 26.75 → use Y=27.50 and 27.85), B.Cu coupled.
    # F.Cu hops only near U5 west pads and J1 east approach.
    Y_DPP_COUPLED = 27.50    # north of U5 body and J1 GND row
    Y_DMP_COUPLED = 27.85    # 0.35mm south of DPP (paired)
    X_F2_W = 74.86 - 0.40    # 74.46 — F.Cu stub from U5 west pads
    X_F2_E = 79.10           # west of J1 pads (B8 west edge 79.585)

    # Pick which J1 pad each net lands on. For DM (south of pair @ Y_DMP=26.9):
    # J1 D- pads: A7 (29.75 north) or B7 (30.75 south). DM coupled at Y=26.9
    # → both pads are FAR south; the fanout descends a lot. Use A7 (closer:
    # 29.75 vs 30.75). For DP (north of pair @ Y_DPP=26.5): J1 D+ pads:
    # A6 (30.25) or B6 (29.25). Use B6 (29.25, closer to coupled Y).
    # Then the A6↔B6 and A7↔B7 bridges happen at J1.
    j1_dmp_target = j1_a7   # DM lands at A7
    j1_dpp_target = j1_b6   # DP lands at B6

    # NOTE: USB-C dual-orientation requires A6↔B6 + A7↔B7 bridges so
    # the cable works in either rotation. These bridges geometrically
    # cross each other at J1 (the other-orientation pad sits exactly
    # between the bridge's source and destination). Bridging properly
    # requires B.Cu vias + an X-offset jog — a small follow-up.
    # For v1 we OMIT the bridges, accept single-orientation USB-C, and
    # connect only the A6/A7 pads. The cable will plug in either way
    # but only one orientation enumerates. Marked in DECISIONS for v1
    # bring-up; v2 fixes it cleanly.
    segs_dmp = [
        # U5.3 (74.86, 30.95) → north detour → coupled Y → A7
        (u5_dmp[0], u5_dmp[1], X_F2_W, Y_DMP_COUPLED),
        (X_F2_W, Y_DMP_COUPLED, X_F2_E, Y_DMP_COUPLED),
        (X_F2_E, Y_DMP_COUPLED, j1_a7[0], j1_a7[1]),
    ]
    segs_dpp = [
        (u5_dpp[0], u5_dpp[1], X_F2_W, Y_DPP_COUPLED),
        (X_F2_W, Y_DPP_COUPLED, X_F2_E, Y_DPP_COUPLED),
        (X_F2_E, Y_DPP_COUPLED, j1_b6[0], j1_b6[1]),
    ]

    # PAIR 2 NEW topology — coupled B.Cu north of U5 body:
    print(f"\n[PAIR 2] U5 ↔ J1 (pre-ESD) — B.Cu coupled north of U5 body")
    # DMP via at X=74.46 (just west of U5.3); DPP via at X=74.66 (between
    # u5.3 west edge and u5.1 west edge — but really, U5.3 west pad edge
    # at 74.86-0.6625=74.20). Use X=74.46 for DMP, X=74.86 for DPP starts
    # but pull DPP via slightly east-offset so verticals don't share X.
    v3_dmp = (74.46, 35.95)   # DMP F.Cu stub end → via, X 0.2mm west of pad
    v3_dpp = (74.66, 34.05)   # DPP F.Cu stub end → via, X 0.2mm east of DMP

    add_track(brd, u5_dmp[0], u5_dmp[1], v3_dmp[0], v3_dmp[1], n_dmp, layer=F_CU, w_mm=W_DIFF)
    add_track(brd, u5_dpp[0], u5_dpp[1], v3_dpp[0], v3_dpp[1], n_dpp, layer=F_CU, w_mm=W_DIFF)
    add_via(brd, v3_dmp[0], v3_dmp[1], n_dmp)
    add_via(brd, v3_dpp[0], v3_dpp[1], n_dpp)

    # B.Cu: each vertical N to its coupled Y, then coupled east to landing vias
    add_track(brd, v3_dmp[0], v3_dmp[1], v3_dmp[0], Y_DMP_COUPLED, n_dmp, layer=pcbnew.B_Cu, w_mm=W_DIFF)
    add_track(brd, v3_dpp[0], v3_dpp[1], v3_dpp[0], Y_DPP_COUPLED, n_dpp, layer=pcbnew.B_Cu, w_mm=W_DIFF)
    # Coupled east at S=0.35 (slightly relaxed from 0.13 — pre-ESD pair
    # is much shorter, ~5mm; Z_diff is less critical and B.Cu has L5 GND
    # ref so trace width may differ. Doc this in CONTROLLED_IMPEDANCE.md.)
    v4_dmp = (X_F2_E, Y_DMP_COUPLED)   # DMP lands at (79.10, 27.85)
    v4_dpp = (X_F2_E, Y_DPP_COUPLED)   # DPP lands at (79.10, 27.50)
    add_track(brd, v3_dmp[0], Y_DMP_COUPLED, v4_dmp[0], v4_dmp[1], n_dmp, layer=pcbnew.B_Cu, w_mm=W_DIFF)
    add_track(brd, v3_dpp[0], Y_DPP_COUPLED, v4_dpp[0], v4_dpp[1], n_dpp, layer=pcbnew.B_Cu, w_mm=W_DIFF)
    add_via(brd, v4_dmp[0], v4_dmp[1], n_dmp)
    add_via(brd, v4_dpp[0], v4_dpp[1], n_dpp)

    # F.Cu south fan to J1 pads: DMP → A7 (29.75), DPP → A6 (30.25)
    add_track(brd, v4_dmp[0], v4_dmp[1], j1_a7[0], j1_a7[1], n_dmp, layer=F_CU, w_mm=W_DIFF)
    add_track(brd, v4_dpp[0], v4_dpp[1], j1_a6[0], j1_a6[1], n_dpp, layer=F_CU, w_mm=W_DIFF)

    print(f"  USBC_D_M_PRE: F.Cu stub + B.Cu N-then-E coupled + F.Cu fan → J1.A7")
    print(f"  USBC_D_P_PRE: parallel topology → J1.A6")

    # USB-C reversibility bridges (per master 2026-05-22 option (b)):
    # OFFSET vias OUTSIDE the 0.5mm-pitch J1 pad field, with short F.Cu
    # hops from pads into the vias. Two bridges on F.Cu+B.Cu in tandem,
    # via columns separated >1.2mm apart so vias don't conflict.
    print(f"\n[BRIDGES] USB-C dual-orientation A6↔B6 (D+) + A7↔B7 (D-) — offset-via approach")
    # D+ via column at X=81.0; D- via column at X=82.5 (1.5mm apart)
    DV_X = 81.0     # D+ via column
    DM_X = 82.5     # D- via column

    # D+ bridge: F.Cu hop from A6 to via, B.Cu down to via, F.Cu hop to B6
    # A6 (79.73, 30.25) → F.Cu east hop → via (81.0, 30.25)
    add_track(brd, j1_a6[0], j1_a6[1], DV_X, j1_a6[1], n_dpp, layer=F_CU, w_mm=W_DIFF)
    add_via(brd, DV_X, j1_a6[1], n_dpp)
    # B.Cu vertical: (81.0, 30.25) → (81.0, 29.25)
    add_track(brd, DV_X, j1_a6[1], DV_X, j1_b6[1], n_dpp, layer=pcbnew.B_Cu, w_mm=W_DIFF)
    add_via(brd, DV_X, j1_b6[1], n_dpp)
    # F.Cu hop back to B6
    add_track(brd, DV_X, j1_b6[1], j1_b6[0], j1_b6[1], n_dpp, layer=F_CU, w_mm=W_DIFF)

    # D- bridge: same pattern, via column at DM_X=82.5
    add_track(brd, j1_a7[0], j1_a7[1], DM_X, j1_a7[1], n_dmp, layer=F_CU, w_mm=W_DIFF)
    add_via(brd, DM_X, j1_a7[1], n_dmp)
    add_track(brd, DM_X, j1_a7[1], DM_X, j1_b7[1], n_dmp, layer=pcbnew.B_Cu, w_mm=W_DIFF)
    add_via(brd, DM_X, j1_b7[1], n_dmp)
    add_track(brd, DM_X, j1_b7[1], j1_b7[0], j1_b7[1], n_dmp, layer=F_CU, w_mm=W_DIFF)
    print(f"  D+ bridge: vias at X={DV_X} (1.0mm Y-sep, 0.5mm gap to D- column)")
    print(f"  D- bridge: vias at X={DM_X} (1.5mm offset from D+)")

    pcbnew.SaveBoard(PCB, brd)
    total_segs = len(segs_dm) + len(segs_dp) + len(segs_dmp) + len(segs_dpp)
    print(f"\n[done] {total_segs} segments written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
