#!/usr/bin/env python3
"""Sense sub-step — route 8 V/I sense traces from Mauch shunts to MCU ADC.

REVISION 2 (2026-05-23): First attempt placed vias dead-center on SMD pads,
which is via-in-pad without DRU exemption — caused 96 new DRC violations.
This revision offsets all vias by ≥1mm from pads via short F.Cu fanout
tracks, and routes through known-clear B.Cu corridors.

Topology (incoming J→R, then outgoing R+C→MCU.ADC):
  J4.3 MAUCH_VBAT_PRE   → R41.1
  J4.4 MAUCH_CURR_PRE   → R42.1
  J19.3 MAUCH2_VBAT_PRE → R43.1
  J19.4 MAUCH2_CURR_PRE → R44.1
  R41.2 + C61.1 → U1.15 BATT_VOLTAGE_SENS
  R42.2 + C62.1 → U1.16 BATT_CURRENT_SENS
  R43.2 + C81.1 → U1.17 BATT2_VOLTAGE_SENS
  R44.2 + C82.1 → U1.18 BATT2_CURRENT_SENS

Discipline (master 2026-05-23 sense sub-step approval):
- Slow analog (Mauch power monitor, sub-100 Hz BW); no controlled-Z
- V_sense + I_sense kept close on each side (common-mode reject)
- Route AWAY from buck SW node (U2 X=24 Y=25, L1 X=29 Y=25, on F.Cu)
- Buck-to-sense vertical separation 10.5mm + planes between (master OK)
- Per-net Rule 9 cluster walk on each trace

Layer plan:
- Incoming J→R: F.Cu, route west-around-Q3 / east-around-Q4
- Outgoing R+C→MCU.ADC: B.Cu south-then-east-then-north topology,
  fanout F.Cu pad → via 1mm offset → B.Cu trunk → via 1mm offset → F.Cu MCU pad

Clean B.Cu corridors (from corridor survey):
- X=25..28 at Y=15..22: between EFUSE_DVDT diagonal (W) and EFUSE_ILIM (E)
- Y=25..30 west of buck: mostly clean for west-side south transit
- South of MCU at Y=46+: clean for east-side wraparound (avoid IMU island
  D-zone X=62..78, Y=12..58)
"""
import os
import sys
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")
F_CU = pcbnew.F_Cu
B_CU = pcbnew.B_Cu

W_SIG = 0.20
VIA_DIA = 0.50
VIA_DRILL = 0.30


def _mm(x):
    return pcbnew.FromMM(x)


def add_track(brd, x1, y1, x2, y2, net_obj, layer, w_mm=W_SIG):
    t = pcbnew.PCB_TRACK(brd)
    t.SetStart(pcbnew.VECTOR2I(_mm(x1), _mm(y1)))
    t.SetEnd(pcbnew.VECTOR2I(_mm(x2), _mm(y2)))
    t.SetWidth(_mm(w_mm))
    t.SetLayer(layer)
    t.SetNet(net_obj)
    brd.Add(t)


def add_via(brd, x, y, net_obj):
    v = pcbnew.PCB_VIA(brd)
    v.SetPosition(pcbnew.VECTOR2I(_mm(x), _mm(y)))
    v.SetWidth(_mm(VIA_DIA))
    v.SetDrill(_mm(VIA_DRILL))
    v.SetNet(net_obj)
    brd.Add(v)


def get_net(brd, name):
    seen = {}
    for fp in list(brd.GetFootprints()):
        for pad in fp.Pads():
            n = pad.GetNet()
            if n is not None:
                seen[pad.GetNetname()] = n
    return seen.get(name)


