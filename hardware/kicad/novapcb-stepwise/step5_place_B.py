#!/usr/bin/env python3
"""Step 5 — place B (POWER_REG_3V3) on the incremental-integration board.

Run AFTER step1 (C), step2 (E), step3 (F), and step4 (G) have placed
their subsystems.

B subsystem per docs/SUBSYSTEM_CONTRACTS.md §B:
  U6   — eFuse (TPS25922 or similar) on the P5V_BEC path
  U2   — main +3V3 LDO (AP2112K-3.3, SOT-25, per power_3b.py)
  D1   — TVS diode on input
  Q2   — auxiliary FET (TBD: reverse polarity?)
  R7..R10, R13 — eFuse programming (ILIM, PG pull-up, FLT pull-up)
  C7, C8, C9, C31..C34 — input/output bulk + 100nF decap
  FB2  — ferrite bead isolating +3V3 → +3V3_IMU
  U13  — secondary LDO for +3V3_IMU (LP5907MFX-3.3, SOT-23-5)
  C77, C78 — U13 input/output decap

Zone: X=20..70, Y=15..28.
  - U6 closer to power input (south, Y=15..20)
  - U2 closer to MCU (north, Y=24..28)
  - FB2 + U13 along path to D (north side; +3V3_IMU exits at Y≈28, X≈45)

Mid-long-edge mounting-hole keep-out RESERVED per master 2026-05-23
(see PLACEMENT_STRATEGY.md §5.3): (3, 35) and (87, 35) with 8mm
circular keep-out. B zone X=20..70 doesn't overlap these positions —
no constraint impact for B specifically, but enforced in the
collision-detection logic as a board-wide rule.

All coords pcbnew Y-down (per reconciled convention).

Hard gate prerequisite (master RF-2 2026-05-23): gate12_thermal.py
must be parameterized BEFORE this PR. Confirmed — see
`gate12_thermal.py` committed sha b960739.
"""
import os
import sys
import math
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")

B_REFDES = [
    "U6", "U2", "U13", "Q2", "D1", "FB2",
    "R7", "R8", "R9", "R10", "R13",
    "C7", "C8", "C9", "C31", "C32", "C33", "C34",
    "C77", "C78",
]

ZONE_X_MIN, ZONE_X_MAX = 20.0, 70.0
ZONE_Y_MIN, ZONE_Y_MAX = 15.0, 28.0

# Mid-long-edge mounting-hole keep-out (sim-gated +2 holes per master
# 2026-05-23). 8mm circular keep-out at each midpoint of long edges.
MID_HOLE_KEEPOUT = [
    (3.0, 35.0, 8.0),    # west mid
    (87.0, 35.0, 8.0),   # east mid
]

# Strategy: U2 north (Y=24..28), U6 south (Y=15..20), U13 + FB2 on
# north edge (Y≈26..28) along the path to D zone.

# Anchor positions for the major components (target X, Y, rot)
ANCHORS = {
    "U6":  (35.0, 18.0, 0.0),    # eFuse, south
    "D1":  (40.0, 19.0, 0.0),    # TVS diode, near U6 input
    "U2":  (45.0, 26.0, 0.0),    # main LDO, north (near MCU)
    "Q2":  (32.0, 25.0, 0.0),    # auxiliary FET
    "FB2": (50.0, 27.0, 0.0),    # ferrite bead, exits north
    "U13": (55.0, 26.0, 0.0),    # IMU LDO, near FB2 exit
    "R7":  (38.0, 21.0, 0.0),
    "R8":  (40.0, 21.0, 0.0),
    "R9":  (42.0, 21.0, 0.0),
    "R10": (44.0, 21.0, 0.0),
    "R13": (46.0, 21.0, 0.0),
    "C7":  (32.0, 19.0, 0.0),
    "C8":  (34.0, 19.0, 0.0),
    "C9":  (33.0, 17.0, 0.0),
    "C31": (43.0, 27.0, 0.0),
    "C32": (45.0, 27.0, 90.0),   # U2 input cap, vertical
    "C33": (47.0, 27.0, 90.0),   # U2 output cap, vertical
    "C34": (43.0, 24.0, 0.0),
    "C77": (53.0, 27.0, 0.0),    # U13 input cap
    "C78": (57.0, 27.0, 0.0),    # U13 output cap
}


def _mm(x): return pcbnew.FromMM(x)


