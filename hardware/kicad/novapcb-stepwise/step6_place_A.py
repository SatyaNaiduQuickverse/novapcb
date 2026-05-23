#!/usr/bin/env python3
"""Step 6 — place A (POWER_INPUT) on the v1.1 105×85 board.

Approved layout (master 2026-05-23, after explicit constraint analysis):
  - 22 components, 230 mm² total courtyard, 18% density on A zone 1275 mm²
  - Two physically-isolated BEC paths (51 mm Q3↔Q4 separation) for EMI
  - Q3/Q4 at Y=10 (max-south within A zone, 10mm from adiabatic north edge)
  - Q3 at X=27 (3mm air-gap to U2 in X but 15mm in Y, no thermal stacking)
  - Q4 at X=78 mirrors symmetrically
  - West cluster: J4 + Q3 + U11 + caps (X=12..40)
  - East cluster: J19 + Q4 + U12 + caps (X=68..95)
  - Mid X=40..68: EMC + thermal breathing room

Mid-edge mounting-hole keep-out (sim-gated +2 holes per master 2026-05-23):
  (3.25, 42.5) west mid + (101.75, 42.5) east mid, 8mm circular. A zone
  Y=0..15 doesn't overlap these (mid-edge is at Y=42.5).

Corner mounting hole keep-outs at H1 (3.25, 3.25) and H2 (101.75, 3.25):
  Both inside A's Y range. 5.5mm pad → effective keep-out radius ~6mm.
  A west boundary X≥10, east boundary X≤96 (enforced).
"""
import os
import sys
import math
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")

A_REFDES = [
    "J4", "J19",
    "Q3", "Q4",
    "U11", "U12",
    "C61", "C62", "C73", "C74", "C75", "C76", "C81", "C82",
    "R41", "R42", "R43", "R44",
    "D5", "D6", "D7", "D8",
]

ZONE_X_MIN, ZONE_X_MAX = 10.0, 96.0
ZONE_Y_MIN, ZONE_Y_MAX = 0.5, 15.0   # extended south to 15 (overlaps B zone at 13-30, but B's X=20-70 placements at Y=14-15 are empty in this strip)

# Corner mounting hole keep-outs in A zone (south corners at Y=3.25)
CORNER_HOLE_KEEPOUT = [
    (3.25, 3.25, 12.0),     # H1 — 6mm radius from 5.5mm pad + 0.5mm clearance, doubled
    (101.75, 3.25, 12.0),   # H2
]

