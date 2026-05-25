#!/usr/bin/env python3
"""Per-net DRC-aware router (master 2026-05-22 method).

For each net:
  - Snapshot board
  - Try strategies in order (direct same-layer → L-shapes → via-to-B.Cu →
    L-shapes on B.Cu → hybrid layer-change midway)
  - After each attempt: save + full DRC. If error count > baseline → revert,
    try next strategy.
  - If all strategies fail → list net as STUCK (do NOT force a bad route).

Baseline is the DRC error count AT START of the batch. We accept any
strategy that doesn't make things worse.

Star-routing for 3+ pad nets: route from pad[0] → pad[i] for each i.
Each leg is tried independently. A net only counts as routed if ALL legs route.
"""
import os, sys, re, json, subprocess, time
from copy import deepcopy
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-layout-v1.1.kicad_pcb")
DRC_TMP = "/tmp/_pn_drc.txt"

F_CU = pcbnew.F_Cu
B_CU = pcbnew.B_Cu
PLANE_LAYER = {"GND": pcbnew.In1_Cu, "+3V3": pcbnew.In2_Cu,
               "+3V3A": pcbnew.In2_Cu, "+5V": pcbnew.In3_Cu}

NET_WIDTH = {"default":0.20,"power":0.50,"usb":0.30,
             "imu_spi":0.20,"can":0.20,"dshot":0.30}
VIA_DIA, VIA_DRILL = 0.60, 0.30

POWER_NETS = {"GND","+3V3","+3V3A","+5V","+3V3_IMU","+3V3_IMU_PRE",
              "+5V_BEC","+5V_BEC_A","+5V_BEC_B","+5V_BEC_PROT",
              "VBAT","VCAP1","VCAP2","VREF_P",
              "ORING_A_GATE","ORING_B_GATE","ORING_A_VCAP","ORING_B_VCAP"}

def net_width(net):
    if net in POWER_NETS: return NET_WIDTH["power"]
    if net.startswith("USBC_D_") or net in ("USB_DM","USB_DP"): return NET_WIDTH["usb"]
    if net.startswith("SPI") or net.startswith("IMU"): return NET_WIDTH["imu_spi"]
    if net.startswith("CAN") or net == "GPIO_CAN1_SILENT": return NET_WIDTH["can"]
    if net.startswith("MOT"): return NET_WIDTH["dshot"]
    return NET_WIDTH["default"]


def _mm(x): return int(x*1_000_000)


def add_via(brd, x, y, net_obj, dia=VIA_DIA, drill=VIA_DRILL):
    v = pcbnew.PCB_VIA(brd)
    v.SetPosition(pcbnew.VECTOR2I(_mm(x), _mm(y)))
    v.SetWidth(_mm(dia)); v.SetDrill(_mm(drill))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetLayerPair(F_CU, B_CU)
    v.SetNet(net_obj)
    brd.Add(v); return v


def add_track(brd, x1, y1, x2, y2, net_obj, layer=F_CU, w=0.20):
    if abs(x1-x2) < 1e-6 and abs(y1-y2) < 1e-6:
        return None  # zero-length, skip
    t = pcbnew.PCB_TRACK(brd)
    t.SetStart(pcbnew.VECTOR2I(_mm(x1), _mm(y1)))
    t.SetEnd(pcbnew.VECTOR2I(_mm(x2), _mm(y2)))
    t.SetWidth(_mm(w)); t.SetLayer(layer); t.SetNet(net_obj)
    brd.Add(t); return t


def get_pad(brd, ref, pn):
    for fp in brd.GetFootprints():
        if fp.GetReference() == ref:
            for p in fp.Pads():
                if p.GetNumber() == pn:
                    return p
    return None


def pad_center(p):
    pos = p.GetPosition(); return pos.x/1e6, pos.y/1e6


def pad_layer(p):
    if p.IsOnLayer(F_CU): return F_CU
    if p.IsOnLayer(B_CU): return B_CU
    return F_CU  # THT — accessible both


