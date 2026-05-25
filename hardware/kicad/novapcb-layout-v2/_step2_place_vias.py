#!/usr/bin/env python3
"""Process B: load stripped board, place plane stitch vias, refill, save,
export DSN."""
import pcbnew, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-layout-v2.kicad_pcb")
DSN = os.path.join(HERE, "novapcb-layout-v2.dsn")
PLANE_NETS = {"GND", "+3V3", "+3V3A", "+5V"}
VIA_OUTER_MM = 0.60
VIA_DRILL_MM = 0.30

brd = pcbnew.LoadBoard(PCB)
print(f"[step2] loaded board")
placed = 0
skipped_th = 0
for fp in brd.GetFootprints():
    for pad in fp.Pads():
        if not pad.GetNet(): continue
        nn = str(pad.GetNet().GetNetname())
        if nn not in PLANE_NETS: continue
        if not (pad.IsOnLayer(pcbnew.F_Cu) or pad.IsOnLayer(pcbnew.B_Cu)): continue
        if pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
            skipped_th += 1
            continue
        bb = pad.GetBoundingBox()
        cx = bb.GetX() + bb.GetWidth() // 2
        cy = bb.GetY() + bb.GetHeight() // 2
        via = pcbnew.PCB_VIA(brd)
        via.SetPosition(pcbnew.VECTOR2I(cx, cy))
        via.SetWidth(int(VIA_OUTER_MM * 1e6))
        via.SetDrill(int(VIA_DRILL_MM * 1e6))
        via.SetViaType(pcbnew.VIATYPE_THROUGH)
        via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        via.SetNet(pad.GetNet())
        brd.Add(via)
        placed += 1
print(f"[step2] placed {placed} plane vias; skipped {skipped_th} TH")
# Refill zones
pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
# Export DSN before save (avoids the LoadBoard-after-SaveBoard SwigPyObject issue)
if os.path.exists(DSN):
    os.remove(DSN)
ok = pcbnew.ExportSpecctraDSN(brd, DSN)
if not ok:
    print(f"[step2] !! DSN export failed"); sys.exit(2)
pcbnew.SaveBoard(PCB, brd)
print(f"[step2] saved board + exported DSN ({os.path.getsize(DSN)} bytes)")
