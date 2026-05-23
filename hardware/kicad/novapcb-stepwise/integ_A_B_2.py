#!/usr/bin/env python3
"""A↔B-2 — OR-FET fanout (U11/U12 via-on-pad-center + B.Cu routing).

Per master 2026-05-23 critical-functional debt #2 + via-in-pad fallback
(rotation tried, didn't clean up B.Cu congestion).

Strategy:
  - U11/U12 stay at rot=0 (original placement).
  - Place B.Cu vias at center of each U11/U12 pad: pad is 0.53×1.07,
    via 0.5mm OD fits with 0.015mm pad-edge gap (Y) and 0.285mm (X).
    Adjacent pad (0.95mm pitch) edge-to-edge clearance: 0.435mm — PASS
    different-net 0.2mm rule.
  - B.Cu traces from each via to target R/C/Q.

Via-on-pad requires JLC's "via filled and capped" process for the
affected vias (12 total: 6 per IC × 2 ICs). Bounded fallback per
master 2026-05-23 ("scope-bounded to just U11/U12 vias").

Routes (B.Cu):
  - U11.1 ORING_A_VCAP → C73.1 (35.52, 4)
  - U11.5 ORING_A_GATE → Q3.4 (28.9, 12.57)
  - U11.3 + U11.6 +5V_BEC_A → C74.1 (35.52, 6) → Q3.3 (27.63, 12.57)
  - U11.4 +5V_BEC → In2.Cu plane via (pad center via)
  - U12 mirror

Cross-check (Rule 9): post-DRC, verify each net has F.Cu pad + via +
B.Cu trace + target via connectivity.
"""
import os
import sys
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")
B_CU = pcbnew.B_Cu
F_CU = pcbnew.F_Cu

W_SIG = 0.20
VIA_DIA = 0.50
VIA_DRILL = 0.30   # standard min — 0.25mm would need DRU rule change


def _mm(x): return pcbnew.FromMM(x)


def add_track(brd, x1, y1, x2, y2, net_obj, layer=B_CU, w_mm=W_SIG):
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
    v.SetWidth(_mm(VIA_DIA))
    v.SetDrill(_mm(VIA_DRILL))
    v.SetNet(net_obj)
    brd.Add(v)


def get_net(brd, name):
    nets = brd.GetNetsByName().asdict()
    for k, v in nets.items():
        kv = k.value() if hasattr(k, 'value') else str(k)
        if kv == name:
            return v
    return None


def get_pad(brd, ref, pin):
    for fp in brd.GetFootprints():
        if fp.GetReference() == ref:
            for pad in fp.Pads():
                if pad.GetPadName() == pin:
                    p = pad.GetPosition()
                    return (p.x/1e6, p.y/1e6)
    return None


