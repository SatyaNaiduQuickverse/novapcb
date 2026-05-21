#!/usr/bin/env python3
"""Step 5 FINE-GRID enumeration over the 2 problem regions.

Per master 2026-05-21 PR #62 audit (post-deletion-test): grid resolution
is the limiter, not geometric impossibility. Fine-grid (0.05 mm → 0.025
mm → 0.0125 mm) over the constrained problem region (~4×4 mm) is cheap.

Exploit B.Cu (no U3 pads) as the preferred routing layer; F.Cu is dense
with U3 IMU pads. Place via in clear B.Cu spot, route on B.Cu, drop via
at residual endpoint.

Verification logic: each placement must REDUCE the unconnected count by
≥1. If it doesn't, the placement was inert (or just-isolated copper) →
revert that placement and try another.

Residuals:
  A: Via (69.20, 29.87) ↔ F.Cu Track (71.11, 31.32) — IMU area
  B: Via (65.06, 32.87) ↔ F.Cu Track (64.17, 30.37) — IMU/crystal area
"""

import os
import sys
import math
import pcbnew
import subprocess
import re
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
PCB_PATH = os.path.join(HERE, "novapcb-layout-v2.kicad_pcb")
PCB_BACKUP = os.path.join(HERE, "novapcb-layout-v2.kicad_pcb.bak")

TRACK_WIDTH_MM = 0.20
VIA_OUTER_MM = 0.60
VIA_DRILL_MM = 0.30
TRACK_HALF = TRACK_WIDTH_MM / 2
VIA_HALF = VIA_OUTER_MM / 2
DEFAULT_CLEARANCE = 0.20
SEGMENT_SAMPLE_MM = 0.05


def _mm(x): return int(x * 1_000_000)


def build_inventory(brd):
    inv = {"F.Cu": [], "B.Cu": [], "In1.Cu": [], "In2.Cu": [], "In3.Cu": [], "In4.Cu": [], "all": []}
    for fp in brd.GetFootprints():
        for pad in fp.Pads():
            bb = pad.GetBoundingBox()
            x = (bb.GetX() + bb.GetWidth()/2) / 1e6
            y = (bb.GetY() + bb.GetHeight()/2) / 1e6
            hw = bb.GetWidth() / 2e6
            hh = bb.GetHeight() / 2e6
            net = pad.GetNet().GetNetCode() if pad.GetNet() else 0
            item = {"type": "pad", "x": x, "y": y, "hw": hw, "hh": hh, "net": net,
                    "ref": f"{fp.GetReference()}.{pad.GetNumber()}"}
            if pad.IsOnLayer(pcbnew.F_Cu): inv["F.Cu"].append(item)
            if pad.IsOnLayer(pcbnew.B_Cu): inv["B.Cu"].append(item)
            for in_layer in ["In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu"]:
                if pad.IsOnLayer(brd.GetLayerID(in_layer)):
                    inv[in_layer].append(item)
            inv["all"].append(item)
    for t in brd.GetTracks():
        if isinstance(t, pcbnew.PCB_VIA):
            p = t.GetPosition()
            x, y = p.x / 1e6, p.y / 1e6
            bb = t.GetBoundingBox()
            half = max(bb.GetWidth(), bb.GetHeight()) / 2e6
            net = t.GetNet().GetNetCode() if t.GetNet() else 0
            item = {"type": "via", "x": x, "y": y, "hw": half, "hh": half, "net": net,
                    "ref": f"via({x:.2f},{y:.2f})"}
            for L in ["F.Cu", "B.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu"]:
                inv[L].append(item)
            inv["all"].append(item)
        else:
            s, e = t.GetStart(), t.GetEnd()
            x1, y1 = s.x/1e6, s.y/1e6
            x2, y2 = e.x/1e6, e.y/1e6
            w = t.GetWidth()/1e6
            net = t.GetNet().GetNetCode() if t.GetNet() else 0
            layer_id = t.GetLayer()
            if layer_id == pcbnew.F_Cu: layer_name = "F.Cu"
            elif layer_id == pcbnew.B_Cu: layer_name = "B.Cu"
            else: layer_name = brd.GetLayerName(layer_id)
            if layer_name in inv:
                inv[layer_name].append({"type": "track", "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                                        "w": w, "net": net,
                                        "ref": f"track[{net}] {layer_name}"})
    return inv


