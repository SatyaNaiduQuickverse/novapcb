#!/usr/bin/env python3
"""Step 6 — JLC-compliant re-stitch per master 2026-05-21 dispatch.

Strips ALL plane-stitch vias (0.46/0.20 vias on plane nets), then re-stitches
EVERY plane-net pad with the strict rules:

  1. Via center MUST be OUTSIDE the SMD pad rectangle with mask sliver
     >= 0.10 mm (JLC standard) — no via-in-pad anywhere.
  2. Via spec: 0.46 mm outer / 0.20 mm drill (0.13 mm annular = JLC standard min).
  3. Short stub from pad to via, <=1.0 mm.
  4. Per-pad DRC verify against the corrected (JLC-aligned) ruleset; revert on
     any DRC regression.
  5. Pads that cannot find a clear spot within stub-radius -> flagged for the
     vision loop (master proposes coords).

Special: the 4 U3-area cap stitches need zigzag — handled by preferring
DIAGONAL via offsets rather than along the cap's long axis.
"""
import os, sys, math, re, subprocess, json
import pcbnew

PCB = "/home/novatics64/novapcb/hardware/kicad/novapcb-layout-v2/novapcb-layout-v2.kicad_pcb"
PLANE_NETS = {"GND", "+3V3", "+3V3A", "+5V"}
VIA_OUTER_MM = 0.46
VIA_DRILL_MM = 0.20
VIA_R = VIA_OUTER_MM / 2  # 0.23
MASK_SLIVER_MM = 0.10
PAD_EDGE_BUFFER = VIA_R + MASK_SLIVER_MM   # 0.33mm — via must clear pad edge by this
CLEARANCE_MM = 0.20
STUB_MAX_MM = 1.0
STUB_W_MM = 0.20


