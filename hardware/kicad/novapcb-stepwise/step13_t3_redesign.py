#!/usr/bin/env python3
"""step13_t3_redesign — South corridor T3 full redesign execution.

Per docs/SOUTH_CORRIDOR_REDESIGN_PLAN.md (master+Sai ratified 2026-05-24).

8-substep plan:
  A. Clear all existing routes on 8 corridor nets
  B. Move R11/R12 south to Y=49.5
  C.1 SPI1 (×3) re-route on B.Cu MCU S pads → U3 IMU1
  C.2 IMU CS (×3) re-route on B.Cu MCU W/N pads → U3/U8/U9
  C.3 I²C2 (×2) F.Cu→B.Cu→F.Cu split (preserves U4 endpoint)
  C.4 MOT3-6 (×4) F.Cu south fanout (now-cleared corridor)
  C.5 MOT1-2 (×2) F.Cu south straight + east bend
  C.6 MOT7-8 (×2) N-edge F.Cu→via→B.Cu→via→F.Cu
  C.7 IMU3_INT1 (×1) PB2 → U9 via B.Cu wraparound
  C.8 J11.10 GND stitching via
  D. Refill zones, save

DON'T touch:
- IMU2_ACC_INT1 (B.Cu, not in MOT* conflict zone)
- SPI3_MOSI (B.Cu wraparound, KEEP)
- +3V3 stubs (anchor to body decap, not relocatable)
- GND stitching vias (keep all)
"""
import os, sys, pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")

W = 0.25
VIA_DIA = 0.50
VIA_DRILL = 0.30
F = pcbnew.F_Cu; B = pcbnew.B_Cu

# Nets to fully reset (clear ALL their tracks/vias)
NETS_TO_RESET = {
    "I2C2_SCL", "I2C2_SDA",
    "SPI1_SCK", "SPI1_MISO", "SPI1_MOSI",
    "IMU1_CS", "IMU2_GYR_CS", "IMU3_CS",
    "IMU3_INT1",
    "MOT1", "MOT2", "MOT3", "MOT4", "MOT5", "MOT6", "MOT7", "MOT8",
}

# R11/R12 relocation
RELOCATE = {
    "R11": (52.51, 49.5, 0),
    "R12": (46.51, 49.5, 0),
}

