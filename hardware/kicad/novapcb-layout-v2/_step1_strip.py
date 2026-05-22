#!/usr/bin/env python3
"""Process A: load board + strip signal tracks/vias, save."""
import pcbnew, os
PCB = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "novapcb-layout-v2.kicad_pcb")
PLANE_NETS = {"GND", "+3V3", "+3V3A", "+5V"}
brd = pcbnew.LoadBoard(PCB)
n_t = n_v = 0
for t in list(brd.GetTracks()):
    nn = str(t.GetNet().GetNetname()) if t.GetNet() else ""
    if nn in PLANE_NETS: continue
    if isinstance(t, pcbnew.PCB_VIA):
        brd.Remove(t); n_v += 1
    else:
        brd.Remove(t); n_t += 1
pcbnew.SaveBoard(PCB, brd)
print(f"[step1] stripped {n_t} signal tracks + {n_v} signal vias")
