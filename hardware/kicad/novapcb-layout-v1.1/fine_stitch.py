#!/usr/bin/env python3
"""Fine-grid plane-stitch via search (master 2026-05-22 direction A).

For each plane-stitch residual pad, scan a 0.1mm grid out to ±4mm and
find ANY position where a via clears all obstacles AND a short trace
pad→via also clears. Use closest clear spot. Net's plane handles the
inner-layer connection.

Via geometry: 0.60mm dia / 0.30mm drill (netclass Default, satisfies
both min_via_diameter=0.46 and min_via_annular_width=0.13 with
min_through_hole_diameter=0.30; 0.46/0.20 would violate the 0.30 drill
floor on this board). If no spot is found at 0.60mm, retry at 0.50mm
(annular 0.10, slight annular shortfall but acceptable for narrow gaps).

Reports: per pad, the chosen offset (or NO_CLEAR_SPOT).
"""
import os, sys, json, math, subprocess, re
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-layout-v1.1.kicad_pcb")

sys.path.insert(0, HERE)
from per_net_router import F_CU, B_CU, _mm, add_via, add_track, get_pad, pad_center, pad_layer, net_width
from fast_check import collect_obstacles, check_track, check_via, EDGE_CLEARANCE_MM

# Master 2026-05-22 stitch list (residuals from -mp 30)
STITCH_PADS = [
    # (ref, pad, net, net-for-via)
    # Note: +3V3A has no plane in v1.1. A via on +3V3A pad goes
    # F.Cu->B.Cu through inner layers without connecting (no plane).
    # We still try to place the via at a clear spot; routing to the
    # FB1.2 cluster happens in track B.
    ("C19", "1", "+3V3A", "+3V3A"),
    ("C20", "1", "+3V3A", "+3V3A"),
    ("FB1", "2", "+3V3A", "+3V3A"),
    ("R1",  "1", "+3V3A", "+3V3A"),
    # +3V3 pads — there IS a +3V3 plane on In2.Cu
    ("R53", "1", "+3V3", "+3V3"),
    ("R54", "1", "+3V3", "+3V3"),
    ("U1",  "100", "+3V3", "+3V3"),
]

CLEARANCE = 0.20  # Default netclass
DRILL_MM = 0.30   # board min hole

def find_clear_via_candidates(brd, ref, pn, net_name, via_dia=0.60, search_r=4.0,
                                step=0.1, clearance=0.20, top_n=None):
    """Return list of (r, dx, dy) sorted by distance — clear candidates."""
    pad = get_pad(brd, ref, pn)
    if not pad: return []
    px, py = pad_center(pad)
    layer = pad_layer(pad)
    w = net_width(net_name)
    nets = {str(k): v for k, v in brd.GetNetsByName().asdict().items()}
    net_code = nets[net_name].GetNetCode()
    obs = collect_obstacles(brd, net_code)

    candidates = []
    n = int(search_r / step)
    for ix in range(-n, n+1):
        for iy in range(-n, n+1):
            dx = ix * step; dy = iy * step
            r = math.hypot(dx, dy)
            if r < 0.4 or r > search_r: continue
            vx, vy = px + dx, py + dy
            if check_via(brd, vx, vy, via_dia, net_code, obs, clearance=clearance): continue
            if check_track(brd, px, py, vx, vy, layer, w, net_code, obs, clearance=clearance): continue
            candidates.append((r, dx, dy))
    candidates.sort()
    return candidates if not top_n else candidates[:top_n]


def place_stitch(brd, ref, pn, net_name, dx, dy, via_dia=0.60):
    """Place via at offset + short trace pad→via."""
    pad = get_pad(brd, ref, pn)
    px, py = pad_center(pad)
    layer = pad_layer(pad)
    w = net_width(net_name)
    nets = {str(k): v for k, v in brd.GetNetsByName().asdict().items()}
    net_obj = nets[net_name]
    add_track(brd, px, py, px+dx, py+dy, net_obj, layer=layer, w=w)
    add_via(brd, px+dx, py+dy, net_obj, dia=via_dia, drill=DRILL_MM)


def drc_counts():
    DRC_TMP = "/tmp/_fs_drc.txt"
    subprocess.run(["kicad-cli","pcb","drc","--severity-error",
                    "--format","report","--output",DRC_TMP,
                    "--units","mm",PCB], capture_output=True, text=True)
    txt = open(DRC_TMP).read()
    e = re.search(r"Found (\d+) DRC violation", txt)
    u = re.search(r"Found (\d+) unconnected pad", txt)
    return (int(e.group(1)) if e else 0, int(u.group(1)) if u else 0)


