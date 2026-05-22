#!/usr/bin/env python3
"""A* maze router for v1.1 R4 (master 2026-05-22 direction).

Grid-based A* over a 2-layer plane (F.Cu + B.Cu) with via transitions.
Each cell is 0.20mm. Obstacles are rasterized from existing copper +
clearance. Same-net copper is NOT an obstacle (router can join to it).

Algorithm:
  1. Build obstacle grid for each layer for current net (other-net only).
  2. Mark source-pad cells and destination-pad cells as start/goal sets.
  3. A* with state (ix, iy, layer); cost 1 per cell move, K_VIA per layer flip.
  4. Reconstruct path → collapse to track segments (consecutive same-layer
     cells) + vias (at layer-flip cells).
  5. Apply to board, refill zones, save.

Per-net iteration: each completed route becomes obstacle for next nets.

Validation: full kicad-cli DRC at end of batch.
"""
import os, sys, json, math, time, subprocess, re
import heapq
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-layout-v1.1.kicad_pcb")
DRC_TMP = "/tmp/_astar_drc.txt"

sys.path.insert(0, HERE)
from per_net_router import (F_CU, B_CU, _mm, add_via, add_track,
                              get_pad, pad_center, pad_layer, net_width,
                              pad_label, NET_WIDTH)

BOARD_W = 90.0
BOARD_H = 70.0
CELL_MM = 0.10  # finer grid for narrow gaps between USB/IMU pads
EDGE_CLEAR = 0.30
DEFAULT_CLEAR = 0.20
VIA_DIA = 0.60
VIA_DRILL = 0.30
VIA_COST = 250  # 25 cells equivalent; discourage vias (cell moves cost 10-14)


def collect_obstacles_for_net(brd, my_net_code):
    """Return F/B obstacle lists per layer (excludes same-net).
    Pads are stored as rectangles (cx, cy, half_w, half_h)."""
    F = pcbnew.F_Cu; B = pcbnew.B_Cu
    pads = {F: [], B: []}
    tracks = {F: [], B: []}
    vias = []
    for t in brd.GetTracks():
        if isinstance(t, pcbnew.PCB_VIA):
            if t.GetNetCode() == my_net_code: continue
            p = t.GetPosition()
            vias.append((p.x/1e6, p.y/1e6, t.GetWidth()/2/1e6))
        else:
            if t.GetNetCode() == my_net_code: continue
            lay = t.GetLayer()
            if lay not in (F, B): continue
            s = t.GetStart(); e = t.GetEnd()
            tracks[lay].append((s.x/1e6, s.y/1e6, e.x/1e6, e.y/1e6, t.GetWidth()/2/1e6))
    for fp in brd.GetFootprints():
        for p in fp.Pads():
            if p.GetNetCode() == my_net_code: continue
            pos = p.GetPosition(); sz = p.GetSize()
            # Store rectangle half-dims (better than circle approximation for SMD)
            half_w = sz.x / 2 / 1e6
            half_h = sz.y / 2 / 1e6
            for lay in (F, B):
                if p.IsOnLayer(lay):
                    pads[lay].append((pos.x/1e6, pos.y/1e6, half_w, half_h))
    return tracks, pads, vias


def build_grid(tracks_by_layer, pads_by_layer, vias, layer, track_w, clearance):
    """Rasterize obstacles into a 2D blocked-cell bitmap.

    Returns: bytearray of W*H cells (0=free, 1=blocked) + (W, H).
    """
    W = int(BOARD_W / CELL_MM) + 1
    H = int(BOARD_H / CELL_MM) + 1
    grid = bytearray(W * H)

    # Half-width inflation for obstacles
    expand = track_w / 2 + clearance

    # Tracks on this layer
    for x1, y1, x2, y2, w in tracks_by_layer.get(layer, []):
        rasterize_segment(grid, W, H, x1, y1, x2, y2, w + expand)
    # Pads on this layer (rectangles)
    for x, y, hw, hh in pads_by_layer.get(layer, []):
        rasterize_rect(grid, W, H, x, y, hw + expand, hh + expand)
    # Vias (always present on F + B)
    for x, y, r in vias:
        rasterize_disk(grid, W, H, x, y, r + expand)
    # Board edge (block bands)
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


