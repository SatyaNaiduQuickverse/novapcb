#!/usr/bin/env python3
"""Gate 1 — bbox-overlap (component-courtyard) check.

Per docs/PLACEMENT_ROUTING_GATES.md §Gate 1:

  "Every PR that places or moves a component runs a body-intersection
   check using pcbnew.BOX2I::Intersects() on the footprint courtyard
   (not just pad-collision). Two parts whose pads don't touch but
   whose bodies overlap is still a fab-blocker — the pick-and-place
   head can't physically place a part on top of another, and the
   design will be rejected at DFM."

  "Self-test requirement. The verifier must be run against a known-bad
   input (two parts deliberately overlapped) BEFORE running it on the
   real PR — to prove the verifier can fail. A green verifier that
   has never failed is unfalsifiable. The PR description must show
   the self-test output."

This script runs in two modes:

  - SELF-TEST (--selftest): copies the board, deliberately moves two
    footprints (R1 and R2) on top of each other, runs the verifier
    on the deliberately-bad input. Must REPORT a violation (red).
  - REAL (default): runs on the actual novapcb-stepwise.kicad_pcb.
    Must report ZERO violations (green).

The verifier checks the COURTYARD bounding box (BOX2I) of each
on-board footprint pair using BOX2I::Intersects(). Off-board parked
footprints (X >= 110 mm) are excluded — they will be repositioned in
future Step-N PRs and aren't physically present on the board yet.

Exit code 0 = green, exit code 1 = violation found, exit code 2 = error.
"""
import os
import sys
import shutil
import argparse
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")
PARK_X_THRESHOLD_MM = 100.0   # any X >= this is "parked", excluded from check


def courtyard_bbox(fp: pcbnew.FOOTPRINT):
    """Return the union bbox of the footprint's F.CrtYd + B.CrtYd shapes
    as a tuple (x0, y0, x1, y1) in mm. Falls back to footprint full bbox
    if no courtyard is defined. Avoids BOX2I.Merge() — KiCad-9 returns
    references that interact badly with PCB_SHAPE-owned bboxes when the
    loop pattern `bbox = bbox.Merge(b)` is used. Compute min/max scalars
    instead.
    """
    ctyd_layers = (pcbnew.F_CrtYd, pcbnew.B_CrtYd)
    x0 = y0 = float("inf")
    x1 = y1 = float("-inf")
    found = False
    for d in fp.GraphicalItems():
        if not isinstance(d, pcbnew.PCB_SHAPE): continue
        if d.GetLayer() not in ctyd_layers: continue
        b = d.GetBoundingBox()
        bx0 = b.GetX() / 1e6
        by0 = b.GetY() / 1e6
        bx1 = bx0 + b.GetWidth() / 1e6
        by1 = by0 + b.GetHeight() / 1e6
        x0, y0 = min(x0, bx0), min(y0, by0)
        x1, y1 = max(x1, bx1), max(y1, by1)
        found = True
    if not found:
        b = fp.GetBoundingBox()
        x0 = b.GetX() / 1e6
        y0 = b.GetY() / 1e6
        x1 = x0 + b.GetWidth() / 1e6
        y1 = y0 + b.GetHeight() / 1e6
    return (x0, y0, x1, y1)


def bbox_intersects(a, b):
    """Tuple-bbox intersect test. (x0, y0, x1, y1) each."""
    return not (a[2] <= b[0] or a[0] >= b[2] or a[3] <= b[1] or a[1] >= b[3])


def bbox_intersect_area(a, b):
    """Area of overlap in mm² (zero if disjoint)."""
    if not bbox_intersects(a, b): return 0.0
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    return max(0.0, w) * max(0.0, h)


def on_board(fp: pcbnew.FOOTPRINT, max_x_mm: float = PARK_X_THRESHOLD_MM) -> bool:
    return fp.GetPosition().x / 1e6 < max_x_mm


def check_overlaps_brd(brd: pcbnew.BOARD):
    """Run the verifier on a loaded board (in-memory). Returns
    (violations, n_on_board)."""
    on_board_fps = [(fp, courtyard_bbox(fp)) for fp in brd.GetFootprints()
                     if on_board(fp)]
    violations = []
    for i in range(len(on_board_fps)):
        fp_a, b_a = on_board_fps[i]
        for j in range(i + 1, len(on_board_fps)):
            fp_b, b_b = on_board_fps[j]
            if bbox_intersects(b_a, b_b):
                ra = fp_a.GetReference()
                rb = fp_b.GetReference()
                area = bbox_intersect_area(b_a, b_b)
                violations.append((ra, rb, area))
    return violations, len(on_board_fps)


def check_overlaps(pcb_path: str):
    """Return list of (ref_a, ref_b, area) tuples; courtyards intersect."""
    brd = pcbnew.LoadBoard(pcb_path)
    return check_overlaps_brd(brd)


def self_test():
    """Self-test: load the real board, deliberately move R1 ON TOP OF U1
    IN MEMORY, run the verifier on that in-memory board. Must REPORT
    an R1/U1 overlap. Does not save the modified board."""
    print("=== SELF-TEST: deliberately overlap R1 on top of U1 (in memory) ===", flush=True)
    brd = pcbnew.LoadBoard(PCB)
    u1 = next((fp for fp in brd.GetFootprints() if fp.GetReference() == "U1"), None)
    r1 = next((fp for fp in brd.GetFootprints() if fp.GetReference() == "R1"), None)
    if u1 is None or r1 is None:
        print("  ERROR: U1 or R1 not found; selftest cannot run", flush=True)
        return False
    r1.SetPosition(u1.GetPosition())

    v, n = check_overlaps_brd(brd)
    print(f"  on-board footprints: {n}", flush=True)
    print(f"  violations: {len(v)}", flush=True)
    pair_seen = False
    for ra, rb, area in v:
        if {ra, rb} == {"R1", "U1"}:
            pair_seen = True
            print(f"    DETECTED R1/U1 overlap (area {area:.2f} mm²) — verifier WORKS", flush=True)
        elif len(v) <= 10:
            print(f"    incidental: {ra}/{rb} ({area:.2f} mm²)", flush=True)
    return pair_seen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true",
                    help="Run only the self-test (deliberately bad input)")
    args = ap.parse_args()

    if args.selftest:
        ok = self_test()
        if not ok:
            print("\nSELF-TEST FAILED — verifier did not detect the deliberate "
                  "R1/U1 overlap. The verifier is broken; do not trust its "
                  "green output on real boards.", flush=True)
            return 2
        print("\nSELF-TEST PASSED — verifier correctly flagged the deliberate "
              "overlap.", flush=True)
        return 0

    # Full run: BOTH self-test AND real check
    print("=== Gate 1 — bbox-overlap check ===\n", flush=True)
    ok = self_test()
    if not ok:
        print("\nSELF-TEST FAILED; refusing to trust the real check.", flush=True)
        return 2

    print("\n=== REAL CHECK: novapcb-stepwise.kicad_pcb ===", flush=True)
    violations, n = check_overlaps(PCB)
    print(f"  on-board footprints: {n}", flush=True)
    print(f"  violations: {len(violations)}", flush=True)
    if violations:
        print("\n  PAIRS WITH OVERLAPPING COURTYARDS:", flush=True)
        for ra, rb, area in violations:
            print(f"    {ra:6} ↔ {rb:6}   intersection area = {area:.3f} mm²", flush=True)
        return 1
    print("\n  Gate 1: GREEN. Self-test passed, zero real overlaps.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
