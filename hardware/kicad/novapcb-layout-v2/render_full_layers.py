#!/usr/bin/env python3
"""Full-board per-layer render with net-color highlighting + legend.

Adapted from render_resA_set.py (Step 5 vision-pass tool) for full-
board rendering of all 6 copper layers. Net-colored: +3V3 red, GND
grey, signals blue, pads distinct yellow for plane pads. Plane fills
shown semi-transparent on inner layers.

Output: PNGs to ~/novapcb-preview/layers_v2/<layer>.png at 40 px/mm.
"""
import os
import pcbnew
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon
from matplotlib.lines import Line2D

PCB_PATH = "/home/novatics64/novapcb/hardware/kicad/novapcb-layout-v2/novapcb-layout-v2.kicad_pcb"
OUT_DIR = "/home/novatics64/novapcb-preview/layers_v2"
os.makedirs(OUT_DIR, exist_ok=True)

# Board ROI (full board)
BOARD_W, BOARD_H = 80.0, 60.0
ROI = dict(xmin=0, xmax=BOARD_W, ymin=0, ymax=BOARD_H)

PX_PER_MM = 40   # 3200×2400 px per layer; ~1MB PNG each

# Net colours
COLOR_3V3 = "#ff3030"
COLOR_3V3A = "#ff8c00"
COLOR_5V = "#ffd700"
COLOR_GND = "#606060"
COLOR_OTHER = "#1c8aff"
COLOR_3V3_FILL = "#ff3030"
COLOR_GND_FILL = "#a0a0a0"
COLOR_5V_FILL = "#ffd700"
COLOR_PAD_PLANE = "#ffd040"
COLOR_PAD_OTHER = "#cccccc"
COLOR_VIA_OUTER = "#00d040"
COLOR_BG = "#0a0a0a"

LAYER_NAMES = {
    pcbnew.F_Cu: "F.Cu",
    pcbnew.B_Cu: "B.Cu",
    pcbnew.In1_Cu: "In1.Cu",
    pcbnew.In2_Cu: "In2.Cu",
    pcbnew.In3_Cu: "In3.Cu",
    pcbnew.In4_Cu: "In4.Cu",
}

LAYER_PLANE_NET = {
    "F.Cu": None,
    "In1.Cu": "GND",
    "In2.Cu": "+3V3",
    "In3.Cu": "+5V",
    "In4.Cu": "GND",
    "B.Cu": None,
}

LAYER_TITLE = {
    "F.Cu": "L1 — F.Cu (top signal)",
    "In1.Cu": "L2 — In1.Cu (GND plane)",
    "In2.Cu": "L3 — In2.Cu (+3V3 plane)",
    "In3.Cu": "L4 — In3.Cu (+5V plane)",
    "In4.Cu": "L5 — In4.Cu (GND plane)",
    "B.Cu": "L6 — B.Cu (bottom signal)",
}


def net_color(net_name):
    """Return color for a trace based on its net."""
    if net_name == "+3V3" or net_name == "+3V3A": return COLOR_3V3
    if net_name == "+5V" or net_name == "+5V_BEC" or net_name == "+5V_BEC_PROT": return COLOR_5V
    if net_name == "GND": return COLOR_GND
    return COLOR_OTHER


def pad_color(net_name):
    if net_name in ("+3V3", "+3V3A", "+5V", "GND"):
        return COLOR_PAD_PLANE
    return COLOR_PAD_OTHER


def setup_axes(ax, title, mirror_x=False):
    if mirror_x:
        ax.set_xlim(ROI["xmax"], ROI["xmin"])
    else:
        ax.set_xlim(ROI["xmin"], ROI["xmax"])
    ax.set_ylim(ROI["ymax"], ROI["ymin"])
    ax.set_aspect("equal")
    ax.set_facecolor(COLOR_BG)
    ax.set_title(title, fontsize=22, color="white", pad=14)
    ax.set_xticks(range(0, int(BOARD_W) + 1, 10))
    ax.set_yticks(range(0, int(BOARD_H) + 1, 10))
    ax.tick_params(colors="white", labelsize=12)
    ax.grid(True, color="#303030", linewidth=0.3, linestyle="--", alpha=0.6)
    for spine in ax.spines.values():
        spine.set_color("#808080")


