#!/usr/bin/env python3
"""3-signal-layer A* maze router for the 20-unrouted residual after
Freerouting (master 2026-05-22 Option B finishing pass).

Layers: L1 (F.Cu), L4 (In3.Cu), L6 (B.Cu).
State: (ix, iy, layer) where layer ∈ {0=F, 1=L4, 2=B}.
Via transitions: any layer ↔ any layer at via_cost (vias are PTH = all 3
signal layers connected); cost paid per layer-flip.

Same fast_check obstacle model + 0.1mm grid + pad-rect rasterization
+ via-near-pad snap.

For each residual net: A* find clean path. If found, place tracks + vias
(snap each via to clear spot). If not found, list as stuck.

After all routes: verify DRC. Target: 0 unrouted + 0 DRC for residuals.
"""
import os, sys, json, math, heapq, subprocess, re, time
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-layout-v1.1.kicad_pcb")
DRC_TMP = "/tmp/_a3_drc.txt"

sys.path.insert(0, HERE)
from per_net_router import _mm, add_via, add_track, get_pad, pad_center, pad_layer, net_width, pad_label
from astar_router import (VIA_DIA, VIA_DRILL, BOARD_W, BOARD_H,
                            collect_obstacles_for_net,
                            rasterize_rect, rasterize_disk, rasterize_segment)
# Override CELL_MM for 3-layer (0.20mm cell = 4x faster A*)
CELL_MM = 0.20
import astar_router
astar_router.CELL_MM = 0.20  # ensure shared funcs see same cell size

F_CU = pcbnew.F_Cu
IN3_CU = pcbnew.In3_Cu   # L4 (the new signal layer)
B_CU = pcbnew.B_Cu

LAYERS = [F_CU, IN3_CU, B_CU]
LAYER_IDX = {F_CU: 0, IN3_CU: 1, B_CU: 2}

CLEARANCE = 0.20
EDGE_CLEAR = 0.30
VIA_COST = 800   # heavily discourage vias to prevent consecutive-via paths
DIAG_COST = 14
ORTHO_COST = 10


def collect_obstacles_3layer(brd, my_net_code):
    """Like the 2-layer collect, but include In3.Cu obstacles too."""
    pads_by_layer = {F_CU: [], IN3_CU: [], B_CU: []}
    tracks_by_layer = {F_CU: [], IN3_CU: [], B_CU: []}
    vias = []
    for t in brd.GetTracks():
        if isinstance(t, pcbnew.PCB_VIA):
            if t.GetNetCode() == my_net_code: continue
            p = t.GetPosition()
            vias.append((p.x/1e6, p.y/1e6, t.GetWidth()/2/1e6))
        else:
            if t.GetNetCode() == my_net_code: continue
            lay = t.GetLayer()
            if lay not in LAYERS: continue
            s = t.GetStart(); e = t.GetEnd()
            tracks_by_layer[lay].append((s.x/1e6, s.y/1e6, e.x/1e6, e.y/1e6, t.GetWidth()/2/1e6))
    for fp in brd.GetFootprints():
        for p in fp.Pads():
            if p.GetNetCode() == my_net_code: continue
            pos = p.GetPosition(); sz = p.GetSize()
            hw = sz.x/2/1e6; hh = sz.y/2/1e6
            for lay in LAYERS:
                if p.IsOnLayer(lay):
                    pads_by_layer[lay].append((pos.x/1e6, pos.y/1e6, hw, hh))
    return tracks_by_layer, pads_by_layer, vias


def build_grid_3l(tracks_by_layer, pads_by_layer, vias, layer, track_w, clearance):
    W = int(BOARD_W / CELL_MM) + 1
    H = int(BOARD_H / CELL_MM) + 1
    grid = bytearray(W * H)
    expand = track_w / 2 + clearance
    for x1, y1, x2, y2, w in tracks_by_layer.get(layer, []):
        rasterize_segment(grid, W, H, x1, y1, x2, y2, w + expand)
    for x, y, hw, hh in pads_by_layer.get(layer, []):
        rasterize_rect(grid, W, H, x, y, hw + expand, hh + expand)
    for x, y, r in vias:
        rasterize_disk(grid, W, H, x, y, r + expand)
    # Edge clearance band
    n_edge = int((EDGE_CLEAR + track_w/2) / CELL_MM) + 1
    for ix in range(W):
        for iy in range(n_edge):
            if iy < H: grid[iy*W + ix] = 1
            if H-1-iy >= 0: grid[(H-1-iy)*W + ix] = 1
    for iy in range(H):
        for ix in range(n_edge):
            if ix < W: grid[iy*W + ix] = 1
            if W-1-ix >= 0: grid[iy*W + (W-1-ix)] = 1
    return grid, W, H


