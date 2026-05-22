#!/usr/bin/env python3
"""Step 3 — place F (USB_INTERFACE) on the incremental-integration board.

Run AFTER step2_place_E.py.

F subsystem per docs/SUBSYSTEM_CONTRACTS.md §F:
  J1   — USB-C receptacle (HRO TYPE-C-31-M-12, 12.44 × 10.69 mm)
  R31  — CC1 5.1k pulldown (defines novapcb as USB device)
  R32  — CC2 5.1k pulldown
  U5   — USB ESD diode array (TPD4S014 or similar)

Pin map (verified against /usr/share/kicad/symbols/MCU_ST_STM32H7
STM32H743VITx symbol — official source):
  PA11 = pin 70 @ (52.67, 31.50) on U1 — USB_DM
  PA12 = pin 71 @ (52.67, 31.00) on U1 — USB_DP
  (Both on U1's E edge, Y=30..31; adjacent for diff pair)

J1 placement strategy:
  - Place J1 at the east board edge with receptacle opening facing OUT
    so the USB cable can physically plug in.
  - HRO_TYPE-C-31-M-12 footprint: solder pads on -X side (west),
    receptacle opening on +X side (east). Default 0° orientation already
    aligns: cable plugs in from the east.
  - Center at (83.78, 30) so the 12.44mm body extends to X=90.00 (board
    edge) and pads land at X≈79.74. Y centered on PA11/PA12 average.

ESD + CC pulldowns:
  - U5 between J1 pads and U1, ~X=73 — short hop to PA11/PA12.
  - R31, R32 near J1's CC pads — on the +/-Y side of J1 to clear the
    USB diff pair path.

All coords pcbnew Y-down (per reconciled convention).
"""
import os
import sys
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")

F_REFDES = ["J1", "R31", "R32", "U5"]
ZONE_X_MIN, ZONE_X_MAX = 65.0, 91.0   # east third of board (J1 body extends to 90.0)
ZONE_Y_MIN, ZONE_Y_MAX = 22.0, 42.0


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


def find_fp(brd, ref):
    for fp in brd.GetFootprints():
        if fp.GetReference() == ref: return fp
    return None


def main():
    print("=== Step 3 — place F (USB_INTERFACE) ===", flush=True)
    brd = pcbnew.LoadBoard(PCB)

    placed = []
    for fp in brd.GetFootprints():
        if fp.GetPosition().x/1e6 < 100.0:
            placed.append((fp, _courtyard_bbox(fp)))
    print(f"  already-placed on-board: {len(placed)} footprints", flush=True)

    import math
    placed_F = []

    def try_place(ref, x, y, rot=0.0):
        fp = find_fp(brd, ref)
        if fp is None:
            print(f"  WARN: {ref} not found"); return
        if rot: fp.SetOrientationDegrees(rot)
        # Snap-search if target conflicts
        for r in [0.0, 0.5, 1.0, 1.5, 2.5]:
            for ang in (0,) if r == 0 else range(0, 360, 30):
                tx = x + r * math.cos(math.radians(ang))
                ty = y + r * math.sin(math.radians(ang))
                if not (ZONE_X_MIN <= tx <= ZONE_X_MAX and ZONE_Y_MIN <= ty <= ZONE_Y_MAX):
                    continue
                fp.SetPosition(pcbnew.VECTOR2I(_mm(tx), _mm(ty)))
                bb = _courtyard_bbox(fp)
                # J1 may extend beyond board outline (the receptacle hangs over
                # the east edge — that's intentional); allow ≤91mm X-max.
                if bb[0] < ZONE_X_MIN - 0.1 or bb[2] > 91.5 or \
                   bb[1] < ZONE_Y_MIN - 0.1 or bb[3] > ZONE_Y_MAX + 0.1:
                    continue
                ok = True
                for _, pb in placed + placed_F:
                    if _bbox_intersects(bb, pb): ok = False; break
                if not ok: continue
                placed_F.append((fp, bb))
                print(f"  {ref:4} @ ({tx:.2f}, {ty:.2f}) rot={rot:.0f}°  "
                      f"bbox X={bb[0]:.2f}..{bb[2]:.2f}, Y={bb[1]:.2f}..{bb[3]:.2f}", flush=True)
                return
        print(f"  !! could not place {ref} near target ({x}, {y})")

    # J1 USB-C: east edge, receptacle facing OUT (+X). Default orient ok.
    # Center X=83.78 so body extends X=77.56..90.00 (to board edge).
    # Center Y=30 centered on PA11/PA12 (Y=30.5/31.0 on U1's E edge).
    try_place("J1", 83.78, 30.00, rot=0.0)

    # R31 / R32 — CC pulldowns. Place on -Y side of J1 (north) so the
    # diff pair path on +Y side is clear. CC pads are at offset ~(-4.04,
    # +/-1.25) from J1 center → A5 at (79.74, 31.25), B5 at (79.74, 28.75).
    try_place("R31", 78.5, 26.0)
    try_place("R32", 78.5, 27.0)

    # U5 ESD diode — between J1 pads (X≈80) and U1 east edge (X≈53).
    # Place ~X=72, Y=30 (midway, same Y as USB pair).
    try_place("U5", 72.0, 30.0)

    pcbnew.SaveBoard(PCB, brd)
    print(f"\n  Placed {len(placed_F)} of {len(F_REFDES)} F components", flush=True)
    return 0 if len(placed_F) == len(F_REFDES) else 1


if __name__ == "__main__":
    sys.exit(main())
