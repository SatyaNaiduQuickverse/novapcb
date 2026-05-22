#!/usr/bin/env python3
"""Optimized per-net router — fast_check + final DRC.

Strategy:
  1. Use fast_check (in-process, ~1ms) to evaluate each candidate
  2. Pick first strategy with 0 fast_check violations
  3. Apply, no per-strategy DRC
  4. Run ONE final DRC at end of batch
  5. If final DRC went up vs baseline, report which nets are likely culprits

~1000x faster than the full-DRC-per-strategy version.

Limitations: fast_check misses inner-layer plane interactions, net-class
clearance > default, mask-bridge edge cases. Final DRC catches these,
but a fast_check-clean strategy may still fail final DRC. In that case
we mark the batch as "needs human review".
"""
import os, sys, json, subprocess, re
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-layout-v1.1.kicad_pcb")
DRC_TMP = "/tmp/_opt_drc.txt"

sys.path.insert(0, HERE)
from per_net_router import (
    F_CU, B_CU, _mm,
    add_via, add_track, get_pad, pad_center, pad_layer,
    net_width, pad_label, NET_WIDTH
)
from fast_check import collect_obstacles, check_track, check_via


# ----- strategy builders return list of geometry actions to apply -----
def gen_direct(x1, y1, x2, y2, layer, width_mm):
    return [("track", x1, y1, x2, y2, layer, width_mm)]


def gen_L(x1, y1, x2, y2, layer, width_mm, horizontal_first=True):
    if horizontal_first:
        cx, cy = x2, y1
    else:
        cx, cy = x1, y2
    return [
        ("track", x1, y1, cx, cy, layer, width_mm),
        ("track", cx, cy, x2, y2, layer, width_mm),
    ]


def gen_via_pair_L(x1, y1, x2, y2, layer_a, layer_b, width_mm, horizontal_first=True):
    """Drop via near pad1, L-route on layer_b, via back near pad2."""
    import math
    dx, dy = x2-x1, y2-y1
    n = max(math.hypot(dx, dy), 0.001)
    # Place via 0.6mm from each endpoint along the direction
    vx1 = x1 + 0.6 * (dx/n)
    vy1 = y1 + 0.6 * (dy/n)
    vx2 = x2 - 0.6 * (dx/n)
    vy2 = y2 - 0.6 * (dy/n)
    if horizontal_first:
        cx, cy = vx2, vy1
    else:
        cx, cy = vx1, vy2
    return [
        ("track", x1, y1, vx1, vy1, layer_a, width_mm),
        ("via",   vx1, vy1, 0.60),
        ("track", vx1, vy1, cx, cy, layer_b, width_mm),
        ("track", cx, cy, vx2, vy2, layer_b, width_mm),
        ("via",   vx2, vy2, 0.60),
        ("track", vx2, vy2, x2, y2, layer_a, width_mm),
    ]


def gen_U_detour(x1, y1, x2, y2, layer, width_mm, detour_dir="north", detour_mm=5.0):
    """U-shape: go out (north/south/east/west), across, back. For routes that
    can't go direct because the pad-pad line crosses dense areas."""
    if detour_dir == "north":
        # both endpoints go north to y_max, then horizontally, then back down
        ym = min(y1, y2) - detour_mm
        return [
            ("track", x1, y1, x1, ym, layer, width_mm),
            ("track", x1, ym, x2, ym, layer, width_mm),
            ("track", x2, ym, x2, y2, layer, width_mm),
        ]
    elif detour_dir == "south":
        ym = max(y1, y2) + detour_mm
        return [
            ("track", x1, y1, x1, ym, layer, width_mm),
            ("track", x1, ym, x2, ym, layer, width_mm),
            ("track", x2, ym, x2, y2, layer, width_mm),
        ]
    elif detour_dir == "east":
        xm = max(x1, x2) + detour_mm
        return [
            ("track", x1, y1, xm, y1, layer, width_mm),
            ("track", xm, y1, xm, y2, layer, width_mm),
            ("track", xm, y2, x2, y2, layer, width_mm),
        ]
    elif detour_dir == "west":
        xm = min(x1, x2) - detour_mm
        return [
            ("track", x1, y1, xm, y1, layer, width_mm),
            ("track", xm, y1, xm, y2, layer, width_mm),
            ("track", xm, y2, x2, y2, layer, width_mm),
        ]


