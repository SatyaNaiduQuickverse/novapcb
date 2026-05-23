#!/usr/bin/env python3
"""Strip MAUCH_VBAT_PRE tracks/vias. No zone touching = no segfault."""
import os
import pcbnew

PCB = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "novapcb-stepwise.kicad_pcb")

brd = pcbnew.LoadBoard(PCB)
n = 0
for t in list(brd.GetTracks()):
    if t.GetNetname() == "MAUCH_VBAT_PRE":
        brd.Remove(t)
        n += 1
pcbnew.SaveBoard(PCB, brd)
print(f"stripped {n} MAUCH_VBAT_PRE segments")
