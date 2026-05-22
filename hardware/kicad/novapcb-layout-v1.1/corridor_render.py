#!/usr/bin/env python3
"""Per-net corridor renders for master's vision-propose loop (2026-05-22).

For each net in a batch JSON:
  - Compute bbox of all net pads + 5mm padding = corridor region
  - Crop from full-board top + bottom renders (rendered at 90px/mm = high-res)
  - Annotate: crosshair each pad, label refdes.pad/net/coord/layer
  - Generate companion coords JSON: pads + obstacle bboxes in corridor
  - Combine into a 1-row-per-net sheet OR per-net separate images

Output: ~/novapcb-preview-v1.1/corridors/batch_N/
"""
import os, sys, json, math, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent.resolve()
PCB = HERE / "novapcb-layout-v1.1.kicad_pcb"
PREV = Path.home() / "novapcb-preview-v1.1" / "corridors"

BOARD_W = 90.0
BOARD_H = 70.0
PX_PER_MM_FULL = 90  # full-board render at 90 px/mm

# Padding around net bbox
CORRIDOR_PAD_MM = 5.0


def render_full_board():
    """Render F.Cu + B.Cu at 90 px/mm (8100×6300 px each)."""
    PREV.mkdir(parents=True, exist_ok=True)
    out_top = PREV / "_full_top.png"
    out_bot = PREV / "_full_bot.png"
    W = int(BOARD_W * PX_PER_MM_FULL)
    H = int(BOARD_H * PX_PER_MM_FULL)
    if not out_top.exists():
        print(f"[render] top at {W}x{H}")
        subprocess.run(["kicad-cli","pcb","render","--output",str(out_top),
                        "--side","top","--background","opaque",
                        "--width",str(W),"--height",str(H),str(PCB)],
                       capture_output=True)
    if not out_bot.exists():
        print(f"[render] bot at {W}x{H}")
        subprocess.run(["kicad-cli","pcb","render","--output",str(out_bot),
                        "--side","bottom","--background","opaque",
                        "--width",str(W),"--height",str(H),str(PCB)],
                       capture_output=True)
    return out_top, out_bot


def get_font(size=20):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def get_net_pads(brd, net_name):
    """Return [(ref, pad, x, y, layer_str)] for all pads on net."""
    import pcbnew
    pads = []
    for fp in brd.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname() == net_name:
                pos = p.GetPosition()
                layer = "F.Cu" if p.IsOnLayer(pcbnew.F_Cu) else ("B.Cu" if p.IsOnLayer(pcbnew.B_Cu) else "?")
                pads.append((fp.GetReference(), p.GetNumber(),
                              pos.x/1e6, pos.y/1e6, layer))
    return pads


def obstacles_in_bbox(brd, bbox_mm, my_net):
    """Return list of (kind, ref/net, layer, x, y, ...) for obstacles in bbox."""
    import pcbnew
    xL, yT, xR, yB = bbox_mm
    obs = {"pads": [], "tracks": [], "vias": []}
    for fp in brd.GetFootprints():
        for p in fp.Pads():
            pos = p.GetPosition()
            x, y = pos.x/1e6, pos.y/1e6
            if xL <= x <= xR and yT <= y <= yB:
                sz = p.GetSize()
                layer = "F.Cu" if p.IsOnLayer(pcbnew.F_Cu) else "B.Cu"
                obs["pads"].append({"ref":fp.GetReference(),"pad":p.GetNumber(),
                                     "net":p.GetNetname(),"x":x,"y":y,
                                     "sx":sz.x/1e6,"sy":sz.y/1e6,"layer":layer})
    for t in brd.GetTracks():
        if isinstance(t, pcbnew.PCB_VIA):
            pos = t.GetPosition()
            x, y = pos.x/1e6, pos.y/1e6
            if xL <= x <= xR and yT <= y <= yB:
                obs["vias"].append({"net":t.GetNetname(),"x":x,"y":y,
                                     "dia":t.GetWidth()/1e6})
        else:
            s = t.GetStart(); e = t.GetEnd()
            sx, sy = s.x/1e6, s.y/1e6
            ex, ey = e.x/1e6, e.y/1e6
            # Track in bbox if any endpoint in bbox or crosses
            if (xL <= sx <= xR and yT <= sy <= yB) or (xL <= ex <= xR and yT <= ey <= yB):
                layer = "F.Cu" if t.GetLayer() == pcbnew.F_Cu else ("B.Cu" if t.GetLayer() == pcbnew.B_Cu else f"layer_{t.GetLayer()}")
                obs["tracks"].append({"net":t.GetNetname(),"layer":layer,
                                       "x1":sx,"y1":sy,"x2":ex,"y2":ey,
                                       "w":t.GetWidth()/1e6})
    return obs


