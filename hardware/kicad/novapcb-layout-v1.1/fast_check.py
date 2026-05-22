#!/usr/bin/env python3
"""Fast in-process collision check (subset of DRC, ~1000x faster).

Catches the common failure modes from naive routing:
  - Track segment crosses or comes too close to other-net track on same layer
  - Track segment crosses or comes too close to other-net pad on same layer
  - Track segment crosses or comes too close to other-net via (any layer pair)
  - Via too close to other-net pad/via (annular ring + mask aperture)
  - Track segment too close to board edge

DOES NOT catch:
  - Inner-layer plane clearance (thermal-relief incidents)
  - Net-class-specific clearances above default
  - Solder-mask bridge edge cases (only approximate)

Use this as a fast filter to pick a strategy. Run full DRC at end of net
(or end of batch) to catch what fast_check missed.
"""
import math
import pcbnew

CLEARANCE_MM = 0.10  # board-setup minimum; netclass may be higher
EDGE_CLEARANCE_MM = 0.30
MASK_EXPAND_MM = 0.05  # solder-mask aperture expansion past copper


def _mm(intval): return intval / 1e6


def seg_to_point_dist(ax, ay, bx, by, px, py):
    dx, dy = bx-ax, by-ay
    L2 = dx*dx + dy*dy
    if L2 < 1e-12: return math.hypot(px-ax, py-ay)
    t = max(0.0, min(1.0, ((px-ax)*dx + (py-ay)*dy) / L2))
    cx, cy = ax + t*dx, ay + t*dy
    return math.hypot(px-cx, py-cy)


def segments_intersect(ax, ay, bx, by, cx, cy, dx, dy):
    """True if segment AB crosses segment CD (proper crossing)."""
    def orient(px, py, qx, qy, rx, ry):
        v = (qx-px)*(ry-py) - (qy-py)*(rx-px)
        if v > 1e-9: return 1
        if v < -1e-9: return -1
        return 0
    o1 = orient(ax, ay, bx, by, cx, cy)
    o2 = orient(ax, ay, bx, by, dx, dy)
    o3 = orient(cx, cy, dx, dy, ax, ay)
    o4 = orient(cx, cy, dx, dy, bx, by)
    return o1 != o2 and o3 != o4


def seg_to_seg_dist(ax, ay, bx, by, cx, cy, dx, dy):
    if segments_intersect(ax, ay, bx, by, cx, cy, dx, dy):
        return 0.0
    return min(
        seg_to_point_dist(ax, ay, bx, by, cx, cy),
        seg_to_point_dist(ax, ay, bx, by, dx, dy),
        seg_to_point_dist(cx, cy, dx, dy, ax, ay),
        seg_to_point_dist(cx, cy, dx, dy, bx, by),
    )


def collect_obstacles(brd, my_net_code):
    """Return: (tracks_by_layer, pads_by_layer, vias). All 'other-net' only.
    Layers: F.Cu=0, B.Cu=31 (KiCad layer ids)."""
    F = pcbnew.F_Cu
    B = pcbnew.B_Cu
    tracks = {F: [], B: []}
    pads = {F: [], B: []}
    vias = []
    for t in brd.GetTracks():
        if isinstance(t, pcbnew.PCB_VIA):
            if t.GetNetCode() != my_net_code:
                p = t.GetPosition()
                vias.append({"x": _mm(p.x), "y": _mm(p.y),
                             "r": _mm(t.GetWidth())/2,
                             "net": t.GetNetname()})
        else:
            if t.GetNetCode() == my_net_code: continue
            s, e = t.GetStart(), t.GetEnd()
            lay = t.GetLayer()
            if lay not in (F, B): continue
            tracks[lay].append({
                "x1": _mm(s.x), "y1": _mm(s.y),
                "x2": _mm(e.x), "y2": _mm(e.y),
                "w": _mm(t.GetWidth()),
                "net": t.GetNetname()
            })
    for fp in brd.GetFootprints():
        for p in fp.Pads():
            if p.GetNetCode() == my_net_code: continue
            pos = p.GetPosition()
            sz = p.GetSize()
            entry = {
                "x": _mm(pos.x), "y": _mm(pos.y),
                "rx": _mm(sz.x)/2, "ry": _mm(sz.y)/2,
                "net": p.GetNetname(), "ref": fp.GetReference(),
                "pad": p.GetNumber(),
            }
            for lay in (F, B):
                if p.IsOnLayer(lay):
                    pads[lay].append(entry)
    return tracks, pads, vias