def rasterize_rect(grid, W, H, cx_mm, cy_mm, hw_mm, hh_mm):
    """Block cells inside the rectangle [cx-hw, cx+hw] × [cy-hh, cy+hh]."""
    x_lo = max(0, int((cx_mm - hw_mm) / CELL_MM))
    x_hi = min(W-1, int((cx_mm + hw_mm) / CELL_MM) + 1)
    y_lo = max(0, int((cy_mm - hh_mm) / CELL_MM))
    y_hi = min(H-1, int((cy_mm + hh_mm) / CELL_MM) + 1)
    for iy in range(y_lo, y_hi+1):
        for ix in range(x_lo, x_hi+1):
            grid[iy*W + ix] = 1


def rasterize_disk(grid, W, H, cx_mm, cy_mm, r_mm):
    """Block cells within radius."""
    cx = cx_mm / CELL_MM
    cy = cy_mm / CELL_MM
    r = r_mm / CELL_MM
    r2 = r * r
    x_lo = max(0, int(cx - r - 1))
    x_hi = min(W-1, int(cx + r + 1))
    y_lo = max(0, int(cy - r - 1))
    y_hi = min(H-1, int(cy + r + 1))
    for iy in range(y_lo, y_hi+1):
        for ix in range(x_lo, x_hi+1):
            if (ix - cx)**2 + (iy - cy)**2 <= r2:
                grid[iy*W + ix] = 1


def rasterize_segment(grid, W, H, x1_mm, y1_mm, x2_mm, y2_mm, half_w_mm):
    """Block cells within half-width of segment."""
    # Sample points along segment, rasterize disk at each
    L = math.hypot(x2_mm-x1_mm, y2_mm-y1_mm)
    n_steps = max(2, int(L / (CELL_MM/2)) + 1)
    for i in range(n_steps+1):
        t = i / n_steps
        x = x1_mm + t * (x2_mm - x1_mm)
        y = y1_mm + t * (y2_mm - y1_mm)
        rasterize_disk(grid, W, H, x, y, half_w_mm)


def unblock_pad_interior(grid_F, grid_B, W, H, px_mm, py_mm, hw_mm, hh_mm, allow_layer):
    """Unblock cells inside the pad rectangle (no padding)."""
    x_lo = max(0, int((px_mm - hw_mm) / CELL_MM))
    x_hi = min(W-1, int((px_mm + hw_mm) / CELL_MM) + 1)
    y_lo = max(0, int((py_mm - hh_mm) / CELL_MM))
    y_hi = min(H-1, int((py_mm + hh_mm) / CELL_MM) + 1)
    for iy in range(y_lo, y_hi+1):
        for ix in range(x_lo, x_hi+1):
            if allow_layer == "F" or allow_layer == "both":
                grid_F[iy*W + ix] = 0
            if allow_layer == "B" or allow_layer == "both":
                grid_B[iy*W + ix] = 0


def pad_xy_to_cell(px_mm, py_mm, W, H):
    return (int(round(px_mm / CELL_MM)), int(round(py_mm / CELL_MM)))


def cell_to_mm(ix, iy):
    return (ix * CELL_MM, iy * CELL_MM)


