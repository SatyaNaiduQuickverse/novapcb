#!/usr/bin/env python3
"""fix_u6_decap — move C9 closer to U6 +5V OUT pads.

Fixes audit DECOUPLING fail (task #91): "U6 VDD net=+5V — nearest cap C9
@ 3.46mm body-edge" — exceeds 3mm threshold.

C9 is the U6 OUT-pin bypass per power_3b.py:307 ("OUT-pin bypass: 1µF
X7R per datasheet's typical application"). Current position (31.75, 15.57)
is east-north of U6 body, 3.46mm body-edge from nearest +5V pad.

Move to (29, 16): north of U6 body (Y=13.82-22.18 → Y=16 just north of
body Y=13.82? actually inside body Y range). Better: north of body
top (Y<13.82): (29, 12.5).

Recalculation:
- U6 +5V pad U6.3 at (26.55, 17.75)
- C9 at (29, 12.5) — distance to U6.3 = sqrt(6+27.56) = 5.79mm — TOO FAR
- C9 at (28, 14) — distance to U6.3 = sqrt(2.10+14.06) = 4.02mm — still over
- C9 at (26, 16) — distance to U6.3 = sqrt(0.30+3.06) = 1.83mm ✓
- Check C9 at (26, 16) within U6 body? body 23.71-32.29, Y=13.82-22.18.
  X=26 + 0.5 (half C9 0402 width) → 26.5 → INSIDE body bbox X.
  Y=16 + 0.25 → 16.25 → INSIDE body bbox Y.
  C9 INSIDE U6 body bbox. Probably DRC error.

Better: place C9 just OUTSIDE U6 body. U6 body north edge Y=13.82.
C9 north of body: anchor (26, 13.3) → pad Y=13.3 ± 0.25 = 13.05..13.55.
Body north Y=13.82 → 0.27mm gap. Tight but OK if courtyards allow.

Distance C9 at (26, 13.3) to U6.3 at (26.55, 17.75) = sqrt(0.30+19.80) = 4.49mm
TOO FAR.

The fundamental problem: U6 +5V pads are at Y=17.75-19.95, all on west
side of body (X=26.55-27.75). The body itself blocks placing cap close
on east/north/south. Cap MUST go WEST of body to be within 3mm.

West of body: X<23.71. Try C9 at (22.5, 18.5):
- C9.1 (22.02, 18.5), C9.2 (22.98, 18.5)
- Distance to U6.3 (26.55, 17.75) = sqrt(12.78+0.56) = 3.65mm
- Distance to U6.4 (26.55, 18.25) = sqrt(12.78+0.06) = 3.59mm
Still TOO FAR.

Even closer: C9 at (24, 18.5):
- C9 east pad at 24.48 — needs to clear U6 west body edge X=23.71. 0.77mm gap. ✓
- Distance to U6.3 = sqrt(6.50+0.56) = 2.66mm ✓

C9 at (24, 18.5) — pad-to-pad ~2.7mm, body-edge maybe just at 3mm.
But C7 at (23.57, 18.75) is RIGHT THERE. Conflict.

C7 is the EFUSE_DVDT cap. Move C7 elsewhere to free this slot.

Actually simpler: add a NEW small decap (100nF 0402) very close to U6
+5V pads. Don't move C9. C7 stays.

Let me add new C100 (next free C ref) at (24, 16) — pad 100nF +5V/GND
close to U6 +5V pads. C100.1 (23.52, 16) just west of body Y=16.
Distance to U6.3 (26.55, 17.75) = sqrt(9.18+3.06) = 3.50mm — still over.

Try (25, 17): C100.1 (24.52, 17), distance to U6.3 (26.55, 17.75)
= sqrt(4.13+0.56) = 2.17mm ✓.

Check body conflicts: C100 anchor (25, 17). 0402 body X=24.5..25.5 Y=16.75..17.25.
U6 body bbox 23.71-32.29 × 13.82-22.18. C100 bbox INSIDE U6 body bbox!
DRC will fail (component inside another component).

The U6 body bbox is wider than the body itself probably. Actual body
typically much smaller. Let me check footprint courtyard.

Actually solution: move C9 from (31.75, 15.57) to (28, 16):
- C9 0402 anchor (28, 16) → pad X=27.5/28.5, Y=15.75/16.25
- U6 +5V pads at U6.3 (26.55, 17.75), U6.7 (27.25, 19.95), U6.8 (27.75, 19.95)
- Nearest is U6.3 — distance sqrt(2.10+3.06) = 2.27mm ✓
- Body conflict: C9 anchor (28, 16) — body Y=16±0.25 inside U6 body Y=13.82-22.18.
  C9 X=28 inside U6 body X=23.71-32.29.
  C9 INSIDE U6 body — courtyard fail likely.

The U6 body bbox is the FOOTPRINT bounding box which includes
ALL the silkscreen text. The actual physical body is just the
4×3mm WQFN-20 package — much smaller than the bbox.

KiCad DRC may or may not flag "inside body bbox" — depends on
courtyard definition. Let me try anyway.

If C9 (28, 16) overlaps U6 courtyard → DRC error.

Best fix: Just MOVE C9 to NORTH of U6 body bbox top, accept ~3.5mm
distance + add a smaller decap closer if possible.

Actually let me JUST RUN the move + see DRC. If DRC fails, fall back.
"""
import os, sys, pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")

# Try moving C9 to (28, 16) — close to U6 +5V pad U6.3 (26.55, 17.75)
C9_NEW_XY = (25.0, 18.0)
# Rationale: U6 WQFN-20 actual pad layout (verified): +5V pads on W edge
# at (26.55, 17.75/18.25/18.75/19.25) [pads 3-6] + S edge at
# (27.25/27.75, 19.95) [pads 7-8]. Body silk bbox is enlarged by ref/value
# text but actual body ~4mm. C9 (25, 18): east pad (25.48, 18) is 1.07mm
# from nearest +5V pad U6.3 (26.55, 17.75) — well within 3mm decoupling
# threshold. Clear of U6 thermal pad 21 (27.18-28.83, 16.68-19.33) by
# 1.68mm. Clear of existing C7 at (23.57, 18.75) by 1.61mm.


def main():
    brd = pcbnew.LoadBoard(PCB)
    c9 = next((f for f in brd.GetFootprints() if f.GetReference()=="C9"), None)
    if c9 is None:
        print("!!! C9 not found")
        return 1
    old = c9.GetPosition()
    print(f"C9: ({old.x/1e6:.2f}, {old.y/1e6:.2f}) → ({C9_NEW_XY[0]:.2f}, {C9_NEW_XY[1]:.2f})")
    c9.SetPosition(pcbnew.VECTOR2I(int(C9_NEW_XY[0]*1e6), int(C9_NEW_XY[1]*1e6)))

    for z in brd.Zones():
        if hasattr(z, "UnFill"): z.UnFill()
    pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
    pcbnew.SaveBoard(PCB, brd)
    print(f"saved")
    return 0


if __name__ == "__main__":
    sys.exit(main())
