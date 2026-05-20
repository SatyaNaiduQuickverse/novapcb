#!/usr/bin/env python3
"""
Phase 4 P0 routing-approach SCALE TEST — build a real pcbnew board from the
actual novapcb.net (73 components / 56 nets / 9 sheets), export Specctra DSN.

This is the realistic-scale smoke test per the Phase 3a P0 lesson:
a toy 2-component test would prove only that the API exists, not that the
toolchain scales. The novapcb netlist IS the workload.

Tool used: kinet2pcb 1.1.4 (xesscorp / SKiDL ecosystem; pip-installed).
"""

import os, sys, shutil, time
import pcbnew

NETLIST = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                       "..", "..", "novapcb", "novapcb.net"))
OUT_PCB = os.path.abspath(os.path.join(os.path.dirname(__file__), "scaletest.kicad_pcb"))
OUT_DSN = os.path.abspath(os.path.join(os.path.dirname(__file__), "scaletest.dsn"))

assert os.path.exists(NETLIST), f"Netlist not found: {NETLIST}"
print(f"[1/4] netlist: {NETLIST} ({os.path.getsize(NETLIST)} bytes)", flush=True)

t0 = time.time()
print(f"[2/4] kinet2pcb netlist -> board (placing in hierplace grid)...", flush=True)
from kinet2pcb import kinet2pcb
try:
    kinet2pcb(netlist=NETLIST, brds=[OUT_PCB])
except TypeError:
    kinet2pcb(NETLIST, OUT_PCB)
elapsed = time.time() - t0
print(f"       kinet2pcb produced {OUT_PCB} in {elapsed:.1f}s "
      f"({os.path.getsize(OUT_PCB)} bytes)", flush=True)

print(f"[3/4] open board + set 4-layer stackup (DECISIONS §8) + add outline...", flush=True)
brd = pcbnew.LoadBoard(OUT_PCB)

# kinet2pcb defaults to 2-layer. Switch to 4-layer per DECISIONS §8.
brd.SetCopperLayerCount(4)

# kinet2pcb's hierplace grid produces overlapping pads / unrouteable density
# for this netlist. Re-place: simple scatter on a 60x60mm grid with 7mm
# component spacing. This is NOT Phase 4b placement quality — it's just
# enough spread for Freerouting to have routable space + to scale-test the
# toolchain. Phase 4b does real placement based on the Phase 2.5 sketch.
fps_for_scatter = [fp for fp in brd.GetFootprints()
                   if fp.GetReference() not in ("REF**",)]
SPACING_MM = 7
COLS = 10
import pcbnew as _pn
for i, fp in enumerate(fps_for_scatter):
    row = i // COLS
    col = i % COLS
    x_mm = 3 + col * SPACING_MM
    y_mm = -(3 + row * SPACING_MM)
    fp.SetPosition(_pn.VECTOR2I(int(x_mm * 1e6), int(y_mm * 1e6)))
print(f"       re-placed {len(fps_for_scatter)} footprints on "
      f"{COLS}-col scatter grid, {SPACING_MM}mm spacing", flush=True)

fps = list(brd.GetFootprints())
nets = brd.GetNetsByName()
tracks = list(brd.GetTracks())
print(f"       footprints (placed): {len(fps)}", flush=True)
print(f"       nets (in board): {nets.size()}", flush=True)
print(f"       tracks pre-routing: {len(tracks)}", flush=True)
print(f"       copper layer count: {brd.GetCopperLayerCount()}", flush=True)

# Add 36x36mm board outline on Edge.Cuts (DECISIONS §2 v1 outline)
# kinet2pcb places fps starting at origin; outline must enclose them.
# Inspect placement bounding box to know how to encompass.
bbox = brd.GetBoundingBox()
print(f"       fp bbox: {bbox.GetX()/1e6:.1f},{bbox.GetY()/1e6:.1f} "
      f"{bbox.GetWidth()/1e6:.1f}x{bbox.GetHeight()/1e6:.1f} mm", flush=True)

# Outline ~80x80mm encompassing the scatter placement (P0 scale-test only; real
# Phase 4 uses 36x36 with smarter placement). PURPOSE here is for Freerouting
# to have a closed boundary; tighter packing isn't the P0 question.
OUT_X = -5_000_000
OUT_Y = -90_000_000
OUT_W = 90_000_000
OUT_H = 95_000_000
print(f"       outline placed at {OUT_X/1e6:.1f},{OUT_Y/1e6:.1f} "
      f"{OUT_W/1e6:.1f}x{OUT_H/1e6:.1f} mm", flush=True)
for (x0, y0, x1, y1) in [
    (OUT_X,        OUT_Y,        OUT_X+OUT_W,  OUT_Y),
    (OUT_X+OUT_W,  OUT_Y,        OUT_X+OUT_W,  OUT_Y+OUT_H),
    (OUT_X+OUT_W,  OUT_Y+OUT_H,  OUT_X,        OUT_Y+OUT_H),
    (OUT_X,        OUT_Y+OUT_H,  OUT_X,        OUT_Y),
]:
    seg = pcbnew.PCB_SHAPE(brd)
    seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
    seg.SetLayer(pcbnew.Edge_Cuts)
    seg.SetStart(pcbnew.VECTOR2I(x0, y0))
    seg.SetEnd(pcbnew.VECTOR2I(x1, y1))
    seg.SetWidth(int(0.15e6))
    brd.Add(seg)
pcbnew.SaveBoard(OUT_PCB, brd)

# Audit which footprints succeeded vs. which got placeholder/missing
missing_fp = [fp.GetReference() for fp in fps
              if fp.GetFPID().GetLibItemName() == "" or
                 fp.GetFPID().GetUniStringLibId() == ""]
print(f"       footprints with empty FPID: {len(missing_fp)} "
      f"({missing_fp[:8]}{'...' if len(missing_fp)>8 else ''})", flush=True)

print(f"[4/4] export Specctra DSN...", flush=True)
t0 = time.time()
ok = pcbnew.ExportSpecctraDSN(brd, OUT_DSN)
elapsed = time.time() - t0
print(f"       ExportSpecctraDSN returned {ok} in {elapsed:.1f}s", flush=True)
if os.path.exists(OUT_DSN):
    print(f"       DSN: {OUT_DSN} ({os.path.getsize(OUT_DSN)} bytes)", flush=True)
else:
    print(f"       !!! DSN NOT WRITTEN — Specctra export failed", flush=True)
    sys.exit(2)

print("done — DSN ready for Freerouting scale test.")