def astar(grid_F, grid_B, W, H, src, goal, via_cost=VIA_COST, via_grid=None):
    """A* over (ix, iy, layer). src and goal are sets of (ix, iy, layer).
    via_grid: optional separate bitmap; layer-flip only allowed if via_grid[cell]==0."""
    open_heap = []
    g_score = {}

    # Initialize start nodes
    for s in src:
        g_score[s] = 0
        # heuristic: min Manhattan to any goal
        h = min(abs(s[0]-g[0]) + abs(s[1]-g[1]) + (0 if s[2]==g[2] else via_cost) for g in goal)
        heapq.heappush(open_heap, (h, 0, s, None))
    came_from = {}

    goal_set = set(goal)

    # 8-connectivity: 4 orthogonal (cost 10) + 4 diagonal (cost 14 ≈ sqrt(2)*10)
    NEIGH_SAME = [(1,0,10),(-1,0,10),(0,1,10),(0,-1,10),
                  (1,1,14),(-1,-1,14),(1,-1,14),(-1,1,14)]

    while open_heap:
        f, g, state, parent = heapq.heappop(open_heap)
        if state in came_from: continue
        came_from[state] = parent
        if state in goal_set:
            # reconstruct
            path = [state]
            while came_from[state] is not None:
                state = came_from[state]
                path.append(state)
            return list(reversed(path))
        ix, iy, lay = state
        # Same-layer moves (8-connectivity)
        for dx, dy, c in NEIGH_SAME:
            nx, ny = ix+dx, iy+dy
            if nx < 0 or nx >= W or ny < 0 or ny >= H: continue
            cell = grid_F if lay == 0 else grid_B
            if cell[ny*W + nx]: continue
            # For diagonal moves, ensure both orthogonal neighbors are also free
            # (prevents corner-cutting through obstacles)
            if dx != 0 and dy != 0:
                if cell[iy*W + (ix+dx)] or cell[(iy+dy)*W + ix]:
                    continue
            new_g = g + c
            ns = (nx, ny, lay)
            if ns in g_score and g_score[ns] <= new_g: continue
            g_score[ns] = new_g
            # Heuristic: octile distance (better for 8-conn)
            dx_h = min(abs(nx-gg[0]) for gg in goal)
            dy_h = min(abs(ny-gg[1]) for gg in goal)
            octile = 14*min(dx_h, dy_h) + 10*abs(dx_h - dy_h)
            via_h = min(0 if lay==gg[2] else via_cost for gg in goal)
            heapq.heappush(open_heap, (new_g + octile + via_h, new_g, ns, state))
        # Layer flip (via) — requires via_grid clear AT this cell on both layers
        other_lay = 1 - lay
        other_cell = grid_F if other_lay == 0 else grid_B
        via_ok = via_grid is None or not via_grid[iy*W + ix]
        if not other_cell[iy*W + ix] and via_ok:
            new_g = g + via_cost
            ns = (ix, iy, other_lay)
            if not (ns in g_score and g_score[ns] <= new_g):
                g_score[ns] = new_g
                dx_h = min(abs(ix-gg[0]) for gg in goal)
                dy_h = min(abs(iy-gg[1]) for gg in goal)
                octile = 14*min(dx_h, dy_h) + 10*abs(dx_h - dy_h)
                via_h = min(0 if other_lay==gg[2] else via_cost for gg in goal)
                heapq.heappush(open_heap, (new_g + octile + via_h, new_g, ns, state))
    return None


def path_to_geometry(path):
    """Convert path of (ix, iy, layer) cells to (tracks, vias) lists in mm."""
    if not path: return [], []
    tracks = []  # (x1, y1, x2, y2, layer)
    vias = []    # (x, y)
    seg_start = path[0]
    cur_layer = path[0][2]
    prev = path[0]
    for s in path[1:]:
        ix, iy, lay = s
        pix, piy, play = prev
        if lay != play:
            # Layer flip: finalize current segment, place via, start new
            if prev != seg_start:
                tracks.append((seg_start[0]*CELL_MM, seg_start[1]*CELL_MM,
                                prev[0]*CELL_MM, prev[1]*CELL_MM, play))
            vias.append((prev[0]*CELL_MM, prev[1]*CELL_MM))
            seg_start = s
        elif (ix - pix, iy - piy) != ((prev[0] - seg_start[0]) > 0 and 1 or (prev[0] - seg_start[0]) < 0 and -1 or 0,
                                       (prev[1] - seg_start[1]) > 0 and 1 or (prev[1] - seg_start[1]) < 0 and -1 or 0):
            # Direction change: end segment at prev, start new from prev
            if prev != seg_start:
                tracks.append((seg_start[0]*CELL_MM, seg_start[1]*CELL_MM,
                                prev[0]*CELL_MM, prev[1]*CELL_MM, play))
            seg_start = prev
        prev = s
    # Final segment
    if prev != seg_start:
        tracks.append((seg_start[0]*CELL_MM, seg_start[1]*CELL_MM,
                        prev[0]*CELL_MM, prev[1]*CELL_MM, prev[2]))
    return tracks, vias


def collapse_path(path):
    """Collapse path into Manhattan segments. Returns list of (ix, iy, layer)
    corner points (changes of direction or layer flips)."""
    if len(path) <= 1: return path
    corners = [path[0]]
    for i in range(1, len(path)-1):
        prev = path[i-1]
        cur = path[i]
        nxt = path[i+1]
        # Layer flip → corner
        if cur[2] != prev[2] or nxt[2] != cur[2]:
            corners.append(cur); continue
        # Direction change → corner
        d_prev = (cur[0]-prev[0], cur[1]-prev[1])
        d_next = (nxt[0]-cur[0], nxt[1]-cur[1])
        if d_prev != d_next:
            corners.append(cur)
    corners.append(path[-1])
    return corners