def make_corridor(full_top, full_bot, net_name, pads, batch_dir, batch_no):
    """Crop both layers to corridor bbox, annotate, return paths."""
    if len(pads) < 2:
        return None
    # bbox
    xs = [p[2] for p in pads]; ys = [p[3] for p in pads]
    xL = max(0, min(xs) - CORRIDOR_PAD_MM)
    yT = max(0, min(ys) - CORRIDOR_PAD_MM)
    xR = min(BOARD_W, max(xs) + CORRIDOR_PAD_MM)
    yB = min(BOARD_H, max(ys) + CORRIDOR_PAD_MM)
    bbox = (xL, yT, xR, yB)

    # Render coords (full board 8100×6300)
    img_top = Image.open(full_top)
    img_bot = Image.open(full_bot)
    Wt, Ht = img_top.size
    # B.Cu render is mirrored horizontally — top-side view of the bottom layer.
    # So the X coordinate in mm needs to be flipped on the B.Cu render.
    def crop_top(im, bbox):
        l = int(bbox[0] * PX_PER_MM_FULL)
        t = int(bbox[1] * PX_PER_MM_FULL)
        r = int(bbox[2] * PX_PER_MM_FULL)
        b = int(bbox[3] * PX_PER_MM_FULL)
        return im.crop((l, t, r, b))
    def crop_bot(im, bbox):
        # B.Cu render is mirrored: x_mm = BOARD_W - x_mm
        l = int((BOARD_W - bbox[2]) * PX_PER_MM_FULL)
        r = int((BOARD_W - bbox[0]) * PX_PER_MM_FULL)
        t = int(bbox[1] * PX_PER_MM_FULL)
        b = int(bbox[3] * PX_PER_MM_FULL)
        cropped = im.crop((l, t, r, b))
        # Flip back so left/right match the F.Cu view
        return cropped.transpose(Image.FLIP_LEFT_RIGHT)

    crop_t = crop_top(img_top, bbox)
    crop_b = crop_bot(img_bot, bbox)
    # Both at PX_PER_MM_FULL = 90 px/mm — exceeds master's 80 spec

    # Combine: F.Cu left, B.Cu right with separator
    ft = get_font(22)
    SEP = 40
    W = crop_t.width + crop_b.width + SEP
    H = max(crop_t.height, crop_b.height) + 80  # header
    combined = Image.new("RGB", (W, H), (15, 20, 28))
    draw = ImageDraw.Draw(combined)
    draw.text((20, 12), f"Net: {net_name}  bbox=({xL:.1f},{yT:.1f})..({xR:.1f},{yB:.1f}) mm  90 px/mm",
              font=ft, fill=(255, 255, 255))
    draw.text((20 + crop_t.width//2 - 30, 50), "F.Cu (top)", font=ft, fill=(255, 200, 100))
    draw.text((20 + crop_t.width + SEP + crop_b.width//2 - 30, 50), "B.Cu (bottom)", font=ft, fill=(100, 200, 255))
    combined.paste(crop_t, (0, 80))
    combined.paste(crop_b, (crop_t.width + SEP, 80))

    # Crosshair + label each pad on both layers
    def annotate(im_draw, x_offset, y_offset, mirror_x=False):
        for ref, pad_num, x, y, layer in pads:
            # Convert mm to crop-local pixel coords
            cx = (x - bbox[0]) * PX_PER_MM_FULL
            cy = (y - bbox[1]) * PX_PER_MM_FULL
            px = int(cx + x_offset)
            py = int(cy + y_offset)
            # Crosshair (12px)
            im_draw.line([(px-12, py), (px+12, py)], fill=(255,255,0), width=2)
            im_draw.line([(px, py-12), (px, py+12)], fill=(255,255,0), width=2)
            label = f"{ref}.{pad_num} ({x:.2f},{y:.2f}) {layer}"
            im_draw.text((px+10, py+10), label, font=get_font(16), fill=(255,255,0))
    annotate(draw, 0, 80)
    annotate(draw, crop_t.width + SEP, 80)

    out = batch_dir / f"corridor_{net_name.replace('+','p').replace('/','_')}.png"
    combined.save(out, optimize=True)
    return out, bbox


def main(batch_file):
    import pcbnew
    spec = json.load(open(batch_file))
    batch_no = Path(batch_file).stem.replace("batch_", "")
    nets_to_render = spec.get("nets", [])
    # Add trace_nets
    for tn in spec.get("trace_nets", []):
        nets_to_render.append(tn["net"])

    batch_dir = PREV / f"batch_{batch_no}"
    batch_dir.mkdir(parents=True, exist_ok=True)

    print(f"[batch {batch_no}] {len(nets_to_render)} nets")
    full_top, full_bot = render_full_board()
    brd = pcbnew.LoadBoard(str(PCB))

    index = []
    for net_name in nets_to_render:
        pads = get_net_pads(brd, net_name)
        if len(pads) < 2:
            print(f"  {net_name}: {len(pads)} pads — skip")
            continue
        out, bbox = make_corridor(full_top, full_bot, net_name, pads, batch_dir, batch_no)
        obs = obstacles_in_bbox(brd, bbox, net_name)
        print(f"  {net_name}: {len(pads)} pads, bbox ({bbox[0]:.1f},{bbox[1]:.1f})..({bbox[2]:.1f},{bbox[3]:.1f})  obs: {len(obs['pads'])}p {len(obs['tracks'])}t {len(obs['vias'])}v")
        index.append({"net":net_name,"corridor_png":str(out.name),
                       "bbox":bbox,"pads":pads,"obstacles":obs})

    json_out = batch_dir / "index.json"
    with open(json_out, "w") as f:
        json.dump(index, f, indent=2, default=str)
    print(f"\n[done] {len(index)} corridor renders + {json_out}")


if __name__ == "__main__":
    main(sys.argv[1])
