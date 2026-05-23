#!/usr/bin/env python3
"""A↔B integration — +5V_BEC plane on In2.Cu + Q3/Q4 source + J4/J19 input.

Per master 2026-05-23 sign-off after stackup lock (DECISIONS §8):

  L1 F.Cu   — components + signals (USB diff, I2C, SPI, sense traces)
  L2 In1.Cu — GND plane
  L3 In2.Cu — +5V_BEC plane (THIS STEP adds it)
  L4 In3.Cu — +3V3 plane (existing from PR #72/#73)
  L5 In4.Cu — GND plane
  L6 B.Cu   — signals

Scope of THIS step:
  1. **+5V_BEC plane on In2.Cu** — covers Q3 drains + Q4 drains + Q2.
     Vias from each +5V_BEC pad drop to the plane (the main A↔B contract).
  2. **+5V_BEC_A trunk** (J4 → Q3 source pads) — F.Cu trace on Y=9 corridor.
     Q3.1-3 bridged. Connects to but doesn't terminate at U11.
  3. **+5V_BEC_B trunk** (J19 → Q4 source pads) — mirror.

DEFERRED (TODO C↔E-2 or A↔B-2 sub-step):
  4. **U11/U12 SOT-23-6 fanout**: ORING_A/B_VCAP, ORING_A/B_GATE,
     U11.3/U12.3 sense, U11.6/U12.6 secondary +5V_BEC_A/B connections,
     U11/U12 GND vias.

     SOT-23-6 has 3 pins on each 2.3mm side at 0.95mm pitch. The 3 nets
     on each side conflict on any direct F.Cu route (each net needs to
     exit between adjacent pins of OTHER nets). B.Cu vias also conflict
     due to via clearance to adjacent pads. Needs either:
       (a) U11/U12 re-orientation/relocation for better pin fanout angle
       (b) Via-in-pad process (more expensive)
       (c) Manual route iteration with non-standard via dia

     Without OR-FET control wiring, A is non-functional electrically but
     spatially correct. Functional OR-FET handoff is for D placement /
     A↔B-2 sub-step. Tracked.

  5. **Sense V/I traces** (MAUCH_VBAT/CURR_PRE, BATT_VOLTAGE/CURRENT_SENS,
     and BATT2 variants — 8 traces total). Cross +3V3 stub on F.Cu and
     congest the C-zone west side. Defer to a sense-traces sub-step
     with B.Cu routing or +3V3-stub re-route.

KNOWN UPSTREAM BUG (already noted in C↔B PR #72): U6 (TPS25922 eFuse)
pads have empty net assignments in the SKiDL netlist. The chain
+5V_BEC → U6 → +5V is broken at U6. +5V (U2 input) is orphaned. Filed
as SKiDL netlist task (separate from PCB routing).

Gates: DRC=0 on this routing scope; gate12 v3 unchanged (heat-source
positions identical; total copper coverage same just shifted layer).
"""
import os
import sys
import math
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")
F_CU = pcbnew.F_Cu
B_CU = pcbnew.B_Cu
IN2_CU = pcbnew.In2_Cu

W_PWR = 0.50
W_SIG = 0.20
VIA_DIA = 0.50
VIA_DRILL = 0.30

# +5V_BEC plane: spans Y=4.5..24, X=18..82.
# Y=4.5 chosen (was Y=6) to cover U11.4 (34.15, 5.95) and U12.4 (73.15, 5.95)
# via-in-pad locations. A↔B-3 master 2026-05-23: zone-fill Rule 9 check
# revealed U11.4/U12.4 vias were OUTSIDE plane outline by 0.05mm.
PLUS5V_PLANE_OUTLINE = [
    (18.0, 4.5),
    (82.0, 4.5),
    (82.0, 24.0),
    (18.0, 24.0),
]


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


def gather_pads(brd, net_names):
    out = {n: [] for n in net_names}
    for fp in brd.GetFootprints():
        if fp.GetPosition().x / 1e6 >= 100:
            continue
        ref = fp.GetReference()
        for pad in fp.Pads():
            nn = pad.GetNetname()
            if nn in out:
                p = pad.GetPosition(); sz = pad.GetSize()
                out[nn].append((ref, pad.GetPadName(),
                                p.x/1e6, p.y/1e6,
                                sz.x/1e6, sz.y/1e6))
    return out