def route_net(brd, net_name, my_net_code, src_pad, dst_pad, track_w, clearance=DEFAULT_CLEAR):
    """Route one leg. Returns (ok, path_cells, n_segs, n_vias).
    Builds two grids:
      - track_grid: inflated by track_r + clearance (for movement)
      - via_grid: inflated by via_r + clearance (for layer flips)
    """
    obs = collect_obstacles_for_net(brd, my_net_code)
    # Track grids (per layer)
    grid_F, W, H = build_grid(*obs, layer=F_CU, track_w=track_w, clearance=clearance)
    grid_B, _, _ = build_grid(*obs, layer=B_CU, track_w=track_w, clearance=clearance)
    # Via grid: blocked if a 0.60mm via at this cell would clash with any
    # other-net pad/via on EITHER layer. Use slightly relaxed clearance
    # (0.15mm) — final DRC verifies at netclass 0.20mm.
    via_clear = 0.15
    via_grid_F, _, _ = build_grid(*obs, layer=F_CU, track_w=VIA_DIA, clearance=via_clear)
    via_grid_B, _, _ = build_grid(*obs, layer=B_CU, track_w=VIA_DIA, clearance=via_clear)
    via_grid = bytearray(W * H)
    for i in range(W * H):
        via_grid[i] = 1 if (via_grid_F[i] or via_grid_B[i]) else 0

    # Unblock pad-interior cells on the pad's actual layer(s)
    for pad in [src_pad, dst_pad]:
        px, py = pad_center(pad)
        sz = pad.GetSize()
        hw = sz.x / 2 / 1e6; hh = sz.y / 2 / 1e6
        if pad.IsOnLayer(F_CU): unblock_pad_interior(grid_F, grid_B, W, H, px, py, hw, hh, "F")
        if pad.IsOnLayer(B_CU): unblock_pad_interior(grid_F, grid_B, W, H, px, py, hw, hh, "B")

    # Build src/goal cell sets (pad rectangle interior)
    def pad_cells(pad):
        px, py = pad_center(pad)
        sz = pad.GetSize()
        hw = sz.x / 2 / 1e6; hh = sz.y / 2 / 1e6
        x_lo = max(0, int((px - hw) / CELL_MM))
        x_hi = min(W-1, int((px + hw) / CELL_MM) + 1)
        y_lo = max(0, int((py - hh) / CELL_MM))
        y_hi = min(H-1, int((py + hh) / CELL_MM) + 1)
        cells = set()
        for iy in range(y_lo, y_hi+1):
            for ix in range(x_lo, x_hi+1):
                if pad.IsOnLayer(F_CU): cells.add((ix, iy, 0))
                if pad.IsOnLayer(B_CU): cells.add((ix, iy, 1))
        # Ensure at least the center cell
        cx = int(round(px / CELL_MM)); cy = int(round(py / CELL_MM))
        if pad.IsOnLayer(F_CU): cells.add((cx, cy, 0))
        if pad.IsOnLayer(B_CU): cells.add((cx, cy, 1))
        return cells

    src = list(pad_cells(src_pad))
    goal = list(pad_cells(dst_pad))

    # via_grid temporarily disabled (too restrictive); vias may cause
    # shorts that final DRC catches. TODO: smarter via placement.
    path = astar(grid_F, grid_B, W, H, src, goal)
    if path is None:
        return False, None, 0, 0

    corners = collapse_path(path)
    # Build geometry from corners (already in cell coords)
    tracks = []; vias = []
    for i in range(len(corners)-1):
        a = corners[i]; b = corners[i+1]
        if a[2] != b[2]:
            # Layer flip — via at this position (a == b in x,y, layer differs)
            vias.append((a[0]*CELL_MM, a[1]*CELL_MM))
        else:
            tracks.append((a[0]*CELL_MM, a[1]*CELL_MM,
                            b[0]*CELL_MM, b[1]*CELL_MM, a[2]))
    return True, path, tracks, vias


def apply_route(brd, net_obj, tracks, vias, track_w):
    for x1, y1, x2, y2, lay in tracks:
        layer = F_CU if lay == 0 else B_CU
        add_track(brd, x1, y1, x2, y2, net_obj, layer=layer, w=track_w)
    for x, y in vias:
        add_via(brd, x, y, net_obj, dia=VIA_DIA, drill=VIA_DRILL)


