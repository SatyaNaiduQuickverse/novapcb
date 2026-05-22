#!/usr/bin/env python3
"""Gate 8 — multi-resolution routing density.

Per docs/PLACEMENT_ROUTING_GATES.md §Gate 8:

  "Every routing PR must report routing density at three resolutions:
   whole-board, 4-quadrant, per-cluster. All three must pass the 0.85
   threshold."

Density definition (Wenwen Liu, 2018; ApolloFC team adaptation):
  per-cell density = (total copper area in cell) / (cell area)

A cell with copper covering >85% of its area is considered "over-dense"
— additional routes through that area will be high-conflict.

For an empty (placement-only) board, the density is near zero except in
small pockets where footprints sit. For the C+E placement + just I2C2
tracks at Step 2 integration, density is expected to be very low.

Gate 8 acceptance: every cell at every resolution ≤ 0.85.
"""
import os
import sys
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")
BOARD_W_MM = 90.0
BOARD_H_MM = 70.0
DENSITY_THRESHOLD = 0.85
CLUSTER_CELL_MM = 5.0    # 5mm-square per-cluster cells (18 × 14 = 252 cells)


def _bbox_area(bb):
    """area in mm² for a (x0, y0, x1, y1) tuple."""
    return max(0.0, bb[2]-bb[0]) * max(0.0, bb[3]-bb[1])


def _intersect_area(a, b):
    if not (a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]):
        return 0.0
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    return max(0.0, w) * max(0.0, h)


def collect_copper_bboxes(brd):
    """Return list of (x0, y0, x1, y1) bboxes of all copper items
    (footprint pads + tracks). Vias are treated as a small circle bbox.
    """
    boxes = []
    # Pad copper
    for fp in brd.GetFootprints():
        for pad in fp.Pads():
            b = pad.GetBoundingBox()
            boxes.append((b.GetX()/1e6, b.GetY()/1e6,
                          (b.GetX()+b.GetWidth())/1e6, (b.GetY()+b.GetHeight())/1e6))
    # Tracks
    for t in brd.GetTracks():
        if isinstance(t, pcbnew.PCB_VIA):
            r = t.GetWidth() / 2 / 1e6
            cx = t.GetPosition().x / 1e6
            cy = t.GetPosition().y / 1e6
            boxes.append((cx-r, cy-r, cx+r, cy+r))
        else:
            # PCB_TRACK: from start to end with width
            s = t.GetStart(); e = t.GetEnd()
            w = t.GetWidth() / 1e6
            x0 = min(s.x, e.x) / 1e6 - w/2
            y0 = min(s.y, e.y) / 1e6 - w/2
            x1 = max(s.x, e.x) / 1e6 + w/2
            y1 = max(s.y, e.y) / 1e6 + w/2
            boxes.append((x0, y0, x1, y1))
    return boxes


def density_grid(boxes, cell_mm):
    """Return 2D list density[j][i] = fraction copper in cell (i, j)."""
    nx = int(BOARD_W_MM / cell_mm)
    ny = int(BOARD_H_MM / cell_mm)
    cell_area = cell_mm * cell_mm
    grid = [[0.0]*nx for _ in range(ny)]
    for bb in boxes:
        ix0 = max(0, int(bb[0] / cell_mm))
        iy0 = max(0, int(bb[1] / cell_mm))
        ix1 = min(nx-1, int(bb[2] / cell_mm))
        iy1 = min(ny-1, int(bb[3] / cell_mm))
        for j in range(iy0, iy1+1):
            for i in range(ix0, ix1+1):
                cx0 = i * cell_mm
                cy0 = j * cell_mm
                cb = (cx0, cy0, cx0+cell_mm, cy0+cell_mm)
                a = _intersect_area(bb, cb)
                grid[j][i] += a / cell_area
    # Clip at 1.0 (in case overlapping boxes total > 1.0)
    for j in range(ny):
        for i in range(nx):
            grid[j][i] = min(1.0, grid[j][i])
    return grid


def main():
    print("=== Gate 8 — multi-resolution density ===\n", flush=True)
    brd = pcbnew.LoadBoard(PCB)
    boxes = collect_copper_bboxes(brd)
    total_copper = sum(_bbox_area(bb) for bb in boxes)
    total_board = BOARD_W_MM * BOARD_H_MM
    print(f"copper items: {len(boxes)}", flush=True)

    # Whole-board: single scalar
    whole = total_copper / total_board
    print(f"\n[1/3] Whole-board density: {whole:.4f}  (threshold {DENSITY_THRESHOLD})", flush=True)
    print(f"        {'GREEN' if whole < DENSITY_THRESHOLD else 'RED'}", flush=True)

    # 4-quadrant
    print(f"\n[2/3] 4-quadrant density:", flush=True)
    cell_q = max(BOARD_W_MM, BOARD_H_MM) / 2
    cell_q_x = BOARD_W_MM / 2
    cell_q_y = BOARD_H_MM / 2
    q_area = cell_q_x * cell_q_y
    quadrants = {}
    for j in range(2):
        for i in range(2):
            qb = (i*cell_q_x, j*cell_q_y, (i+1)*cell_q_x, (j+1)*cell_q_y)
            qcopper = sum(_intersect_area(bb, qb) for bb in boxes)
            quadrants[(i,j)] = qcopper / q_area
            label = ['NW','NE','SW','SE'][2*j + i]
            print(f"  {label}: {quadrants[(i,j)]:.4f}", flush=True)
    q_max = max(quadrants.values())
    print(f"  worst: {q_max:.4f}  {'GREEN' if q_max < DENSITY_THRESHOLD else 'RED'}", flush=True)

    # Per-cluster (5mm cells = 18×14 = 252 cells)
    print(f"\n[3/3] Per-cluster density (cell {CLUSTER_CELL_MM}mm = {int(BOARD_W_MM/CLUSTER_CELL_MM)}×{int(BOARD_H_MM/CLUSTER_CELL_MM)} grid):", flush=True)
    grid = density_grid(boxes, CLUSTER_CELL_MM)
    max_density = 0.0
    max_pos = (0, 0)
    over_count = 0
    for j in range(len(grid)):
        for i in range(len(grid[0])):
            d = grid[j][i]
            if d > max_density:
                max_density, max_pos = d, (i, j)
            if d >= DENSITY_THRESHOLD:
                over_count += 1
    print(f"  worst cell: ({max_pos[0]*CLUSTER_CELL_MM:.0f}, {max_pos[1]*CLUSTER_CELL_MM:.0f}) density {max_density:.4f}", flush=True)
    print(f"  cells over threshold: {over_count}", flush=True)
    print(f"  {'GREEN' if max_density < DENSITY_THRESHOLD else 'RED'}", flush=True)

    overall_green = (whole < DENSITY_THRESHOLD and q_max < DENSITY_THRESHOLD
                     and max_density < DENSITY_THRESHOLD)
    print(f"\nGate 8: {'GREEN' if overall_green else 'RED'}", flush=True)
    return 0 if overall_green else 1


if __name__ == "__main__":
    sys.exit(main())