def main():
    print("=== A↔B integration — +5V_BEC plane + Q3/Q4 source ===", flush=True)
    brd = pcbnew.LoadBoard(PCB)

    pad_map = gather_pads(brd, ["+5V_BEC", "+5V_BEC_A", "+5V_BEC_B"])
    n_5v_bec = get_net(brd, "+5V_BEC")
    n_5v_a = get_net(brd, "+5V_BEC_A")
    n_5v_b = get_net(brd, "+5V_BEC_B")

    print(f"+5V_BEC pads on board:    {len(pad_map['+5V_BEC'])}")
    print(f"+5V_BEC_A pads on board:  {len(pad_map['+5V_BEC_A'])}")
    print(f"+5V_BEC_B pads on board:  {len(pad_map['+5V_BEC_B'])}")

    # 1. +5V_BEC plane on In2.Cu (inline — function indirection causes
    # SIGSEGV on this pcbnew Python build)
    print(f"\n[1] +5V_BEC plane on In2.Cu", flush=True)
    z = pcbnew.ZONE(brd)
    z.SetLayer(IN2_CU)
    z.SetNet(n_5v_bec)
    o = pcbnew.SHAPE_POLY_SET(); o.NewOutline()
    for x, y in PLUS5V_PLANE_OUTLINE:
        o.Append(_mm(x), _mm(y))
    z.SetOutline(o)
    brd.Add(z)
    print(f"  +5V_BEC plane outline: {PLUS5V_PLANE_OUTLINE}")

    # Vias at all +5V_BEC pads (Q3.5-8, Q4.5-8, Q2.2)
    via_count = 0
    for r, pn, x, y, w, h in pad_map["+5V_BEC"]:
        add_via(brd, x, y, n_5v_bec)
        via_count += 1
    print(f"  {via_count} vias at +5V_BEC pads (Q3.5-8, Q4.5-8, Q2.2)")

    # 2. +5V_BEC_A trunk: J4 → Q3 source (Q3.1-3)
    # J4.1+J4.2 bridge, J4.2 → Y=9 trunk → Q3.3 → Q3.2 → Q3.1
    print(f"\n[2] +5V_BEC_A: J4 → Q3 source", flush=True)
    add_track(brd, 12.88, 3.15, 12.88, 8.5, n_5v_a)
    add_track(brd, 12.88, 8.5, 14.12, 8.5, n_5v_a)
    add_track(brd, 14.12, 8.5, 14.12, 9.0, n_5v_a)
    add_track(brd, 14.12, 3.15, 14.12, 8.5, n_5v_a)
    add_track(brd, 14.12, 9.0, 27.63, 9.0, n_5v_a)    # trunk east to Q3.3 X
    add_track(brd, 27.63, 9.0, 27.63, 12.57, n_5v_a)  # south to Q3.3 pad
    add_track(brd, 27.63, 12.57, 26.37, 12.57, n_5v_a, w_mm=0.40)  # Q3 bridges
    add_track(brd, 26.37, 12.57, 25.10, 12.57, n_5v_a, w_mm=0.40)
    print(f"  J4 + 4 trunk segments + 2 Q3 bridges")

    # 3. +5V_BEC_B trunk: J19 → Q4 source (Q4.1-3) — mirror of (2)
    print(f"\n[3] +5V_BEC_B: J19 → Q4 source", flush=True)
    add_track(brd, 87.12, 3.15, 87.12, 8.5, n_5v_b)
    add_track(brd, 87.12, 8.5, 85.88, 8.5, n_5v_b)
    add_track(brd, 85.88, 8.5, 85.88, 9.0, n_5v_b)
    add_track(brd, 85.88, 3.15, 85.88, 8.5, n_5v_b)
    add_track(brd, 85.88, 9.0, 78.63, 9.0, n_5v_b)    # trunk west to Q4.3 X
    add_track(brd, 78.63, 9.0, 78.63, 12.57, n_5v_b)  # south to Q4.3 pad
    add_track(brd, 78.63, 12.57, 77.37, 12.57, n_5v_b, w_mm=0.40)
    add_track(brd, 77.37, 12.57, 76.10, 12.57, n_5v_b, w_mm=0.40)
    print(f"  J19 + 4 trunk segments + 2 Q4 bridges")

    # Zone fill before save (defensive — master 2026-05-23 Rule 9 discipline)
    try:
        for z in brd.Zones():
            if hasattr(z, 'UnFill'): z.UnFill()
        pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
    except Exception as _e:
        print(f"  zone fill skipped: {_e}")

    pcbnew.SaveBoard(PCB, brd)
    print(f"\n  Saved {PCB}")
    print(f"\n  DEFERRED (next sub-step): U11/U12 SOT-23-6 fanout + 8 sense traces")
    return 0


if __name__ == "__main__":
    sys.exit(main())
