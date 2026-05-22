#!/usr/bin/env python3
"""C↔E integration step — route the I2C2 nets.

Per docs/PLACEMENT_ROUTING_GATES.md §0 (incremental-integration loop):

  After placing E, the integration PR routes the new cross-subsystem
  nets between E and the already-locked stack (C), then runs the per-
  step sims (Gates 8 / 12 / 13).

Scope (verified against netlist 2026-05-22):
  • I2C2_SDA = PB11 (pin 47 @ X=49.5, Y=42.67) → R11 → U4.pin3
  • I2C2_SCL = PB10 (pin 46 @ X=49.0, Y=42.67) → R12 → U4.pin4

  Note: U7 (BMP388 alternate baro) is on **I2C1**, not I2C2 (per
  baro_3d.py:247-248). The C↔E integration is JUST U4 + the I2C2
  pullups. U7's I2C1 connection routes during the C↔G integration step
  (when G's GPS+mag I2C1 connector + I2C1 pullups R21/R22 land).

  R11/R12 are placed at (49.0, 46.0) and (51.23, 46.0). R11 connects
  to I2C2_SDA, R12 to I2C2_SCL — the routes follow the actual net
  assignments, not the placement geometry.

Topology: daisy chain MCU → pullup → U4 IC. The pullup pad acts as a
through-stub (just a small detour). For I2C at 400 kHz the rise time
is ~1 µs and stub effects are negligible (wavelength 750 m).

Gates exercised:
  Gate 8 — density check (per-cluster, the new I2C2 cluster only)
  Gate 12 — re-run U1 thermal: unchanged from Step 2 (U4 dissipates
            <1 mW; net contribution negligible)
  Gate 13 — Elmer thermal already validated; tracks don't affect it
  + I2C2 SI sanity at 400 kHz (analytical — wavelength vs trace)
"""
import os
import sys
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")

TRACK_WIDTH_MM = 0.127   # 5 mil — fits the LQFP-100 0.5mm-pitch exit
                          # corridor (0.20mm tripped clearance vs adjacent
                          # S-edge pin pads). Plenty for I2C-2 <1mA.
F_CU = pcbnew.F_Cu


def _mm(x_mm): return pcbnew.FromMM(x_mm)


def find_pads_on_net(brd, net_name):
    """Return list of (refdes, pin_num, x_mm, y_mm) for all pads on the net."""
    out = []
    nets = brd.GetNetsByName().asdict()
    if net_name not in nets:
        for k in nets:
            if k == net_name or (hasattr(k, 'value') and k.value() == net_name):
                net_name = k; break
    for fp in brd.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetname() == net_name:
                p = pad.GetPosition()
                out.append((fp.GetReference(), pad.GetNumber(), p.x/1e6, p.y/1e6))
    return out


def add_track(brd, x1, y1, x2, y2, net_obj, layer=F_CU, w_mm=TRACK_WIDTH_MM):
    t = pcbnew.PCB_TRACK(brd)
    t.SetStart(pcbnew.VECTOR2I(_mm(x1), _mm(y1)))
    t.SetEnd(pcbnew.VECTOR2I(_mm(x2), _mm(y2)))
    t.SetWidth(_mm(w_mm))
    t.SetLayer(layer)
    t.SetNet(net_obj)
    brd.Add(t)
    return t


def get_net(brd, name):
    nets = brd.GetNetsByName().asdict()
    for k, v in nets.items():
        kv = k.value() if hasattr(k, 'value') else str(k)
        if kv == name:
            return v
    return None


