#!/usr/bin/env python3
"""Move FB2 out of the CAN N-edge exit band (master-approved option A, task #45).

FB2 (+3V3 -> +3V3_IMU_PRE IMU-rail filter) sat at (49.25,25.7) directly N of
CAN1_RX (PD0, FDCAN1-peripheral-locked). Move EAST to (52.0,25.0) — verified
empty zone (X=50.5..54 Y=23..27), clears the X=47..49.5 CAN climb corridor,
keeps both legs short (between +3V3 source U1.75@52.67,29 and U13@60,26).

Legs:
- +3V3 (FB2.1): plane-via tap only (no track). Move via (48.77,25.7)->(51.52,25.0).
- +3V3_IMU_PRE (FB2.2): re-route only the FB2->node-A segment
  (49.73,25.7)-(56.02,27.0) to land on the existing X=56.02 vertical at (56.02,25.0).
  Rest of PR #78 route to U13 (56.02,24->60,24->U13) unchanged.
"""
import os, sys, pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")
F = pcbnew.F_Cu

FB2_NEW = (52.0, 25.0)
OLD_3V3_VIA = (48.77, 25.70)
NEW_3V3_VIA = (51.52, 25.0)          # new FB2.1 (+3V3) plane tap
OLD_PRE_SEG = (49.73, 25.70, 56.02, 27.00)   # remove (old FB2.2 -> node A)
NEW_PRE_SEG = (52.48, 25.0, 56.02, 25.0)     # new FB2.2 -> existing X=56.02 vertical


def mm(x): return pcbnew.FromMM(x)
def near(a, b, tol=0.05): return abs(a - b) < tol


def main():
    brd = pcbnew.LoadBoard(PCB)

    fb2 = next(f for f in brd.GetFootprints() if f.GetReference() == "FB2")
    old = fb2.GetPosition()
    print(f"FB2 ({old.x/1e6:.2f},{old.y/1e6:.2f}) -> {FB2_NEW}")
    fb2.SetPosition(pcbnew.VECTOR2I(mm(FB2_NEW[0]), mm(FB2_NEW[1])))

    # nets
    net_3v3 = net_pre = None
    for fp in brd.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname() == "+3V3" and net_3v3 is None: net_3v3 = p.GetNet()
            if p.GetNetname() == "+3V3_IMU_PRE" and net_pre is None: net_pre = p.GetNet()

    # remove old +3V3 via + old PRE segment
    rm = 0
    for t in list(brd.GetTracks()):
        if t.GetClass() == "PCB_VIA":
            p = t.GetPosition()
            if t.GetNetname() == "+3V3" and near(p.x/1e6, OLD_3V3_VIA[0]) and near(p.y/1e6, OLD_3V3_VIA[1]):
                brd.Remove(t); rm += 1
        else:
            s, e = t.GetStart(), t.GetEnd()
            if t.GetNetname() == "+3V3_IMU_PRE":
                a = (s.x/1e6, s.y/1e6, e.x/1e6, e.y/1e6)
                b = (e.x/1e6, e.y/1e6, s.x/1e6, s.y/1e6)
                if all(near(a[i], OLD_PRE_SEG[i]) for i in range(4)) or \
                   all(near(b[i], OLD_PRE_SEG[i]) for i in range(4)):
                    brd.Remove(t); rm += 1
    print(f"  removed {rm} old items (+3V3 via + PRE seg)")

    # new +3V3 plane tap via at new FB2.1
    v = pcbnew.PCB_VIA(brd)
    v.SetPosition(pcbnew.VECTOR2I(mm(NEW_3V3_VIA[0]), mm(NEW_3V3_VIA[1])))
    v.SetWidth(mm(0.50)); v.SetDrill(mm(0.30)); v.SetNet(net_3v3); brd.Add(v)
    # new PRE leg
    t = pcbnew.PCB_TRACK(brd)
    t.SetStart(pcbnew.VECTOR2I(mm(NEW_PRE_SEG[0]), mm(NEW_PRE_SEG[1])))
    t.SetEnd(pcbnew.VECTOR2I(mm(NEW_PRE_SEG[2]), mm(NEW_PRE_SEG[3])))
    t.SetWidth(mm(0.25)); t.SetLayer(F); t.SetNet(net_pre); brd.Add(t)
    print(f"  added new +3V3 via {NEW_3V3_VIA} + PRE seg {NEW_PRE_SEG}")

    for z in brd.Zones():
        if hasattr(z, "UnFill"): z.UnFill()
    pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
    pcbnew.SaveBoard(PCB, brd)
    print("  saved")
    return 0


if __name__ == "__main__":
    sys.exit(main())