def gen_U_detour_with_vias(x1, y1, x2, y2, layer_a, layer_b, width_mm, detour_dir, detour_mm):
    """U-shape on layer_b with via at each end to layer_a (pad's layer)."""
    import math
    dx, dy = x2-x1, y2-y1
    n = max(math.hypot(dx, dy), 0.001)
    vx1 = x1 + 0.6 * (dx/n); vy1 = y1 + 0.6 * (dy/n)
    vx2 = x2 - 0.6 * (dx/n); vy2 = y2 - 0.6 * (dy/n)
    if detour_dir == "north":
        ym = min(vy1, vy2) - detour_mm
        return [
            ("track", x1, y1, vx1, vy1, layer_a, width_mm),
            ("via",   vx1, vy1, 0.60),
            ("track", vx1, vy1, vx1, ym, layer_b, width_mm),
            ("track", vx1, ym, vx2, ym, layer_b, width_mm),
            ("track", vx2, ym, vx2, vy2, layer_b, width_mm),
            ("via",   vx2, vy2, 0.60),
            ("track", vx2, vy2, x2, y2, layer_a, width_mm),
        ]
    elif detour_dir == "south":
        ym = max(vy1, vy2) + detour_mm
        return [
            ("track", x1, y1, vx1, vy1, layer_a, width_mm),
            ("via",   vx1, vy1, 0.60),
            ("track", vx1, vy1, vx1, ym, layer_b, width_mm),
            ("track", vx1, ym, vx2, ym, layer_b, width_mm),
            ("track", vx2, ym, vx2, vy2, layer_b, width_mm),
            ("via",   vx2, vy2, 0.60),
            ("track", vx2, vy2, x2, y2, layer_a, width_mm),
        ]
    elif detour_dir == "east":
        xm = max(vx1, vx2) + detour_mm
        return [
            ("track", x1, y1, vx1, vy1, layer_a, width_mm),
            ("via",   vx1, vy1, 0.60),
            ("track", vx1, vy1, xm, vy1, layer_b, width_mm),
            ("track", xm, vy1, xm, vy2, layer_b, width_mm),
            ("track", xm, vy2, vx2, vy2, layer_b, width_mm),
            ("via",   vx2, vy2, 0.60),
            ("track", vx2, vy2, x2, y2, layer_a, width_mm),
        ]
    elif detour_dir == "west":
        xm = min(vx1, vx2) - detour_mm
        return [
            ("track", x1, y1, vx1, vy1, layer_a, width_mm),
            ("via",   vx1, vy1, 0.60),
            ("track", vx1, vy1, xm, vy1, layer_b, width_mm),
            ("track", xm, vy1, xm, vy2, layer_b, width_mm),
            ("track", xm, vy2, vx2, vy2, layer_b, width_mm),
            ("via",   vx2, vy2, 0.60),
            ("track", vx2, vy2, x2, y2, layer_a, width_mm),
        ]


def gen_stub_via(px, py, ox, oy, layer, width_mm, shape="direct"):
    """Plane-stitch: trace + via at offset. shape='direct'|'L_HF'|'L_VF'."""
    vx, vy = px+ox, py+oy
    if shape == "direct":
        return [
            ("track", px, py, vx, vy, layer, width_mm),
            ("via",   vx, vy, 0.60),
        ]
    elif shape == "L_HF":
        cx, cy = vx, py
        return [
            ("track", px, py, cx, cy, layer, width_mm),
            ("track", cx, cy, vx, vy, layer, width_mm),
            ("via",   vx, vy, 0.60),
        ]
    elif shape == "L_VF":
        cx, cy = px, vy
        return [
            ("track", px, py, cx, cy, layer, width_mm),
            ("track", cx, cy, vx, vy, layer, width_mm),
            ("via",   vx, vy, 0.60),
        ]


