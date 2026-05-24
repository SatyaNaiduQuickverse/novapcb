#!/usr/bin/env python3
"""route_can — CAN bus subsystem routing (CAN1_RX/TX/SILENT + CANH/CANL).

Per master 2026-05-24 dispatch. Rule-18+19 survey done — Y=20 horizontal
lane is clear in X=48..88 (only C83/U14 at X≥88 area which is destination).

Topology:
  MCU side (3 nets):
    CAN1_RX  PD0 pad 81 (48.5, 27.32) → U14.4 (94.98, 23.43)
    CAN1_TX  PD1 pad 82 (48.0, 27.32) → U14.1 (93.02, 23.43)
    GPIO_CAN1_SILENT PD3 pad 84 (47.0, 27.32) → U14.8 (93.02, 20.57)

  CAN bus (CANH/CANL):
    CANH: U14.7 (93.68, 20.57) → R45.1 (99.50, 21.82) → U15.1 (97, 27.95) → J20.2 (96.38, 9.15)
    CANL: U14.6 (94.33, 20.57) → R46.2 (99.50, 24.18) → U15.2 (97, 26.05) → J20.3 (97.62, 9.15)

All F.Cu. Width 0.25mm (default).
"""
import os, sys, pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")

W = 0.25
F = pcbnew.F_Cu

NETS_TO_RESET = {"CAN1_RX", "CAN1_TX", "GPIO_CAN1_SILENT", "CANH_NET", "CANL_NET"}

ROUTES = {
    # MCU N pads → U14 east side (north-then-east-then-south to land)
    # Use Y=19 horizontal lane (clear of C83/C84 + U14 north pads)
    "CAN1_TX": [
        ("track", 48.000, 27.320, 48.000, 19.000, F),   # N stub from MCU pad 82
        ("track", 48.000, 19.000, 93.020, 19.000, F),   # E horizontal lane
        ("track", 93.020, 19.000, 93.020, 23.430, F),   # S to U14.1
    ],
    "CAN1_RX": [
        ("track", 48.500, 27.320, 48.500, 18.500, F),   # N stub
        ("track", 48.500, 18.500, 94.980, 18.500, F),   # E (separate lane from TX)
        ("track", 94.980, 18.500, 94.980, 23.430, F),   # S to U14.4
    ],
    "GPIO_CAN1_SILENT": [
        ("track", 47.000, 27.320, 47.000, 19.500, F),   # N stub
        ("track", 47.000, 19.500, 93.020, 19.500, F),   # E
        ("track", 93.020, 19.500, 93.020, 20.570, F),   # S to U14.8
    ],
    # CANH: U14.7 (93.68, 20.57) → R45.1 (99.5, 21.82) → U15.1 (97, 27.95) → J20.2 (96.38, 9.15)
    "CANH_NET": [
        ("track", 93.680, 20.570, 99.500, 20.570, F),   # E from U14.7
        ("track", 99.500, 20.570, 99.500, 21.820, F),   # S to R45.1
        # R45 internal — continues from R45.2 via CAN_TERM_MID to R46.1
        # CANH continues from R45.1 (separate trace) to U15.1 (97, 27.95) and J20.2 (96.38, 9.15)
        # Branch back to U15.1: from (99.50, 21.82) go SW
        ("track", 99.500, 21.820, 97.000, 24.000, F),
        ("track", 97.000, 24.000, 97.000, 27.950, F),   # S to U15.1
        # Branch to J20.2: from (97, 24) go N to J20 area
        ("track", 97.000, 24.000, 97.000, 13.000, F),   # N up to J20.2 column
        ("track", 97.000, 13.000, 96.380, 13.000, F),   # W to J20.2 column
        ("track", 96.380, 13.000, 96.380, 9.150, F),    # N to J20.2
    ],
    # CANL: similar to CANH but mirrored on east side
    "CANL_NET": [
        ("track", 94.330, 20.570, 99.500, 24.180, F),   # diagonal to R46.2 (S of R45)
        # R46 internal — continues from R46.1 via CAN_TERM_MID to R45.2
        # CANL continues to U15.2 (97, 26.05) + J20.3 (97.62, 9.15)
        ("track", 99.500, 24.180, 97.620, 25.000, F),   # SW
        ("track", 97.620, 25.000, 97.620, 26.050, F),   # S to U15.2 column
        ("track", 97.620, 26.050, 97.000, 26.050, F),   # W to U15.2
        # Branch to J20.3: from (97.62, 25) go N
        ("track", 97.620, 25.000, 97.620, 9.150, F),    # N to J20.3
    ],
    # CAN_TERM_MID R45.2-R46.1 short link
    # R45.2 at (99.5, 20.18), R46.1 at (99.5, 25.82). Vertical link.
    # Actually CAN_TERM_MID is intra-pair, not in NETS_TO_RESET — handle separately
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


def main():
    print("=== Route CAN subsystem ===\n")
    brd = pcbnew.LoadBoard(PCB)

    # Reset CAN nets
    to_remove = [t for t in brd.GetTracks() if t.GetNetname() in NETS_TO_RESET]
    for t in to_remove:
        brd.Remove(t)
    print(f"  removed {len(to_remove)} existing CAN tracks/vias")

    n_tr = 0
    for name, segs in ROUTES.items():
        net = get_net(brd, name)
        if net is None:
            print(f"  !!! {name}: net not found"); continue
        for seg in segs:
            if seg[0] == "track":
                _, x1, y1, x2, y2, layer = seg
                add_track(brd, x1, y1, x2, y2, layer, net)
                n_tr += 1
        print(f"  {name}: {sum(1 for s in segs if s[0]=='track')} tracks")

    # CAN_TERM_MID short link between R45.2 + R46.1
    can_term = get_net(brd, "CAN_TERM_MID")
    if can_term:
        add_track(brd, 99.500, 20.180, 99.500, 25.820, F, can_term)
        n_tr += 1
        print(f"  CAN_TERM_MID: 1 track (R45.2 ↔ R46.1)")

    print(f"\n  Total: {n_tr} tracks added\n")

    for z in brd.Zones():
        if hasattr(z, "UnFill"): z.UnFill()
    pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
    pcbnew.SaveBoard(PCB, brd)
    print("  saved\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
