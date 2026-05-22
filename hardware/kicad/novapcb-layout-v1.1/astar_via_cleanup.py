#!/usr/bin/env python3
"""A* topological routes + via cleanup post-processor (master 2026-05-22).

Strategy:
  1. Run A* to get 14/14 topological paths.
  2. PATH-LEVEL POST-PROCESS: walk each path; if a layer flip lasts ≤ N cells
     with no useful routing between (i.e., short layer-excursion), collapse
     it back to the original layer. Eliminates "zigzag" via artifacts.
  3. Apply cleaned paths to PCB.
  4. REFILL plane zones — planes auto-void around real vias. Most
     zone_clearance violations should vanish.
  5. DRC check. Report final + identify any stubborn conflicts for master
     vision-loop.

Bounded: ≤ 2h time-box per master directive.
"""
import os, sys, math, json, heapq, subprocess, re, time
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-layout-v1.1.kicad_pcb")

sys.path.insert(0, HERE)
from per_net_router import _mm, add_via, add_track, get_pad, pad_center, pad_layer, net_width, pad_label
from astar_router import (rasterize_rect, rasterize_disk, rasterize_segment,
                            BOARD_W, BOARD_H)
from fast_check import check_via, collect_obstacles as fast_collect
from astar_3layer import (CELL_MM, VIA_DIA, VIA_DRILL,
                            collect_obstacles_3layer, build_grid_3l, unblock_pad,
                            astar_3l, pad_cells_3l, snap_via_3l,
                            F_CU, IN3_CU, B_CU, LAYERS, CLEARANCE)

VIA_COST = 1000  # heavily discourage vias
DRC_TMP = "/tmp/_avc_drc.txt"


def collapse_useless_excursions(path, min_segment_cells=10):
    """Walk path; find layer-flip → short-segment → layer-flip-back patterns.
    If the layer excursion lasts < min_segment_cells and same start/end layer,
    DELETE the excursion (force same-layer path).

    Path = [(ix, iy, layer), ...] in cell coords.
    """
    if len(path) < 4: return path
    cleaned = list(path)
    changed = True
    while changed:
        changed = False
        i = 0
        new_cleaned = []
        while i < len(cleaned):
            # Look ahead for via excursion: A on L1, several cells on L2, return to L1
            if i + 3 >= len(cleaned):
                new_cleaned.append(cleaned[i]); i += 1; continue
            cur = cleaned[i]
            nxt = cleaned[i+1]
            if cur[2] == nxt[2]:
                # No layer flip here
                new_cleaned.append(cur); i += 1; continue
            # Layer flip at i→i+1. Find next layer flip back.
            flip_back_idx = None
            for j in range(i+2, min(len(cleaned), i+2+min_segment_cells+1)):
                if cleaned[j][2] == cur[2]:
                    flip_back_idx = j
                    break
            if flip_back_idx is None:
                # No return — keep this flip
                new_cleaned.append(cur); i += 1; continue
            excursion_len = flip_back_idx - i
            if excursion_len <= min_segment_cells:
                # Skip the excursion: keep cur, skip to flip_back_idx (continuing on cur layer)
                # Replace cleaned[i+1..flip_back_idx] with same (x, y, cur[2]) path
                new_cleaned.append(cur)
                # Insert cells from i+1 to flip_back_idx-1 with layer = cur[2]
                for k in range(i+1, flip_back_idx):
                    px, py, _ = cleaned[k]
                    new_cleaned.append((px, py, cur[2]))
                i = flip_back_idx
                changed = True
            else:
                new_cleaned.append(cur); i += 1
        cleaned = new_cleaned
    return cleaned


def collapse_path_v2(path):
    """Standard direction-change + layer-flip collapse."""
    if len(path) <= 1: return path
    corners = [path[0]]
    for i in range(1, len(path)-1):
        prev = path[i-1]; cur = path[i]; nxt = path[i+1]
        if cur[2] != prev[2] or nxt[2] != cur[2]:
            corners.append(cur); continue
        d_prev = (cur[0]-prev[0], cur[1]-prev[1])
        d_next = (nxt[0]-cur[0], nxt[1]-cur[1])
        if d_prev != d_next: corners.append(cur)
    corners.append(path[-1])
    return corners


def drc_count():
    subprocess.run(["kicad-cli","pcb","drc","--severity-error","--format","report",
                    "--output",DRC_TMP,"--units","mm",PCB],
                   capture_output=True, text=True)
    txt = open(DRC_TMP).read()
    e = re.search(r"Found (\d+) DRC violation", txt)
    u = re.search(r"Found (\d+) unconnected pad", txt)
    return (int(e.group(1)) if e else 0, int(u.group(1)) if u else 0)


