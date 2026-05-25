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

Output: ~/novapcb-preview-v1.1/vision/<refdes>_<pad>_<net>/render.png + data.md
"""
import os, json, math
from pathlib import Path
import pcbnew
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon
from matplotlib.lines import Line2D

PCB_PATH = "/home/novatics64/novapcb/hardware/kicad/novapcb-layout-v1.1/novapcb-layout-v1.1.kicad_pcb"
OUT_BASE = Path("/home/novatics64/novapcb-preview-v1.1/vision")
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
    ("R53", "1", "+3V3", 53.0100, 33.0000, ""),
    ("R54", "1", "+3V3", 53.0100, 35.0000, ""),
    ("U1", "100", "+3V3", 35.0000, 27.3250, ""),
    ("C19", "1", "+3V3A", 46.5200, 25.5000, ""),
    ("C20", "1", "+3V3A", 30.0200, 36.0000, ""),
    ("FB1", "2", "+3V3A", 30.5000, 39.0150, ""),
    ("R1", "1", "+3V3A", 51.4900, 28.5000, ""),
    ("U1", "81", "CAN1_RX", 44.5000, 27.3250, ""),
    ("U14", "4", "CAN1_RX", 83.4800, 36.4300, ""),
    ("U1", "82", "CAN1_TX", 44.0000, 27.3250, ""),
    ("U14", "1", "CAN1_TX", 81.5200, 36.4300, ""),
    ("U1", "19", "GND", 33.3250, 38.0000, ""),
    ("U1", "74", "GND", 48.6750, 29.5000, ""),
    ("U1", "84", "GPIO_CAN1_SILENT", 43.0000, 27.3250, ""),
    ("U14", "8", "GPIO_CAN1_SILENT", 81.5200, 33.5700, ""),
    ("D6", "1", "GPS1_RX", 48.5300, 62.4000, ""),
    ("U1", "87", "GPS1_RX", 41.5000, 27.3250, ""),
    ("Q5", "1", "HEATER_PWM", 64.0625, 16.0500, ""),
    ("U1", "31", "HEATER_PWM", 37.5000, 42.6750, ""),
    ("U1", "12", "HSE_IN", 33.3250, 34.5000, ""),
    ("Y1", "1", "HSE_IN", 50.9000, 35.8500, ""),
    ("C25", "1", "HSE_OUT", 51.5200, 38.0000, ""),
    ("U1", "13", "HSE_OUT", 33.3250, 35.0000, ""),
    ("U1", "92", "I2C1_SCL", 39.0000, 27.3250, ""),
    ("U1", "93", "I2C1_SDA", 38.5000, 27.3250, ""),
    ("U1", "9", "IMU1_CS", 33.3250, 33.0000, ""),
    ("U3", "10", "IMU1_CS", 70.4625, 24.7500, ""),
    ("U1", "85", "IMU2_GYR_CS", 42.5000, 27.3250, ""),
    ("U8", "5", "IMU2_GYR_CS", 67.8000, 34.5000, ""),
    ("U1", "5", "IMU2_GYR_INT3", 33.3250, 31.0000, ""),
    ("U8", "12", "IMU2_GYR_INT3", 70.2000, 35.0000, ""),
    ("U1", "1", "IMU3_CS", 33.3250, 29.0000, ""),
    ("U9", "12", "IMU3_CS", 68.5000, 45.9200, ""),
    ("U1", "41", "IMU3_INT1", 42.5000, 42.6750, ""),
    ("U9", "4", "IMU3_INT1", 70.1700, 44.2500, ""),
    ("J11", "1", "MOT1", 32.0000, 3.0000, ""),
    ("U1", "34", "MOT1", 39.0000, 42.6750, ""),
    ("J12", "1", "MOT2", 37.0000, 3.0000, ""),
    ("U1", "35", "MOT2", 39.5000, 42.6750, ""),
    ("J15", "1", "MOT5", 52.0000, 3.0000, ""),
    ("U1", "24", "MOT5", 33.3250, 40.5000, ""),
    ("R51", "2", "SDMMC1_CMD", 29.4900, 33.0000, ""),
    ("U1", "83", "SDMMC1_CMD", 43.5000, 27.3250, ""),
    ("R52", "2", "SDMMC1_D0", 29.4900, 35.0000, ""),
    ("U1", "65", "SDMMC1_D0", 48.6750, 34.0000, ""),
    ("R55", "2", "SDMMC1_D3", 29.4900, 31.0000, ""),
    ("U1", "79", "SDMMC1_D3", 45.5000, 27.3250, ""),
    ("U1", "30", "SPI1_MISO", 37.0000, 42.6750, ""),
    ("U3", "9", "SPI1_MISO", 70.4625, 25.2500, ""),
    ("U1", "88", "SPI1_MOSI", 41.0000, 27.3250, ""),
    ("U3", "12", "SPI1_MOSI", 69.5000, 23.8000, ""),
    ("U1", "29", "SPI1_SCK", 36.5000, 42.6750, ""),
    ("U3", "11", "SPI1_SCK", 70.4625, 24.2500, ""),
    ("U8", "10", "SPI2_MISO", 70.2000, 34.0000, ""),
    ("U1", "90", "SPI3_MISO", 40.0000, 27.3250, ""),
    ("U9", "1", "SPI3_MISO", 70.1700, 45.7500, ""),
    ("U1", "91", "SPI3_MOSI", 39.5000, 27.3250, ""),
    ("U9", "14", "SPI3_MOSI", 69.5000, 45.9200, ""),
    ("U1", "89", "SPI3_SCK", 40.5000, 27.3250, ""),
    ("U9", "13", "SPI3_SCK", 69.0000, 45.9200, ""),
    ("D13", "1", "USART6_TX", 70.5300, 62.4000, ""),
    ("U1", "63", "USART6_TX", 48.6750, 35.0000, ""),
    ("J1", "A5", "USBC_CC1", 38.2500, 61.8050, ""),
    ("R31", "1", "USBC_CC1", 25.9900, 55.0000, ""),
    ("J1", "B5", "USBC_CC2", 41.2500, 61.8050, ""),
    ("R32", "1", "USBC_CC2", 27.9900, 55.0000, ""),
    ("J1", "A7", "USBC_D_M_PRE", 39.7500, 61.8050, ""),
    ("J1", "B7", "USBC_D_M_PRE", 38.7500, 61.8050, ""),
    ("U5", "3", "USBC_D_M_PRE", 30.8625, 55.9500, ""),
    ("J1", "A6", "USBC_D_P_PRE", 39.2500, 61.8050, ""),
    ("J1", "B6", "USBC_D_P_PRE", 40.2500, 61.8050, ""),
    ("U5", "1", "USBC_D_P_PRE", 30.8625, 54.0500, ""),
    ("C17", "1", "VCAP1", 34.5200, 25.5000, ""),
    ("U1", "48", "VCAP1", 46.0000, 42.6750, ""),
    ("C22", "1", "VREF_P", 30.0200, 33.0000, ""),
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
          f"Plane to reach: {net.replace('+3V3A','+3V3')} on {LAYER_NAMES.get(PLANE_LAYER.get(net), 'signal layer')}",
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
        rel = os.path.relpath(img, "/home/novatics64/novapcb-preview-v1.1")
        index.append({"id": f"{fp}.{pad}", "net": net, "pos": [cx, cy], "layer": layer,
                       "render_url": f"http://100.91.55.18:8770/{rel}",
                       "data_url": f"http://100.91.55.18:8770/{rel.replace('render.png','data.md')}"})
        print(f"  [{i+1}/{len(RESIDUALS)}] {fp}.{pad}", flush=True)
    idx_path = OUT_BASE / "index.json"
    idx_path.write_text(json.dumps(index, indent=2))
    print(f"Done. Index at {idx_path}")


if __name__ == "__main__":
    main()