# Per-net routes after corridor clear
# Format: list of ('track', x1, y1, x2, y2, layer) | ('via', x, y)
ROUTES = {
    # === C.1 SPI1 (B.Cu) MCU S pads → U3 IMU1 in D-zone ===
    # SPI1_SCK PA5 pad 29 (40.50, 42.67) → U3.11 (61.46, 56.25)
    "SPI1_SCK": [
        ("track", 40.500, 42.670, 40.500, 44.000, F),  # F.Cu stub S from pad
        ("via",   40.500, 44.000),
        ("track", 40.500, 44.000, 60.000, 56.000, B),  # B.Cu SE diagonal
        ("track", 60.000, 56.000, 61.460, 56.250, B),
        ("via",   61.460, 56.250),
        # U3.11 F.Cu — no stub needed if via at pad center; small finish trace
    ],
    "SPI1_MISO": [
        ("track", 41.000, 42.670, 41.000, 44.500, F),  # F.Cu stub (staggered Y from SCK)
        ("via",   41.000, 44.500),
        ("track", 41.000, 44.500, 60.500, 57.000, B),
        ("track", 60.500, 57.000, 61.460, 57.250, B),
        ("via",   61.460, 57.250),
    ],
    "SPI1_MOSI": [
        ("track", 41.500, 42.670, 41.500, 45.000, F),
        ("via",   41.500, 45.000),
        ("track", 41.500, 45.000, 60.000, 55.500, B),
        ("track", 60.000, 55.500, 60.500, 55.800, B),
        ("via",   60.500, 55.800),
    ],
    # === C.2 IMU CS (B.Cu) ===
    # IMU1_CS PC15 pad 9 W (37.33, 33.00) → U3.10 (61.46, 56.75)
    "IMU1_CS": [
        ("track", 37.330, 33.000, 36.500, 33.000, F),  # F.Cu W stub from pad
        ("via",   36.500, 33.000),
        ("track", 36.500, 33.000, 36.500, 50.000, B),  # B.Cu south
        ("track", 36.500, 50.000, 61.460, 56.750, B),  # B.Cu SE diagonal to U3.10
        ("via",   61.460, 56.750),
    ],
    # IMU2_GYR_CS PD4 pad 85 N (46.50, 27.32) → U8.5 (66.80, 56.50)
    "IMU2_GYR_CS": [
        ("track", 46.500, 27.320, 46.500, 26.000, F),  # tiny N stub
        ("via",   46.500, 26.000),
        ("track", 46.500, 26.000, 66.800, 56.500, B),  # B.Cu long SE
        ("via",   66.800, 56.500),
    ],
    # IMU3_CS PE2 pad 1 W (37.33, 29.00) → U9.12 (77.50, 57.92)
    "IMU3_CS": [
        ("track", 37.330, 29.000, 36.000, 29.000, F),  # F.Cu W stub
        ("via",   36.000, 29.000),
        ("track", 36.000, 29.000, 36.000, 51.000, B),  # B.Cu south
        ("track", 36.000, 51.000, 77.500, 57.920, B),  # B.Cu SE long diagonal to U9.12
        ("via",   77.500, 57.920),
    ],
    # === C.3 I²C2 F.Cu→B.Cu→F.Cu split (preserves U4 endpoint) ===
    # I²C2_SCL: U1.46 (49, 42.67) → R12 (46.51, 49.5 NEW) → U4.4 (43.98, 47.8)
    "I2C2_SCL": [
        ("track", 49.000, 42.670, 49.000, 44.000, F),  # F.Cu stub S
        ("via",   49.000, 44.000),
        ("track", 49.000, 44.000, 46.510, 49.500, B),  # B.Cu SW to R12 new pos
        ("via",   46.510, 49.500),
        # R12 internal — continues from R12 (other pad) via internal
        # Continue from R12 to U4.4: separate trace
        ("via",   46.510, 49.500),  # via at R12 pad (idempotent — same loc)
        ("track", 46.510, 49.500, 43.980, 48.500, B),  # B.Cu NW
        ("via",   43.980, 48.500),
        ("track", 43.980, 48.500, 43.980, 47.800, F),  # F.Cu N stub to U4.4
    ],
    # I²C2_SDA: U1.47 → R11 new → U4.3
    "I2C2_SDA": [
        ("track", 49.500, 42.670, 49.500, 44.500, F),
        ("via",   49.500, 44.500),
        ("track", 49.500, 44.500, 52.510, 49.500, B),  # B.Cu SE to R11 new
        ("via",   52.510, 49.500),
        ("via",   52.510, 49.500),
        ("track", 52.510, 49.500, 43.330, 49.500, B),  # B.Cu long W to U4.3 area
        ("via",   43.330, 48.500),
        ("track", 43.330, 48.500, 43.330, 47.800, F),  # F.Cu N stub to U4.3
    ],
    # === C.4 MOT3-6 F.Cu south fanout (corridor now cleared) ===
    "MOT3": [
        ("track", 45.500, 42.670, 45.500, 50.500, F),  # straight S past R12 (now at 49.5)
        ("track", 45.500, 50.500, 45.500, 72.500, F),  # continue S past D-zone
        ("track", 45.500, 72.500, 49.375, 72.500, F),  # E bend
        ("track", 49.375, 72.500, 49.375, 78.150, F),  # S to J11.3
    ],
    "MOT4": [
        ("track", 46.500, 42.670, 46.500, 48.000, F),  # S until just N of R12
        ("track", 46.500, 48.000, 47.500, 49.000, F),  # SE diagonal AROUND R12 at (46.51, 49.5)
        ("track", 47.500, 49.000, 47.500, 50.500, F),  # S
        ("track", 47.500, 50.500, 46.500, 51.500, F),  # SW back to MOT4 column
        ("track", 46.500, 51.500, 46.500, 72.000, F),
        ("track", 46.500, 72.000, 50.625, 72.000, F),
        ("track", 50.625, 72.000, 50.625, 78.150, F),
    ],
    "MOT5": [
        ("track", 47.500, 42.670, 47.500, 48.000, F),
        ("track", 47.500, 48.000, 48.500, 49.000, F),  # SE around U7 west edge
        ("track", 48.500, 49.000, 48.500, 71.500, F),
        ("track", 48.500, 71.500, 51.875, 71.500, F),
        ("track", 51.875, 71.500, 51.875, 78.150, F),
    ],
    "MOT6": [
        ("track", 48.000, 42.670, 48.000, 48.000, F),
        ("track", 48.000, 48.000, 49.500, 49.500, F),  # SE
        ("track", 49.500, 49.500, 49.500, 71.000, F),
        ("track", 49.500, 71.000, 53.125, 71.000, F),
        ("track", 53.125, 71.000, 53.125, 78.150, F),
    ],
    # === C.5 MOT1-2 (south straight + east bend) ===
    "MOT1": [
        ("track", 43.000, 42.670, 43.000, 50.000, F),  # straight S clear of U4 at X=43.5
        ("track", 43.000, 50.000, 44.000, 51.000, F),  # SE
        ("track", 44.000, 51.000, 44.000, 73.000, F),
        ("track", 44.000, 73.000, 46.875, 73.000, F),
        ("track", 46.875, 73.000, 46.875, 78.150, F),
    ],
    "MOT2": [
        ("track", 43.500, 42.670, 43.500, 44.000, F),  # tiny S then bend west to clear U4
        ("track", 43.500, 44.000, 42.500, 45.000, F),  # SW
        ("track", 42.500, 45.000, 42.500, 73.500, F),
        ("track", 42.500, 73.500, 48.125, 73.500, F),
        ("track", 48.125, 73.500, 48.125, 78.150, F),
    ],
    # === C.6 MOT7-8 N-edge F.Cu→via→B.Cu→via→F.Cu ===
    "MOT7": [
        ("track", 41.500, 27.320, 39.000, 27.320, F),  # W stub clear of BOOT0
        ("via",   39.000, 27.320),
        ("track", 39.000, 27.320, 39.000, 71.500, B),
        ("track", 39.000, 71.500, 54.375, 71.500, B),
        ("via",   54.375, 71.500),
        ("track", 54.375, 71.500, 54.375, 78.150, F),
    ],
    "MOT8": [
        ("track", 41.000, 27.320, 38.000, 27.320, F),
        ("via",   38.000, 27.320),
        ("track", 38.000, 27.320, 38.000, 71.000, B),
        ("track", 38.000, 71.000, 55.625, 71.000, B),
        ("via",   55.625, 71.000),
        ("track", 55.625, 71.000, 55.625, 78.150, F),
    ],
    # === C.7 IMU3_INT1 PB2 pad 36 (44.0, 42.67) → U9 IMU3_INT1 pad (79.17, 56.25) ===
    "IMU3_INT1": [
        ("track", 44.000, 42.670, 44.000, 43.500, F),
        ("via",   44.000, 43.500),
        ("track", 44.000, 43.500, 60.000, 48.500, B),
        ("track", 60.000, 48.500, 78.000, 55.000, B),
        ("via",   78.000, 55.000),
        ("track", 78.000, 55.000, 79.170, 56.250, F),
    ],
}

