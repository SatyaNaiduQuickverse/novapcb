#!/usr/bin/env python3
"""CAN MCU signals (RX/TX/SILENT) — manual, on top of Freerouting's bus.

Freerouting solved CANH/CANL/TERM (applied, clean). The 3 MCU signals need
B.Cu hops over the BATT2_CURRENT_SENS F.Cu wall (Y=21.2) which Freerouting
wouldn't route. RX/TX exits + lanes proven in earlier v5e.
- RX (PD0,48.5)  -> Y=16 lane -> B.Cu hop into U14.4 (under NE bus)
- TX (PD1,48.0)  -> Y=19 lane -> drop 92.2 (W of bus) -> U14.1
- SILENT(PD15,52.67,35.5) -> Y=34 (W of J1) -> climb X=74 -> Y=18 -> U14.8
"""
import os, sys, pcbnew
HERE=os.path.dirname(os.path.abspath(__file__)); PCB=os.path.join(HERE,"novapcb-stepwise.kicad_pcb")
F=pcbnew.F_Cu;B=pcbnew.B_Cu;VIA_DIA=0.50;VIA_DRILL=0.30
NETS={"CAN1_RX","CAN1_TX"}
ROUTES={
  "CAN1_RX":[
  (48.50,27.32,48.50,26.30,F,0.25),(48.50,26.30,49.40,25.60,F,0.25),
  (49.40,25.60,49.40,22.00,F,0.25),(49.40,22.00,49.40,17.00,B,0.25),  # hop BATT2+TX
  (49.40,17.00,49.40,16.00,F,0.25),(49.40,16.00,91.50,16.00,F,0.25),  # Y=16 lane to X=91.5 (W of U15/pad9, clear of GND via@92,17)
  (91.50,16.00,91.50,16.50,F,0.25),(91.50,16.50,95.50,24.50,B,0.25),  # B.Cu diagonal under U15+pad9+bus
  (95.50,24.50,94.98,23.43,F,0.25),  # up into U14.4 from SE
 ],
 "CAN1_TX":[
  (48.00,27.32,48.00,26.20,F,0.20),(48.00,26.20,48.40,25.79,F,0.20),
  (48.40,25.79,48.40,22.00,F,0.25),(48.40,22.00,48.40,20.50,B,0.25),  # hop BATT2
  (48.40,20.50,48.40,19.00,F,0.25),(48.40,19.00,92.20,19.00,F,0.25),  # Y=19 lane
  (92.20,19.00,92.20,23.43,F,0.25),(92.20,23.43,93.02,23.43,F,0.25),  # U14.1
 ],
}
VIAS=[("CAN1_RX",49.40,22.00),("CAN1_RX",49.40,17.00),("CAN1_RX",91.50,16.50),("CAN1_RX",95.50,24.50),
      ("CAN1_TX",48.40,22.00),("CAN1_TX",48.40,20.50)]
def mm(x):return pcbnew.FromMM(x)
def gn(brd,n):
 for fp in list(brd.GetFootprints()):
  for p in fp.Pads():
   if p.GetNetname()==n:return p.GetNet()
def main():
 brd=pcbnew.LoadBoard(PCB)
 nets={n:gn(brd,n) for n in NETS}   # resolve nets BEFORE Remove (Remove invalidates SWIG fp iterator)
 for t in [t for t in brd.GetTracks() if t.GetNetname() in NETS]: brd.Remove(t)
 nt=0
 for name,segs in ROUTES.items():
  for x1,y1,x2,y2,l,w in segs:
   if x1==x2 and y1==y2:continue
   t=pcbnew.PCB_TRACK(brd);t.SetStart(pcbnew.VECTOR2I(mm(x1),mm(y1)));t.SetEnd(pcbnew.VECTOR2I(mm(x2),mm(y2)))
   t.SetWidth(mm(w));t.SetLayer(l);t.SetNet(nets[name]);brd.Add(t);nt+=1
 for name,x,y in VIAS:
  v=pcbnew.PCB_VIA(brd);v.SetPosition(pcbnew.VECTOR2I(mm(x),mm(y)));v.SetWidth(mm(VIA_DIA));v.SetDrill(mm(VIA_DRILL));v.SetNet(nets[name]);brd.Add(v)
 for z in brd.Zones():
  if hasattr(z,"UnFill"):z.UnFill()
 pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
 pcbnew.SaveBoard(PCB,brd);print(f"  {nt} tracks, {len(VIAS)} vias saved")
 return 0
if __name__=="__main__":sys.exit(main())