def _courtyard_bbox(fp):
    ctyd_layers = (pcbnew.F_CrtYd, pcbnew.B_CrtYd)
    x0 = y0 = float("inf"); x1 = y1 = float("-inf"); found = False
    for d in fp.GraphicalItems():
        if not isinstance(d, pcbnew.PCB_SHAPE): continue
        if d.GetLayer() not in ctyd_layers: continue
        b = d.GetBoundingBox()
        bx0 = b.GetX()/1e6; by0 = b.GetY()/1e6
        bx1 = bx0 + b.GetWidth()/1e6; by1 = by0 + b.GetHeight()/1e6
        x0, y0 = min(x0, bx0), min(y0, by0)
        x1, y1 = max(x1, bx1), max(y1, by1); found = True
    if not found:
        b = fp.GetBoundingBox()
        x0 = b.GetX()/1e6; y0 = b.GetY()/1e6
        x1 = x0 + b.GetWidth()/1e6; y1 = y0 + b.GetHeight()/1e6
    return (x0, y0, x1, y1)


def _bbox_intersects(a, b):
    return not (a[2] <= b[0] or a[0] >= b[2] or a[3] <= b[1] or a[1] >= b[3])


def _bbox_within_keepout(bb, keepouts):
    """Check if footprint bbox intersects ANY mid-edge mounting-hole
    keep-out circle. Returns True if collision (bad)."""
    cx = (bb[0] + bb[2]) / 2
    cy = (bb[1] + bb[3]) / 2
    half_x = (bb[2] - bb[0]) / 2
    half_y = (bb[3] - bb[1]) / 2
    for kx, ky, kdia in keepouts:
        kr = kdia / 2
        # Distance from bbox center to keepout center
        d = math.hypot(cx - kx, cy - ky)
        # Rough: bbox closest distance ≤ d - max(half_x, half_y); collision if d < kr + bbox_diag
        bbox_diag = math.hypot(half_x, half_y)
        if d < kr + bbox_diag:
            return True
    return False


def find_fp(brd, ref):
    for fp in brd.GetFootprints():
        if fp.GetReference() == ref: return fp
    return None


def main():
    print("=== Step 5 — place B (POWER_REG_3V3) ===", flush=True)
    brd = pcbnew.LoadBoard(PCB)

    # Idempotent: park any pre-existing B refs before snapshotting.
    park_x = 130.0
    for ref in B_REFDES:
        fp = find_fp(brd, ref)
        if fp:
            fp.SetPosition(pcbnew.VECTOR2I(_mm(park_x), _mm(5.0)))
            park_x += 5.0

    placed = []
    for fp in brd.GetFootprints():
        if fp.GetPosition().x/1e6 < 100.0:
            placed.append((fp, _courtyard_bbox(fp)))
    print(f"  already-placed on-board (excl B): {len(placed)} footprints", flush=True)

    placed_B = []

    def try_place(ref, x, y, rot=0.0):
        fp = find_fp(brd, ref)
        if fp is None:
            print(f"  WARN: {ref} not found"); return
        if rot: fp.SetOrientationDegrees(rot)
        for r in [0.0, 0.5, 1.0, 1.5, 2.5, 4.0]:
            for ang in (0,) if r == 0 else range(0, 360, 30):
                tx = x + r * math.cos(math.radians(ang))
                ty = y + r * math.sin(math.radians(ang))
                if not (ZONE_X_MIN <= tx <= ZONE_X_MAX and ZONE_Y_MIN <= ty <= ZONE_Y_MAX):
                    continue
                fp.SetPosition(pcbnew.VECTOR2I(_mm(tx), _mm(ty)))
                bb = _courtyard_bbox(fp)
                if bb[0] < ZONE_X_MIN - 0.1 or bb[2] > ZONE_X_MAX + 0.1 or \
                   bb[1] < ZONE_Y_MIN - 0.1 or bb[3] > ZONE_Y_MAX + 0.1:
                    continue
                # Mid-edge keep-out check (board-wide rule)
                if _bbox_within_keepout(bb, MID_HOLE_KEEPOUT):
                    continue
                ok = True
                for _, pb in placed + placed_B:
                    if _bbox_intersects(bb, pb): ok = False; break
                if not ok: continue
                placed_B.append((fp, bb))
                print(f"  {ref:4} @ ({tx:.2f}, {ty:.2f}) rot={rot:.0f}°  "
                      f"bbox X={bb[0]:.2f}..{bb[2]:.2f}, Y={bb[1]:.2f}..{bb[3]:.2f}", flush=True)
                return
        print(f"  !! could not place {ref} near target ({x}, {y})")

    # Place in priority order: U2, U6, U13 first (the heat-generating + critical)
    for ref in ["U2", "U6", "U13", "Q2", "D1", "FB2",
                "C32", "C33", "C77", "C78",
                "C31", "C34", "C7", "C8", "C9",
                "R7", "R8", "R9", "R10", "R13"]:
        if ref in ANCHORS:
            tx, ty, rot = ANCHORS[ref]
            try_place(ref, tx, ty, rot)

    pcbnew.SaveBoard(PCB, brd)
    print(f"\n  Placed {len(placed_B)} of {len(B_REFDES)} B components", flush=True)
    return 0 if len(placed_B) == len(B_REFDES) else 1


if __name__ == "__main__":
    sys.exit(main())