def point_clear_of_feature(px, py, item, my_net, my_radius):
    if item["net"] == my_net: return True
    if item["type"] == "pad":
        dx = max(0, abs(px - item["x"]) - item["hw"])
        dy = max(0, abs(py - item["y"]) - item["hh"])
        d = math.sqrt(dx*dx + dy*dy)
        return d >= my_radius + DEFAULT_CLEARANCE
    elif item["type"] == "via":
        d = math.sqrt((px - item["x"])**2 + (py - item["y"])**2)
        return d >= my_radius + item["hw"] + DEFAULT_CLEARANCE
    elif item["type"] == "track":
        x1,y1,x2,y2 = item["x1"], item["y1"], item["x2"], item["y2"]
        dx, dy = x2-x1, y2-y1
        ll = dx*dx + dy*dy
        if ll == 0: t = 0
        else: t = max(0, min(1, ((px-x1)*dx + (py-y1)*dy)/ll))
        cx, cy = x1 + t*dx, y1 + t*dy
        d = math.sqrt((px-cx)**2 + (py-cy)**2)
        return d >= my_radius + item["w"]/2 + DEFAULT_CLEARANCE
    return True


def via_clear(brd_inv, x, y, my_net):
    for L in ["F.Cu", "B.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu"]:
        for item in brd_inv[L]:
            if not point_clear_of_feature(x, y, item, my_net, VIA_HALF):
                return False
    return True


def segment_clear(brd_inv, layer_key, x1, y1, x2, y2, my_net):
    length = math.sqrt((x2-x1)**2 + (y2-y1)**2)
    n = max(2, int(length / SEGMENT_SAMPLE_MM) + 1)
    for i in range(n+1):
        t = i/n
        px, py = x1+t*(x2-x1), y1+t*(y2-y1)
        for item in brd_inv[layer_key]:
            if not point_clear_of_feature(px, py, item, my_net, TRACK_HALF):
                return False, item
    return True, None


def add_track(brd, x1, y1, x2, y2, layer, net):
    t = pcbnew.PCB_TRACK(brd)
    t.SetStart(pcbnew.VECTOR2I(_mm(x1), _mm(y1)))
    t.SetEnd(pcbnew.VECTOR2I(_mm(x2), _mm(y2)))
    t.SetLayer(layer)
    t.SetWidth(_mm(TRACK_WIDTH_MM))
    t.SetNet(net)
    brd.Add(t)
    return t


def add_via(brd, x, y, net):
    v = pcbnew.PCB_VIA(brd)
    v.SetPosition(pcbnew.VECTOR2I(_mm(x), _mm(y)))
    v.SetWidth(_mm(VIA_OUTER_MM))
    v.SetDrill(_mm(VIA_DRILL_MM))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetNet(net)
    brd.Add(v)
    return v


def drc_summary():
    subprocess.run(["kicad-cli", "pcb", "drc", "--severity-error", "--format", "report",
                    "--output", os.path.join(HERE, "drc_report.txt"), PCB_PATH],
                   capture_output=True)
    with open(os.path.join(HERE, "drc_report.txt")) as f:
        txt = f.read()
    blocks = re.split(r'\n(?=\[)', txt)
    err = sum(1 for b in blocks if b.startswith('[') and 'unconnected_items' not in b
              and 'Found' not in b and 'End of' not in b)
    unc = sum(1 for b in blocks if 'unconnected_items' in b)
    return err, unc


def fill_save(brd):
    pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
    pcbnew.SaveBoard(PCB_PATH, brd)


