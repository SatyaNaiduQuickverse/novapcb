#!/usr/bin/env python3
"""Convert L4 (In3.Cu) from +5V plane to signal layer (master 2026-05-22).

Removes the +5V zone fills on In3.Cu so the layer becomes routing
space. Keeps L2/L5 GND and L3 +3V3 planes intact.

Pour +5V as a small filled zone on L1 near power consumers
(rather than leaving +5V unconnected — Freerouting still needs to
connect +5V loads). Simpler: leave +5V to be ROUTED as a wide
power trace by Freerouting (it's not a plane anymore).

Stackup result:
  L1 Signal (F.Cu)
  L2 GND plane (In1.Cu)
  L3 +3V3 plane (In2.Cu)
  L4 SIGNAL (In3.Cu) — was +5V plane
  L5 GND plane (In4.Cu)
  L6 Signal (B.Cu)

+50% routing room; every signal layer adjacent to a reference plane.
"""
import os
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-layout-v1.1.kicad_pcb")


def main():
    brd = pcbnew.LoadBoard(PCB)
    # Remove all zones on In3.Cu (the layer becoming signal)
    n_removed = 0
    for z in list(brd.Zones()):
        if z.IsOnLayer(pcbnew.In3_Cu):
            print(f"  removing In3.Cu zone net={z.GetNetname()}")
            brd.Remove(z)
            n_removed += 1
    print(f"\n[L4-rebalance] removed {n_removed} +5V zones from In3.Cu")
    pcbnew.SaveBoard(PCB, brd)
    print("[saved zones]")

    # Now strip routes — load fresh board to avoid SWIG iteration issue
    brd2 = pcbnew.LoadBoard(PCB)
    n_t = n_v = 0
    for t in list(brd2.GetTracks()):
        if isinstance(t, pcbnew.PCB_VIA):
            brd2.Remove(t); n_v += 1
        else:
            brd2.Remove(t); n_t += 1
    print(f"[strip] {n_t} tracks + {n_v} vias removed (fresh route)")
    pcbnew.ZONE_FILLER(brd2).Fill(list(brd2.Zones()))
    pcbnew.SaveBoard(PCB, brd2)
    print("[saved]")


if __name__ == "__main__":
    main()