def unblock_pad(grid_F, grid_M, grid_B, W, H, px, py, hw, hh, layer):
    """Unblock pad rectangle on the appropriate layer(s)."""
    x_lo = max(0, int((px - hw) / CELL_MM))
    x_hi = min(W-1, int((px + hw) / CELL_MM) + 1)
    y_lo = max(0, int((py - hh) / CELL_MM))
    y_hi = min(H-1, int((py + hh) / CELL_MM) + 1)
    for iy in range(y_lo, y_hi+1):
        for ix in range(x_lo, x_hi+1):
            if layer == F_CU: grid_F[iy*W + ix] = 0
            elif layer == B_CU: grid_B[iy*W + ix] = 0
            elif layer == IN3_CU: grid_M[iy*W + ix] = 0


NEIGH = [(1,0,ORTHO_COST),(-1,0,ORTHO_COST),(0,1,ORTHO_COST),(0,-1,ORTHO_COST),
         (1,1,DIAG_COST),(-1,-1,DIAG_COST),(1,-1,DIAG_COST),(-1,1,DIAG_COST)]


def astar_3l(grids, W, H, src_states, goal_states, via_cost=VIA_COST, max_states=500000):
    """Cap explored states to prevent runaway. Returns None if exceeded."""
    """A* over 3-layer grid. src/goal are sets of (ix, iy, layer_idx).
    grids: list of [grid_F, grid_M, grid_B]."""
    open_heap = []
    g_score = {}
    came_from = {}
    goal_set = set(goal_states)
    for s in src_states:
        g_score[s] = 0
        # heuristic: min octile + via cost to nearest goal
        h = min(_octile_h(s, gg, via_cost) for gg in goal_states)
        heapq.heappush(open_heap, (h, 0, s, None))

    n_explored = 0
    while open_heap:
        n_explored += 1
        if n_explored > max_states:
            return None  # state-cap exceeded — give up
        f, g, state, parent = heapq.heappop(open_heap)
        if state in came_from: continue
        came_from[state] = parent
        if state in goal_set:
            path = [state]
            while came_from[state] is not None:
                state = came_from[state]
                path.append(state)
            return list(reversed(path))
        ix, iy, lay = state
        cur_grid = grids[lay]
        # Same-layer 8-conn
        for dx, dy, c in NEIGH:
            nx, ny = ix+dx, iy+dy
            if nx<0 or nx>=W or ny<0 or ny>=H: continue
            if cur_grid[ny*W + nx]: continue
            if dx and dy:
                if cur_grid[iy*W + (ix+dx)] or cur_grid[(iy+dy)*W + ix]: continue
            new_g = g + c
            ns = (nx, ny, lay)
            if ns in g_score and g_score[ns] <= new_g: continue
            g_score[ns] = new_g
            h = min(_octile_h(ns, gg, via_cost) for gg in goal_states)
            heapq.heappush(open_heap, (new_g+h, new_g, ns, state))
        # Layer flips (to other 2 layers)
        for other_lay in range(3):
            if other_lay == lay: continue
            other_grid = grids[other_lay]
            if other_grid[iy*W + ix]: continue
            new_g = g + via_cost
            ns = (ix, iy, other_lay)
            if ns in g_score and g_score[ns] <= new_g: continue
            g_score[ns] = new_g
            h = min(_octile_h(ns, gg, via_cost) for gg in goal_states)
            heapq.heappush(open_heap, (new_g+h, new_g, ns, state))
    return None