def fine_grid_enumerate(brd, inv, roi, my_net_code, grid_steps=[0.1, 0.05, 0.025, 0.0125]):
    """Return list of clear via locations within ROI, sorted by distance from centre.
    Tries grid sizes coarse-to-fine; returns first non-empty set."""
    x_min, x_max, y_min, y_max = roi
    cx, cy = (x_min + x_max) / 2, (y_min + y_max) / 2
    for grid in grid_steps:
        candidates = []
        nx = int((x_max - x_min) / grid) + 1
        ny = int((y_max - y_min) / grid) + 1
        for ix in range(nx):
            for iy in range(ny):
                x = x_min + ix * grid
                y = y_min + iy * grid
                if via_clear(inv, x, y, my_net_code):
                    d = math.sqrt((x-cx)**2 + (y-cy)**2)
                    candidates.append((d, x, y))
        if candidates:
            candidates.sort()
            print(f"      grid={grid} mm: found {len(candidates)} clear via candidates in ROI {nx}×{ny} samples")
            return candidates, grid
    return [], grid_steps[-1]


def close_residual(brd, n3v3_code, n3v3, ep_a, ep_b, label):
    """Try to close a residual by placing a B.Cu trace + via in the open B.Cu space
    between endpoints. Uses fine grid + verification (DRC unconnected must decrease)."""
    pre_err, pre_unc = drc_summary()
    print(f"    {label}: PRE drc={pre_err} errors, {pre_unc} unconnected")

    inv = build_inventory(brd)

    # ROI: bbox of the two endpoints + 2 mm padding
    x_min = min(ep_a[0], ep_b[0]) - 2
    x_max = max(ep_a[0], ep_b[0]) + 2
    y_min = min(ep_a[1], ep_b[1]) - 2
    y_max = max(ep_a[1], ep_b[1]) + 2
    print(f"    {label}: ROI X={x_min:.2f}..{x_max:.2f}, Y={y_min:.2f}..{y_max:.2f}")

    cands, grid = fine_grid_enumerate(brd, inv, (x_min, x_max, y_min, y_max), n3v3_code)
    if not cands:
        print(f"    ✗ {label}: NO clear via location in ROI at grid down to {grid} mm")
        return False
    print(f"    {label}: trying top via candidates with B.Cu/F.Cu segment to both endpoints...")

    def try_path(layer_key, layer, vx, vy, ep, label_suffix):
        """Try direct + 25 L-shape corner offsets from via (vx,vy) to endpoint ep."""
        ok, _ = segment_clear(inv, layer_key, vx, vy, ep[0], ep[1], n3v3_code)
        if ok:
            return [(vx, vy, ep[0], ep[1])]
        # L-shape with corner offsets
        for dx in [-2, -1, 0, 1, 2]:
            for dy in [-2, -1, 0, 1, 2]:
                if dx == 0 and dy == 0: continue
                cx, cy = vx + dx, vy + dy
                ok1, _ = segment_clear(inv, layer_key, vx, vy, cx, cy, n3v3_code)
                ok2, _ = segment_clear(inv, layer_key, cx, cy, ep[0], ep[1], n3v3_code)
                if ok1 and ok2:
                    return [(vx, vy, cx, cy), (cx, cy, ep[0], ep[1])]
        return None

    for cand_idx, (d, vx, vy) in enumerate(cands[:100]):
        for layer_key, layer in [("B.Cu", pcbnew.B_Cu), ("F.Cu", pcbnew.F_Cu)]:
            path_a = try_path(layer_key, layer, vx, vy, ep_a, "to-A")
            path_b = try_path(layer_key, layer, vx, vy, ep_b, "to-B")
            if path_a and path_b:
                shutil.copy(PCB_PATH, PCB_BACKUP)
                add_via(brd, vx, vy, n3v3)
                for seg in path_a + path_b:
                    add_track(brd, seg[0], seg[1], seg[2], seg[3], layer, n3v3)
                fill_save(brd)
                post_err, post_unc = drc_summary()
                delta_unc = post_unc - pre_unc
                if post_err == 0 and post_unc < pre_unc:
                    print(f"    ✓ {label}: via ({vx:.4f},{vy:.4f}) + {layer_key} path "
                          f"(A={len(path_a)} seg, B={len(path_b)} seg) → unconnected {pre_unc}→{post_unc}")
                    return True
                else:
                    shutil.copy(PCB_BACKUP, PCB_PATH)
                    brd = pcbnew.LoadBoard(PCB_PATH)
                    n3v3 = {str(k): v for k, v in brd.GetNetsByName().asdict().items()}["+3V3"]
                    n3v3_code = n3v3.GetNetCode()
                    inv = build_inventory(brd)
    print(f"    ✗ {label}: tried {min(100, len(cands))} via candidates × 2 layers × (direct + 25 L-shapes) — none verified-reduce-unconnected")
    return False


