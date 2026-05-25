#!/usr/bin/env python3
"""Step 2: cluster-close plane pads via shared via + short traces from each pad.

Per master 2026-05-21:
  - One shared via per power-pad cluster (in clearest nearby spot)
  - Short ADD-only traces from cluster pads to the shared via
  - For 4 GND: trace direct to F.Cu/B.Cu GND pour edge
  - All ADD-only, DRC-verify per addition, revert any new error

Clusters defined manually based on pad geometry (small distance between pads).
"""
import os, sys, math, json, subprocess, re
import pcbnew

PCB = "/home/novatics64/novapcb/hardware/kicad/novapcb-layout-v2/novapcb-layout-v2.kicad_pcb"

# Cluster definitions: (cluster_name, pads_list, target_via_pos_search_center, layer)
# Each pad: (refdes, pad_num, net_name, x, y)
CLUSTERS = [
    # F.Cu +3V3 cluster 1: C11.1, C12.1, C15.1 (Y=39.19 cap row)
    ("F1_cap_row_pair", [
        ("C11", "1", "+3V3", 33.40, 39.19),
        ("C12", "1", "+3V3", 36.23, 39.19),
    ], (34.815, 39.19 - 1.0), "F.Cu"),   # mid-X between C11/C12, south
    ("F1_cap_C15", [
        ("C15", "1", "+3V3", 44.70, 39.19),
    ], (44.70, 39.19 - 1.0), "F.Cu"),
    # F.Cu +3V3 cluster 2: U1.27 + U1.50 (Y=37.67)
    ("F2_U1_S_pair", [
        ("U1", "27", "+3V3", 34.03, 37.675),
        ("U1", "50", "+3V3", 45.53, 37.675),
    ], (39.78, 37.675 + 1.5), "F.Cu"),   # mid-X between, south
    # F.Cu +3V3 cluster 3: U1.11, U1.100, U1.75
    ("F3_U1_N", [
        ("U1", "11", "+3V3", 31.855, 29.00),
        ("U1", "100", "+3V3", 33.53, 22.325),
        ("U1", "75", "+3V3", 47.205, 24.00),
    ], (35.0, 26.0), "F.Cu"),  # rough center
    # B.Cu +3V3 cluster: R51/R53/R54/R55 + J2.4
    ("B1_R_west", [
        ("R51", "1", "+3V3", 30.08, 26.13),
        ("R55", "1", "+3V3", 30.08, 24.19),
    ], (30.08 - 1.0, 25.16), "B.Cu"),
    ("B1_R_east", [
        ("R53", "1", "+3V3", 47.96, 26.13),
        ("R54", "1", "+3V3", 47.96, 28.06),
    ], (47.96 + 1.0, 27.1), "B.Cu"),
    ("B2_J2_4", [
        ("J2", "4", "+3V3", 39.005, 37.725),
    ], (39.005, 37.725 - 1.0), "B.Cu"),
    # Singletons
    ("U3_8", [
        ("U3", "8", "+3V3", 71.1125, 30.75),
    ], (71.1125 - 1.0, 30.75), "F.Cu"),
    # +3V3A
    ("3V3A_C19_1", [
        ("C19", "1", "+3V3A", 44.70, 20.81),
    ], (44.70, 20.81 - 1.0), "F.Cu"),
    ("3V3A_FB1_2", [
        ("FB1", "2", "+3V3A", 29.65, 29.515),
    ], (29.65 - 1.0, 29.515), "F.Cu"),
    ("3V3A_R1_1", [
        ("R1", "1", "+3V3A", 65.37, 21.29),
    ], (65.37, 21.29 + 1.0), "F.Cu"),
    # +5V
    ("5V_J1_A9", [
        ("J1", "A9", "+5V", 47.45, 52.085),
    ], (47.45 - 1.0, 52.085 - 0.6), "F.Cu"),  # offset toward already-placed dupe via area
    ("5V_U5_5", [
        ("U5", "5", "+5V", 50.0775, 48.39),
    ], (50.0775 + 0.8, 48.39), "F.Cu"),
]

# Direct-to-pour for 4 GND
GND_PADS = [
    ("C43", "2", 51.30, 35.81, "F.Cu"),
    ("U1", "19", 31.855, 33.00, "F.Cu"),
    ("U1", "49", 45.03, 37.675, "F.Cu"),
    ("Y1", "2", 51.92, 30.85, "F.Cu"),    # crystal — shortest!
]


def drc_count():
    subprocess.run(["kicad-cli","pcb","drc","--severity-all","--format","report",
                    "--output","/tmp/dru.txt","--units","mm",PCB], capture_output=True)
    t = open("/tmp/dru.txt").read()
    e = int(re.search(r"Found (\d+) DRC violation", t).group(1)) if re.search(r"Found \d+ DRC", t) else 0
    u = int(re.search(r"Found (\d+) unconnected", t).group(1)) if re.search(r"Found \d+ unconnected", t) else 0
    return e, u


def add_via(brd, x, y, net):
    v = pcbnew.PCB_VIA(brd)
    v.SetPosition(pcbnew.VECTOR2I(int(x*1e6), int(y*1e6)))
    v.SetWidth(int(0.46*1e6))
    v.SetDrill(int(0.20*1e6))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetNet(net)
    brd.Add(v)
    return v


def add_track(brd, x1, y1, x2, y2, net, layer, w=0.20):
    t = pcbnew.PCB_TRACK(brd)
    t.SetStart(pcbnew.VECTOR2I(int(x1*1e6), int(y1*1e6)))
    t.SetEnd(pcbnew.VECTOR2I(int(x2*1e6), int(y2*1e6)))
    t.SetWidth(int(w*1e6))
    t.SetLayer(layer)
    t.SetNet(net)
    brd.Add(t)
    return t


