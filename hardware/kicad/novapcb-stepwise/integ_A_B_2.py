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

    # 3. +5V_BEC plane via via F.Cu stub east of U11.4 (via-on-pad fails
    # clearance to U11.5 ORING_A_GATE at 0.95mm pitch — 0.035mm short)
    print("[3] +5V_BEC: U11.4 → F.Cu stub → via → In2.Cu plane", flush=True)
    # Via at (34.7, 5.95) — gap 0.82mm to C74.1 via avoids hole-clearance fail
    add_track(brd, u11["4"][0], u11["4"][1], 34.7, 5.95, n_5v, layer=F_CU)
    add_via(brd, 34.7, 5.95, n_5v)

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

    # 6. +5V_BEC plane via at U12.4 — F.Cu east stub then via (mirror)
    print("[6] +5V_BEC: U12.4 → F.Cu stub → via → In2.Cu plane", flush=True)
    # Via at (75, 5.95) — east enough to clear GATE B.Cu diagonal at (73.7, 5.62)
    add_track(brd, u12["4"][0], u12["4"][1], 75.0, 5.95, n_5v, layer=F_CU)
    add_via(brd, 75.0, 5.95, n_5v)

    # Note: +5V_BEC_A (U11.3 + U11.6) and +5V_BEC_B (U12.3 + U12.6)
    # are SENSE feedback for the LM74700 controller. PR #74 routed
    # Q3 source bridges on +5V_BEC_A net, U11.3 was connected via Y=9
    # trunk. Verify connectivity in Rule 9 step. If not, add B.Cu via
    # for these too.

    pcbnew.SaveBoard(PCB, brd)
    print(f"\n  Saved {PCB}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
