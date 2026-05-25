#!/usr/bin/env python3
"""Convert to 4-signal stackup (master 2026-05-22 Option A).

NEW: L1 Sig / L2 GND / L3 SIGNAL / L4 SIGNAL / L5 GND / L6 Sig

Changes from prior (3-signal):
- Remove +3V3 zones from In2.Cu (L3 becomes signal)
- L4 already has no plane (from earlier rebalance)
- Add +3V3 pour on L1 (W power + MCU region for short via stitches)
- Add +5V pour on L1 (W power block for 3A current capacity)
- Strip all routes (fresh re-route required)

Mitigation: L3/L4 are adjacent signals (no plane between). Per master:
route SENSITIVE nets (3 IMU SPIs + USB pair) on OUTER layers L1/L6
(well-referenced to L2/L5 GND). Bulk routing on L3/L4.
"""
import os
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-layout-v1.1.kicad_pcb")


def add_pour(brd, net_obj, layer, poly, clearance=0.20):
    z = pcbnew.ZONE(brd)
    z.SetLayer(layer)
    z.SetNet(net_obj)
    z.SetIsFilled(True)
    z.SetLocalClearance(int(clearance * 1e6))
    pts = pcbnew.VECTOR_VECTOR2I()
    for x, y in poly:
        pts.append(pcbnew.VECTOR2I(int(x*1e6), int(y*1e6)))
    z.AddPolygon(pts)
    brd.Add(z)
    return z


def main():
    brd = pcbnew.LoadBoard(PCB)
    # Remove +3V3 zones from In2.Cu (L3 becomes signal)
    removed = 0
    for z in list(brd.Zones()):
        if z.IsOnLayer(pcbnew.In2_Cu) and z.GetNetname() == "+3V3":
            print(f"  removing In2.Cu +3V3 zone")
            brd.Remove(z); removed += 1
    print(f"[L3] removed {removed} +3V3 zones")

    pcbnew.SaveBoard(PCB, brd)
    # Reload to strip routes (avoid SWIG iteration issue)
    brd2 = pcbnew.LoadBoard(PCB)
    n_t = n_v = 0
    for t in list(brd2.GetTracks()):
        if isinstance(t, pcbnew.PCB_VIA):
            brd2.Remove(t); n_v += 1
        else:
            brd2.Remove(t); n_t += 1
    print(f"[strip] {n_t} tracks + {n_v} vias")
    pcbnew.SaveBoard(PCB, brd2)
    # Reload for pour adds
    brd2 = pcbnew.LoadBoard(PCB)
    nets = {str(k): v for k, v in brd2.GetNetsByName().asdict().items()}

    # +5V pour on L1 (F.Cu) — W power block for 3A capacity
    POUR_5V = [(2,14), (30,14), (30,56), (2,56)]
    add_pour(brd2, nets["+5V"], pcbnew.F_Cu, POUR_5V)
    print("[pour] +5V on L1 W block (2-30 X, 14-56 Y)")

    # +3V3 pour on L6 (B.Cu) — covers MCU + sensors region for short via stitches
    POUR_3V3 = [(20,15), (80,15), (80,55), (20,55)]
    add_pour(brd2, nets["+3V3"], pcbnew.B_Cu, POUR_3V3)
    print("[pour] +3V3 on L6 MCU+sensors (20-80 X, 15-55 Y)")

    pcbnew.ZONE_FILLER(brd2).Fill(list(brd2.Zones()))
    pcbnew.SaveBoard(PCB, brd2)
    print("[saved]")


if __name__ == "__main__":
    main()
