#!/usr/bin/env python3
"""T3 Sub-attempt 2b: IMU1_CS + IMU3_CS to B.Cu (south-perimeter wraparound).

Per master 2026-05-24 (A) sign-off after T3 2b survey PR #97.

Scope: 2 nets only (IMU2_GYR_CS already on B.Cu per PR #77).

Path pattern per (A) south-perimeter:
  F.Cu MCU pin → via → B.Cu south past D-zone → B.Cu east at Y=66
  (south of D-zone south Y=63) → B.Cu north entering D-zone → via → F.Cu
  stub to destination pad.

Avoids dense B.Cu envelope X=35..80 Y=27..60 by routing south of D-zone.
"""
import os, sys, pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")

W = 0.25; VIA_DIA = 0.50; VIA_DRILL = 0.30
F = pcbnew.F_Cu; B = pcbnew.B_Cu

NETS_TO_RESET = {"IMU1_CS", "IMU3_CS"}

ROUTES = {
    # IMU1_CS: PC15 pad 9 W (37.33, 33.00) → U3.10 (61.46, 56.75)
    # South-perimeter wraparound
    "IMU1_CS": [
        ("track", 37.330, 33.000, 36.000, 33.000, F),       # F.Cu W stub
        ("via",   36.000, 33.000),
        ("track", 36.000, 33.000, 36.000, 66.000, B),       # B.Cu S past D-zone
        ("track", 36.000, 66.000, 61.460, 66.000, B),       # B.Cu E at Y=66 (S of D-zone)
        ("track", 61.460, 66.000, 61.460, 56.750, B),       # B.Cu N entering D-zone to U3.10 Y
        ("via",   61.460, 56.750),                          # via at U3.10 pad
    ],
    # IMU3_CS: PE2 pad 1 W (37.33, 29.00) → U9.12 (77.50, 57.92)
    # Same south-perimeter pattern, west column further out for via separation
    "IMU3_CS": [
        ("track", 37.330, 29.000, 35.000, 29.000, F),       # F.Cu W stub
        ("via",   35.000, 29.000),
        ("track", 35.000, 29.000, 35.000, 66.500, B),       # B.Cu S past D-zone (lane south of IMU1_CS)
        ("track", 35.000, 66.500, 77.500, 66.500, B),       # B.Cu long E at Y=66.5
        ("track", 77.500, 66.500, 77.500, 57.920, B),       # B.Cu N entering D-zone to U9.12
        ("via",   77.500, 57.920),                          # via at U9.12 pad
    ],
}


def _mm(x): return pcbnew.FromMM(x)


def get_net(brd, name):
    for fp in list(brd.GetFootprints()):
        for pad in fp.Pads():
            if pad.GetNetname() == name:
                return pad.GetNet()
    return None


def add_track(brd, x1, y1, x2, y2, layer, net):
    t = pcbnew.PCB_TRACK(brd)
    t.SetStart(pcbnew.VECTOR2I(_mm(x1), _mm(y1)))
    t.SetEnd(pcbnew.VECTOR2I(_mm(x2), _mm(y2)))
    t.SetWidth(_mm(W)); t.SetLayer(layer); t.SetNet(net)
    brd.Add(t)


def add_via(brd, x, y, net):
    v = pcbnew.PCB_VIA(brd)
    v.SetPosition(pcbnew.VECTOR2I(_mm(x), _mm(y)))
    v.SetWidth(_mm(VIA_DIA)); v.SetDrill(_mm(VIA_DRILL)); v.SetNet(net)
    brd.Add(v)


def main():
    print("=== T3 2b: IMU1_CS + IMU3_CS B.Cu south-perimeter ===\n")
    brd = pcbnew.LoadBoard(PCB)

    to_remove = [t for t in brd.GetTracks() if t.GetNetname() in NETS_TO_RESET]
    for t in to_remove: brd.Remove(t)
    print(f"  removed {len(to_remove)} existing tracks/vias on {len(NETS_TO_RESET)} nets\n")

    n_tr = n_vi = 0
    for name, segs in ROUTES.items():
        net = get_net(brd, name)
        if net is None:
            print(f"  !!! {name}: net not found"); continue
        f_c = b_c = via_c = 0
        for seg in segs:
            if seg[0] == "track":
                _, x1, y1, x2, y2, layer = seg
                add_track(brd, x1, y1, x2, y2, layer, net)
                if layer == F: f_c += 1
                else: b_c += 1
                n_tr += 1
            else:
                _, x, y = seg
                add_via(brd, x, y, net)
                via_c += 1
                n_vi += 1
        print(f"  {name}: {f_c}F+{b_c}B trk + {via_c}via")

    print(f"\n  Total: {n_tr} tracks + {n_vi} vias\n")

    for z in brd.Zones():
        if hasattr(z, "UnFill"): z.UnFill()
    pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
    pcbnew.SaveBoard(PCB, brd)
    print("  saved\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
