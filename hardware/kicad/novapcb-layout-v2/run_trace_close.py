#!/usr/bin/env python3
"""Close remaining stuck pads via short traces to nearest connected
same-net copper. Per master 2026-05-21 directive:
  - 6 GND pads → trace to F.Cu/B.Cu GND pour edge
  - 16 non-GND pads → trace to nearest connected same-net pad/via/track

Algorithm:
  For each stuck pad:
    1. Find candidate target points on the same net (existing pads,
       vias, track endpoints — anything CONNECTED).
    2. For each candidate, attempt a straight-line trace from pad
       center to candidate point.
    3. Verify the trace path is clear of OTHER-net obstacles using
       same approximate model.
    4. If straight clear → place trace.
    5. Otherwise try L-shape detour (insert intermediate point).
    6. If still no path within reasonable budget (≤5mm trace length)
       → flag for vision/component-nudge.

For GND pads: the F.Cu/B.Cu pour itself is the target — any open spot
on the pour within ~5mm is a candidate.
"""
import os, sys, math, json, re, subprocess
import pcbnew

PCB = "/home/novatics64/novapcb/hardware/kicad/novapcb-layout-v2/novapcb-layout-v2.kicad_pcb"
PLANE_NETS = {"GND", "+3V3", "+3V3A", "+5V"}
TRACE_W_MM = 0.20
CLEARANCE_MM = 0.20
MAX_TRACE_LEN_MM = 5.0


