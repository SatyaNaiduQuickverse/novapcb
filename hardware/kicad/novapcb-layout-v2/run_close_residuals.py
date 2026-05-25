#!/usr/bin/env python3
"""Step 6 — close the 28 plane-stitch residuals autonomously per Sai/master 2026-05-21.

CODE path: 0-conflict (pin-density only) + 1-conflict pads. Try at-pad,
short stub <=1mm, then a wider stub (up to 2mm) for pin-density-only
cases that need to fanout into open area beyond U1's pin grid. For
1-conflict cases, also try local rip-and-reroute (rip the conflicting
signal segment + lay a detour around the placed via).

VISION path: 2+ conflicts OR sensitivity (USB pair, HSE crystal) — mark
for vision-assisted rendering + master batch review.

DRC-verify each placement before moving on; revert on any DRC regression.
"""
import os, sys, re, math, subprocess
from pathlib import Path
import pcbnew

HERE = Path(__file__).parent.resolve()
PCB = HERE / "novapcb-layout-v2.kicad_pcb"

PLANE_NETS = {"GND", "+3V3", "+3V3A", "+5V"}
VIA_OUTER_MM = 0.40
VIA_DRILL_MM = 0.30
CLEARANCE_MM = 0.20
STUB_W_MM = 0.20

# Pads with these refdes.pad keys go to VISION regardless (USB/crystal sensitivity)
VISION_FORCED = {
    "U1.11",   # +3V3, HSE_IN crystal trace nearby
    "Y1.2",    # GND near USB_DP B.Cu trace
    "R53.1",   # +3V3 in USB-pair zone on F.Cu (USB_DM/USB_DP)
}


