#!/usr/bin/env python3
"""Step 6 precursor — R1-amended plane stitcher per master 2026-05-21.

For each plane-net pad on outer layer:
  1. Try via AT pad center (smallest project via 0.40/0.30). If clear,
     place — best PDN (zero stub).
  2. If at-pad conflicts, try SHORT FANOUT STUB (<=1.0 mm). Place via
     at the first clear spot within 1.0 mm, add stub trace from pad to
     via on the pad's outer layer. Standard fine-pitch fanout — NOT a
     compromise (master 2026-05-21 recalibration).
  3. If neither at-pad nor short stub finds room, flag for local
     rip-and-reroute (separate pass) or fine-grid/vision residual.

Pad-level obstacle model uses pad bounding-box + via outer + clearance.
Track-level uses point-to-segment distance with sample-free analytical
computation.
"""
import os, sys, re, subprocess, math
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-layout-v2.kicad_pcb")

PLANE_NETS = {"GND", "+3V3", "+3V3A", "+5V"}
VIA_OUTER_MM = 0.40   # project min
VIA_DRILL_MM = 0.30
CLEARANCE_MM = 0.20

STUB_MAX_MM = 1.0     # short fanout stub limit (master directive)
STUB_STEP_MM = 0.05   # search step
STUB_W_MM = 0.20      # stub trace width


def via_clear(brd, vx, vy, my_net):
    """Check if a via at (vx, vy) clears all OTHER-net obstacles."""
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
    # Check against pads of OTHER nets — use proper rectangle distance
    # (not point-to-center + radius, which overestimates for long thin pads)
    for fp in brd.GetFootprints():
        for pad in fp.Pads():
            if not pad.GetNet(): continue
            if pad.GetNet().GetNetCode() == my_net.GetNetCode(): continue
            bb = pad.GetBoundingBox()
            pcx = (bb.GetX() + bb.GetWidth()//2) / 1e6
            pcy = (bb.GetY() + bb.GetHeight()//2) / 1e6
            pw = bb.GetWidth() / 2 / 1e6
            ph = bb.GetHeight() / 2 / 1e6
            # Distance from (vx, vy) to axis-aligned rect at (pcx, pcy):
            dx = max(0.0, abs(vx - pcx) - pw)
            dy = max(0.0, abs(vy - pcy) - ph)
            d = math.hypot(dx, dy)
            if d < need:  # `need` includes via_r + clearance
                return False
    return True


def find_short_stub(brd, pad_cx, pad_cy, my_net, on_layer):
    """Spiral search up to STUB_MAX_MM for a clear via spot. Returns
    (vx, vy, stub_len) or None."""
    n = int(STUB_MAX_MM / STUB_STEP_MM)
    for r_steps in range(1, n + 1):
        r = r_steps * STUB_STEP_MM
        n_ang = max(8, int(r * 16))  # finer angular density at larger radius
        for k in range(n_ang):
            ang = k * 2 * math.pi / n_ang
            vx = pad_cx + r * math.cos(ang)
            vy = pad_cy + r * math.sin(ang)
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


def add_stub(brd, x1, y1, x2, y2, net, layer):
    t = pcbnew.PCB_TRACK(brd)
    t.SetStart(pcbnew.VECTOR2I(int(x1 * 1e6), int(y1 * 1e6)))
    t.SetEnd(pcbnew.VECTOR2I(int(x2 * 1e6), int(y2 * 1e6)))
    t.SetWidth(int(STUB_W_MM * 1e6))
    t.SetLayer(layer)
    t.SetNet(net)
    brd.Add(t)


def drc_summary():
    out = "/tmp/drc_r1.txt"
    subprocess.run(["kicad-cli", "pcb", "drc", "--severity-error",
                    "--format", "report", "--output", out, PCB], capture_output=True)
    txt = open(out).read()
    n_err = int(re.search(r"Found (\d+) DRC violation", txt).group(1)) if re.search(r"Found \d+ DRC violation", txt) else None
    n_unc = int(re.search(r"Found (\d+) unconnected", txt).group(1)) if re.search(r"Found \d+ unconnected", txt) else None
    return n_err, n_unc


def main():
    brd = pcbnew.LoadBoard(PCB)
    print(f"[1] load: tracks={sum(1 for t in brd.GetTracks() if not isinstance(t, pcbnew.PCB_VIA))} "
          f"vias={sum(1 for t in brd.GetTracks() if isinstance(t, pcbnew.PCB_VIA))}", flush=True)

    print("[2] stitch plane pads (at-pad -> short stub -> rip-reroute flag)", flush=True)
    at_pad = 0
    short_stub = 0
    needs_rip = []
    skipped_th = 0

    for fp in brd.GetFootprints():
        for pad in fp.Pads():
            if not pad.GetNet(): continue
            nn = str(pad.GetNet().GetNetname())
            if nn not in PLANE_NETS: continue
            if not (pad.IsOnLayer(pcbnew.F_Cu) or pad.IsOnLayer(pcbnew.B_Cu)): continue
            if pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
                skipped_th += 1; continue
            bb = pad.GetBoundingBox()
            pcx = (bb.GetX() + bb.GetWidth()//2) / 1e6
            pcy = (bb.GetY() + bb.GetHeight()//2) / 1e6
            pad_layer = pcbnew.F_Cu if pad.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu

            # Try at-pad first
            if via_clear(brd, pcx, pcy, pad.GetNet()):
                add_via(brd, pcx, pcy, pad.GetNet())
                at_pad += 1
                if (at_pad + short_stub) % 30 == 0:
                    print(f"    ... {at_pad} at-pad + {short_stub} stub = {at_pad+short_stub}", flush=True)
                continue

            # Try short fanout stub
            spot = find_short_stub(brd, pcx, pcy, pad.GetNet(), pad_layer)
            if spot is not None:
                vx, vy, stub_len = spot
                add_via(brd, vx, vy, pad.GetNet())
                # Add stub from pad center to via center
                add_stub(brd, pcx, pcy, vx, vy, pad.GetNet(), pad_layer)
                short_stub += 1
                if (at_pad + short_stub) % 30 == 0:
                    print(f"    ... {at_pad} at-pad + {short_stub} stub = {at_pad+short_stub}", flush=True)
                continue

            # Genuine residual
            needs_rip.append({"fp": fp.GetReference(), "pad": pad.GetNumber(),
                              "net": nn, "pos": (pcx, pcy)})

    total = at_pad + short_stub
    print(f"    at-pad: {at_pad}", flush=True)
    print(f"    short-stub: {short_stub}", flush=True)
    print(f"    needs-rip-reroute (residual): {len(needs_rip)}", flush=True)
    if needs_rip:
        for nr in needs_rip[:15]:
            print(f"      {nr['fp']}.{nr['pad']} ({nr['net']}) "
                  f"at ({nr['pos'][0]:.2f},{nr['pos'][1]:.2f})")
    print(f"    skipped TH pads: {skipped_th}", flush=True)

    print("[3] refill zones + save", flush=True)
    pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
    pcbnew.SaveBoard(PCB, brd)

    print("[4] DRC", flush=True)
    n_err, n_unc = drc_summary()
    print(f"    DRC: {n_err} errors, {n_unc} unconnected")


if __name__ == "__main__":
    main()
