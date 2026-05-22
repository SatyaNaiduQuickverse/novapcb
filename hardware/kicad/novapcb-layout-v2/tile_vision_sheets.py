#!/usr/bin/env python3
"""Tile the 28 vision residual renders into 4 composite review sheets
per master 2026-05-21 dispatch.

Each tile: 500x500 px (existing 600x600 render scaled) + 30px label header.
Grouping per sheet = difficulty tier."""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

VISION_DIR = Path("/home/novatics64/novapcb-preview/vision")

TILE = 500
LABEL_H = 36
TILE_BG = (10, 10, 10)
LABEL_BG = (33, 38, 45)
LABEL_FG = (220, 220, 220)
SHEET_BG = (13, 17, 23)

# Find a readable font
def get_font():
    for path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]:
        if Path(path).exists():
            return ImageFont.truetype(path, 18), ImageFont.truetype(path, 14)
    return ImageFont.load_default(), ImageFont.load_default()

FONT_TITLE, FONT_SUB = get_font()

# (slug, label_top, label_sub) — tile descriptions
SHEETS = {
    1: {
        "title": "Sheet 1 — Pin-density only (8 pads)",
        "tiles": [
            ("U1_19_GND",   "U1.19 (GND)",    "(31.86, 33.00) F.Cu — pin density"),
            ("U1_21_p3V3A", "U1.21 (+3V3A)",  "(31.86, 34.00) F.Cu — pin density"),
            ("U1_49_GND",   "U1.49 (GND)",    "(45.03, 37.68) F.Cu — pin density"),
            ("U1_75_p3V3",  "U1.75 (+3V3)",   "(47.21, 24.00) F.Cu — pin density"),
            ("U1_100_p3V3", "U1.100 (+3V3)",  "(33.53, 22.33) F.Cu — pin density"),
            ("J2_3_GND",    "J2.3 (GND)",     "(40.11, 37.73) B.Cu — pin density"),
            ("J2_4_p3V3",   "J2.4 (+3V3)",    "(39.01, 37.73) B.Cu — pin density"),
            ("J2_6_GND",    "J2.6 (GND)",     "(36.81, 37.73) B.Cu — pin density"),
        ],
        "cols": 4,
    },
    2: {
        "title": "Sheet 2 — Single-conflict (7 pads)",
        "tiles": [
            ("FB1_2_p3V3A", "FB1.2 (+3V3A)",  "(29.65, 29.52) F.Cu — SDMMC1_CMD B.Cu"),
            ("U1_27_p3V3",  "U1.27 (+3V3)",   "(34.03, 37.68) F.Cu — SDMMC1_D2 B.Cu"),
            ("U1_99_GND",   "U1.99 (GND)",    "(34.03, 22.33) F.Cu — USART1_RX B.Cu"),
            ("C23_2_GND",   "C23.2 (GND)",    "(40.01, 20.81) F.Cu — SWDIO B.Cu"),
            ("U3_8_p3V3",   "U3.8 (+3V3)",    "(71.11, 30.75) F.Cu — I2C2_SDA B.Cu"),
            ("R52_1_p3V3",  "R52.1 (+3V3)",   "(30.08, 28.06) B.Cu — GND F.Cu (same family)"),
            ("R55_1_p3V3",  "R55.1 (+3V3)",   "(30.08, 24.19) B.Cu — BOOT0 F.Cu"),
        ],
        "cols": 4,
    },
    3: {
        "title": "Sheet 3 — Double-conflict (7 pads)",
        "tiles": [
            ("R3_2_GND",    "R3.2 (GND)",     "(30.16, 24.68) F.Cu — USART1_TX B.Cu"),
            ("C11_1_p3V3",  "C11.1 (+3V3)",   "(33.40, 39.19) F.Cu — SDMMC1_CMD/D3 B.Cu"),
            ("C11_2_GND",   "C11.2 (GND)",    "(34.36, 39.19) F.Cu — SDMMC1_CMD/D3 B.Cu"),
            ("C12_1_p3V3",  "C12.1 (+3V3)",   "(36.23, 39.19) F.Cu — SDMMC1_CMD/D3 B.Cu"),
            ("C12_2_GND",   "C12.2 (GND)",    "(37.19, 39.19) F.Cu — SDMMC1_CMD/D3 B.Cu"),
            ("R54_1_p3V3",  "R54.1 (+3V3)",   "(47.96, 28.06) B.Cu — SDMMC1_D1 F.Cu"),
            ("C20_1_p3V3A", "C20.1 (+3V3A)",  "(29.17, 31.94) F.Cu — SDMMC1_CMD/D3 + USART1_TX (3 conflicts)"),
        ],
        "cols": 4,
    },
    4: {
        "title": "Sheet 4 — Triple/quad + sensitive (6 pads)",
        "tiles": [
            ("C18_2_GND",   "C18.2 (GND)",    "(31.54, 20.81) F.Cu — GPS1_RX + SPI1_MOSI x2 (3 conflicts)"),
            ("C17_2_GND",   "C17.2 (GND)",    "(34.36, 20.81) F.Cu — GPS1_RX + I2C1_SCL/SDA (3 conflicts)"),
            ("C24_2_GND",   "C24.2 (GND)",    "(51.30, 27.10) F.Cu — MOT7 + USART6_RX x2 + USART6_TX (4 conflicts)"),
            ("U1_11_p3V3",  "U1.11 (+3V3)",   "(31.86, 29.00) F.Cu — HSE_IN crystal F.Cu (SENSITIVE)"),
            ("Y1_2_GND",    "Y1.2 (GND)",     "(51.92, 30.85) F.Cu — USB_DP B.Cu (SENSITIVE)"),
            ("R53_1_p3V3",  "R53.1 (+3V3)",   "(47.96, 26.13) B.Cu — USB_DM/DP F.Cu (SENSITIVE)"),
        ],
        "cols": 3,
    },
}


