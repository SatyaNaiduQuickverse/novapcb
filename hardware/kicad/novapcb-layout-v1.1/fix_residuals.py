#!/usr/bin/env python3
"""Fix remaining DRC after greedy placer: targeted nudges for big blocks
+ specific small parts to resolve the last shorts/courtyards."""
import os
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-layout-v1.1.kicad_pcb")

# (ref, new_x_mm, new_y_mm)
MOVES = [
    # R61 too close to Q5 — move E (only big-block move that's clean)
    ("R61", 67.5, 55.0),
    # D8 ESD diode conflict with J14 ESC — move N
    ("D8", 28.0, 7.5),
    # D12/D11 conflict with U15 CAN ESD — move further N
    ("D12", 86.0, 23.5),
    ("D11", 84.0, 23.5),
    # J10 too close to J3 — move further S (Y larger = further from J3 at Y=50)
    ("J10", 84.0, 56.0),
    # D5-D8 ESD diodes overlap ESC pads at Y=3 — move to Y=9 instead
    ("D5", 10.0, 9.5),
    ("D6", 15.0, 9.5),
    ("D7", 20.0, 9.5),
    ("D9", 60.0, 9.5),
    ("D13", 70.0, 9.5),
    ("D14", 75.0, 9.5),
    # Keep J20/U14/U15 at original v5 positions (revert my v7 moves)
    ("J20", 84.0, 8.0),
    ("U14", 82.0, 18.0),
    ("U15", 87.0, 19.0),
]


def main():
    brd = pcbnew.LoadBoard(PCB)
    fps = {fp.GetReference(): fp for fp in brd.GetFootprints()}
    for ref, x, y in MOVES:
        fp = fps.get(ref)
        if not fp:
            print(f"  {ref}: not found"); continue
        fp.SetPosition(pcbnew.VECTOR2I(int(x*1e6), int(y*1e6)))
        print(f"  {ref} -> ({x}, {y})")
    pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
    pcbnew.SaveBoard(PCB, brd)
    print("saved")


if __name__ == "__main__":
    main()