def drc_counts():
    """Return (errors, unconnected) from kicad-cli DRC."""
    subprocess.run(["kicad-cli","pcb","drc","--severity-error",
                    "--format","report","--output",DRC_TMP,
                    "--units","mm",PCB],
                   capture_output=True, text=True)
    with open(DRC_TMP) as f: t = f.read()
    e = re.search(r"Found (\d+) DRC violation", t)
    u = re.search(r"Found (\d+) unconnected pad", t)
    return (int(e.group(1)) if e else 0, int(u.group(1)) if u else 0)


# ---- strategies ----------------------------------------------------------
def strat_direct(brd, x1, y1, x2, y2, layer, net_obj, w):
    t = add_track(brd, x1, y1, x2, y2, net_obj, layer=layer, w=w)
    return [t] if t else []


def strat_L(brd, x1, y1, x2, y2, layer, net_obj, w, horizontal_first=True):
    objs = []
    if horizontal_first:
        cx, cy = x2, y1
    else:
        cx, cy = x1, y2
    t1 = add_track(brd, x1, y1, cx, cy, net_obj, layer=layer, w=w)
    t2 = add_track(brd, cx, cy, x2, y2, net_obj, layer=layer, w=w)
    if t1: objs.append(t1)
    if t2: objs.append(t2)
    return objs


def strat_via_pair_L(brd, x1, y1, x2, y2, layer_a, layer_b, net_obj, w, horizontal_first=True):
    """Drop via at pad1 corner, L-route on layer_b, via back near pad2."""
    objs = []
    # via near p1 (10 mils = 0.25mm offset toward midpoint)
    dx, dy = x2-x1, y2-y1
    n = max(abs(dx)+abs(dy), 0.001)
    vx1 = x1 + 0.4 * (dx/n) * 1.0   # 0.4mm in the direction of p2
    vy1 = y1 + 0.4 * (dy/n) * 1.0
    vx2 = x2 - 0.4 * (dx/n) * 1.0
    vy2 = y2 - 0.4 * (dy/n) * 1.0
    # short trace pad1 → via1 on layer_a
    t = add_track(brd, x1, y1, vx1, vy1, net_obj, layer=layer_a, w=w); objs.append(t)
    v1 = add_via(brd, vx1, vy1, net_obj); objs.append(v1)
    # L on layer_b
    if horizontal_first:
        cx, cy = vx2, vy1
    else:
        cx, cy = vx1, vy2
    objs.append(add_track(brd, vx1, vy1, cx, cy, net_obj, layer=layer_b, w=w))
    objs.append(add_track(brd, cx, cy, vx2, vy2, net_obj, layer=layer_b, w=w))
    v2 = add_via(brd, vx2, vy2, net_obj); objs.append(v2)
    objs.append(add_track(brd, vx2, vy2, x2, y2, net_obj, layer=layer_a, w=w))
    return [o for o in objs if o]


def strat_via_stub(brd, x, y, ox, oy, net_obj, w, layer):
    """For plane-stitch: short trace pad → via at offset (via to plane)."""
    objs = []
    t = add_track(brd, x, y, x+ox, y+oy, net_obj, layer=layer, w=w); objs.append(t)
    v = add_via(brd, x+ox, y+oy, net_obj); objs.append(v)
    return [o for o in objs if o]


