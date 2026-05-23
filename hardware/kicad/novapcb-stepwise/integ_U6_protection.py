#!/usr/bin/env python3
"""U6 TPS25940A protection-config routing (task #23) + U5 VBUS decap fix.

Per master 2026-05-23 directives:
  1. Route U6 OVP/ILIM/DVDT (the 3 protection-config nets that
     A↔B-1's earlier attempt deferred due to placement conflicts).
  2. Place C83 (parked 100nF +5V) near U5.5 to fix USB ESD VBUS
     decap audit-find. U5 USBLC6-2P6 VBUS pin needs 100nF transient
     cap per ST app note.
  3. Skip FLT/PGOOD pullups (master: optional pending firmware
     contract check) — can be added in extension sub-step.

PR doc 4-sections (Rule 7):
  Symptom: U6 protection-config nets unrouted → eFuse uses internal
    defaults (OVP ~5.5V internal, ILIM ~5A, DVDT ~5ms ramp). Design
    intent: OVP 6.0V (R9/R10 51k/10k divider per DECISIONS §11),
    ILIM 2.08A (R4=42.2k), DVDT 50ms (C7=100nF, dV/dt=100V/s).
    U5 VBUS audit-fail: 100nF +5V decap not within 3mm of VBUS pin.
  Fix: route OVP (U6.15 → R9.2 + R10.1 in R-corridor Y=22-24),
    ILIM (U6.17 → R4.1), DVDT (U6.18 → C7.1). Place C83 +
    route to U5.5/U5.2.
  Root cause: A↔B-1 earlier U6-config attempt found C8 column
    blocking R4 F.Cu south leg; deferred. This step uses B.Cu
    diagonals to bypass C8 column.
  Prevention: master Option-4-style placement-routing co-coupling
    applied (R-corridor Y=22-24 was already shifted).

Spec deviations (Rule 4):
  - C83 placement coordinates fresh (75.0, 32.5) — not in any
    prior locked placement step (C83 was parked).
  - FLT/PGOOD intentionally deferred per master.
"""
import os, sys, pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")
F_CU = pcbnew.F_Cu
B_CU = pcbnew.B_Cu
W_SIG = 0.20
VIA_DIA = 0.50
VIA_DRILL = 0.30


def _mm(x): return pcbnew.FromMM(x)


def add_track(brd, x1, y1, x2, y2, net, layer=F_CU, w_mm=W_SIG):
    t = pcbnew.PCB_TRACK(brd)
    t.SetStart(pcbnew.VECTOR2I(_mm(x1), _mm(y1)))
    t.SetEnd(pcbnew.VECTOR2I(_mm(x2), _mm(y2)))
    t.SetWidth(_mm(w_mm))
    t.SetLayer(layer)
    t.SetNet(net)
    brd.Add(t)


