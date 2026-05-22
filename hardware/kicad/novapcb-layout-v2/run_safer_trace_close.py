#!/usr/bin/env python3
"""Safer add-only plane-stitch close per master 2026-05-21.

Discipline:
  - ADD-only: never rip existing tracks/vias
  - DRC-verify AFTER each addition; REVERT any addition that
    introduces a new DRC error
  - Targets ONLY plane-net pads (GND, +3V3, +3V3A, +5V) —
    signal-net unconnected pads are NOT touched

Strategy per pad:
  1. GND pad: short trace to nearest F.Cu/B.Cu GND pour edge (same layer)
  2. Non-GND: trace to nearest connected same-net point
  3. Try straight → L-shape → flag

Each attempt:
  - Capture pre-DRC error count
  - Add trace
  - Refill zones
  - Save board
  - Run DRC
  - If errors increased: REVERT (remove the just-added items)
  - If errors stable: keep, move to next pad
"""
import os, sys, math, json, re, subprocess
import pcbnew

PCB = "/home/novatics64/novapcb/hardware/kicad/novapcb-layout-v2/novapcb-layout-v2.kicad_pcb"
PLANE_NETS = {"GND", "+3V3", "+3V3A", "+5V"}
TRACE_W_MM = 0.20
MAX_TRACE_LEN_MM = 5.0
DRC_TMP = "/tmp/drc_safer.txt"


def drc_error_count():
    """Return number of severity-all DRC violations (excluding unconnected)."""
    subprocess.run(["kicad-cli","pcb","drc","--severity-all","--format","report",
                    "--output", DRC_TMP, "--units","mm", PCB], capture_output=True)
    txt = open(DRC_TMP).read()
    m_total = re.search(r"Found (\d+) DRC violation", txt)
    m_unc = re.search(r"Found (\d+) unconnected", txt)
    n_violations = int(m_total.group(1)) if m_total else 0
    n_unconnected = int(m_unc.group(1)) if m_unc else 0
    return n_violations, n_unconnected


def add_track_seg(brd, x1, y1, x2, y2, net, layer, width=TRACE_W_MM):
    t = pcbnew.PCB_TRACK(brd)
    t.SetStart(pcbnew.VECTOR2I(int(x1*1e6), int(y1*1e6)))
    t.SetEnd(pcbnew.VECTOR2I(int(x2*1e6), int(y2*1e6)))
    t.SetWidth(int(width*1e6))
    t.SetLayer(layer)
    t.SetNet(net)
    brd.Add(t)
    return t


def find_pour_edge_point(brd, layer, pcx, pcy, max_r=5.0):
    """For GND pad: find nearest point on the GND pour outline."""
    for z in brd.Zones():
        if z.GetNetname() != "GND": continue
        if z.GetFirstLayer() != layer: continue
        poly = z.GetFilledPolysList(layer)
        closest = None; closest_d = max_r + 1
        for i in range(poly.OutlineCount()):
            ol = poly.Outline(i)
            for j in range(ol.PointCount()):
                p = ol.CPoint(j)
                x, y = p.x/1e6, p.y/1e6
                d = math.hypot(x - pcx, y - pcy)
                if d < closest_d:
                    closest_d = d; closest = (x, y)
        if closest: return closest
    return None


