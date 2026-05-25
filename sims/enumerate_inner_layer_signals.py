#!/usr/bin/env python3
"""Step 6 Block A precursor — full-scope census of signal copper on the
inner PLANE layers In1.Cu / In2.Cu / In3.Cu / In4.Cu.

Per master 2026-05-21 directive: USB on In3.Cu and IMU SPI on In2.Cu
mean Freerouting was treating the plane layers as routing layers.
That's potentially systemic. Enumerate ALL nets with signal copper on
the 4 inner layers so the scope of the reroute fix is known.

A "plane net" (GND, +3V3, +5V) on its own plane layer is the plane
itself — not a routing violation. Only NON-plane nets count as
signal-on-plane misroutes.
"""
import os
import json
from collections import defaultdict
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(os.path.dirname(HERE),
                   "hardware/kicad/novapcb-layout-v2/novapcb-layout-v2.kicad_pcb")
OUT = os.path.join(HERE, "inner_layer_signal_census.json")

INNER_LAYERS = [pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu]

LAYER_PLANE_NET = {
    "In1.Cu": "GND",
    "In2.Cu": "+3V3",
    "In3.Cu": "+5V",
    "In4.Cu": "GND",
}


def name(brd, layer_id):
    return brd.GetLayerName(layer_id)


def main():
    brd = pcbnew.LoadBoard(PCB)
    # Per-layer per-net: list of segments
    by_layer_net = defaultdict(lambda: defaultdict(lambda: {"len_mm": 0.0,
                                                              "n_segments": 0,
                                                              "n_vias": 0,
                                                              "segments": []}))
    for t in brd.GetTracks():
        if t.GetNet() is None:
            continue
        netname = str(t.GetNet().GetNetname())
        if isinstance(t, pcbnew.PCB_VIA):
            # Vias touch their span layers — record on each inner layer in
            # the span so we don't miss plane-via stitches
            top, bot = t.TopLayer(), t.BottomLayer()
            for L in INNER_LAYERS:
                if top <= L <= bot:
                    layer_name = name(brd, L)
                    by_layer_net[layer_name][netname]["n_vias"] += 1
            continue
        layer = t.GetLayer()
        if layer not in INNER_LAYERS:
            continue
        s, e = t.GetStart(), t.GetEnd()
        sx, sy = s.x/1e6, s.y/1e6
        ex, ey = e.x/1e6, e.y/1e6
        length = ((ex-sx)**2 + (ey-sy)**2) ** 0.5
        layer_name = name(brd, layer)
        d = by_layer_net[layer_name][netname]
        d["len_mm"] += length
        d["n_segments"] += 1
        d["segments"].append({"start": [round(sx,4), round(sy,4)],
                              "end":   [round(ex,4), round(ey,4)],
                              "len_mm": round(length, 4)})

    # Classify: plane-net-on-own-plane-layer = OK; everything else = misroute
    summary = {}
    misroutes = []
    for layer_name in sorted(by_layer_net.keys()):
        plane_net = LAYER_PLANE_NET.get(layer_name, "<unknown>")
        layer_info = {"plane_net": plane_net, "nets": {}}
        for net, info in sorted(by_layer_net[layer_name].items(),
                                 key=lambda kv: -kv[1]["len_mm"]):
            info["len_mm"] = round(info["len_mm"], 3)
            is_plane = (net == plane_net)
            is_signal_misroute = (info["n_segments"] > 0 and not is_plane)
            layer_info["nets"][net] = {
                "len_mm": info["len_mm"],
                "n_segments": info["n_segments"],
                "n_vias": info["n_vias"],
                "classification": "plane" if is_plane else (
                    "signal-misroute" if is_signal_misroute else "via-only"),
            }
            if is_signal_misroute:
                misroutes.append({
                    "layer": layer_name,
                    "plane_layer_carries": plane_net,
                    "net": net,
                    "len_mm": info["len_mm"],
                    "n_segments": info["n_segments"],
                    "n_vias": info["n_vias"],
                })
        summary[layer_name] = layer_info

    payload = {
        "_source": PCB,
        "summary_by_layer": summary,
        "misroute_count": len(misroutes),
        "total_misrouted_length_mm": round(sum(m["len_mm"] for m in misroutes), 3),
        "misroutes_ranked": sorted(misroutes, key=lambda m: -m["len_mm"]),
    }
    with open(OUT, "w") as f:
        json.dump(payload, f, indent=2)

    # Console report
    print("="*72)
    print("Inner-layer signal-copper census")
    print("="*72)
    for layer, info in summary.items():
        print(f"\n{layer} (plane net = {info['plane_net']}):")
        for net, ndata in info["nets"].items():
            if ndata["n_segments"] == 0 and ndata["n_vias"] == 0:
                continue
            tag = ""
            if ndata["classification"] == "signal-misroute":
                tag = "  <-- SIGNAL MISROUTE"
            print(f"  {net:24s} len={ndata['len_mm']:8.3f}mm "
                  f"segs={ndata['n_segments']:3d} vias={ndata['n_vias']:3d} "
                  f"[{ndata['classification']}]{tag}")
    print("\n" + "="*72)
    print(f"TOTAL signal misroutes on plane layers: {len(misroutes)} nets, "
          f"{round(sum(m['len_mm'] for m in misroutes), 1)} mm total")
    print("="*72)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
