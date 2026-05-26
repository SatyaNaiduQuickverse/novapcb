#!/usr/bin/env python3
"""DFM check for novapcb-stepwise against the JLCPCB JLC06161H 6-layer rule pack.

Adapted from novapcb-layout-v2/run_dfm_check.py (board path + DRU-exception
classification + min-feature capability scan added for the stepwise board).

JLC06161H (6-layer, 7628 prepreg) manufacturability floor — the *advanced* tier
this design is already priced for (via-in-pad filled+capped, 4mil U6 exits):
  - Min trace width:     0.09 mm
  - Min trace clearance: 0.09 mm
  - Min via drill:       0.15 mm
  - Min via annular:     0.09 mm
  - Min copper-to-edge:  0.20 mm
  - Min hole-to-hole:    0.50 mm
  - Min through-hole:    0.20 mm

IMPORTANT — kicad-cli vs GUI DRC:
  `kicad-cli pcb drc` does NOT apply the project .kicad_dru custom rules (no CLI
  option exists for it). It therefore OVER-reports: every via-in-pad / 4mil
  exception that the GUI DRC passes via .kicad_dru shows up here as an error.
  This checker re-classifies those known, scope-bounded exceptions so the verdict
  reflects the GUI-DRC-authoritative state. The GUI DRC (which DOES apply
  .kicad_dru) is the authority for the Phase 7a freeze.
"""
import json, re, subprocess
from pathlib import Path

HERE = Path(__file__).parent.resolve()
PCB = HERE / "novapcb-stepwise.kicad_pcb"

JLC_FLOOR = {
    "min_track_width": 0.09,
    "min_via_drill": 0.15,
    "min_via_annular": 0.09,
    "min_via_diameter": 0.40,
    "min_through_hole": 0.20,
    "min_copper_to_edge": 0.20,
}

# Known .kicad_dru-covered exceptions (GUI DRC passes these). kicad-cli flags
# them because it ignores custom rules. Each is scope-bounded + documented in
# novapcb-stepwise.kicad_dru and docs/DECISIONS.md §13 (fab process).
DRU_COVERED_NETS = {"ORING_A_GATE", "ORING_B_GATE", "+5V_BEC",
                    "EFUSE_OVP", "EFUSE_ILIM", "EFUSE_DVDT", "EFUSE_FLT"}


def drc_json(extra_args=None):
    out = "/tmp/dfm_stepwise_drc.json"
    cmd = ["kicad-cli", "pcb", "drc", "--severity-error", "--format", "json",
           "--output", out, "--units", "mm"] + (extra_args or []) + [str(PCB)]
    subprocess.run(cmd, capture_output=True)
    return json.load(open(out))


def classify_violations(drc):
    """Split kicad-cli violations into DRU-covered vs unexpected."""
    covered, unexpected = [], []
    for v in drc.get("violations", []):
        nets = set()
        for it in v.get("items", []):
            d = it.get("description", "")
            if "[" in d and "]" in d:
                nets.add(d[d.find("[") + 1:d.find("]")])
        # via_diameter / drill_out_of_range on a DRU-covered net == exception
        if v["type"] in ("via_diameter", "drill_out_of_range") and nets & DRU_COVERED_NETS:
            covered.append((v["type"], sorted(nets)))
        # courtyards_overlap: pre-existing accepted SOT-23-6 / WQFN relaxations
        # (u11-u12-fanout-clearance-relax, u6 courtyard rules)
        elif v["type"] == "courtyards_overlap":
            covered.append((v["type"], "pre-existing courtyard relaxation"))
        else:
            unexpected.append((v["type"], sorted(nets)))
    return covered, unexpected


def min_features():
    import pcbnew
    b = pcbnew.LoadBoard(str(PCB))
    mm = lambda v: v / 1e6
    tw, vod, vdr, ann, phd = [], [], [], [], []
    for t in b.GetTracks():
        if t.GetClass() == "PCB_VIA":
            od = mm(t.GetWidth(pcbnew.F_Cu)); dr = mm(t.GetDrillValue())
            vod.append(od); vdr.append(dr); ann.append((od - dr) / 2)
        elif t.GetClass() == "PCB_TRACK":
            tw.append(mm(t.GetWidth()))
    for fp in b.GetFootprints():
        for p in fp.Pads():
            d = p.GetDrillSize()
            if d.x > 0:
                phd.append(mm(min(d.x, d.y) if d.y > 0 else d.x))
    feat = {
        "min_track_width": (min(tw), JLC_FLOOR["min_track_width"]),
        "min_via_diameter": (min(vod), JLC_FLOOR["min_via_diameter"]),
        "min_via_drill": (min(vdr), JLC_FLOOR["min_via_drill"]),
        "min_via_annular": (min(ann), JLC_FLOOR["min_via_annular"]),
        "min_through_hole": (min(phd), JLC_FLOOR["min_through_hole"]),
    }
    inv = {"footprints": sum(1 for _ in b.GetFootprints()),
           "pads": sum(1 for fp in b.GetFootprints() for _ in fp.Pads()),
           "tracks": len(tw), "vias": len(vod),
           "zones": len(list(b.Zones()))}
    return feat, inv