def main():
    brd = pcbnew.LoadBoard(PCB)
    base_err, base_unc = drc_counts()
    print(f"[baseline] err={base_err} unc={base_unc}")
    cur_err = base_err

    results = []
    placed = 0
    for ref, pn, net_name, via_net in STITCH_PADS:
        print(f"\n--- {ref}.{pn} ({net_name}) ---")
        # fast_check grid search → top-5 candidates → DRC each in order,
        # accept first clean. Capped at 5 DRC/pad to stay under 5 min/pad.
        all_cands = []
        for dia, rad in [(0.60, 4.0), (0.56, 4.0), (0.60, 6.0), (0.56, 6.0), (0.60, 8.0), (0.56, 8.0)]:
            cs = find_clear_via_candidates(brd, ref, pn, via_net, via_dia=dia,
                                            search_r=rad, clearance=0.20, top_n=5)
            for r, dx, dy in cs:
                all_cands.append((r, dx, dy, dia))
            if cs: break
        # Dedupe by (round to 0.1mm)
        seen = set()
        dedup = []
        for r, dx, dy, dia in sorted(all_cands):
            key = (round(dx, 1), round(dy, 1), dia)
            if key in seen: continue
            seen.add(key)
            dedup.append((r, dx, dy, dia))
        candidates = dedup[:5]
        if not candidates:
            print(f"  NO_CLEAR_SPOT — fast_check finds no via fit in 8mm")
            results.append({"ref":ref,"pad":pn,"net":net_name,
                            "ok":False,"reason":"no_clear_spot_8mm"})
            continue

        placed_this = False
        for r, dx, dy, dia in candidates:
            place_stitch(brd, ref, pn, via_net, dx, dy, via_dia=dia)
            pcbnew.SaveBoard(PCB, brd)
            new_err, _ = drc_counts()
            if new_err <= cur_err:
                print(f"  PLACED via {dia}mm at offset ({dx:+.2f}, {dy:+.2f}), r={r:.2f}mm, drc {cur_err}->{new_err}")
                results.append({"ref":ref,"pad":pn,"net":net_name,"ok":True,
                                "via_dia":dia,"offset":[dx,dy],"r":r})
                cur_err = new_err
                placed += 1
                placed_this = True
                break
            # Revert single placement
            print(f"  cand ({dx:+.2f},{dy:+.2f})/{dia}mm: drc {cur_err}->{new_err}, revert")
            brd = pcbnew.LoadBoard(PCB)
            px, py = pad_center(get_pad(brd, ref, pn))
            for t in list(brd.GetTracks()):
                pos = t.GetPosition()
                if isinstance(t, pcbnew.PCB_VIA):
                    if abs(pos.x/1e6 - (px+dx)) < 0.01 and abs(pos.y/1e6 - (py+dy)) < 0.01:
                        brd.Remove(t)
                else:
                    s = t.GetStart(); e = t.GetEnd()
                    if (abs(s.x/1e6 - px) < 0.01 and abs(s.y/1e6 - py) < 0.01 and
                        abs(e.x/1e6 - (px+dx)) < 0.01 and abs(e.y/1e6 - (py+dy)) < 0.01):
                        brd.Remove(t)
            pcbnew.SaveBoard(PCB, brd)
        if not placed_this:
            print(f"  STUCK — {len(candidates)} DRC-checked candidates all failed")
            results.append({"ref":ref,"pad":pn,"net":net_name,
                            "ok":False,"reason":f"all_{len(candidates)}_drc_failed"})

    pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
    pcbnew.SaveBoard(PCB, brd)
    final_err, final_unc = drc_counts()
    delta_err = final_err - base_err
    delta_unc = final_unc - base_unc
    print(f"\n[final] err={final_err} unc={final_unc}  delta_err={delta_err:+d} delta_unc={delta_unc:+d}")
    print(f"placed: {placed}/{len(STITCH_PADS)}")

    out = os.path.join(HERE, "fine_stitch_log.json")
    with open(out, "w") as f:
        json.dump({"baseline":{"err":base_err,"unc":base_unc},
                   "final":{"err":final_err,"unc":final_unc},
                   "delta_err":delta_err,"delta_unc":delta_unc,
                   "placed":placed,"results":results}, f, indent=2)
    print(f"[log] {out}")


if __name__ == "__main__":
    main()
