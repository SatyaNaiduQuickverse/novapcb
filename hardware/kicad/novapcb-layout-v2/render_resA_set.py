#!/usr/bin/env python3
"""Render high-res per-layer set for the resA vision pass.

Per master 2026-05-21 directive: current 31.7 px/mm composite render is
insufficient (0.1mm trace = 4 px). Need:
  - Tight ROI: X=67.5..72.0, Y=29.0..34.0 mm (~4.5x5 mm)
  - >=100 px/mm
  - 3 SEPARATE per-layer renders: F.Cu, B.Cu, In2.Cu (+3V3 plane)
  - +3V3 net distinctly coloured
  - Crosshair markers at resA endpoints
  - Orphan-island outline drawn
"""
import os
import pcbnew
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon
from matplotlib.collections import PatchCollection

HERE = os.path.dirname(os.path.abspath(__file__))
PCB_PATH = os.path.join(HERE, "novapcb-layout-v2.kicad_pcb")
OUT_DIR = os.path.join(HERE, "renders")

# Tight ROI per master
ROI = dict(xmin=67.5, xmax=72.0, ymin=29.0, ymax=34.0)
PX_PER_MM = 150  # 150 px/mm -> 675x750 px image, comfortably above 100 px/mm bar

# resA endpoints (the string-check anchor)
RESA_ENDPOINTS = [
    (69.2000, 29.8200, "resA-A: F.Cu Track 0.05mm"),
    (71.1125, 31.3174, "resA-B: F.Cu Track 0.567mm"),
]

# Net colours
COLOR_3V3 = "#ff3030"       # bright red
COLOR_GND = "#404040"        # dark grey
COLOR_OTHER = "#1c8aff"      # blue
COLOR_3V3_FILL = "#ff3030"   # plane fill colour
COLOR_PAD_3V3 = "#ffd040"    # bright yellow pads for +3V3 (high contrast)
COLOR_PAD_OTHER = "#cccccc"  # light grey
COLOR_VIA_OUTER = "#00d040"  # bright green for vias
COLOR_BG = "#101010"          # near-black for contrast

LAYER_NAMES = {
    pcbnew.F_Cu: "F.Cu",
    pcbnew.B_Cu: "B.Cu",
    pcbnew.In1_Cu: "In1.Cu",
    pcbnew.In2_Cu: "In2.Cu",
    pcbnew.In3_Cu: "In3.Cu",
    pcbnew.In4_Cu: "In4.Cu",
}


def in_roi(x, y, pad=0.2):
    """Is (x,y) within ROI with optional padding (mm)?"""
    return (ROI["xmin"] - pad <= x <= ROI["xmax"] + pad and
            ROI["ymin"] - pad <= y <= ROI["ymax"] + pad)


def setup_axes(ax, title):
    ax.set_xlim(ROI["xmin"], ROI["xmax"])
    ax.set_ylim(ROI["ymax"], ROI["ymin"])  # invert Y (KiCad: +Y = down)
    ax.set_aspect("equal")
    ax.set_facecolor(COLOR_BG)
    ax.set_title(title, fontsize=10, color="white", pad=4)
    # Grid every 0.5 mm
    ax.set_xticks([ROI["xmin"] + 0.5*i for i in range(int((ROI["xmax"]-ROI["xmin"])/0.5)+1)])
    ax.set_yticks([ROI["ymin"] + 0.5*i for i in range(int((ROI["ymax"]-ROI["ymin"])/0.5)+1)])
    ax.tick_params(colors="white", labelsize=7)
    ax.grid(True, color="#404040", linewidth=0.3, linestyle="--", alpha=0.4)
    for spine in ax.spines.values():
        spine.set_color("#808080")


