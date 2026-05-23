#!/usr/bin/env python3
"""Add MAUCH_VBAT_PRE route via X=24 corridor (between EFUSE_DVDT east
edge X=23.57 and Q3 west edge X=24.52). Done as separate-process step
to avoid the unfill+strip+refill segfault in the combined script.

Run AFTER strip_mauch_vbat.py.

Path:
- F.Cu fanout J4.3 (15.375, 3.15) → (15.375, 4.5)  [exit south, 1.35mm]
- Via @ (15.375, 4.5)
- B.Cu east (15.375, 4.5) → (24.0, 4.5)
- B.Cu south (24.0, 4.5) → (24.0, 14.0)  [through X=24 corridor]
- Via @ (24.0, 14.0)
- F.Cu hop (24.0, 14.0) → (23.49, 14.5)  [to R41.1]
"""
import os
import pcbnew

PCB = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "novapcb-stepwise.kicad_pcb")


def _mm(x):
    return pcbnew.FromMM(x)


brd = pcbnew.LoadBoard(PCB)
nets = {p.GetNetname(): p.GetNet()
        for fp in brd.GetFootprints() for p in fp.Pads()
        if p.GetNet() is not None}
net = nets["MAUCH_VBAT_PRE"]


def trk(x1, y1, x2, y2, layer):
    t = pcbnew.PCB_TRACK(brd)
    t.SetStart(pcbnew.VECTOR2I(_mm(x1), _mm(y1)))
    t.SetEnd(pcbnew.VECTOR2I(_mm(x2), _mm(y2)))
    t.SetWidth(_mm(0.20))
    t.SetLayer(layer)
    t.SetNet(net)
    brd.Add(t)


def via(x, y):
    v = pcbnew.PCB_VIA(brd)
    v.SetPosition(pcbnew.VECTOR2I(_mm(x), _mm(y)))
    v.SetWidth(_mm(0.50))
    v.SetDrill(_mm(0.30))
    v.SetNet(net)
    brd.Add(v)


trk(15.375, 3.150, 15.375, 4.5, pcbnew.F_Cu)
via(15.375, 4.5)
# B.Cu route to via NORTH of R41.1 (not west — C61 GND pad at X=22.48
# blocks the west approach; sense-row Y=14.5 is fully occupied X=18..25).
# Via at (23.5, 13.5):
#   - Clears EFUSE_DVDT F.Cu (line at X=24.02 at Y=13.5) by 0.52mm ≥0.45 OK
#   - Clears Q3 west edge X=24.52 by 1.02mm
#   - F.Cu hop south 1mm to R41.1 pad — clears EFUSE_DVDT F.Cu all the way
trk(15.375, 4.5, 22.6, 4.5, pcbnew.B_Cu)
trk(22.6, 4.5, 22.6, 13.5, pcbnew.B_Cu)
via(22.6, 13.5)
trk(22.6, 13.5, 23.49, 14.5, pcbnew.F_Cu)  # 1.34mm F.Cu SE hop to R41.1, clears EFUSE_DVDT F.Cu by 2mm

pcbnew.SaveBoard(PCB, brd)
print("MAUCH_VBAT_PRE added (no refill)")