def trace_clear(brd, x1, y1, x2, y2, my_net, layer):
    """Check if a straight trace from (x1,y1) to (x2,y2) on `layer` is
    clear of other-net obstacles. Approximate: sample N points along
    segment + check distance to all other-net items."""
    L = math.hypot(x2-x1, y2-y1)
    if L < 1e-3: return True
    n_samples = max(5, int(L / 0.1))
    half_w = TRACE_W_MM / 2 + CLEARANCE_MM
    for i in range(n_samples + 1):
        t = i / n_samples
        px, py = x1 + t*(x2-x1), y1 + t*(y2-y1)
        # Check vias/tracks on the SAME layer
        for tr in brd.GetTracks():
            same_net = tr.GetNet() and tr.GetNet().GetNetCode() == my_net.GetNetCode()
            if isinstance(tr, pcbnew.PCB_VIA):
                p = tr.GetPosition()
                r = tr.GetWidth()/2/1e6
                d = math.hypot(px - p.x/1e6, py - p.y/1e6)
                if same_net:
                    if d < r + half_w - 0.05: continue  # OK to graze same-net via
                else:
                    if d < r + half_w: return False
            else:
                if tr.GetLayer() != layer: continue
                s, e = tr.GetStart(), tr.GetEnd()
                sx, sy = s.x/1e6, s.y/1e6
                ex, ey = e.x/1e6, e.y/1e6
                dx, dy = ex-sx, ey-sy
                seglen2 = dx*dx + dy*dy
                if seglen2 < 1e-9: d = math.hypot(px-sx, py-sy)
                else:
                    tt = max(0, min(1, ((px-sx)*dx + (py-sy)*dy)/seglen2))
                    d = math.hypot(px - (sx+tt*dx), py - (sy+tt*dy))
                tw = tr.GetWidth()/2/1e6
                if same_net:
                    if d < tw + half_w - 0.05: continue
                else:
                    if d < tw + half_w: return False
        # Check pads
        for fp in brd.GetFootprints():
            for pad in fp.Pads():
                if not pad.IsOnLayer(layer): continue
                if not pad.GetNet(): continue
                same_pad_net = pad.GetNet().GetNetCode() == my_net.GetNetCode()
                bb = pad.GetBoundingBox()
                pcx = (bb.GetX()+bb.GetWidth()//2)/1e6
                pcy = (bb.GetY()+bb.GetHeight()//2)/1e6
                pw = bb.GetWidth()/2/1e6
                ph = bb.GetHeight()/2/1e6
                ddx = max(0.0, abs(px-pcx) - pw)
                ddy = max(0.0, abs(py-pcy) - ph)
                d_pad = math.hypot(ddx, ddy)
                if same_pad_net:
                    continue  # touching same-net pad is fine
                if d_pad < half_w: return False
    return True


def find_same_net_targets(brd, my_net, layer, max_targets=12):
    """Find candidate points on the same net (existing pads, vias,
    track endpoints). Returns list of (x, y, kind)."""
    targets = []
    for fp in brd.GetFootprints():
        for pad in fp.Pads():
            if not pad.GetNet() or pad.GetNet().GetNetCode() != my_net.GetNetCode(): continue
            bb = pad.GetBoundingBox()
            cx = (bb.GetX()+bb.GetWidth()//2)/1e6
            cy = (bb.GetY()+bb.GetHeight()//2)/1e6
            targets.append((cx, cy, "pad"))
    for t in brd.GetTracks():
        if not t.GetNet() or t.GetNet().GetNetCode() != my_net.GetNetCode(): continue
        if isinstance(t, pcbnew.PCB_VIA):
            p = t.GetPosition()
            targets.append((p.x/1e6, p.y/1e6, "via"))
        else:
            if t.GetLayer() != layer: continue
            s, e = t.GetStart(), t.GetEnd()
            targets.append((s.x/1e6, s.y/1e6, "trk_end"))
            targets.append((e.x/1e6, e.y/1e6, "trk_end"))
    return targets


def find_pour_edge_point(brd, my_net, layer, pcx, pcy, max_r=5.0):
    """For a GND pad, find a point on the same-layer GND pour edge
    closest to pad. Returns (x, y) or None."""
    # Locate the F.Cu or B.Cu GND zone
    target_zone = None
    for z in brd.Zones():
        if z.GetNetname() != "GND": continue
        if z.GetFirstLayer() != layer: continue
        target_zone = z
        break
    if target_zone is None: return None
    poly = target_zone.GetFilledPolysList(layer)
    closest = None; closest_d = 999
    for i in range(poly.OutlineCount()):
        ol = poly.Outline(i)
        n = ol.PointCount()
        for j in range(n):
            p = ol.CPoint(j)
            x, y = p.x/1e6, p.y/1e6
            d = math.hypot(x - pcx, y - pcy)
            if d < closest_d and d < max_r:
                closest_d = d; closest = (x, y)
    return closest


def add_track_seg(brd, x1, y1, x2, y2, net, layer, width=TRACE_W_MM):
    t = pcbnew.PCB_TRACK(brd)
    t.SetStart(pcbnew.VECTOR2I(int(x1*1e6), int(y1*1e6)))
    t.SetEnd(pcbnew.VECTOR2I(int(x2*1e6), int(y2*1e6)))
    t.SetWidth(int(width*1e6))
    t.SetLayer(layer)
    t.SetNet(net)
    brd.Add(t)


def try_trace_close(brd, pcx, pcy, pad_net, pad_layer):
    """Try to close a pad by routing a short trace to a same-net target.
    Returns 'closed' or 'flagged'."""
    # For GND pads: try pour edge first
    if str(pad_net.GetNetname()) == "GND":
        edge = find_pour_edge_point(brd, pad_net, pad_layer, pcx, pcy)
        if edge:
            ex, ey = edge
            if trace_clear(brd, pcx, pcy, ex, ey, pad_net, pad_layer):
                add_track_seg(brd, pcx, pcy, ex, ey, pad_net, pad_layer)
                return "closed-pour-edge", ex, ey
    # Find same-net targets, sorted by distance
    targets = find_same_net_targets(brd, pad_net, pad_layer)
    targets = [(math.hypot(t[0]-pcx, t[1]-pcy), t) for t in targets]
    targets.sort()
    for d, (tx, ty, kind) in targets:
        if d > MAX_TRACE_LEN_MM: break
        if d < 0.1: continue  # too close (probably the target pad itself)
        # Try straight trace
        if trace_clear(brd, pcx, pcy, tx, ty, pad_net, pad_layer):
            add_track_seg(brd, pcx, pcy, tx, ty, pad_net, pad_layer)
            return f"closed-{kind}", tx, ty
        # Try L-shape via (pcx, ty) and (tx, pcy)
        for ix, iy in [(pcx, ty), (tx, pcy)]:
            if (trace_clear(brd, pcx, pcy, ix, iy, pad_net, pad_layer) and
                trace_clear(brd, ix, iy, tx, ty, pad_net, pad_layer)):
                add_track_seg(brd, pcx, pcy, ix, iy, pad_net, pad_layer)
                add_track_seg(brd, ix, iy, tx, ty, pad_net, pad_layer)
                return f"closed-L-{kind}", tx, ty
    return "flagged", None, None


def main():
    brd = pcbnew.LoadBoard(PCB)
    # Get all unconnected pads from current DRC
    subprocess.run(["kicad-cli","pcb","drc","--severity-all","--format","report",
                    "--output","/tmp/drc_pre_trace.txt","--units","mm",PCB], capture_output=True)
    txt = open("/tmp/drc_pre_trace.txt").read()
    unconnected = set()
    for m in re.finditer(r'Pad (\S+) \[([^\]]+)\] of (\S+) on', txt):
        unconnected.add((m.group(3), m.group(1), m.group(2)))
    print(f"unconnected pads: {len(unconnected)}")

    closed = []; flagged = []
    for ref, pad_num, net_name in sorted(unconnected):
        pad_obj = None; pcx = pcy = None; pad_layer = None
        for fp in brd.GetFootprints():
            if fp.GetReference() != ref: continue
            for pad in fp.Pads():
                if pad.GetNumber() == pad_num:
                    pad_obj = pad
                    bb = pad.GetBoundingBox()
                    pcx = (bb.GetX()+bb.GetWidth()//2)/1e6
                    pcy = (bb.GetY()+bb.GetHeight()//2)/1e6
                    pad_layer = pcbnew.F_Cu if pad.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu
                    break
            if pad_obj: break
        if not pad_obj: continue
        outcome, tx, ty = try_trace_close(brd, pcx, pcy, pad_obj.GetNet(), pad_layer)
        if outcome.startswith("closed"):
            closed.append({"ref": ref, "pad": pad_num, "net": net_name,
                              "outcome": outcome, "target": [tx, ty]})
        else:
            flagged.append({"ref": ref, "pad": pad_num, "net": net_name,
                               "pos": [pcx, pcy], "layer": "F.Cu" if pad_layer == pcbnew.F_Cu else "B.Cu"})

    print(f"closed: {len(closed)}")
    for c in closed:
        print(f"  {c['ref']}.{c['pad']} ({c['net']}): {c['outcome']}")
    print(f"flagged: {len(flagged)}")
    for f in flagged:
        print(f"  {f['ref']}.{f['pad']} ({f['net']}) at ({f['pos'][0]:.2f},{f['pos'][1]:.2f}) {f['layer']}")

    pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
    pcbnew.SaveBoard(PCB, brd)
    open("trace_close_result.json","w").write(json.dumps(
        {"closed": closed, "flagged": flagged}, indent=2))


if __name__ == "__main__":
    main()