def _octile_h(s, g, via_cost):
    dx = abs(s[0] - g[0]); dy = abs(s[1] - g[1])
    oct_d = 14*min(dx, dy) + 10*abs(dx - dy)
    return oct_d + (0 if s[2] == g[2] else via_cost)


def pad_cells_3l(pad, W, H):
    px, py = pad_center(pad); sz = pad.GetSize()
    hw = sz.x/2/1e6; hh = sz.y/2/1e6
    x_lo = max(0, int((px-hw)/CELL_MM)); x_hi = min(W-1, int((px+hw)/CELL_MM)+1)
    y_lo = max(0, int((py-hh)/CELL_MM)); y_hi = min(H-1, int((py+hh)/CELL_MM)+1)
    cells = set()
    layers_on = []
    if pad.IsOnLayer(F_CU): layers_on.append(0)
    if pad.IsOnLayer(IN3_CU): layers_on.append(1)  # rare; THT pads
    if pad.IsOnLayer(B_CU): layers_on.append(2)
    # THT pads are typically marked F.Cu + B.Cu — and PTH goes through ALL layers
    # so include layer 1 (L4) too for THT
    if F_CU in [pcbnew.F_Cu for _ in [0]] and B_CU in [pcbnew.B_Cu for _ in [0]]:
        if pad.IsOnLayer(F_CU) and pad.IsOnLayer(B_CU):
            if 1 not in layers_on: layers_on.append(1)
    for iy in range(y_lo, y_hi+1):
        for ix in range(x_lo, x_hi+1):
            for L in layers_on:
                cells.add((ix, iy, L))
    cx = int(round(px/CELL_MM)); cy = int(round(py/CELL_MM))
    for L in layers_on:
        cells.add((cx, cy, L))
    return cells


def collapse_path(path):
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


def snap_via_3l(brd, vx, vy, net_code, search_cells=20):
    """Find nearest clear via position to (vx, vy). Uses fast_check."""
    from fast_check import check_via, collect_obstacles
    obs = collect_obstacles(brd, net_code)
    if not check_via(brd, vx, vy, VIA_DIA, net_code, obs, clearance=CLEARANCE):
        return (vx, vy)
    for r_cells in range(1, search_cells+1):
        for ang in range(0, 360, 15):
            dx = r_cells * CELL_MM * math.cos(math.radians(ang))
            dy = r_cells * CELL_MM * math.sin(math.radians(ang))
            tx = vx+dx; ty = vy+dy
            if tx < 1 or tx > 89 or ty < 1 or ty > 69: continue
            if not check_via(brd, tx, ty, VIA_DIA, net_code, obs, clearance=CLEARANCE):
                return (tx, ty)
    return None


def route_net_3l(brd, net_name, src_pad, dst_pad):
    """Route one leg. Returns (ok, n_tracks, n_vias)."""
    nets = {str(k): v for k, v in brd.GetNetsByName().asdict().items()}
    net_obj = nets[net_name]
    net_code = net_obj.GetNetCode()
    track_w = net_width(net_name)

    obs = collect_obstacles_3layer(brd, net_code)
    grid_F, W, H = build_grid_3l(*obs, layer=F_CU, track_w=track_w, clearance=CLEARANCE)
    grid_M, _, _ = build_grid_3l(*obs, layer=IN3_CU, track_w=track_w, clearance=CLEARANCE)
    grid_B, _, _ = build_grid_3l(*obs, layer=B_CU, track_w=track_w, clearance=CLEARANCE)

    for pad in [src_pad, dst_pad]:
        px, py = pad_center(pad); sz = pad.GetSize()
        hw = sz.x/2/1e6; hh = sz.y/2/1e6
        for lay in [F_CU, IN3_CU, B_CU]:
            if pad.IsOnLayer(lay):
                unblock_pad(grid_F, grid_M, grid_B, W, H, px, py, hw, hh, lay)

    src = list(pad_cells_3l(src_pad, W, H))
    goal = list(pad_cells_3l(dst_pad, W, H))
    if not src or not goal:
        return False, 0, 0

    path = astar_3l([grid_F, grid_M, grid_B], W, H, src, goal)
    if not path: return False, 0, 0

    corners = collapse_path(path)
    # Apply
    tracks_added = 0; vias_added = 0
    for i in range(len(corners)-1):
        a = corners[i]; b = corners[i+1]
        if a[2] != b[2]:
            # via at a position (same x,y)
            vx, vy = a[0]*CELL_MM, a[1]*CELL_MM
            spot = snap_via_3l(brd, vx, vy, net_code)
            if spot is None: spot = (vx, vy)
            add_via(brd, spot[0], spot[1], net_obj, dia=VIA_DIA, drill=VIA_DRILL)
            vias_added += 1
        else:
            layer_kicad = [F_CU, IN3_CU, B_CU][a[2]]
            add_track(brd, a[0]*CELL_MM, a[1]*CELL_MM,
                       b[0]*CELL_MM, b[1]*CELL_MM,
                       net_obj, layer=layer_kicad, w=track_w)
            tracks_added += 1
    return True, tracks_added, vias_added


