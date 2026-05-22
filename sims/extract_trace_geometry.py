#!/usr/bin/env python3
"""Step 6 Block A — extract routed-trace geometry from layout-v2.

Pulls per-net total length, segment counts, via counts, and start/end
endpoints from the Step 5 routed board. Output is a JSON the Block A
sim scripts consume.

Categories the sims need:
  - USB diff pair: USB_DP / USB_DM
  - IMU SPI: SPI1_SCK, SPI1_MISO, SPI1_MOSI, IMU1_CS, IMU2_CS
  - SDMMC: SDMMC_CK, SDMMC_CMD, SDMMC_D0..D3
  - DShot motor outputs: MOT1..MOT8
"""

import json
import os
import re
from collections import defaultdict
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB_PATH = os.path.join(os.path.dirname(HERE),
                        "hardware/kicad/novapcb-layout-v2/novapcb-layout-v2.kicad_pcb")
OUT_PATH = os.path.join(HERE, "trace_geometry.json")

LAYER_NAMES = {
    pcbnew.F_Cu: "F.Cu", pcbnew.B_Cu: "B.Cu",
    pcbnew.In1_Cu: "In1.Cu", pcbnew.In2_Cu: "In2.Cu",
    pcbnew.In3_Cu: "In3.Cu", pcbnew.In4_Cu: "In4.Cu",
}

NET_CATEGORIES = {
    "usb_diff_pair": ["USB_DP", "USB_DM"],
    "imu_spi": ["SPI1_SCK", "SPI1_MISO", "SPI1_MOSI",
                "IMU1_CS", "IMU2_CS"],
    "sdmmc": ["SDMMC1_CLK", "SDMMC1_CMD",
              "SDMMC1_D0", "SDMMC1_D1", "SDMMC1_D2", "SDMMC1_D3"],
    "dshot": ["MOT1", "MOT2", "MOT3", "MOT4",
              "MOT5", "MOT6", "MOT7", "MOT8"],
}


def per_net_geometry(brd):
    """{netname: {len_mm, n_segments, n_vias, layers, segments[]}}"""
    out = defaultdict(lambda: {"len_mm": 0.0, "n_segments": 0,
                                "n_vias": 0, "layers": set(),
                                "segments": []})
    for t in brd.GetTracks():
        if t.GetNet() is None:
            continue
        net = str(t.GetNet().GetNetname())
        if isinstance(t, pcbnew.PCB_VIA):
            out[net]["n_vias"] += 1
            continue
        s, e = t.GetStart(), t.GetEnd()
        sx, sy = s.x/1e6, s.y/1e6
        ex, ey = e.x/1e6, e.y/1e6
        length = ((ex-sx)**2 + (ey-sy)**2) ** 0.5
        layer = LAYER_NAMES.get(t.GetLayer(), f"L{t.GetLayer()}")
        out[net]["len_mm"] += length
        out[net]["n_segments"] += 1
        out[net]["layers"].add(layer)
        out[net]["segments"].append(
            {"start": [round(sx, 4), round(sy, 4)],
             "end":   [round(ex, 4), round(ey, 4)],
             "layer": layer,
             "len_mm": round(length, 4),
             "width_mm": round(t.GetWidth()/1e6, 3)})
    # Make layers JSON-serializable
    for k in out:
        out[k]["layers"] = sorted(list(out[k]["layers"]))
        out[k]["len_mm"] = round(out[k]["len_mm"], 4)
    return out


def fuzzy_match(name, candidates):
    """Match net name vs candidate list with flexibility (case, prefix)."""
    name_u = name.upper().replace("-", "_")
    for c in candidates:
        if c.upper() in name_u:
            return c
    return None


def main():
    print(f"[1] load {PCB_PATH}")
    brd = pcbnew.LoadBoard(PCB_PATH)

    print(f"[2] extract per-net geometry")
    geom = per_net_geometry(brd)
    print(f"    {len(geom)} nets with track geometry")

    print(f"[3] map to categories")
    by_category = {}
    for cat, candidates in NET_CATEGORIES.items():
        by_category[cat] = {}
        for net_name, info in geom.items():
            match = fuzzy_match(net_name, candidates)
            if match:
                by_category[cat][net_name] = {
                    "matched_to": match,
                    **info,
                }

    print(f"[4] summary by category")
    for cat, nets in by_category.items():
        n = len(nets)
        total_len = sum(d["len_mm"] for d in nets.values())
        print(f"    {cat}: {n} nets, total routed length {total_len:.2f} mm")
        for net, info in sorted(nets.items()):
            print(f"      {net}: len={info['len_mm']:.3f}mm "
                  f"segs={info['n_segments']} vias={info['n_vias']} "
                  f"layers={info['layers']}")

    print(f"[5] write {OUT_PATH}")
    payload = {
        "_source": PCB_PATH,
        "_summary": {cat: {"n_nets": len(nets),
                            "lens_mm": [round(d["len_mm"], 3) for d in nets.values()]}
                     for cat, nets in by_category.items()},
        "by_category": by_category,
    }
    with open(OUT_PATH, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"    done")


if __name__ == "__main__":
    main()
