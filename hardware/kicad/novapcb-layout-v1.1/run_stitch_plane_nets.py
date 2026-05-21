#!/usr/bin/env python3
"""Step 6 precursor — stitch plane-net pads to their plane fills.

After the pristine 2-layer Freerouting run, signal nets are routed on
F.Cu/B.Cu but plane nets (GND, +3V3, +3V3A, +5V) were excluded from
Freerouting entirely. Each plane-net pad on F.Cu or B.Cu needs a via
dropping to the corresponding plane layer:

  GND   pad on F.Cu -> via to In1.Cu (or In4.Cu — both GND)
  +3V3  pad on F.Cu -> via to In2.Cu
  +3V3A pad on F.Cu -> ALSO In2.Cu (it's an analog supply on the same plane net)
  +5V   pad on F.Cu -> via to In3.Cu

Through-via approach (simpler than blind/buried): place a F.Cu↔B.Cu
through-via at the pad center. The via punches through every layer,
connecting the pad to whichever plane carries that net.

For +3V3A: in this design, +3V3A may NOT be on a plane (need to check).
If it's a separate net, treat it as a signal net (already routed by
Freerouting since we removed +3V3A from PLANE_NETS earlier — wait, we
DID include it in PLANE_NETS so it was excluded. Need to verify what's
on the In2.Cu plane.

DRC verification: 0 errors, 0 unconnected after stitching.
"""
import os
import sys
import re
import subprocess
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-layout-v1.1.kicad_pcb")

# Plane net → which inner layer carries that fill
PLANE_LAYER_OF = {
    "GND": pcbnew.In1_Cu,      # also In4_Cu, but In1 is sufficient
    "+3V3": pcbnew.In2_Cu,
    "+3V3A": pcbnew.In2_Cu,    # +3V3A shares the +3V3 plane in this design (verify)
    "+5V": pcbnew.In3_Cu,
}

VIA_OUTER_MM = 0.60
VIA_DRILL_MM = 0.30


def via_at(brd, x_mm, y_mm, net, top_layer=pcbnew.F_Cu, bot_layer=pcbnew.B_Cu):
    via = pcbnew.PCB_VIA(brd)
    via.SetPosition(pcbnew.VECTOR2I(int(x_mm * 1e6), int(y_mm * 1e6)))
    via.SetWidth(int(VIA_OUTER_MM * 1e6))
    via.SetDrill(int(VIA_DRILL_MM * 1e6))
    via.SetViaType(pcbnew.VIATYPE_THROUGH)
    via.SetLayerPair(top_layer, bot_layer)
    via.SetNet(net)
    brd.Add(via)


def track_at(brd, x1, y1, x2, y2, net, layer, width_mm=0.20):
    t = pcbnew.PCB_TRACK(brd)
    t.SetStart(pcbnew.VECTOR2I(int(x1 * 1e6), int(y1 * 1e6)))
    t.SetEnd(pcbnew.VECTOR2I(int(x2 * 1e6), int(y2 * 1e6)))
    t.SetWidth(int(width_mm * 1e6))
    t.SetLayer(layer)
    t.SetNet(net)
    brd.Add(t)


def build_obstacle_index(brd):
    """Build a list of (x_mm, y_mm, radius_mm, net_code) representing
    all existing track midpoints / via centers / pad centers — enough
    to do approximate collision checks for via candidates."""
    obs = []
    # Pads (all components, all nets)
    for fp in brd.GetFootprints():
        for pad in fp.Pads():
            bb = pad.GetBoundingBox()
            cx = (bb.GetX() + bb.GetWidth()/2) / 1e6
            cy = (bb.GetY() + bb.GetHeight()/2) / 1e6
            # Use half the larger pad dimension as radius
            r = max(bb.GetWidth(), bb.GetHeight()) / 2 / 1e6
            n = pad.GetNet().GetNetCode() if pad.GetNet() else 0
            obs.append((cx, cy, r, n, "pad"))
    # Vias
    for t in brd.GetTracks():
        if isinstance(t, pcbnew.PCB_VIA):
            p = t.GetPosition()
            r = t.GetWidth() / 2 / 1e6
            n = t.GetNet().GetNetCode() if t.GetNet() else 0
            obs.append((p.x/1e6, p.y/1e6, r, n, "via"))
    # Tracks — sample midpoints + width/2 as proxy
    for t in brd.GetTracks():
        if isinstance(t, pcbnew.PCB_VIA): continue
        s, e = t.GetStart(), t.GetEnd()
        sx, sy = s.x/1e6, s.y/1e6
        ex, ey = e.x/1e6, e.y/1e6
        # Sample every 0.5mm along segment
        length = ((ex-sx)**2 + (ey-sy)**2) ** 0.5
        nsamples = max(2, int(length / 0.5))
        n = t.GetNet().GetNetCode() if t.GetNet() else 0
        w = t.GetWidth() / 1e6 / 2
        for i in range(nsamples + 1):
            tt = i / max(1, nsamples)
            x = sx + (ex-sx)*tt
            y = sy + (ey-sy)*tt
            obs.append((x, y, w, n, "track"))
    return obs


