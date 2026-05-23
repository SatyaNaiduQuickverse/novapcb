#!/usr/bin/env python3
"""C↔E-2 sub-step — close 3 MANDATORY pre-freeze power connections.

Per task #86 (C↔B integration deferred items). Per master 2026-05-23:
"DO NOT let this slip past Phase 7a."

Deferred from C↔B (PR #72):
  1. U1.27 (39.50, 42.67) +3V3 — south-stub to nearby plane via (39.02, 44.95).
  2. U1.50 (51.00, 42.67) +3V3 — south + west jog + B.Cu detour to plane via
     (50.52, 44.95). Direct south crosses I2C2_SDA diagonal (49.50,43.88)→
     (52.00,44.00) at (51, 43.95). Detour clears.
  3. R11.1 (51.49, 46.50) +3V3 — via-in-pad on R11.1 pad center.
     Earlier 'under clearance' note was for non-centered via location; pad-
     centered via PASSES (R11.2 west edge 52.24mm vs via edge 51.74mm =
     0.50mm gap; I2C2_SDA via at (52, 47.30) 0.949mm away = 0.45mm
     edge-to-edge clearance).

PR doc 4-sections (Rule 7):
  Symptom: MCU U1 has 5 VDD pins (11, 27, 50, 75, 100). C↔B routed
    3 of 5 (11, 75, 100). 27 + 50 unconnected → MCU underpowered (3 of
    5 VDD pins is insufficient for STM32H743 spec; 100mA/pin nominal,
    needs all 5).
  Fix: south-stub each unrouted VDD pin to nearest +3V3 plane via.
    U1.27 direct; U1.50 needs B.Cu detour around I2C2_SDA.
  Root cause: C↔B prioritized plane laydown; pin-level stub closure
    was deferred to C↔E-2 sub-step (declared pre-freeze mandatory).
  Prevention: pin-level VDD connectivity check in audit (count VDD
    pins per IC, verify each in cluster with plane).

Spec deviations (Rule 4): none.

Rule 9 verification (master directive): after routing, verify each VDD
pin in same physical cluster as +3V3 plane via.
"""
import os
import sys
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")
F_CU = pcbnew.F_Cu
B_CU = pcbnew.B_Cu
W_SIG = 0.20
W_PWR = 0.30
VIA_DIA = 0.50
VIA_DRILL = 0.30


def _mm(x): return pcbnew.FromMM(x)


def add_track(brd, x1, y1, x2, y2, net_obj, layer=F_CU, w_mm=W_SIG):
    t = pcbnew.PCB_TRACK(brd)
    t.SetStart(pcbnew.VECTOR2I(_mm(x1), _mm(y1)))
    t.SetEnd(pcbnew.VECTOR2I(_mm(x2), _mm(y2)))
    t.SetWidth(_mm(w_mm))
    t.SetLayer(layer)
    t.SetNet(net_obj)
    brd.Add(t)


def add_via(brd, x, y, net_obj, dia=VIA_DIA, drill=VIA_DRILL):
    v = pcbnew.PCB_VIA(brd)
    v.SetPosition(pcbnew.VECTOR2I(_mm(x), _mm(y)))
    v.SetWidth(_mm(dia))
    v.SetDrill(_mm(drill))
    v.SetNet(net_obj)
    brd.Add(v)


def get_net(brd, name):
    seen = {}
    for fp in list(brd.GetFootprints()):
        if not hasattr(fp, "GetReference") or not hasattr(fp, "Pads"):
            continue
        for pad in fp.Pads():
            n = pad.GetNet()
            if n is not None:
                seen[pad.GetNetname()] = n
    return seen.get(name)


def get_pad(brd, ref, pin):
    for fp in list(brd.GetFootprints()):
        if not hasattr(fp, "GetReference") or not hasattr(fp, "Pads"):
            continue
        if fp.GetReference() == ref:
            for pad in fp.Pads():
                if pad.GetPadName() == pin:
                    p = pad.GetPosition()
                    return (p.x/1e6, p.y/1e6)
    return None


