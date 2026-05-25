#!/usr/bin/env python3
"""Tile the 75 v1.1 vision residuals into composite review sheets.

Per master 2026-05-22: ~8-9 tiles per sheet, each >=400px, labelled
with net name + pad endpoints, grouped by board region.
"""
import os, json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

VISION = Path("/home/novatics64/novapcb-preview-v1.1/vision")
OUT = Path("/home/novatics64/novapcb-preview-v1.1/sheets")
OUT.mkdir(parents=True, exist_ok=True)

# Load index for all residuals
items_index = json.load(open(VISION / "index.json"))

TILE_W = 500
TILE_H = 500
LABEL_H = 48
HEADER_H = 60

# Group residuals by board REGION (X-coord-based since 5 zones run along X)
# Zones: POWER X<22, MCU X=22-60, IMU X=60-78, CAN X>=78, plus N-edge / S-edge
def region_for(item):
    x, y, net = item["pos"][0], item["pos"][1], item["net"]
    if y < 16: return "S_edge"      # ESC pads, J9, microSD
    if y > 60: return "N_edge"      # USB-C J1, J3/J5/J10 connectors
    if x < 22: return "POWER"       # west
    if x > 60: return "EAST_IMU_CAN"  # IMU + CAN
    return "MCU"                    # center

groups = {"S_edge":[], "POWER":[], "MCU":[], "N_edge":[], "EAST_IMU_CAN":[]}
for it in items_index:
    groups[region_for(it)].append(it)

# Print groups
for g, items in groups.items():
    print(f"  {g}: {len(items)} residuals")

def get_font():
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
        if Path(p).exists():
            return ImageFont.truetype(p, 20), ImageFont.truetype(p, 14)
    return ImageFont.load_default(), ImageFont.load_default()
FT_TITLE, FT_LABEL = get_font()

SHEET_INDEX = []

for region, items in groups.items():
    if not items: continue
    items.sort(key=lambda i: (i["net"], i["id"]))
    # ~8-9 tiles per sheet
    chunks = [items[i:i+9] for i in range(0, len(items), 9)]
    for chunk_idx, chunk in enumerate(chunks):
        sheet_name = f"sheet_{region}_{chunk_idx+1}"
        n = len(chunk)
        cols = 3
        rows = (n + cols - 1) // cols
        sheet_w = cols * TILE_W
        sheet_h = HEADER_H + rows * (TILE_H + LABEL_H)
        img = Image.new("RGB", (sheet_w, sheet_h), (13, 17, 23))
        draw = ImageDraw.Draw(img)
        title = f"Sheet [{region}] — {len(chunk)} residuals (chunk {chunk_idx+1}/{len(chunks)})"
        draw.text((20, 18), title, font=FT_TITLE, fill=(88, 166, 255))
        for i, it in enumerate(chunk):
            # Derive tile dir from id (e.g. "R53.1" → "R53_1_p3V3")
            ref, pad = it["id"].split(".")
            net_safe = it["net"].replace("+", "p").replace("/", "_").replace("-", "_")
            tile_dir = f"{ref}_{pad}_{net_safe}"
            png_path = VISION / tile_dir / "render.png"
            if not png_path.exists():
                continue
            col, row = i % cols, i // cols
            x0 = col * TILE_W
            y0 = HEADER_H + row * (TILE_H + LABEL_H)
            try:
                tile = Image.open(png_path).resize((TILE_W, TILE_H), Image.LANCZOS)
                img.paste(tile, (x0, y0))
            except Exception as e:
                print(f"  failed to paste {png_path}: {e}")
                continue
            # Label below tile: net + ref.pad + coords
            label1 = f"{it['id']}  net={it['net']}"
            label2 = f"@({it['pos'][0]:.2f}, {it['pos'][1]:.2f})  layer={it['layer'] or 'F.Cu'}"
            draw.text((x0 + 6, y0 + TILE_H + 4), label1, font=FT_LABEL, fill=(255, 255, 255))
            draw.text((x0 + 6, y0 + TILE_H + 24), label2, font=FT_LABEL, fill=(150, 200, 255))
        out_path = OUT / f"{sheet_name}.png"
        img.save(out_path, optimize=True)
        print(f"  → {out_path.name} ({n} tiles, {sheet_w}x{sheet_h})")
        SHEET_INDEX.append({
            "region": region,
            "chunk": chunk_idx + 1,
            "tiles": n,
            "file": sheet_name + ".png",
            "items": [{"id":x["id"],"net":x["net"],"pos":x["pos"],
                       "layer":x["layer"] or "F.Cu"} for x in chunk],
        })

with open(OUT / "index.json", "w") as f:
    json.dump(SHEET_INDEX, f, indent=2)
print(f"\nTotal sheets: {len(SHEET_INDEX)}")
print(f"Index: {OUT / 'index.json'}")