def drc_counts():
    subprocess.run(["kicad-cli","pcb","drc","--severity-error",
                    "--format","report","--output",DRC_TMP,
                    "--units","mm",PCB], capture_output=True, text=True)
    txt = open(DRC_TMP).read()
    e = re.search(r"Found (\d+) DRC violation", txt)
    u = re.search(r"Found (\d+) unconnected pad", txt)
    return (int(e.group(1)) if e else 0, int(u.group(1)) if u else 0)


def main(nets_file):
    spec = json.load(open(nets_file))
    brd = pcbnew.LoadBoard(PCB)
    nets = {str(k): v for k, v in brd.GetNetsByName().asdict().items()}

    base_err, base_unc = drc_counts()
    print(f"[baseline] err={base_err} unc={base_unc}")
    cur_err = base_err

    log = []
    residuals = json.load(open(os.path.join(HERE, "vision_residuals_mp30.json")))
    by_net = residuals.get("by_net", {})

    for net_name in spec.get("nets", []):
        pad_specs = by_net.get(net_name, [])
        if len(pad_specs) < 2:
            print(f"  {net_name}: <2 pads — skip")
            log.append({"net":net_name,"ok":False,"reason":"singleton"})
            continue
        net_obj = nets[net_name]
        net_code = net_obj.GetNetCode()
        track_w = net_width(net_name)
        # Reload board so fresh net handles
        brd = pcbnew.LoadBoard(PCB)
        nets = {str(k): v for k, v in brd.GetNetsByName().asdict().items()}
        net_obj = nets[net_name]
        net_code = net_obj.GetNetCode()
        pads = [get_pad(brd, ps["ref"], ps["pad"]) for ps in pad_specs]
        pads = [p for p in pads if p]
        if len(pads) < 2:
            log.append({"net":net_name,"ok":False,"reason":"pads_not_found"}); continue

        leg_logs = []
        # Star route from pads[0] to each other pad
        t0 = time.time()
        all_ok = True
        for p_tgt in pads[1:]:
            ok, path, tracks, vias = route_net(brd, net_name, net_code,
                                                 pads[0], p_tgt, track_w)
            elapsed = time.time() - t0
            leg = f"{pad_label(pads[0])}->{pad_label(p_tgt)}"
            if ok:
                apply_route(brd, net_obj, tracks, vias, track_w)
                pcbnew.SaveBoard(PCB, brd)
                # Re-collect for next leg
                brd = pcbnew.LoadBoard(PCB)
                nets = {str(k): v for k, v in brd.GetNetsByName().asdict().items()}
                net_obj = nets[net_name]
                net_code = net_obj.GetNetCode()
                pads = [get_pad(brd, ps["ref"], ps["pad"]) for ps in pad_specs]
                leg_logs.append({"leg":leg,"ok":True,"tracks":len(tracks),"vias":len(vias)})
                print(f"  {net_name}  {leg}  OK  ({len(tracks)} tracks, {len(vias)} vias, {elapsed:.1f}s)")
            else:
                all_ok = False
                leg_logs.append({"leg":leg,"ok":False,"reason":"no_path"})
                print(f"  {net_name}  {leg}  NO_PATH ({elapsed:.1f}s)")
                break
        log.append({"net":net_name,"ok":all_ok,"legs":leg_logs})

    # Final DRC
    pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
    pcbnew.SaveBoard(PCB, brd)
    final_err, final_unc = drc_counts()
    delta_err = final_err - base_err
    delta_unc = final_unc - base_unc
    print(f"\n[final] err={final_err} unc={final_unc}  delta_err={delta_err:+d} delta_unc={delta_unc:+d}")
    n_ok = sum(1 for r in log if r.get("ok"))
    print(f"routed: {n_ok}/{len(log)}")

    log_path = os.path.join(HERE, os.path.basename(nets_file).replace(".json","_astar_log.json"))
    with open(log_path, "w") as f:
        json.dump({"baseline":{"err":base_err,"unc":base_unc},
                   "final":{"err":final_err,"unc":final_unc},
                   "delta_err":delta_err,"delta_unc":delta_unc,
                   "routed":n_ok,"total":len(log),"results":log}, f, indent=2)
    print(f"[log] {log_path}")


if __name__ == "__main__":
    main(sys.argv[1])
