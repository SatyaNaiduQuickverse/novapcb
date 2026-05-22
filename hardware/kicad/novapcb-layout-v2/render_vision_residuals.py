#!/usr/bin/env python3
"""Render targeted ROIs for the 28 plane-stitch residuals — vision-assisted batch.

Per docs/VISION_ASSISTED_ROUTING.md + master 2026-05-21 dispatch.

For each residual pad, render a 5mm x 5mm ROI centered on the pad at
100 px/mm with:
  - +3V3/+5V/+3V3A/GND traces colour-coded (red/gold/orange/grey)
  - Signal traces blue
  - Plane fills semi-transparent
  - Pad highlighted with crosshair + label
  - Coord data sheet (text) — every pad/via/track in the ROI

Output: ~/novapcb-preview/vision/<refdes>_<pad>_<net>/render.png + data.md
"""
import os, json, math
from pathlib import Path
import pcbnew
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon
from matplotlib.lines import Line2D

PCB_PATH = "/home/novatics64/novapcb/hardware/kicad/novapcb-layout-v2/novapcb-layout-v2.kicad_pcb"
OUT_BASE = Path("/home/novatics64/novapcb-preview/vision")
OUT_BASE.mkdir(parents=True, exist_ok=True)

PX_PER_MM = 120
ROI_RADIUS_MM = 2.5    # 5mm x 5mm window
PLANE_NETS = {"GND", "+3V3", "+3V3A", "+5V"}

LAYER_NAMES = {
    pcbnew.F_Cu: "F.Cu", pcbnew.B_Cu: "B.Cu",
    pcbnew.In1_Cu: "In1.Cu", pcbnew.In2_Cu: "In2.Cu",
    pcbnew.In3_Cu: "In3.Cu", pcbnew.In4_Cu: "In4.Cu",
}
PLANE_LAYER = {"GND": pcbnew.In1_Cu, "+3V3": pcbnew.In2_Cu,
               "+3V3A": pcbnew.In2_Cu, "+5V": pcbnew.In3_Cu}

# Residuals from the run_close_residuals output — 28 entries
RESIDUALS = [
    ("FB1", "2", "+3V3A", 29.6500, 29.5150, "F.Cu"),
    ("C20", "1", "+3V3A", 29.1700, 31.9400, "F.Cu"),
    ("U1", "11", "+3V3", 31.8550, 29.0000, "F.Cu"),
    ("U1", "19", "GND", 31.8550, 33.0000, "F.Cu"),
    ("U1", "21", "+3V3A", 31.8550, 34.0000, "F.Cu"),
    ("U1", "27", "+3V3", 34.0300, 37.6750, "F.Cu"),
    ("U1", "49", "GND", 45.0300, 37.6750, "F.Cu"),
    ("U1", "75", "+3V3", 47.2050, 24.0000, "F.Cu"),
    ("U1", "99", "GND", 34.0300, 22.3250, "F.Cu"),
    ("U1", "100", "+3V3", 33.5300, 22.3250, "F.Cu"),
    ("C24", "2", "GND", 51.3000, 27.1000, "F.Cu"),
    ("C18", "2", "GND", 31.5400, 20.8100, "F.Cu"),
    ("R3", "2", "GND", 30.1600, 24.6800, "F.Cu"),
    ("C23", "2", "GND", 40.0100, 20.8100, "F.Cu"),
    ("U3", "8", "+3V3", 71.1125, 30.7500, "F.Cu"),
    ("C17", "2", "GND", 34.3600, 20.8100, "F.Cu"),
    ("Y1", "2", "GND", 51.9200, 30.8500, "F.Cu"),
    ("C11", "1", "+3V3", 33.4000, 39.1900, "F.Cu"),
    ("C11", "2", "GND", 34.3600, 39.1900, "F.Cu"),
    ("C12", "1", "+3V3", 36.2300, 39.1900, "F.Cu"),
    ("C12", "2", "GND", 37.1900, 39.1900, "F.Cu"),
    ("R53", "1", "+3V3", 47.9600, 26.1300, "B.Cu"),
    ("J2", "3", "GND", 40.1050, 37.7250, "B.Cu"),
    ("J2", "4", "+3V3", 39.0050, 37.7250, "B.Cu"),
    ("J2", "6", "GND", 36.8050, 37.7250, "B.Cu"),
    ("R54", "1", "+3V3", 47.9600, 28.0600, "B.Cu"),
    ("R52", "1", "+3V3", 30.0800, 28.0600, "B.Cu"),
    ("R55", "1", "+3V3", 30.0800, 24.1900, "B.Cu"),
]


