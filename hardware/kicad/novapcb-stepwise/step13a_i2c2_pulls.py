#!/usr/bin/env python3
"""T3 Sub-attempt 2a: R11/R12 move + I²C2 re-route (3 nets only).

Per master 2026-05-24 T3 micro-PR cascade (1 of 5).

Moves:
- R12: (46.00, 46.50) → (41.00, 49.50) — west of MOT1+2 columns (X=43-43.5)
- R11: (52.00, 46.50) → (52.51, 49.50) — preserve X, south of corridor

Re-route:
- I²C2_SCL: MCU pad U1.46 (49, 42.67) → R12.2 (41.51, 49.5) → R12.1 (40.51, 49.5) →
  U4.4 (43.98, 47.80)
- I²C2_SDA: MCU pad U1.47 (49.5, 42.67) → R11.2 (53.01, 49.5) → R11.1 (52.01, 49.5)
  → U4.3 (43.33, 47.80)

F.Cu→B.Cu→F.Cu split (where corridor crossings happen).
Cluster walk: F.Cu over In1 GND, B.Cu over In4 GND (both continuous full-board).
"""
import os, sys, pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")

W = 0.25; VIA_DIA = 0.50; VIA_DRILL = 0.30
F = pcbnew.F_Cu; B = pcbnew.B_Cu

# Nets to reset (clear existing tracks)
NETS_TO_RESET = {"I2C2_SCL", "I2C2_SDA"}

# Component moves
RELOCATE = {
    "R11": (52.51, 49.5, 0),    # preserve X, move south
    "R12": (41.00, 49.5, 0),    # move WEST of MOT1+2 columns (X=43, 43.5)
}

# Post-move R11/R12 pad positions:
# R11 anchor (52.51, 49.5): pad1 (52.01, 49.5) +3V3, pad2 (53.01, 49.5) I²C2_SDA
# R12 anchor (41.00, 49.5): pad1 (40.51, 49.5) +3V3, pad2 (41.51, 49.5) I²C2_SCL

ROUTES = {
    # I²C2_SCL: U1.46 (49.0, 42.67) → R12.2 (41.51, 49.5) → R12.1 (40.51, 49.5) → U4.4 (43.98, 47.80)
    # F.Cu→B.Cu→F.Cu split: F.Cu stub south from MCU, via to B.Cu, B.Cu W under MCU body
    # shadow to R12.2, via to F.Cu, F.Cu through R12 internal R, then via to B.Cu, B.Cu NE
    # to U4 area, via to F.Cu, F.Cu N stub to U4.4
    "I2C2_SCL": [
        ("track", 49.000, 42.670, 49.000, 43.500, F),       # F.Cu pad stub S
        ("via",   49.000, 43.500),
        ("track", 49.000, 43.500, 41.510, 49.500, B),       # B.Cu SW long traversal to R12.2
        ("via",   41.510, 49.500),                          # via at R12.2
        # R12 internal — pad1 +3V3, pad2 I²C2_SCL. Continue from R12.1 (40.51, 49.5)
        # Wait — pad1 is +3V3, pad2 is I²C2_SCL. So I²C2 connects only to pad2.
        # The +3V3 connects to pad1 separately. So I²C2_SCL ends at pad2; from there
        # continues to U4.4 via separate F.Cu.
        ("track", 41.510, 49.500, 43.980, 49.500, F),       # F.Cu E to U4.4 column (stop short)
        # Wait — that F.Cu trace passes through R12.1 pad at (40.51) — no, 41.51 east to 43.98 is
        # NORTH/EAST of R12 anchor (41, 49.5). R12 bbox 0.5mm half: X=40.51..41.51. So my
        # F.Cu trace starts at X=41.51 (R12.2 east edge) and goes east. Clear.
        ("track", 43.980, 49.500, 43.980, 47.800, F),       # F.Cu N stub to U4.4
    ],
    # I²C2_SDA: U1.47 (49.5, 42.67) → R11.2 (53.01, 49.5) → continues to U4.3 (43.33, 47.80)
    "I2C2_SDA": [
        ("track", 49.500, 42.670, 49.500, 44.000, F),       # F.Cu pad stub S
        ("via",   49.500, 44.000),
        ("track", 49.500, 44.000, 53.010, 49.500, B),       # B.Cu SE to R11.2
        ("via",   53.010, 49.500),
        ("track", 53.010, 49.500, 53.010, 50.500, F),       # F.Cu tiny S past R11 pad
        ("via",   53.010, 50.500),
        ("track", 53.010, 50.500, 43.330, 50.500, B),       # B.Cu long W to U4.3 area
        ("via",   43.330, 50.500),
        ("track", 43.330, 50.500, 43.330, 47.800, F),       # F.Cu N stub to U4.3
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
    print("=== T3 sub-attempt 2a: R11/R12 move + I²C2 re-route ===\n")
    brd = pcbnew.LoadBoard(PCB)

    # Clear I²C2 tracks
    to_remove = [t for t in brd.GetTracks() if t.GetNetname() in NETS_TO_RESET]
    for t in to_remove: brd.Remove(t)
    print(f"  removed {len(to_remove)} I²C2 tracks/vias\n")

    # Move R11/R12
    for ref, (x, y, rot) in RELOCATE.items():
        fp = next((f for f in brd.GetFootprints() if f.GetReference()==ref), None)
        if fp:
            old = fp.GetPosition()
            fp.SetPosition(pcbnew.VECTOR2I(_mm(x), _mm(y)))
            fp.SetOrientationDegrees(rot)
            print(f"  {ref}: ({old.x/1e6:.2f},{old.y/1e6:.2f}) → ({x:.2f},{y:.2f})")

    # Add new I²C2 routes
    print()
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

    # Refill zones
    for z in brd.Zones():
        if hasattr(z, "UnFill"): z.UnFill()
    pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
    pcbnew.SaveBoard(PCB, brd)
    print("  saved\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