def find_same_net_targets(brd, net_code, layer):
    """Return list of (x, y, d_to_pad_fn, kind) — same-net items on same layer."""
    out = []
    for fp in brd.GetFootprints():
        for pad in fp.Pads():
            if not pad.GetNet() or pad.GetNet().GetNetCode() != net_code: continue
            if not pad.IsOnLayer(layer): continue
            bb = pad.GetBoundingBox()
            cx = (bb.GetX()+bb.GetWidth()//2)/1e6
            cy = (bb.GetY()+bb.GetHeight()//2)/1e6
            out.append((cx, cy, "pad"))
    for t in brd.GetTracks():
        if not t.GetNet() or t.GetNet().GetNetCode() != net_code: continue
        if isinstance(t, pcbnew.PCB_VIA):
            p = t.GetPosition()
            out.append((p.x/1e6, p.y/1e6, "via"))
        else:
            if t.GetLayer() != layer: continue
            for ep in (t.GetStart(), t.GetEnd()):
                out.append((ep.x/1e6, ep.y/1e6, "trk_end"))
    return out


def main():
    print("=== Safer add-only plane-stitch close ===\n")
    print("[1] establish baseline DRC")
    base_err, base_unc = drc_error_count()
    print(f"    baseline: {base_err} errors, {base_unc} unconnected\n")

    brd = pcbnew.LoadBoard(PCB)

    # Collect unconnected plane pads
    txt = open(DRC_TMP).read()
    pad_set = set()
    for m in re.finditer(r'Pad (\S+) \[([^\]]+)\] of (\S+) on', txt):
        if m.group(2) in PLANE_NETS:
            pad_set.add((m.group(3), m.group(1), m.group(2)))
    print(f"[2] {len(pad_set)} plane-net pads unconnected to address\n")

    closed = []
    flagged = []
    cur_err = base_err

    for ref, pad_num, net_name in sorted(pad_set):
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
        if not pad_obj:
            flagged.append((ref, pad_num, net_name, "no pad object"))
            continue

        # Build candidate target points
        candidates = []
        if net_name == "GND":
            edge = find_pour_edge_point(brd, pad_layer, pcx, pcy, max_r=MAX_TRACE_LEN_MM)
            if edge:
                candidates.append((*edge, "pour_edge", math.hypot(edge[0]-pcx, edge[1]-pcy)))
        targets = find_same_net_targets(brd, pad_obj.GetNet().GetNetCode(), pad_layer)
        for tx, ty, kind in targets:
            d = math.hypot(tx-pcx, ty-pcy)
            if d < 0.1: continue
            if d > MAX_TRACE_LEN_MM: continue
            candidates.append((tx, ty, kind, d))
        candidates.sort(key=lambda c: c[3])

        if not candidates:
            flagged.append((ref, pad_num, net_name, "no candidates within 5mm"))
            continue

        # Try each candidate (straight first, then L-shape) — DRC-verify per attempt
        success = None
        for tx, ty, kind, d in candidates[:8]:  # try top 8 candidates
            # Strategy A: straight trace
            added = []
            t1 = add_track_seg(brd, pcx, pcy, tx, ty, pad_obj.GetNet(), pad_layer)
            added.append(t1)
            pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
            pcbnew.SaveBoard(PCB, brd)
            new_err, new_unc = drc_error_count()
            if new_err <= cur_err and new_unc <= base_unc:
                # accepted!
                cur_err = new_err
                base_unc = new_unc
                success = (kind, d, "straight")
                break
            # revert
            for tr in added: brd.Remove(tr)
            pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
            pcbnew.SaveBoard(PCB, brd)

            # Strategy B: L-shape via (pcx, ty)
            t1 = add_track_seg(brd, pcx, pcy, pcx, ty, pad_obj.GetNet(), pad_layer)
            t2 = add_track_seg(brd, pcx, ty, tx, ty, pad_obj.GetNet(), pad_layer)
            added = [t1, t2]
            pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
            pcbnew.SaveBoard(PCB, brd)
            new_err, new_unc = drc_error_count()
            if new_err <= cur_err and new_unc <= base_unc:
                cur_err = new_err
                base_unc = new_unc
                success = (kind, d, "L1")
                break
            for tr in added: brd.Remove(tr)
            pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
            pcbnew.SaveBoard(PCB, brd)

            # Strategy C: L-shape via (tx, pcy)
            t1 = add_track_seg(brd, pcx, pcy, tx, pcy, pad_obj.GetNet(), pad_layer)
            t2 = add_track_seg(brd, tx, pcy, tx, ty, pad_obj.GetNet(), pad_layer)
            added = [t1, t2]
            pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
            pcbnew.SaveBoard(PCB, brd)
            new_err, new_unc = drc_error_count()
            if new_err <= cur_err and new_unc <= base_unc:
                cur_err = new_err
                base_unc = new_unc
                success = (kind, d, "L2")
                break
            for tr in added: brd.Remove(tr)
            pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
            pcbnew.SaveBoard(PCB, brd)

        if success:
            print(f"  ✓ {ref}.{pad_num} ({net_name}): {success}", flush=True)
            closed.append((ref, pad_num, net_name, success))
        else:
            print(f"  ✗ {ref}.{pad_num} ({net_name}): all candidates produced new errors", flush=True)
            flagged.append((ref, pad_num, net_name, "all attempts caused new errors"))

    print(f"\n[final]")
    print(f"  closed: {len(closed)}")
    print(f"  flagged: {len(flagged)}")
    final_err, final_unc = drc_error_count()
    print(f"  final DRC: {final_err} errors, {final_unc} unconnected")
    json.dump({
        "closed": [{"ref": c[0], "pad": c[1], "net": c[2], "method": str(c[3])} for c in closed],
        "flagged": [{"ref": f[0], "pad": f[1], "net": f[2], "reason": f[3]} for f in flagged],
        "final_drc_err": final_err, "final_drc_unc": final_unc,
    }, open("safer_close_result.json","w"), indent=2)


if __name__ == "__main__":
    main()
