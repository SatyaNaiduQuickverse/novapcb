#!/usr/bin/env python3
"""Park small parts that overlap with big blocks at their NEW positions.

Approach: keep all small parts at their ORIGINAL positions. For each
big block at its NEW position, identify any small part whose footprint
overlaps the big block's footprint. Park those overlapping smalls
in a free area of the board.

This avoids the cascading-conflict issue: smalls that DIDN'T overlap
remain in their (working) original positions; only the genuinely
conflicting smalls move.
"""
import os
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-layout-v1.1.kicad_pcb")

# Big-block NEW positions + bbox-half-dimensions (estimated for clearance)
BIG_BLOCKS_AT_NEW = [
    ("U1", 41, 35, 9, 10),
    ("J11", 10, 3, 1.5, 3), ("J12", 15, 3, 1.5, 3),
    ("J13", 20, 3, 1.5, 3), ("J14", 25, 3, 1.5, 3),
    ("J15", 60, 3, 1.5, 3), ("J16", 65, 3, 1.5, 3),
    ("J17", 70, 3, 1.5, 3), ("J18", 75, 3, 1.5, 3),
    ("J2", 39, 15, 8, 12),
    ("J20", 84, 8, 5, 5), ("U14", 82, 18, 5, 6), ("U15", 87, 19, 1, 1),
    ("Y1", 30, 35, 2, 3),
    ("J4", 4, 18, 3, 5), ("J19", 4, 52, 3, 5),
    ("U11", 15.5, 28.5, 5, 6), ("Q3", 11, 28.5, 2, 2),
    ("U12", 15.5, 47.5, 5, 6), ("Q4", 11, 47.5, 2, 2),
    ("U6", 9, 36.5, 4, 4), ("U2", 22, 27.5, 5, 3),
    ("Q2", 10, 22, 1, 1), ("D1", 16.5, 21, 1, 1),
    ("J1", 85, 30, 6, 5), ("U5", 75, 26, 5, 3),
    ("D11", 84, 20, 1, 1), ("D12", 86, 20, 1, 1),
    ("J3", 85, 50, 6, 4), ("J10", 85, 60, 6, 4), ("J5", 85, 40, 6, 5),
    ("U8", 50, 55, 3, 7), ("U3", 35, 55, 16, 3), ("U9", 42, 60, 5, 6),
    ("U7", 56, 60, 4, 6), ("U4", 30, 60, 3, 4),
    ("Q5", 60, 55, 1.5, 1.5), ("R61", 65, 55, 1, 1),
    ("U13", 65, 60, 6, 6), ("FB2", 60, 60, 1, 1),
    ("FB1", 30, 39, 1, 1),
    ("J9", 41, 65, 6, 2),
    ("D5", 10, 7, 1, 1), ("D6", 15, 7, 1, 1), ("D7", 20, 7, 1, 1),
    ("D8", 25, 7, 1, 1), ("D9", 60, 7, 1, 1),
    ("D13", 70, 7, 1, 1), ("D14", 75, 7, 1, 1),
]


def main():
    brd = pcbnew.LoadBoard(PCB)
    big_refs = {b[0] for b in BIG_BLOCKS_AT_NEW}

    # Identify overlapping smalls
    overlapping = []  # (ref, fp)
    for fp in brd.GetFootprints():
        ref = fp.GetReference()
        if ref in big_refs: continue
        if ref.startswith("H"): continue
        pos = fp.GetPosition()
        x, y = pos.x/1e6, pos.y/1e6
        # Check overlap with any big block (margin 0.5mm)
        for bref, bx, by, hw, hh in BIG_BLOCKS_AT_NEW:
            if abs(x - bx) <= hw + 0.5 and abs(y - by) <= hh + 0.5:
                overlapping.append((ref, fp, bref))
                break

    print(f"[overlap] {len(overlapping)} smalls overlap with big blocks at NEW positions")

    # Park zone: spread across multiple safe areas.
    # 1. SW corner: X=8..22, Y=58..67 (between W power block + slot W edge)
    # 2. SE corner: X=73..86, Y=33..62 — but E edge has connectors. Use Y=22..32 (between CAN and J1).
    # 3. N edge gaps: Y=10..14, X=2..8 (between H1 and J11) or X=30..38 (between J14 and J2)
    park_positions = []
    # SW: 8x4 = 32 slots at 2mm pitch
    for col in [8, 10, 12, 14, 16, 18, 20, 22]:
        for row in [58, 60, 62, 64]:
            park_positions.append((col, row))
    # NE between J20/U14 and J1 USB: X=73..86, Y=22..28 = 14x4 = 56 slots
    for col in [73, 75, 77, 79]:
        for row in [22, 24, 26, 28]:
            park_positions.append((col, row))
    # E-mid between J1 and J5: Y=33..38, X=75..82
    for col in [75, 77, 79, 81]:
        for row in [33, 35, 37]:
            park_positions.append((col, row))
    # SW + NW filler — but careful of mounting hole + slot
    for col in [8, 10, 12, 14, 16, 18, 20, 22]:
        for row in [40, 42, 44]:
            park_positions.append((col, row))

    # Sort overlapping by ref for determinism
    overlapping.sort(key=lambda x: x[0])
    parked = 0
    for i, (ref, fp, bref) in enumerate(overlapping):
        if i >= len(park_positions):
            # Overflow: stack further
            x = 1 + (i % 80) * 1.0
            y = 0.5
        else:
            x, y = park_positions[i]
        fp.SetPosition(pcbnew.VECTOR2I(int(x*1e6), int(y*1e6)))
        parked += 1
    print(f"[parked] {parked} smalls to S-edge park zone")

    pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
    pcbnew.SaveBoard(PCB, brd)
    print(f"[save] PCB written")


if __name__ == "__main__":
    main()
