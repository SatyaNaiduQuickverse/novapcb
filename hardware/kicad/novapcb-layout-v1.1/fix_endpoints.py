#!/usr/bin/env python3
"""Fix connectivity gaps on the 14 A*-routed residuals (master 2026-05-22 step 1).

After astar_via_cleanup, the routes are topologically right but their
endpoints land on cell-aligned coords that don't quite touch the actual
pad centers (gaps of ~0.07-0.10mm). DRC reports them as unconnected.

This script walks each of the 14 residual nets, finds the closest track
endpoint to each pad on that net, and if not touching the pad center,
adds a short connecting segment.

Goal per master: unconnected 143 → ~8 (just the GND seg).
"""
import os, math, json, subprocess, re
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-layout-v1.1.kicad_pcb")
DRC_TMP = "/tmp/_ef_drc.txt"

import sys
sys.path.insert(0, HERE)
from per_net_router import add_track, pad_center, pad_layer, net_width, F_CU, B_CU
IN3_CU = pcbnew.In3_Cu
LAYERS = [F_CU, IN3_CU, B_CU]

RESIDUALS = [
    "BATT_CURRENT_SENS", "IMU3_CS", "IMU3_INT1", "MOT1", "MOT2", "NRST",
    "SPI1_SCK", "SPI1_MISO", "SPI1_MOSI",
    "SPI3_SCK", "SPI3_MISO", "SPI3_MOSI",
    "SWCLK", "SWDIO",
]

# Tolerance for "touching" a pad (mm)
TOUCH_TOL = 0.001  # require ACTUAL contact (sub-micron); anything less is a gap


def drc_count():
    subprocess.run(["kicad-cli","pcb","drc","--severity-error","--format","report",
                    "--output",DRC_TMP,"--units","mm",PCB],
                   capture_output=True, text=True)
    txt = open(DRC_TMP).read()
    e = re.search(r"Found (\d+) DRC violation", txt)
    u = re.search(r"Found (\d+) unconnected pad", txt)
    return (int(e.group(1)) if e else 0, int(u.group(1)) if u else 0)


def point_seg_dist(px, py, sx, sy, ex, ey):
    """Distance from point to line segment."""
    dx, dy = ex-sx, ey-sy
    L2 = dx*dx + dy*dy
    if L2 < 1e-12: return math.hypot(px-sx, py-sy)
    t = max(0.0, min(1.0, ((px-sx)*dx + (py-sy)*dy) / L2))
    cx, cy = sx + t*dx, sy + t*dy
    return math.hypot(px-cx, py-cy)


def fix_net_endpoints(brd, net_name):
    """For this net: find all pads + all tracks. For each pad, if no track
    endpoint within TOUCH_TOL, find nearest track endpoint and add a short
    connecting segment."""
    nets = {str(k): v for k, v in brd.GetNetsByName().asdict().items()}
    net_obj = nets[net_name]
    net_code = net_obj.GetNetCode()
    w = net_width(net_name)

    # Collect pads + tracks on this net
    pads = []
    for fp in brd.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname() == net_name:
                pads.append((fp.GetReference(), p.GetNumber(), pad_center(p),
                              [L for L in LAYERS if p.IsOnLayer(L)]))
    tracks = []  # (ref_obj, layer, sx, sy, ex, ey)
    for t in brd.GetTracks():
        if isinstance(t, pcbnew.PCB_VIA): continue
        if t.GetNetname() != net_name: continue
        s = t.GetStart(); e = t.GetEnd()
        tracks.append((t.GetLayer(), s.x/1e6, s.y/1e6, e.x/1e6, e.y/1e6))

    # For each pad, check if any track endpoint or via is within TOUCH_TOL
    n_extensions = 0
    for ref, pn, (px, py), pad_layers in pads:
        # Check if any track touches this pad
        touching = False
        for layer, sx, sy, ex, ey in tracks:
            if layer not in pad_layers: continue
            if (math.hypot(px-sx, py-sy) < TOUCH_TOL or
                math.hypot(px-ex, py-ey) < TOUCH_TOL or
                point_seg_dist(px, py, sx, sy, ex, ey) < TOUCH_TOL):
                touching = True; break
        if touching: continue
        # Check vias too — via at pad center is fine
        # Find nearest track endpoint on a compatible layer
        nearest = None
        nearest_dist = float('inf')
        for layer, sx, sy, ex, ey in tracks:
            if layer not in pad_layers: continue
            for tx, ty in [(sx, sy), (ex, ey)]:
                d = math.hypot(px-tx, py-ty)
                if d < nearest_dist:
                    nearest_dist = d
                    nearest = (layer, tx, ty)
        if nearest is None or nearest_dist > 3.0:
            continue   # no nearby track to extend from — skip
        layer, tx, ty = nearest
        # Add extending segment
        add_track(brd, tx, ty, px, py, net_obj, layer=layer, w=w)
        n_extensions += 1
        # Update tracks list (so subsequent pads see this extension)
        tracks.append((layer, tx, ty, px, py))
    return n_extensions


def main():
    brd = pcbnew.LoadBoard(PCB)
    err_before, unc_before = drc_count()
    print(f"[baseline] err={err_before} unc={unc_before}")

    total_ext = 0
    for net_name in RESIDUALS:
        n = fix_net_endpoints(brd, net_name)
        print(f"  {net_name}: +{n} extending segments")
        total_ext += n
    print(f"\n[total] {total_ext} extending segments added")

    pcbnew.SaveBoard(PCB, brd)
    # Refill zones
    brd2 = pcbnew.LoadBoard(PCB)
    pcbnew.ZONE_FILLER(brd2).Fill(list(brd2.Zones()))
    pcbnew.SaveBoard(PCB, brd2)

    err_after, unc_after = drc_count()
    print(f"[after] err={err_after} unc={unc_after}  delta_unc={unc_after-unc_before:+d}")


if __name__ == "__main__":
    main()
