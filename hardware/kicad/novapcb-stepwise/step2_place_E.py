#!/usr/bin/env python3
"""Step 2 — place E (BARO_I2C) on the incremental-integration board.

Run AFTER step1_place_C.py.

E subsystem per docs/SUBSYSTEM_CONTRACTS.md §E:
  U4 — DPS310 primary barometer (I2C2 at 0x76)
  U7 — BMP388 alternate barometer (I2C2 at 0x77)
  C51, C52 — U4 VDD + VDDIO decap (100nF each, 0402)
  C71, C72 — U7 VDD + VDDIO decap (100nF each, 0402)
  R11, R12 — I2C2 pullups (4.7k each, 0402)

Zone (per SUBSYSTEM_CONTRACTS): NW corner of the C zone — X=20..32,
Y=42..50 mm. The barometers are NOT in the IMU island (D) because
they're acoustic-noise-sensitive but not vibration-sensitive.
Adjacency: C (immediately east), short I2C2 trace to U1 pins PB10/PB11.

Snap-clear placer: same algorithm as Step 1 — for each E component,
search for the nearest free position in the assigned zone such that
its courtyard doesn't intersect any already-placed footprint.
"""
import os
import sys
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")

E_REFDES = ["U4", "U7", "C51", "C52", "C71", "C72", "R11", "R12"]
# Zone reconciled 2026-05-22 per master directive: E sits south of U1
# adjacent to PB10 (pin 46 @ X=49) / PB11 (pin 47 @ X=49.5) on U1's
# south edge — that's where I2C2_SCL/SDA exit the MCU. All coords
# pcbnew Y-down (Y=0 top, Y=70 bottom).
ZONE_X_MIN, ZONE_X_MAX = 40.0, 60.0
ZONE_Y_MIN, ZONE_Y_MAX = 44.0, 53.5


def _mm(x_mm: float) -> int:
    return pcbnew.FromMM(x_mm)


def _courtyard_bbox(fp):
    ctyd_layers = (pcbnew.F_CrtYd, pcbnew.B_CrtYd)
    x0 = y0 = float("inf")
    x1 = y1 = float("-inf")
    found = False
    for d in fp.GraphicalItems():
        if not isinstance(d, pcbnew.PCB_SHAPE): continue
        if d.GetLayer() not in ctyd_layers: continue
        b = d.GetBoundingBox()
        bx0 = b.GetX() / 1e6
        by0 = b.GetY() / 1e6
        bx1 = bx0 + b.GetWidth() / 1e6
        by1 = by0 + b.GetHeight() / 1e6
        x0, y0 = min(x0, bx0), min(y0, by0)
        x1, y1 = max(x1, bx1), max(y1, by1)
        found = True
    if not found:
        b = fp.GetBoundingBox()
        x0 = b.GetX() / 1e6
        y0 = b.GetY() / 1e6
        x1 = x0 + b.GetWidth() / 1e6
        y1 = y0 + b.GetHeight() / 1e6
    return (x0, y0, x1, y1)


def _bbox_intersects(a, b):
    return not (a[2] <= b[0] or a[0] >= b[2] or a[3] <= b[1] or a[1] >= b[3])


def find_fp(brd, ref):
    for fp in brd.GetFootprints():
        if fp.GetReference() == ref:
            return fp
    return None


def main():
    print("=== Step 2 — place E (BARO_I2C) ===", flush=True)
    brd = pcbnew.LoadBoard(PCB)

    # Snapshot all currently-placed footprints (X < 100mm) — these are the
    # already-locked subsystems that E must not collide with.
    placed = []
    for fp in brd.GetFootprints():
        if fp.GetPosition().x / 1e6 < 100.0:
            placed.append((fp, _courtyard_bbox(fp)))
    print(f"  on-board (already-placed): {len(placed)} footprints", flush=True)

    # Targeted placement: E sits south of U1, with R11/R12 (I2C2
    # pullups) RIGHT BELOW the PB10/PB11 pins (pin 46 @ X=49, pin 47 @
    # X=49.5, both Y=42.67 on U1 S edge). Baros U4/U7 to the west,
    # decaps adjacent to each baro within 1mm.
    # Pullup placement corrected 2026-05-22 per master Step-3 audit:
    # R11 = SDA pullup -> paired with PB11 (X=49.5), placed EAST of the
    #   C13/C17 corridor so the I2C2_SDA route can come straight south
    #   from PB11 east of C13.
    # R12 = SCL pullup -> paired with PB10 (X=49.0), placed WEST of the
    #   corridor so I2C2_SCL routes south west of C17.
    # Each pullup is a clean stub on the RIGHT net (no SCL↔SDA short).
    targets = [
        # (ref, x, y) in mm (pcbnew Y-down)
        ("R11", 52.0, 46.5),   # SDA pullup, east of C13 (X=51 +/-0.5)
        ("R12", 46.0, 46.5),   # SCL pullup, west of C17 (X=49 +/-0.5)
        ("U4",  43.0, 47.0),   # DPS310 primary baro, west of pullups
        ("C51", 45.0, 47.5),   # U4 VDD decap (moved W 0.5mm to clear SCL via)
        ("C52", 43.0, 49.0),   # U4 VDDIO decap, immediately S of U4
        ("U7",  55.0, 47.0),   # BMP388 alternate baro, far east clear of R11
        ("C71", 57.5, 47.0),   # U7 VDD decap
        ("C72", 55.0, 49.0),   # U7 VDDIO decap
    ]
    placed_E = []
    for ref, x, y in targets:
        fp = find_fp(brd, ref)
        if fp is None:
            print(f"  WARN: {ref} not found in netlist", flush=True)
            continue
        # Try the target spot first; if it conflicts, spiral-search nearby
        spot_found = False
        for radius in [0.0, 0.5, 1.0, 1.5, 2.0, 3.0]:
            for ang in range(0, 360, 30) if radius > 0 else (0,):
                import math
                tx = x + radius * math.cos(math.radians(ang))
                ty = y + radius * math.sin(math.radians(ang))
                if not (ZONE_X_MIN <= tx <= ZONE_X_MAX and ZONE_Y_MIN <= ty <= ZONE_Y_MAX):
                    continue
                fp.SetPosition(pcbnew.VECTOR2I(_mm(tx), _mm(ty)))
                bb = _courtyard_bbox(fp)
                if (bb[0] < ZONE_X_MIN - 0.1 or bb[2] > ZONE_X_MAX + 0.1 or
                    bb[1] < ZONE_Y_MIN - 0.1 or bb[3] > ZONE_Y_MAX + 0.1):
                    continue
                conflict = False
                for _, pb in placed:
                    if _bbox_intersects(bb, pb):
                        conflict = True; break
                if conflict: continue
                for _, eb in placed_E:
                    if _bbox_intersects(bb, eb):
                        conflict = True; break
                if conflict: continue
                placed_E.append((fp, bb))
                print(f"  {ref:5} @ ({tx:.2f}, {ty:.2f}) mm  (target {x:.2f}, {y:.2f})", flush=True)
                spot_found = True
                break
            if spot_found: break
        if not spot_found:
            print(f"  !! could not place {ref} near target ({x}, {y})", flush=True)

    pcbnew.SaveBoard(PCB, brd)
    print(f"\n  Placed {len(placed_E)} of {len(E_REFDES)} E components", flush=True)
    return 0 if len(placed_E) == len(E_REFDES) else 1


if __name__ == "__main__":
    sys.exit(main())