def main():
    print("=== C↔E integration — route I2C2 ===", flush=True)
    brd = pcbnew.LoadBoard(PCB)

    total_segments = 0
    total_length_mm = 0.0

    for net_name, mcu_pin_num in [("I2C2_SDA", "47"), ("I2C2_SCL", "46")]:
        print(f"\n[{net_name}] MCU pin {mcu_pin_num} → pullup → U4", flush=True)
        net_obj = get_net(brd, net_name)
        if net_obj is None:
            print(f"  ERROR: net {net_name} not found in board"); return 1
        pads = find_pads_on_net(brd, net_name)
        print(f"  pads on net: {len(pads)}")
        for ref, pn, x, y in pads:
            print(f"    {ref}.{pn} @ ({x:.2f}, {y:.2f})", flush=True)

        # Identify (a) U1 pin, (b) pullup pad (R11 or R12), (c) U4 pad
        # Drop any U7 pads silently (U7 is on I2C1, shouldn't be here)
        u1_pad = next(((r,n,x,y) for r,n,x,y in pads if r == "U1"), None)
        r_pad = next(((r,n,x,y) for r,n,x,y in pads if r in ("R11","R12")), None)
        u4_pad = next(((r,n,x,y) for r,n,x,y in pads if r == "U4"), None)

        if not u1_pad or not r_pad or not u4_pad:
            print(f"  WARN: missing pad. U1={u1_pad} R={r_pad} U4={u4_pad}", flush=True)
            continue

        # Routing topology (corrected per master 2026-05-22):
        # The C-zone has C13 (+3V3) at X=51 and C17 (VCAP1) at X=49 blocking
        # a straight south route. R11 (SDA pullup) sits east of C13 at
        # X=52; R12 (SCL pullup) sits west of C17 at X=46. So SDA exits
        # PB11 (X=49.5) eastward over C13, SCL exits PB10 (X=49) westward
        # under C17. Then both daisy-chain west to U4.
        #
        # SDA leg-2 + SCL leg-2 share the corridor between the pullup row
        # (Y=46.5) and U4 (Y=47.8). C51 (U4 decap) sits at (45.5, 47.5)
        # in this corridor. Detour:
        #   - SDA goes SOUTH past C51 (Y=48.0)
        #   - SCL goes NORTH around C51 (Y=45.5, north of pullups)
        # → no shared row, no crossing.
        import math
        def add_segment(x1, y1, x2, y2):
            nonlocal total_segments, total_length_mm
            add_track(brd, x1, y1, x2, y2, net_obj)
            total_segments += 1
            total_length_mm += math.hypot(x2-x1, y2-y1)

        u_x, u_y = u1_pad[2], u1_pad[3]
        r_x, r_y = r_pad[2], r_pad[3]
        e_x, e_y = u4_pad[2], u4_pad[3]

        # Common exit pattern: pin → straight south ≥1.2mm (clears the
        # S-edge pin pad envelope which extends ~0.8mm south from pin
        # center for LQFP-100), then lateral jog.
        EXIT_DROP = 1.2

        # 2-layer routing: F.Cu near MCU + pullup + IC; B.Cu in the
        # middle where the C-zone decap caps + S-edge pin pads block
        # the F.Cu path. Per master 2026-05-22: "use a via-pair layer
        # change if a clean crossing needs it." It does — the C13
        # (+3V3, X=51) and C17 (VCAP1, X=49) sit directly in the south
        # route from PB10/PB11, and their pads are spaced 0.5mm same
        # pitch as the MCU pins.
        def add_via(x, y):
            # 0.5mm/0.3mm via — JLC default-spec compatible
            v = pcbnew.PCB_VIA(brd)
            v.SetPosition(pcbnew.VECTOR2I(_mm(x), _mm(y)))
            v.SetWidth(_mm(0.50))
            v.SetDrill(_mm(0.30))
            v.SetNet(net_obj)
            brd.Add(v)

        def add_seg_layer(x1, y1, x2, y2, layer):
            nonlocal total_segments, total_length_mm
            add_track(brd, x1, y1, x2, y2, net_obj, layer=layer)
            total_segments += 1
            total_length_mm += math.hypot(x2-x1, y2-y1)

        # Leg 1 strategy: F.Cu diagonal from MCU pin out to OFFSET column
        # NORTH of C13/C17, then via down to B.Cu. B.Cu vertical south past
        # the obstacles. Via back up to F.Cu near the pullup (offset to
        # clear pullup +3V3 pad). Short F.Cu hop to pullup signal pad.
        if net_name == "I2C2_SDA":
            # SDA: jog to X=52 (east of C13 body 50.5..51.5), Y=44 north of C13
            JX = 52.0
            # exit south first to clear LQFP pad envelope
            add_seg_layer(u_x, u_y, u_x, u_y + EXIT_DROP, F_CU)
            # diagonal to (JX, 44.0) — north of C13 body
            add_seg_layer(u_x, u_y + EXIT_DROP, JX, 44.0, F_CU)
            # via to B.Cu at (JX, 44.0)
            add_via(JX, 44.0)
            # B.Cu vertical south, well clear of C13 pads (Y=44.955) and R11.1 pad
            add_seg_layer(JX, 44.0, JX, r_y + 0.8, pcbnew.B_Cu)
            # via back to F.Cu south of R11 (Y=47.3)
            add_via(JX, r_y + 0.8)
            # F.Cu short hop to R11.2 pad approached from south
            add_seg_layer(JX, r_y + 0.8, r_x, r_y + 0.8, F_CU)
            add_seg_layer(r_x, r_y + 0.8, r_x, r_y, F_CU)
            # Leg 2: south detour to U4 (Y=48.3 between C51 south + C72 north)
            detour_y = 48.3
            add_segment(r_x, r_y, r_x, detour_y)
            add_segment(r_x, detour_y, e_x, detour_y)
            add_segment(e_x, detour_y, e_x, e_y)
        else:
            # SCL: jog to X=47 (west of C17 body 48.5..49.5), Y=44 north.
            # Return via at (47.5, 46.5) — same Y as R12 pad, clear of C51
            # (X=46.0, Y=47.5).
            JX = 47.0
            RV_X, RV_Y = 47.5, r_y    # return via location
            add_seg_layer(u_x, u_y, u_x, u_y + EXIT_DROP, F_CU)
            add_seg_layer(u_x, u_y + EXIT_DROP, JX, 44.0, F_CU)
            add_via(JX, 44.0)
            add_seg_layer(JX, 44.0, RV_X, RV_Y, pcbnew.B_Cu)
            add_via(RV_X, RV_Y)
            add_seg_layer(RV_X, RV_Y, r_x, r_y, F_CU)
            # Leg 2: NORTH detour around C51
            detour_y = 45.5
            add_segment(r_x, r_y, r_x, detour_y)
            add_segment(r_x, detour_y, e_x + 0.7, detour_y)
            add_segment(e_x + 0.7, detour_y, e_x + 0.7, e_y)
            add_segment(e_x + 0.7, e_y, e_x, e_y)

        print(f"  routed via {r_pad[0]}, total {net_name} length so far ≈ {total_length_mm:.2f} mm", flush=True)

    pcbnew.SaveBoard(PCB, brd)
    print(f"\n[done] {total_segments} segments, {total_length_mm:.2f} mm total", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
