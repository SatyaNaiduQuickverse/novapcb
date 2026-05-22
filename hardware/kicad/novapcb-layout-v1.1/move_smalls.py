#!/usr/bin/env python3
"""Bring each big block's small parts (caps/Rs/ESD/etc) as a group.

For each small part, find its nearest BIG-BLOCK at the original
positions; translate the small part by the same delta the big block
moved (new - old).

Also re-cut the IMU stress-relief slot: delete the old U-slot,
re-cut around the new S-edge sensor island.
"""
import os, sys, math
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-layout-v1.1.kicad_pcb")

# Big-block (ref, OLD_x, OLD_y, NEW_x, NEW_y, NEW_orient_deg)
# OLD positions are from the original 1e91717 placement; NEW from replace_v2.py
BIG_BLOCKS = [
    ("U1",   41.0, 35.0, 41.0, 35.0, 0),
    # ESC pads
    ("J11",  32.0, 3.0,  10.0, 3.0,  0),
    ("J12",  37.0, 3.0,  15.0, 3.0,  0),
    ("J13",  42.0, 3.0,  20.0, 3.0,  0),
    ("J14",  47.0, 3.0,  25.0, 3.0,  0),
    ("J15",  52.0, 3.0,  60.0, 3.0,  0),
    ("J16",  57.0, 3.0,  65.0, 3.0,  0),
    ("J17",  62.0, 3.0,  70.0, 3.0,  0),
    ("J18",  67.0, 3.0,  75.0, 3.0,  0),
    # microSD + CAN
    ("J2",   20.0, 8.9,  39.0, 15.0, 0),
    ("J20",  84.5, 50.0, 84.0, 8.0,  0),
    ("U14",  82.5, 35.0, 82.0, 18.0, 90),
    ("U15",  87.0, 38.5, 87.0, 19.0, 0),
    # Crystal
    ("Y1",   52.0, 35.0, 30.0, 35.0, 0),
    # Power (kept W block, slight U2 shift)
    ("J4",   4.0, 18.0,  4.0, 18.0,  0),
    ("J19",  4.0, 52.0,  4.0, 52.0,  0),
    ("U11",  15.5, 28.5, 15.5, 28.5, 0),
    ("Q3",   11.0, 28.5, 11.0, 28.5, 0),
    ("U12",  15.5, 47.5, 15.5, 47.5, 0),
    ("Q4",   11.0, 47.5, 11.0, 47.5, 0),
    ("U6",   9.0, 36.5,  9.0, 36.5,  0),
    ("U2",   24.0, 27.5, 22.0, 27.5, 0),
    ("Q2",   10.0, 22.0, 10.0, 22.0, 0),
    ("D1",   16.5, 21.0, 16.5, 21.0, 0),
    # USB / E edge
    ("J1",   39.5, 65.8, 85.0, 30.0, 90),
    ("U5",   32.0, 55.0, 75.0, 26.0, 0),
    ("D11",  20.0, 62.0, 84.0, 20.0, 0),
    ("D12",  28.0, 62.0, 86.0, 20.0, 0),
    ("J3",   24.0, 66.5, 85.0, 50.0, 90),
    ("J10",  74.0, 66.5, 85.0, 60.0, 90),
    ("J5",   55.0, 66.5, 85.0, 40.0, 90),
    # Sensor island
    ("U8",   69.0, 35.0, 50.0, 55.0, 0),
    ("U3",   69.0, 25.0, 35.0, 55.0, 0),
    ("U9",   69.0, 45.0, 42.0, 60.0, 0),
    ("U7",   75.0, 30.0, 56.0, 60.0, 0),
    ("U4",   66.5, 30.0, 30.0, 60.0, 0),
    ("Q5",   65.0, 17.0, 60.0, 55.0, 0),
    ("R61",  71.0, 17.0, 65.0, 55.0, 0),
    ("U13",  69.0, 52.0, 65.0, 60.0, 0),
    ("FB2",  65.5, 52.0, 60.0, 60.0, 0),
    ("FB1",  30.5, 39.5, 30.0, 39.0, 0),
    # SWD
    ("J9",   41.0, 7.0,  41.0, 65.0, 0),
    # ESC ESD diodes
    ("D5",   46.0, 62.0, 10.0, 7.0,  0),
    ("D6",   48.0, 62.0, 15.0, 7.0,  0),
    ("D7",   50.0, 62.0, 20.0, 7.0,  0),
    ("D8",   52.0, 62.0, 25.0, 7.0,  0),
    ("D9",   54.0, 62.0, 60.0, 7.0,  0),
    ("D13",  70.0, 62.0, 70.0, 7.0,  0),
    ("D14",  78.0, 62.0, 75.0, 7.0,  0),
]