def _close_with_reload(brd, n3v3_code, n3v3_obj, ep_a, ep_b, label, cands, start_idx):
    """Continue after a revert with fresh brd."""
    inv = build_inventory(brd)
    nets = {str(k): v for k, v in brd.GetNetsByName().asdict().items()}
    n3v3 = nets["+3V3"]
    for cand_idx, (d, vx, vy) in enumerate(cands[start_idx:50], start=start_idx):
        for layer_key, layer in [("B.Cu", pcbnew.B_Cu), ("F.Cu", pcbnew.F_Cu)]:
            ok_a, _ = segment_clear(inv, layer_key, vx, vy, ep_a[0], ep_a[1], n3v3_code)
            ok_b, _ = segment_clear(inv, layer_key, vx, vy, ep_b[0], ep_b[1], n3v3_code)
            if ok_a and ok_b:
                shutil.copy(PCB_PATH, PCB_BACKUP)
                add_via(brd, vx, vy, n3v3)
                add_track(brd, vx, vy, ep_a[0], ep_a[1], layer, n3v3)
                add_track(brd, vx, vy, ep_b[0], ep_b[1], layer, n3v3)
                fill_save(brd)
                pre_err, pre_unc = drc_summary()
                if pre_err == 0:
                    print(f"    ✓ {label}: via ({vx:.4f},{vy:.4f}) {layer_key} verified — DRC clean")
                    return True
                else:
                    shutil.copy(PCB_BACKUP, PCB_PATH)
                    brd_reload = pcbnew.LoadBoard(PCB_PATH)
                    return _close_with_reload(brd_reload, n3v3_code, n3v3_obj, ep_a, ep_b, label, cands, cand_idx+1)
    return False


def main():
    print(f"[1] load board")
    brd = pcbnew.LoadBoard(PCB_PATH)
    nets = {str(k): v for k, v in brd.GetNetsByName().asdict().items()}
    n3v3 = nets["+3V3"]
    n3v3_code = n3v3.GetNetCode()
    err, unc = drc_summary()
    print(f"    initial: {err} errors, {unc} unconnected")

    print(f"\n[2] close residual A — IMU U3.8 area (exact DRC coords)")
    close_residual(brd, n3v3_code, n3v3,
                   ep_a=(69.1996, 29.8241), ep_b=(71.1125, 31.3174),
                   label="resA")

    # Reload after residual A modifications
    brd = pcbnew.LoadBoard(PCB_PATH)
    nets = {str(k): v for k, v in brd.GetNetsByName().asdict().items()}
    n3v3 = nets["+3V3"]

    print(f"\n[3] close residual B — IMU/crystal area")
    close_residual(brd, n3v3_code, n3v3,
                   ep_a=(65.06, 32.87), ep_b=(64.17, 30.37),
                   label="resB")

    print(f"\n[4] final state")
    err, unc = drc_summary()
    print(f"    final: {err} errors, {unc} unconnected")


if __name__ == "__main__":
    main()
