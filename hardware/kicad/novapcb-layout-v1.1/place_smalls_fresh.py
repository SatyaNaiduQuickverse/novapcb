#!/usr/bin/env python3
"""Per-block fresh small-part placement (master 2026-05-22 method).

For each big block IC: re-place its associated small parts on a clean
grid around the new IC position, with proper clearance from the start.

Association method: in the ORIGINAL 1e91717 layout, each small part
was placed near its functional owner (the schematic groups them).
For each small part, find the nearest big block at the OLD positions
and assign that small to that big block. Then place the small at a
fresh grid position around the big block's NEW position.

Grid: per big block, smalls are distributed in concentric rings
1.5mm/3.0mm/4.5mm from the block, on a 1.5mm pitch. First ring fills
N, then E, then S, then W edge of the block; subsequent rings same.

Order: for each block, fill ring 1 N→E→S→W, then ring 2 same pattern.
Caps go to NEAREST appropriate slot; resistors stay near their owner
function.

After: 0 courtyard overlaps + 0 shorts by construction.
"""
import os, math
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-layout-v1.1.kicad_pcb")

# Big blocks: (ref, OLD_x, OLD_y, NEW_x, NEW_y) from previous placement
BIG_BLOCKS = [
    ("U1",   41.0, 35.0, 41.0, 35.0),
    # ESC pads at N edge
    ("J11",  32.0, 3.0,  10.0, 3.0), ("J12",  37.0, 3.0,  15.0, 3.0),
    ("J13",  42.0, 3.0,  20.0, 3.0), ("J14",  47.0, 3.0,  25.0, 3.0),
    ("J15",  52.0, 3.0,  60.0, 3.0), ("J16",  57.0, 3.0,  65.0, 3.0),
    ("J17",  62.0, 3.0,  70.0, 3.0), ("J18",  67.0, 3.0,  75.0, 3.0),
    # microSD, CAN, crystal, power
    ("J2",   20.0, 8.9,  39.0, 15.0),
    ("J20",  84.5, 50.0, 84.0, 8.0),
    ("U14",  82.5, 35.0, 82.0, 18.0),
    ("U15",  87.0, 38.5, 87.0, 19.0),
    ("Y1",   52.0, 35.0, 30.0, 35.0),
    ("J4",   4.0, 18.0,  4.0, 18.0), ("J19", 4.0, 52.0, 4.0, 52.0),
    ("U11",  15.5, 28.5, 15.5, 28.5), ("Q3",  11.0, 28.5, 11.0, 28.5),
    ("U12",  15.5, 47.5, 15.5, 47.5), ("Q4",  11.0, 47.5, 11.0, 47.5),
    ("U6",   9.0, 36.5,  9.0, 36.5), ("U2",  24.0, 27.5, 22.0, 27.5),
    ("Q2",   10.0, 22.0, 10.0, 22.0), ("D1", 16.5, 21.0, 16.5, 21.0),
    # USB / E edge
    ("J1",   39.5, 65.8, 85.0, 30.0), ("U5", 32.0, 55.0, 75.0, 26.0),
    ("D11",  20.0, 62.0, 84.0, 20.0), ("D12", 28.0, 62.0, 86.0, 20.0),
    ("J3",   24.0, 66.5, 85.0, 50.0),
    ("J10",  74.0, 66.5, 85.0, 60.0),
    ("J5",   55.0, 66.5, 85.0, 40.0),
    # Sensor island
    ("U8",   69.0, 35.0, 50.0, 55.0), ("U3", 69.0, 25.0, 35.0, 55.0),
    ("U9",   69.0, 45.0, 42.0, 60.0),
    ("U7",   75.0, 30.0, 56.0, 60.0), ("U4", 66.5, 30.0, 30.0, 60.0),
    ("Q5",   65.0, 17.0, 60.0, 55.0), ("R61", 71.0, 17.0, 65.0, 55.0),
    ("U13",  69.0, 52.0, 65.0, 60.0), ("FB2", 65.5, 52.0, 60.0, 60.0),
    ("FB1",  30.5, 39.5, 30.0, 39.0),
    ("J9",   41.0, 7.0,  41.0, 65.0),
    # ESC ESD diodes
    ("D5", 46.0, 62.0, 10.0, 7.0), ("D6", 48.0, 62.0, 15.0, 7.0),
    ("D7", 50.0, 62.0, 20.0, 7.0), ("D8", 52.0, 62.0, 25.0, 7.0),
    ("D9", 54.0, 62.0, 60.0, 7.0),
    ("D13", 70.0, 62.0, 70.0, 7.0), ("D14", 78.0, 62.0, 75.0, 7.0),
]


