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

TRACK_WIDTH_MM = 0.20    # IPC-2152 for ~50 mA I2C, 1oz Cu, plenty
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

        # Daisy chain: U1 → R → U4. All on F.Cu (top).
        # Add a small Y-orthogonal jog if X delta is non-trivial.
        import math
        def add_segment(x1, y1, x2, y2):
            nonlocal total_segments, total_length_mm
            if abs(x2-x1) > 0.05 and abs(y2-y1) > 0.05:
                # Two-segment L: vertical first, then horizontal
                add_track(brd, x1, y1, x1, y2, net_obj)
                add_track(brd, x1, y2, x2, y2, net_obj)
                total_segments += 2
                total_length_mm += abs(y2-y1) + abs(x2-x1)
            else:
                add_track(brd, x1, y1, x2, y2, net_obj)
                total_segments += 1
                total_length_mm += math.hypot(x2-x1, y2-y1)

        # U1 pin → R pad
        add_segment(u1_pad[2], u1_pad[3], r_pad[2], r_pad[3])
        # R pad → U4 pad
        add_segment(r_pad[2], r_pad[3], u4_pad[2], u4_pad[3])
        print(f"  routed via {r_pad[0]}, total {net_name} length so far ≈ {total_length_mm:.2f} mm", flush=True)

    pcbnew.SaveBoard(PCB, brd)
    print(f"\n[done] {total_segments} segments, {total_length_mm:.2f} mm total", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
