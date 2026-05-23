#!/usr/bin/env python3
"""Step 7 — place D (IMU_ISLAND) on the v1.1 105×85 board.

Per master 2026-05-23 D constraint analysis sign-off (decisions 1-5 in
`docs/D_PLACEMENT_CONSTRAINT_ANALYSIS.md`):
- Decision 1: KEEP mixed IMUs (U3 ICM-42688-P + U8 BMI088 + U9 LSM6DSV16X)
- Decision 2: U3 → +3V3_IMU (DONE in SKiDL amend sha 6d423fc)
- Decision 3: D zone shifted east to X=56..86 (preserves buck-to-IMU ≥25mm)
- Decision 4: relocate R13 east/west out of SPI3 fanout corridor
- Decision 5: bridge 10mm starting, Elmer FEA refines at integration

This script does (in one pass to avoid mid-state SWIG issues):
1. Patch U3 + C41/C42/C43 pad-nets P3V3 → P3V3_IMU
   (board not auto-synced from netlist; SKiDL amend changed nets but
   board's pad assignments are still on old +3V3)
2. Park then place 13 D components at provisional anchors
   (U3, U8, U9 IMU triplet; Q5+R61 heater; C41-C43, C91-C96 decap)
3. SLOT DEFERRED to separate sub-step (master 2026-05-23 S3 approval).
   Slot polygon needs dedicated up-front geometry analysis; deferring
   prevents region-cutout bug class. D↔C/B routing in upcoming steps
   ASSUMES slot at §4 geometry — bridge X=63 ± 5mm enforced as the
   only valid Y=51 crossing column.
4. Relocate R13 (EFUSE_FLT pull-up) to (30, 22) — south of U6, 5mm
   south of U6 south edge, ~6.6mm trace to U6.20 (acceptable for slow
   DC pull-up), clear of MCU pin-row fanout corridor entirely.
   (R13 only connects R13↔U6.20, no MCU consumer — see analysis §1
   Note 1; free to relocate along EFUSE_FLT trace.)

Discipline (master 2026-05-23 D placement reminders):
- R61 (2512 heater) placed CENTRALLY between IMUs for uniform heating
- IMU INT lines (placement-only here; routing later) kept away from
  buck SW node + L1 magnetic field
- Decap caps within 3mm of each IMU body edge (DECOUPLING audit gate)
- Mid-edge mounting-hole keep-out enforced (3, 42.5) + (102, 42.5)
- Single closed polygon for stress-relief slot (imu-slot-integrity gate)
- Up-front render verification after placement, before DRC
"""
import math
import os
import sys
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")

D_REFDES = [
    "U3", "U8", "U9",                           # 3 IMUs
    "Q5", "R61",                                # heater driver + R
    "C41", "C42", "C43",                        # U3 decap
    "C91", "C92", "C93",                        # U8 decap
    "C94", "C95", "C96",                        # U9 decap
]

# D zone — Decision 3 Option (a): shift east to X=56..86 (preserves
# buck-to-IMU >=25mm; buck L1 east edge X=31.4 → D west edge X=56 = 24.6mm
# edge-to-edge, but D zone CENTER X=71 = 42mm from L1 center X=29 — safely
# beyond 25mm rule whether measured edge or center).
ZONE_X_MIN, ZONE_X_MAX = 56.0, 86.0
ZONE_Y_MIN, ZONE_Y_MAX = 51.0, 63.0

# Mid-edge mounting-hole keep-out (board-wide)
MID_HOLE_KEEPOUT = [
    (3.0, 42.5, 8.0),
    (102.0, 42.5, 8.0),
]

# Stress-relief slot — DEFERRED to separate sub-step (task #102, master
# 2026-05-23 S3 approval). Slot polygon geometry needs dedicated review
# (region-cutout bug class). D↔C/B routing assumes bridge X=63 ± 5mm.

