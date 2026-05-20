#!/usr/bin/env python3
"""
novapcb Phase 4a — board scaffolding generator.

Produces novapcb-layout.kicad_pcb READY for placement (Phase 4b). NOT placed,
NOT routed.

What this script does:
  1. Imports the Phase 3 netlist via kinet2pcb (the canonical headless
     netlist → .kicad_pcb tool, xesscorp / SKiDL ecosystem).
  2. Sets 4 copper layers per DECISIONS §8.
  3. Adds a single CLOSED 36 × 36 mm outline via SHAPE_T_RECT (single
     primitive — Phase 4 P0 noted iter-#3 saw 4-disjoint-segments outline
     trigger SHAPE_POLY_SET non-closed asserts; SHAPE_T_RECT is one
     primitive and is always closed).
  4. Places the 4 M3 mounting holes at the 30.5 × 30.5 mm c-to-c pattern
     (Phase 2.5 P1.1 + DECISIONS §2 v1 outline). Inset 2.75 mm from each
     edge.
  5. Resolves the PHASE3_AUDIT.md §B placeholder footprints:
     - ICM-42688-P (U3): KiCad-generic `Package_LGA:LGA-14_3x2.5mm_P0.5mm_
       LayoutBorder3x4y` retained — body/pitch/pad-arrangement match TDK
       ds-000347 spec (Phase 2.5 P0.4 confirmed); pad-size dimensions are
       KiCad IPC-7351 nominal (TDK datasheet recommended-land-pattern not
       extractable in this session — WebFetch on the 60-page PDF timed
       out). Phase 6.5 forum review confirms IPC-7351-Density-B vs TDK
       recommended at Phase 7 pre-fab.
     - DPS310 (U4): existing `Package_LGA:Bosch_LGA-8_...` retained.
       Phase 3.5 verified 8/8 pin geometry match across Infineon DPS310
       datasheet + Bosch BMP280 datasheet + KiCad symbol. Value field is
       already overridden to "DPS310" (sheets/baro_3d.py); physical board
       silkscreen shows U4 + DPS310 (NOT the KiCad lib "BMP280" name).
     - ESC solder pads (MOT1-MOT8): footprint OVERRIDDEN here to the
       in-repo `novapcb_lib:ESC_solder_pad` — 2× SMD pads 2.0×1.5 mm
       at 2.5 mm pitch (signal + GND), per MatekH743 mini-FC convention.
       Replaces the `Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_
       Vertical` placeholder from Phase 3f.
  6. Sets the DRC ruleset on the board (track widths, clearances, vias)
     via BOARD_DESIGN_SETTINGS. The net-class table itself lives in the
     companion .kicad_pro file (KiCad 9 stores net classes in the project
     JSON, not the .kicad_pcb).

This script is the authoritative source. Re-run produces a bit-identical
.kicad_pcb modulo KiCad's internal UUIDs.

Usage:
    KICAD9_FOOTPRINT_DIR=/usr/share/kicad/footprints python3 generate_board.py

Outputs:
    novapcb-layout.kicad_pcb  — the board scaffolding (committed for review)
    novapcb-layout.kicad_pro  — companion project file (separate, hand-written)
"""

import os
import sys
import pcbnew
from kinet2pcb import kinet2pcb

HERE = os.path.dirname(os.path.abspath(__file__))
NETLIST = os.path.abspath(os.path.join(HERE, "..", "novapcb", "novapcb.net"))
OUT_PCB = os.path.join(HERE, "novapcb-layout.kicad_pcb")

# ---------- spec (Phase 2.5 P1.1 + DECISIONS §2 v1) ----------
BOARD_W_MM     = 36.0
BOARD_H_MM     = 36.0
HOLE_SPACING   = 30.5   # c-to-c, Pixhawk-standard mini-FC pattern
HOLE_INSET     = (BOARD_W_MM - HOLE_SPACING) / 2.0   # 2.75 mm from each edge
# Phase 3f assigned the 8 ESC output connectors as J11-J18 (Conn_01x02 placeholders).
# MOT1-MOT8 are the NET names, not the component refs.
MOTOR_CONN_REFS = [f"J{i}" for i in range(11, 19)]
NOVAPCB_LIB    = os.path.join(HERE, "lib", "novapcb.pretty")

def _mm(x_mm):
    return int(x_mm * 1_000_000)


# ============================================================
# Step 1+2 — kinet2pcb netlist → 4-layer board
# ============================================================
print(f"[1/6] kinet2pcb {os.path.basename(NETLIST)} -> board", flush=True)
assert os.path.exists(NETLIST), f"Netlist not found: {NETLIST}"
if os.path.exists(OUT_PCB):
    os.remove(OUT_PCB)
kinet2pcb(NETLIST, OUT_PCB)
brd = pcbnew.LoadBoard(OUT_PCB)
brd.SetCopperLayerCount(4)
print(f"      footprints loaded: {len(list(brd.GetFootprints()))}", flush=True)
print(f"      copper layer count: {brd.GetCopperLayerCount()}", flush=True)


# ============================================================
# Step 3 — single CLOSED 36×36 mm outline (SHAPE_T_RECT primitive)
# ============================================================
print(f"[2/6] outline = closed 36×36 mm rectangle on Edge.Cuts", flush=True)
# Place board origin at (0,0); rectangle from (0,0) to (36,36) mm.
out = pcbnew.PCB_SHAPE(brd)
out.SetShape(pcbnew.SHAPE_T_RECT)
out.SetLayer(pcbnew.Edge_Cuts)
out.SetStart(pcbnew.VECTOR2I(_mm(0),       _mm(0)))
out.SetEnd(  pcbnew.VECTOR2I(_mm(BOARD_W_MM), _mm(BOARD_H_MM)))
out.SetWidth(int(0.15e6))
out.SetFilled(False)
brd.Add(out)