# 15 residual nets to route (from FR3 unrouted list)
RESIDUALS = [
    "BATT_CURRENT_SENS", "IMU3_CS", "IMU3_INT1", "MOT1", "MOT2", "NRST",
    "SPI1_SCK", "SPI1_MISO", "SPI1_MOSI",
    "SPI3_SCK", "SPI3_MISO", "SPI3_MOSI",
    "SWCLK", "SWDIO",
    # GND removed — GND is a plane net (routed via plane stitches, NOT
    # as a signal). The single GND segment FR3 flagged is handled by
    # plane fill, not by A*.
]


def main():
    brd = pcbnew.LoadBoard(PCB)
    # Identify all unconnected pads per net
    from per_net_router import get_pad
    results = []
    for net_name in RESIDUALS:
        # Find pads on this net
        net_pads = []
        for fp in brd.GetFootprints():
            for p in fp.Pads():
                if p.GetNetname() == net_name:
                    net_pads.append((fp.GetReference(), p.GetNumber(), p))
        if len(net_pads) < 2:
            print(f"  {net_name}: {len(net_pads)} pads — skip")
            continue
        # For multi-pad nets, route from pad[0] to each other pad
        legs_ok = 0; legs_fail = 0
        t0 = time.time()
        for i in range(1, len(net_pads)):
            src = net_pads[0][2]
            tgt = net_pads[i][2]
            # Reload brd for fresh net obstacles (other-net just-placed tracks)
            brd = pcbnew.LoadBoard(PCB)
            for fp in brd.GetFootprints():
                if fp.GetReference() == net_pads[0][0]:
                    for p in fp.Pads():
                        if p.GetNumber() == net_pads[0][1]:
                            src = p; break
                if fp.GetReference() == net_pads[i][0]:
                    for p in fp.Pads():
                        if p.GetNumber() == net_pads[i][1]:
                            tgt = p; break
            ok, nt, nv = route_net_3l(brd, net_name, src, tgt)
            if ok:
                pcbnew.SaveBoard(PCB, brd)
                legs_ok += 1
            else:
                legs_fail += 1
        elapsed = time.time() - t0
        print(f"  {net_name}: {legs_ok}/{legs_ok+legs_fail} legs ok ({elapsed:.1f}s)")
        results.append({"net": net_name, "ok": legs_ok, "fail": legs_fail})

    # Final DRC
    subprocess.run(["kicad-cli","pcb","drc","--severity-error","--format","report",
                    "--output",DRC_TMP,"--units","mm",PCB], capture_output=True)
    with open(DRC_TMP) as f: t = f.read()
    err = re.search(r"Found (\d+) DRC violation", t)
    unc = re.search(r"Found (\d+) unconnected pad", t)
    print(f"\n[DRC] errors={err.group(1) if err else '?'} unconnected={unc.group(1) if unc else '?'}")

    log_path = os.path.join(HERE, "astar_3layer_log.json")
    with open(log_path, "w") as f:
        json.dump({"results": results, "drc_err": int(err.group(1)) if err else 0,
                    "drc_unc": int(unc.group(1)) if unc else 0}, f, indent=2)
    print(f"[log] {log_path}")


if __name__ == "__main__":
    main()
