#!/usr/bin/env python3
"""Step 5 residual closer — RIGOROUS collision-aware enumeration.

Per master 2026-05-21 PR #62 audit: "collision-aware placement is a
CODE task when you have the geometry, which you do." Previous attempts
skipped the clearance check. This time: enumerate candidate locations,
geometric-clearance-check each against the full inventory, place only
verified-clear ones.

Residuals (final Freerouting run):
  #1 F.Cu Track (71.11, 31.32) ↔ F.Cu Via (69.20, 29.82) — 2.4 mm IMU area
  #2 In2.Cu Zone islands ↔ In2.Cu Zone islands — plane fragmentation
  #3 F.Cu Track (69.15, 28.80) ↔ F.Cu Track (64.54, 30.00) — 4.8 mm

For #1, #3 (track-to-track / track-to-via): enumerate a path of segments
(direct + L-shape detours) and pick first one where every segment
sample point passes pad/via clearance.

For #2 (plane bridge): pick an existing +3V3 via INSIDE an orphan island.
Enumerate candidate via locations in MAIN island within reach (≤ 5 mm).
For each, geometric-clearance-check against full pad/via inventory.
Place first verified-clear via + connecting segment.
"""

import os
import sys
import math
import pcbnew
import subprocess
import re

HERE = os.path.dirname(os.path.abspath(__file__))
PCB_PATH = os.path.join(HERE, "novapcb-layout-v2.kicad_pcb")
TRACK_WIDTH_MM = 0.20
VIA_OUTER_MM = 0.60        # was 0.45; bump to give room for 0.30 drill + annular
VIA_DRILL_MM = 0.30        # was 0.20; board min hole is 0.30 (DRC)
TRACK_HALF = TRACK_WIDTH_MM / 2
VIA_HALF = VIA_OUTER_MM / 2
DEFAULT_CLEARANCE = 0.20   # netclass clearance — actual is 0.20 not 0.15
SEGMENT_SAMPLE_MM = 0.1    # sample density along segments for clearance check


def _mm(x): return int(x * 1_000_000)


# ============================================================
# Inventory: enumerate every pad, via, track on the board
# ============================================================

def build_inventory(brd):
    """Return dict with all blocking features.

    Each feature is a dict: type, layer, x, y, half_w, half_h, net_code.
    Net code lets us skip same-net features (same-net is fine).
    """
    inv = {"F.Cu": [], "B.Cu": [], "all": []}

    for fp in brd.GetFootprints():
        for pad in fp.Pads():
            # Use BOARD-frame bounding box so pad rotation is correctly captured.
            bb = pad.GetBoundingBox()
            x = (bb.GetX() + bb.GetWidth()/2) / 1e6
            y = (bb.GetY() + bb.GetHeight()/2) / 1e6
            hw = bb.GetWidth() / 2e6
            hh = bb.GetHeight() / 2e6
            net = pad.GetNet().GetNetCode() if pad.GetNet() else 0
            item = {"type": "pad", "x": x, "y": y, "hw": hw, "hh": hh,
                    "net": net, "ref": f"{fp.GetReference()}.{pad.GetNumber()}"}
            if pad.IsOnLayer(pcbnew.F_Cu):
                inv["F.Cu"].append(item)
            if pad.IsOnLayer(pcbnew.B_Cu):
                inv["B.Cu"].append(item)
            # Also add to inner-layer inventory (through-hole pads + IP pads
            # span inner layers; SMD pads stay on outer)
            for in_layer in ["In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu"]:
                inv.setdefault(in_layer, [])
                if pad.IsOnLayer(brd.GetLayerID(in_layer)):
                    inv[in_layer].append(item)
            inv["all"].append(item)

    # Track all inner layers we might have tracks/vias on
    for in_layer in ["In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu"]:
        inv.setdefault(in_layer, [])

    for t in brd.GetTracks():
        if isinstance(t, pcbnew.PCB_VIA):
            p = t.GetPosition()
            x, y = p.x / 1e6, p.y / 1e6
            # Use BBox for via (covers actual outer extent)
            bb = t.GetBoundingBox()
            half = max(bb.GetWidth(), bb.GetHeight()) / 2e6
            net = t.GetNet().GetNetCode() if t.GetNet() else 0
            item = {"type": "via", "x": x, "y": y, "hw": half, "hh": half,
                    "net": net, "ref": f"via({x:.2f},{y:.2f})"}
            inv["F.Cu"].append(item)
            inv["B.Cu"].append(item)
            # Through-vias touch all inner layers too
            for in_layer in ["In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu"]:
                inv[in_layer].append(item)
            inv["all"].append(item)
        else:
            # Track — sample as series of points
            s, e = t.GetStart(), t.GetEnd()
            x1, y1 = s.x / 1e6, s.y / 1e6
            x2, y2 = e.x / 1e6, e.y / 1e6
            w = t.GetWidth() / 1e6
            net = t.GetNet().GetNetCode() if t.GetNet() else 0
            layer_id = t.GetLayer()
            if layer_id == pcbnew.F_Cu:
                layer_name = "F.Cu"
            elif layer_id == pcbnew.B_Cu:
                layer_name = "B.Cu"
            else:
                # Inner layer
                layer_name = brd.GetLayerName(layer_id)
            if layer_name in inv:
                inv[layer_name].append(
                    {"type": "track", "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                     "w": w, "net": net,
                     "ref": f"track[{net}] {layer_name} ({x1:.2f},{y1:.2f})-({x2:.2f},{y2:.2f})"})
    return inv