def check_track(brd, x1, y1, x2, y2, layer, width_mm, my_net_code,
                obstacles=None, clearance=CLEARANCE_MM):
    """Return list of violation dicts (empty = clean)."""
    if obstacles is None:
        obstacles = collect_obstacles(brd, my_net_code)
    tracks_by_layer, pads_by_layer, vias = obstacles
    half_w = width_mm / 2
    viols = []

    for ot in tracks_by_layer.get(layer, []):
        d = seg_to_seg_dist(x1, y1, x2, y2,
                            ot["x1"], ot["y1"], ot["x2"], ot["y2"])
        need = half_w + ot["w"]/2 + clearance
        if d < need:
            viols.append({"kind":"track-track", "other":ot["net"],
                          "dist":d, "need":need})
            break  # one is enough to fail

    for op in pads_by_layer.get(layer, []):
        # Approximate pad as rectangle — use circular bound of larger half-dim
        pad_r = max(op["rx"], op["ry"])
        d = seg_to_point_dist(x1, y1, x2, y2, op["x"], op["y"]) - pad_r
        need = half_w + clearance
        if d < need:
            viols.append({"kind":"track-pad", "other":f"{op['ref']}.{op['pad']}({op['net']})",
                          "dist":d, "need":need})
            break

    for vi in vias:
        d = seg_to_point_dist(x1, y1, x2, y2, vi["x"], vi["y"]) - vi["r"]
        need = half_w + clearance
        if d < need:
            viols.append({"kind":"track-via", "other":vi["net"],
                          "dist":d, "need":need})
            break

    # Board edge
    if min(x1, x2) < EDGE_CLEARANCE_MM + half_w or max(x1, x2) > 90 - EDGE_CLEARANCE_MM - half_w \
       or min(y1, y2) < EDGE_CLEARANCE_MM + half_w or max(y1, y2) > 70 - EDGE_CLEARANCE_MM - half_w:
        viols.append({"kind":"edge", "dist":0, "need":EDGE_CLEARANCE_MM})

    return viols


def check_via(brd, x, y, dia_mm, my_net_code, obstacles=None, clearance=CLEARANCE_MM):
    """Return list of violation dicts (empty = clean)."""
    if obstacles is None:
        obstacles = collect_obstacles(brd, my_net_code)
    tracks_by_layer, pads_by_layer, vias = obstacles
    r = dia_mm / 2
    viols = []

    # Track on F.Cu and B.Cu near via
    for layer, tracks in tracks_by_layer.items():
        for ot in tracks:
            d = seg_to_point_dist(ot["x1"], ot["y1"], ot["x2"], ot["y2"], x, y) - ot["w"]/2
            need = r + clearance
            if d < need:
                viols.append({"kind":"via-track", "other":ot["net"],
                              "dist":d, "need":need})
                return viols
    # Pads
    for layer, pads in pads_by_layer.items():
        for op in pads:
            pad_r = max(op["rx"], op["ry"])
            d = math.hypot(x - op["x"], y - op["y"]) - pad_r
            need_clear = r + clearance
            need_mask = r + MASK_EXPAND_MM + pad_r/0.5 * 0  # simple approx
            need = max(need_clear, MASK_EXPAND_MM * 2)
            if d < need:
                viols.append({"kind":"via-pad", "other":f"{op['ref']}.{op['pad']}({op['net']})",
                              "dist":d, "need":need})
                return viols
    # Other vias
    for vi in vias:
        d = math.hypot(x - vi["x"], y - vi["y"]) - vi["r"]
        need = r + clearance
        if d < need:
            viols.append({"kind":"via-via", "other":vi["net"],
                          "dist":d, "need":need})
            return viols
    # Edge
    if x < EDGE_CLEARANCE_MM + r or x > 90 - EDGE_CLEARANCE_MM - r \
       or y < EDGE_CLEARANCE_MM + r or y > 70 - EDGE_CLEARANCE_MM - r:
        viols.append({"kind":"via-edge", "dist":0, "need":EDGE_CLEARANCE_MM})
    return viols


if __name__ == "__main__":
    # Self-test: load board, find an empty 0.5x0.5mm region, validate via fits
    import os
    pcb = os.path.join(os.path.dirname(__file__), "novapcb-layout-v1.1.kicad_pcb")
    brd = pcbnew.LoadBoard(pcb)
    nets = {str(k): v for k, v in brd.GetNetsByName().asdict().items()}
    obs = collect_obstacles(brd, nets["+3V3"].GetNetCode())
    print(f"obstacles: {sum(len(v) for v in obs[0].values())} tracks, "
          f"{sum(len(v) for v in obs[1].values())} pads, {len(obs[2])} vias")
    # Try a via at clear (10, 10) on +3V3
    v = check_via(brd, 10.0, 10.0, 0.60, nets["+3V3"].GetNetCode(), obs)
    print(f"via @(10,10) +3V3: {len(v)} violations  {v[:2]}")
    # Try track on +3V3 from (10,10) to (15,15)
    t = check_track(brd, 10.0, 10.0, 15.0, 15.0, pcbnew.F_Cu, 0.20,
                    nets["+3V3"].GetNetCode(), obs)
    print(f"track (10,10)->(15,15) +3V3: {len(t)} violations  {t[:2]}")
    # Test speed: 100 random checks
    import random, time
    t0 = time.time()
    n_clean = 0
    for _ in range(100):
        x = random.uniform(5, 85); y = random.uniform(5, 65)
        v = check_via(brd, x, y, 0.60, nets["+3V3"].GetNetCode(), obs)
        if not v: n_clean += 1
    dt = time.time() - t0
    print(f"100 via checks in {dt:.3f}s ({dt*10:.1f}ms each), {n_clean} clean")
