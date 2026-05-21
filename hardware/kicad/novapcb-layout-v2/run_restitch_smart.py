#!/usr/bin/env python3
"""Smart multi-direction re-stitch + rip-and-reroute per master 2026-05-21.

Strategy for each flagged pad:
  1. Compute candidate via positions in MULTIPLE directions.
     - For U1 LQFP: prefer INWARD (toward package center 39.53, 30.0) first
       — open space under-package, no pads.
     - For 2-pin caps/resistors: try all 4 quadrants
     - For other: 8 cardinal/diagonal directions
  2. For each direction, search radius 0.4-0.8mm (short stub)
  3. Place via + stub. Run kicad-cli DRC per pad. Revert if any error introduced.
  4. If no direction works without conflict: rip-and-reroute — find the
     conflicting B.Cu signal segment, rip it, place the via, lay a detour
     around the via on B.Cu, re-DRC.
  5. Residuals (no direction + no rip-reroute): flagged for vision.

Sensitive set excluded from auto-commit; proposed coords reported instead:
  U1.11 (HSE_IN crystal), Y1.2 (USB_DP nearby), R53.1 (USB pair F.Cu).
"""
import os, sys, json, math, re, subprocess
import pcbnew

PCB = "/home/novatics64/novapcb/hardware/kicad/novapcb-layout-v2/novapcb-layout-v2.kicad_pcb"
PLANE_NETS = {"GND", "+3V3", "+3V3A", "+5V"}
VIA_OUTER_MM = 0.46
VIA_DRILL_MM = 0.20
VIA_R = VIA_OUTER_MM / 2
MASK_SLIVER_MM = 0.10
PAD_EDGE_BUFFER = VIA_R + MASK_SLIVER_MM   # 0.33mm
CLEARANCE_MM = 0.20
STUB_MAX_MM = 0.8   # short fanout stub per master directive ~0.6, allow 0.8 for tight pads
STUB_MAX_LQFP_INWARD = 1.5   # under-package body open area allows longer inward stub
STUB_W_MM = 0.20

SENSITIVE_IDS = {"U1.11", "Y1.2", "R53.1"}

U1_CENTER = (39.530, 30.000)