def find_pour_edge(brd, layer, pcx, pcy, max_r=5.0):
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
                d = math.hypot(x-pcx, y-pcy)
                if d < closest_d:
                    closest_d = d; closest = (x, y)
        return closest
    return None


def try_shared_via_and_traces(brd, nets, cluster_name, pads, center, layer):
    """Try placing one shared via at center area + traces from each pad.
    Returns count of pads connected (0 if cluster fails completely)."""
    if not pads: return 0
    net_name = pads[0][2]
    net = nets[net_name]
    layer_id = pcbnew.F_Cu if layer == "F.Cu" else pcbnew.B_Cu
    # Search for clear via spot near center
    base_e, base_u = drc_count()
    cx, cy = center
    via_obj = None
    via_pos = None
    for r in [0.0, 0.5, 0.8, 1.0, 1.3, 1.6, 2.0]:
        for ang_deg in (0, 90, 180, -90, 45, -45, 135, -135):
            ang = math.radians(ang_deg)
            vx, vy = cx + r*math.cos(ang), cy + r*math.sin(ang)
            v = add_via(brd, vx, vy, net)
            pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
            pcbnew.SaveBoard(PCB, brd)
            e, u = drc_count()
            if e <= base_e:
                via_obj = v
                via_pos = (vx, vy)
                base_e = e
                break
            brd.Remove(v)
            pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
            pcbnew.SaveBoard(PCB, brd)
        if via_obj: break

    if via_obj is None:
        return 0, []

    # For each pad in cluster, try trace to via
    connected = []
    for ref, pad, net_name, pcx, pcy in pads:
        vx, vy = via_pos
        # Try straight, then L
        for traces_to_add in [
            [(pcx, pcy, vx, vy)],
            [(pcx, pcy, pcx, vy), (pcx, vy, vx, vy)],
            [(pcx, pcy, vx, pcy), (vx, pcy, vx, vy)],
        ]:
            added = []
            for t in traces_to_add:
                tk = add_track(brd, t[0], t[1], t[2], t[3], net, layer_id)
                added.append(tk)
            pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
            pcbnew.SaveBoard(PCB, brd)
            e, u = drc_count()
            if e <= base_e:
                connected.append((ref, pad))
                base_e = e
                break
            for tk in added: brd.Remove(tk)
            pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
            pcbnew.SaveBoard(PCB, brd)

    if not connected:
        # Remove the via if nothing connected to it
        brd.Remove(via_obj)
        pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
        pcbnew.SaveBoard(PCB, brd)
        return 0, []
    return len(connected), connected


def try_gnd_pour_trace(brd, nets, ref, pad_num, pcx, pcy, layer):
    """Short trace from GND pad to nearest F.Cu/B.Cu GND pour edge."""
    layer_id = pcbnew.F_Cu if layer == "F.Cu" else pcbnew.B_Cu
    net = nets["GND"]
    base_e, base_u = drc_count()
    edge = find_pour_edge(brd, layer_id, pcx, pcy, max_r=5.0)
    if not edge:
        return False
    ex, ey = edge
    for traces_to_add in [
        [(pcx, pcy, ex, ey)],
        [(pcx, pcy, pcx, ey), (pcx, ey, ex, ey)],
        [(pcx, pcy, ex, pcy), (ex, pcy, ex, ey)],
    ]:
        added = []
        for t in traces_to_add:
            tk = add_track(brd, t[0], t[1], t[2], t[3], net, layer_id)
            added.append(tk)
        pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
        pcbnew.SaveBoard(PCB, brd)
        e, u = drc_count()
        if e <= base_e:
            return True
        for tk in added: brd.Remove(tk)
        pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
        pcbnew.SaveBoard(PCB, brd)
    return False


def main():
    brd = pcbnew.LoadBoard(PCB)
    nets = {str(k): v for k, v in brd.GetNetsByName().asdict().items()}
    base_e, base_u = drc_count()
    print(f"baseline: {base_e} err, {base_u} unconn\n")

    total_closed = 0
    cluster_results = []
    for name, pads, center, layer in CLUSTERS:
        n_conn, connected = try_shared_via_and_traces(brd, nets, name, pads, center, layer)
        print(f"  {name}: {n_conn}/{len(pads)} connected (target was {[p[0]+'.'+p[1] for p in pads]})")
        cluster_results.append({"cluster": name, "connected": n_conn, "total": len(pads)})
        total_closed += n_conn
        brd = pcbnew.LoadBoard(PCB)

    # GND pour traces
    print("\nGND pour traces:")
    gnd_results = []
    for ref, pad, pcx, pcy, layer in GND_PADS:
        ok = try_gnd_pour_trace(brd, nets, ref, pad, pcx, pcy, layer)
        print(f"  {ref}.{pad}: {'✓' if ok else '✗'}")
        gnd_results.append({"ref": ref, "pad": pad, "connected": ok})
        if ok: total_closed += 1
        brd = pcbnew.LoadBoard(PCB)

    print(f"\nTotal closed this pass: {total_closed}")
    e, u = drc_count()
    print(f"Final DRC: {e} errors, {u} unconnected")

    json.dump({"clusters": cluster_results, "gnd": gnd_results,
               "total_closed": total_closed, "final_err": e, "final_unc": u},
               open("cluster_close_result.json", "w"), indent=2)


if __name__ == "__main__":
    main()