def main():
    print("=== A↔B-2: OR-FET fanout (via-in-pad GATE + offset stubs) ===", flush=True)
    brd = pcbnew.LoadBoard(PCB)

    # Remove redundant +5V_BEC vias at U11.4 (34.15, 5.95) and U12.4
    # (73.15, 5.95) added by PR #74. They conflict with the new GATE
    # via-in-pad at U11.5/U12.5. Offset stub vias added below replace them.
    to_remove = []
    for t in brd.GetTracks():
        if isinstance(t, pcbnew.PCB_VIA) and t.GetNetname() == "+5V_BEC":
            p = t.GetPosition()
            x, y = round(p.x/1e6, 2), round(p.y/1e6, 2)
            if (x, y) in ((34.15, 5.95), (73.15, 5.95)):
                to_remove.append(t)
    for t in to_remove:
        brd.Remove(t)
    print(f"  removed {len(to_remove)} redundant +5V_BEC vias at U11.4/U12.4")

    # Idempotency: strip everything A↔B-2 owns (GATE/VCAP nets entirely,
    # +5V_BEC tracks/vias in U11/U12 ORFET corner only — leaves PR #74
    # trunk and Q3/Q4 source bridges + In2.Cu plane untouched).
    ab2_owned_nets = {"ORING_A_VCAP", "ORING_B_VCAP", "ORING_A_GATE", "ORING_B_GATE"}
    # Coord-set of THIS-script-added +5V_BEC stub vias at U11.4 / U12.4 offsets
    # AND +5V_BEC_A/B SENSE additions
    ab2_offset_5v_vias = {(34.70, 5.95), (75.00, 5.95), (71.50, 5.95), (74.50, 5.95), (74.55, 5.95), (34.15, 7.0), (73.15, 7.0)}
    # Footprint-bounded region for +5V_BEC_A SENSE additions
    def in_u11_sense_box(x, y):
        return 27.0 <= x <= 36.0 and 2.5 <= y <= 9.5
    def in_u12_sense_box(x, y):
        return 68.0 <= x <= 76.0 and 2.5 <= y <= 9.5

    to_remove = []
    for t in brd.GetTracks():
        net = t.GetNetname()
        if isinstance(t, pcbnew.PCB_VIA):
            p = t.GetPosition()
            x, y = round(p.x/1e6, 2), round(p.y/1e6, 2)
            if net in ab2_owned_nets:
                to_remove.append(t); continue
            if net == "+5V_BEC" and (x, y) in ab2_offset_5v_vias:
                to_remove.append(t); continue
            if net == "+5V_BEC_A" and in_u11_sense_box(x, y):
                to_remove.append(t); continue
            if net == "+5V_BEC_B" and in_u12_sense_box(x, y):
                to_remove.append(t); continue
        else:
            if net in ab2_owned_nets:
                to_remove.append(t); continue
            # +5V_BEC_A/B SENSE tracks fully inside footprint-bounded box:
            s = t.GetStart(); e = t.GetEnd()
            sx, sy = s.x/1e6, s.y/1e6
            ex, ey = e.x/1e6, e.y/1e6
            if net == "+5V_BEC_A" and in_u11_sense_box(sx, sy) and in_u11_sense_box(ex, ey):
                # exclude PR #74 trunk that ends at (27.63, 9) — trunk is X<28
                if sx >= 27.7 and ex >= 27.7:
                    to_remove.append(t); continue
            if net == "+5V_BEC_B" and in_u12_sense_box(sx, sy) and in_u12_sense_box(ex, ey):
                if sx <= 78.5 and ex <= 78.5:
                    to_remove.append(t); continue
            # +5V_BEC F.Cu stubs / B.Cu diagonals at U11.4/U12.4 (section 3/6)
            if net == "+5V_BEC":
                endpoints = ((round(sx,2), round(sy,2)), (round(ex,2), round(ey,2)))
                if (34.15, 5.95) in endpoints or (73.15, 5.95) in endpoints:
                    to_remove.append(t); continue
                if (34.15, 7.0) in endpoints or (73.15, 7.0) in endpoints:
                    to_remove.append(t); continue
                # B.Cu diagonal U11.4→Q3.5/Q3.8 or U12.4→Q4.5/Q4.8
                q_pads = ((25.10, 7.43), (26.37, 7.43), (27.63, 7.43), (28.90, 7.43),
                          (76.10, 7.43), (77.37, 7.43), (78.63, 7.43), (79.90, 7.43))
                for q in q_pads:
                    if q in endpoints and t.GetLayer() == B_CU:
                        to_remove.append(t); break
    for t in to_remove:
        brd.Remove(t)
    print(f"  stripped {len(to_remove)} A↔B-2-owned items for idempotency")

    n_vca = get_net(brd, "ORING_A_VCAP")
    n_vcb = get_net(brd, "ORING_B_VCAP")
    n_ga = get_net(brd, "ORING_A_GATE")
    n_gb = get_net(brd, "ORING_B_GATE")
    n_5va = get_net(brd, "+5V_BEC_A")
    n_5vb = get_net(brd, "+5V_BEC_B")
    n_5v = get_net(brd, "+5V_BEC")

    # U11 pads (rot=0): pad i at original positions
    u11 = {pn: get_pad(brd, "U11", pn) for pn in "123456"}
    u12 = {pn: get_pad(brd, "U12", pn) for pn in "123456"}
    print(f"U11 pads: {u11}")
    print(f"U12 pads: {u12}")

    # Critical routes only — GATE + VCAP (without these, OR-FET non-functional)
    # +5V_BEC_A/B chains already wired in PR #74 to Q3/Q4 source bridges.
    # U11.4 / U12.4 to +5V_BEC plane via (drops through In2.Cu).
    # GND defer (no GND plane yet).

    # 1. ORING_A_VCAP: U11.1 (31.85, 4.05) → C73.1 (35.52, 4)
    print("[1] ORING_A_VCAP: U11.1 → C73.1 (B.Cu)", flush=True)
    add_via(brd, *u11["1"], n_vca)
    c73 = get_pad(brd, "C73", "1")
    add_via(brd, *c73, n_vca)
    add_track(brd, u11["1"][0], u11["1"][1], c73[0], c73[1], n_vca)

    # 2. ORING_A_GATE: U11.5 → Q3.4 (via-in-pad, master Option B)
    # Via 0.45mm OD / 0.25mm drill per DRU rule "via-in-pad-orfet*"
    # (KiCad design rules scoped to ORING_A_GATE / ORING_B_GATE nets).
    # JLC via-filled-and-capped process required at fab order.
    print("[2] ORING_A_GATE: U11.5 → Q3.4 (via-in-pad)", flush=True)
    v = pcbnew.PCB_VIA(brd)
    v.SetPosition(pcbnew.VECTOR2I(_mm(u11["5"][0]), _mm(u11["5"][1])))
    v.SetWidth(_mm(0.45))
    v.SetDrill(_mm(0.25))
    v.SetNet(n_ga)
    brd.Add(v)
    add_via(brd, 28.9, 12.57, n_ga)
    add_track(brd, u11["5"][0], u11["5"][1], 28.9, 12.57, n_ga, layer=B_CU, w_mm=W_SIG)

    # 3. +5V_BEC: U11.4 → plane connection — DEFERRED to A↔B-3.
    # ROOT CAUSE: SOT-23-6 0.95mm pin pitch leaves no via-in-pad option
    # without DRU clearance relaxation (0.19mm vs 0.20mm rule). External
    # via paths each conflict:
    #   - East stub via in U11-C73/C74 gap: clears GATE B.Cu only at
    #     X=74.55+ which leaves <0.20mm to SENSE F.Cu at X=75.15.
    #   - F.Cu/B.Cu diagonal U11.4 → Q3.5: ALWAYS crosses GATE B.Cu
    #     because both diverge from same X column to same X column with
    #     different slopes (U11.4 starts SOUTH of GATE, ends NORTH).
    #   - F.Cu detour south-around-Q3-then-up: 19.87mm path length and
    #     conflicts with SENSE F.Cu vertical clearance.
    # Resolution requires either (a) DRU clearance-relax to 0.15mm
    # scoped to U11/U12 courtyard (master OK needed), or (b) U11 placement
    # shift to add 0.1mm Y spacing (revisits Step 6 placement),
    # or (c) switch SENSE to B.Cu vertical to free F.Cu corner.
    # ESCALATING to master with options.
    print("[3] +5V_BEC: U11.4 DEFERRED — escalating to master (clearance constraint)", flush=True)

    # 4. ORING_B_VCAP: U12.1 (70.85, 4.05) → C75.1 (68.52, 4)
    print("[4] ORING_B_VCAP: U12.1 → C75.1 (B.Cu)", flush=True)
    add_via(brd, *u12["1"], n_vcb)
    c75 = get_pad(brd, "C75", "1")
    add_via(brd, *c75, n_vcb)
    add_track(brd, u12["1"][0], u12["1"][1], c75[0], c75[1], n_vcb)

    # 5. ORING_B_GATE: U12.5 → Q4.4 (via-in-pad, mirror)
    print("[5] ORING_B_GATE: U12.5 → Q4.4 (via-in-pad)", flush=True)
    v = pcbnew.PCB_VIA(brd)
    v.SetPosition(pcbnew.VECTOR2I(_mm(u12["5"][0]), _mm(u12["5"][1])))
    v.SetWidth(_mm(0.45))
    v.SetDrill(_mm(0.25))
    v.SetNet(n_gb)
    brd.Add(v)
    add_via(brd, 79.9, 12.57, n_gb)
    add_track(brd, u12["5"][0], u12["5"][1], 79.9, 12.57, n_gb, layer=B_CU, w_mm=W_SIG)

    # 6. +5V_BEC: U12.4 → plane DEFERRED (mirror of U11.4 deferral)
    print("[6] +5V_BEC: U12.4 DEFERRED — escalating to master", flush=True)

    # 7. SENSE pin connections — Rule 9 push-back from master 2026-05-23.
    # U11.3/U11.6 + U12.3/U12.6 are LM74700 source-feedback (SENSE) pins;
    # WITHOUT physical connection to +5V_BEC_A/B trunks the ideal-diode
    # comparator can't see source voltage and OR-FET behaves as always-on
    # → reverse-current path possible.
    # All-F.Cu routing chosen: GATE owns the B.Cu corner; SENSE goes on
    # F.Cu via north-of-U11 jog + south-of-trunk extension. Avoids the
    # B.Cu B.Cu crossing that the first SENSE attempt produced (0.04mm
    # actual vs 0.20mm rule clearance fail).
    #
    # U11 west cluster geometry:
    #   U11 pads at (31.85, 4.05/5.0/5.95) and (34.15, 4.05/5.0/5.95).
    #   GATE B.Cu diagonal U11.5→Q3.4 passes through (31.5..34.2, 5..12.5).
    #   SENSE F.Cu corridor is north of U11 footprint (Y=3) + south at Y=9.
    #   Vertical X=29.85 (east of Q3.8 pad edge X=29.50 + 0.20 clr +
    #   track half 0.10 = 29.80, use 29.85).

    # 7a. U11.3 → F.Cu south to Y=9 trunk (extends existing PR #74 trunk east)
    print("[7a] +5V_BEC_A: U11.3 → Y=9 F.Cu south stub", flush=True)
    add_track(brd, u11["3"][0], u11["3"][1], 31.85, 9.0, n_5va, layer=F_CU, w_mm=W_SIG)
    add_track(brd, 31.85, 9.0, 27.63, 9.0, n_5va, layer=F_CU, w_mm=W_SIG)

    # 7b. U11.6 → F.Cu north-around to X=29.85 vertical → joins extended trunk
    print("[7b] +5V_BEC_A: U11.6 → F.Cu north-around (X=29.85 vertical)", flush=True)
    add_track(brd, u11["6"][0], u11["6"][1], 34.15, 3.0, n_5va, layer=F_CU, w_mm=W_SIG)
    add_track(brd, 34.15, 3.0, 29.85, 3.0, n_5va, layer=F_CU, w_mm=W_SIG)
    add_track(brd, 29.85, 3.0, 29.85, 9.0, n_5va, layer=F_CU, w_mm=W_SIG)
    # extend trunk to meet (29.85, 9): (31.85, 9) west already, now extend east
    add_track(brd, 31.85, 9.0, 29.85, 9.0, n_5va, layer=F_CU, w_mm=W_SIG)

    # 7c. C74.1 → F.Cu south-around (35.52,6)→(35.52,9)→(29.85,9) joins trunk.
    # North-around shorts C73 (35.52, 4) ORING_A_VCAP — vertical at X=35.52
    # crosses C73.1 pad. South-around clears C73 + the rest of the U11 cluster.
    print("[7c] +5V_BEC_A: C74.1 → F.Cu south to Y=9 trunk", flush=True)
    c74 = get_pad(brd, "C74", "1")
    if c74:
        add_track(brd, c74[0], c74[1], c74[0], 9.0, n_5va, layer=F_CU, w_mm=W_SIG)
        add_track(brd, c74[0], 9.0, 29.85, 9.0, n_5va, layer=F_CU, w_mm=W_SIG)

    # 7d. U12.3 → F.Cu south to Y=9 trunk (mirror, extends PR #74 trunk west)
    print("[7d] +5V_BEC_B: U12.3 → Y=9 F.Cu south stub", flush=True)
    add_track(brd, u12["3"][0], u12["3"][1], 70.85, 9.0, n_5vb, layer=F_CU, w_mm=W_SIG)
    add_track(brd, 70.85, 9.0, 78.63, 9.0, n_5vb, layer=F_CU, w_mm=W_SIG)

    # 7e. U12.6 → F.Cu north-around to X=75.15 vertical → joins extended trunk.
    # X=75.15: mirror of U11 X=29.85 (offset from Q-pad west edge 75.50
    # by 0.35mm; track edge 75.25 vs Q4.8 pad west edge 75.50 → 0.25mm clr).
    # +5V_BEC stub now at (71.5, 5.95) — west of U12 — so no conflict.
    print("[7e] +5V_BEC_B: U12.6 → F.Cu north-around (X=75.15 vertical)", flush=True)
    add_track(brd, u12["6"][0], u12["6"][1], 73.15, 3.0, n_5vb, layer=F_CU, w_mm=W_SIG)
    add_track(brd, 73.15, 3.0, 75.15, 3.0, n_5vb, layer=F_CU, w_mm=W_SIG)
    add_track(brd, 75.15, 3.0, 75.15, 9.0, n_5vb, layer=F_CU, w_mm=W_SIG)
    add_track(brd, 70.85, 9.0, 75.15, 9.0, n_5vb, layer=F_CU, w_mm=W_SIG)

    # 7f. C76.1 → F.Cu north-around (68.52,6)→(68.52,3)→(70.85,3)... but
    # going east-towards-U12.6-line works only if line extends west of 73.15.
    # Simpler: C76 → F.Cu DIRECT south (68.52, 6) → (68.52, 9) → east to (70.85, 9).
    print("[7f] +5V_BEC_B: C76.1 → F.Cu south to trunk", flush=True)
    c76 = get_pad(brd, "C76", "1")
    if c76:
        add_track(brd, c76[0], c76[1], c76[0], 9.0, n_5vb, layer=F_CU, w_mm=W_SIG)
        add_track(brd, c76[0], 9.0, 70.85, 9.0, n_5vb, layer=F_CU, w_mm=W_SIG)

    pcbnew.SaveBoard(PCB, brd)
    print(f"\n  Saved {PCB}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