# Component anchors (X, Y, rotation) — master 2026-05-23 sign-off
ANCHORS = {
    # PRIMARY BEC (west cluster, X=12..40)
    # NOTE: Q3 is SO-8 power MOSFET; pads extend Y=7.43..12.57 (well
    # beyond its courtyard Y=8..12). Sense R+C placed in SOUTH BAND
    # (Y=14.5) — north of Q3 conflicts with Q3's north pad row at Y=7.43.
    "J4":  (15.0, 5.0, 0.0),       # Mauch primary 6-pin JST-GH (pads Y=3.15)
    "D5":  (23.0, 4.0, 0.0),       # TVS on J4 BATT+ input
    "D6":  (23.0, 6.0, 0.0),       # TVS on J4 BATT- (return)
    "U11": (33.0, 5.0, 0.0),       # LM74700-Q1 OR-FET ctrl west (SOT-23-6) — kept rot=0 (rot=90 trial had B.Cu crossings; via-on-pad-center fits cleanly per A↔B-2)
    "C73": (36.0, 4.0, 0.0),       # U11 VCAP, NE of U11
    "C74": (36.0, 6.0, 0.0),       # U11 bypass
    "Q3":  (27.0, 10.0, 0.0),      # OR-FET N-channel SO-8 west — REVERTED to (27, 10) — Y=9.5 broke thermal LOCK by +8.5°C MCU. Master 2026-05-23 directive: thermal LOCK load-bearing on Q3 Y=10. DVDT routes via west-around-U6 instead.
    # R42 + C62 RELOCATED WEST (master 2026-05-23 selective B re-place).
    # Original positions (28, 14.5) and (30, 14.5) sat DIRECTLY ABOVE U6
    # north pin column (X=27.25..28.75) blocking 3 of 4 EFUSE protection
    # config exits. New positions clear X=27..30 strip at Y=14.5 entirely.
    # Mauch sense traces re-route in sense sub-step (tracked).
    "R41": (24.0, 14.5, 0.0),      # V_sense divider — SOUTH of Q3 (unchanged)
    "R42": (20.0, 14.5, 0.0),      # I_sense filter — RELOCATED 28→20 (clears U6 north)
    "C61": (22.0, 14.5, 0.0),      # V_sense filter cap (unchanged)
    "C62": (18.0, 14.5, 0.0),      # I_sense filter cap — RELOCATED 30→18 (clears U6 north)

    # BACKUP BEC (east cluster, X=68..95) — mirror of primary
    "J19": (90.0, 5.0, 0.0),       # Mauch secondary 6-pin
    "D7":  (82.0, 4.0, 0.0),       # TVS on J19 BATT+
    "D8":  (82.0, 6.0, 0.0),       # TVS on J19 BATT-
    "U12": (72.0, 5.0, 0.0),       # LM74700-Q1 OR-FET ctrl east (mirror of U11)
    "C75": (69.0, 4.0, 0.0),       # U12 VCAP
    "C76": (69.0, 6.0, 0.0),       # U12 bypass
    "Q4":  (78.0, 9.5, 0.0),       # OR-FET N-channel SO-8 east — MOVED 10.0→9.5 (NORTH 0.5mm) for Q3 symmetry per master 2026-05-23 Option (E)
    "R43": (76.0, 14.5, 0.0),      # V_sense2 divider — SOUTH of Q4
    "R44": (80.0, 14.5, 0.0),      # I_sense2 filter — SOUTH of Q4
    "C81": (74.0, 14.5, 0.0),      # V_sense2 filter cap
    "C82": (82.0, 14.5, 0.0),      # I_sense2 filter cap
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


def _bbox_within_circular_keepout(bb, keepouts):
    cx = (bb[0] + bb[2]) / 2
    cy = (bb[1] + bb[3]) / 2
    half_x = (bb[2] - bb[0]) / 2
    half_y = (bb[3] - bb[1]) / 2
    for kx, ky, kdia in keepouts:
        kr = kdia / 2
        d = math.hypot(cx - kx, cy - ky)
        bbox_diag = math.hypot(half_x, half_y)
        if d < kr + bbox_diag:
            return True
    return False


def find_fp(brd, ref):
    for fp in brd.GetFootprints():
        if fp.GetReference() == ref: return fp
    return None


def main():
    print("=== Step 6 — place A (POWER_INPUT) ===", flush=True)
    brd = pcbnew.LoadBoard(PCB)

    # Idempotent: park any pre-existing A refs before snapshotting
    park_x = 130.0
    for ref in A_REFDES:
        fp = find_fp(brd, ref)
        if fp:
            fp.SetPosition(pcbnew.VECTOR2I(_mm(park_x), _mm(5.0)))
            park_x += 5.0

    # Inventory currently placed (excluding A and parked)
    placed = []
    for fp in brd.GetFootprints():
        if fp.GetPosition().x/1e6 < 100.0:
            placed.append((fp, _courtyard_bbox(fp)))
    print(f"  already-placed on-board (excl A): {len(placed)} footprints", flush=True)

    placed_A = []

    def try_place(ref, x, y, rot=0.0):
        fp = find_fp(brd, ref)
        if fp is None:
            print(f"  WARN: {ref} not found"); return
        if rot: fp.SetOrientationDegrees(rot)
        for r in [0.0, 0.3, 0.6, 1.0, 1.5, 2.5, 4.0]:
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
                if _bbox_within_circular_keepout(bb, CORNER_HOLE_KEEPOUT):
                    continue
                ok = True
                for _, pb in placed + placed_A:
                    if _bbox_intersects(bb, pb): ok = False; break
                if not ok: continue
                placed_A.append((fp, bb))
                print(f"  {ref:4} @ ({tx:.2f}, {ty:.2f}) rot={rot:.0f}°  "
                      f"bbox X={bb[0]:.2f}..{bb[2]:.2f}, Y={bb[1]:.2f}..{bb[3]:.2f}", flush=True)
                return
        print(f"  !! could not place {ref} near target ({x}, {y})")

    # Place in priority order: connectors first (largest), then OR-FETs (next biggest + heat sources), then ctrl/caps
    place_order = [
        "J4", "J19",                    # connectors first (largest)
        "Q3", "Q4",                     # OR-FETs (heat-spreading positions)
        "U11", "U12",                   # controllers
        "C73", "C74", "C75", "C76",     # U11/U12 decap (close to ctrl)
        "D5", "D6", "D7", "D8",         # TVS (close to connectors)
        "R41", "R42", "R43", "R44",     # sense resistors
        "C61", "C62", "C81", "C82",     # sense filter caps
    ]
    for ref in place_order:
        if ref in ANCHORS:
            tx, ty, rot = ANCHORS[ref]
            try_place(ref, tx, ty, rot)

    pcbnew.SaveBoard(PCB, brd)
    print(f"\n  Placed {len(placed_A)} of {len(A_REFDES)} A components", flush=True)
    return 0 if len(placed_A) == len(A_REFDES) else 1


if __name__ == "__main__":
    sys.exit(main())
