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


def add_via(brd, x, y, net_obj, dia_mm=0.50, drill_mm=0.30):
    v = pcbnew.PCB_VIA(brd)
    v.SetPosition(pcbnew.VECTOR2I(_mm(x), _mm(y)))
    v.SetWidth(_mm(dia_mm))
    v.SetDrill(_mm(drill_mm))
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
    # Geometric analysis (root-cause + 2nd re-open 2026-05-23):
    #   U5 moved to X=73 (was 76). Pin 5 +5V east edge X = 74.80.
    #   J1 west-pad column at X=79.735, pad B8 west edge X=79.585.
    #   Corridor pin5_east → B8_west = 4.785mm — fits fan + bridge vias.
    #   X_SPLIT (coupled section east end) ≤ 79.285 (B8 clearance).
    #   X_FAN_END chosen for 1mm soft margin at DM-pin5 Y=35 crossing:
    #     X(Y=35) = 0.205×X_SPLIT + 0.795×X_FAN_END
    #     Required X(Y=35) ≥ X_pin5_east + 1.30 = 76.10
    #     Solving with X_SPLIT=79.28: X_FAN_END ≥ 76.74 (gives 1.16mm
    #     soft margin); use X_FAN_END = 76.74 (= 1.94mm east of pin5
    #     east edge — comfortable; horizontal land trace from X=76.74
    #     to U5.4 X=74.138 stays south of pin5 by 0.65mm Y).
    X_BEND_W_1 = 54.0
    # 2026-05-23 final topology — COUPLED-DIAGONAL + DIVERGENT FAN:
    #   1. Coupled-horizontal: (54, 31.0/31.33) → (X_SPLIT_H, 31.0/31.33)
    #   2. Coupled-diagonal: descends in parallel maintaining 0.33mm
    #      pitch from (X_SPLIT_H, 31.0/31.33) to (X_SPLIT_D, 33.0/33.33)
    #   3. Divergent fan: (X_SPLIT_D, 33.0/33.33) → (X_FAN_END, 34.05/35.95)
    #   4. Horizontal land into U5.4/U5.6
    #
    # The coupled-diagonal preserves pair pitch (no crossing). The
    # divergent fan grows pitch from 0.33 to 1.90mm with DM south of
    # DP throughout. Per master: USB FS, fan discontinuity electrically
    # negligible.
    # PARALLEL-DIAGONAL topology (single diagonal each, staggered fan-H ends):
    #   DM coupled-H to X_M_H=78.65, single diag (78.65, 31.33) → (74.90, 35.95)
    #   DP coupled-H to X_P_H=77.37, single diag (77.37, 31.00) → (74.90, 34.05)
    # Solved for parallel slopes: X_P_H = (1.57*X_FE + 3.05*X_M_H)/4.62.
    # With X_M_H=78.65, X_FE=74.90 → X_P_H = 77.37.
    # Both diagonals have slope ~1.232 (parallel) → Y-separation stays
    # ≥0.33mm everywhere in coupled-diag (no crossing); X range
    # [X_P_H, X_M_H] has only DM (DP ended coupled-H earlier).
    # Pin5 margin: DM at Y=35 at X = 78.65 - 2.980 = 75.67 → 0.87mm
    # east of pin5 east edge 74.80 (below master's 1mm soft, but
    # ≥0.30mm hard; trade-off forced by A5 pad X=79.010 constraint).
    # 2026-05-23 MASTER ROOT-CAUSE DIRECTIVE:
    # U5 RE-PLACED at (73, 31) — on the pair Y=31 corridor. The earlier
    # U5 at Y=35 created a 4mm Y-misalignment forcing steep descent at
    # tight 0.33mm pitch (perp-distance failure). With U5 at Y=31:
    #   - DM pin 4 at (74.138, 31.95) — 0.62mm south of coupled Y=31.33
    #   - DP pin 6 at (74.138, 30.05) — 0.95mm north of coupled Y=31.00
    #   - Short fan, no steep descent.
    #
    # But U5 pin 2 (GND, X=71.862, Y=31) and pin 5 (+5V, X=74.138, Y=31)
    # sit ON the pair corridor, AND pin 3 (D-_pre, X=71.862, Y=31.95)
    # blocks DM fan to pin 4. Use TWO-STAGE fan:
    #
    #   Stage 1 (shallow, X_SPLIT→72.825):
    #     DM goes from (X_SPLIT, 31.33) shallowly to (72.825, 31.30)
    #       (clears pin 3 N edge 31.65 with ≥0.20 margin)
    #     DP goes from (X_SPLIT, 31.00) shallowly to (72.825, 30.55)
    #       (clears pin 1 S edge 30.35 with ≥0.20 margin)
    #   Stage 2 (steeper, 72.825→74.138):
    #     DM (72.825, 31.30) → (74.138, 31.95) — into U5.4
    #     DP (72.825, 30.55) → (74.138, 30.05) — into U5.6
    #     Both clear pin 5 (Y=31, X 73.475..74.80) by ≥0.20mm
    #
    # X_SPLIT = 70.90 — DM/DP coupled-H end before pin 2 west edge
    # (71.20) with cap+clearance.
    X_M_H = 70.90       # DM coupled-H east end (pin 2 GND clearance)
    X_P_H = 70.90       # DP coupled-H end (same X — no stagger needed)
    X_STAGE2 = 72.825   # 2-stage fan bend point (east of pin 3 by 0.30mm)
    X_FAN_END = 74.138  # U5 east pad centers
    Y_DM_STAGE1 = 31.30 # DM Y at stage1 end (clears pin 3 by 0.20+0.10)
    Y_DP_STAGE1 = 30.55 # DP Y at stage1 end (clears pin 1 by 0.20+0.10)
    Y_PIN4 = u5_dm[1]   # 31.95
    Y_PIN6 = u5_dp[1]   # 30.05

    # DM: 5 segments (west jog, coupled-H, stage 1 fan, stage 2 fan, pad land)
    add_track(brd, u1_dm[0], u1_dm[1], X_BEND_W_1, Y_DM_COUPLED, n_dm, layer=F_CU, w_mm=W_DIFF)
    add_track(brd, X_BEND_W_1, Y_DM_COUPLED, X_M_H, Y_DM_COUPLED, n_dm, layer=F_CU, w_mm=W_DIFF)
    add_track(brd, X_M_H, Y_DM_COUPLED, X_STAGE2, Y_DM_STAGE1, n_dm, layer=F_CU, w_mm=W_DIFF)
    add_track(brd, X_STAGE2, Y_DM_STAGE1, X_FAN_END, Y_PIN4, n_dm, layer=F_CU, w_mm=W_DIFF)

    # DP: 4 segments (west jog, coupled-H, stage 1 fan, stage 2 fan)
    add_track(brd, u1_dp[0], u1_dp[1], X_BEND_W_1, Y_DP_COUPLED, n_dp, layer=F_CU, w_mm=W_DIFF)
    add_track(brd, X_BEND_W_1, Y_DP_COUPLED, X_P_H, Y_DP_COUPLED, n_dp, layer=F_CU, w_mm=W_DIFF)
    add_track(brd, X_P_H, Y_DP_COUPLED, X_STAGE2, Y_DP_STAGE1, n_dp, layer=F_CU, w_mm=W_DIFF)
    add_track(brd, X_STAGE2, Y_DP_STAGE1, X_FAN_END, Y_PIN6, n_dp, layer=F_CU, w_mm=W_DIFF)

    print(f"  USB_DM: H to X={X_M_H} → stage1 (X={X_STAGE2}, Y={Y_DM_STAGE1}) → pin 4 (X={X_FAN_END}, Y={Y_PIN4})")
    print(f"  USB_DP: H to X={X_P_H} → stage1 (X={X_STAGE2}, Y={Y_DP_STAGE1}) → pin 6 (X={X_FAN_END}, Y={Y_PIN6})")

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
    # With U5 at X=73 (west move), U5 west pads at X=71.862.
    # Route PAIR 2 NORTH around U5 body (Y < 28) on B.Cu coupled,
    # then descend to J1 D+/D- pad pair via F.Cu.
    Y_DPP_COUPLED = 27.50    # north of U5 body and J1 GND row
    Y_DMP_COUPLED = 27.85    # 0.35mm south of DPP (paired on B.Cu)
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
    # PAIR 2 topology v3 — B.Cu straight diagonals to B-side J1 pads:
    print(f"\n[PAIR 2] U5 ↔ J1 (pre-ESD) — B.Cu straight diagonals to B6/B7")
    # Crossing analysis: DPP→B6 (Y=29.25) keeps DPP north of DMP at both
    # ends (pre-ESD pair Y-order preserved). DMP→B7 (Y=30.75) keeps DMP
    # south. Straight diagonals don't cross (solved: crossing point
    # outside [0,1] segment range).
    # Lands at B6/B7 (B-side pads). Bridges (A6↔B6, A7↔B7) provide the
    # A-side connection for USB-C dual-orientation.
    #
    # U5 west pads: U5.1 (71.862, 34.05) D+, U5.3 (71.862, 35.95) D-
    # Pad west edge X = 71.862 - 0.6625 = 71.20
    # Via spots WEST of pad west edge (with 0.20 clearance + 0.25 via r):
    #   v3_dpp at (70.55, 34.05) — 0.65mm west of pad west edge ≥ 0.45 ✓
    #   v3_dmp at (70.10, 35.95) — 1.10mm west of pad west edge ✓
    # U5 at (73, 31): pre-ESD pads at (71.862, 30.05) D+ and (71.862, 31.95) D-
    v3_dpp = (70.50, 30.05)   # F.Cu west stub from pin 1, via west of U5 body
    v3_dmp = (70.50, 31.95)   # F.Cu west stub from pin 3, via west of U5 body
    # B.Cu landing vias just west of J1 pad column (X=79.010 west edge)
    v4_dpp = (78.50, 29.25)   # land at B6 (X=79.735, Y=29.25)
    v4_dmp = (78.50, 30.75)   # land at B7 (X=79.735, Y=30.75)

    # F.Cu west stubs from U5 pads to vias
    add_track(brd, u5_dpp[0], u5_dpp[1], v3_dpp[0], v3_dpp[1], n_dpp, layer=F_CU, w_mm=W_DIFF)
    add_track(brd, u5_dmp[0], u5_dmp[1], v3_dmp[0], v3_dmp[1], n_dmp, layer=F_CU, w_mm=W_DIFF)
    add_via(brd, v3_dpp[0], v3_dpp[1], n_dpp)
    add_via(brd, v3_dmp[0], v3_dmp[1], n_dmp)

    # B.Cu straight diagonals
    add_track(brd, v3_dpp[0], v3_dpp[1], v4_dpp[0], v4_dpp[1], n_dpp, layer=pcbnew.B_Cu, w_mm=W_DIFF)
    add_track(brd, v3_dmp[0], v3_dmp[1], v4_dmp[0], v4_dmp[1], n_dmp, layer=pcbnew.B_Cu, w_mm=W_DIFF)
    add_via(brd, v4_dpp[0], v4_dpp[1], n_dpp)
    add_via(brd, v4_dmp[0], v4_dmp[1], n_dmp)

    # F.Cu east stubs to J1 B-side pads (B6 = D+ B-side, B7 = D- B-side)
    add_track(brd, v4_dpp[0], v4_dpp[1], j1_b6[0], j1_b6[1], n_dpp, layer=F_CU, w_mm=W_DIFF)
    add_track(brd, v4_dmp[0], v4_dmp[1], j1_b7[0], j1_b7[1], n_dmp, layer=F_CU, w_mm=W_DIFF)

    print(f"  USBC_D_P_PRE: F.Cu stub + B.Cu diagonal + F.Cu stub → J1.B6")
    print(f"  USBC_D_M_PRE: parallel topology → J1.B7")

    # USB-C reversibility bridges (per master 2026-05-22 option (b)):
    # OFFSET vias OUTSIDE the 0.5mm-pitch J1 pad field, with short F.Cu
    # hops from pads into the vias. Two bridges on F.Cu+B.Cu in tandem,
    # via columns separated >1.2mm apart so vias don't conflict.
    print(f"\n[BRIDGES] USB-C dual-orientation A6↔B6 (D+) + A7↔B7 (D-) — 0.50mm vias east of pad column")
    # Bridges use standard 0.50mm vias. J1 USB-C signal pads are
    # 1.45mm wide (X) × 0.30mm tall (Y) — the WIDE direction is X due
    # to J1's 90° rotation. Pad column X-extent: 79.010..80.460.
    # Vias must clear pad east edge (X=80.460) by ≥ 0.13 + 0.25 + tolerance.
    # D+ via column X=80.85 (0.39mm east of pad east edge).
    # D- via column X=82.00 (1.15mm east of pad east edge, well clear
    # of D+ column for 0.13mm in-pair clearance).
    DV_X = 80.85    # D+ via column
    DM_X = 82.00    # D- via column

    # D+ bridge: F.Cu hop A6 → via → B.Cu vertical → via → F.Cu hop B6.
    # PAIR 2's DPP already lands at B6 — bridge stub from D+ via lands
    # on B6 same-net (USBC_D_P_PRE), no conflict.
    add_track(brd, j1_a6[0], j1_a6[1], DV_X, j1_a6[1], n_dpp, layer=F_CU, w_mm=W_DIFF)
    add_via(brd, DV_X, j1_a6[1], n_dpp)
    add_track(brd, DV_X, j1_a6[1], DV_X, j1_b6[1], n_dpp, layer=pcbnew.B_Cu, w_mm=W_DIFF)
    add_via(brd, DV_X, j1_b6[1], n_dpp)
    add_track(brd, DV_X, j1_b6[1], j1_b6[0], j1_b6[1], n_dpp, layer=F_CU, w_mm=W_DIFF)

    # D- bridge: A7 → via → B.Cu → via → B7. Bridge B.Cu vertical at
    # X=81.5 — well east of PAIR 2's landing vias at X=78.3/78.5.
    add_track(brd, j1_a7[0], j1_a7[1], DM_X, j1_a7[1], n_dmp, layer=F_CU, w_mm=W_DIFF)
    add_via(brd, DM_X, j1_a7[1], n_dmp)
    add_track(brd, DM_X, j1_a7[1], DM_X, j1_b7[1], n_dmp, layer=pcbnew.B_Cu, w_mm=W_DIFF)
    add_via(brd, DM_X, j1_b7[1], n_dmp)
    add_track(brd, DM_X, j1_b7[1], j1_b7[0], j1_b7[1], n_dmp, layer=F_CU, w_mm=W_DIFF)
    print(f"  D+ bridge: 0.50mm vias at X={DV_X}, Y=29.25/30.25")
    print(f"  D- bridge: 0.50mm vias at X={DM_X}, Y=29.75/30.75 (1.0mm X-offset from D+)")

    pcbnew.SaveBoard(PCB, brd)
    print(f"\n[done] segments written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
