#!/usr/bin/env python3
"""Tile 45 vision residuals into 6 review sheets per master 2026-05-21.
~8-9 tiles per sheet, 500x500px each (>=400 px), grouped by region/difficulty."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

VIS = Path("/home/novatics64/novapcb-preview/vision")
flagged = json.load(open("restitch_flagged.json"))["flagged"]
keyed = {f"{f['fp']}.{f['pad']}": f for f in flagged}
print(f"Total flagged: {len(flagged)}")

TILE = 500
LABEL_H = 36
SHEETS = {
    "v2_sheet1": {
        "title": "Sheet 1 — U1 LQFP-100 pin-density (9 pads)",
        "ids": ["U1.10", "U1.11", "U1.19", "U1.21", "U1.26", "U1.27", "U1.49", "U1.50", "U1.75"],
        "cols": 5,
    },
    "v2_sheet2": {
        "title": "Sheet 2 — U1 LQFP-100 + U5/FB1 (8 pads)",
        "ids": ["U1.99", "U1.100", "FB1.2", "U5.5", "C19.1", "C19.2", "C23.2", "C43.2"],
        "cols": 4,
    },
    "v2_sheet3": {
        "title": "Sheet 3 — J1 USB-C reversibility pair-sharers (6 pads)",
        "ids": ["J1.A9", "J1.A12", "J1.B1", "J1.B4", "J1.B9", "J1.B12"],
        "cols": 6,
    },
    "v2_sheet4": {
        "title": "Sheet 4 — SDMMC/USART-area caps (8 pads)",
        "ids": ["C11.1", "C11.2", "C12.1", "C12.2", "C15.1", "C20.1", "C22.2", "C17.2"],
        "cols": 4,
    },
    "v2_sheet5": {
        "title": "Sheet 5 — B.Cu side residuals (7 pads)",
        "ids": ["J2.3", "J2.4", "J2.6", "R51.1", "R52.1", "R54.1", "R55.1"],
        "cols": 4,
    },
    "v2_sheet6": {
        "title": "Sheet 6 — Sensitive (USB/HSE) + J9 + remaining (8 pads)",
        "ids": ["U1.11", "Y1.2", "R53.1", "U3.8", "R3.2", "C18.2", "C24.2", "J9.3", "J9.5"],
        "cols": 5,
    },
}

# Verify all 45 covered
all_ids = set()
for k, s in SHEETS.items():
    for i in s["ids"]: all_ids.add(i)
covered = sum(1 for k in keyed if k in all_ids)
print(f"Coverage: {covered} of {len(keyed)} mapped")
missing = set(keyed.keys()) - all_ids
if missing:
    print(f"MISSING: {missing}")

def get_font():
    for path in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
        if Path(path).exists():
            return ImageFont.truetype(path, 18), ImageFont.truetype(path, 14)
    return ImageFont.load_default(), ImageFont.load_default()
FT, FS = get_font()

for name, info in SHEETS.items():
    ids = info["ids"]
    cols = info["cols"]
    rows = (len(ids) + cols - 1) // cols
    HEADER = 50
    tile_h = TILE + LABEL_H
    sheet_w = cols * TILE
    sheet_h = HEADER + rows * tile_h
    img = Image.new("RGB", (sheet_w, sheet_h), (13, 17, 23))
    draw = ImageDraw.Draw(img)
    draw.text((20, 14), info["title"], font=FT, fill=(88, 166, 255))
    for i, pid in enumerate(ids):
        col, row = i % cols, i // cols
        x0 = col * TILE
        y0 = HEADER + row * tile_h
        f = keyed.get(pid)
        if not f:
            draw.text((x0+10, y0+10), f"MISSING {pid}", font=FT, fill=(255,100,100))
            continue
        label = f"{pid} ({f['net']})"
        sub = f"({f['pos'][0]:.2f},{f['pos'][1]:.2f}) {f['layer']}"
        draw.rectangle([x0, y0, x0+TILE, y0+LABEL_H], fill=(33, 38, 45))
        draw.text((x0+8, y0+4), label, font=FT, fill=(220,220,220))
        draw.text((x0+8, y0+22), sub, font=FS, fill=(140,148,158))
        slug = f"{f['fp']}_{f['pad']}_{f['net'].replace('+','p')}"
        src = VIS / slug / "render.png"
        if src.exists():
            tile = Image.open(src).convert("RGB").resize((TILE, TILE), Image.LANCZOS)
            img.paste(tile, (x0, y0+LABEL_H))
        else:
            draw.text((x0+10, y0+LABEL_H+10), f"NO RENDER {slug}", font=FT, fill=(255,100,100))
    out = VIS / f"{name}.png"
    img.save(out, optimize=True)
    print(f"{name}: {out} ({sheet_w}x{sheet_h}, {out.stat().st_size//1024} KB)")