def draw_endpoints_and_orphan(ax):
    """Crosshair markers at resA endpoints + orphan-island outline."""
    for x, y, label in RESA_ENDPOINTS:
        ax.plot(x, y, marker="+", color="#ffffff", markersize=18, markeredgewidth=1.5, zorder=20)
        ax.plot(x, y, marker="o", color="#ffffff", markersize=10, markerfacecolor="none",
                markeredgewidth=1.0, zorder=20)
        ax.annotate(label, (x, y), xytext=(8, -8), textcoords="offset points",
                    fontsize=6, color="#ffffff",
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="#000000", edgecolor="#ffffff", alpha=0.7),
                    zorder=21)
    # Orphan island outline (outline 1 of +3V3 zone on In2.Cu)
    brd = ax._brd  # passed via attr
    for z in brd.Zones():
        if z.GetNetname() != "+3V3":
            continue
        poly = z.GetFilledPolysList(z.GetFirstLayer())
        # outline 1 = orphan island per probe
        for i in range(poly.OutlineCount()):
            ol = poly.Outline(i)
            xs = [ol.CPoint(j).x/1e6 for j in range(ol.PointCount())]
            ys = [ol.CPoint(j).y/1e6 for j in range(ol.PointCount())]
            if not xs:
                continue
            # The orphan island bbox
            if (68.0 <= min(xs) and max(xs) <= 70.4 and
                32.2 <= min(ys) and max(ys) <= 33.85):
                ax.plot(xs + [xs[0]], ys + [ys[0]],
                        color="#ffff00", linewidth=1.5, linestyle="--", zorder=15,
                        label="orphan island (outline 1)")


def draw_zone_fill(ax, brd, target_layer):
    """Draw +3V3 plane fill on target layer."""
    for z in brd.Zones():
        if z.GetNetname() != "+3V3":
            continue
        if not z.IsOnLayer(target_layer):
            continue
        poly = z.GetFilledPolysList(target_layer)
        for i in range(poly.OutlineCount()):
            ol = poly.Outline(i)
            xs = [ol.CPoint(j).x/1e6 for j in range(ol.PointCount())]
            ys = [ol.CPoint(j).y/1e6 for j in range(ol.PointCount())]
            if not xs:
                continue
            # Clip to ROI bbox: if outline doesn't intersect ROI, skip
            if (max(xs) < ROI["xmin"] - 0.5 or min(xs) > ROI["xmax"] + 0.5 or
                max(ys) < ROI["ymin"] - 0.5 or min(ys) > ROI["ymax"] + 0.5):
                continue
            pts = list(zip(xs, ys))
            ax.add_patch(Polygon(pts, facecolor=COLOR_3V3_FILL, edgecolor="#ff8080",
                                 linewidth=0.4, alpha=0.55, zorder=1))


def draw_layer(ax, brd, target_layer, draw_planes=False):
    """Draw all tracks, vias, pads on target_layer within ROI."""
    # Zone fills first (lowest)
    if draw_planes:
        draw_zone_fill(ax, brd, target_layer)
    # Pads — only those on target_layer or thru-hole that touches it
    for fp in brd.GetFootprints():
        for pad in fp.Pads():
            bb = pad.GetBoundingBox()
            x = (bb.GetX() + bb.GetWidth()/2) / 1e6
            y = (bb.GetY() + bb.GetHeight()/2) / 1e6
            if not in_roi(x, y, pad=0.5):
                continue
            if not pad.IsOnLayer(target_layer):
                continue
            net = pad.GetNetname() if pad.GetNet() else ""
            color = COLOR_PAD_3V3 if net == "+3V3" else COLOR_PAD_OTHER
            w = bb.GetWidth()/1e6
            h = bb.GetHeight()/1e6
            rect = Rectangle((x - w/2, y - h/2), w, h,
                             facecolor=color, edgecolor="#ffffff",
                             linewidth=0.3, alpha=0.95, zorder=8)
            ax.add_patch(rect)
            # Pad number label if large enough
            if w * PX_PER_MM > 25 or h * PX_PER_MM > 25:
                label = f"{fp.GetReference()}.{pad.GetNumber()}"
                ax.annotate(label, (x, y), fontsize=4.5, color="#000000",
                            ha="center", va="center", zorder=9)
    # Tracks
    for t in brd.GetTracks():
        if isinstance(t, pcbnew.PCB_VIA):
            continue
        if t.GetLayer() != target_layer:
            continue
        s, e = t.GetStart(), t.GetEnd()
        sx, sy = s.x/1e6, s.y/1e6
        ex, ey = e.x/1e6, e.y/1e6
        if not (in_roi(sx, sy, pad=0.3) or in_roi(ex, ey, pad=0.3)):
            continue
        net = t.GetNetname() if t.GetNet() else ""
        width = t.GetWidth()/1e6
        color = COLOR_3V3 if net == "+3V3" else (COLOR_GND if net == "GND" else COLOR_OTHER)
        z = 7 if net == "+3V3" else 6
        ax.plot([sx, ex], [sy, ey], color=color,
                linewidth=width * PX_PER_MM * 0.072,
                solid_capstyle="round", zorder=z)
    # Vias (drawn on all copper layers they pass through)
    for t in brd.GetTracks():
        if not isinstance(t, pcbnew.PCB_VIA):
            continue
        # PCB_VIA: TopLayer..BottomLayer; treat through-hole as on all
        top, bot = t.TopLayer(), t.BottomLayer()
        if not (top <= target_layer <= bot or
                (target_layer in (pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu)
                 and top == pcbnew.F_Cu and bot == pcbnew.B_Cu)):
            continue
        p = t.GetPosition()
        x, y = p.x/1e6, p.y/1e6
        if not in_roi(x, y, pad=0.3):
            continue
        outer = t.GetWidth()/1e6 / 2
        drill = t.GetDrill()/1e6 / 2
        net = t.GetNetname() if t.GetNet() else ""
        edge = COLOR_3V3 if net == "+3V3" else COLOR_VIA_OUTER
        ax.add_patch(Circle((x, y), outer, facecolor="#202020",
                            edgecolor=edge, linewidth=0.8, zorder=10))
        ax.add_patch(Circle((x, y), drill, facecolor="#000000",
                            edgecolor="none", zorder=11))


