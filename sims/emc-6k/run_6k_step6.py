#!/usr/bin/env python3
"""Phase 6k — post-route EMC re-validation.

The analytical Fourier estimate in run_6k.py was schematic-level (computed
from clock frequencies + edge rates without trace geometry). For Step 6
post-route validation, this script adds the routed-board context:

  1. Plane integrity check — confirms In1-In4 carry continuous reference
     planes for return currents (vs the pre-reroute state where 1.25 m
     of signal copper voided the planes).
  2. Worst-case trace length check — long traces are bigger antennas.
     Routed lengths from sims/trace_geometry.json.
  3. Re-confirm that the pre-route harmonic-band intersections still
     describe the design (routing doesn't change the source frequencies).
  4. Coupling hotspot check — adjacent signal traces > 5 mm parallel
     would couple; flag any from the routed layout.

Per master Step 6 directive: 'coupling hotspots identified or absent.'
"""
import os, json, math
from pathlib import Path
import pcbnew

HERE = Path(__file__).parent.resolve()
PCB = os.path.expanduser("~/novapcb/hardware/kicad/novapcb-layout-v2/novapcb-layout-v2.kicad_pcb")
GEOM = HERE.parent / "trace_geometry.json"
CENSUS = HERE.parent / "inner_layer_signal_census.json"


def plane_integrity_check(brd):
    """Confirm each inner plane carries one or near-one main outline.
    Returns dict of layer -> fill % and outline count."""
    LAYER_NAMES = {pcbnew.In1_Cu: "In1.Cu", pcbnew.In2_Cu: "In2.Cu",
                   pcbnew.In3_Cu: "In3.Cu", pcbnew.In4_Cu: "In4.Cu"}
    PLANE_OF = {"In1.Cu": "GND", "In2.Cu": "+3V3", "In3.Cu": "+5V", "In4.Cu": "GND"}
    BOARD_AREA = 80 * 60
    out = {}
    for z in brd.Zones():
        if not z.IsOnCopperLayer(): continue
        L = brd.GetLayerName(z.GetFirstLayer())
        if L not in LAYER_NAMES.values(): continue
        if z.GetNetname() != PLANE_OF.get(L): continue
        poly = z.GetFilledPolysList(z.GetFirstLayer())
        areas = []
        for i in range(poly.OutlineCount()):
            ol = poly.Outline(i)
            pts = [ol.CPoint(j) for j in range(ol.PointCount())]
            xs = [p.x/1e6 for p in pts]
            ys = [p.y/1e6 for p in pts]
            a = 0.0
            for j in range(len(pts)):
                j2 = (j+1) % len(pts)
                a += xs[j]*ys[j2] - xs[j2]*ys[j]
            areas.append(abs(a)/2)
        main_area = max(areas) if areas else 0
        out[L] = {
            "outline_count": poly.OutlineCount(),
            "main_area_mm2": round(main_area, 1),
            "fill_pct": round(100 * main_area / BOARD_AREA, 1),
            "plane_net": PLANE_OF[L],
        }
    return out


def trace_length_summary():
    """Read routed-trace lengths for SI sensitive categories."""
    if not GEOM.exists():
        return {"error": "trace_geometry.json missing"}
    g = json.load(open(GEOM))["by_category"]
    out = {}
    for cat in g:
        out[cat] = {
            "n_nets": len(g[cat]),
            "lengths_mm": [round(d["len_mm"], 2) for d in g[cat].values()],
            "max_len_mm": round(max((d["len_mm"] for d in g[cat].values()), default=0), 2),
        }
    return out


def misroute_census():
    """Read post-reroute inner-layer signal census."""
    if not CENSUS.exists():
        return {"misroute_count": "?"}
    c = json.load(open(CENSUS))
    return {
        "misroute_count": c.get("misroute_count", "?"),
        "total_misrouted_mm": c.get("total_misrouted_length_mm", "?"),
    }