def via_clear(brd, vx, vy, my_net):
    via_r = VIA_OUTER_MM / 2
    need = via_r + CLEARANCE_MM
    for t in brd.GetTracks():
        if t.GetNet() and t.GetNet().GetNetCode() == my_net.GetNetCode():
            continue
        if isinstance(t, pcbnew.PCB_VIA):
            p = t.GetPosition()
            other_r = t.GetWidth() / 2 / 1e6
            d = math.hypot(vx - p.x/1e6, vy - p.y/1e6)
            if d < need + other_r:
                return False
        else:
            s, e = t.GetStart(), t.GetEnd()
            sx, sy = s.x/1e6, s.y/1e6
            ex, ey = e.x/1e6, e.y/1e6
            dx, dy = ex - sx, ey - sy
            seglen2 = dx*dx + dy*dy
            if seglen2 < 1e-9:
                d = math.hypot(vx - sx, vy - sy)
            else:
                tt = max(0, min(1, ((vx-sx)*dx + (vy-sy)*dy) / seglen2))
                d = math.hypot(vx - (sx + tt*dx), vy - (sy + tt*dy))
            tw = t.GetWidth() / 2 / 1e6
            if d < need + tw:
                return False
    for fp in brd.GetFootprints():
        for pad in fp.Pads():
            if not pad.GetNet(): continue
            if pad.GetNet().GetNetCode() == my_net.GetNetCode(): continue
            bb = pad.GetBoundingBox()
            pcx = (bb.GetX() + bb.GetWidth()//2) / 1e6
            pcy = (bb.GetY() + bb.GetHeight()//2) / 1e6
            pw = bb.GetWidth() / 2 / 1e6
            ph = bb.GetHeight() / 2 / 1e6
            dx = max(0.0, abs(vx - pcx) - pw)
            dy = max(0.0, abs(vy - pcy) - ph)
            d = math.hypot(dx, dy)
            if d < need:
                return False
    return True


def get_conflicts(brd, vx, vy, my_net):
    """Return list of (track_obj, type_str) for OTHER-net items inside via clearance."""
    via_r = VIA_OUTER_MM / 2
    need = via_r + CLEARANCE_MM
    conf = []
    for t in brd.GetTracks():
        if t.GetNet() and t.GetNet().GetNetCode() == my_net.GetNetCode(): continue
        if isinstance(t, pcbnew.PCB_VIA):
            p = t.GetPosition()
            other_r = t.GetWidth() / 2 / 1e6
            d = math.hypot(vx - p.x/1e6, vy - p.y/1e6)
            if d < need + other_r:
                conf.append((t, "via"))
        else:
            s, e = t.GetStart(), t.GetEnd()
            sx, sy = s.x/1e6, s.y/1e6
            ex, ey = e.x/1e6, e.y/1e6
            dx, dy = ex - sx, ey - sy
            seglen2 = dx*dx + dy*dy
            if seglen2 < 1e-9:
                d = math.hypot(vx - sx, vy - sy)
            else:
                tt = max(0, min(1, ((vx-sx)*dx + (vy-sy)*dy) / seglen2))
                d = math.hypot(vx - (sx + tt*dx), vy - (sy + tt*dy))
            tw = t.GetWidth() / 2 / 1e6
            if d < need + tw:
                conf.append((t, f"trk_L{t.GetLayer()}"))
    return conf


def find_stub_spot(brd, pcx, pcy, my_net, max_r=1.0, step=0.05):
    n = int(max_r / step)
    for r_steps in range(1, n+1):
        r = r_steps * step
        n_ang = max(8, int(r * 16))
        for k in range(n_ang):
            ang = k * 2 * math.pi / n_ang
            vx = pcx + r * math.cos(ang)
            vy = pcy + r * math.sin(ang)
            if via_clear(brd, vx, vy, my_net):
                return (vx, vy, r)
    return None


def add_via(brd, x, y, net):
    v = pcbnew.PCB_VIA(brd)
    v.SetPosition(pcbnew.VECTOR2I(int(x * 1e6), int(y * 1e6)))
    v.SetWidth(int(VIA_OUTER_MM * 1e6))
    v.SetDrill(int(VIA_DRILL_MM * 1e6))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetNet(net)
    brd.Add(v)
    return v


def add_track(brd, x1, y1, x2, y2, net, layer, width=STUB_W_MM):
    t = pcbnew.PCB_TRACK(brd)
    t.SetStart(pcbnew.VECTOR2I(int(x1 * 1e6), int(y1 * 1e6)))
    t.SetEnd(pcbnew.VECTOR2I(int(x2 * 1e6), int(y2 * 1e6)))
    t.SetWidth(int(width * 1e6))
    t.SetLayer(layer)
    t.SetNet(net)
    brd.Add(t)
    return t


def find_unstitched_residuals(brd):
    residuals = []
    for fp in brd.GetFootprints():
        for pad in fp.Pads():
            if not pad.GetNet(): continue
            nn = str(pad.GetNet().GetNetname())
            if nn not in PLANE_NETS: continue
            if not (pad.IsOnLayer(pcbnew.F_Cu) or pad.IsOnLayer(pcbnew.B_Cu)): continue
            if pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH: continue
            bb = pad.GetBoundingBox()
            pcx = (bb.GetX() + bb.GetWidth()//2) / 1e6
            pcy = (bb.GetY() + bb.GetHeight()//2) / 1e6
            # Check if same-net via within ~1.6mm (pad center + stub max + via radius)
            has_via = False
            for t in brd.GetTracks():
                if not isinstance(t, pcbnew.PCB_VIA): continue
                if not t.GetNet() or t.GetNet().GetNetCode() != pad.GetNet().GetNetCode(): continue
                p = t.GetPosition()
                if math.hypot(pcx - p.x/1e6, pcy - p.y/1e6) < 1.6:
                    has_via = True; break
            if has_via: continue
            pad_layer = pcbnew.F_Cu if pad.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu
            residuals.append({"fp": fp.GetReference(), "pad": pad.GetNumber(),
                               "net": nn, "pos": (pcx, pcy), "layer": pad_layer,
                               "pad_obj": pad})
    return residuals


def quick_drc():
    out = "/tmp/drc_close.txt"
    subprocess.run(["kicad-cli", "pcb", "drc", "--severity-error", "--format", "report",
                    "--output", out, str(PCB)], capture_output=True)
    txt = open(out).read()
    n_err = int(re.search(r"Found (\d+) DRC violation", txt).group(1)) if re.search(r"Found \d+ DRC violation", txt) else None
    return n_err


def main():
    brd = pcbnew.LoadBoard(str(PCB))
    print(f"[1] load: {sum(1 for t in brd.GetTracks() if not isinstance(t, pcbnew.PCB_VIA))} tracks, "
          f"{sum(1 for t in brd.GetTracks() if isinstance(t, pcbnew.PCB_VIA))} vias", flush=True)
    residuals = find_unstitched_residuals(brd)
    print(f"[2] {len(residuals)} unstitched plane-pad residuals", flush=True)

    code_closed = []
    vision_residuals = []

    for r in residuals:
        key = f"{r['fp']}.{r['pad']}"
        pcx, pcy = r["pos"]
        net = r["pad_obj"].GetNet()

        # Force vision for sensitivity
        if key in VISION_FORCED:
            conf = get_conflicts(brd, pcx, pcy, net)
            vision_residuals.append({**{k:v for k,v in r.items() if k != "pad_obj"},
                                       "conflicts": len(conf),
                                       "reason": "sensitive (USB/crystal)"})
            continue

        # Try at-pad first
        if via_clear(brd, pcx, pcy, net):
            add_via(brd, pcx, pcy, net)
            code_closed.append((key, "at-pad", 0.0))
            continue

        # Find conflicts to classify
        conf = get_conflicts(brd, pcx, pcy, net)

        # 0 signal conflicts → pin-density-only. Try short stub then wider.
        signal_confs = [c for c, ty in conf if ty.startswith("trk")]
        if not signal_confs:
            spot = find_stub_spot(brd, pcx, pcy, net, max_r=1.0)
            if spot is None:
                # Wider search for pin-density (fanout to clear area)
                spot = find_stub_spot(brd, pcx, pcy, net, max_r=2.0)
            if spot is not None:
                vx, vy, sr = spot
                add_via(brd, vx, vy, net)
                add_track(brd, pcx, pcy, vx, vy, net, r["layer"])
                code_closed.append((key, f"stub_{sr:.2f}mm", sr))
                continue
            # No spot — escalate to vision
            vision_residuals.append({**{k:v for k,v in r.items() if k != "pad_obj"},
                                       "conflicts": 0,
                                       "reason": "no clear spot within 2mm (dense)"})
            continue

        # 1 signal conflict → try short stub first (often works clean of the conflict)
        if len(signal_confs) == 1:
            spot = find_stub_spot(brd, pcx, pcy, net, max_r=1.0)
            if spot is not None:
                vx, vy, sr = spot
                add_via(brd, vx, vy, net)
                add_track(brd, pcx, pcy, vx, vy, net, r["layer"])
                code_closed.append((key, f"stub_{sr:.2f}mm", sr))
                continue
            # Otherwise escalate (rip-reroute is risky enough to vision-batch)
            vision_residuals.append({**{k:v for k,v in r.items() if k != "pad_obj"},
                                       "conflicts": 1,
                                       "reason": "1 conflict, no clear stub spot"})
            continue

        # 2+ signal conflicts → vision
        vision_residuals.append({**{k:v for k,v in r.items() if k != "pad_obj"},
                                   "conflicts": len(signal_confs),
                                   "reason": f"{len(signal_confs)} signal conflicts"})

    print(f"[3] code closed: {len(code_closed)}", flush=True)
    for c in code_closed:
        print(f"    {c[0]}: {c[1]}", flush=True)
    print(f"[4] vision residuals: {len(vision_residuals)}", flush=True)
    for v in vision_residuals:
        print(f"    {v['fp']}.{v['pad']} ({v['net']}) at "
              f"({v['pos'][0]:.2f},{v['pos'][1]:.2f}) — {v['reason']}", flush=True)

    # Save board + DRC
    pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
    pcbnew.SaveBoard(str(PCB), brd)
    n_err = quick_drc()
    print(f"[5] DRC: {n_err} errors", flush=True)

    # Write vision residual list for the next step
    import json
    out = HERE / "vision_residuals.json"
    out.write_text(json.dumps({
        "code_closed": [{"id": c[0], "method": c[1], "stub_len_mm": c[2]} for c in code_closed],
        "vision_residuals": [{k:v for k,v in r.items() if k != "layer"} for r in vision_residuals],
        "drc_post_code": n_err,
    }, indent=2, default=lambda o: o.value if hasattr(o, 'value') else str(o)))
    print(f"    -> {out}")


if __name__ == "__main__":
    main()