def render_layer(brd, target_layer, label):
    fig, ax = plt.subplots(figsize=((ROI["xmax"]-ROI["xmin"])*PX_PER_MM/100,
                                     (ROI["ymax"]-ROI["ymin"])*PX_PER_MM/100),
                            dpi=100)
    ax._brd = brd
    title = f"resA ROI — {label} ({PX_PER_MM} px/mm, ROI X={ROI['xmin']}..{ROI['xmax']} Y={ROI['ymin']}..{ROI['ymax']})"
    setup_axes(ax, title)
    is_plane = (target_layer == pcbnew.In2_Cu)
    draw_layer(ax, brd, target_layer, draw_planes=is_plane)
    draw_endpoints_and_orphan(ax)

    # Legend
    from matplotlib.lines import Line2D
    handles = [
        Line2D([0],[0], color=COLOR_3V3, linewidth=2, label="+3V3 tracks/vias"),
        Line2D([0],[0], color=COLOR_GND, linewidth=2, label="GND tracks"),
        Line2D([0],[0], color=COLOR_OTHER, linewidth=2, label="other nets"),
        Line2D([0],[0], color=COLOR_PAD_3V3, marker="s", linewidth=0, markersize=6, label="+3V3 pads"),
        Line2D([0],[0], color=COLOR_VIA_OUTER, marker="o", linewidth=0, markersize=6,
               markerfacecolor="none", label="vias"),
        Line2D([0],[0], color="#ffff00", linestyle="--", linewidth=1.5, label="orphan island"),
        Line2D([0],[0], color="#ffffff", marker="+", linewidth=0, markersize=10, label="resA endpoint"),
    ]
    if is_plane:
        handles.insert(0, Line2D([0],[0], color=COLOR_3V3_FILL, alpha=0.55, linewidth=8, label="+3V3 plane fill"))
    leg = ax.legend(handles=handles, loc="lower left", fontsize=6, framealpha=0.85,
                    facecolor="#000000", edgecolor="#808080", labelcolor="white")
    fig.patch.set_facecolor("#000000")
    fig.tight_layout(pad=0.3)
    out = os.path.join(OUT_DIR, f"resA_{label.replace('.', '_').lower()}.png")
    fig.savefig(out, dpi=100, facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  wrote {out}")
    return out


def main():
    print(f"[1] load board")
    brd = pcbnew.LoadBoard(PCB_PATH)
    print(f"    ROI = X {ROI['xmin']}..{ROI['xmax']} mm, Y {ROI['ymin']}..{ROI['ymax']} mm")
    print(f"    resolution = {PX_PER_MM} px/mm")
    print(f"[2] render per-layer set")
    outs = []
    for layer, label in [(pcbnew.F_Cu, "F.Cu"),
                          (pcbnew.B_Cu, "B.Cu"),
                          (pcbnew.In2_Cu, "In2.Cu")]:
        out = render_layer(brd, layer, label)
        outs.append(out)
    print(f"[3] done — {len(outs)} renders")


if __name__ == "__main__":
    main()
