#!/usr/bin/env python3
"""Step 5 residual hand-route — close the 4 unconnected items left by
Freerouting on the 80×60 6-layer board.

Residuals from DRC (after zone fill):
  1. +3V3 gap between (44.7, 40.0) and (45.5, 37.3) on F.Cu — short
     ~3 mm joining segment between two Freerouting-placed +3V3 fan-out
     tracks. Add a single track segment.
  2. SDMMC1_D0: R52 pad (31.1, 28.06) on B.Cu ↔ track endpoint
     (35.7, 36.8) on B.Cu. Same layer; add L-shaped track.
  3. SDMMC1_D2: J2 pad 9 (33.66, 37.7) on B.Cu ↔ track endpoint
     (42.8, 27.3) on F.Cu. Cross layers — add via + L-shaped tracks.
  4. SDMMC1_D3: U1 pad 79 (44.03, 22.32) on F.Cu ↔ track endpoint
     (31.1, 24.19) on B.Cu. Cross layers — add via + tracks.

Each hand-route uses 0.20 mm track width (Default netclass) and
0.4/0.2 mm via (drill/inner-diameter standard).
"""

import os
import sys
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB_PATH = os.path.join(HERE, "novapcb-layout-v2.kicad_pcb")

TRACK_WIDTH_MM = 0.20
VIA_OUTER_MM = 0.45
VIA_DRILL_MM = 0.20


def _mm(x):
    return int(x * 1_000_000)


def add_track(brd, x1, y1, x2, y2, layer, net):
    t = pcbnew.PCB_TRACK(brd)
    t.SetStart(pcbnew.VECTOR2I(_mm(x1), _mm(y1)))
    t.SetEnd(pcbnew.VECTOR2I(_mm(x2), _mm(y2)))
    t.SetLayer(layer)
    t.SetWidth(_mm(TRACK_WIDTH_MM))
    t.SetNet(net)
    brd.Add(t)


def add_via(brd, x, y, net, top=pcbnew.F_Cu, bot=pcbnew.B_Cu):
    v = pcbnew.PCB_VIA(brd)
    v.SetPosition(pcbnew.VECTOR2I(_mm(x), _mm(y)))
    v.SetWidth(_mm(VIA_OUTER_MM))
    v.SetDrill(_mm(VIA_DRILL_MM))
    v.SetLayerPair(top, bot)
    v.SetNet(net)
    brd.Add(v)


def main():
    print(f"[1/3] load {PCB_PATH}")
    brd = pcbnew.LoadBoard(PCB_PATH)
    nets = {str(k): v for k, v in brd.GetNetsByName().asdict().items()}

    # ============================================================
    # Residual 1 — +3V3 short gap on F.Cu
    # ============================================================
    print(f"[2/3] residual 1: +3V3 short gap (44.7, 40.0) → (45.5, 37.3) F.Cu")
    n_3v3 = nets["+3V3"]
    # Single segment connecting the two endpoints
    add_track(brd, 44.7, 40.0127, 45.53, 37.3093, pcbnew.F_Cu, n_3v3)
    print(f"      added F.Cu segment +3V3")

    # ============================================================
    # Residual 2 — SDMMC1_D0: R52 pad (B.Cu) → track endpoint (B.Cu)
    # ============================================================
    print(f"[2/3] residual 2: SDMMC1_D0 R52 (31.1, 28.06) → (35.7, 36.82) B.Cu")
    n_d0 = nets["SDMMC1_D0"]
    # L-shape: go up first, then east
    add_track(brd, 31.1, 28.06, 31.1, 36.82, pcbnew.B_Cu, n_d0)
    add_track(brd, 31.1, 36.82, 35.705, 36.8233, pcbnew.B_Cu, n_d0)
    print(f"      added B.Cu L-shape for SDMMC1_D0")

    # ============================================================
    # Residual 3 — SDMMC1_D2: J2 pad B.Cu → track F.Cu (cross-layer)
    # ============================================================
    print(f"[2/3] residual 3: SDMMC1_D2 J2 pad (33.66, 37.7, B.Cu) → (42.8, 27.3, F.Cu)")
    n_d2 = nets["SDMMC1_D2"]
    # Run track on B.Cu from J2 pad to a via location, then via to F.Cu,
    # then track on F.Cu to existing endpoint.
    via_x, via_y = 39.5, 27.3  # via E of MCU on B.Cu/F.Cu
    # B.Cu segment: J2 pad → via
    add_track(brd, 33.655, 37.725, 33.655, via_y, pcbnew.B_Cu, n_d2)
    add_track(brd, 33.655, via_y, via_x, via_y, pcbnew.B_Cu, n_d2)
    # Via
    add_via(brd, via_x, via_y, n_d2)
    # F.Cu segment: via → existing track endpoint
    add_track(brd, via_x, via_y, 42.803, 27.331, pcbnew.F_Cu, n_d2)
    print(f"      added L-shape (B.Cu) + via + segment (F.Cu) for SDMMC1_D2")

    # ============================================================
    # Residual 4 — SDMMC1_D3: U1 pad F.Cu → track B.Cu (cross-layer)
    # ============================================================
    print(f"[2/3] residual 4: SDMMC1_D3 U1 pad (44.03, 22.32, F.Cu) → (31.1, 24.19, B.Cu)")
    n_d3 = nets["SDMMC1_D3"]
    via_x, via_y = 33.0, 22.32  # via SW of MCU
    # F.Cu: MCU pad → via_x at same Y
    add_track(brd, 44.03, 22.325, via_x, 22.325, pcbnew.F_Cu, n_d3)
    add_via(brd, via_x, via_y, n_d3)
    # B.Cu: via → existing track endpoint
    add_track(brd, via_x, via_y, via_x, 24.19, pcbnew.B_Cu, n_d3)
    add_track(brd, via_x, 24.19, 31.1, 24.19, pcbnew.B_Cu, n_d3)
    print(f"      added segment (F.Cu) + via + L-shape (B.Cu) for SDMMC1_D3")

    # ============================================================
    print(f"[3/3] re-fill zones + save")
    filler = pcbnew.ZONE_FILLER(brd)
    filler.Fill(list(brd.Zones()))
    pcbnew.SaveBoard(PCB_PATH, brd)
    print(f"      saved: {PCB_PATH} ({os.path.getsize(PCB_PATH)} bytes)")


if __name__ == "__main__":
    main()
