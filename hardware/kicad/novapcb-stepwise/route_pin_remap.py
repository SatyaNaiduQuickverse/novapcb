#!/usr/bin/env python3
"""Manual routing after pin remap (master+Sai 2026-05-24).

Nets to (re-)route:
  1. IMU3_INT1: was U1.pad41(PE11) → U9.IMU3_INT1; now U1.pad36(PB2) → U9
     - Delete old 13 segments
     - New F.Cu route from (44.00, 42.67) south + east to (79.17, 56.25)
  2-7. MOT1-6 (S-edge MCU pads → J11.1-6): F.Cu south sweep + small east bend
  8-9. MOT7-8 (N-edge MCU pads → J11.7-8): F.Cu N-stub → via → B.Cu south
       past MCU body → continue south → via → F.Cu to J11
  10. J11.10 GND stitching via at (59.0, 78.5) + F.Cu stub from J11.10

Per master 2026-05-24 sign-off after audit + remap PR ratification.
"""
import os
import sys
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")

W = 0.25
VIA_DIA = 0.50
VIA_DRILL = 0.30

F = pcbnew.F_Cu
B = pcbnew.B_Cu

NETS_TO_RESET = ["MOT1", "MOT2", "MOT3", "MOT4", "MOT5", "MOT6", "MOT7", "MOT8", "IMU3_INT1"]

# Per-net path. Same format as route_h_manual.py.
ROUTES = {
    # IMU3_INT1: new pad 36 (44.0, 42.67) → U9 (79.17, 56.25)
    # Drop to B.Cu near pad to avoid MOT3-6 F.Cu sweeps at X=45-48,
    # route B.Cu SE under MCU body shadow to D-zone, via back to F.Cu
    # close to U9.
    "IMU3_INT1": [
        ("track", 44.000, 42.670, 44.000, 43.500, F),  # F.Cu pad stub S
        ("via",   44.000, 43.500),
        ("track", 44.000, 43.500, 49.000, 48.500, B),  # B.Cu SE diagonal (clear of MOT*)
        ("track", 49.000, 48.500, 60.000, 48.500, B),  # B.Cu E
        ("track", 60.000, 48.500, 78.000, 55.000, B),  # B.Cu SE toward U9
        ("via",   78.000, 55.000),
        ("track", 78.000, 55.000, 79.170, 56.250, F),  # F.Cu stub to U9 pad
    ],
    # MOT1: S pad (43.00, 42.67) → J11.1 (46.875, 78.15)
    "MOT1": [
        ("track", 43.000, 42.670, 43.000, 44.000, F),
        ("track", 43.000, 44.000, 42.000, 45.000, F),  # SW past I2C2_SCL cluster
        ("track", 42.000, 45.000, 42.000, 75.000, F),  # straight south at X=42 (clear)
        ("track", 42.000, 75.000, 46.875, 75.000, F),  # east bend
        ("track", 46.875, 75.000, 46.875, 78.150, F),
    ],
    # MOT2: S pad (43.50, 42.67) → J11.2 (48.125, 78.15)
    "MOT2": [
        ("track", 43.500, 42.670, 43.500, 44.500, F),
        ("track", 43.500, 44.500, 40.500, 47.500, F),  # SW past I2C2 cluster
        ("track", 40.500, 47.500, 40.500, 74.500, F),
        ("track", 40.500, 74.500, 48.125, 74.500, F),
        ("track", 48.125, 74.500, 48.125, 78.150, F),
    ],
    # MOT3-6: fan EAST first to staggered X columns (≥0.85mm pitch) at
    # Y≈51 (clear of I2C2/SPI1 mess at Y=44-48), then south sweep, then
    # east to J11 pin.
    # Target X columns at Y=51..72: MOT3=49.0, MOT4=50.0, MOT5=51.0, MOT6=52.0
    # MOT3 pad 39 (45.50, 42.67) → J11.3 (49.375, 78.15)
    "MOT3": [
        ("track", 45.500, 42.670, 45.500, 44.000, F),
        ("track", 45.500, 44.000, 49.000, 50.000, F),  # NE-bend out to column
        ("track", 49.000, 50.000, 49.000, 74.000, F),  # south sweep at X=49.0
        ("track", 49.000, 74.000, 49.375, 74.000, F),
        ("track", 49.375, 74.000, 49.375, 78.150, F),
    ],
    # MOT4 pad 41 (46.50, 42.67) → J11.4 (50.625, 78.15)
    "MOT4": [
        ("track", 46.500, 42.670, 46.500, 44.000, F),
        ("track", 46.500, 44.000, 50.000, 50.500, F),
        ("track", 50.000, 50.500, 50.000, 73.500, F),
        ("track", 50.000, 73.500, 50.625, 73.500, F),
        ("track", 50.625, 73.500, 50.625, 78.150, F),
    ],
    # MOT5 pad 43 (47.50, 42.67) → J11.5 (51.875, 78.15)
    "MOT5": [
        ("track", 47.500, 42.670, 47.500, 44.000, F),
        ("track", 47.500, 44.000, 51.000, 51.000, F),
        ("track", 51.000, 51.000, 51.000, 73.000, F),
        ("track", 51.000, 73.000, 51.875, 73.000, F),
        ("track", 51.875, 73.000, 51.875, 78.150, F),
    ],
    # MOT6 pad 44 (48.00, 42.67) → J11.6 (53.125, 78.15)
    "MOT6": [
        ("track", 48.000, 42.670, 48.000, 44.000, F),
        ("track", 48.000, 44.000, 52.000, 51.500, F),
        ("track", 52.000, 51.500, 52.000, 72.500, F),
        ("track", 52.000, 72.500, 53.125, 72.500, F),
        ("track", 53.125, 72.500, 53.125, 78.150, F),
    ],
    # MOT7-8: N-edge pads → SHORT F.Cu stub → via north of MCU body in
    # CLEAR area (avoiding R3 BOOT0 at (41.49, 25.045)).
    # R3 BOOT0 pad bbox: X≈41.0..42.0, Y≈24.55..25.55. Place vias at
    # X≥40 + Y≥26 to clear R3 by ≥0.5mm.
    # MOT7 pad 95 (41.50, 27.32) → J11.7 (54.375, 78.15)
    "MOT7": [
        ("track", 41.500, 27.320, 39.000, 27.320, F),  # W F.Cu stub to clear R3
        ("via",   39.000, 27.320),                      # via west of MCU N pad row, clear of R3
        ("track", 39.000, 27.320, 39.000, 70.000, B),  # B.Cu south past MCU body + south corridor
        ("track", 39.000, 70.000, 54.375, 70.000, B),  # east on B.Cu
        ("via",   54.375, 70.000),
        ("track", 54.375, 70.000, 54.375, 78.150, F),
    ],
    # MOT8 pad 96 (41.00, 27.32) → J11.8 (55.625, 78.15)
    "MOT8": [
        ("track", 41.000, 27.320, 38.000, 27.320, F),  # W stub (further than MOT7 for via clearance)
        ("via",   38.000, 27.320),
        ("track", 38.000, 27.320, 38.000, 69.500, B),
        ("track", 38.000, 69.500, 55.625, 69.500, B),
        ("via",   55.625, 69.500),
        ("track", 55.625, 69.500, 55.625, 78.150, F),
    ],
}