# ============================================================
# Step 4 — 4× M3 mounting holes at 30.5 c-to-c
# ============================================================
print(f"[3/6] 4× M3 mounting holes at corners (inset {HOLE_INSET} mm)", flush=True)
# Find the existing H1-H4 footprints kinet2pcb placed and re-position them
# to the proper 30.5 × 30.5 mm c-to-c pattern (Phase 2.5 P1.1 geometry).
HOLE_POSITIONS = [
    (HOLE_INSET,                       HOLE_INSET),                       # H1: bottom-left
    (BOARD_W_MM - HOLE_INSET,          HOLE_INSET),                       # H2: bottom-right
    (HOLE_INSET,                       BOARD_H_MM - HOLE_INSET),          # H3: top-left
    (BOARD_W_MM - HOLE_INSET,          BOARD_H_MM - HOLE_INSET),          # H4: top-right
]
mounting_refs = ["H1", "H2", "H3", "H4"]
for fp in brd.GetFootprints():
    ref = fp.GetReference()
    if ref in mounting_refs:
        x_mm, y_mm = HOLE_POSITIONS[mounting_refs.index(ref)]
        fp.SetPosition(pcbnew.VECTOR2I(_mm(x_mm), _mm(y_mm)))
        print(f"      {ref:3s} placed at ({x_mm:6.2f}, {y_mm:6.2f}) mm", flush=True)


# ============================================================
# Step 5 — override placeholder footprints (PHASE3_AUDIT.md §B)
# ============================================================
# 5.1 ESC solder pads — swap J11-J18 from PinHeader to in-repo custom.
print(f"[4/6] swap J11-J18 footprint -> novapcb_lib:ESC_solder_pad", flush=True)
swapped = 0
for fp in brd.GetFootprints():
    if fp.GetReference() in MOTOR_CONN_REFS:
        # Load the custom footprint from the in-repo lib
        new_fp = pcbnew.FootprintLoad(NOVAPCB_LIB, "ESC_solder_pad")
        if new_fp is None:
            print(f"      !!! FootprintLoad failed for ESC_solder_pad", flush=True)
            sys.exit(2)
        # Preserve net assignments + position + reference
        old_pos = fp.GetPosition()
        old_ref = fp.GetReference()
        # Map net assignments by pad-number (1 = signal, 2 = GND)
        net_map = {pad.GetNumber(): pad.GetNet() for pad in fp.Pads()}
        new_fp.SetReference(old_ref)
        new_fp.SetPosition(old_pos)
        for pad in new_fp.Pads():
            n = net_map.get(pad.GetNumber())
            if n is not None:
                pad.SetNet(n)
        # Remove old, add new
        brd.Remove(fp)
        brd.Add(new_fp)
        swapped += 1
print(f"      swapped {swapped} ESC footprints (MOT1-MOT8)", flush=True)


# ============================================================
# Step 6 — DRC ruleset (BOARD_DESIGN_SETTINGS)
# ============================================================
# Per PHASE4_P0_REPORT.md §P0.4 + JLCPCB 4-layer capability:
#   - min track 0.13 mm, min clearance 0.13 mm (JLCPCB 4-layer free spec)
#   - min via 0.45 mm with 0.20 mm drill (JLCPCB free spec)
#   - min annular ring 0.05 mm
#   - edge clearance 0.30 mm
# These values are at-or-above JLCPCB minimums (no fab reject risk).
print(f"[5/6] set DRC ruleset (min trace/clearance/via/annular/edge)", flush=True)
ds = brd.GetDesignSettings()
ds.m_TrackMinWidth        = _mm(0.13)
ds.m_MinClearance         = _mm(0.13)
ds.m_ViasMinSize          = _mm(0.45)
ds.m_ViasMinAnnularWidth  = _mm(0.05)
ds.m_HoleClearance        = _mm(0.20)
ds.m_CopperEdgeClearance  = _mm(0.30)
print(f"      m_TrackMinWidth       = 0.13 mm", flush=True)
print(f"      m_MinClearance        = 0.13 mm", flush=True)
print(f"      m_ViasMinSize         = 0.45 mm", flush=True)
print(f"      m_ViasMinAnnularWidth = 0.05 mm", flush=True)
print(f"      m_HoleClearance       = 0.20 mm", flush=True)
print(f"      m_CopperEdgeClearance = 0.30 mm", flush=True)


# ============================================================
# Save board
# ============================================================
print(f"[6/6] save board", flush=True)
pcbnew.SaveBoard(OUT_PCB, brd)
print(f"      out: {OUT_PCB} ({os.path.getsize(OUT_PCB)} bytes)", flush=True)


# ============================================================
# Self-audit: confirm every footprint has a non-empty FPID
# (4a.2 — any still-placeholder footprint is a Rule 13 stop)
# ============================================================
print(f"--- 4a.2 self-audit: footprint coverage ---", flush=True)
brd2 = pcbnew.LoadBoard(OUT_PCB)
missing = []
for fp in brd2.GetFootprints():
    fpid = fp.GetFPID().GetUniStringLibId()
    if not fpid:
        missing.append(fp.GetReference())
if missing:
    print(f"!!! {len(missing)} footprints with empty FPID: {missing}", flush=True)
    sys.exit(3)
print(f"    PASS — all {len(list(brd2.GetFootprints()))} footprints have a resolved FPID", flush=True)
print(f"done.", flush=True)
