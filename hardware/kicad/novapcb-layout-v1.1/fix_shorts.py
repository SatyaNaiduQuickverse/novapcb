#!/usr/bin/env python3
"""Fix small-part shorts only (slot already cut by cleanup_placement.py)."""
import os
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-layout-v1.1.kicad_pcb")


def main():
    brd = pcbnew.LoadBoard(PCB)
    fps_by_ref = {fp.GetReference(): fp for fp in brd.GetFootprints()}

    MOVES = [
        ("C34", 19.05, 29.0),   # was (20, 30.5), move 1.5mm N to clear C74
        ("C22", 27.0, 32.5),    # VREF_P cap, move W away from C24 HSE_IN
        ("C20", 32.5, 38.5),    # +3V3A cap, move SE away from Y1
        ("R12", 70.5, 62.5),    # I2C2_SCL R, move S+E away from C78
        ("R61", 67.5, 55.0),    # heater R, move E away from Q5
        ("C83", 80.0, 35.0),    # +5V cap, move W away from J1
        ("C84", 80.0, 38.5),    # cap, move W away from J5
        ("R45", 78.0, 22.0),    # CAN term, move N+W away from J5
        ("C72", 71.0, 26.5),    # +3V3 cap, move W away from U5
    ]
    for ref, x, y in MOVES:
        fp = fps_by_ref.get(ref)
        if fp is None:
            print(f"  {ref}: NOT FOUND")
            continue
        fp.SetPosition(pcbnew.VECTOR2I(int(x*1e6), int(y*1e6)))
        print(f"  {ref} -> ({x}, {y})")
    pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
    pcbnew.SaveBoard(PCB, brd)
    print(f"saved")


if __name__ == "__main__":
    main()