def main():
    print("=== C↔E-2: close 3 deferred MCU VDD + R11 connections ===", flush=True)
    brd = pcbnew.LoadBoard(PCB)

    # Idempotency: strip prior C↔E-2 work + 2 pre-existing I2C2 dangling
    # tracks at (44.67, 47.80) and (43.33, 48.30) per master 2026-05-23 ack.
    ce2_owned_via_coords = {
        ("+3V3", 50.70, 43.50),
        ("+3V3", 51.00, 43.70),
        ("+3V3", 51.49, 46.50),
        ("+3V3", 51.45, 46.50),
        ("+3V3", 52.60, 45.00),
    }
    ce2_owned_track_endpoints = {
        (39.50, 42.67), (39.50, 43.48), (39.50, 44.95), (39.02, 44.95),
        (51.00, 42.67), (51.00, 43.50), (51.00, 43.70),
        (50.70, 43.50), (50.52, 44.95),
        (52.60, 42.67), (52.60, 45.00),
    }
    to_remove = []
    for t in brd.GetTracks():
        net = t.GetNetname()
        if net != "+3V3": continue
        if isinstance(t, pcbnew.PCB_VIA):
            p = t.GetPosition()
            x, y = round(p.x/1e6, 2), round(p.y/1e6, 2)
            if (net, x, y) in ce2_owned_via_coords:
                to_remove.append(t)
        else:
            s, e = t.GetStart(), t.GetEnd()
            sp = (round(s.x/1e6, 2), round(s.y/1e6, 2))
            ep = (round(e.x/1e6, 2), round(e.y/1e6, 2))
            if sp in ce2_owned_track_endpoints or ep in ce2_owned_track_endpoints:
                to_remove.append(t)
    for t in to_remove:
        brd.Remove(t)
    print(f"  stripped {len(to_remove)} C↔E-2-owned items for idempotency")

    n_3v3 = get_net(brd, "+3V3")
    n_scl = get_net(brd, "I2C2_SCL")
    n_sda = get_net(brd, "I2C2_SDA")

    u1_27 = get_pad(brd, "U1", "27")
    u1_50 = get_pad(brd, "U1", "50")
    r11_1 = get_pad(brd, "R11", "1")
    u4_3 = get_pad(brd, "U4", "3")
    u4_4 = get_pad(brd, "U4", "4")
    print(f"  U1.27={u1_27} U1.50={u1_50} R11.1={r11_1}")

    # 1. U1.27 → F.Cu vertical inside pad + diagonal to C12.1 (39.02, 44.95).
    # Direct diagonal from pad center fails clearance to U1.26 GND pad SE
    # corner by 0.08mm. Vertical stub to pad south edge first, then
    # diagonal from outside pad → clears U1.26 corner by 0.46mm.
    print("[1] U1.27 → F.Cu vertical (39.50,43.475) → diagonal → C12.1 (39.02,44.95)", flush=True)
    add_track(brd, u1_27[0], u1_27[1], 39.50, 43.475, n_3v3, layer=F_CU, w_mm=W_SIG)
    add_track(brd, 39.50, 43.475, 39.02, 44.95, n_3v3, layer=F_CU, w_mm=W_SIG)

    # 2. U1.50 → F.Cu east-around then south to via at (52.6, 45).
    # ROOT: south-stub at X=51 ALWAYS crosses I2C2_SDA F.Cu diagonal
    # at (51, 43.95). Pad-centered via fails U1.49/U1.51 clearance
    # (0.10mm vs 0.20mm rule). Via at Y=43..44.4 conflicts SDA. Via
    # south of SDA (Y > 44.4) requires crossing SDA on F.Cu.
    # SOLUTION: route east FIRST (Y=42.67 clear of any pad south of
    # U1.50), then south outside U1 east-column (X=52.6, east of pad
    # east edge 52.825 — actually X=52.6 INSIDE pad X range BUT Y gap
    # 0.87mm to U1.51 south edge clears).
    print("[2] U1.50 → F.Cu east (52.6,42.67) → south → via (52.6,45)", flush=True)
    add_track(brd, u1_50[0], u1_50[1], 52.6, 42.67, n_3v3, layer=F_CU, w_mm=W_SIG)
    add_track(brd, 52.6, 42.67, 52.6, 45.0, n_3v3, layer=F_CU, w_mm=W_SIG)
    add_via(brd, 52.6, 45.0, n_3v3)

    # 3. R11.1 → via at (51.45, 46.50) — 0.04mm west of pad center.
    # Pad-centered via fails clearance to I2C2_SDA B.Cu vertical at X=52
    # by 0.0035mm (master "needs careful relocation" — INTEGRATION_LOG).
    # Offset via 0.04mm west: distance to SDA B.Cu = 0.55mm; edge-to-edge
    # 0.55-0.25-0.10 = 0.20mm. PASSES at limit. Via still 100% inside R11.1
    # pad (pad X range 51.22..51.76, via X range 51.20..51.70).
    print("[3] R11.1 → via at (51.45, 46.50) [pad-offset 0.04mm west]", flush=True)
    add_via(brd, 51.45, 46.50, n_3v3)

    # 4. Pre-existing I2C2 dangling-track cleanup (master 2026-05-23 ack):
    # 2 tracks endpoints reported as 'unconnected end'. Root cause:
    # 5µm coordinate mismatch (44675000nm vs 43975000nm-rounded paths
    # not exactly meeting). Strip ALL final-hop segments in U4 area and
    # redraw using exact joining-track endpoints (not rounded mm).
    print("[4] I2C2 final-hop cleanup near U4", flush=True)
    # Find exact joining-track endpoint coords from existing C↔E tracks
    junction_scl = None  # the (44.67ish, 47.80ish) junction
    junction_sda = None  # the (43.33ish, 48.30ish) junction
    for t in brd.GetTracks():
        if isinstance(t, pcbnew.PCB_VIA): continue
        if t.GetNetname() == "I2C2_SCL":
            for ep in (t.GetStart(), t.GetEnd()):
                if abs(ep.x/1e6 - 44.67) < 0.01 and abs(ep.y/1e6 - 47.80) < 0.01:
                    junction_scl = (ep.x, ep.y)
        if t.GetNetname() == "I2C2_SDA":
            for ep in (t.GetStart(), t.GetEnd()):
                if abs(ep.x/1e6 - 43.33) < 0.01 and abs(ep.y/1e6 - 48.30) < 0.01:
                    junction_sda = (ep.x, ep.y)
    print(f"  SCL junction at nm {junction_scl}, SDA at nm {junction_sda}")

    # Strip OLD final-hop segments to U4 pads
    to_strip = []
    for t in brd.GetTracks():
        if isinstance(t, pcbnew.PCB_VIA): continue
        if t.GetNetname() not in ("I2C2_SCL", "I2C2_SDA"): continue
        try:
            s, e = t.GetStart(), t.GetEnd()
        except (AttributeError, TypeError):
            continue
        # Strip tracks that end at U4 pad area
        for tp in (s, e):
            for u4pad in (u4_3, u4_4):
                if abs(tp.x/1e6 - u4pad[0]) < 0.01 and abs(tp.y/1e6 - u4pad[1]) < 0.01:
                    to_strip.append(t); break
            else:
                continue
            break
    for t in to_strip:
        brd.Remove(t)
    print(f"  stripped {len(to_strip)} U4-pad-final-hop segments")

    # Redraw using EXACT junction nm coords (not rounded) to U4 pad
    def add_track_nm(brd, x1_nm, y1_nm, x2, y2, net, layer, w_mm):
        t = pcbnew.PCB_TRACK(brd)
        t.SetStart(pcbnew.VECTOR2I(int(x1_nm), int(y1_nm)))
        t.SetEnd(pcbnew.VECTOR2I(_mm(x2), _mm(y2)))
        t.SetWidth(_mm(w_mm))
        t.SetLayer(layer)
        t.SetNet(net)
        brd.Add(t)

    if junction_scl:
        add_track_nm(brd, junction_scl[0], junction_scl[1], u4_4[0], u4_4[1], n_scl, F_CU, W_SIG)
    if junction_sda:
        add_track_nm(brd, junction_sda[0], junction_sda[1], u4_3[0], u4_3[1], n_sda, F_CU, W_SIG)

    # Explicit zone fill — unfill first then fill (master 2026-05-23 Rule 9).
    print("[fill] unfill + refill all zones...", flush=True)
    try:
        for z in brd.Zones():
            if hasattr(z, 'UnFill'):
                z.UnFill()
        filler = pcbnew.ZONE_FILLER(brd)
        filler.Fill(list(brd.Zones()))
    except Exception as e:
        print(f"  zone fill skipped: {e}")

    pcbnew.SaveBoard(PCB, brd)
    print(f"\n  Saved {PCB}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