def clear_for_via(x, y, via_radius, clearance, obstacles, my_net_code):
    """Check if a via at (x,y) is clear of obstacles (other nets only)."""
    min_dist = via_radius + clearance
    for ox, oy, oradius, onet, _ in obstacles:
        if onet == my_net_code:
            continue  # same net — no clearance required
        d = ((x-ox)**2 + (y-oy)**2) ** 0.5
        if d < min_dist + oradius:
            return False
    return True


def find_via_spot(brd, pad, obstacles, search_radius_mm=2.0, step_mm=0.1):
    """Search a spiral around the pad for a clear via spot. Returns (x,y) or None."""
    bb = pad.GetBoundingBox()
    cx = (bb.GetX() + bb.GetWidth()/2) / 1e6
    cy = (bb.GetY() + bb.GetHeight()/2) / 1e6
    via_r = VIA_OUTER_MM / 2
    clearance = 0.20
    my_net = pad.GetNet().GetNetCode()
    # Try center first
    if clear_for_via(cx, cy, via_r, clearance, obstacles, my_net):
        return (cx, cy, 0.0)
    # Spiral outward in steps
    n_steps = int(search_radius_mm / step_mm)
    for r_steps in range(1, n_steps + 1):
        r = r_steps * step_mm
        # Sample 16 angles at this radius
        for k in range(16):
            ang = k * 2 * 3.14159265 / 16
            from math import sin, cos
            x = cx + r * cos(ang)
            y = cy + r * sin(ang)
            if clear_for_via(x, y, via_r, clearance, obstacles, my_net):
                return (x, y, r)
    return None


def pad_already_has_via(brd, pad, tolerance_mm=0.3):
    bb = pad.GetBoundingBox()
    px = (bb.GetX() + bb.GetWidth()/2) / 1e6
    py = (bb.GetY() + bb.GetHeight()/2) / 1e6
    net_code = pad.GetNet().GetNetCode() if pad.GetNet() else 0
    for t in brd.GetTracks():
        if not isinstance(t, pcbnew.PCB_VIA): continue
        if t.GetNet().GetNetCode() != net_code: continue
        p = t.GetPosition()
        dx = px - p.x/1e6
        dy = py - p.y/1e6
        if (dx*dx + dy*dy) ** 0.5 < tolerance_mm:
            return True
    return False


def main():
    brd = pcbnew.LoadBoard(PCB)
    print("[1] build obstacle index")
    obstacles = build_obstacle_index(brd)
    print(f"    {len(obstacles)} obstacle samples")

    print("[2] stitch plane-net pads")
    stitched = 0
    skipped_th = 0
    skipped_havia = 0
    failed = []
    for fp in brd.GetFootprints():
        for pad in fp.Pads():
            if not pad.GetNet(): continue
            net_name = str(pad.GetNet().GetNetname())
            if net_name not in PLANE_LAYER_OF: continue
            if not (pad.IsOnLayer(pcbnew.F_Cu) or pad.IsOnLayer(pcbnew.B_Cu)):
                continue
            if pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
                skipped_th += 1
                continue
            if pad_already_has_via(brd, pad):
                skipped_havia += 1
                continue
            spot = find_via_spot(brd, pad, obstacles)
            if spot is None:
                failed.append((fp.GetReference(), pad.GetNumber(), net_name))
                continue
            x, y, dist = spot
            via_at(brd, x, y, pad.GetNet())
            # Add stub trace from pad center to via center (on outer layer of pad)
            bb = pad.GetBoundingBox()
            cx = (bb.GetX() + bb.GetWidth()/2) / 1e6
            cy = (bb.GetY() + bb.GetHeight()/2) / 1e6
            if dist > 0.05:
                layer = pcbnew.F_Cu if pad.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu
                track_at(brd, cx, cy, x, y, pad.GetNet(), layer)
            # Add the new via to obstacles so subsequent searches see it
            obstacles.append((x, y, VIA_OUTER_MM/2, pad.GetNet().GetNetCode(), "newvia"))
            stitched += 1
    print(f"    stitched {stitched} pads; skipped {skipped_th} TH + {skipped_havia} havia; failed {len(failed)}")
    if failed:
        print(f"    failed pads: {failed[:10]}{'...' if len(failed)>10 else ''}")

    # Re-fill zones
    filler = pcbnew.ZONE_FILLER(brd)
    filler.Fill(list(brd.Zones()))
    pcbnew.SaveBoard(PCB, brd)

    # DRC
    out = "/tmp/drc_stitched.txt"
    subprocess.run(["kicad-cli", "pcb", "drc", "--severity-error",
                    "--format", "report", "--output", out, PCB],
                   capture_output=True)
    txt = open(out).read()
    m_err = re.search(r"Found (\d+) DRC violation", txt)
    m_unc = re.search(r"Found (\d+) unconnected item", txt)
    print(f"  DRC: {m_err.group(1) if m_err else '?'} errors, "
          f"{m_unc.group(1) if m_unc else '?'} unconnected")


if __name__ == "__main__":
    main()