# J11.10 GND stitching via at (59.0, 78.5) + F.Cu stub from pad
GND_STITCH = {
    "via_xy": (59.0, 78.5),
    "pad_xy": (58.125, 78.15),
}


def _mm(x):
    return pcbnew.FromMM(x)


def get_net(brd, name):
    for fp in list(brd.GetFootprints()):
        for pad in fp.Pads():
            if pad.GetNetname() == name:
                return pad.GetNet()
    return None


def add_track(brd, x1, y1, x2, y2, layer, net_obj):
    t = pcbnew.PCB_TRACK(brd)
    t.SetStart(pcbnew.VECTOR2I(_mm(x1), _mm(y1)))
    t.SetEnd(pcbnew.VECTOR2I(_mm(x2), _mm(y2)))
    t.SetWidth(_mm(W))
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


def main():
    print("=== Route post-pin-remap (MOT1-8 + IMU3_INT1 + J11.10 GND) ===\n")
    brd = pcbnew.LoadBoard(PCB)

    # Reset all affected nets (remove old tracks/vias)
    targets = set(NETS_TO_RESET)
    to_remove = [t for t in brd.GetTracks() if t.GetNetname() in targets]
    for t in to_remove:
        brd.Remove(t)
    print(f"  removed {len(to_remove)} existing tracks/vias on {len(targets)} nets\n")

    n_tr = 0; n_vi = 0
    for name, segs in ROUTES.items():
        net = get_net(brd, name)
        if net is None:
            print(f"  !!! {name}: net not found"); continue
        total_len = 0.0
        f_count = b_count = 0; via_count = 0
        for seg in segs:
            if seg[0] == "track":
                _, x1, y1, x2, y2, layer = seg
                add_track(brd, x1, y1, x2, y2, layer, net)
                total_len += ((x1-x2)**2 + (y1-y2)**2) ** 0.5
                n_tr += 1
                if layer == F: f_count += 1
                else: b_count += 1
            else:
                _, x, y = seg
                add_via(brd, x, y, net)
                n_vi += 1
                via_count += 1
        print(f"  {name:<11}: {f_count}F+{b_count}B trk + {via_count} via, len={total_len:.1f}mm")

    # J11.10 GND stitching via + trace
    gnd_net = get_net(brd, "GND")
    add_via(brd, GND_STITCH["via_xy"][0], GND_STITCH["via_xy"][1], gnd_net)
    add_track(brd, GND_STITCH["pad_xy"][0], GND_STITCH["pad_xy"][1],
              GND_STITCH["via_xy"][0], GND_STITCH["via_xy"][1], F, gnd_net)
    n_tr += 1; n_vi += 1
    print(f"  J11.10 GND : 1F trk + 1 via @ ({GND_STITCH['via_xy'][0]},{GND_STITCH['via_xy'][1]})")

    print(f"\n  Total: {n_tr} tracks + {n_vi} vias\n")

    for z in brd.Zones():
        if hasattr(z, "UnFill"): z.UnFill()
    pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
    pcbnew.SaveBoard(PCB, brd)
    print(f"  refilled zones + saved\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
