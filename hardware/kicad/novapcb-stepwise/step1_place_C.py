#!/usr/bin/env python3
"""Step 1 — place C (MCU_CORE) per docs/SUBSYSTEM_CONTRACTS.md.

This is the FIRST subsystem placement on the stepwise board. Per the
incremental-integration loop (docs/PLACEMENT_ROUTING_GATES.md §0):

  1. C is the hub. Everything else's coordinates are relative to U1.
  2. Only C components land on-board; all other subsystems' components
     are PARKED off-board at X >= 110 mm (board is 90 mm wide), to be
     positioned in future Step-N PRs.
  3. Board outline (90 × 70 mm) and 4 corner M3 mounting holes
     (5, 5)(85, 5)(5, 65)(85, 65) are added per master directive
     2026-05-22.

C subsystem components placed (per mcu_3a.py — 22 parts total):
  U1   STM32H743VIT6 LQFP-100, centered at (45, 35).
  Y1   8 MHz HSE crystal, W edge of U1 near PH0/PH1 (pins 12/13).
  C24, C25  HSE load caps (18 pF), within 2 mm of Y1.
  C11..C15  Per-VDD-pin 100 nF decap, within 2 mm of each VDD pin
                  (pins 11, 27, 50, 75, 100).
  C16  Bulk 4.7 µF on +3V3, immediately N of U1.
  C17  VCAP1 2.2 µF, within 2 mm of pin 48.
  C18  VCAP2 2.2 µF, within 2 mm of pin 73.
  FB1  Ferrite +3V3 -> +3V3A, near VDDA pin 21.
  C19, C20  VDDA decap (100 nF + 1 µF), within 2 mm of pin 21.
  C21, C22  VREF+ decap (100 nF + 1 µF), within 2 mm of pin 20.
  R1   VREF tie (0R), between +3V3A and VREF.
  R2   VBAT tie (0R), between +3V3 and VBAT.
  C23  VBAT 100 nF, within 2 mm of pin 6.
  C26  NRST 100 nF, within 2 mm of pin 14.
  R3   BOOT0 10k pulldown, within 2 mm of pin 94.

All other (non-C) footprints are moved to a PARK grid at X >= 110 mm.
"""
import os
import sys
import sexpdata
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
# Source: the v1.1 board has all footprints already loaded via kinet2pcb
# from a previous KiCad version. We clone it via S-expression rewrite,
# stripping all tracks/vias/zones (superseded R1..R4 routing) and Edge.Cuts
# shapes (old outline + IMU slot), then re-place C with pcbnew Python.
# This sidesteps a KiCad-9 kinet2pcb API regression where
# pcbnew.FootprintLoad returns None on a fresh netlist import. We do not
# modify the source v1.1 board.
SOURCE_PCB = os.path.join(ROOT, "hardware", "kicad", "novapcb-layout-v1.1",
                           "novapcb-layout-v1.1.kicad_pcb")
OUT_PCB = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")

BOARD_W_MM = 90.0
BOARD_H_MM = 70.0

# 4 corner mounting holes per master directive 2026-05-22
MOUNTING_HOLES = [
    (5.0, 5.0),
    (85.0, 5.0),
    (5.0, 65.0),
    (85.0, 65.0),
]
M3_HOLE_DRILL_MM = 3.2     # M3 clearance
M3_HOLE_DIAMETER_MM = 5.5  # pad diameter

# C subsystem refdes — anything in this set stays on-board
C_REFDES = {
    "U1",  "Y1",  "FB1",
    "C11", "C12", "C13", "C14", "C15",   # per-VDD decap
    "C16",                                  # bulk
    "C17", "C18",                           # VCAP1/VCAP2
    "C19", "C20",                           # VDDA 100n+1u
    "C21", "C22",                           # VREF 100n+1u
    "C23",                                  # VBAT 100n
    "C24", "C25",                           # HSE 18p
    "C26",                                  # NRST 100n
    "R1",  "R2",  "R3",                     # VREF tie / VBAT tie / BOOT0
}

PARK_X_START = 110.0
PARK_X_STEP  = 3.0
PARK_Y_START = 0.0
PARK_Y_STEP  = 3.0
PARK_COLS    = 30   # 30 cols * 3mm = 90mm of parking width


def _mm(x_mm: float) -> int:
    return pcbnew.FromMM(x_mm)


def add_board_outline(brd: pcbnew.BOARD) -> None:
    """Add the 90 x 70 mm Edge.Cuts rectangle."""
    rect = pcbnew.PCB_SHAPE(brd)
    rect.SetShape(pcbnew.SHAPE_T_RECT)
    rect.SetLayer(pcbnew.Edge_Cuts)
    rect.SetStart(pcbnew.VECTOR2I(_mm(0), _mm(0)))
    rect.SetEnd(pcbnew.VECTOR2I(_mm(BOARD_W_MM), _mm(BOARD_H_MM)))
    rect.SetWidth(_mm(0.15))
    brd.Add(rect)