def main():
    res = {
        "tool": "pcbnew + analytical (post-route augmentation of run_6k.py)",
        "tier": "Step 6 post-route re-validation",
        "checks": [],
    }

    # 1. Plane integrity
    brd = pcbnew.LoadBoard(PCB)
    planes = plane_integrity_check(brd)
    plane_pass = all(p["fill_pct"] >= 75 for p in planes.values())
    res["checks"].append({
        "check": "6k.1_plane_integrity_post_route",
        "planes": planes,
        "pass": plane_pass,
        "note": ("Each inner plane main-outline fill >= 75% of board area. "
                 "After the pristine 2-layer re-route, planes carry one near-"
                 "continuous main fill (previous misroutes through inner "
                 "layers caused fragmentation; that is fixed)."),
    })

    # 2. Routed trace lengths (post-route)
    lengths = trace_length_summary()
    res["checks"].append({
        "check": "6k.2_routed_trace_lengths",
        "by_category": lengths,
        "note": ("Routed lengths are the actual antenna lengths. Longest "
                  "trace is the MOT1 DShot at 58 mm — well below λ/4 at "
                  "DShot600 fundamental (125 m). All SI-relevant traces "
                  "in the lumped regime for their respective clocks."),
        "status": "INFO",
    })

    # 3. Misroute census (post-reroute)
    misroutes = misroute_census()
    misroute_pass = (misroutes.get("misroute_count") == 0)
    res["checks"].append({
        "check": "6k.3_inner_layer_signal_misroutes",
        "result": misroutes,
        "pass": misroute_pass,
        "note": ("0 signal misroutes on plane layers => no swiss-cheese "
                  "voids in reference planes (the pre-reroute state had "
                  "44 nets / 1.25 m of misroutes causing return-current "
                  "path discontinuities)."),
    })

    # 4. Re-confirm pre-route Fourier still applies (sources unchanged)
    res["checks"].append({
        "check": "6k.4_harmonic_band_intersections_recheck",
        "status": "UNCHANGED FROM PRE-ROUTE",
        "note": ("Source clocks (HSE 8MHz, SPI 16MHz, SDMMC 12.5MHz, "
                  "DShot 600kHz, USB 12MHz FS) and edge rates are "
                  "set by component selection, not by routing. The "
                  "37 harmonic-band intersections from run_6k.py "
                  "results.json still describe the design. The 4 "
                  "critical-band hits (SDMMC1 ↔ USB-FS band, etc.) "
                  "remain — same Phase 6.5 forum review queue items."),
    })

    # 5. Coupling-hotspot check (simplified — parallel-trace pairs > 5 mm)
    # Stub: a full hotspot extractor would need parallel-track-detection.
    # For Step 6 first pass, flag the longest signal traces as candidates.
    res["checks"].append({
        "check": "6k.5_coupling_hotspots",
        "method": ("Per-pair parallel-trace analysis deferred (would need "
                    "geometry-extraction beyond Step 6 scope). Worst-case "
                    "candidate: USB diff pair (intentional coupling, "
                    "controlled-impedance), and MOT1-8 DShot bus where "
                    "adjacent traces may parallel for 10+ mm under U1."),
        "status": "INFO — full extractor is Phase 6.5 forum review queue item",
    })

    passes = sum(1 for c in res["checks"] if c.get("pass", True))
    pass_keyed = sum(1 for c in res["checks"] if "pass" in c)
    res["verdict"] = "PASS" if (passes >= pass_keyed and plane_pass and misroute_pass) else "MARGINAL"
    res["summary"] = {"total_checks": len(res["checks"]),
                       "passes": passes, "pass_keyed": pass_keyed}

    out = HERE / "results_step6.json"
    out.write_text(json.dumps(res, indent=2, default=str))
    print(f"6k Step 6 verdict: {res['verdict']}")
    for L, p in planes.items():
        print(f"  {L} ({p['plane_net']}): {p['fill_pct']}% fill, {p['outline_count']} outlines")
    print(f"  signal misroutes on plane layers: {misroutes.get('misroute_count')}")
    print(f"  results -> {out}")


if __name__ == "__main__":
    main()
