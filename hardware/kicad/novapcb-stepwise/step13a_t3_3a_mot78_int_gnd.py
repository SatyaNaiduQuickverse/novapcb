#!/usr/bin/env python3
"""T3 Sub-attempt 3a: MOT7-8 + IMU3_INT1 + J11.10 GND stitching via.

Per master 2026-05-24 (A) sign-off after focused obstacle survey PR #98.

Per survey: MOT7-8 N-edge column X=37.5..42 essentially clear (1 BATT
sense B.Cu + 7 vias to dodge). IMU3_INT1 wraps to D-zone via B.Cu
SE diagonal.

Vias placed at clear positions:
- MOT7 entry via (40, 26): clear of R3 BOOT0 (41.49, 25.05) + GND via
  (38, 28). B.Cu south at X=40 until Y=55, dodge east to X=41 at Y=55-70
  (avoid GND via at 40, 60). Exit via (54.375, 70).
- MOT8 entry via (37.5, 26): west of GND vias at X=38. B.Cu south at
  X=37.5 to Y=70 (GND vias at 38,28/43/48 are 0.5mm clear). Exit via
  (55.625, 70).
- IMU3_INT1 entry via (44, 43.5): close to PB2 pad 36 (44, 42.67).
  B.Cu SE diagonal to (79, 55). Exit via at (79, 55). F.Cu short to
  U9.12 (79.17, 56.25).
- J11.10 GND: via (59, 78.5), 1mm F.Cu trace from pad (58.125, 78.15).
"""
import os, sys, pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")

W = 0.25; VIA_DIA = 0.50; VIA_DRILL = 0.30
F = pcbnew.F_Cu; B = pcbnew.B_Cu

NETS_TO_RESET = {"MOT7", "MOT8", "IMU3_INT1"}

ROUTES = {
    # Iter 2 fixes from iter 1 (+37 DRC):
    # - MOT7/MOT8 E legs WERE BOTH at Y=70 → physical overlap. Stagger.
    # - MOT8 at Y=70 hit GND via (40,70). Push MOT8 to Y=72.
    # - MOT7 keep Y=68 to avoid GND via at (40,70) too.
    # - IMU3_INT1 diagonal passed GND via at (58,48). Shift diagonal.
    # Iter 4 fixes:
    # - Y-stagger MOT7 (Y=25.5) vs MOT8 (Y=24.5) W stubs — was same-Y overlap
    # - MOT8 B.Cu corridor shift X=37.5→36.5 to clear BATT_VOLTAGE_SENS at X=37.14
    "MOT7": [
        ("track", 41.500, 27.320, 41.500, 25.500, F),       # N stub
        ("track", 41.500, 25.500, 40.000, 25.500, F),       # W at Y=25.5
        ("via",   40.000, 25.500),
        ("track", 40.000, 25.500, 40.000, 55.000, B),
        ("track", 40.000, 55.000, 41.000, 56.000, B),       # dodge E around GND via at (40,60)
        ("track", 41.000, 56.000, 41.000, 68.000, B),
        ("track", 41.000, 68.000, 54.375, 68.000, B),       # E at Y=68
        ("via",   54.375, 68.000),
        ("track", 54.375, 68.000, 54.375, 78.150, F),
    ],
    "MOT8": [
        ("track", 41.000, 27.320, 41.000, 24.500, F),       # N stub (Y-staggered from MOT7 Y=25.5)
        ("track", 41.000, 24.500, 36.500, 24.500, F),       # W at Y=24.5 (clear of MOT7 W stub at Y=25.5)
        ("via",   36.500, 24.500),
        ("track", 36.500, 24.500, 36.500, 72.000, B),       # B.Cu S at X=36.5 (1mm W of MOT7 X=40, clear of BATT B.Cu at X=37.14)
        ("track", 36.500, 72.000, 55.625, 72.000, B),       # E at Y=72 (Y-staggered from MOT7 Y=68)
        ("via",   55.625, 72.000),
        ("track", 55.625, 72.000, 55.625, 78.150, F),
    ],
    "IMU3_INT1": [
        ("track", 44.000, 42.670, 44.000, 43.500, F),       # F.Cu pad stub
        ("via",   44.000, 43.500),
        # Iter 4 kink: dodge GND via at (58, 48) — route through (56, 46) NORTH of via
        ("track", 44.000, 43.500, 56.000, 46.000, B),       # B.Cu SE — exits NORTH of GND via at 58,48
        ("track", 56.000, 46.000, 60.000, 50.000, B),       # SE down past via
        ("track", 60.000, 50.000, 79.000, 55.000, B),
        ("via",   79.000, 55.000),
        ("track", 79.000, 55.000, 79.170, 56.250, F),
    ],
}

GND_STITCH = {"via_xy": (59.0, 78.5), "pad_xy": (58.125, 78.15)}


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
    print("=== T3 3a: MOT7-8 + IMU3_INT1 + GND stitch ===\n")
    brd = pcbnew.LoadBoard(PCB)

    to_remove = [t for t in brd.GetTracks() if t.GetNetname() in NETS_TO_RESET]
    for t in to_remove: brd.Remove(t)
    print(f"  removed {len(to_remove)} existing tracks/vias\n")

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

    gnd = get_net(brd, "GND")
    add_via(brd, GND_STITCH["via_xy"][0], GND_STITCH["via_xy"][1], gnd)
    add_track(brd, GND_STITCH["pad_xy"][0], GND_STITCH["pad_xy"][1],
              GND_STITCH["via_xy"][0], GND_STITCH["via_xy"][1], F, gnd)
    n_tr += 1; n_vi += 1
    print(f"  J11.10 GND: 1F+1via @ ({GND_STITCH['via_xy'][0]},{GND_STITCH['via_xy'][1]})")

    print(f"\n  Total: {n_tr} tracks + {n_vi} vias\n")

    for z in brd.Zones():
        if hasattr(z, "UnFill"): z.UnFill()
    pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
    pcbnew.SaveBoard(PCB, brd)
    print("  saved\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
