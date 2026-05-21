#!/usr/bin/env python3
"""Process B: load board, find USB vias, add GND stitches near each."""
import pcbnew, math, re, subprocess, os
HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-layout-v2.kicad_pcb")
brd = pcbnew.LoadBoard(PCB)
usb_vias = []
for t in brd.GetTracks():
    if not isinstance(t, pcbnew.PCB_VIA): continue
    if not t.GetNet(): continue
    nn = str(t.GetNet().GetNetname())
    if nn not in ("USB_DM", "USB_DP"): continue
    p = t.GetPosition()
    usb_vias.append((nn, p.x/1e6, p.y/1e6))
print(f"USB vias: {usb_vias}", flush=True)
nets = brd.GetNetsByName().asdict()
n_gnd = None
for k, v in nets.items():
    if str(k) == "GND": n_gnd = v; break
added = 0
for nn, vx, vy in usb_vias:
    # Try multiple offset positions (1.2mm priority)
    for dx, dy in [(-1.2, 0.0), (+1.2, 0.0), (0.0, -1.2), (0.0, +1.2),
                   (-1.0, -0.8), (+1.0, +0.8), (-1.0, +0.8), (+1.0, -0.8)]:
        gx, gy = vx + dx, vy + dy
        skip = False
        for t in brd.GetTracks():
            if isinstance(t, pcbnew.PCB_VIA):
                p = t.GetPosition()
                if math.hypot(gx - p.x/1e6, gy - p.y/1e6) < 0.95:
                    skip = True; break
            else:
                s, e = t.GetStart(), t.GetEnd()
                sx, sy = s.x/1e6, s.y/1e6
                ex, ey = e.x/1e6, e.y/1e6
                dx2, dy2 = ex - sx, ey - sy
                seglen2 = dx2*dx2 + dy2*dy2
                if seglen2 < 1e-9:
                    cd = math.hypot(gx-sx, gy-sy)
                else:
                    tt = max(0, min(1, ((gx-sx)*dx2 + (gy-sy)*dy2) / seglen2))
                    cd = math.hypot(gx - (sx+tt*dx2), gy - (sy+tt*dy2))
                if cd < 0.55:
                    skip = True; break
        if skip: continue
        break  # found a clear spot
    else:
        continue  # no clear spot found
        v = pcbnew.PCB_VIA(brd)
        v.SetPosition(pcbnew.VECTOR2I(int(gx * 1e6), int(gy * 1e6)))
        v.SetWidth(int(0.60 * 1e6))
        v.SetDrill(int(0.30 * 1e6))
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetNet(n_gnd)
        brd.Add(v)
        added += 1
print(f"added {added} GND stitch vias", flush=True)
pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
pcbnew.SaveBoard(PCB, brd)
subprocess.run(["kicad-cli", "pcb", "drc", "--severity-error", "--format", "report",
                "--output", "/tmp/drc_usb_stitch.txt", PCB], capture_output=True)
txt = open("/tmp/drc_usb_stitch.txt").read()
ne = re.search(r"Found (\d+) DRC violation", txt)
nu = re.search(r"Found (\d+) unconnected", txt)
print(f"DRC: {ne.group(1) if ne else '?'} errors, {nu.group(1) if nu else '?'} unconnected", flush=True)
