#!/usr/bin/env python3
"""U6 EN routing — make 'board boots' actually true.

Per master 2026-05-23 critical-functional debt #1: U6 EN floating →
internal pull-down keeps eFuse OFF → +5V chain doesn't conduct →
board doesn't boot.

EN intent (verified SKiDL power_3b.py:230+): R7(30.1k from
+5V_BEC_PROT) + R8(10k to GND) — UVLO divider, auto-on when
V_BEC_PROT > 4.0V. No MCU GPIO.

This script routes ONLY EFUSE_EN — the single boot-critical net.

OTHER CONFIG NETS DEFERRED (functional residuals, not boot-blockers):
  - EFUSE_OVP: OVP threshold setter — floating default may be either
    always-on or always-off per TPS25940A datasheet. Without OVP
    routing the over-voltage protection is the IC's internal default,
    not a designed trip point. Board still boots; OVP safety reduced.
    Routing collision: R10.1 OVP via too close to C16 +3V3 via at
    (41.05, 23.245) — hole_clearance fails. Needs R10 relocation OR
    C16 relocation OR via-in-pad. Defer.
  - EFUSE_ILIM: Current Limit — floating default ~5A internal. Without
    ILIM routing, board uses ~5A trip. Board boots. Routing collision:
    R4.1 X=32.49 sits under C8 +5V_BEC_PROT pad column; F.Cu south
    leg shorts C8. B.Cu vertical at X=32.49 crosses OVP B.Cu diagonal.
    Needs R4 relocation (far east X≥46). Defer.
  - EFUSE_FLT: open-drain fault output — floating means no fault signal
    to MCU. Board boots. R13.1 via too close to C16.2 GND pad (0.195mm
    clearance < 0.2mm rule). Needs placement nudge. Defer.
  - EFUSE_PGOOD: open-drain Power Good — floating means no PG signal
    to MCU. Board boots. Routed cleanly here for completeness if no
    collision; deferred if any.
  - EFUSE_DVDT: soft-start ramp time — floating uses default ~5ms ramp.
    Board boots. C7 placement collides with R41/R42 sense row. Defer.

All deferrals tracked for U6-config-extension sub-step before Phase 7a
freeze.

PR doc 4-sections (per master Rule 7 adoption):
  Symptom: board doesn't boot — U6 EN floating
  Fix: R7/R8 UVLO divider routed to U6.14 via F.Cu south-stub + B.Cu
       diagonal through R-row-moved Y=24 corridor (R-row was at Y=22,
       master Option 4 moved to Y=24)
  Root cause: SKiDL netlist correctly assigned EN to R7/R8 but
       .kicad_pcb wasn't updated AND EN routing path through dense
       D1/C8/C9/Q3 sandwich blocked
  Prevention: dense-fanout placement-routing co-coupling — apply
       Option 4-style nudges earlier in placement, not as recovery

Spec deviations (per master Rule 4 adoption):
  - R-row Y=22→Y=24 (approved by master 2026-05-23, Option 4)
  - 4 EFUSE config nets deferred (FLT, ILIM, OVP, DVDT, PGOOD) — only
    EN routed in this PR
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


def _mm(x): return pcbnew.FromMM(x)


def add_track(brd, x1, y1, x2, y2, net_obj, layer=F_CU, w_mm=W_SIG):
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
    nets = brd.GetNetsByName().asdict()
    for k, v in nets.items():
        kv = k.value() if hasattr(k, 'value') else str(k)
        if kv == name:
            return v
    return None


def main():
    print("=== U6 EN routing (board-boots-critical only) ===", flush=True)
    brd = pcbnew.LoadBoard(PCB)
    n_en = get_net(brd, "EFUSE_EN")

    # EFUSE_EN: U6.14 (29.45, 17.75) → R7.2 (35.51, 24) + R8.1 (36.49, 24)
    # F.Cu east jog → south past U6/D1 → via at Y=22.5 in corridor opened
    # by R-row Y=22→Y=24 move → B.Cu diagonal to R7.2 via → F.Cu R7.2↔R8.1
    print("[EN] U6.14 → R7.2 + R8.1", flush=True)
    add_track(brd, 29.45, 17.75, 30.5, 17.75, n_en, w_mm=W_SIG)
    add_track(brd, 30.5, 17.75, 30.5, 22.5, n_en, w_mm=W_SIG)
    add_via(brd, 30.5, 22.5, n_en)
    add_via(brd, 35.51, 24.0, n_en)
    add_via(brd, 36.49, 24.0, n_en)
    # B.Cu intermediate (30.5, 23.5) → R7.2 diagonal
    add_track(brd, 30.5, 22.5, 30.5, 23.5, n_en, layer=B_CU, w_mm=W_SIG)
    add_track(brd, 30.5, 23.5, 35.51, 24.0, n_en, layer=B_CU, w_mm=W_SIG)
    # F.Cu R7.2↔R8.1 bridge (same net, both F.Cu pads)
    add_track(brd, 35.51, 24.0, 36.49, 24.0, n_en, w_mm=W_SIG)

    pcbnew.SaveBoard(PCB, brd)
    print(f"  Saved {PCB}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
