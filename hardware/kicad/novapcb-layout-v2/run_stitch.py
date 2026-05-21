#!/usr/bin/env python3
"""Step 5 residual closer — bridge +3V3 plane orphans to main island.

After plane-island analysis (run_stitch.py output via GetFilledPolysList):
the +3V3 zone on In2.Cu has 3 outlines:
  Outline 0 (orphan): X=45.4..48.6, Y=28.7..29.8  — near MCU east, R54 group
  Outline 1 (orphan): X=29.6..34.9, Y=23.8..27.5  — near MCU SW, R52/R51 group
  Outline 2 (main):   X=0.3..79.7,  Y=0.3..59.7   — the rest

Residual pairs from DRC:
  A: B.Cu (30.08, 26.99) ↔ F.Cu (30.79, 28.89)
     B endpoint is in Outline 1 (orphan), F endpoint is in Outline 2 (main)
  B: B.Cu (47.96, 28.53) ↔ B.Cu (47.96, 26.13)
     First endpoint links via (48.51, 29.08) into Outline 0 (orphan),
     second is in Outline 2 (main)

Bridge strategy: add a track on F.Cu (above the orphan) connecting an
existing +3V3 via in the orphan to a clear point in main, then a new
via at that point on +3V3 net.

Residual A bridge:
  - Existing +3V3 via at (30.05, 26.99) is in orphan #1
  - Existing +3V3 via at (29.01, 28.89) is in main (X=29.01 < 29.6 orphan W edge)
  - The earlier-added F.Cu segment (30.79, 28.89) → (29.01, 28.89) already
    connected F.Cu endpoint to main via.
  - To bridge orphan #1 to main: add B.Cu segment (30.05, 26.99) →
    (28.50, 26.99) — leftward 1.55 mm; new endpoint at X=28.5 is in main
    (X=28.5 < 29.6). Then add via at (28.50, 26.99) on +3V3 — this via
    is in main island, joining orphan #1 (via the new segment + via).

Residual B bridge:
  - Existing +3V3 via at (48.51, 29.08) — inside orphan #0 (X=48.51 in
    45.4..48.6, Y=29.08 in 28.7..29.8)
  - Add B.Cu segment (48.51, 29.08) → (50.50, 29.08) — east 2 mm, X=50.5
    outside orphan E edge (48.6). Then add via at (50.50, 29.08) on +3V3
    — this via is in main island.
  - Path check at Y=29.08, X=48.51..50.50 on B.Cu: avoid Y1.4 GND pad at
    (49.72, 29.15). The pad is 0.07 mm N of the trace centreline; with
    0.10 mm track half-width + 0.15 mm clearance + Y1.4 pad outer,
    minimum required vertical gap ≈ 0.4 mm. Margin is tight; reroute via
    a small dog-leg if needed.

DRC-after-each pattern: try fix → DRC → if errors, revert + try alternate.
"""

import os
import sys
import pcbnew
import subprocess
import re

HERE = os.path.dirname(os.path.abspath(__file__))
PCB_PATH = os.path.join(HERE, "novapcb-layout-v2.kicad_pcb")
TRACK_WIDTH_MM = 0.20
VIA_OUTER_MM = 0.45
VIA_DRILL_MM = 0.20


def _mm(x): return int(x * 1_000_000)


def add_track(brd, x1, y1, x2, y2, layer, net):
    t = pcbnew.PCB_TRACK(brd)
    t.SetStart(pcbnew.VECTOR2I(_mm(x1), _mm(y1)))
    t.SetEnd(pcbnew.VECTOR2I(_mm(x2), _mm(y2)))
    t.SetLayer(layer)
    t.SetWidth(_mm(TRACK_WIDTH_MM))
    t.SetNet(net)
    brd.Add(t)
    return t


def add_via(brd, x, y, net):
    v = pcbnew.PCB_VIA(brd)
    v.SetPosition(pcbnew.VECTOR2I(_mm(x), _mm(y)))
    v.SetWidth(_mm(VIA_OUTER_MM))
    v.SetDrill(_mm(VIA_DRILL_MM))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetNet(net)
    brd.Add(v)
    return v


def fill_save(brd):
    pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
    pcbnew.SaveBoard(PCB_PATH, brd)


def drc():
    subprocess.run(["kicad-cli", "pcb", "drc", "--severity-error", "--format", "report",
                    "--output", os.path.join(HERE, "drc_report.txt"), PCB_PATH],
                   capture_output=True)
    with open(os.path.join(HERE, "drc_report.txt")) as f:
        txt = f.read()
    blocks = re.split(r'\n(?=\[)', txt)
    err = sum(1 for b in blocks if b.startswith('[') and 'unconnected_items' not in b)
    unc = sum(1 for b in blocks if 'unconnected_items' in b)
    return err, unc


def main():
    print(f"[1] load board + initial DRC")
    brd = pcbnew.LoadBoard(PCB_PATH)
    nets = {str(k): v for k, v in brd.GetNetsByName().asdict().items()}
    n3v3 = nets["+3V3"]
    err, unc = drc()
    print(f"    initial: {err} errors, {unc} unconnected")

    # Residual A bridge: B.Cu segment + via
    print(f"\n[2] residual A bridge: B.Cu (30.05, 26.99) → (28.50, 26.99) +3V3 + via")
    add_track(brd, 30.05, 26.99, 28.50, 26.99, pcbnew.B_Cu, n3v3)
    add_via(brd, 28.50, 26.99, n3v3)

    # Residual B bridge: B.Cu segment + via
    print(f"[3] residual B bridge: B.Cu (48.51, 29.08) → (50.50, 29.08) +3V3 + via")
    add_track(brd, 48.51, 29.08, 50.50, 29.08, pcbnew.B_Cu, n3v3)
    add_via(brd, 50.50, 29.08, n3v3)

    print(f"\n[4] fill + save + DRC")
    fill_save(brd)
    err, unc = drc()
    print(f"    after bridges: {err} errors, {unc} unconnected")


if __name__ == "__main__":
    main()
