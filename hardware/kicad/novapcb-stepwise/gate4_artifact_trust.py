#!/usr/bin/env python3
"""Gate 4 — artifact-trust audit.

Per docs/PLACEMENT_ROUTING_GATES.md §Gate 4:

  "Trust the ARTIFACT, not the tool exit code — grep the actual
   .kicad_pcb; do not trust place_board.py "0 unplaced" / verify
   "0 overlaps" alone."

This script COMPUTES placement metrics by parsing the .kicad_pcb
artifact directly (no reliance on step1_place_C.py's exit messages).
Run after step1_place_C.py to verify what's actually in the board.

Reports:
  - board outline (Edge.Cuts rectangle dimensions)
  - mounting hole count + positions
  - on-board footprints (X < 100 mm) — refdes, count
  - off-board parked footprints (X >= 110 mm) — count only
  - any footprint in the "no-mans-land" 100 <= X < 110

Exit 0 always; this is informational. The PR description quotes its
output verbatim as Gate-4 evidence.
"""
import os
import sys
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")
PARK_MIN_X = 110.0
ON_BOARD_MAX_X = 100.0


def main():
    brd = pcbnew.LoadBoard(PCB)
    print(f"=== Gate 4 — artifact audit on {os.path.basename(PCB)} ===\n", flush=True)

    # Board outline (parse Edge.Cuts shapes)
    edges = [d for d in brd.GetDrawings()
              if isinstance(d, pcbnew.PCB_SHAPE) and d.GetLayer() == pcbnew.Edge_Cuts]
    if edges:
        x_min = y_min = float("inf")
        x_max = y_max = float("-inf")
        for e in edges:
            b = e.GetBoundingBox()
            x0, y0 = b.GetX()/1e6, b.GetY()/1e6
            x1, y1 = x0 + b.GetWidth()/1e6, y0 + b.GetHeight()/1e6
            x_min, y_min = min(x_min, x0), min(y_min, y0)
            x_max, y_max = max(x_max, x1), max(y_max, y1)
        print(f"board outline: {len(edges)} Edge.Cuts shape(s); "
              f"bbox {x_min:.1f}..{x_max:.1f} × {y_min:.1f}..{y_max:.1f} mm "
              f"({x_max-x_min:.1f} × {y_max-y_min:.1f})", flush=True)
    else:
        print("board outline: MISSING Edge.Cuts geometry", flush=True)

    # Mounting holes (NPTH pads with no copper layer set)
    holes = []
    for fp in brd.GetFootprints():
        ref = fp.GetReference()
        if ref.startswith("H"):
            p = fp.GetPosition()
            holes.append((ref, p.x/1e6, p.y/1e6))
    holes.sort()
    print(f"\nmounting holes: {len(holes)}", flush=True)
    for ref, x, y in holes:
        print(f"  {ref} @ ({x:.2f}, {y:.2f}) mm", flush=True)

    # Footprint placement audit
    on_board = []
    parked = []
    limbo = []
    for fp in brd.GetFootprints():
        ref = fp.GetReference()
        if ref.startswith("H"):
            continue
        p = fp.GetPosition()
        x = p.x / 1e6
        y = p.y / 1e6
        if x < ON_BOARD_MAX_X:
            on_board.append((ref, x, y))
        elif x >= PARK_MIN_X:
            parked.append((ref, x, y))
        else:
            limbo.append((ref, x, y))

    print(f"\non-board footprints (X < {ON_BOARD_MAX_X} mm): {len(on_board)}", flush=True)
    for ref, x, y in sorted(on_board):
        print(f"  {ref:6} @ ({x:6.2f}, {y:6.2f}) mm", flush=True)

    print(f"\noff-board parked (X >= {PARK_MIN_X} mm): {len(parked)} footprints", flush=True)
    if limbo:
        print(f"\n!! WARN: {len(limbo)} footprint(s) in limbo "
              f"({ON_BOARD_MAX_X} <= X < {PARK_MIN_X}):", flush=True)
        for ref, x, y in limbo:
            print(f"   {ref} @ ({x:.2f}, {y:.2f})", flush=True)

    # Counts
    total = len(on_board) + len(parked) + len(limbo)
    print(f"\ntotal non-H footprints: {total}", flush=True)
    print(f"tracks/vias on board: {len(list(brd.GetTracks()))} "
          f"(expected 0 — routing is a later phase)", flush=True)
    print(f"zones on board:        {len(list(brd.Zones()))} "
          f"(expected 0 — planes added cross-subsystem)", flush=True)


if __name__ == "__main__":
    sys.exit(main())