def draw_edge_cuts(ax, brd):
    for d in brd.GetDrawings():
        if d.GetLayer() != pcbnew.Edge_Cuts: continue
        if d.GetClass() == "PCB_SHAPE":
            shape = d.GetShape()
            if shape == pcbnew.SHAPE_T_SEGMENT:
                s, e = d.GetStart(), d.GetEnd()
                ax.plot([s.x/1e6, e.x/1e6], [s.y/1e6, e.y/1e6],
                        color="#ffffff", linewidth=1.5, zorder=1)


def draw_plane_fill(ax, brd, target_layer, fill_color):
    for z in brd.Zones():
        if z.GetNetname() not in ("GND", "+3V3", "+3V3A", "+5V"): continue
        if not z.IsOnLayer(target_layer): continue
        poly = z.GetFilledPolysList(target_layer)
        for i in range(poly.OutlineCount()):
            ol = poly.Outline(i)
            xs = [ol.CPoint(j).x/1e6 for j in range(ol.PointCount())]
            ys = [ol.CPoint(j).y/1e6 for j in range(ol.PointCount())]
            if not xs: continue
            pts = list(zip(xs, ys))
            ax.add_patch(Polygon(pts, facecolor=fill_color, edgecolor=fill_color,
                                  linewidth=0.2, alpha=0.50, zorder=2))


