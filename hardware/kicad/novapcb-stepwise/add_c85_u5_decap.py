#!/usr/bin/env python3
"""Add C85 (100nF U5 USB-C VBUS decap) to board.

2-phase subprocess workflow per KiCad 9 SWIG-clean pattern.
Position: (74.5, 28.5) per prior task #98 placement (NW of U5 USB-C ESD chip).
"""
import os, re, sys, subprocess, pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")
NET_PATH = os.path.join(HERE, "..", "novapcb", "novapcb.net")
X, Y = 74.5, 28.5
REF = "C85"
FP_LIB = "/usr/share/kicad/footprints/Capacitor_SMD.pretty"
FP_NAME = "C_0402_1005Metric"

def add():
    fp = pcbnew.FootprintLoad(FP_LIB, FP_NAME)
    if fp is None:
        raise RuntimeError(f"FootprintLoad {FP_LIB}:{FP_NAME} failed")
    fp.SetReference(REF)
    fp.SetValue("100nF")
    fp.SetPosition(pcbnew.VECTOR2I(int(X*1e6), int(Y*1e6)))
    brd = pcbnew.LoadBoard(PCB)
    # Idempotency: remove old C85 if exists
    for old in list(brd.GetFootprints()):
        if old.GetReference() == REF:
            brd.Remove(old)
    brd.Add(fp)
    pcbnew.SaveBoard(PCB, brd)
    print(f"add: {REF} placed at ({X},{Y})")

def nets():
    with open(NET_PATH) as f:
        text = f.read()
    netmap = {}
    for m in re.finditer(r'\(net\s+\(code "?\d+"?\)\s+\(name "?([^"\)]+)"?\)(.*?)(?=\(net\s+\(code|\Z)',
                         text, re.DOTALL):
        name = m.group(1).strip()
        for n in re.finditer(r'\(node\s+\(ref "?(\w+)"?\)\s+\(pin "?(\w+)"?\)', m.group(2)):
            if n.group(1) == REF:
                netmap[n.group(2)] = name
    print(f"nets: {netmap}")
    brd = pcbnew.LoadBoard(PCB)
    fp = next((f for f in brd.GetFootprints() if f.GetReference()==REF), None)
    if fp is None:
        raise RuntimeError(f"{REF} missing after add")
    for pad in fp.Pads():
        nm = pad.GetPadName()
        if nm in netmap:
            net = brd.FindNet(netmap[nm])
            if net is None:
                net = pcbnew.NETINFO_ITEM(brd, netmap[nm])
                brd.Add(net)
            pad.SetNet(net)
    for z in brd.Zones():
        if hasattr(z, "UnFill"): z.UnFill()
    pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
    pcbnew.SaveBoard(PCB, brd)
    print("nets: saved with refilled zones")

if __name__ == "__main__":
    phase = sys.argv[1] if len(sys.argv) > 1 else "all"
    if phase == "all":
        for ph in ("add", "nets"):
            r = subprocess.run([sys.executable, __file__, ph], check=False)
            if r.returncode != 0: raise SystemExit(r.returncode)
    elif phase == "add":
        add()
    elif phase == "nets":
        nets()