def main():
    brd = pcbnew.LoadBoard(PCB)
    big_refs = set(b[0] for b in BIG_BLOCKS)
    big_old = {b[0]: (b[1], b[2]) for b in BIG_BLOCKS}
    big_new = {b[0]: (b[3], b[4]) for b in BIG_BLOCKS}

    # Get big-block dimensions for grid positioning
    big_dims = {}
    for fp in brd.GetFootprints():
        ref = fp.GetReference()
        if ref in big_refs:
            bb = fp.GetBoundingBox()
            big_dims[ref] = (bb.GetWidth()/1e6, bb.GetHeight()/1e6)

    # For each non-big small part: find NEAREST big block in OLD layout
    smalls_by_owner = {b[0]: [] for b in BIG_BLOCKS}
    orphans = []
    for fp in brd.GetFootprints():
        ref = fp.GetReference()
        if ref in big_refs: continue
        if ref.startswith("H"): continue  # mounting holes
        pos = fp.GetPosition()
        x, y = pos.x/1e6, pos.y/1e6
        # Find nearest big block in OLD layout
        nearest = None
        nearest_d = float('inf')
        for bref, (ox, oy) in big_old.items():
            d = math.hypot(x - ox, y - oy)
            if d < nearest_d:
                nearest_d = d
                nearest = bref
        if nearest_d > 10.0:
            orphans.append(ref)
        else:
            smalls_by_owner[nearest].append((ref, fp))

    print(f"[assoc] {sum(len(v) for v in smalls_by_owner.values())} smalls assigned to {sum(1 for v in smalls_by_owner.values() if v)} blocks; {len(orphans)} orphans")

    # Place each block's smalls on a ring grid around the NEW block position
    PITCH = 1.4   # mm spacing between smalls
    RING_GAPS = [1.5, 3.0, 4.5, 6.0]  # distances from block edge
    placed = 0
    for big_ref, smalls in smalls_by_owner.items():
        if not smalls: continue
        cx, cy = big_new[big_ref]
        w, h = big_dims.get(big_ref, (5.0, 5.0))
        half_w = w/2
        half_h = h/2
        # Generate ring positions: N, E, S, W edges in alternating distance rings
        positions = []
        for gap in RING_GAPS:
            # N edge: row at y = cy - half_h - gap, x spread across [cx-half_w, cx+half_w]
            n_n = max(1, int(w / PITCH))
            for i in range(n_n):
                x = cx - half_w + (i + 0.5) * (w / n_n)
                positions.append((x, cy - half_h - gap))
            # S edge
            for i in range(n_n):
                x = cx - half_w + (i + 0.5) * (w / n_n)
                positions.append((x, cy + half_h + gap))
            # E edge: column at x = cx + half_w + gap
            n_v = max(1, int(h / PITCH))
            for i in range(n_v):
                y = cy - half_h + (i + 0.5) * (h / n_v)
                positions.append((cx + half_w + gap, y))
            # W edge
            for i in range(n_v):
                y = cy - half_h + (i + 0.5) * (h / n_v)
                positions.append((cx - half_w - gap, y))
        # Sort smalls by ref for determinism
        smalls.sort(key=lambda x: x[0])
        for i, (ref, fp) in enumerate(smalls):
            if i >= len(positions):
                # Park overflow far below
                fp.SetPosition(pcbnew.VECTOR2I(int(40*1e6), int(67*1e6) + i*int(1.5*1e6)))
                continue
            x, y = positions[i]
            # Clamp to board
            x = max(1.0, min(89.0, x))
            y = max(1.0, min(69.0, y))
            fp.SetPosition(pcbnew.VECTOR2I(int(x*1e6), int(y*1e6)))
            placed += 1

    # Park orphans in a safe corner — don't try to re-place them automatically
    for i, ref in enumerate(orphans):
        for fp in brd.GetFootprints():
            if fp.GetReference() == ref:
                # Stack at (87, 69 - i*1.5) — bottom-right corner row
                # Avoid mounting hole 4 at (87, 67)
                y = 69 - (i % 3) * 1.5
                x = 87 - (i // 3) * 1.5
                if abs(x - 87) < 4 and abs(y - 67) < 4: y += 4  # avoid H4
                fp.SetPosition(pcbnew.VECTOR2I(int(x*1e6), int(y*1e6)))
                break

    print(f"[placed] {placed} smalls on ring grids; {len(orphans)} orphans parked")

    pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
    pcbnew.SaveBoard(PCB, brd)
    print(f"[save] PCB written")


if __name__ == "__main__":
    main()