def draw_layer(ax, brd, target_layer, draw_planes=False):
    if draw_planes:
        plane_net = LAYER_PLANE_NET.get(LAYER_NAMES[target_layer])
        if plane_net:
            fc = {"+3V3": COLOR_3V3_FILL, "GND": COLOR_GND_FILL,
                  "+5V": COLOR_5V_FILL}.get(plane_net, COLOR_OTHER)
            draw_plane_fill(ax, brd, target_layer, fc)

    # Pads
    for fp in brd.GetFootprints():
        for pad in fp.Pads():
            if not pad.IsOnLayer(target_layer): continue
            bb = pad.GetBoundingBox()
            x = (bb.GetX() + bb.GetWidth()//2) / 1e6
            y = (bb.GetY() + bb.GetHeight()//2) / 1e6
            w = bb.GetWidth()/1e6
            h = bb.GetHeight()/1e6
            net = pad.GetNet().GetNetname() if pad.GetNet() else ""
            color = pad_color(net)
            rect = Rectangle((x - w/2, y - h/2), w, h,
                             facecolor=color, edgecolor="#ffffff",
                             linewidth=0.2, alpha=0.95, zorder=6)
            ax.add_patch(rect)

    # Tracks
    for t in brd.GetTracks():
        if isinstance(t, pcbnew.PCB_VIA): continue
        if t.GetLayer() != target_layer: continue
        s, e = t.GetStart(), t.GetEnd()
        sx, sy = s.x/1e6, s.y/1e6
        ex, ey = e.x/1e6, e.y/1e6
        net = t.GetNet().GetNetname() if t.GetNet() else ""
        width = t.GetWidth()/1e6
        color = net_color(net)
        ax.plot([sx, ex], [sy, ey], color=color,
                linewidth=max(1, width * PX_PER_MM * 0.072),
                solid_capstyle="round", zorder=5)

    # Vias (drawn on all layers they span)
    for t in brd.GetTracks():
        if not isinstance(t, pcbnew.PCB_VIA): continue
        top, bot = t.TopLayer(), t.BottomLayer()
        layer_in_span = (top <= target_layer <= bot or
                         (target_layer in (pcbnew.In1_Cu, pcbnew.In2_Cu,
                                            pcbnew.In3_Cu, pcbnew.In4_Cu)
                          and top == pcbnew.F_Cu and bot == pcbnew.B_Cu))
        if not layer_in_span: continue
        p = t.GetPosition()
        outer = t.GetWidth()/2/1e6
        drill = t.GetDrill()/2/1e6
        net = t.GetNet().GetNetname() if t.GetNet() else ""
        edge = net_color(net) if net in ("+3V3","+3V3A","+5V","GND") else COLOR_VIA_OUTER
        ax.add_patch(Circle((p.x/1e6, p.y/1e6), outer, facecolor="#202020",
                            edgecolor=edge, linewidth=0.4, zorder=8))
        ax.add_patch(Circle((p.x/1e6, p.y/1e6), drill, facecolor="#000000",
                            edgecolor="none", zorder=9))


def render_layer(brd, target_layer, layer_name):
    is_plane = layer_name in ("In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu")
    is_bottom = layer_name == "B.Cu"
    fig, ax = plt.subplots(figsize=((ROI["xmax"]-ROI["xmin"])*PX_PER_MM/100,
                                     (ROI["ymax"]-ROI["ymin"])*PX_PER_MM/100),
                            dpi=100)
    title = LAYER_TITLE[layer_name]
    if is_bottom:
        title += "  (mirrored — looking down from top)"
    setup_axes(ax, title, mirror_x=is_bottom)
    draw_edge_cuts(ax, brd)
    draw_layer(ax, brd, target_layer, draw_planes=is_plane)

    # Legend
    handles = [
        Line2D([0],[0], color=COLOR_3V3, linewidth=3, label="+3V3 / +3V3A"),
        Line2D([0],[0], color=COLOR_5V, linewidth=3, label="+5V"),
        Line2D([0],[0], color=COLOR_GND, linewidth=3, label="GND"),
        Line2D([0],[0], color=COLOR_OTHER, linewidth=3, label="signal nets"),
        Line2D([0],[0], color=COLOR_PAD_PLANE, marker="s", linewidth=0, markersize=10,
               label="plane-net pads"),
        Line2D([0],[0], color=COLOR_VIA_OUTER, marker="o", linewidth=0, markersize=10,
               markerfacecolor="none", label="vias"),
    ]
    if is_plane:
        handles.insert(0, Line2D([0],[0], color={"GND": COLOR_GND_FILL,
                                                    "+3V3": COLOR_3V3_FILL,
                                                    "+5V": COLOR_5V_FILL}[
                                                        LAYER_PLANE_NET[layer_name]],
                                  alpha=0.55, linewidth=12,
                                  label=f"{LAYER_PLANE_NET[layer_name]} plane fill"))
    ax.legend(handles=handles, loc="lower right", fontsize=12, framealpha=0.85,
              facecolor="#000000", edgecolor="#808080", labelcolor="white")
    fig.patch.set_facecolor("#000000")
    fig.tight_layout(pad=0.5)
    out = os.path.join(OUT_DIR, f"{layer_name.replace('.', '_')}.png")
    fig.savefig(out, dpi=100, facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  {layer_name} -> {out}")
    return out


def main():
    print("[1] load board")
    brd = pcbnew.LoadBoard(PCB_PATH)
    print(f"[2] render 6 layers at {PX_PER_MM} px/mm")
    for layer_id, name in [(pcbnew.F_Cu, "F.Cu"),
                            (pcbnew.In1_Cu, "In1.Cu"),
                            (pcbnew.In2_Cu, "In2.Cu"),
                            (pcbnew.In3_Cu, "In3.Cu"),
                            (pcbnew.In4_Cu, "In4.Cu"),
                            (pcbnew.B_Cu, "B.Cu")]:
        render_layer(brd, layer_id, name)
    print("[3] done")


if __name__ == "__main__":
    main()
