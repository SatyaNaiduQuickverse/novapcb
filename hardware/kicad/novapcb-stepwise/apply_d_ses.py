#!/usr/bin/env python3
"""Apply D-routing SES wires + vias to board. Reuses sense-sub-step's
proven SES parser (sha d82f08a's apply_sense_ses.py)."""
import os
import re
import sys
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")
SES = os.path.join(HERE, "d_routing.ses")

D_NETS = {
    "SPI1_SCK", "SPI1_MISO", "SPI1_MOSI", "IMU1_CS",
    "SPI2_SCK", "SPI2_MISO", "SPI2_MOSI", "IMU2_ACC_CS", "IMU2_GYR_CS",
    "SPI3_SCK", "SPI3_MISO", "SPI3_MOSI", "IMU3_CS",
    "IMU2_ACC_INT1", "IMU2_GYR_INT3", "IMU3_INT1",
    "HEATER_PWM",
}

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
    v.SetWidth(_mm(0.50))
    v.SetDrill(_mm(0.30))
    v.SetNet(net)
    brd.Add(v)


def main():
    print(f"=== Apply D-routing SES wires ===\n", flush=True)
    if not os.path.exists(SES):
        print(f"!!! SES missing: {SES}")
        return 1
    all_nets = parse_ses(SES)
    d = {n: s for n, s in all_nets.items() if n in D_NETS}
    print(f"Found {len(d)} of {len(D_NETS)} D nets in SES")
    for n in sorted(D_NETS):
        if n in d:
            segs = d[n]
            tr = sum(1 for s in segs if s["type"] == "wire")
            vi = sum(1 for s in segs if s["type"] == "via")
            pts = sum(len(s["points"]) for s in segs if s["type"] == "wire")
            print(f"  {n:<22}: {tr} wires ({pts} pts), {vi} vias", flush=True)
        else:
            print(f"  {n:<22}: MISSING from SES", flush=True)

    brd = pcbnew.LoadBoard(PCB)
    n_tr = 0
    n_vi = 0
    for name, segs in d.items():
        net_obj = get_net(brd, name)
        if net_obj is None:
            print(f"  WARN: net '{name}' not on board, skip")
            continue
        for seg in segs:
            if seg["type"] == "wire":
                layer = LAYER_MAP.get(seg["layer"])
                if layer is None:
                    continue
                w_mm = seg["width_um"] / 10000.0
                pts = seg["points"]
                for (x1u, y1u), (x2u, y2u) in zip(pts[:-1], pts[1:]):
                    add_track(brd, x1u / 10000.0, -y1u / 10000.0,
                              x2u / 10000.0, -y2u / 10000.0,
                              layer, w_mm, net_obj)
                    n_tr += 1
            else:
                add_via(brd, seg["x_um"] / 10000.0, -seg["y_um"] / 10000.0, net_obj)
                n_vi += 1
    print(f"\nAdded {n_tr} track segments, {n_vi} vias", flush=True)

    # Refill zones
    for z in brd.Zones():
        if hasattr(z, "UnFill"):
            z.UnFill()
    filler = pcbnew.ZONE_FILLER(brd)
    filler.Fill(list(brd.Zones()))
    pcbnew.SaveBoard(PCB, brd)
    print(f"Refilled + saved {PCB}\n", flush=True)

    # Per-net Rule-9 cluster walk
    print("=== Rule-9 per-net cluster walk ===", flush=True)
    brd2 = pcbnew.LoadBoard(PCB)
    for name in sorted(D_NETS):
        n_trk = 0
        n_via = 0
        total = 0.0
        layers = set()
        for trk in brd2.GetTracks():
            if trk.GetNetname() != name:
                continue
            if trk.GetClass() == "PCB_VIA":
                n_via += 1
            else:
                n_trk += 1
                s = trk.GetStart()
                e = trk.GetEnd()
                dx = (s.x - e.x) / 1e6
                dy = (s.y - e.y) / 1e6
                total += (dx * dx + dy * dy) ** 0.5
                layers.add(brd2.GetLayerName(trk.GetLayer()))
        status = "PASS" if n_trk >= 2 else "FAIL"
        print(f"  {name:<22}: {n_trk:>2} tracks, {n_via:>2} vias, len={total:5.1f}mm "
              f"L={sorted(layers)}  {status}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