# ============================================================
# Collision-checking primitives
# ============================================================

def point_clear_of_feature(px, py, item, my_net, my_radius):
    """True if a point (px, py) is clearance-clear of `item`."""
    if item["net"] == my_net:
        return True  # same net is fine
    if item["type"] == "pad":
        # Distance to nearest pad edge
        dx = max(0, abs(px - item["x"]) - item["hw"])
        dy = max(0, abs(py - item["y"]) - item["hh"])
        d = math.sqrt(dx**2 + dy**2)
        return d >= my_radius + DEFAULT_CLEARANCE
    elif item["type"] == "via":
        d = math.sqrt((px - item["x"])**2 + (py - item["y"])**2)
        return d >= my_radius + item["hw"] + DEFAULT_CLEARANCE
    elif item["type"] == "track":
        # Distance from point to line segment
        x1, y1, x2, y2 = item["x1"], item["y1"], item["x2"], item["y2"]
        dx, dy = x2 - x1, y2 - y1
        ll = dx*dx + dy*dy
        if ll == 0:
            t = 0
        else:
            t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / ll))
        cx, cy = x1 + t*dx, y1 + t*dy
        d = math.sqrt((px - cx)**2 + (py - cy)**2)
        return d >= my_radius + item["w"]/2 + DEFAULT_CLEARANCE
    return True


def via_clear(brd_inv, x, y, my_net):
    """True if a via at (x, y) on `my_net` clears all features on EVERY layer
    it passes through (F.Cu, B.Cu, AND inner layers In1..In4)."""
    for layer in ["F.Cu", "B.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu"]:
        if layer not in brd_inv: continue
        for item in brd_inv[layer]:
            if not point_clear_of_feature(x, y, item, my_net, VIA_HALF):
                return False, item
    return True, None


def segment_clear(brd_inv, layer, x1, y1, x2, y2, my_net):
    """True if a track segment on `layer` clears all features on that layer."""
    layer_key = "F.Cu" if layer == pcbnew.F_Cu else "B.Cu"
    length = math.sqrt((x2-x1)**2 + (y2-y1)**2)
    n_samples = max(2, int(length / SEGMENT_SAMPLE_MM) + 1)
    for i in range(n_samples + 1):
        t = i / n_samples
        px, py = x1 + t*(x2-x1), y1 + t*(y2-y1)
        for item in brd_inv[layer_key]:
            if not point_clear_of_feature(px, py, item, my_net, TRACK_HALF):
                return False, item, (px, py)
    return True, None, None


# ============================================================
# Board-modification primitives
# ============================================================

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


def fill_save(brd):
    pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
    pcbnew.SaveBoard(PCB_PATH, brd)


def drc():
    subprocess.run(["kicad-cli", "pcb", "drc", "--severity-error", "--format", "report",
                    "--output", os.path.join(HERE, "drc_report.txt"), PCB_PATH],
                   capture_output=True)
    with open(os.path.join(HERE, "drc_report.txt")) as f:
        txt = f.read()
    blocks = re.split(r'\n(?=\[)', txt)
    err = sum(1 for b in blocks if b.startswith('[') and 'unconnected_items' not in b
              and not b.startswith('** '))
    unc = sum(1 for b in blocks if 'unconnected_items' in b)
    return err, unc


# ============================================================
# Residual closers
# ============================================================