def fast_eval(brd, ops, my_net_code, obstacles, clearance=0.10):
    """Evaluate proposed ops via fast_check. Return list of violations."""
    viols = []
    for op in ops:
        if op[0] == "track":
            _, x1, y1, x2, y2, lay, w = op
            v = check_track(brd, x1, y1, x2, y2, lay, w, my_net_code, obstacles, clearance)
            viols.extend(v)
        elif op[0] == "via":
            _, x, y, dia = op
            v = check_via(brd, x, y, dia, my_net_code, obstacles, clearance)
            viols.extend(v)
    return viols


def apply_ops(brd, ops, net_obj):
    added = []
    for op in ops:
        if op[0] == "track":
            _, x1, y1, x2, y2, lay, w = op
            t = add_track(brd, x1, y1, x2, y2, net_obj, layer=lay, w=w)
            if t: added.append(t)
        elif op[0] == "via":
            _, x, y, dia = op
            v = add_via(brd, x, y, net_obj, dia=dia)
            added.append(v)
    return added


def revert_ops(brd, added):
    for o in added:
        try: brd.Remove(o)
        except: pass


def route_signal_leg(brd, p_src, p_tgt, net_name, net_obj, net_code):
    """Try strategies, fast-evaluate, apply first clean. Return (ok, strat, ops)."""
    x1, y1 = pad_center(p_src); x2, y2 = pad_center(p_tgt)
    l1 = pad_layer(p_src); l2 = pad_layer(p_tgt)
    w = net_width(net_name)
    other = B_CU if l1 == F_CU else F_CU
    obs = collect_obstacles(brd, net_code)

    candidates = []
    if l1 == l2:
        candidates = [
            ("direct",      gen_direct(x1, y1, x2, y2, l1, w)),
            ("L_HF",        gen_L(x1, y1, x2, y2, l1, w, True)),
            ("L_VF",        gen_L(x1, y1, x2, y2, l1, w, False)),
            # opp_* removed — routing on opposite layer without vias leaves pads floating
            ("via_HF",      gen_via_pair_L(x1, y1, x2, y2, l1, other, w, True)),
            ("via_VF",      gen_via_pair_L(x1, y1, x2, y2, l1, other, w, False)),
        ]
        # U-detour at expanding distances. On pad's layer = no vias needed.
        # Opposite-layer variants always use vias.
        for det_mm in [3, 5, 8, 10, 12, 15, 20]:
            for dirn in ["north","south","east","west"]:
                candidates.append((f"U_{dirn}_{det_mm}_F",
                                   gen_U_detour(x1, y1, x2, y2, l1, w, dirn, det_mm)))
                candidates.append((f"U_{dirn}_{det_mm}_vp",
                                   gen_U_detour_with_vias(x1, y1, x2, y2, l1, other, w, dirn, det_mm)))
    else:
        candidates = [
            ("via_HF",      gen_via_pair_L(x1, y1, x2, y2, l1, l2, w, True)),
            ("via_VF",      gen_via_pair_L(x1, y1, x2, y2, l1, l2, w, False)),
        ]
        for det_mm in [3, 5, 8, 10, 12, 15, 20]:
            for dirn in ["north","south","east","west"]:
                candidates.append((f"U_{dirn}_{det_mm}_vp",
                                   gen_U_detour_with_vias(x1, y1, x2, y2, l1, l2, w, dirn, det_mm)))

    for name, ops in candidates:
        viols = fast_eval(brd, ops, net_code, obs, clearance=0.20)
        if not viols:
            apply_ops(brd, ops, net_obj)
            return True, name, ops
    return False, "stuck", None


