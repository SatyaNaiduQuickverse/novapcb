#!/usr/bin/env python3
"""Update novapcb-stepwise.kicad_pcb to v1.1 105×85 mm outline.

Per master 2026-05-23 sign-off after gate12 v3 sweep:
  - Old: 90×70 mm, mounting holes H1-H4 at corners with 5mm inset
    (80×60 c-to-c) — undersized per gate12 v3 + rigorous powers
  - New: 105×85 mm, mounting holes at 3mm inset (99×79 c-to-c)
    — smallest size meeting ≥5°C MCU margin

Mid-edge mounting hole keep-outs (sim-gated +2 holes) scale to:
  - Old: (3, 35) west mid + (87, 35) east mid (h=8mm)
  - New: (3, 42.5) west mid + (102, 42.5) east mid (h=8mm)

Run from hardware/kicad/novapcb-stepwise/:
  python3 update_outline_v11.py
"""
import os
import sys
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")

OLD_BOARD = (90, 70)
NEW_BOARD = (105, 85)
HOLE_INSET = 3.0     # 3mm from each edge
HOLE_C2C_X = NEW_BOARD[0] - 2 * HOLE_INSET   # 99 mm
HOLE_C2C_Y = NEW_BOARD[1] - 2 * HOLE_INSET   # 79 mm


def _mm(x):
    return pcbnew.FromMM(x)


def main():
    print(f"=== Update board outline 90×70 → 105×85 ===\n")
    brd = pcbnew.LoadBoard(PCB)

    # 1. Find + update edge cuts rectangle
    edge_updated = 0
    for d in brd.GetDrawings():
        if d.GetLayer() != pcbnew.Edge_Cuts:
            continue
        if isinstance(d, pcbnew.PCB_SHAPE):
            shape = d.GetShape()
            if shape == pcbnew.SHAPE_T_RECT:
                start = d.GetStart()
                end = d.GetEnd()
                # Set to (0,0) → (105, 85)
                d.SetStart(pcbnew.VECTOR2I(_mm(0.0), _mm(0.0)))
                d.SetEnd(pcbnew.VECTOR2I(_mm(NEW_BOARD[0]), _mm(NEW_BOARD[1])))
                edge_updated += 1
                print(f"  edge cut rect: ({start.x/1e6:.1f},{start.y/1e6:.1f}) → "
                      f"({end.x/1e6:.1f},{end.y/1e6:.1f})  "
                      f"updated to (0,0)→({NEW_BOARD[0]},{NEW_BOARD[1]})")
    print(f"  → {edge_updated} edge-cuts rect updated\n")

    # 2. Update mounting holes
    HOLE_POSITIONS = {
        "H1": (HOLE_INSET, HOLE_INSET),                       # SW
        "H2": (NEW_BOARD[0] - HOLE_INSET, HOLE_INSET),        # SE
        "H3": (HOLE_INSET, NEW_BOARD[1] - HOLE_INSET),        # NW
        "H4": (NEW_BOARD[0] - HOLE_INSET, NEW_BOARD[1] - HOLE_INSET),  # NE
    }
    for fp in brd.GetFootprints():
        ref = fp.GetReference()
        if ref in HOLE_POSITIONS:
            old = fp.GetPosition()
            new_x, new_y = HOLE_POSITIONS[ref]
            fp.SetPosition(pcbnew.VECTOR2I(_mm(new_x), _mm(new_y)))
            print(f"  {ref}: ({old.x/1e6:.1f},{old.y/1e6:.1f}) → "
                  f"({new_x:.1f},{new_y:.1f})")

    # 3. Save
    pcbnew.SaveBoard(PCB, brd)
    print(f"\n  Saved {PCB}")
    print(f"\n  v1.1 outline: 105 × 85 mm")
    print(f"  Mounting holes c-to-c: {HOLE_C2C_X} × {HOLE_C2C_Y} mm "
          f"({HOLE_INSET} mm inset)")
    print(f"  Mid-edge keep-outs (sim-gated +2): (3, 42.5) + (102, 42.5), 8mm")
    return 0


if __name__ == "__main__":
    sys.exit(main())