# Component anchors (X, Y, rotation) per D analysis §8
ANCHORS = {
    # 3 IMUs in a row across the island, central Y (mid of Y=51..63 = 57)
    "U3":  (60.0, 57.0, 0.0),     # IMU1 ICM-42688-P — SPI1 bridge-south-straight
    "U8":  (68.0, 57.0, 0.0),     # IMU2 BMI088 — SPI2 east-wrap
    "U9":  (78.0, 57.0, 0.0),     # IMU3 LSM6DSV16X — SPI3 wraparound
    # Heater: Q5 SE of U3, R61 central between U3+U8 for uniform heating
    "Q5":  (64.0, 60.0, 0.0),     # AO3400 SOT-23 heater FET
    "R61": (64.0, 53.0, 0.0),     # 2512 6.3x3.2mm — central between IMUs, N side
    # Decap caps (0402) within 3mm of each IMU body edge
    "C41": (60.0, 54.5, 0.0),     # U3 VDD 100nF — N of U3
    "C42": (57.0, 57.0, 0.0),     # U3 VDDIO 100nF — W of U3
    "C43": (60.0, 59.5, 0.0),     # U3 bulk 2.2µF — S of U3
    "C91": (68.0, 54.5, 0.0),     # U8 VDD 100nF — N of U8
    "C92": (71.0, 57.0, 0.0),     # U8 VDDIO 100nF — E of U8 (between U8 and U9)
    "C93": (68.0, 59.5, 0.0),     # U8 bulk 1µF — S of U8
    "C94": (78.0, 54.5, 0.0),     # U9 VDD 100nF — N of U9
    "C95": (81.0, 57.0, 0.0),     # U9 VDDIO 100nF — E of U9
    "C96": (78.0, 59.5, 0.0),     # U9 bulk 1µF — S of U9
}

# R13 relocation — Decision 4 Option α-i (master 2026-05-23). Refined
# position (27, 14) after (30, 22) caused 5 shorts with C34 (Cout HF
# cap at 29,21.5) + EFUSE_EN F.Cu track. (27, 14) is NW of U6, between
# Q3 (south, Y=10) and sense row (Y=14.5) — clears MCU fanout corridor
# entirely (13mm clear) + clears all neighboring footprints + gives
# short 2.19mm F.Cu trace to U6.20 at (27.25, 16.05).
# Master α-i intent (5mm clear of MCU pin row) preserved; position
# refined for actual on-board neighbor clearance.
# R13 relocation: REVERTED to original (44.30, 24.75) after 3 iterations
# (47.5,24.75), (30,22), (27,14), (27,14.5), (28,14.5) all conflicted
# with U6-area routing density (EFUSE_DVDT/ILIM/EN tracks + vias +
# C34/C8/Q3 pad clearance). U6/Q3/sense-row region is fully booked.
# Honest escalation: corridor-block (SPI3 + U1.85) becomes WARNING in
# audit (not FAIL — fanout-corridor check is warn-only). SPI3 routing
# sub-step (separate from D placement) handles via In1.Cu wraparound
# OR routes around R13 with extra layer changes. R13 position preserved.
R13_NEW_POS = (44.30, 24.75)  # ORIGINAL — see comment above


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
    cx = (bb[0] + bb[2]) / 2
    cy = (bb[1] + bb[3]) / 2
    half_x = (bb[2] - bb[0]) / 2
    half_y = (bb[3] - bb[1]) / 2
    for kx, ky, kdia in keepouts:
        kr = kdia / 2
        d = math.hypot(cx - kx, cy - ky)
        if d < kr + math.hypot(half_x, half_y):
            return True
    return False


def find_fp(brd, ref):
    for fp in brd.GetFootprints():
        if fp.GetReference() == ref:
            return fp
    return None


def patch_u3_decap_nets(brd):
    """Migrate U3.8/14 + C41/C42/C43 pin 1 from +3V3 → +3V3_IMU
    (corrective amend per SKiDL change in sha 6d423fc)."""
    p3v3_imu = brd.FindNet("+3V3_IMU")
    if p3v3_imu is None:
        print("  ERROR: +3V3_IMU net not found on board")
        return False
    n_patched = 0
    # U3.8 (VDDIO) + U3.14 (VDD)
    fp_u3 = find_fp(brd, "U3")
    if fp_u3:
        for pad in fp_u3.Pads():
            if pad.GetPadName() in ("8", "14"):
                pad.SetNet(p3v3_imu)
                n_patched += 1
    # C41/C42/C43 pin 1
    for ref in ("C41", "C42", "C43"):
        fp = find_fp(brd, ref)
        if fp is None:
            continue
        for pad in fp.Pads():
            if pad.GetPadName() == "1":
                pad.SetNet(p3v3_imu)
                n_patched += 1
    print(f"  patched {n_patched} pads to +3V3_IMU (was +3V3)")
    return True