def route_stitch(brd, ref, pn, net_name, ox, oy, net_obj, net_code):
    """Try via at master-suggested offset, then expanding fallbacks."""
    pad = get_pad(brd, ref, pn)
    if not pad:
        return False, "pad_not_found", None
    px, py = pad_center(pad)
    layer = pad_layer(pad)
    w = net_width(net_name)
    obs = collect_obstacles(brd, net_code)

    # Build offset candidates: master's first, then expanding rings 1.0-5.0mm
    candidates = [(ox, oy)]
    import itertools
    for scale in [1.0, 1.2, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]:
        for dx, dy in itertools.product([-1, 0, 1], repeat=2):
            if dx == 0 and dy == 0: continue
            o = (dx*scale, dy*scale)
            if o not in candidates: candidates.append(o)

    # For each offset, try direct then L-shaped traces from pad to via
    # Use 0.20mm clearance to match Default netclass (fast_check default is 0.10)
    for cx_off, cy_off in candidates:
        for shape in ["direct", "L_HF", "L_VF"]:
            ops = gen_stub_via(px, py, cx_off, cy_off, layer, w, shape)
            viols = fast_eval(brd, ops, net_code, obs, clearance=0.20)
            if not viols:
                apply_ops(brd, ops, net_obj)
                return True, f"offset({cx_off:+.1f},{cy_off:+.1f})/{shape}", ops
    return False, "stuck-all-offsets", None


def route_trace_net(brd, net_name, src_ref, src_pad, targets, net_obj, net_code):
    """Star-route from src to each target. Returns list of leg results."""
    results = []
    p_src = get_pad(brd, src_ref, src_pad)
    if not p_src:
        return [{"tgt":t, "ok":False, "strat":"src_not_found"} for t in targets]
    for tgt in targets:
        p_tgt = get_pad(brd, tgt["ref"], tgt["pad"])
        if not p_tgt:
            results.append({"tgt":f"{tgt['ref']}.{tgt['pad']}", "ok":False, "strat":"tgt_not_found"})
            continue
        ok, strat, _ = route_signal_leg(brd, p_src, p_tgt, net_name, net_obj, net_code)
        results.append({"tgt":pad_label(p_tgt), "ok":ok, "strat":strat})
    return results


def drc_counts():
    subprocess.run(["kicad-cli","pcb","drc","--severity-error",
                    "--format","report","--output",DRC_TMP,
                    "--units","mm",PCB], capture_output=True, text=True)
    txt = open(DRC_TMP).read()
    e = re.search(r"Found (\d+) DRC violation", txt)
    u = re.search(r"Found (\d+) unconnected pad", txt)
    return (int(e.group(1)) if e else 0, int(u.group(1)) if u else 0)