def make_sheet(sheet_num, info):
    tiles = info["tiles"]
    cols = info["cols"]
    rows = (len(tiles) + cols - 1) // cols
    tile_total = TILE + LABEL_H
    # Header area for sheet title
    HEADER = 50
    sheet_w = cols * TILE
    sheet_h = HEADER + rows * tile_total
    img = Image.new("RGB", (sheet_w, sheet_h), SHEET_BG)
    draw = ImageDraw.Draw(img)
    draw.text((20, 14), info["title"], font=FONT_TITLE, fill=(88, 166, 255))

    for i, (slug, label, sub) in enumerate(tiles):
        col = i % cols
        row = i // cols
        x0 = col * TILE
        y0 = HEADER + row * tile_total
        # Label background
        draw.rectangle([x0, y0, x0 + TILE, y0 + LABEL_H], fill=LABEL_BG)
        draw.text((x0 + 8, y0 + 4), label, font=FONT_TITLE, fill=LABEL_FG)
        draw.text((x0 + 8, y0 + 22), sub, font=FONT_SUB, fill=(140, 148, 158))
        # Render
        src = VISION_DIR / slug / "render.png"
        if src.exists():
            tile_img = Image.open(src).convert("RGB")
            tile_img = tile_img.resize((TILE, TILE), Image.LANCZOS)
            img.paste(tile_img, (x0, y0 + LABEL_H))
        else:
            draw.text((x0 + 10, y0 + LABEL_H + 10), f"MISSING: {slug}", font=FONT_TITLE, fill=(255, 100, 100))

    out = VISION_DIR / f"sheet{sheet_num}.png"
    img.save(out, optimize=True)
    print(f"sheet{sheet_num}: {out} ({sheet_w}x{sheet_h}, {out.stat().st_size//1024} KB)")
    return out


def main():
    for num, info in SHEETS.items():
        make_sheet(num, info)
    print("Done.")


if __name__ == "__main__":
    main()