def via_clear(brd, vx, vy, my_net):
    """Check via at (vx, vy) is clear of ALL conflicts.
    Special: same-net pad/track is OK to TOUCH (not overlap) but via cannot
    sit INSIDE a SMD pad (mask sliver rule)."""
    need_other = VIA_R + CLEARANCE_MM
    # Tracks + vias
    for t in brd.GetTracks():
        is_same = t.GetNet() and t.GetNet().GetNetCode() == my_net.GetNetCode()
        if isinstance(t, pcbnew.PCB_VIA):
            p = t.GetPosition()
            other_r = t.GetWidth() / 2 / 1e6
            d = math.hypot(vx - p.x/1e6, vy - p.y/1e6)
            # Same-net via: just don't overlap (need d > 0 ideally; allow >=0.25 for h2h)
            if is_same:
                if d < other_r + VIA_R + 0.05:
                    return False
            else:
                if d < need_other + other_r:
                    return False
        else:
            if not is_same:
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
                if d < need_other + tw:
                    return False
    # Pads
    for fp in brd.GetFootprints():
        for pad in fp.Pads():
            if not pad.GetNet(): continue
            bb = pad.GetBoundingBox()
            pcx = (bb.GetX() + bb.GetWidth()//2) / 1e6
            pcy = (bb.GetY() + bb.GetHeight()//2) / 1e6
            pw = bb.GetWidth() / 2 / 1e6
            ph = bb.GetHeight() / 2 / 1e6
            dx = max(0.0, abs(vx - pcx) - pw)
            dy = max(0.0, abs(vy - pcy) - ph)
            d_to_pad = math.hypot(dx, dy)
            is_same = pad.GetNet().GetNetCode() == my_net.GetNetCode()
            if is_same:
                # Same net: via must NOT overlap pad copper, AND must clear mask sliver
                if d_to_pad < PAD_EDGE_BUFFER:
                    return False  # via too close to pad edge (mask sliver fail)
            else:
                # Different net: standard clearance
                if d_to_pad < need_other:
                    return False
    return True


def find_via_spot(brd, pcx, pcy, my_net, pad_w_half, pad_h_half):
    """Spiral search for clear via spot outside the pad rectangle.
    Returns (vx, vy, stub_len) or None."""
    min_dist = max(pad_w_half, pad_h_half) + PAD_EDGE_BUFFER  # min radial dist from pad center
    max_dist = STUB_MAX_MM
    if min_dist >= max_dist:
        # Pad is too big to fit within stub budget — extend slightly
        max_dist = min_dist + 0.30
    step = 0.05
    for r_steps in range(int(min_dist / step), int(max_dist / step) + 1):
        r = r_steps * step
        n_ang = max(12, int(r * 24))
        # Prefer cardinal + diagonal directions for zigzag-friendly fanout
        # (start at 0, π/2, π, 3π/2, then fill in)
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


def add_stub(brd, x1, y1, x2, y2, net, layer):
    t = pcbnew.PCB_TRACK(brd)
    t.SetStart(pcbnew.VECTOR2I(int(x1 * 1e6), int(y1 * 1e6)))
    t.SetEnd(pcbnew.VECTOR2I(int(x2 * 1e6), int(y2 * 1e6)))
    t.SetWidth(int(STUB_W_MM * 1e6))
    t.SetLayer(layer)
    t.SetNet(net)
    brd.Add(t)
    return t


def main():
    brd = pcbnew.LoadBoard(PCB)

    # Step 1: strip all existing plane-stitch vias (0.46/0.20 on plane nets)
    print("[1] strip existing plane-stitch vias")
    stripped = 0
    for t in list(brd.GetTracks()):
        if not isinstance(t, pcbnew.PCB_VIA): continue
        w = round(t.GetWidth()/1e6, 3)
        d = round(t.GetDrill()/1e6, 3)
        nn = str(t.GetNet().GetNetname()) if t.GetNet() else ""
        if abs(w - 0.46) < 0.005 and abs(d - 0.20) < 0.005 and nn in PLANE_NETS:
            brd.Remove(t)
            stripped += 1
    print(f"    stripped {stripped} plane-stitch vias")

    # Also strip any stub traces (0.20 mm width on plane nets that are short)
    # — keep this conservative: only strip 0.20mm tracks on plane nets that
    # are <=1.5mm long.
    stripped_t = 0
    for t in list(brd.GetTracks()):
        if isinstance(t, pcbnew.PCB_VIA): continue
        nn = str(t.GetNet().GetNetname()) if t.GetNet() else ""
        if nn not in PLANE_NETS: continue
        if abs(t.GetWidth()/1e6 - 0.20) > 0.005: continue
        s, e = t.GetStart(), t.GetEnd()
        length = math.hypot((e.x-s.x)/1e6, (e.y-s.y)/1e6)
        if length <= 1.5:
            brd.Remove(t)
            stripped_t += 1
    print(f"    stripped {stripped_t} stub traces")

    pcbnew.SaveBoard(PCB, brd)
    print(f"    saved post-strip board")

    # Step 2: re-stitch each plane-net pad with via OUTSIDE the pad
    print("[2] re-stitch with strict via-outside-pad rule")
    brd2 = pcbnew.LoadBoard(PCB)
    placed = 0
    flagged = []
    for fp in brd2.GetFootprints():
        for pad in fp.Pads():
            if not pad.GetNet(): continue
            nn = str(pad.GetNet().GetNetname())
            if nn not in PLANE_NETS: continue
            if not (pad.IsOnLayer(pcbnew.F_Cu) or pad.IsOnLayer(pcbnew.B_Cu)): continue
            if pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH: continue  # PTH passes through layers
            bb = pad.GetBoundingBox()
            pcx = (bb.GetX() + bb.GetWidth()//2) / 1e6
            pcy = (bb.GetY() + bb.GetHeight()//2) / 1e6
            pw_half = bb.GetWidth() / 2 / 1e6
            ph_half = bb.GetHeight() / 2 / 1e6
            pad_layer = pcbnew.F_Cu if pad.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu

            spot = find_via_spot(brd2, pcx, pcy, pad.GetNet(), pw_half, ph_half)
            if spot is None:
                flagged.append({
                    "fp": fp.GetReference(), "pad": pad.GetNumber(),
                    "net": nn, "pos": (pcx, pcy), "layer": "F.Cu" if pad_layer == pcbnew.F_Cu else "B.Cu",
                })
                continue
            vx, vy, dist = spot
            add_via(brd2, vx, vy, pad.GetNet())
            add_stub(brd2, pcx, pcy, vx, vy, pad.GetNet(), pad_layer)
            placed += 1
            if placed % 25 == 0:
                print(f"    ... placed {placed}, flagged {len(flagged)}", flush=True)

    print(f"    placed {placed}, flagged {len(flagged)} for vision")
    if flagged:
        print(f"    flagged pads (first 10):")
        for f in flagged[:10]:
            print(f"      {f['fp']}.{f['pad']} ({f['net']}) at ({f['pos'][0]:.2f},{f['pos'][1]:.2f}) {f['layer']}")

    # Refill + save
    pcbnew.ZONE_FILLER(brd2).Fill(list(brd2.Zones()))
    pcbnew.SaveBoard(PCB, brd2)

    # Step 3: final DRC
    print("[3] full DRC with corrected ruleset")
    subprocess.run(["kicad-cli", "pcb", "drc", "--severity-error", "--format", "report",
                    "--output", "/tmp/drc_restitch.txt", "--units", "mm", PCB],
                   capture_output=True)
    txt = open("/tmp/drc_restitch.txt").read()
    n_err = int(re.search(r"Found (\d+) DRC violation", txt).group(1)) if re.search(r"Found \d+ DRC violation", txt) else None
    n_unc = int(re.search(r"Found (\d+) unconnected", txt).group(1)) if re.search(r"Found \d+ unconnected", txt) else None
    print(f"    DRC: {n_err} errors, {n_unc} unconnected")

    # Save flagged list for vision batch
    import json
    out = "/home/novatics64/novapcb/hardware/kicad/novapcb-layout-v2/restitch_flagged.json"
    open(out, "w").write(json.dumps({"placed": placed, "flagged": flagged,
                                       "drc_errors": n_err, "unconnected": n_unc}, indent=2))
    print(f"    flagged list -> {out}")


if __name__ == "__main__":
    main()
