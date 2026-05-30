#!/usr/bin/env python3
"""T17 silkscreen reposition — reduce silk_overlap warnings.

Problem: 159 silk_overlap warnings from audit_layout_compliance — refdes labels
overlap pads/courtyards. Cosmetic but assembly QC + service legibility hit.

Strategy:
  1. For each footprint, get pad bounding box on this footprint's layer.
  2. Get refdes text current position.
  3. If refdes overlaps any pad of this footprint OR overlaps adjacent footprint's
     courtyard, try repositioning to one of 8 candidate positions:
       N=above, S=below, E=right, W=left, then NE/NW/SE/SW corners.
     Each tested at refdes_text_height + 0.5mm offset from footprint courtyard edge.
  4. First overlap-free position wins.
  5. Refdes that can't fit anywhere (rare — only super-dense clusters) — hide
     (set visible=False) per IPC-7351 acceptable practice for assembly-aided
     boards with CPL file. Log these.

Tool: pcbnew Python API (KiCad 9). Run on worker (novatics64).

Usage:
  python3 scripts/silk_reposition.py hardware/kicad/novapcb-stepwise/novapcb-stepwise.kicad_pcb

Output:
  - Modifies the .kicad_pcb file in-place (worker reviews diff in GUI before commit)
  - Prints summary: N labels moved, N hidden, N unchanged
  - Re-run audit_layout_compliance afterward to confirm silk_overlap drop

NOTE: this is a cosmetic-only fix. NO copper / route / pad / via touched. Strictly
silk-layer F.SilkS / B.SilkS Reference text properties.
"""
import sys
import pcbnew
from pathlib import Path

if len(sys.argv) < 2:
    sys.exit("usage: silk_reposition.py <board.kicad_pcb>")

board_path = Path(sys.argv[1])
board = pcbnew.LoadBoard(str(board_path))

REFDES_OFFSET_MM = 0.5  # offset from footprint courtyard edge
CANDIDATES = [  # (dx, dy) offsets from footprint center, in mm
    (0, -1),    # N (above)
    (0, +1),    # S (below)
    (+1, 0),    # E (right)
    (-1, 0),    # W (left)
    (+1, -1),   # NE
    (-1, -1),   # NW
    (+1, +1),   # SE
    (-1, +1),   # SW
]

moved = 0
hidden = 0
unchanged = 0
unfittable = []

def rect_overlap(a, b):
    """Return True if KICad BOX2I rectangles a and b intersect."""
    return not (a.GetRight() < b.GetLeft() or b.GetRight() < a.GetLeft() or
                a.GetBottom() < b.GetTop() or b.GetBottom() < a.GetTop())


for fp in board.GetFootprints():
    ref_text = fp.Reference()
    if not ref_text.IsVisible():
        continue
    ref_bbox = ref_text.GetBoundingBox()

    # Build list of obstacles: this footprint's own pads + adjacent footprints' courtyards
    obstacles = []
    for pad in fp.Pads():
        obstacles.append(pad.GetBoundingBox())
    fp_pos = fp.GetPosition()
    for other in board.GetFootprints():
        if other is fp:
            continue
        other_pos = other.GetPosition()
        # Only check footprints within ~15mm (skip distant)
        dx = (other_pos.x - fp_pos.x) / 1e6
        dy = (other_pos.y - fp_pos.y) / 1e6
        if (dx*dx + dy*dy) > 225:  # 15mm radius
            continue
        obstacles.append(other.GetBoundingBox())

    # Test current position
    overlap_now = any(rect_overlap(ref_bbox, ob) for ob in obstacles)
    if not overlap_now:
        unchanged += 1
        continue

    # Try candidates — each puts refdes center at (fp_pos + dx * (fp_width/2 + offset), ...)
    fp_bbox = fp.GetBoundingBox()
    fp_w_mm = (fp_bbox.GetWidth()) / 1e6
    fp_h_mm = (fp_bbox.GetHeight()) / 1e6
    ref_h_mm = ref_bbox.GetHeight() / 1e6
    placed = False

    for dx, dy in CANDIDATES:
        # Compute candidate refdes center position
        offset_x_mm = dx * (fp_w_mm / 2 + REFDES_OFFSET_MM + ref_bbox.GetWidth()/2/1e6)
        offset_y_mm = dy * (fp_h_mm / 2 + REFDES_OFFSET_MM + ref_h_mm/2)
        new_x = int(fp_pos.x + offset_x_mm * 1e6)
        new_y = int(fp_pos.y + offset_y_mm * 1e6)
        ref_text.SetPosition(pcbnew.VECTOR2I(new_x, new_y))
        new_bbox = ref_text.GetBoundingBox()
        if not any(rect_overlap(new_bbox, ob) for ob in obstacles):
            moved += 1
            placed = True
            break

    if not placed:
        # Last resort: hide (visible=False); CPL+silk-on-courtyard typically OK
        ref_text.SetVisible(False)
        hidden += 1
        unfittable.append(fp.GetReference())

board.Save(str(board_path))

print(f"Silk reposition complete:")
print(f"  Moved: {moved}")
print(f"  Hidden: {hidden}  (unfittable refdes — assembly relies on CPL)")
print(f"  Unchanged (already clean): {unchanged}")
if unfittable:
    print(f"  Hidden refdes list: {', '.join(unfittable[:20])}")
print()
print(f"NEXT: re-run scripts/audit_layout_compliance.py to confirm silk_overlap drop")
print(f"      open pcbnew GUI for visual sanity check before commit")
