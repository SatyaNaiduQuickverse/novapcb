#!/usr/bin/env python3
"""Apply CAN wires from Freerouting's gps_routing.ses to the board (task #45).

Bypass KiCad's ImportSpecctraSES (returns False on stripped DSN per
project pattern). Parse SES manually for the 8 MOT* nets, add their
wires/vias as PCB_TRACK/PCB_VIA, refill zones, save.

SES coordinate convention: KiCad export uses micrometers, Y flipped.
Wire paths inside SES use µm units, Y negative.
Conversion: x_mm = x_um / 10000.0; y_mm = -y_um / 10000.0
"""
import os
import re
import sys
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")
SES = os.path.join(HERE, "gps_routing.ses")

H_NETS = {"GPS1_TX"}

LAYER_MAP = {"F.Cu": pcbnew.F_Cu, "B.Cu": pcbnew.B_Cu}


def _mm(x):
    return pcbnew.FromMM(x)


def get_net(brd, name):
    seen = {}
    for fp in list(brd.GetFootprints()):
        for pad in fp.Pads():
            n = pad.GetNet()
            if n is not None:
                seen[pad.GetNetname()] = n
    return seen.get(name)


def parse_ses_nets(ses_path):
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
                j += 1
                break
        j += 1
    net_out = text[no_pos:j]
    i = 0
    while True:
        m = re.search(r'\(net\s+"([^"]+)"', net_out[i:])
        if not m:
            break
        start = i + m.start()
        name = m.group(1)
        k = start
        depth = 0
        while k < len(net_out):
            if net_out[k] == "(":
                depth += 1
            elif net_out[k] == ")":
                depth -= 1
                if depth == 0:
                    k += 1
                    break
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
            x_um = int(vm.group(1))
            y_um = int(vm.group(2))
            segs.append({"type": "via", "x_um": x_um, "y_um": y_um})
        out[name] = segs
        i = k
    return out


def add_track(brd, x1_mm, y1_mm, x2_mm, y2_mm, layer, width_mm, net_obj):
    t = pcbnew.PCB_TRACK(brd)
    t.SetStart(pcbnew.VECTOR2I(_mm(x1_mm), _mm(y1_mm)))
    t.SetEnd(pcbnew.VECTOR2I(_mm(x2_mm), _mm(y2_mm)))
    t.SetWidth(_mm(width_mm))
    t.SetLayer(layer)
    t.SetNet(net_obj)
    brd.Add(t)


def add_via(brd, x_mm, y_mm, net_obj, dia_mm=0.50, drill_mm=0.30):
    v = pcbnew.PCB_VIA(brd)
    v.SetPosition(pcbnew.VECTOR2I(_mm(x_mm), _mm(y_mm)))
    v.SetWidth(_mm(dia_mm))
    v.SetDrill(_mm(drill_mm))
    v.SetNet(net_obj)
    brd.Add(v)


def main():
    print(f"=== Apply H↔C wires from {SES} ===\n")
    if not os.path.exists(SES):
        print(f"!!! SES missing: {SES}")
        return 1

    all_nets = parse_ses_nets(SES)
    h_in_ses = {n: segs for n, segs in all_nets.items() if n in H_NETS}
    print(f"Found {len(h_in_ses)} of {len(H_NETS)} MOT* nets in SES")
    for name in sorted(H_NETS):
        if name in h_in_ses:
            segs = h_in_ses[name]
            n_wires = sum(1 for s in segs if s["type"] == "wire")
            n_vias = sum(1 for s in segs if s["type"] == "via")
            n_pts = sum(len(s["points"]) for s in segs if s["type"] == "wire")
            print(f"  {name:<6}: {n_wires} wires ({n_pts} pts), {n_vias} vias")
        else:
            print(f"  {name:<6}: MISSING from SES")

    brd = pcbnew.LoadBoard(PCB)
    n_tr = 0; n_vi = 0
    for name, segs in h_in_ses.items():
        net_obj = get_net(brd, name)
        if net_obj is None:
            print(f"  WARN: net '{name}' not on board, skipping")
            continue
        for seg in segs:
            if seg["type"] == "wire":
                layer = LAYER_MAP.get(seg["layer"])
                if layer is None:
                    print(f"  WARN: unknown layer {seg['layer']} on {name}")
                    continue
                width_mm = seg["width_um"] / 10000.0
                pts = seg["points"]
                for (x1_um, y1_um), (x2_um, y2_um) in zip(pts[:-1], pts[1:]):
                    add_track(brd,
                              x1_um / 10000.0, -y1_um / 10000.0,
                              x2_um / 10000.0, -y2_um / 10000.0,
                              layer, width_mm, net_obj)
                    n_tr += 1
            else:
                add_via(brd,
                        seg["x_um"] / 10000.0, -seg["y_um"] / 10000.0,
                        net_obj)
                n_vi += 1
    print(f"\nAdded {n_tr} track segments, {n_vi} vias\n")

    for z in brd.Zones():
        if hasattr(z, "UnFill"):
            z.UnFill()
    filler = pcbnew.ZONE_FILLER(brd)
    filler.Fill(list(brd.Zones()))
    pcbnew.SaveBoard(PCB, brd)
    print(f"Refilled zones + saved {PCB}\n")

    print("=== Per-net Rule-9 cluster walk ===")
    brd2 = pcbnew.LoadBoard(PCB)
    fails = 0
    for name in sorted(H_NETS):
        n_trk = 0; n_via = 0; total = 0.0
        layers = set()
        for trk in brd2.GetTracks():
            if trk.GetNetname() != name:
                continue
            if trk.GetClass() == "PCB_VIA":
                n_via += 1
            else:
                n_trk += 1
                s = trk.GetStart(); e = trk.GetEnd()
                dx = (s.x - e.x) / 1e6
                dy = (s.y - e.y) / 1e6
                total += (dx * dx + dy * dy) ** 0.5
                layers.add(brd2.GetLayerName(trk.GetLayer()))
        status = "PASS" if n_trk >= 1 else "FAIL"
        print(f"  {name:<6}: {n_trk:>2} tracks, {n_via:>2} vias, "
              f"len={total:5.1f}mm  layers={sorted(layers)}  {status}")
        if n_trk < 1:
            fails += 1
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