def try_segment(brd, brd_inv, layer, x1, y1, x2, y2, net_code, net_obj, label):
    """Try to lay a direct segment; if it clears, place it."""
    ok, blocker, blocker_pt = segment_clear(brd_inv, layer, x1, y1, x2, y2, net_code)
    if ok:
        add_track(brd, x1, y1, x2, y2, layer, net_obj)
        print(f"    ✓ {label}: direct segment ({x1:.2f},{y1:.2f})→({x2:.2f},{y2:.2f}) CLEAR")
        return True
    print(f"    ✗ {label}: direct segment blocked at ({blocker_pt[0]:.2f},{blocker_pt[1]:.2f}) by {blocker['ref']}")
    return False


def try_l_shape(brd, brd_inv, layer, x1, y1, x2, y2, net_code, net_obj, label):
    """Try L-shaped segment with many corner candidates."""
    # Enumerate corner offsets — detour up to 4 mm in each direction
    candidates = []
    for dx in [-4, -3, -2, -1, 0, 1, 2, 3, 4]:
        for dy in [-4, -3, -2, -1, 0, 1, 2, 3, 4]:
            if dx == 0 and dy == 0: continue
            # Two L-shape forms with offset (dx, dy) added to natural corner
            for corner_x, corner_y, name in [
                (x2 + dx, y1 + dy, f"H/V offset ({dx},{dy})"),
                (x1 + dx, y2 + dy, f"V/H offset ({dx},{dy})"),
            ]:
                total_len = (math.sqrt((corner_x-x1)**2 + (corner_y-y1)**2) +
                             math.sqrt((x2-corner_x)**2 + (y2-corner_y)**2))
                candidates.append((total_len, corner_x, corner_y, name))
    candidates.sort()
    for _, cx, cy, name in candidates:
        ok1, b1, _ = segment_clear(brd_inv, layer, x1, y1, cx, cy, net_code)
        ok2, b2, _ = segment_clear(brd_inv, layer, cx, cy, x2, y2, net_code)
        if ok1 and ok2:
            add_track(brd, x1, y1, cx, cy, layer, net_obj)
            add_track(brd, cx, cy, x2, y2, layer, net_obj)
            print(f"    ✓ {label}: L-shape via ({cx:.2f},{cy:.2f}) [{name}] CLEAR")
            return True
    print(f"    ✗ {label}: no L-shape corner clears (tried {len(candidates)} candidates)")
    return False


def try_offset_endpoint_segment(brd, brd_inv, layer, x1, y1, x2, y2, net_code, net_obj, label):
    """When the start/end is at a pad-clearance boundary: offset the endpoints
    by up to 0.5 mm and try L-shape from offset point."""
    for off_x in [-0.5, -0.3, 0, 0.3, 0.5]:
        for off_y in [-0.5, -0.3, 0, 0.3, 0.5]:
            x1o, y1o = x1 + off_x, y1 + off_y
            for off_x2 in [-0.5, -0.3, 0, 0.3, 0.5]:
                for off_y2 in [-0.5, -0.3, 0, 0.3, 0.5]:
                    x2o, y2o = x2 + off_x2, y2 + off_y2
                    # Stub segments from endpoints to offset points
                    ok_a, _, _ = segment_clear(brd_inv, layer, x1, y1, x1o, y1o, net_code)
                    ok_b, _, _ = segment_clear(brd_inv, layer, x2, y2, x2o, y2o, net_code)
                    ok_mid, _, _ = segment_clear(brd_inv, layer, x1o, y1o, x2o, y2o, net_code)
                    if ok_a and ok_b and ok_mid:
                        # Place
                        if (x1, y1) != (x1o, y1o):
                            add_track(brd, x1, y1, x1o, y1o, layer, net_obj)
                        if (x2, y2) != (x2o, y2o):
                            add_track(brd, x2, y2, x2o, y2o, layer, net_obj)
                        add_track(brd, x1o, y1o, x2o, y2o, layer, net_obj)
                        print(f"    ✓ {label}: stubbed direct via ({x1o:.2f},{y1o:.2f})→({x2o:.2f},{y2o:.2f})")
                        return True
    return False


def enumerate_via_location(brd, brd_inv, near_x, near_y, net_code, net_obj,
                            radius_max=5.0, grid=0.1):
    """Enumerate candidate via locations in a square around (near_x, near_y).
    Return first CLEAR location (within radius_max, grid step `grid` mm)."""
    candidates = []
    for dx in [g * grid for g in range(-int(radius_max/grid), int(radius_max/grid) + 1)]:
        for dy in [g * grid for g in range(-int(radius_max/grid), int(radius_max/grid) + 1)]:
            x, y = near_x + dx, near_y + dy
            ok, blocker = via_clear(brd_inv, x, y, net_code)
            if ok:
                candidates.append((math.sqrt(dx*dx + dy*dy), x, y))
    candidates.sort()
    return candidates