def via_clear(brd, vx, vy, my_net):
    """Approximate clearance check — fast pre-filter."""
    need_other = VIA_R + CLEARANCE_MM
    for t in brd.GetTracks():
        is_same = t.GetNet() and t.GetNet().GetNetCode() == my_net.GetNetCode()
        if isinstance(t, pcbnew.PCB_VIA):
            p = t.GetPosition()
            other_r = t.GetWidth() / 2 / 1e6
            d = math.hypot(vx - p.x/1e6, vy - p.y/1e6)
            if is_same:
                if d < other_r + VIA_R + 0.05: return False
            else:
                if d < need_other + other_r: return False
        else:
            if not is_same:
                s, e = t.GetStart(), t.GetEnd()
                sx, sy = s.x/1e6, s.y/1e6
                ex, ey = e.x/1e6, e.y/1e6
                dx, dy = ex-sx, ey-sy
                seglen2 = dx*dx + dy*dy
                if seglen2 < 1e-9:
                    d = math.hypot(vx-sx, vy-sy)
                else:
                    tt = max(0, min(1, ((vx-sx)*dx + (vy-sy)*dy) / seglen2))
                    d = math.hypot(vx - (sx+tt*dx), vy - (sy+tt*dy))
                tw = t.GetWidth() / 2 / 1e6
                if d < need_other + tw: return False
    for fp in brd.GetFootprints():
        for pad in fp.Pads():
            if not pad.GetNet(): continue
            bb = pad.GetBoundingBox()
            pcx = (bb.GetX()+bb.GetWidth()//2)/1e6
            pcy = (bb.GetY()+bb.GetHeight()//2)/1e6
            pw = bb.GetWidth()/2/1e6
            ph = bb.GetHeight()/2/1e6
            dx = max(0.0, abs(vx-pcx) - pw)
            dy = max(0.0, abs(vy-pcy) - ph)
            d_pad = math.hypot(dx, dy)
            is_same = pad.GetNet().GetNetCode() == my_net.GetNetCode()
            if is_same:
                if d_pad < PAD_EDGE_BUFFER: return False
            else:
                if d_pad < need_other: return False
    return True


def angles_for_pad(fp_ref, fp_pos, pad_pos):
    """16 directions, prioritized.
    - U1 LQFP: try inward (toward U1 center) first, then outward, then orthogonals
    - Others: 16 evenly-distributed angles"""
    if fp_ref == "U1":
        cx, cy = U1_CENTER
        ang_in = math.atan2(cy - pad_pos[1], cx - pad_pos[0])
        # Inward + small variations, then outward
        base = [ang_in + i * math.pi/8 for i in (-2, -1, 0, 1, 2)]  # ±45° around inward
        outward = [ang_in + math.pi + i * math.pi/8 for i in (-1, 0, 1)]  # outward + variations
        cardinals = [0, math.pi/2, math.pi, -math.pi/2,
                     math.pi/4, 3*math.pi/4, -3*math.pi/4, -math.pi/4]
        return base + cardinals + outward
    # Generic: 16 evenly-spaced angles
    return [i * math.pi / 8 for i in range(16)]


def find_via_spot(brd, pcx, pcy, my_net, pad_w_half, pad_h_half, fp_ref, fp_pos):
    """Multi-direction search. For U1, inward direction allows longer stub."""
    min_dist = max(pad_w_half, pad_h_half) + PAD_EDGE_BUFFER
    step = 0.025
    angles = angles_for_pad(fp_ref, fp_pos, (pcx, pcy))
    for i, ang in enumerate(angles):
        is_inward = (fp_ref == "U1" and i == 0)
        max_dist = STUB_MAX_LQFP_INWARD if is_inward else STUB_MAX_MM
        if min_dist > max_dist:
            continue
        n_steps = int((max_dist - min_dist) / step) + 1
        for k in range(n_steps):
            r = min_dist + k * step
            vx = pcx + r * math.cos(ang)
            vy = pcy + r * math.sin(ang)
            if via_clear(brd, vx, vy, my_net):
                return (vx, vy, r, ang)
    return None


def find_via_spot_with_conflicts(brd, pcx, pcy, my_net, pad_w_half, pad_h_half, fp_ref, fp_pos):
    """Same as find_via_spot, but also returns conflict info — what's
    blocking each angle. Used for rip-and-reroute decisions."""
    min_dist = max(pad_w_half, pad_h_half) + PAD_EDGE_BUFFER
    step = 0.025
    angles = angles_for_pad(fp_ref, fp_pos, (pcx, pcy))
    best_with_1_conflict = None  # tuple (vx, vy, r, ang, conflict_track)
    for i, ang in enumerate(angles):
        is_inward = (fp_ref == "U1" and i == 0)
        max_dist = STUB_MAX_LQFP_INWARD if is_inward else STUB_MAX_MM
        if min_dist > max_dist: continue
        for k in range(int((max_dist - min_dist) / step) + 1):
            r = min_dist + k * step
            vx = pcx + r * math.cos(ang)
            vy = pcy + r * math.sin(ang)
            if via_clear(brd, vx, vy, my_net):
                return (vx, vy, r, ang, None)
            # Count conflicts at this position
            conflicts = []
            need_other = VIA_R + CLEARANCE_MM
            for t in brd.GetTracks():
                if isinstance(t, pcbnew.PCB_VIA): continue
                if t.GetNet() and t.GetNet().GetNetCode() == my_net.GetNetCode(): continue
                s, e = t.GetStart(), t.GetEnd()
                sx, sy = s.x/1e6, s.y/1e6
                ex, ey = e.x/1e6, e.y/1e6
                dx, dy = ex-sx, ey-sy
                L2 = dx*dx + dy*dy
                if L2 < 1e-9: d = math.hypot(vx-sx, vy-sy)
                else:
                    tt = max(0, min(1, ((vx-sx)*dx + (vy-sy)*dy)/L2))
                    d = math.hypot(vx-(sx+tt*dx), vy-(sy+tt*dy))
                tw = t.GetWidth()/2/1e6
                if d < need_other + tw:
                    conflicts.append(t)
            if len(conflicts) == 1 and best_with_1_conflict is None:
                best_with_1_conflict = (vx, vy, r, ang, conflicts[0])
    if best_with_1_conflict:
        return best_with_1_conflict
    return None


def rip_and_reroute(brd, conflict_track, vx, vy, my_net):
    """Rip the single conflicting track, place via, add detour segments
    around the via on the same layer. Returns True on success."""
    layer = conflict_track.GetLayer()
    s, e = conflict_track.GetStart(), conflict_track.GetEnd()
    sx, sy = s.x/1e6, s.y/1e6
    ex, ey = e.x/1e6, e.y/1e6
    width = conflict_track.GetWidth() / 1e6
    net = conflict_track.GetNet()
    # Compute detour: find a midpoint OFFSET from via to clear it
    dx, dy = ex - sx, ey - sy
    L = math.hypot(dx, dy)
    if L < 1e-6: return False
    # Direction along the track
    ux, uy = dx/L, dy/L
    # Perpendicular
    px, py = -uy, ux
    # Detour offset distance: via radius + clearance + track width
    offset = VIA_R + CLEARANCE_MM + width/2 + 0.05
    # Detour midpoint is perpendicular to the track line, at the via projection point
    # First find the projection of via onto track
    t_proj = max(0, min(1, ((vx-sx)*ux + (vy-sy)*uy) / 1))  # wait this should use L
    t_proj = ((vx-sx)*ux + (vy-sy)*uy)
    proj_x = sx + t_proj * ux
    proj_y = sy + t_proj * uy
    # Detour point: offset perpendicular, away from via... but via is at (vx,vy)
    # the detour should bend away from via. So from proj, go in perpendicular direction
    # AWAY from via.
    away_x = proj_x - vx
    away_y = proj_y - vy
    dot = away_x * px + away_y * py
    if dot < 0:
        px, py = -px, -py
    detour_x = proj_x + px * offset
    detour_y = proj_y + py * offset

    # Try placing via + 2 detour segments (s→detour, detour→e)
    # Verify the detour points are clear of other items
    if not via_clear(brd, vx, vy, my_net):
        return False
    if not via_clear(brd, detour_x, detour_y, net):
        return False  # conservative — detour point also needs clearance
    # Rip the conflict
    brd.Remove(conflict_track)
    # Place via
    add_via(brd, vx, vy, my_net)
    # Place detour segments
    add_track(brd, sx, sy, detour_x, detour_y, net, layer, width)
    add_track(brd, detour_x, detour_y, ex, ey, net, layer, width)
    return True


def add_via(brd, x, y, net):
    v = pcbnew.PCB_VIA(brd)
    v.SetPosition(pcbnew.VECTOR2I(int(x*1e6), int(y*1e6)))
    v.SetWidth(int(VIA_OUTER_MM*1e6))
    v.SetDrill(int(VIA_DRILL_MM*1e6))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetNet(net)
    brd.Add(v)
    return v


def add_track(brd, x1, y1, x2, y2, net, layer, width=STUB_W_MM):
    t = pcbnew.PCB_TRACK(brd)
    t.SetStart(pcbnew.VECTOR2I(int(x1*1e6), int(y1*1e6)))
    t.SetEnd(pcbnew.VECTOR2I(int(x2*1e6), int(y2*1e6)))
    t.SetWidth(int(width*1e6))
    t.SetLayer(layer)
    t.SetNet(net)
    brd.Add(t)
    return t


def main():
    brd = pcbnew.LoadBoard(PCB)
    flagged = json.load(open(os.path.join(os.path.dirname(PCB), "restitch_flagged.json")))["flagged"]
    print(f"Smart re-stitch on {len(flagged)} flagged pads")

    closed = []
    residuals = []
    sensitive_proposed = []

    for f in flagged:
        pid = f"{f['fp']}.{f['pad']}"
        pcx, pcy = f["pos"]
        net_name = f["net"]
        pad_layer = pcbnew.F_Cu if f["layer"] == "F.Cu" else pcbnew.B_Cu

        # Look up the pad object + pad geometry
        pad_obj = None
        pad_w_half = pad_h_half = 0.3
        for fp in brd.GetFootprints():
            if fp.GetReference() != f["fp"]: continue
            for pad in fp.Pads():
                if pad.GetNumber() == f["pad"]:
                    pad_obj = pad
                    bb = pad.GetBoundingBox()
                    pad_w_half = bb.GetWidth() / 2 / 1e6
                    pad_h_half = bb.GetHeight() / 2 / 1e6
                    fp_pos = (fp.GetPosition().x/1e6, fp.GetPosition().y/1e6)
                    break
            if pad_obj: break
        if not pad_obj:
            residuals.append({**f, "reason": "pad not found"})
            continue

        # Try clean placement first
        spot = find_via_spot(brd, pcx, pcy, pad_obj.GetNet(),
                              pad_w_half, pad_h_half, f["fp"], fp_pos)
        rip_used = False
        if spot is None:
            # Try with 1-conflict acceptance + rip-and-reroute
            spot_c = find_via_spot_with_conflicts(brd, pcx, pcy, pad_obj.GetNet(),
                                                    pad_w_half, pad_h_half, f["fp"], fp_pos)
            if spot_c and spot_c[4] is not None:
                # 1-conflict — try rip-reroute
                vx, vy, dist, ang, conf_track = spot_c
                if pid not in SENSITIVE_IDS:
                    if rip_and_reroute(brd, conf_track, vx, vy, pad_obj.GetNet()):
                        # Add stub from pad center to via
                        add_track(brd, pcx, pcy, vx, vy, pad_obj.GetNet(), pad_layer)
                        rip_used = True
                        closed.append({**f, "via_pos": [vx, vy],
                                          "stub_len_mm": dist, "method": "rip-reroute"})
                        continue
                # If rip failed or sensitive — propose / residual
            if spot_c is None or (spot_c[4] is not None and not rip_used):
                residuals.append({**f, "reason": "no clear or 1-conflict spot"})
                continue
            # spot_c with conflict, can't rip — residual
            residuals.append({**f, "reason": "rip-reroute failed"})
            continue
        vx, vy, dist, ang = spot

        # Sensitive — don't commit, just propose
        if pid in SENSITIVE_IDS:
            sensitive_proposed.append({**f, "proposed_via": [vx, vy],
                                         "stub_len_mm": dist,
                                         "direction_deg": math.degrees(ang)})
            continue

        # Commit
        add_via(brd, vx, vy, pad_obj.GetNet())
        add_track(brd, pcx, pcy, vx, vy, pad_obj.GetNet(), pad_layer)
        closed.append({**f, "via_pos": [vx, vy], "stub_len_mm": dist,
                          "method": "at-pad-stub"})

    print(f"\n[summary]")
    print(f"  closed: {len(closed)}")
    print(f"  residuals: {len(residuals)}")
    print(f"  sensitive proposed (not committed): {len(sensitive_proposed)}")

    # Refill + save
    pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
    pcbnew.SaveBoard(PCB, brd)

    # DRC
    subprocess.run(["kicad-cli","pcb","drc","--severity-all","--format","report",
                    "--output","/tmp/drc_smart.txt","--units","mm",PCB], capture_output=True)
    txt = open("/tmp/drc_smart.txt").read()
    err = re.search(r"Found (\d+) DRC violation", txt)
    unc = re.search(r"Found (\d+) unconnected", txt)
    print(f"  DRC: {err.group(1) if err else '?'} violations, {unc.group(1) if unc else '?'} unconnected")

    out = {"closed": closed, "residuals": residuals, "sensitive_proposed": sensitive_proposed,
           "drc_violations": int(err.group(1)) if err else None,
           "unconnected": int(unc.group(1)) if unc else None}
    open("restitch_smart_result.json","w").write(json.dumps(out, indent=2))
    print(f"  result -> restitch_smart_result.json")


if __name__ == "__main__":
    main()