def net_color(net):
    if net in ("+3V3", "+3V3A"): return "#ff3030"
    if net == "+5V": return "#ffd700"
    if net == "GND": return "#888888"
    return "#1c8aff"


def plane_color(net):
    return {"GND": "#a0a0a0", "+3V3": "#ff3030", "+5V": "#ffd700"}.get(net, "#888")


def render_residual(brd, fp_ref, pad_num, net, cx, cy, pad_layer):
    xmin, xmax = cx - ROI_RADIUS_MM, cx + ROI_RADIUS_MM
    ymin, ymax = cy - ROI_RADIUS_MM, cy + ROI_RADIUS_MM

    fig, ax = plt.subplots(figsize=(2 * ROI_RADIUS_MM * PX_PER_MM / 100,
                                     2 * ROI_RADIUS_MM * PX_PER_MM / 100),
                            dpi=100)
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymax, ymin)
    ax.set_aspect("equal")
    ax.set_facecolor("#0a0a0a")
    ax.set_title(f"{fp_ref}.{pad_num} ({net}) @ ({cx:.4f}, {cy:.4f}) — {pad_layer} side",
                  fontsize=10, color="white", pad=4)
    ax.set_xticks([round(xmin + 1.0*i, 1) for i in range(int((xmax-xmin)/1.0)+1)])
    ax.set_yticks([round(ymin + 1.0*i, 1) for i in range(int((ymax-ymin)/1.0)+1)])
    ax.tick_params(colors="white", labelsize=6)
    ax.grid(True, color="#202020", linewidth=0.3, alpha=0.5)
    for s in ax.spines.values(): s.set_color("#808080")

    # Plane fill of the pad's target plane (semi-transparent)
    target_plane_layer = PLANE_LAYER.get(net)
    if target_plane_layer is not None:
        for z in brd.Zones():
            if z.GetNetname() != net.replace("+3V3A", "+3V3"): continue
            if not z.IsOnLayer(target_plane_layer): continue
            poly = z.GetFilledPolysList(target_plane_layer)
            for i in range(poly.OutlineCount()):
                ol = poly.Outline(i)
                xs = [ol.CPoint(j).x/1e6 for j in range(ol.PointCount())]
                ys = [ol.CPoint(j).y/1e6 for j in range(ol.PointCount())]
                if not xs: continue
                if max(xs) < xmin or min(xs) > xmax or max(ys) < ymin or min(ys) > ymax:
                    continue
                pts = list(zip(xs, ys))
                ax.add_patch(Polygon(pts, facecolor=plane_color(net.replace("+3V3A","+3V3")),
                                      edgecolor=plane_color(net.replace("+3V3A","+3V3")),
                                      alpha=0.35, linewidth=0.3, zorder=1))

    # Pads (on F.Cu/B.Cu only — for ROI clarity)
    for fp in brd.GetFootprints():
        for pad in fp.Pads():
            if not (pad.IsOnLayer(pcbnew.F_Cu) or pad.IsOnLayer(pcbnew.B_Cu)): continue
            bb = pad.GetBoundingBox()
            x = (bb.GetX() + bb.GetWidth()//2) / 1e6
            y = (bb.GetY() + bb.GetHeight()//2) / 1e6
            if not (xmin-0.5 <= x <= xmax+0.5 and ymin-0.5 <= y <= ymax+0.5): continue
            w, h = bb.GetWidth()/1e6, bb.GetHeight()/1e6
            net_p = pad.GetNet().GetNetname() if pad.GetNet() else ""
            color = "#ffd040" if net_p in PLANE_NETS else "#cccccc"
            zorder = 7 if pad.IsOnLayer(pcbnew.F_Cu) else 6
            ax.add_patch(Rectangle((x-w/2, y-h/2), w, h, facecolor=color,
                                    edgecolor="#ffffff", linewidth=0.2,
                                    alpha=0.95, zorder=zorder))
            ax.annotate(f"{fp.GetReference()}.{pad.GetNumber()}", (x, y),
                         fontsize=4, color="#000000", ha="center", va="center", zorder=8)

    # Tracks
    for t in brd.GetTracks():
        if isinstance(t, pcbnew.PCB_VIA): continue
        if not t.GetLayer() in (pcbnew.F_Cu, pcbnew.B_Cu): continue
        s, e = t.GetStart(), t.GetEnd()
        sx, sy = s.x/1e6, s.y/1e6
        ex, ey = e.x/1e6, e.y/1e6
        if not (xmin-0.2 <= max(sx,ex) and min(sx,ex) <= xmax+0.2 and
                ymin-0.2 <= max(sy,ey) and min(sy,ey) <= ymax+0.2): continue
        net_t = t.GetNet().GetNetname() if t.GetNet() else ""
        col = net_color(net_t)
        w = t.GetWidth()/1e6
        L = "F" if t.GetLayer() == pcbnew.F_Cu else "B"
        linestyle = "-" if L == "F" else "--"
        ax.plot([sx, ex], [sy, ey], color=col, linewidth=max(0.8, w * PX_PER_MM * 0.072),
                solid_capstyle="round", linestyle=linestyle, alpha=0.85, zorder=5)

    # Vias
    for t in brd.GetTracks():
        if not isinstance(t, pcbnew.PCB_VIA): continue
        p = t.GetPosition()
        x, y = p.x/1e6, p.y/1e6
        if not (xmin-0.3 <= x <= xmax+0.3 and ymin-0.3 <= y <= ymax+0.3): continue
        outer = t.GetWidth()/2/1e6
        drill = t.GetDrill()/2/1e6
        net_v = t.GetNet().GetNetname() if t.GetNet() else ""
        edge = net_color(net_v) if net_v in PLANE_NETS else "#00d040"
        ax.add_patch(Circle((x,y), outer, facecolor="#202020", edgecolor=edge,
                            linewidth=0.5, zorder=9))
        ax.add_patch(Circle((x,y), drill, facecolor="#000000", edgecolor="none", zorder=10))

    # Crosshair on target pad
    ax.plot(cx, cy, marker="+", color="#ffffff", markersize=20,
            markeredgewidth=1.5, zorder=15)
    ax.plot(cx, cy, marker="o", color="#ffffff", markersize=12,
            markerfacecolor="none", markeredgewidth=1.0, zorder=15)
    ax.annotate(f"{fp_ref}.{pad_num}", (cx, cy), xytext=(8, -8),
                 textcoords="offset points", fontsize=6, color="white",
                 bbox=dict(boxstyle="round,pad=0.2", facecolor="#000",
                           edgecolor="#ffffff", alpha=0.85), zorder=16)

    # Legend
    handles = [
        Line2D([0],[0], color="#ff3030", linewidth=2, label="+3V3/+3V3A"),
        Line2D([0],[0], color="#ffd700", linewidth=2, label="+5V"),
        Line2D([0],[0], color="#888888", linewidth=2, label="GND"),
        Line2D([0],[0], color="#1c8aff", linewidth=2, label="signal"),
        Line2D([0],[0], color="#1c8aff", linewidth=2, linestyle="--", label="(B.Cu)"),
        Line2D([0],[0], color="#ffd040", marker="s", linewidth=0, markersize=6, label="plane pad"),
        Line2D([0],[0], color="#00d040", marker="o", linewidth=0, markersize=6,
                markerfacecolor="none", label="via"),
        Line2D([0],[0], color="#ffffff", marker="+", linewidth=0, markersize=10, label="target pad"),
    ]
    ax.legend(handles=handles, loc="lower left", fontsize=5, framealpha=0.85,
              facecolor="#000", edgecolor="#808080", labelcolor="white")
    fig.patch.set_facecolor("#000")
    fig.tight_layout(pad=0.3)

    out_dir = OUT_BASE / f"{fp_ref}_{pad_num}_{net.replace('+','p')}"
    out_dir.mkdir(parents=True, exist_ok=True)
    img_path = out_dir / "render.png"
    fig.savefig(img_path, dpi=100, facecolor=fig.get_facecolor())
    plt.close(fig)

    # Coord data sheet
    md = [f"# {fp_ref}.{pad_num} ({net}) plane-stitch residual\n",
          f"ROI: X={xmin:.3f}..{xmax:.3f}, Y={ymin:.3f}..{ymax:.3f} mm",
          f"Pad center: ({cx:.4f}, {cy:.4f}) on {pad_layer}",
          f"Plane to reach: {net.replace('+3V3A','+3V3')} on {LAYER_NAMES[PLANE_LAYER[net]]}",
          "",
          "## Pads in ROI",
          "| Refdes | (x, y) | size | layer | net |",
          "|---|---|---|---|---|"]
    for fp in brd.GetFootprints():
        for pad in fp.Pads():
            bb = pad.GetBoundingBox()
            x = (bb.GetX() + bb.GetWidth()//2) / 1e6
            y = (bb.GetY() + bb.GetHeight()//2) / 1e6
            if not (xmin <= x <= xmax and ymin <= y <= ymax): continue
            w, h = bb.GetWidth()/1e6, bb.GetHeight()/1e6
            net_p = pad.GetNet().GetNetname() if pad.GetNet() else ""
            L = "F.Cu" if pad.IsOnLayer(pcbnew.F_Cu) else ("B.Cu" if pad.IsOnLayer(pcbnew.B_Cu) else "TH")
            md.append(f"| {fp.GetReference()}.{pad.GetNumber()} | ({x:.4f}, {y:.4f}) | {w:.3f}x{h:.3f} | {L} | {net_p} |")
    md.append("\n## Tracks in ROI (any endpoint inside)")
    md.append("| layer | start | end | length | net |")
    md.append("|---|---|---|---|---|")
    for t in brd.GetTracks():
        if isinstance(t, pcbnew.PCB_VIA): continue
        s, e = t.GetStart(), t.GetEnd()
        sx, sy = s.x/1e6, s.y/1e6
        ex, ey = e.x/1e6, e.y/1e6
        if not ((xmin <= sx <= xmax and ymin <= sy <= ymax) or
                (xmin <= ex <= xmax and ymin <= ey <= ymax)): continue
        L = LAYER_NAMES.get(t.GetLayer(), f"L{t.GetLayer()}")
        net_t = t.GetNet().GetNetname() if t.GetNet() else ""
        length = math.hypot(ex-sx, ey-sy)
        md.append(f"| {L} | ({sx:.4f},{sy:.4f}) | ({ex:.4f},{ey:.4f}) | {length:.3f} | {net_t} |")
    md.append("\n## Vias in ROI")
    md.append("| (x, y) | net | outer/drill |")
    md.append("|---|---|---|")
    for t in brd.GetTracks():
        if not isinstance(t, pcbnew.PCB_VIA): continue
        p = t.GetPosition()
        x, y = p.x/1e6, p.y/1e6
        if not (xmin <= x <= xmax and ymin <= y <= ymax): continue
        net_v = t.GetNet().GetNetname() if t.GetNet() else ""
        md.append(f"| ({x:.4f},{y:.4f}) | {net_v} | {t.GetWidth()/1e6:.2f}/{t.GetDrill()/1e6:.2f} |")

    data_path = out_dir / "data.md"
    data_path.write_text("\n".join(md))
    return str(img_path), str(data_path)


def main():
    brd = pcbnew.LoadBoard(PCB_PATH)
    index = []
    print(f"Rendering {len(RESIDUALS)} vision residuals...", flush=True)
    for i, (fp, pad, net, cx, cy, layer) in enumerate(RESIDUALS):
        img, data = render_residual(brd, fp, pad, net, cx, cy, layer)
        rel = os.path.relpath(img, "/home/novatics64/novapcb-preview")
        index.append({"id": f"{fp}.{pad}", "net": net, "pos": [cx, cy], "layer": layer,
                       "render_url": f"http://100.91.55.18:8770/{rel}",
                       "data_url": f"http://100.91.55.18:8770/{rel.replace('render.png','data.md')}"})
        print(f"  [{i+1}/{len(RESIDUALS)}] {fp}.{pad}", flush=True)
    idx_path = OUT_BASE / "index.json"
    idx_path.write_text(json.dumps(index, indent=2))
    print(f"Done. Index at {idx_path}")


if __name__ == "__main__":
    main()
