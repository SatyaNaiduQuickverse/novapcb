#!/usr/bin/env python3
"""
Fix the 11 DRC violations introduced by run_stitch_plane_nets.py.

Per master directive 2026-05-21: don't hand-wave; fix each violation
genuinely; re-check the FULL set for misses.

Strategy:
  - Delete 5 stitch vias whose placement causes pad-clearance violations
    against a neighbor component's pad. The plane-net pad these were
    serving will revert to unconnected (still better than a short).
  - For starved_thermal at U4 (DPS310 baro, B.Cu) and U7 (LPS22HB, F.Cu):
    add a direct via-through-pad-area to bypass the single-spoke thermal
    relief connection (proper electrical connection to the GND plane).

Specific vias to delete (from DRC report against current board):
  1. (43.14,  4.00) +3V3 — SHORT vs J13 MOT3 pad
  2. (54.01, 35.00) +3V3 — 0.129mm vs Y1 GND pad
  3. (66.83, 29.60) +3V3 — 0.198mm vs U4 GND pad 1
  4. (66.83, 30.40) GND  — 0.198mm vs U4 +3V3 pad 6
  5. (66.18, 31.20) +3V3 — 0.198mm vs U4 GND pad 5
  6. (30.51, 33.70) +3V3 — 0.184mm vs C22 GND pad
  7. (83.17, 37.26) +5V  — 0.193mm vs U14 CAN1_RX pad
"""
import os
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-layout-v1.1.kicad_pcb")

# (X_mm, Y_mm, net_name) of vias to DELETE. Tolerance 0.05mm position match.
VIAS_TO_DELETE = [
    (43.1413, 3.9981, "+3V3"),
    (54.0100, 35.0000, "+3V3"),
    (66.8250, 29.6000, "+3V3"),
    (66.8250, 30.4000, "GND"),
    (66.1750, 31.2000, "+3V3"),
    (30.5100, 33.7000, "+3V3"),
    (83.1744, 37.2615, "+5V"),
]

# Manual GND bypass vias for starved_thermal — placed DIRECTLY at pad
# center, will make solid pad-to-plane connection bypassing thermal relief.
# U4 (DPS310 on B.Cu) pad 7 [GND] at (66.825, 30.800)
# U7 (LPS22HB on F.Cu) pad 5 [GND] at (75.500, 30.830)
BYPASS_VIAS = [
    (66.825, 30.800, "GND"),
    (75.500, 30.830, "GND"),
]


def main():
    brd = pcbnew.LoadBoard(PCB)
    nets = {str(k): v for k, v in brd.GetNetsByName().asdict().items()}

    # Delete problematic stitch vias
    deleted = 0
    for t in list(brd.GetTracks()):
        if not isinstance(t, pcbnew.PCB_VIA): continue
        p = t.GetPosition()
        x, y = p.x / 1e6, p.y / 1e6
        netname = t.GetNetname() or ""
        for (vx, vy, vnet) in VIAS_TO_DELETE:
            if abs(x - vx) < 0.05 and abs(y - vy) < 0.05 and netname == vnet:
                brd.Remove(t)
                deleted += 1
                print(f"  DEL via at ({x:.3f}, {y:.3f}) net={netname}")
                break
    print(f"deleted {deleted} bad stitch vias (expected {len(VIAS_TO_DELETE)})")

    # Add bypass vias for starved_thermal pads
    added = 0
    for vx, vy, vnet in BYPASS_VIAS:
        nv = pcbnew.PCB_VIA(brd)
        nv.SetPosition(pcbnew.VECTOR2I(int(vx * 1e6), int(vy * 1e6)))
        nv.SetWidth(int(0.46e6))
        nv.SetDrill(int(0.20e6))
        nv.SetViaType(pcbnew.VIATYPE_THROUGH)
        nv.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        if vnet in nets: nv.SetNet(nets[vnet])
        brd.Add(nv)
        added += 1
        print(f"  ADD via at ({vx:.3f}, {vy:.3f}) net={vnet} (bypass thermal relief)")
    print(f"added {added} thermal-bypass vias")

    # Refill zones
    pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
    pcbnew.SaveBoard(PCB, brd)
    print(f"saved {PCB}")


if __name__ == "__main__":
    main()
