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

Zone (v1.1 = 105 × 85 mm board, updated 2026-05-23 after gate12 v3
sign-off): X=10..85, Y=13..30 (expanded from old 90×70 X=20..70,
Y=15..28 — more breathing room west + east on the bigger board).
  - U6 closer to power input (south of B band, Y=15..20)
  - U2 closer to MCU but **pushed maximally west** to put extra
    distance between U2 (LDO heat ~0.642W) and U1 (MCU heat ~0.700W).
    On 90×70 U2 was at (24, 25) = 23mm from U1; on 105×85 U2 moves
    to (15, 22) = 32.7mm from U1 (+40% separation, ~30% heat-flux
    benefit at the U1 site).
  - FB2 + U13 along path to D (north side; +3V3_IMU exits ~Y=28).

Mid-long-edge mounting-hole keep-out (sim-gated +2 holes per master
2026-05-23): on 105×85 board the mid-edge positions are (3, 42.5)
west mid + (102, 42.5) east mid, 8mm circular each. B zone Y=13..30
doesn't overlap these (B is north band, mid-edge is mid-board).

All coords pcbnew Y-down (per reconciled convention).

Hard gate prerequisite (master RF-2 2026-05-23): gate12_thermal.py
must be parameterized BEFORE this PR. Confirmed — see
`gate12_thermal.py` committed sha 3f80f3b (v3 with per-body Body
Force + energy-balance gate + min-mesh-density gate).
"""
import os
import sys
import math
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")

B_REFDES = [
    "U6", "U2", "U13", "Q2", "D1", "FB2",
    "R4", "R5", "R7", "R8", "R9", "R10", "R13",
    "C7", "C8", "C9", "C31", "C32", "C33", "C34",
    "C77", "C78",
]

# v1.1 = 105 × 85 mm board (master sign-off 2026-05-23)
ZONE_X_MIN, ZONE_X_MAX = 10.0, 85.0
ZONE_Y_MIN, ZONE_Y_MAX = 13.0, 30.0

# Mid-long-edge mounting-hole keep-out (sim-gated +2 holes per master
# 2026-05-23). 8mm circular keep-out at each midpoint of long edges
# on the 105×85 board → mid-edge Y = 85/2 = 42.5.
MID_HOLE_KEEPOUT = [
    (3.0, 42.5, 8.0),    # west mid
    (102.0, 42.5, 8.0),  # east mid
]

# Constraint analysis 2026-05-23 (master directive: full analysis up
# front before placement to avoid multi-iteration sagas like U5):
#
# 1. Power flow (south → north, A is south of B):
#    A.+5V_BEC → U6 eFuse (south) → P5V (filtered)
#    P5V → Q2 (rev-pol FET) → U2 LDO (north) → +3V3 (to C+E+F+G plane)
#    +3V3 → FB2 (ferrite) → U13 LDO → +3V3_IMU (to D only)
#    Linear power flow placement: input south, output north.
#
# 2. Heat: U2 (595mW) is the first major added heat source. U1 (700mW)
#    is at (45, 35) — heat halo centered there. To avoid heat stacking,
#    U2 placed at WEST END of B zone (X=24, Y=25) — ~21mm lateral
#    separation from U1 center. Matches STEP4's validated layout
#    (U2_LDO was at X=10, U1_MCU at X=39.53 — 30mm apart).
#
# 3. Mid-edge keep-out per master 2026-05-23 (sim-gated 4→6 holes):
#    (3, 35) west mid + (87, 35) east mid, 8mm circular each. B zone
#    X=20..70, Y=15..28 doesn't overlap either. Rule still enforced
#    in _bbox_within_keepout() as a board-wide constraint.
#
# 4. C boundary: U1 body at Y=28..42 (centered 35, 14mm). B zone
#    upper bound Y=28 keeps B clear of C body — no encroachment.
#
# 5. Heat-dissipation summary (post-placement gate12 v2 run):
#    U1 (45, 35) 700mW + U2 (24, 25) 595mW + U6 (28, 18) 18mW.
#    Predicted Tj_MCU/Tj_LDO similar to STEP4 (within ~75°C) on
#    larger 90×70 board with anisotropic k=33.5/0.316 + h=5 + Tamb=50°C.
ANCHORS = {
    # POWER INPUT SOUTH (Y=15..20)
    "U6":  (28.0, 18.0, 0.0),    # eFuse — input side, south (kept from 90×70)
    "D1":  (35.0, 18.0, 0.0),    # TVS post-eFuse
    "C7":  (24.0, 19.0, 0.0),    # U6 input bulk cap
    "C8":  (32.0, 19.0, 0.0),    # U6 output cap
    "C9":  (32.0, 16.0, 0.0),    # secondary bulk — moved east 4mm to clear A zone R42 sense (which sits at Y=14.5 in same X range as old C9 anchor)

    # AUXILIARY FET MID (Y=21..23)
    "Q2":  (24.0, 22.0, 0.0),    # reverse-polarity FET (kept; small heat)

    # eFuse PROGRAMMING RESISTORS — 0402 row, MOVED Y=22 → Y=24 (master
    # 2026-05-23 Option 4): opens Y=22-23 routing corridor for U6 config
    # nets. Zero thermal/SI impact — these are static dividers/pulldowns,
    # 0 W dissipation. See: dense-fanout placement-routing co-coupling
    # insight in DECISIONS (placement nudges to enable routing are
    # legitimate within the closure step).
    "R4":  (34.0, 22.0, 0.0),    # EFUSE_ILIM (42.2k to GND) — MOVED 33,24→34,22 per master 2026-05-23 Option (c). Iterations: 32→32.5→34 to clear ILIM via vs OVP B.Cu clearance (was 0.19mm; now 0.21mm PASS).
    "R7":  (35.0, 24.0, 0.0),    # EFUSE_EN UVLO upper (30.1k)
    "R8":  (37.0, 24.0, 0.0),    # EFUSE_EN UVLO lower (10k)
    "R9":  (39.0, 24.0, 0.0),    # EFUSE_OVP upper (51k)
    "R10": (41.0, 24.0, 0.0),    # EFUSE_OVP lower (10k)
    "R13": (43.0, 24.0, 0.0),    # EFUSE_FLT pullup (10k)
    "R5":  (45.0, 24.0, 0.0),    # EFUSE_PGOOD pullup (10k)

    # LDO — KEPT at (24, 25) sweet spot.
    #
    # Iteration log (DO NOT push U2 max-west again, mistake documented):
    #   - (22, 25) on 90×70: MCU +0.9°C — adiabatic-west-edge reflects
    #     heat eastward into MCU.
    #   - (24, 25) on 90×70: MCU +2.1°C — best balance found.
    #   - (24, 25) on 105×85: MCU +6.0°C — the bigger board's extra
    #     north-south space gives the MCU enough surrounding cool board
    #     even without changing U2.
    #   - (15, 22) on 105×85: MCU +4.8°C — RE-MADE the same adiabatic-edge
    #     mistake; U2 too close to adiabatic west edge (15mm) forces heat
    #     east into MCU vicinity. Reverted 2026-05-23.
    #
    # Conclusion: on 105×85 board, U2 at (24, 25) gives both MCU +6°C
    # margin AND U2 itself at +10°C margin. No need to relocate.
    "U2":  (24.0, 25.0, 0.0),    # AP2112K main LDO, 21mm from MCU, 24mm from W edge
    "C31": (28.0, 25.0, 0.0),    # U2 input cap
    "C32": (26.0, 27.0, 90.0),   # U2 output cap (vertical)
    "C33": (22.0, 27.0, 90.0),   # U2 output decap (vertical)
    "C34": (30.0, 27.0, 0.0),    # decap, east of others

    # FERRITE + IMU LDO EAST (along path to D)
    # C77 originally at X=58 collided with U13 pad 5 — moved west to
    # X=56.5 for 1.5mm extra clearance.
    "FB2": (50.0, 27.0, 0.0),    # ferrite, +3V3 → +3V3_IMU_PRE
    "U13": (60.0, 26.0, 0.0),    # LP5907 IMU LDO
    "C77": (56.5, 27.0, 0.0),    # U13 input cap (pre) — moved west
    "C78": (63.0, 27.0, 0.0),    # U13 output cap (+3V3_IMU)
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
                "R4", "R7", "R8", "R9", "R10", "R13", "R5"]:
        if ref in ANCHORS:
            tx, ty, rot = ANCHORS[ref]
            try_place(ref, tx, ty, rot)

    pcbnew.SaveBoard(PCB, brd)
    print(f"\n  Placed {len(placed_B)} of {len(B_REFDES)} B components", flush=True)
    return 0 if len(placed_B) == len(B_REFDES) else 1


if __name__ == "__main__":
    sys.exit(main())