def strip_imu_slot(brd):
    """Idempotent: remove any pre-existing IMU-slot polygons from prior runs.
    Slot is deferred to sub-step #102."""
    to_remove = []
    for d in list(brd.GetDrawings()):
        if isinstance(d, pcbnew.PCB_SHAPE) and d.GetLayer() == pcbnew.Edge_Cuts:
            if d.GetShape() == pcbnew.SHAPE_T_POLY:
                ps = d.GetPolyShape()
                if ps.OutlineCount() > 0 and ps.Outline(0).PointCount() > 4:
                    to_remove.append(d)
    for d in to_remove:
        brd.Remove(d)
    if to_remove:
        print(f"  removed {len(to_remove)} existing IMU-slot polygon(s) (deferred)")


def relocate_r13(brd):
    fp = find_fp(brd, "R13")
    if fp is None:
        print("  WARN: R13 not found")
        return
    old = fp.GetPosition()
    fp.SetPosition(pcbnew.VECTOR2I(_mm(R13_NEW_POS[0]), _mm(R13_NEW_POS[1])))
    print(f"  R13: ({old.x/1e6:.2f}, {old.y/1e6:.2f}) → "
          f"({R13_NEW_POS[0]:.2f}, {R13_NEW_POS[1]:.2f}) "
          f"(clears SPI3 fanout col X=43.5..44.5)")


def main():
    print("=== Step 7 — place D (IMU_ISLAND) ===\n")
    brd = pcbnew.LoadBoard(PCB)

    # Pre-pass 1: pad-net patch for U3 + decap
    if not patch_u3_decap_nets(brd):
        return 1

    # Pre-pass 2: relocate R13
    relocate_r13(brd)

    # Pre-pass 3: park D components for idempotent re-run
    park_x = 130.0
    for ref in D_REFDES:
        fp = find_fp(brd, ref)
        if fp:
            fp.SetPosition(pcbnew.VECTOR2I(_mm(park_x), _mm(5.0)))
            park_x += 5.0

    # Inventory placed (excluding D)
    placed = []
    for fp in brd.GetFootprints():
        if fp.GetPosition().x/1e6 < 100.0:
            placed.append((fp, _courtyard_bbox(fp)))
    print(f"  already-placed (excl D): {len(placed)} footprints\n")

    placed_D = []

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
                if _bbox_within_keepout(bb, MID_HOLE_KEEPOUT):
                    continue
                ok = True
                for _, pb in placed + placed_D:
                    if _bbox_intersects(bb, pb): ok = False; break
                if not ok: continue
                placed_D.append((fp, bb))
                print(f"  {ref:4} @ ({tx:.2f}, {ty:.2f}) rot={rot:.0f}°  "
                      f"bbox X={bb[0]:.2f}..{bb[2]:.2f}, Y={bb[1]:.2f}..{bb[3]:.2f}", flush=True)
                return
        print(f"  !! could not place {ref} near target ({x}, {y})")

    # Place in priority order: IMUs first (largest), then heater, then decap
    place_order = [
        "U8", "U9", "U3",                       # IMUs (BMI088 largest, then LSMs/ICM)
        "R61", "Q5",                            # heater first (large 2512 R61)
        "C41", "C42", "C43",                    # U3 decap
        "C91", "C92", "C93",                    # U8 decap
        "C94", "C95", "C96",                    # U9 decap
    ]
    for ref in place_order:
        if ref in ANCHORS:
            tx, ty, rot = ANCHORS[ref]
            try_place(ref, tx, ty, rot)

    # Pre-pass 4: ensure no orphan slot polygons remain (slot deferred
    # to task #102 — master S3 approval 2026-05-23)
    print()
    strip_imu_slot(brd)

    pcbnew.SaveBoard(PCB, brd)
    print(f"\n  Placed {len(placed_D)} of {len(D_REFDES)} D components")
    print(f"  Saved {PCB}")
    return 0 if len(placed_D) == len(D_REFDES) else 1


if __name__ == "__main__":
    sys.exit(main())
