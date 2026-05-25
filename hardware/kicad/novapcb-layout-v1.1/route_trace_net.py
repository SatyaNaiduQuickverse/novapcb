#!/usr/bin/env python3
"""Route a 'trace net' (no plane): pick a source pad, route fresh traces
to each unconnected target pad. DRC-aware: each new trace validated.

Used for nets like +3V3A which have NO inner-layer plane but DO have
multiple consumer pads scattered around the board.

Strategy per leg (source → target):
  1. direct on source's layer
  2. L-horizontal-first on source's layer
  3. L-vertical-first on source's layer
  4. via-pair to opposite layer + L-shape detour
  5. via-pair to opposite layer + serpentine if needed
  6. STUCK — list it

Source-pad selection: use the pad with the most existing routing
(usually the source of the analog filter — e.g. FB1.2 for +3V3A).

Reuses per_net_router.py's strategy functions where possible.
"""
import os, sys, re, json, subprocess
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-layout-v1.1.kicad_pcb")
DRC_TMP = "/tmp/_tn_drc.txt"

# Reuse strategy primitives + helpers
sys.path.insert(0, HERE)
from per_net_router import (
    F_CU, B_CU, NET_WIDTH, POWER_NETS, _mm,
    add_via, add_track, get_pad, pad_center, pad_layer,
    net_width, pad_label, drc_counts as _drc,
    strat_direct, strat_L, strat_via_pair_L
)


def route_leg_trace(brd, p_src, p_tgt, net_name, net_obj, baseline_err):
    """Try strategies for a source→target leg. Returns (ok, strat, new_err)."""
    x1, y1 = pad_center(p_src); x2, y2 = pad_center(p_tgt)
    l1 = pad_layer(p_src); l2 = pad_layer(p_tgt)
    w = net_width(net_name)
    other_layer = B_CU if l1 == F_CU else F_CU

    strategies = []
    if l1 == l2:
        strategies = [
            ("direct",     lambda: strat_direct(brd, x1, y1, x2, y2, l1, net_obj, w)),
            ("L_HF",       lambda: strat_L(brd, x1, y1, x2, y2, l1, net_obj, w, True)),
            ("L_VF",       lambda: strat_L(brd, x1, y1, x2, y2, l1, net_obj, w, False)),
            ("opp_direct", lambda: strat_direct(brd, x1, y1, x2, y2, other_layer, net_obj, w)),
            ("opp_L_HF",   lambda: strat_L(brd, x1, y1, x2, y2, other_layer, net_obj, w, True)),
            ("opp_L_VF",   lambda: strat_L(brd, x1, y1, x2, y2, other_layer, net_obj, w, False)),
            ("via_pair_HF",lambda: strat_via_pair_L(brd, x1, y1, x2, y2, l1, other_layer, net_obj, w, True)),
            ("via_pair_VF",lambda: strat_via_pair_L(brd, x1, y1, x2, y2, l1, other_layer, net_obj, w, False)),
        ]
    else:
        strategies = [
            ("via_pair_HF",lambda: strat_via_pair_L(brd, x1, y1, x2, y2, l1, l2, net_obj, w, True)),
            ("via_pair_VF",lambda: strat_via_pair_L(brd, x1, y1, x2, y2, l1, l2, net_obj, w, False)),
        ]

    for name, fn in strategies:
        added = fn()
        if not added: continue
        pcbnew.SaveBoard(PCB, brd)
        new_err, _ = _drc()
        if new_err <= baseline_err:
            return True, name, new_err
        for o in added:
            try: brd.Remove(o)
            except: pass
        pcbnew.SaveBoard(PCB, brd)
    return False, "stuck", baseline_err


def main(spec_file):
    with open(spec_file) as f:
        spec = json.load(f)
    brd = pcbnew.LoadBoard(PCB)
    nets = {str(k): v for k, v in brd.GetNetsByName().asdict().items()}
    base_err, base_unc = _drc()
    print(f"[baseline] err={base_err} unc={base_unc}")
    log = []
    cur_err = base_err

    for net_spec in spec.get("trace_nets", []):
        net_name = net_spec["net"]
        net_obj = nets[net_name]
        src = net_spec["source"]
        p_src = get_pad(brd, src["ref"], src["pad"])
        if not p_src:
            print(f"  {net_name}: source {src['ref']}.{src['pad']} not found")
            continue
        for tgt in net_spec["targets"]:
            brd = pcbnew.LoadBoard(PCB)
            p_src = get_pad(brd, src["ref"], src["pad"])
            p_tgt = get_pad(brd, tgt["ref"], tgt["pad"])
            if not p_tgt:
                print(f"  {net_name} -> {tgt['ref']}.{tgt['pad']}: not found")
                continue
            ok, strat, ne = route_leg_trace(brd, p_src, p_tgt, net_name, net_obj, cur_err)
            tag = f"{net_name}: {pad_label(p_src)} -> {pad_label(p_tgt)}"
            if ok:
                print(f"  {tag}  OK  {strat}  err->{ne}")
                cur_err = ne
            else:
                print(f"  {tag}  STUCK")
            log.append({"net":net_name,"src":pad_label(p_src),
                        "tgt":pad_label(p_tgt),"ok":ok,
                        "strat":strat,"err_after":ne})

    log_path = spec_file.replace(".json","_log.json")
    with open(log_path, "w") as f:
        json.dump({"baseline":{"err":base_err,"unc":base_unc},
                   "results":log}, f, indent=2)
    print(f"[log] {log_path}")


if __name__ == "__main__":
    main(sys.argv[1])
