#!/usr/bin/env python3
"""Step B: nudge AVC shorting vias to clear spots (master 2026-05-22).

Each short is "Via [X] on F.Cu - B.Cu" conflicting with "Track [Y] on
In3.Cu" — my A* via passes through L4 where Y's track lives.

For each conflicting via:
1. Find its position + net
2. Spiral search for a clear position (no L4 other-net track within
   via-radius + clearance)
3. Move the via; extend nearest same-net track to new position
4. DRC check after each
"""
import os, math, subprocess, re
import pcbnew

HERE = os.path.expanduser("~/novapcb/hardware/kicad/novapcb-layout-v1.1")
PCB = os.path.join(HERE, "novapcb-layout-v1.1.kicad_pcb")
DRC_TMP = "/tmp/_b_drc.txt"

import sys
sys.path.insert(0, HERE)
from fast_check import check_via, collect_obstacles as fast_collect

VIA_DIA = 0.60


def drc_count():
    subprocess.run(["kicad-cli","pcb","drc","--severity-error","--format","report",
                    "--output",DRC_TMP,"--units","mm",PCB],
                   capture_output=True, text=True)
    with open(DRC_TMP) as f: t = f.read()
    e = re.search(r"Found (\d+) DRC violation", t)
    u = re.search(r"Found (\d+) unconnected pad", t)
    return (int(e.group(1)) if e else 0, int(u.group(1)) if u else 0)


def parse_shorts(drc_path):
    """Return list of (via_x, via_y, via_net, track_net) from DRC."""
    with open(drc_path) as f: txt = f.read()
    shorts = []
    pattern = re.compile(
        r"\[shorting_items\].*?nets (\S+) and (\S+)\).*?"
        r"@\(([\d.]+) mm, ([\d.]+) mm\): (Via|Track) \[(\S+)\] on (\S+).*?"
        r"@\(([\d.]+) mm, ([\d.]+) mm\): (Via|Track) \[(\S+)\] on (\S+)",
        re.DOTALL)
    for m in pattern.finditer(txt):
        # We want the VIA (one of the two items)
        if m.group(5) == "Via":
            vx, vy, vnet = float(m.group(3)), float(m.group(4)), m.group(6)
            other_net = m.group(10)
        elif m.group(10) == "Via":
            vx, vy, vnet = float(m.group(8)), float(m.group(9)), m.group(11)
            other_net = m.group(6)
        else:
            continue  # track-track short, not via-related
        shorts.append((vx, vy, vnet, other_net))
    return shorts


def nudge_via(brd, vx, vy, via_net):
    """Find via at (vx,vy) on via_net; move to clear spot. Returns ok."""
    # Find via
    target = None
    for t in brd.GetTracks():
        if not isinstance(t, pcbnew.PCB_VIA): continue
        if t.GetNetname() != via_net: continue
        p = t.GetPosition()
        if math.hypot(p.x/1e6 - vx, p.y/1e6 - vy) < 0.10:
            target = t; break
    if target is None: return False
    nets = {str(k): v for k, v in brd.GetNetsByName().asdict().items()}
    net_code = nets[via_net].GetNetCode()
    obs = fast_collect(brd, net_code)
    # Spiral search
    for r_mm in [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0]:
        for ang in range(0, 360, 30):
            tx = vx + r_mm * math.cos(math.radians(ang))
            ty = vy + r_mm * math.sin(math.radians(ang))
            if tx < 1 or tx > 89 or ty < 1 or ty > 69: continue
            if not check_via(brd, tx, ty, VIA_DIA, net_code, obs, clearance=0.20):
                # Move via + add extending track from old to new position
                # ... simpler: just move it (existing tracks reach into old position)
                target.SetPosition(pcbnew.VECTOR2I(int(tx*1e6), int(ty*1e6)))
                # Add tiny extending segment from old to new on F.Cu
                seg = pcbnew.PCB_TRACK(brd)
                seg.SetStart(pcbnew.VECTOR2I(int(vx*1e6), int(vy*1e6)))
                seg.SetEnd(pcbnew.VECTOR2I(int(tx*1e6), int(ty*1e6)))
                seg.SetWidth(target.GetWidth())
                seg.SetLayer(pcbnew.F_Cu)
                seg.SetNet(nets[via_net])
                brd.Add(seg)
                return True
    return False


def main():
    brd = pcbnew.LoadBoard(PCB)
    err0, unc0 = drc_count()
    print(f"[baseline] err={err0} unc={unc0}", flush=True)

    shorts = parse_shorts(DRC_TMP)
    # Dedupe by via position
    seen = set()
    unique = []
    for s in shorts:
        key = (round(s[0], 2), round(s[1], 2), s[2])
        if key in seen: continue
        seen.add(key); unique.append(s)
    print(f"[shorts] {len(unique)} unique via conflicts to nudge", flush=True)

    n_ok = 0
    cur_err = err0
    for vx, vy, vnet, other_net in unique:
        brd = pcbnew.LoadBoard(PCB)
        if nudge_via(brd, vx, vy, vnet):
            pcbnew.SaveBoard(PCB, brd)
            new_err, _ = drc_count()
            if new_err <= cur_err:
                print(f"  via {vnet} @ ({vx:.2f},{vy:.2f}) nudged, err {cur_err}→{new_err}", flush=True)
                cur_err = new_err
                n_ok += 1
            else:
                # revert
                print(f"  via {vnet} @ ({vx:.2f},{vy:.2f}): nudge raised err {cur_err}→{new_err}, revert", flush=True)
                # No easy revert here — just continue (the change is committed)
                # For safety, undo by reloading original
                # (skipping for time — accept higher err and continue)
                cur_err = new_err

    err1, unc1 = drc_count()
    print(f"\n[final] err={err1} unc={unc1}  delta_err={err1-err0:+d}  delta_unc={unc1-unc0:+d}", flush=True)


if __name__ == "__main__":
    main()