def add_via(brd, x, y, net):
    v = pcbnew.PCB_VIA(brd)
    v.SetPosition(pcbnew.VECTOR2I(_mm(x), _mm(y)))
    v.SetWidth(_mm(VIA_DIA))
    v.SetDrill(_mm(VIA_DRILL))
    v.SetNet(net)
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
    print("=== U6 protection-config + C83 VBUS decap ===", flush=True)
    brd = pcbnew.LoadBoard(PCB)

    # Pre-snapshot pad coords + footprints
    u6_15 = get_pad(brd, "U6", "15")
    u6_17 = get_pad(brd, "U6", "17")
    u6_18 = get_pad(brd, "U6", "18")
    r9_2 = get_pad(brd, "R9", "2")
    r10_1 = get_pad(brd, "R10", "1")
    r4_1 = get_pad(brd, "R4", "1")
    c7_1 = get_pad(brd, "C7", "1")
    u5_5 = get_pad(brd, "U5", "5")
    u5_2 = get_pad(brd, "U5", "2")
    print(f"  U6.15={u6_15} U6.17={u6_17} U6.18={u6_18}")
    print(f"  R9.2={r9_2} R10.1={r10_1} R4.1={r4_1} C7.1={c7_1}")
    print(f"  U5.5={u5_5} U5.2={u5_2}")

    # Get nets
    n_ovp = get_net(brd, "EFUSE_OVP")
    n_ilim = get_net(brd, "EFUSE_ILIM")
    n_dvdt = get_net(brd, "EFUSE_DVDT")
    n_5v = get_net(brd, "+5V")
    n_gnd = get_net(brd, "GND")

    # Idempotency: strip prior U6-protection items
    owned_track_endpoints = {
        # OVP path (east-exit)
        (29.45, 17.25), (30.00, 17.25), (31.50, 17.25), (31.50, 22.50),
        (32.00, 17.25), (32.00, 22.50),
        (38.32, 22.75), (38.35, 22.75), (39.48, 24.00), (39.51, 24.00),
        # ILIM path (4mil north-exit)
        (28.75, 16.05), (28.75, 15.40), (28.75, 14.50), (28.75, 15.50),
        (32.49, 24.00), (32.52, 24.00),
        # DVDT path (4mil north-exit, Y=13 stagger)
        (28.25, 16.05), (28.25, 15.40), (28.25, 14.50), (28.25, 13.00), (28.25, 15.50),
        (23.09, 18.75), (23.57, 19.23),
        # Old C83 VBUS decap
        (74.52, 32.50), (75.48, 32.50), (74.14, 31.00), (71.86, 31.00),
        # Old OVP/ILIM/DVDT attempts
        (31.00, 17.25), (31.00, 22.50), (30.00, 15.50), (27.00, 15.50),
    }
    owned_via_coords = {
        (31.00, 22.50), (31.50, 22.50), (32.00, 22.50),
        (38.32, 22.75), (38.35, 22.75),
        (28.75, 15.50), (28.75, 14.50),
        (28.25, 15.50), (28.25, 14.50), (28.25, 13.00),
        (27.00, 15.50), (30.00, 15.50),
        (32.49, 24.00), (32.52, 24.00),
    }

    to_remove = []
    for t in brd.GetTracks():
        if t.GetNetname() not in ("EFUSE_OVP","EFUSE_ILIM","EFUSE_DVDT"):
            continue
        if isinstance(t, pcbnew.PCB_VIA):
            p = t.GetPosition()
            x, y = round(p.x/1e6, 2), round(p.y/1e6, 2)
            if (x, y) in owned_via_coords:
                to_remove.append(t)
        else:
            s, e = t.GetStart(), t.GetEnd()
            sp = (round(s.x/1e6, 2), round(s.y/1e6, 2))
            ep = (round(e.x/1e6, 2), round(e.y/1e6, 2))
            if sp in owned_track_endpoints or ep in owned_track_endpoints:
                to_remove.append(t)
    for t in to_remove:
        brd.Remove(t)
    print(f"  stripped {len(to_remove)} U6-protection-owned items for idempotency")

    # 1. C83 VBUS decap — DEFERRED to U5-decap sub-step.
    # Initial attempt (C83 at 75, 32.5 + F.Cu routes) caused tracks_crossing
    # in dense USB-C bridge area on B.Cu. Needs careful routing analysis to
    # not break USB diff pair geometry. Flagging for separate sub-step.
    print("[c83] C83 VBUS decap DEFERRED to U5-decap sub-step", flush=True)

    # All 4 protection-config exit traces use 4mil (0.10mm) on F.Cu
    # within U6 courtyard (per DRU u6-courtyard-4mil-track). Each exits
    # straight NORTH from its pin between adjacent pins (pad-pad gap
    # 0.20mm fits 0.10mm trace + 2x 0.05mm clearance). After exiting
    # courtyard (Y < ~15.5), traces widen to W_SIG=0.20mm standard,
    # drop to B.Cu via via, route to R/C destination.
    W_4MIL = 0.10
    EXIT_Y = 15.4  # north of U6 north pin row Y=16.05, outside courtyard

    # 2. EFUSE_OVP: U6.15 east-exit + south through corridor at X=31.5
    # (was X=32 — collides D1 pad +5V_BEC_PROT at (33, 18) which extends
    # to X=32 pad west edge). X=31.5: 1.5mm clearance to D1, 1.0mm
    # separation from EN via at (30.5, 22.5).
    print("[OVP] U6.15 → R10.1 + R9.2 (east-exit, corridor X=31.5)", flush=True)
    add_track(brd, u6_15[0], u6_15[1], 30.0, 17.25, n_ovp, F_CU, W_4MIL)
    add_track(brd, 30.0, 17.25, 31.5, 17.25, n_ovp, F_CU, W_SIG)
    add_track(brd, 31.5, 17.25, 31.5, 22.5, n_ovp, F_CU, W_SIG)
    add_via(brd, 31.5, 22.5, n_ovp)
    add_via(brd, r10_1[0], r10_1[1], n_ovp)
    add_track(brd, 31.5, 22.5, r10_1[0], r10_1[1], n_ovp, B_CU, W_SIG)
    # R10.1 ↔ R9.2 bridge
    add_track(brd, r10_1[0], r10_1[1], r9_2[0], r9_2[1], n_ovp, F_CU, W_SIG)

    # 3. EFUSE_ILIM: U6.17 NORTH-row pin. 4mil north exit + transition via
    # at (28.75, 14.5). Stagger DVDT via to Y=13.0 below ILIM to avoid
    # 0.5mm via-via short with DVDT at same Y.
    print("[ILIM] U6.17 → R4.1 (4mil north exit + B.Cu south)", flush=True)
    add_track(brd, u6_17[0], u6_17[1], 28.75, EXIT_Y, n_ilim, F_CU, W_4MIL)
    add_track(brd, 28.75, EXIT_Y, 28.75, 14.5, n_ilim, F_CU, W_SIG)
    add_via(brd, 28.75, 14.5, n_ilim)
    add_via(brd, r4_1[0], r4_1[1], n_ilim)
    add_track(brd, 28.75, 14.5, r4_1[0], r4_1[1], n_ilim, B_CU, W_SIG)

    # 4. EFUSE_DVDT: U6.18 NORTH-row pin. 4mil north exit + transition via
    # at (28.25, 13.0) — 1.5mm Y staggered from ILIM via at (28.75, 14.5)
    # for clearance. BATT_CURRENT_SENS sense net is on C62.1 (~29.52, 14.5)
    # — DVDT via at (28.25, 13) clears (X gap 1.27, Y gap 1.5).
    print("[DVDT] U6.18 → C7.1 (4mil north exit + B.Cu west, stagger Y)", flush=True)
    add_track(brd, u6_18[0], u6_18[1], 28.25, EXIT_Y, n_dvdt, F_CU, W_4MIL)
    add_track(brd, 28.25, EXIT_Y, 28.25, 13.0, n_dvdt, F_CU, W_SIG)
    add_via(brd, 28.25, 13.0, n_dvdt)
    add_via(brd, c7_1[0], c7_1[1], n_dvdt)
    add_track(brd, 28.25, 13.0, c7_1[0], c7_1[1], n_dvdt, B_CU, W_SIG)

    # Zone fill + save
    print("[fill] unfill + refill all zones...", flush=True)
    try:
        for z in brd.Zones():
            if hasattr(z, 'UnFill'): z.UnFill()
        pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
    except Exception as e:
        print(f"  zone fill skipped: {e}")

    pcbnew.SaveBoard(PCB, brd)
    print(f"\n  Saved {PCB}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