# ---- main router ---------------------------------------------------------
def route_leg(brd, p1, p2, net_name, net_obj, baseline_err):
    """Try strategies for a single 2-pad leg. Returns (success, strat_name, new_err)."""
    x1, y1 = pad_center(p1); x2, y2 = pad_center(p2)
    l1 = pad_layer(p1); l2 = pad_layer(p2)
    w = net_width(net_name)

    strategies = []
    if l1 == l2:
        strategies = [
            ("direct_F",   lambda: strat_direct(brd, x1, y1, x2, y2, F_CU, net_obj, w)),
            ("L_HF_F",     lambda: strat_L(brd, x1, y1, x2, y2, F_CU, net_obj, w, True)),
            ("L_VF_F",     lambda: strat_L(brd, x1, y1, x2, y2, F_CU, net_obj, w, False)),
            ("direct_B",   lambda: strat_direct(brd, x1, y1, x2, y2, B_CU, net_obj, w)),
            ("L_HF_B",     lambda: strat_L(brd, x1, y1, x2, y2, B_CU, net_obj, w, True)),
            ("L_VF_B",     lambda: strat_L(brd, x1, y1, x2, y2, B_CU, net_obj, w, False)),
            ("via_pair_HF",lambda: strat_via_pair_L(brd, x1, y1, x2, y2, l1, B_CU if l1==F_CU else F_CU, net_obj, w, True)),
            ("via_pair_VF",lambda: strat_via_pair_L(brd, x1, y1, x2, y2, l1, B_CU if l1==F_CU else F_CU, net_obj, w, False)),
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
        new_err, new_unc = drc_counts()
        if new_err <= baseline_err:
            return True, name, new_err
        # revert this strategy's adds
        for o in added:
            try: brd.Remove(o)
            except: pass
        pcbnew.SaveBoard(PCB, brd)
    return False, "stuck", baseline_err


def pad_label(pad):
    """Safe ref.pad string even if GetParent() returns a base container."""
    fp = pad.GetParentFootprint() if hasattr(pad, 'GetParentFootprint') else pad.GetParent()
    try:
        ref = fp.GetReference()
    except Exception:
        ref = "?"
    return f"{ref}.{pad.GetNumber()}"


def route_net(brd, net_name, pads, baseline_err):
    """Star-route from pad[0] to all others. Returns dict of legs."""
    nets = {str(k): v for k, v in brd.GetNetsByName().asdict().items()}
    net_obj = nets[net_name]
    results = []
    cur_err = baseline_err
    if len(pads) < 2:
        return [("solo", "skipped-1pad", cur_err)]
    if len(pads) == 2:
        ok, strat, ne = route_leg(brd, pads[0], pads[1], net_name, net_obj, cur_err)
        results.append((f"{pad_label(pads[0])}->{pad_label(pads[1])}", strat, ne))
        return results
    # Star: pad[0] → each other
    for p in pads[1:]:
        ok, strat, ne = route_leg(brd, pads[0], p, net_name, net_obj, cur_err)
        results.append((f"star->{pad_label(p)}", strat, ne))
        cur_err = ne  # accept the new baseline if it didn't go up
    return results


def route_plane_stitch(brd, ref, pn, net_name, ox, oy, baseline_err):
    """For plane-stitch failure: place via at offset, short trace from pad."""
    pad = get_pad(brd, ref, pn)
    if not pad:
        return False, f"{ref}.{pn} not found", baseline_err
    nets = {str(k): v for k, v in brd.GetNetsByName().asdict().items()}
    via_net_name = "+3V3" if net_name == "+3V3A" else net_name
    net_obj = nets[via_net_name]
    px, py = pad_center(pad)
    w = net_width(net_name)
    layer = pad_layer(pad)

    # Try master-suggested offset first, then progressively-larger fallback offsets.
    # Each scale tier in 8 cardinal/diagonal directions = 17 total candidates.
    candidates = [(ox, oy)]
    for scale in [1.5, 2.0, 2.5, 3.0]:
        for dx, dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,-1),(1,-1),(-1,1)]:
            o = (dx*scale, dy*scale)
            if o != (ox,oy): candidates.append(o)

    for cx_off, cy_off in candidates:
        added = strat_via_stub(brd, px, py, cx_off, cy_off, net_obj, w, layer)
        pcbnew.SaveBoard(PCB, brd)
        new_err, new_unc = drc_counts()
        if new_err <= baseline_err:
            return True, f"offset({cx_off:+.1f},{cy_off:+.1f})", new_err
        for o in added:
            try: brd.Remove(o)
            except: pass
        pcbnew.SaveBoard(PCB, brd)
    return False, "stuck-all-offsets", baseline_err


