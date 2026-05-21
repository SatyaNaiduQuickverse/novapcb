#!/usr/bin/env python3
"""Render per-batch review images: board-wide top/bot + ROI per routed net.

Output to ~/novapcb-preview-v1.1/batches/batch_N/ for master review.
Commits renders into repo dir too so GitHub raw URLs work.
"""
import os, sys, json, subprocess, shutil
from pathlib import Path

HERE = Path(__file__).parent.resolve()
PCB = HERE / "novapcb-layout-v1.1.kicad_pcb"
PREV = Path.home() / "novapcb-preview-v1.1" / "batches"

def board_render(batch_dir, suffix=""):
    for side, name in [("top","top"), ("bottom","bot")]:
        out = batch_dir / f"render_board_{name}{suffix}.png"
        subprocess.run(["kicad-cli","pcb","render","--output",str(out),
                        "--side",side,"--background","opaque",
                        "--width","2200","--height","1700",str(PCB)],
                       capture_output=True, text=True)
        print(f"  {out.name}")


def roi_render(batch_dir, log_path):
    """ROI per touched net: load log, for each net pair render a 14x14mm view."""
    with open(log_path) as f:
        log = json.load(f)

    # For each net touched, render an ROI centered on its pads
    import pcbnew
    brd = pcbnew.LoadBoard(str(PCB))

    rois = []
    for r in log.get("results", []):
        kind = r.get("kind")
        if kind == "stitch":
            ref, pn = r["ref"], r["pad"]
            # find pad
            for fp in brd.GetFootprints():
                if fp.GetReference() == ref:
                    for p in fp.Pads():
                        if p.GetNumber() == pn:
                            pos = p.GetPosition()
                            rois.append({
                                "name": f"stitch_{ref}_{pn}_{r['net']}",
                                "x": pos.x/1e6, "y": pos.y/1e6,
                                "ok": r["ok"], "label": f"{ref}.{pn} {r['net']} [{r['strategy']}]"
                            })
        elif kind == "net":
            # find any pad on that net
            net_name = r["net"]
            res_json = json.load(open(HERE / "vision_residuals_mp30.json"))
            specs = res_json.get("by_net", {}).get(net_name, [])
            if specs:
                ps = specs[0]
                pad = None
                for fp in brd.GetFootprints():
                    if fp.GetReference() == ps["ref"]:
                        for p in fp.Pads():
                            if p.GetNumber() == ps["pad"]:
                                pad = p; break
                if pad:
                    pos = pad.GetPosition()
                    strats = ",".join(set(l.get("strat","?") for l in r.get("legs",[])))
                    rois.append({
                        "name": f"net_{net_name.replace('+','p').replace('/','_')}",
                        "x": pos.x/1e6, "y": pos.y/1e6,
                        "ok": r["ok"], "label": f"net={net_name} [{strats}]"
                    })

    # Use kicad-cli render with --pages to crop? KiCad has no native crop.
    # Instead render board, then PIL-crop each ROI.
    from PIL import Image, ImageDraw, ImageFont
    full = batch_dir / "render_board_top.png"
    bot = batch_dir / "render_board_bot.png"
    if not full.exists():
        print("  ! no board render yet"); return

    # Board outline: 0..90 mm X, 0..70 mm Y
    img = Image.open(full)
    W, H = img.size
    BOARD_W_MM, BOARD_H_MM = 90.0, 70.0
    px_per_mm_x = W / BOARD_W_MM
    px_per_mm_y = H / BOARD_H_MM
    ROI_MM = 14.0  # 14mm view

    try:
        ft = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
    except Exception:
        ft = ImageFont.load_default()

    for roi in rois:
        x_px = int(roi["x"] * px_per_mm_x)
        y_px = int(roi["y"] * px_per_mm_y)
        half = int(ROI_MM/2 * px_per_mm_x)
        l = max(0, x_px - half); t = max(0, y_px - half)
        r_ = min(W, x_px + half); b = min(H, y_px + half)
        crop = img.crop((l, t, r_, b))
        crop = crop.resize((600, 600), Image.LANCZOS)
        # Annotate
        draw = ImageDraw.Draw(crop)
        color = (40, 200, 80) if roi["ok"] else (240, 80, 80)
        draw.rectangle([(2,2),(598,598)], outline=color, width=4)
        draw.text((8, 8), roi["label"], font=ft, fill=color)
        out = batch_dir / f"roi_{roi['name']}.png"
        crop.save(out)
    print(f"  {len(rois)} ROIs rendered")


def main(batch_no):
    log_path = HERE / f"batch_{batch_no}.json"
    log_result = HERE / f"batch_{batch_no}_log.json"
    if not log_result.exists():
        print(f"!! no log at {log_result}"); sys.exit(1)
    PREV.mkdir(parents=True, exist_ok=True)
    batch_dir = PREV / f"batch_{batch_no}"
    batch_dir.mkdir(parents=True, exist_ok=True)

    print(f"[1] board renders → {batch_dir}")
    board_render(batch_dir)
    print(f"[2] ROIs from {log_result.name}")
    roi_render(batch_dir, log_result)

    # Copy board renders into repo so they're committable
    repo_renders = HERE / f"render_batch_{batch_no}_top.png"
    repo_bot = HERE / f"render_batch_{batch_no}_bot.png"
    shutil.copy(batch_dir / "render_board_top.png", repo_renders)
    shutil.copy(batch_dir / "render_board_bot.png", repo_bot)
    print(f"[3] copied board renders into repo for git-tracking")
    print(f"[done] batch {batch_no} renders at {batch_dir}")


if __name__ == "__main__":
    main(int(sys.argv[1]))