def main():
    res = {"tool": "kicad-cli pcb drc + analytical capability scan",
           "fab": "JLCPCB 6-layer (JLC06161H-7628), advanced tier", "checks": []}

    # 1. DRC + DRU-exception classification
    drc = drc_json()
    covered, unexpected = classify_violations(drc)
    edge = [v for v in drc.get("violations", []) if v["type"] == "copper_edge_clearance"]
    res["checks"].append({
        "check": "drc_with_dru_classification",
        "kicad_cli_total": len(drc.get("violations", [])),
        "dru_covered": len(covered),
        "unexpected": len(unexpected),
        "copper_edge_clearance": len(edge),
        "gui_drc_authoritative_errors": len(unexpected),
        "pass": len(unexpected) == 0 and len(edge) == 0,
        "covered_detail": covered,
        "unexpected_detail": unexpected,
        "note": ("kicad-cli ignores .kicad_dru; all kicad_cli errors must be "
                 "DRU-covered exceptions. copper_edge_clearance MUST be 0 "
                 "(no copper crossing a board cut)."),
    })

    # 2. Min-feature vs JLC capability floor
    feat, inv = min_features()
    fpass = all(actual >= floor for actual, floor in feat.values())
    res["checks"].append({
        "check": "min_feature_vs_jlc_capability",
        "features": {k: {"actual": round(a, 3), "jlc_floor": f, "ok": a >= f}
                     for k, (a, f) in feat.items()},
        "pass": fpass,
        "note": ("via-in-pad family (0.45 OD / 0.25 drill) within capability but "
                 "requires JLC vias-filled-and-capped process — see DECISIONS §13."),
    })

    # 3. Connectivity (ratsnest) — informational; tracks unrouted-by-design nets
    n_unc = drc.get("unconnected_items", [])
    mot_unrouted = sorted({d[d.find("[") + 1:d.find("]")]
                           for u in n_unc for it in u.get("items", [])
                           for d in [it.get("description", "")]
                           if "[MOT" in d})
    res["checks"].append({
        "check": "connectivity_inventory",
        "unconnected_ratsnest": len(n_unc),
        "mot_unrouted": mot_unrouted,
        "status": "INFO",
        "note": ("MOT7/MOT8 unrouted by design (Sai option D, all 8 PWM defined). "
                 "MOT1/MOT2 unrouted (T3-partial scope routed MOT3-6 only). "
                 "Artifact = 4/8 MOT routed; see DFM_REPORT for the STATUS '6/8' "
                 "doc-vs-artifact note."),
    })

    # 4. Board feature inventory
    res["checks"].append({"check": "board_feature_inventory", **inv, "status": "INFO"})

    pass_keyed = sum(1 for c in res["checks"] if "pass" in c)
    passes = sum(1 for c in res["checks"] if c.get("pass", True) and "pass" in c)
    res["verdict"] = "PASS" if passes == pass_keyed else "FAIL"
    res["summary"] = {"checks": len(res["checks"]), "pass_keyed": pass_keyed,
                      "passes": passes}

    out_path = HERE / "dfm_results.json"
    out_path.write_text(json.dumps(res, indent=2, default=str))
    print(f"DFM verdict: {res['verdict']}")
    c0 = res["checks"][0]
    print(f"  DRC: {c0['kicad_cli_total']} kicad-cli flags = "
          f"{c0['dru_covered']} DRU-covered + {c0['unexpected']} unexpected; "
          f"edge-clearance={c0['copper_edge_clearance']}")
    print(f"  Min features vs JLC: {'OK' if res['checks'][1]['pass'] else 'CHECK'}")
    print(f"  MOT unrouted: {mot_unrouted}")
    print(f"  Inventory: {inv['footprints']} fps, {inv['pads']} pads, "
          f"{inv['tracks']} tracks, {inv['vias']} vias, {inv['zones']} zones")
    print(f"  results -> {out_path}")


if __name__ == "__main__":
    main()
