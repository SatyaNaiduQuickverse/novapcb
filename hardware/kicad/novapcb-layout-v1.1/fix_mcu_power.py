#!/usr/bin/env python3
"""Step A: MCU +3V3/GND pin connectivity via decap traces + stitch retry.
"""
import os, math, subprocess, re
import pcbnew

HERE = os.path.expanduser("~/novapcb/hardware/kicad/novapcb-layout-v1.1")
PCB = os.path.join(HERE, "novapcb-layout-v1.1.kicad_pcb")
DRC_TMP = "/tmp/_a_drc.txt"

VIA_DIA = 0.60
VIA_DRILL = 0.30


def drc_count():
    subprocess.run(["kicad-cli","pcb","drc","--severity-error","--format","report",
                    "--output",DRC_TMP,"--units","mm",PCB],
                   capture_output=True, text=True)
    with open(DRC_TMP) as f: t = f.read()
    e = re.search(r"Found (\d+) DRC violation", t)
    u = re.search(r"Found (\d+) unconnected pad", t)
    return (int(e.group(1)) if e else 0, int(u.group(1)) if u else 0)


def find_pads_by_net(brd, net_name):
    """Return [(ref, num, x_mm, y_mm, pad_obj)] for all pads on this net."""
    out = []
    for fp in brd.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname() == net_name:
                pos = p.GetPosition()
                out.append((fp.GetReference(), p.GetNumber(),
                              pos.x/1e6, pos.y/1e6, p))
    return out


def has_via_near(brd, x, y, net_name, radius_mm=1.0):
    """Check if a via on net_name exists within radius."""
    for t in brd.GetTracks():
        if not isinstance(t, pcbnew.PCB_VIA): continue
        if t.GetNetname() != net_name: continue
        p = t.GetPosition()
        if math.hypot(p.x/1e6 - x, p.y/1e6 - y) < radius_mm:
            return True
    return False


def has_trace_between(brd, x1, y1, x2, y2, net_name, tol=0.10):
    """Check if there's a trace from (x1,y1) to (x2,y2) on the same net."""
    for t in brd.GetTracks():
        if isinstance(t, pcbnew.PCB_VIA): continue
        if t.GetNetname() != net_name: continue
        s = t.GetStart(); e = t.GetEnd()
        # Either endpoint matches start, other endpoint matches end
        if (math.hypot(s.x/1e6-x1, s.y/1e6-y1) < tol and math.hypot(e.x/1e6-x2, e.y/1e6-y2) < tol) or \
           (math.hypot(s.x/1e6-x2, s.y/1e6-y2) < tol and math.hypot(e.x/1e6-x1, e.y/1e6-y1) < tol):
            return True
    return False


def add_track_simple(brd, net_obj, x1, y1, x2, y2, layer, w=0.25):
    t = pcbnew.PCB_TRACK(brd)
    t.SetStart(pcbnew.VECTOR2I(int(x1*1e6), int(y1*1e6)))
    t.SetEnd(pcbnew.VECTOR2I(int(x2*1e6), int(y2*1e6)))
    t.SetWidth(int(w*1e6))
    t.SetLayer(layer)
    t.SetNet(net_obj)
    brd.Add(t)


def main():
    brd = pcbnew.LoadBoard(PCB)
    err0, unc0 = drc_count()
    print(f"[baseline] err={err0} unc={unc0}", flush=True)

    nets = {str(k): v for k, v in brd.GetNetsByName().asdict().items()}

    # Find U1 power pins (+3V3, +5V) and GND pins reported unconnected
    # Pull pad positions from PCB; for each that's NOT near a same-net via,
    # find nearest same-net cap and add a trace to it.

    n_traces = 0
    for net in ["+3V3", "+5V", "GND"]:
        pads = find_pads_by_net(brd, net)
        # MCU power pins (U1) + power pins in other ICs that don't have a stitch
        for ref, num, px, py, pad in pads:
            if not (ref == "U1" or ref.startswith("U")):
                continue
            # Skip if pad has a same-net via within 0.6mm (already stitched)
            if has_via_near(brd, px, py, net, radius_mm=0.7):
                continue
            # Find nearest same-net cap pad with a stitch via
            best = None; best_d = 3.0  # 3mm max
            for ref2, num2, px2, py2, pad2 in pads:
                if ref2.startswith("C") or ref2.startswith("FB"):
                    if has_via_near(brd, px2, py2, net, radius_mm=0.7):
                        d = math.hypot(px-px2, py-py2)
                        if d < best_d:
                            best_d = d
                            best = (ref2, px2, py2)
            if best is None: continue
            ref2, px2, py2 = best
            # Add a short trace from pad to cap pad on F.Cu (or B.Cu if pad is B.Cu)
            net_obj = nets[net]
            layer = pcbnew.F_Cu if pad.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu
            add_track_simple(brd, net_obj, px, py, px2, py2, layer)
            n_traces += 1
            print(f"  {ref}.{num} ({net}) → {ref2} via trace ({best_d:.2f}mm)", flush=True)
    print(f"[traces] {n_traces} MCU-power → decap connection traces added")

    pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
    pcbnew.SaveBoard(PCB, brd)
    err1, unc1 = drc_count()
    print(f"[after-traces] err={err1} unc={unc1}  delta_unc={unc1-unc0:+d}", flush=True)


if __name__ == "__main__":
    main()
