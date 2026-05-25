#!/usr/bin/env python3
"""Apply +3V3_IMU SES wires + vias to board."""
import os
import re
import sys
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")
SES = os.path.join(HERE, "3v3_imu.ses")

TARGET_NET = "+3V3_IMU"
LAYER_MAP = {"F.Cu": pcbnew.F_Cu, "B.Cu": pcbnew.B_Cu}


def _mm(x): return pcbnew.FromMM(x)


def get_net(brd, name):
    seen = {}
    for fp in brd.GetFootprints():
        for pad in fp.Pads():
            n = pad.GetNet()
            if n is not None:
                seen[pad.GetNetname()] = n
    return seen.get(name)


def parse_ses(ses_path):
    with open(ses_path) as f:
        text = f.read()
    out = {}
    no_pos = text.find("(network_out")
    if no_pos < 0:
        return out
    j = no_pos
    depth = 0
    while j < len(text):
        if text[j] == "(":
            depth += 1
        elif text[j] == ")":
            depth -= 1
            if depth == 0:
                j += 1; break
        j += 1
    net_out = text[no_pos:j]
    i = 0
    while True:
        m = re.search(r'\(net\s+"([^"]+)"', net_out[i:])
        if not m: break
        start = i + m.start()
        name = m.group(1)
        k = start; depth = 0
        while k < len(net_out):
            if net_out[k] == "(": depth += 1
            elif net_out[k] == ")":
                depth -= 1
                if depth == 0: k += 1; break
            k += 1
        net_block = net_out[start:k]
        segs = []
        for wm in re.finditer(r'\(wire\s*\(path\s+(\S+)\s+(\d+)([^)]+)\)', net_block):
            layer = wm.group(1)
            width_um = int(wm.group(2))
            coords = [int(c) for c in wm.group(3).split()]
            points = list(zip(coords[0::2], coords[1::2]))
            segs.append({"type": "wire", "layer": layer, "width_um": width_um, "points": points})
        for vm in re.finditer(r'\(via\s+"[^"]+"\s+(-?\d+)\s+(-?\d+)', net_block):
            segs.append({"type": "via", "x_um": int(vm.group(1)), "y_um": int(vm.group(2))})
        out[name] = segs
        i = k
    return out


def add_track(brd, x1, y1, x2, y2, layer, w_mm, net):
    t = pcbnew.PCB_TRACK(brd)
    t.SetStart(pcbnew.VECTOR2I(_mm(x1), _mm(y1)))
    t.SetEnd(pcbnew.VECTOR2I(_mm(x2), _mm(y2)))
    t.SetWidth(_mm(w_mm))
    t.SetLayer(layer)
    t.SetNet(net)
    brd.Add(t)


def add_via(brd, x, y, net):
    v = pcbnew.PCB_VIA(brd)
    v.SetPosition(pcbnew.VECTOR2I(_mm(x), _mm(y)))
    v.SetWidth(_mm(0.50)); v.SetDrill(_mm(0.30))
    v.SetNet(net)
    brd.Add(v)


def main():
    print(f"=== Apply +3V3_IMU SES wires ===\n", flush=True)
    all_nets = parse_ses(SES)
    if TARGET_NET not in all_nets:
        print(f"!!! {TARGET_NET} not in SES")
        return 1
    segs = all_nets[TARGET_NET]
    n_wires = sum(1 for s in segs if s["type"] == "wire")
    n_vias = sum(1 for s in segs if s["type"] == "via")
    pts = sum(len(s["points"]) for s in segs if s["type"] == "wire")
    print(f"  {TARGET_NET}: {n_wires} wires ({pts} pts), {n_vias} vias", flush=True)

    brd = pcbnew.LoadBoard(PCB)
    net_obj = get_net(brd, TARGET_NET)
    if net_obj is None:
        print(f"!!! {TARGET_NET} net not on board")
        return 1

    n_tr = 0
    n_vi = 0
    for seg in segs:
        if seg["type"] == "wire":
            layer = LAYER_MAP.get(seg["layer"])
            if layer is None: continue
            w_mm = seg["width_um"] / 10000.0
            ps = seg["points"]
            for (x1u, y1u), (x2u, y2u) in zip(ps[:-1], ps[1:]):
                add_track(brd, x1u / 10000.0, -y1u / 10000.0,
                          x2u / 10000.0, -y2u / 10000.0, layer, w_mm, net_obj)
                n_tr += 1
        else:
            add_via(brd, seg["x_um"] / 10000.0, -seg["y_um"] / 10000.0, net_obj)
            n_vi += 1
    print(f"Added {n_tr} tracks, {n_vi} vias", flush=True)

    for z in brd.Zones():
        if hasattr(z, "UnFill"): z.UnFill()
    pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
    pcbnew.SaveBoard(PCB, brd)
    print(f"Refilled + saved", flush=True)

    # Per-net cluster walk
    brd2 = pcbnew.LoadBoard(PCB)
    n_trk = 0; n_via = 0; total = 0.0; layers = set()
    for trk in brd2.GetTracks():
        if trk.GetNetname() != TARGET_NET: continue
        if trk.GetClass() == "PCB_VIA": n_via += 1
        else:
            n_trk += 1
            s = trk.GetStart(); e = trk.GetEnd()
            dx = (s.x - e.x) / 1e6; dy = (s.y - e.y) / 1e6
            total += (dx*dx + dy*dy) ** 0.5
            layers.add(brd2.GetLayerName(trk.GetLayer()))
    print(f"\n=== Rule-9 cluster walk ===")
    print(f"  {TARGET_NET}: {n_trk} tracks, {n_via} vias, len={total:.1f}mm L={sorted(layers)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