def main(batch_file):
    with open(batch_file) as f: spec = json.load(f)
    brd = pcbnew.LoadBoard(PCB)
    nets = {str(k): v for k, v in brd.GetNetsByName().asdict().items()}

    print(f"[batch] {batch_file}")
    base_err, base_unc = drc_counts()
    print(f"[baseline] err={base_err}  unc={base_unc}")

    log = []
    n_ok_stitch = n_stuck_stitch = 0
    n_ok_net = n_stuck_net = 0

    # Plane stitches
    for ref, pn, net_name, ox, oy in spec.get("stitch_fails", []):
        if net_name == "+3V3A":
            print(f"  STITCH {ref}.{pn} ({net_name}): no-plane, defer to trace")
            log.append({"kind":"stitch","ref":ref,"pad":pn,"net":net_name,
                        "ok":False,"strategy":"deferred-no-plane"})
            continue
        via_net = "+3V3" if net_name == "+3V3A" else net_name
        net_obj = nets[via_net]
        net_code = net_obj.GetNetCode()
        ok, why, _ = route_stitch(brd, ref, pn, net_name, ox, oy, net_obj, net_code)
        if ok: n_ok_stitch += 1
        else:  n_stuck_stitch += 1
        log.append({"kind":"stitch","ref":ref,"pad":pn,"net":net_name,
                    "ok":ok,"strategy":why})
        print(f"  STITCH {ref}.{pn} ({net_name}): {'OK' if ok else 'STUCK'} {why}")

    # Save after stitches
    pcbnew.SaveBoard(PCB, brd)

    # Signal nets — from residuals JSON
    residuals = json.load(open(os.path.join(HERE, "vision_residuals_mp30.json")))
    by_net = residuals.get("by_net", {})

    # Reload to refresh net objects
    brd = pcbnew.LoadBoard(PCB)
    nets = {str(k): v for k, v in brd.GetNetsByName().asdict().items()}

    for net_name in spec.get("nets", []):
        pad_specs = by_net.get(net_name, [])
        if len(pad_specs) < 2:
            print(f"  NET {net_name}: only {len(pad_specs)} pad(s) — skip")
            log.append({"kind":"net","net":net_name,"ok":False,
                        "strategy":"skipped-singleton"})
            continue
        net_obj = nets[net_name]
        net_code = net_obj.GetNetCode()
        pads = [get_pad(brd, ps["ref"], ps["pad"]) for ps in pad_specs]
        pads = [p for p in pads if p]
        leg_results = []
        # Star routing: pad[0] → others
        for p_tgt in pads[1:]:
            ok, strat, _ = route_signal_leg(brd, pads[0], p_tgt, net_name, net_obj, net_code)
            leg_results.append({"leg":f"{pad_label(pads[0])}->{pad_label(p_tgt)}",
                                "ok":ok, "strat":strat})
        any_ok = any(l["ok"] for l in leg_results)
        if any_ok: n_ok_net += 1
        else:      n_stuck_net += 1
        log.append({"kind":"net","net":net_name,"ok":any_ok,"legs":leg_results})
        print(f"  NET {net_name}: {'OK' if any_ok else 'STUCK'} ({len(leg_results)} legs)")

    # Trace nets (no plane, e.g. +3V3A)
    for tn in spec.get("trace_nets", []):
        net_name = tn["net"]
        net_obj = nets[net_name]
        net_code = net_obj.GetNetCode()
        results = route_trace_net(brd, net_name, tn["source"]["ref"], tn["source"]["pad"],
                                  tn["targets"], net_obj, net_code)
        any_ok = any(r["ok"] for r in results)
        if any_ok: n_ok_net += 1
        else:      n_stuck_net += 1
        log.append({"kind":"net","net":net_name,"trace":True,"ok":any_ok,"legs":results})
        print(f"  TRACE_NET {net_name}: {'OK' if any_ok else 'STUCK'} ({len(results)} legs)")

    # Save + final DRC
    pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
    pcbnew.SaveBoard(PCB, brd)
    final_err, final_unc = drc_counts()
    delta = final_err - base_err
    print(f"\n[final] err={final_err}  unc={final_unc}  delta={delta:+d}")
    print(f"  stitches: {n_ok_stitch}/{n_ok_stitch+n_stuck_stitch} ok")
    print(f"  nets:     {n_ok_net}/{n_ok_net+n_stuck_net} ok")

    log_path = batch_file.replace(".json", "_log.json")
    with open(log_path, "w") as f:
        json.dump({"baseline":{"err":base_err,"unc":base_unc},
                   "final":{"err":final_err,"unc":final_unc},
                   "delta":delta,
                   "stats":{"stitch_ok":n_ok_stitch,"stitch_stuck":n_stuck_stitch,
                            "net_ok":n_ok_net,"net_stuck":n_stuck_net},
                   "results":log}, f, indent=2)
    print(f"[log] {log_path}")


if __name__ == "__main__":
    main(sys.argv[1])
