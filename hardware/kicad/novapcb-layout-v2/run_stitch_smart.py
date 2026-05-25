#!/usr/bin/env python3
"""Step 6 precursor — refined plane stitcher per master 2026-05-21.

Method:
  - Smallest JLCPCB-6L through via: 0.40mm pad / 0.20mm drill (their
    advanced/PRO tier on 6-layer JLC06161H; standard is 0.45/0.30 but
    PRO is fine for fab and gives a much smaller annular ring footprint).
  - Place via AT pad center (zero offset, zero stub — best PDN).
  - If via at pad conflicts with an adjacent signal trace (DRC clearance
    violation): LOCAL RIP-AND-REROUTE the conflicting segment around the
    via. Keep the via AT the pad — only the signal is nudged locally.
  - Any genuine residual after that -> fine-grid enumeration or vision
    pass (proven from Step 5).
"""
import os, sys, re, subprocess, math
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-layout-v2.kicad_pcb")

PLANE_NETS = {"GND", "+3V3", "+3V3A", "+5V"}
# Project min via 0.40 / min drill 0.30 (per novapcb-layout-v2.kicad_pro
# board.design_settings.rules). JLC advanced/PRO supports this (5mil
# annular ring). Smallest project-compatible via.
VIA_OUTER_MM = 0.40
VIA_DRILL_MM = 0.30
CLEARANCE_MM = 0.20  # netclass default


def make_via(brd, x_nm, y_nm, net):
    via = pcbnew.PCB_VIA(brd)
    via.SetPosition(pcbnew.VECTOR2I(int(x_nm), int(y_nm)))
    via.SetWidth(int(VIA_OUTER_MM * 1e6))
    via.SetDrill(int(VIA_DRILL_MM * 1e6))
    via.SetViaType(pcbnew.VIATYPE_THROUGH)
    via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    via.SetNet(net)
    brd.Add(via)
    return via


def via_conflicts(brd, via_x_mm, via_y_mm, my_net_code):
    """Return list of tracks/vias that would conflict with via at (x,y)."""
    r = VIA_OUTER_MM / 2 + CLEARANCE_MM
    conflicts = []
    for t in brd.GetTracks():
        if t.GetNet() and t.GetNet().GetNetCode() == my_net_code:
            continue  # same net is fine
        if isinstance(t, pcbnew.PCB_VIA):
            p = t.GetPosition()
            d = math.hypot(via_x_mm - p.x/1e6, via_y_mm - p.y/1e6)
            other_r = t.GetWidth()/2/1e6
            if d < r + other_r:
                conflicts.append(t)
        else:
            s, e = t.GetStart(), t.GetEnd()
            sx, sy = s.x/1e6, s.y/1e6
            ex, ey = e.x/1e6, e.y/1e6
            # Closest distance from (via_x, via_y) to segment
            dx, dy = ex - sx, ey - sy
            seglen2 = dx*dx + dy*dy
            if seglen2 < 1e-9:
                cd = math.hypot(via_x_mm - sx, via_y_mm - sy)
            else:
                tt = max(0, min(1, ((via_x_mm-sx)*dx + (via_y_mm-sy)*dy) / seglen2))
                cx, cy = sx + tt*dx, sy + tt*dy
                cd = math.hypot(via_x_mm - cx, via_y_mm - cy)
            tw = t.GetWidth()/2/1e6
            if cd < r + tw:
                conflicts.append(t)
    return conflicts


def find_offset_spot(brd, pad_x, pad_y, my_net_code, max_r_mm=2.0, step=0.05):
    """Fine-grid spiral search for a clear via spot near (pad_x, pad_y)."""
    n = int(max_r_mm / step)
    for r_steps in range(0, n+1):
        r = r_steps * step
        n_ang = max(8, int(r * 8))
        for k in range(n_ang):
            ang = k * 2*math.pi / n_ang
            x = pad_x + r*math.cos(ang)
            y = pad_y + r*math.sin(ang)
            if not via_conflicts(brd, x, y, my_net_code):
                return x, y, r
    return None


def drc_summary():
    out = "/tmp/drc_smart.txt"
    subprocess.run(["kicad-cli", "pcb", "drc", "--severity-error",
                    "--format", "report", "--output", out, PCB], capture_output=True)
    txt = open(out).read()
    n_err = int(re.search(r"Found (\d+) DRC violation", txt).group(1)) if re.search(r"Found \d+ DRC violation", txt) else None
    n_unc = int(re.search(r"Found (\d+) unconnected", txt).group(1)) if re.search(r"Found \d+ unconnected", txt) else None
    return n_err, n_unc


def main():
    print("[1] load board (signal routed, no plane stitches yet)", flush=True)
    brd = pcbnew.LoadBoard(PCB)
    print(f"    tracks={sum(1 for t in brd.GetTracks() if not isinstance(t, pcbnew.PCB_VIA))} "
          f"vias={sum(1 for t in brd.GetTracks() if isinstance(t, pcbnew.PCB_VIA))}")

    print("[2] place small via (0.40/0.30) at each plane-pad center", flush=True)
    at_pad = 0
    needs_ripreroute = []  # pads where at-pad conflicts — caller handles separately
    for fp in brd.GetFootprints():
        for pad in fp.Pads():
            if not pad.GetNet(): continue
            net_name = str(pad.GetNet().GetNetname())
            if net_name not in PLANE_NETS: continue
            if not (pad.IsOnLayer(pcbnew.F_Cu) or pad.IsOnLayer(pcbnew.B_Cu)): continue
            if pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH: continue
            bb = pad.GetBoundingBox()
            cx = (bb.GetX() + bb.GetWidth() // 2) / 1e6
            cy = (bb.GetY() + bb.GetHeight() // 2) / 1e6
            net = pad.GetNet()
            net_code = net.GetNetCode()
            # At-pad placement only; if conflict, flag for rip-and-reroute
            conflicts = via_conflicts(brd, cx, cy, net_code)
            if not conflicts:
                make_via(brd, cx * 1e6, cy * 1e6, net)
                at_pad += 1
                if at_pad % 30 == 0:
                    print(f"    ... {at_pad} at-pad", flush=True)
                continue
            # Flag for rip-and-reroute
            cf_summary = []
            for c in conflicts:
                if isinstance(c, pcbnew.PCB_VIA):
                    cf_summary.append(f"via@{c.GetPosition().x/1e6:.2f},{c.GetPosition().y/1e6:.2f}")
                else:
                    nn = str(c.GetNet().GetNetname()) if c.GetNet() else ""
                    cf_summary.append(f"trk({nn})@layer{c.GetLayer()}")
            needs_ripreroute.append({
                "fp": fp.GetReference(), "pad": pad.GetNumber(), "net": net_name,
                "pos": (cx, cy), "conflicts": cf_summary,
            })

    print(f"    at-pad placements: {at_pad}", flush=True)
    print(f"    needs-rip-reroute: {len(needs_ripreroute)} pads", flush=True)
    for nr in needs_ripreroute[:15]:
        print(f"      {nr['fp']}.{nr['pad']} ({nr['net']}) at "
              f"({nr['pos'][0]:.2f},{nr['pos'][1]:.2f}) "
              f"conflicts={nr['conflicts'][:3]}")

    print("[3] refill zones + save", flush=True)
    pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
    pcbnew.SaveBoard(PCB, brd)

    print("[4] DRC", flush=True)
    n_err, n_unc = drc_summary()
    print(f"    DRC: {n_err} errors, {n_unc} unconnected")


if __name__ == "__main__":
    main()