def main():
    brd = pcbnew.LoadBoard(PCB)

    # Build big-block-by-ref lookup. Use CURRENT position (post-replace)
    # for each big block — we need delta = NEW - OLD.
    deltas = {}  # ref -> (dx, dy)
    big_old = {}  # ref -> (old_x, old_y)
    for ref, ox, oy, nx, ny, _ in BIG_BLOCKS:
        deltas[ref] = (nx - ox, ny - oy)
        big_old[ref] = (ox, oy)

    # Get all small parts (anything not a big block).
    big_refs = set(b[0] for b in BIG_BLOCKS)
    moved = 0
    skipped = 0
    for fp in brd.GetFootprints():
        ref = fp.GetReference()
        if ref in big_refs: continue
        if ref.startswith("H"): continue  # mounting holes — fixed
        # Find nearest big block at OLD position
        pos = fp.GetPosition()
        x, y = pos.x/1e6, pos.y/1e6
        nearest = None
        nearest_d = float('inf')
        for bref, (ox, oy) in big_old.items():
            d = math.hypot(x - ox, y - oy)
            if d < nearest_d:
                nearest_d = d
                nearest = bref
        # Only move if nearest big block is within 8mm
        if nearest_d > 8.0:
            skipped += 1
            continue
        dx, dy = deltas[nearest]
        if abs(dx) < 0.01 and abs(dy) < 0.01:
            skipped += 1
            continue
        new_pos = pcbnew.VECTOR2I(int((x + dx)*1e6), int((y + dy)*1e6))
        fp.SetPosition(new_pos)
        moved += 1

    print(f"[smalls] moved {moved} small parts; skipped {skipped} (no nearby big block / no delta)")

    # Re-cut IMU stress-relief slot: delete OLD slot, cut NEW around S-edge island
    print(f"[slot] deleting OLD slot, cutting NEW around S-island")
    # Find slot drawings on Edge.Cuts that are NOT the outer board outline
    edge_cuts = []
    for d in brd.GetDrawings():
        if d.GetLayer() == pcbnew.Edge_Cuts:
            edge_cuts.append(d)
    # Outer outline = drawings whose bbox includes near (0,0) or (90,70)
    # Slot = drawings inside the board (centered around old IMU island ~70, 35)
    n_removed = 0
    for d in edge_cuts:
        bb = d.GetBoundingBox()
        x_c = (bb.GetLeft() + bb.GetRight()) / 2 / 1e6
        y_c = (bb.GetTop() + bb.GetBottom()) / 2 / 1e6
        # If centroid is in [55, 85] x [20, 55] (old IMU island), remove
        if 55 < x_c < 85 and 20 < y_c < 55:
            brd.Remove(d)
            n_removed += 1
    print(f"  removed {n_removed} OLD slot segments")

    # Cut NEW slot around new S-edge sensor island
    # New island bbox: U3 (35,55), U8 (50,55), U9 (42,60), U4 (30,60), U7 (56,60),
    # Q5 (60,55), R61 (65,55), U13 (65,60), FB2 (60,60)
    # Island bbox: X 28..70, Y 50..65 — let's use a generous bbox X 27..70, Y 50..65
    # U-slot: cut around the south + east + west of island, keep 10mm bridge on N
    # Slot path: starts at (27, 50) goes west-down-east-up to (70, 50) with a gap
    # for the 10mm bridge.
    # Bridge at X = 40-50 on north side (Y=50). So slot starts at X=27, goes N→S
    # to Y=65, then east to X=70, then north to Y=50. Bridge from 40-50.
    # Actually simpler: slot is a closed-polygon U around the island; bridge in middle of N.
    # Slot poly (CCW):
    #   (27, 50) → (40, 50) [partial north]
    #     skip 50→50 = bridge between X=40 and X=50
    #   (50, 50) → (70, 50) [partial north]
    #   (70, 65) [E side]
    #   (27, 65) [S side]
    #   (27, 50) [W side back to start]
    # That's 6 line segments forming a U with a 10mm bridge at the top.

    SLOT_PTS = [
        (27.0, 50.0), (40.0, 50.0),   # N-west partial
        # ---bridge--- (40,50)..(50,50) NO LINE
        (50.0, 50.0), (70.0, 50.0),   # N-east partial
        (70.0, 65.0),                   # E side
        (27.0, 65.0),                   # S side
        (27.0, 50.0),                   # W side back to start
    ]
    # Add line segments
    # Widened: X=25..72 (gives 3mm clearance from all island components),
    # Y=51..66 (1mm clear of S edge Y=70). 10mm bridge at top (X=40-50).
    SEGMENTS = [
        ((25, 51), (40, 51)),   # N-west partial
        ((50, 51), (72, 51)),   # N-east partial (10mm bridge X=40-50)
        ((72, 51), (72, 66)),   # E side
        ((72, 66), (25, 66)),   # S side
        ((25, 66), (25, 51)),   # W side
    ]
    for (x1, y1), (x2, y2) in SEGMENTS:
        seg = pcbnew.PCB_SHAPE(brd)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetStart(pcbnew.VECTOR2I(int(x1*1e6), int(y1*1e6)))
        seg.SetEnd(pcbnew.VECTOR2I(int(x2*1e6), int(y2*1e6)))
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetWidth(int(0.1*1e6))
        brd.Add(seg)
    print(f"  added {len(SEGMENTS)} new slot segments (5 lines forming U with 10mm bridge at X=40-50)")

    # Refill zones, save
    pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
    pcbnew.SaveBoard(PCB, brd)
    print(f"[save] PCB written")


if __name__ == "__main__":
    main()