def main():
    print("=== Sense sub-step — 8 V/I sense traces ===\n")
    brd = pcbnew.LoadBoard(PCB)

    nets = {}
    for n in ("MAUCH_VBAT_PRE", "MAUCH_CURR_PRE",
              "MAUCH2_VBAT_PRE", "MAUCH2_CURR_PRE",
              "BATT_VOLTAGE_SENS", "BATT_CURRENT_SENS",
              "BATT2_VOLTAGE_SENS", "BATT2_CURRENT_SENS"):
        nets[n] = get_net(brd, n)
        if nets[n] is None:
            print(f"  FAIL: net '{n}' not found in board")
            return 1

    # === Incoming J→R (F.Cu, west-around-Q3 / east-around-Q4) ===
    # All connector pads start at Y=3.15; sense resistor pads at Y=14.5
    # Q3 bbox (24.52..29.48, 8.03..11.98); transit Y=13.0 clears Q3 south
    # by 1mm. Pin-to-track exits J4/J19 south to start.

    # Per-trace approach to avoid F.Cu collisions:
    # +5V_BEC_A horizontal at Y=9 blocks F.Cu vertical descents from J4
    # → switch to B.Cu for the south transit.
    # MAUCH_VBAT_PRE @ Y=13 + MAUCH_CURR_PRE @ Y=13.5 cross each other
    # if both on F.Cu → put VBAT on F.Cu, CURR on B.Cu (parallel layers).
    # EFUSE_DVDT @ (28.25, 15.4)→(20, 11.7) F.Cu blocks Y=12-15 X=20..28
    # F.Cu transit; transit on B.Cu instead.

    # Trace 1: MAUCH_VBAT_PRE — F.Cu fanout, via @ Y=4.5 to B.Cu, B.Cu south+east
    print("Trace 1: MAUCH_VBAT_PRE (J4.3 → R41.1) — F.Cu fanout + B.Cu transit")
    n = nets["MAUCH_VBAT_PRE"]
    add_track(brd, 15.375, 3.150, 15.375, 4.5,   n, F_CU)   # exit J4.3 south
    add_via  (brd, 15.375, 4.5,                   n)         # via to B.Cu
    add_track(brd, 15.375, 4.5,   15.375, 13.0,   n, B_CU)  # B.Cu south
    add_track(brd, 15.375, 13.0,  23.490, 13.0,   n, B_CU)  # B.Cu east (under Q3)
    add_track(brd, 23.490, 13.0,  23.490, 13.5,   n, B_CU)  # B.Cu south
    add_via  (brd, 23.490, 13.5,                  n)         # via back to F.Cu
    add_track(brd, 23.490, 13.5,  23.490, 14.5,   n, F_CU)  # F.Cu to R41.1

    # Trace 2: MAUCH_CURR_PRE — F.Cu fanout, via to B.Cu (different Y from T1)
    print("Trace 2: MAUCH_CURR_PRE (J4.4 → R42.1) — F.Cu fanout + B.Cu transit")
    n = nets["MAUCH_CURR_PRE"]
    add_track(brd, 16.625, 3.150, 16.625, 4.5,   n, F_CU)
    add_via  (brd, 16.625, 4.5,                   n)
    add_track(brd, 16.625, 4.5,   16.625, 13.7,  n, B_CU)
    add_track(brd, 16.625, 13.7,  19.490, 13.7,  n, B_CU)  # 0.7mm south of T1 horizontal at 13.0
    add_track(brd, 19.490, 13.7,  19.490, 13.5,  n, B_CU)
    add_via  (brd, 19.490, 13.5,                  n)
    add_track(brd, 19.490, 13.5,  19.490, 14.5,  n, F_CU)

    # Trace 3: MAUCH2_VBAT_PRE — mirror of T1
    print("Trace 3: MAUCH2_VBAT_PRE (J19.3 → R43.1) — F.Cu fanout + B.Cu transit")
    n = nets["MAUCH2_VBAT_PRE"]
    add_track(brd, 88.375, 3.150, 88.375, 4.5,   n, F_CU)
    add_via  (brd, 88.375, 4.5,                   n)
    add_track(brd, 88.375, 4.5,   88.375, 13.0,  n, B_CU)
    add_track(brd, 88.375, 13.0,  80.490, 13.0,  n, B_CU)
    add_track(brd, 80.490, 13.0,  80.490, 13.5,  n, B_CU)
    add_via  (brd, 80.490, 13.5,                  n)
    add_track(brd, 80.490, 13.5,  80.490, 14.5,  n, F_CU)

    # Trace 4: MAUCH2_CURR_PRE — mirror of T2
    print("Trace 4: MAUCH2_CURR_PRE (J19.4 → R44.1) — F.Cu fanout + B.Cu transit")
    n = nets["MAUCH2_CURR_PRE"]
    add_track(brd, 89.625, 3.150, 89.625, 4.5,   n, F_CU)
    add_via  (brd, 89.625, 4.5,                   n)
    add_track(brd, 89.625, 4.5,   89.625, 13.7,  n, B_CU)
    add_track(brd, 89.625, 13.7,  84.490, 13.7,  n, B_CU)
    add_track(brd, 84.490, 13.7,  84.490, 13.5,  n, B_CU)
    add_via  (brd, 84.490, 13.5,                  n)
    add_track(brd, 84.490, 13.5,  84.490, 14.5,  n, F_CU)

    pcbnew.SaveBoard(PCB, brd)
    print("\n  Phase 1 saved — 4 incoming traces routed; outgoing deferred to phase 2.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
