#!/usr/bin/env python3
"""step9_place_microSD — place microSD subsystem (J2 + R51-R55 + C63).

Per docs/MICROSD_PLACEMENT_ANALYSIS.md (master signed off 4 decisions
2026-05-24): Zone B east-band south (J2 at (95, 67)), 5x 47k pulls
clustered west of J2, C63 VDD decap near J2.4.

J2 = DM3AT-SF-PEJM5 bbox 15.75 x 24.15mm — large.
Anchor (95, 67): bbox X=87..103, Y=55..79. Fits east band.
"""
import os, sys, pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")

PLACEMENTS = [
    ("J2",  95.0, 67.0,  0.0),   # microSD socket — east-band south
    ("R51", 86.0, 62.0,  0.0),   # CMD pull-up — cluster west of J2
    ("R52", 86.0, 64.0,  0.0),   # D0 pull-up
    ("R53", 86.0, 66.0,  0.0),   # D1 pull-up
    ("R54", 86.0, 68.0,  0.0),   # D2 pull-up
    ("R55", 86.0, 70.0,  0.0),   # D3 pull-up
    ("C63", 91.5, 62.0,  0.0),   # VDD decap — near J2.4 (north pin)
]


def main():
    print("=== Step 9: place microSD subsystem ===\n")
    brd = pcbnew.LoadBoard(PCB)
    for ref, x, y, rot in PLACEMENTS:
        fp = next((f for f in brd.GetFootprints() if f.GetReference() == ref), None)
        if fp is None:
            print(f"  !!! {ref}: not found")
            continue
        fp.SetPosition(pcbnew.VECTOR2I(int(x*1e6), int(y*1e6)))
        fp.SetOrientationDegrees(rot)
        print(f"  {ref}: placed at ({x:.2f}, {y:.2f}) rot={rot}°")
    for z in brd.Zones():
        if hasattr(z, "UnFill"): z.UnFill()
    pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
    pcbnew.SaveBoard(PCB, brd)
    print(f"\n  saved {PCB}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