# C.8 J11.10 GND stitching via at (59.0, 78.5)
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
    print("=== Step 13: T3 south corridor full redesign ===\n")
    brd = pcbnew.LoadBoard(PCB)

    # Step A: clear corridor nets
    targets = set(NETS_TO_RESET)
    to_remove = [t for t in brd.GetTracks() if t.GetNetname() in targets]
    for t in to_remove: brd.Remove(t)
    print(f"  Step A: removed {len(to_remove)} existing tracks/vias on {len(targets)} corridor nets\n")

    # Step B: relocate R11/R12
    for ref, (x, y, rot) in RELOCATE.items():
        fp = next((f for f in brd.GetFootprints() if f.GetReference()==ref), None)
        if fp:
            old = fp.GetPosition()
            fp.SetPosition(pcbnew.VECTOR2I(_mm(x), _mm(y)))
            fp.SetOrientationDegrees(rot)
            print(f"  Step B: {ref}: ({old.x/1e6:.2f},{old.y/1e6:.2f}) → ({x:.2f},{y:.2f})")

    # Steps C.1-C.7: add new routes
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
        print(f"  {name:<14}: {f_c}F+{b_c}B trk + {via_c}via")

    # Step C.8 GND stitch
    gnd = get_net(brd, "GND")
    add_via(brd, GND_STITCH["via_xy"][0], GND_STITCH["via_xy"][1], gnd)
    add_track(brd, GND_STITCH["pad_xy"][0], GND_STITCH["pad_xy"][1],
              GND_STITCH["via_xy"][0], GND_STITCH["via_xy"][1], F, gnd)
    n_tr += 1; n_vi += 1
    print(f"  J11.10 GND   : 1F+1via @ ({GND_STITCH['via_xy'][0]},{GND_STITCH['via_xy'][1]})")

    print(f"\n  Total: {n_tr} tracks + {n_vi} vias\n")

    # Step D: refill zones
    for z in brd.Zones():
        if hasattr(z, "UnFill"): z.UnFill()
    pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
    pcbnew.SaveBoard(PCB, brd)
    print(f"  Step D: refilled zones + saved\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