# ============================================================
# Main
# ============================================================

def main():
    print(f"[1] load board + initial DRC")
    brd = pcbnew.LoadBoard(PCB_PATH)
    nets = {str(k): v for k, v in brd.GetNetsByName().asdict().items()}
    n3v3 = nets["+3V3"]
    n3v3_code = n3v3.GetNetCode()
    err, unc = drc()
    print(f"    initial: {err} errors, {unc} unconnected")

    print(f"\n[2] build inventory of all pads + vias + tracks")
    inv = build_inventory(brd)
    print(f"    F.Cu items: {len(inv['F.Cu'])}, B.Cu items: {len(inv['B.Cu'])}")

    # ============================================================
    # Residual #1: F.Cu Track (71.11, 31.32) ↔ F.Cu Via (69.20, 29.82)
    # Direct F.Cu segment 2.4 mm
    # ============================================================
    print(f"\n[3] residual #1: F.Cu (71.11, 31.32) ↔ (69.20, 29.82)")
    closed1 = try_segment(brd, inv, pcbnew.F_Cu, 71.11, 31.32, 69.20, 29.82, n3v3_code, n3v3, "#1 direct")
    if not closed1:
        closed1 = try_l_shape(brd, inv, pcbnew.F_Cu, 71.11, 31.32, 69.20, 29.82, n3v3_code, n3v3, "#1 L-shape")
    if not closed1:
        closed1 = try_offset_endpoint_segment(brd, inv, pcbnew.F_Cu, 71.11, 31.32, 69.20, 29.82, n3v3_code, n3v3, "#1 offset")
    if not closed1:
        # Fallback: just place a via at each stranded endpoint to drop into
        # the +3V3 plane. Each endpoint then joins whichever +3V3 island it
        # lands in — if both land in MAIN, the residual closes.
        print(f"    fallback: drop stranded stubs into +3V3 plane via individual vias")
        inv2 = build_inventory(brd)
        for name, x, y in [("stub A", 71.11, 31.32), ("stub B", 69.20, 29.82)]:
            cands = enumerate_via_location(brd, inv2, x, y, n3v3_code, n3v3, radius_max=0.8, grid=0.05)
            if cands:
                _, vx, vy = cands[0]
                add_via(brd, vx, vy, n3v3)
                add_track(brd, x, y, vx, vy, pcbnew.F_Cu, n3v3)
                print(f"    ✓ #1 fallback {name}: via at ({vx:.2f},{vy:.2f}) + F.Cu segment ({x:.2f},{y:.2f})→({vx:.2f},{vy:.2f})")
            else:
                print(f"    ✗ #1 fallback {name}: no clear via location within 0.8 mm")

    # ============================================================
    # Residual #3: F.Cu Track (69.15, 28.80) ↔ F.Cu Track (64.54, 30.00)
    # Direct F.Cu segment 4.8 mm
    # ============================================================
    print(f"\n[4] residual #3: F.Cu (69.15, 28.80) ↔ (64.54, 30.00)")
    # Re-build inventory after #1 modifications
    inv = build_inventory(brd)
    closed3 = try_segment(brd, inv, pcbnew.F_Cu, 69.15, 28.80, 64.54, 30.00, n3v3_code, n3v3, "#3 direct")
    if not closed3:
        closed3 = try_l_shape(brd, inv, pcbnew.F_Cu, 69.15, 28.80, 64.54, 30.00, n3v3_code, n3v3, "#3 L-shape")
    if not closed3:
        closed3 = try_offset_endpoint_segment(brd, inv, pcbnew.F_Cu, 69.15, 28.80, 64.54, 30.00, n3v3_code, n3v3, "#3 offset")

    # ============================================================
    # Residual #2: +3V3 plane fragmentation
    # Orphan islands at:
    #   #1 (X=29.6..34.9, Y=23.8..27.5) — near MCU SW (R51.1 pull-up trapped)
    #   #0 (X=45.4..48.6, Y=28.7..29.8) — near MCU east
    # Bridge each via a new via in MAIN + B.Cu segment
    # ============================================================
    print(f"\n[5] residual #2: +3V3 plane fragmentation")

    inv = build_inventory(brd)

    # Generic bridge function: enumerate via candidates near orphan boundary +
    # enumerate connecting segment via direct + L-shape; pick first combo that
    # passes both.
    def try_bridge_plane(orphan_via_x, orphan_via_y, orphan_bbox, label, brd, inv):
        """orphan_via_x, orphan_via_y: existing +3V3 via inside orphan.
        orphan_bbox: (xmin, xmax, ymin, ymax) of orphan polygon.
        Try to bridge to MAIN via L-shape B.Cu segment + new via.
        """
        x_min, x_max, y_min, y_max = orphan_bbox
        # Candidate via locations: grid over a wider box (8 mm padding)
        via_cands = []
        for vx_int in range(int((x_min - 8) * 10), int((x_max + 8) * 10) + 1, 2):
            for vy_int in range(int((y_min - 8) * 10), int((y_max + 8) * 10) + 1, 2):
                vx, vy = vx_int / 10, vy_int / 10
                if x_min <= vx <= x_max and y_min <= vy <= y_max:
                    continue   # inside orphan, won't help
                # Distance from orphan via (longer reach OK)
                d = math.sqrt((vx - orphan_via_x)**2 + (vy - orphan_via_y)**2)
                if d > 8: continue
                ok, _ = via_clear(inv, vx, vy, n3v3_code)
                if ok:
                    via_cands.append((d, vx, vy))
        via_cands.sort()
        print(f"    {label}: enumerated {len(via_cands)} clear via candidates near orphan")

        for d, vx, vy in via_cands[:20]:   # try closest 20
            # Try direct B.Cu segment first
            ok, _, _ = segment_clear(inv, pcbnew.B_Cu, orphan_via_x, orphan_via_y, vx, vy, n3v3_code)
            if ok:
                add_via(brd, vx, vy, n3v3)
                add_track(brd, orphan_via_x, orphan_via_y, vx, vy, pcbnew.B_Cu, n3v3)
                print(f"    ✓ {label}: via at ({vx:.2f},{vy:.2f}) + direct B.Cu segment from ({orphan_via_x:.2f},{orphan_via_y:.2f})")
                return True
            # Try L-shape segments
            for dx_corner in [-2, -1, 0, 1, 2]:
                for dy_corner in [-2, -1, 0, 1, 2]:
                    if dx_corner == 0 and dy_corner == 0: continue
                    cx, cy = vx + dx_corner, vy + dy_corner
                    ok1, _, _ = segment_clear(inv, pcbnew.B_Cu, orphan_via_x, orphan_via_y, cx, cy, n3v3_code)
                    ok2, _, _ = segment_clear(inv, pcbnew.B_Cu, cx, cy, vx, vy, n3v3_code)
                    if ok1 and ok2:
                        add_via(brd, vx, vy, n3v3)
                        add_track(brd, orphan_via_x, orphan_via_y, cx, cy, pcbnew.B_Cu, n3v3)
                        add_track(brd, cx, cy, vx, vy, pcbnew.B_Cu, n3v3)
                        print(f"    ✓ {label}: via at ({vx:.2f},{vy:.2f}) + L-shape via ({cx:.2f},{cy:.2f})")
                        return True
            # Try F.Cu segment instead of B.Cu (in case B.Cu has many SDMMC tracks)
            ok_f, _, _ = segment_clear(inv, pcbnew.F_Cu, orphan_via_x, orphan_via_y, vx, vy, n3v3_code)
            if ok_f:
                add_via(brd, vx, vy, n3v3)
                add_track(brd, orphan_via_x, orphan_via_y, vx, vy, pcbnew.F_Cu, n3v3)
                print(f"    ✓ {label}: via at ({vx:.2f},{vy:.2f}) + F.Cu segment (B.Cu blocked)")
                return True
        print(f"    ✗ {label}: no clear via + segment combination found among {min(20, len(via_cands))} via candidates")
        return False

    closed_orphan1 = try_bridge_plane(30.05, 26.99, (29.6, 34.9, 23.8, 27.5), "[5a] orphan-#1", brd, inv)
    inv = build_inventory(brd)
    closed_orphan0 = try_bridge_plane(48.51, 29.08, (45.4, 48.6, 28.7, 29.8), "[5b] orphan-#0", brd, inv)

    print(f"\n[6] fill + save + DRC")
    fill_save(brd)
    err, unc = drc()
    print(f"    after rigorous-stitch: {err} errors, {unc} unconnected")


if __name__ == "__main__":
    main()