def route_one_residual(brd, net_name):
    """A* route + post-process, apply to brd. Returns (ok, n_tracks, n_vias)."""
    nets = {str(k): v for k, v in brd.GetNetsByName().asdict().items()}
    net_obj = nets[net_name]
    net_code = net_obj.GetNetCode()
    track_w = net_width(net_name)

    # Find pads on this net
    pads = []
    for fp in brd.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname() == net_name:
                pads.append(p)
    if len(pads) < 2:
        return False, 0, 0

    # Build 3-layer grids
    obs = collect_obstacles_3layer(brd, net_code)
    grid_F, W, H = build_grid_3l(*obs, layer=F_CU, track_w=track_w, clearance=CLEARANCE)
    grid_M, _, _ = build_grid_3l(*obs, layer=IN3_CU, track_w=track_w, clearance=CLEARANCE)
    grid_B, _, _ = build_grid_3l(*obs, layer=B_CU, track_w=track_w, clearance=CLEARANCE)
    for pad in pads:
        px, py = pad_center(pad); sz = pad.GetSize()
        hw = sz.x/2/1e6; hh = sz.y/2/1e6
        for lay in [F_CU, IN3_CU, B_CU]:
            if pad.IsOnLayer(lay):
                unblock_pad(grid_F, grid_M, grid_B, W, H, px, py, hw, hh, lay)

    n_tracks = n_vias = 0
    for i in range(1, len(pads)):
        src = list(pad_cells_3l(pads[0], W, H))
        goal = list(pad_cells_3l(pads[i], W, H))
        path = astar_3l([grid_F, grid_M, grid_B], W, H, src, goal,
                          via_cost=VIA_COST)
        if not path: continue
        # POST-PROCESS: collapse useless excursions FIRST
        path = collapse_useless_excursions(path, min_segment_cells=10)
        # THEN corner-collapse
        corners = collapse_path_v2(path)
        # Apply
        for k in range(len(corners)-1):
            a = corners[k]; b = corners[k+1]
            if a[2] != b[2]:
                vx, vy = a[0]*CELL_MM, a[1]*CELL_MM
                spot = snap_via_3l(brd, vx, vy, net_code)
                if spot is None: spot = (vx, vy)
                add_via(brd, spot[0], spot[1], net_obj, dia=VIA_DIA, drill=VIA_DRILL)
                n_vias += 1
            else:
                layer_kicad = [F_CU, IN3_CU, B_CU][a[2]]
                add_track(brd, a[0]*CELL_MM, a[1]*CELL_MM,
                           b[0]*CELL_MM, b[1]*CELL_MM,
                           net_obj, layer=layer_kicad, w=track_w)
                n_tracks += 1
    return True, n_tracks, n_vias


RESIDUALS = [
    "BATT_CURRENT_SENS", "IMU3_CS", "IMU3_INT1", "MOT1", "MOT2", "NRST",
    "SPI1_SCK", "SPI1_MISO", "SPI1_MOSI",
    "SPI3_SCK", "SPI3_MISO", "SPI3_MOSI",
    "SWCLK", "SWDIO",
]


def main():
    t_start = time.time()
    base_err, base_unc = drc_count()
    print(f"[baseline] err={base_err} unc={base_unc}", flush=True)

    results = []
    for net_name in RESIDUALS:
        brd = pcbnew.LoadBoard(PCB)
        t0 = time.time()
        ok, nt, nv = route_one_residual(brd, net_name)
        elapsed = time.time() - t0
        if ok:
            pcbnew.SaveBoard(PCB, brd)
        results.append({"net":net_name,"ok":ok,"tracks":nt,"vias":nv,"sec":elapsed})
        print(f"  {net_name}: ok={ok} tracks={nt} vias={nv} ({elapsed:.1f}s)", flush=True)

    # Refill plane zones (auto-voids around real vias)
    print(f"\n[refill] planes refilling around new vias...", flush=True)
    brd = pcbnew.LoadBoard(PCB)
    pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
    pcbnew.SaveBoard(PCB, brd)

    err, unc = drc_count()
    total = time.time() - t_start
    print(f"\n[final] err={err} unc={unc}  delta_err={err-base_err:+d}  total={total/60:.1f}min", flush=True)

    log_path = os.path.join(HERE, "astar_via_cleanup_log.json")
    with open(log_path, "w") as f:
        json.dump({"baseline":{"err":base_err,"unc":base_unc},
                   "final":{"err":err,"unc":unc},
                   "delta_err": err-base_err,
                   "results": results}, f, indent=2)
    print(f"[log] {log_path}")


if __name__ == "__main__":
    main()