def add_mounting_hole(brd: pcbnew.BOARD, x_mm: float, y_mm: float, ref: str) -> None:
    """Add an M3 mounting-hole footprint at (x, y)."""
    fp = pcbnew.FOOTPRINT(brd)
    # Plain non-plated through-hole pad
    pad = pcbnew.PAD(fp)
    pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
    pad.SetAttribute(pcbnew.PAD_ATTRIB_NPTH)
    pad.SetSize(pcbnew.VECTOR2I(_mm(M3_HOLE_DIAMETER_MM), _mm(M3_HOLE_DIAMETER_MM)))
    pad.SetDrillSize(pcbnew.VECTOR2I(_mm(M3_HOLE_DRILL_MM), _mm(M3_HOLE_DRILL_MM)))
    pad.SetLayerSet(pcbnew.PAD.PTHMask())
    fp.Add(pad)
    fp.SetReference(ref)
    fp.SetValue("M3")
    fp.SetPosition(pcbnew.VECTOR2I(_mm(x_mm), _mm(y_mm)))
    brd.Add(fp)


def find_fp(brd: pcbnew.BOARD, ref: str):
    for fp in brd.GetFootprints():
        if fp.GetReference() == ref:
            return fp
    return None


def _courtyard_bbox(fp):
    """Return (x0, y0, x1, y1) in mm of the footprint's F.CrtYd+B.CrtYd
    shape union (in CURRENT board coordinates). Falls back to footprint
    full bbox if no courtyard. Avoids BOX2I.Merge() — KiCad-9 returns
    references that interact badly when accumulated in a loop. Use
    scalar min/max instead. Mirror of gate1_bbox_overlap.courtyard_bbox.
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


def find_pad_position(fp, pad_name: str):
    """Return (x_mm, y_mm) of the named pad (e.g. '11' for VDD pin 11)
    in board coordinates, considering the footprint's current position
    and rotation."""
    for pad in fp.Pads():
        if pad.GetNumber() == pad_name:
            p = pad.GetPosition()
            return (p.x / 1e6, p.y / 1e6)
    return None


def move_fp(fp, x_mm: float, y_mm: float, rot_deg: float = 0.0) -> None:
    fp.SetPosition(pcbnew.VECTOR2I(_mm(x_mm), _mm(y_mm)))
    if rot_deg:
        fp.SetOrientationDegrees(rot_deg)


def sexp_strip(src_path: str, dst_path: str) -> None:
    """S-expression rewrite: drop (segment), (via), (zone), and any
    (gr_*) shape on Edge.Cuts. Footprints + their pads are preserved.
    """
    with open(src_path) as f:
        tree = sexpdata.loads(f.read())

    def fp_ref(node):
        """If node is a (footprint ...) returns its reference, else None."""
        if not (isinstance(node, list) and node
                and isinstance(node[0], sexpdata.Symbol)
                and node[0].value() == "footprint"):
            return None
        for sub in node[1:]:
            if (isinstance(sub, list) and len(sub) >= 3
                    and isinstance(sub[0], sexpdata.Symbol)
                    and sub[0].value() == "property"
                    and isinstance(sub[1], str)
                    and sub[1] == "Reference"):
                return sub[2] if isinstance(sub[2], str) else None
        return None

    def is_drop(node):
        if not isinstance(node, list) or not node: return False
        head = node[0]
        if not isinstance(head, sexpdata.Symbol): return False
        name = head.value()
        if name in ("segment", "via", "zone"):
            return True
        # Strip original v1.1 mounting-hole footprints (refdes H1..H4) so
        # we re-add fresh ones at master's corner-inset positions.
        ref = fp_ref(node)
        if ref and ref in {"H1", "H2", "H3", "H4"}:
            return True
        if name in ("gr_rect", "gr_line", "gr_arc", "gr_circle", "gr_poly"):
            for sub in node[1:]:
                if (isinstance(sub, list) and len(sub) >= 2
                        and isinstance(sub[0], sexpdata.Symbol)
                        and sub[0].value() == "layer"):
                    layer = sub[1]
                    val = (layer.value() if isinstance(layer, sexpdata.Symbol)
                           else layer if isinstance(layer, str) else None)
                    if val == "Edge.Cuts":
                        return True
        return False

    cleaned = [n for i, n in enumerate(tree) if i == 0 or not is_drop(n)]
    with open(dst_path, "w") as f:
        f.write(sexpdata.dumps(cleaned))


def main() -> int:
    print(f"[1/6] clone+strip {os.path.basename(SOURCE_PCB)} -> {os.path.basename(OUT_PCB)}", flush=True)
    if os.path.exists(OUT_PCB):
        os.remove(OUT_PCB)
    sexp_strip(SOURCE_PCB, OUT_PCB)
    brd = pcbnew.LoadBoard(OUT_PCB)
    n_fp = len(list(brd.GetFootprints()))
    print(f"      stripped: tracks/vias/zones/edge-cuts removed; {n_fp} footprints preserved", flush=True)

    print(f"[2/6] add fresh board outline (90 x 70 mm) + 4 corner M3 holes", flush=True)
    add_board_outline(brd)
    for i, (x, y) in enumerate(MOUNTING_HOLES, 1):
        add_mounting_hole(brd, x, y, f"H{i}")

    # ---- park EVERYTHING first; we'll then position C components on-board
    print(f"[3/6] park ALL footprints off-board at X >= {PARK_X_START} mm", flush=True)
    park_idx = 0
    parked = []
    for fp in brd.GetFootprints():
        ref = fp.GetReference()
        if ref.startswith("H"):  # mounting holes — leave on-board
            continue
        col = park_idx % PARK_COLS
        row = park_idx // PARK_COLS
        x = PARK_X_START + col * PARK_X_STEP
        y = PARK_Y_START + row * PARK_Y_STEP
        move_fp(fp, x, y)
        parked.append(ref)
        park_idx += 1
    print(f"      parked {park_idx} footprints", flush=True)

    # ---- place C components on-board
    print(f"[4/6] place C subsystem (MCU_CORE) on-board", flush=True)
    u1 = find_fp(brd, "U1")
    if u1 is None:
        print("ERROR: U1 not found in netlist", flush=True)
        return 1

    # U1 center at (45, 35). LQFP-100 is 14x14 mm body, 16x16 leads.
    # Default orientation: pin 1 at NW corner (KiCad's Package_QFP convention).
    U1_X, U1_Y = 45.0, 35.0
    move_fp(u1, U1_X, U1_Y, rot_deg=0.0)

    # Compute U1's courtyard extent so we can place decap caps in the
    # band JUST OUTSIDE the courtyard (standard practice — keeps the
    # cap close enough for low inductance but lets P&P pick the IC).
    # Build extent from the (now in-board-coords) courtyard shapes.
    ctyd_layers = (pcbnew.F_CrtYd, pcbnew.B_CrtYd)
    cx0 = cy0 = float("inf")
    cx1 = cy1 = float("-inf")
    for d in u1.GraphicalItems():
        if isinstance(d, pcbnew.PCB_SHAPE) and d.GetLayer() in ctyd_layers:
            b = d.GetBoundingBox()
            x = b.GetX() / 1e6
            y = b.GetY() / 1e6
            cx0, cy0 = min(cx0, x), min(cy0, y)
            cx1, cy1 = max(cx1, x + b.GetWidth() / 1e6), max(cy1, y + b.GetHeight() / 1e6)
    # 1.2 mm clearance band beyond U1's courtyard (0402 cap half-width + margin)
    BAND = 1.2
    W_BAND = cx0 - BAND     # X of cap centers on W side
    E_BAND = cx1 + BAND     # X on E side
    N_BAND = cy0 - BAND     # Y on N side
    S_BAND = cy1 + BAND     # Y on S side
    print(f"      U1 courtyard: x={cx0:.2f}..{cx1:.2f}, y={cy0:.2f}..{cy1:.2f}", flush=True)
    print(f"      decap bands: W={W_BAND:.2f}, E={E_BAND:.2f}, N={N_BAND:.2f}, S={S_BAND:.2f}", flush=True)

    # Build a pin -> (x_mm, y_mm) map for U1 (board coords after U1 placed)
    pin_pos = {}
    for pad in u1.Pads():
        p = pad.GetPosition()
        pin_pos[pad.GetNumber()] = (p.x / 1e6, p.y / 1e6)

    # ---- non-overlap placer ----
    # Keep a list of (fp, bbox) for already-placed-on-board parts so
    # subsequent placements can snap to the nearest clear position.
    placed = [(u1, _courtyard_bbox(u1))]

    def _bbox_intersects(a, b):
        return not (a[2] <= b[0] or a[0] >= b[2] or a[3] <= b[1] or a[1] >= b[3])

    def place_decap(ref: str, pin: str, side: str, extra: float = 0.0,
                    rot: float = 0.0) -> None:
        """Snap a footprint to the U1-perimeter band on `side` near the
        given pin, then spiral-search for the nearest Y (W/E side) or
        nearest X (N/S side) where its courtyard doesn't intersect any
        already-placed footprint."""
        fp = find_fp(brd, ref)
        if fp is None: print(f"  WARN: {ref} not found", flush=True); return
        if pin not in pin_pos: print(f"  WARN: pin {pin}", flush=True); return
        px, py = pin_pos[pin]
        if rot: fp.SetOrientationDegrees(rot)
        if side == "W":  fixed_x, var_axis, var_seed = W_BAND - extra, "Y", py
        elif side == "E":  fixed_x, var_axis, var_seed = E_BAND + extra, "Y", py
        elif side == "N":  fixed_y, var_axis, var_seed = N_BAND - extra, "X", px
        elif side == "S":  fixed_y, var_axis, var_seed = S_BAND + extra, "X", px
        else: raise ValueError(side)

        # spiral-search in 0.2mm steps until courtyard is clear of all placed
        for step in range(0, 80):   # up to 16mm of slide
            for sgn in ((+1,) if step == 0 else (+1, -1)):
                delta = step * 0.2 * sgn
                if side in ("W", "E"):
                    x, y = fixed_x, var_seed + delta
                else:
                    x, y = var_seed + delta, fixed_y
                # Try this position
                fp.SetPosition(pcbnew.VECTOR2I(_mm(x), _mm(y)))
                bb = _courtyard_bbox(fp)
                if not any(_bbox_intersects(bb, pb) for _, pb in placed):
                    placed.append((fp, bb))
                    return
        print(f"  WARN: could not place {ref} clear on side {side}", flush=True)

    # HSE crystal Y1 placed FIRST (largest part on W edge) — close to
    # pins 12/13 (HSE_IN/OUT). All subsequent W-side caps will snap
    # clear of Y1.
    if "12" in pin_pos and "13" in pin_pos:
        x12, y12 = pin_pos["12"]
        x13, y13 = pin_pos["13"]
        ycenter = (y12 + y13) / 2.0
        # Y1 ~2 mm W of U1 courtyard, rotated 90° so 3.2mm dim is in Y
        y1 = find_fp(brd, "Y1")
        if y1:
            y1.SetOrientationDegrees(90.0)
            y1.SetPosition(pcbnew.VECTOR2I(_mm(W_BAND - 2.0), _mm(ycenter)))
            placed.append((y1, _courtyard_bbox(y1)))
        # C24, C25 load caps further W (in the next band over)
        c24 = find_fp(brd, "C24")
        if c24:
            c24.SetPosition(pcbnew.VECTOR2I(_mm(W_BAND - 5.5), _mm(ycenter - 1.5)))
            placed.append((c24, _courtyard_bbox(c24)))
        c25 = find_fp(brd, "C25")
        if c25:
            c25.SetPosition(pcbnew.VECTOR2I(_mm(W_BAND - 5.5), _mm(ycenter + 1.5)))
            placed.append((c25, _courtyard_bbox(c25)))

    # Per-VDD decap (C11..C15) — one per VDD pin.
    # LQFP-100 default orient: pin 1 NW; counter-clockwise:
    #   1..25 W edge, 26..50 S, 51..75 E, 76..100 N
    place_decap("C11", "11",  "W")   # W band; will snap past Y1
    place_decap("C12", "27",  "S")
    place_decap("C13", "50",  "S")
    place_decap("C14", "75",  "E")
    place_decap("C15", "100", "N")

    # VCAP1/VCAP2 (LDO core caps, 2.2µF each)
    place_decap("C17", "48",  "S")   # VCAP1
    place_decap("C18", "73",  "E")   # VCAP2

    # VDDA chain: ferrite + 100nF + 1uF, all on W edge near pin 21
    place_decap("FB1", "21",  "W", extra=2.6)   # furthest W
    place_decap("C19", "21",  "W")              # band
    place_decap("C20", "21",  "W", extra=1.3)   # mid

    # VREF+ chain (pin 20): 100nF + 1uF + 0R tie
    place_decap("C21", "20",  "W")
    place_decap("C22", "20",  "W", extra=1.3)
    place_decap("R1",  "20",  "W", extra=2.6)

    # VBAT (pin 6) — W edge, with 0R tie further out
    place_decap("C23", "6", "W")
    place_decap("R2",  "6", "W", extra=1.3)

    # NRST (pin 14)
    place_decap("C26", "14", "W")

    # BOOT0 (pin 94) — N side
    place_decap("R3", "94", "N")

    # C16 bulk — N edge, offset E from R3 so they don't collide
    place_decap("C16", "94", "N", extra=1.8)

    print(f"[5/6] save board -> {OUT_PCB}", flush=True)
    pcbnew.SaveBoard(OUT_PCB, brd)

    print(f"[6/6] summary", flush=True)
    on_board = []
    off_board = []
    for fp in brd.GetFootprints():
        ref = fp.GetReference()
        p = fp.GetPosition()
        x = p.x / 1e6
        if x < BOARD_W_MM + 5:  # in or just past board
            on_board.append(ref)
        else:
            off_board.append(ref)
    print(f"      on-board: {len(on_board)} refs")
    print(f"      off-board (parked): {len(off_board)} refs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