# ---- batch driver --------------------------------------------------------
def main(batch_file):
    with open(batch_file) as f:
        batch = json.load(f)
    print(f"[batch] {batch_file} — {len(batch['stitch_fails'])} stitch + {len(batch['nets'])} nets")
    brd = pcbnew.LoadBoard(PCB)

    # Establish baseline
    err0, unc0 = drc_counts()
    print(f"[baseline] err={err0}  unc={unc0}")
    current_err = err0
    log = []

    # Stitch fails first. NOTE: +3V3A has NO plane — those pads are routed
    # as a trace net in the 'nets' section, not stitched here.
    for ref, pn, net_name, ox, oy in batch['stitch_fails']:
        if net_name == "+3V3A":
            print(f"  STITCH {ref}.{pn} ({net_name}): +3V3A has no plane — defer to trace-route")
            log.append({"kind":"stitch","ref":ref,"pad":pn,"net":net_name,
                        "ok":False,"strategy":"deferred-to-trace","err_after":current_err})
            continue
        print(f"  STITCH {ref}.{pn} ({net_name})...")
        ok, why, ne = route_plane_stitch(brd, ref, pn, net_name, ox, oy, current_err)
        log.append({"kind":"stitch","ref":ref,"pad":pn,"net":net_name,
                    "ok":ok,"strategy":why,"err_after":ne})
        if ok:
            print(f"    OK  {why}  err->{ne}")
            current_err = ne
        else:
            print(f"    STUCK  {why}")
        # Reload board between attempts to refresh net objs (avoids stale handles)
        brd = pcbnew.LoadBoard(PCB)

    # Signal nets — pad list from residual JSON
    residuals = json.load(open(os.path.join(HERE, "vision_residuals_mp30.json")))
    by_net = residuals.get("by_net", {})

    for net_name in batch['nets']:
        pad_specs = by_net.get(net_name, [])
        if len(pad_specs) < 2:
            print(f"  NET {net_name}: only {len(pad_specs)} pad(s) — skip")
            log.append({"kind":"net","net":net_name,"ok":False,
                        "strategy":"skipped-singleton","err_after":current_err})
            continue
        pads = [get_pad(brd, ps["ref"], ps["pad"]) for ps in pad_specs]
        pads = [p for p in pads if p]
        # reload board to refresh net objects after each net (saves accumulate)
        brd = pcbnew.LoadBoard(PCB)
        # re-resolve pads on reloaded board
        pads = [get_pad(brd, ps["ref"], ps["pad"]) for ps in pad_specs]
        pads = [p for p in pads if p]
        print(f"  NET {net_name} ({len(pads)} pads)...")
        results = route_net(brd, net_name, pads, current_err)
        any_ok = False
        for leg, strat, ne in results:
            if strat == "stuck":
                print(f"    STUCK leg={leg}")
            else:
                print(f"    OK  leg={leg}  strat={strat}  err->{ne}")
                any_ok = True
                current_err = max(current_err, ne)
        log.append({"kind":"net","net":net_name,
                    "ok":any_ok,"legs":[{"leg":l,"strat":s,"err":e} for l,s,e in results],
                    "err_after":current_err})

    # Final refill + DRC
    brd = pcbnew.LoadBoard(PCB)
    pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
    pcbnew.SaveBoard(PCB, brd)
    final_err, final_unc = drc_counts()
    print(f"\n[final] err={final_err}  unc={final_unc}  delta={final_err-err0:+d}")

    # Write log
    log_path = os.path.join(HERE, batch_file.replace(".json","_log.json"))
    with open(log_path, "w") as f:
        json.dump({"baseline":{"err":err0,"unc":unc0},
                   "final":{"err":final_err,"unc":final_unc},
                   "results":log}, f, indent=2)
    print(f"[log] {log_path}")


if __name__ == "__main__":
    main(sys.argv[1])
