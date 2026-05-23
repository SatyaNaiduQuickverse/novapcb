#!/usr/bin/env python3
"""C↔B integration — power rail routing from B (POWER_REG_3V3) to C (MCU).

Per master 2026-05-23: "+3V3 plane vias / power-flow routes are short
and not impedance-critical — no controlled-Z. Just clean routing."

Strategy (revised after F.Cu trace+zone shorts on MCU pin rows + GND
overlaps):
  - +3V3 main rail: INNER LAYER PLANE on In3.Cu
  - Vias from F.Cu +3V3 pads → In3.Cu plane (via at pad center where
    pad size permits; for narrow MCU LQFP pin pads, short F.Cu stub
    to adjacent decap cap, then via at the cap)
  - +5V_BEC: short F.Cu trace Q2 → U2.1 (B-internal, no conflict)
  - +3V3_IMU_PRE: short F.Cu chain FB2.2 → C77.1 → U13.1 + U13.1↔U13.3
    routed around U13 body

Gates: DRC=0, render eyeball, gate12 v3 thermal.
"""
import os
import sys
import math
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")
F_CU = pcbnew.F_Cu
B_CU = pcbnew.B_Cu
IN3_CU = pcbnew.In3_Cu   # +3V3 plane layer (moved from In4 per DECISIONS §8 v1.1 SI-stackup lock 2026-05-23 — B.Cu signals now reference In4 GND not +3V3)

W_PWR = 0.50    # power trace width (mm)
VIA_DIA = 0.50
VIA_DRILL = 0.30
PAD_WIDE_THRESHOLD = 0.45   # pad needs ≥0.45mm in BOTH X and Y for via-at-center

# +3V3 plane on In3.Cu — covers the central placement area, avoiding
# the parked-component region (X >= 100) and the long-edge mounting
# hole keep-outs at (3, 42.5) / (102, 42.5).
PLUS3V3_PLANE_OUTLINE = [
    (15.0, 18.0),
    (95.0, 18.0),
    (95.0, 52.0),
    (15.0, 52.0),
]


def _mm(x): return pcbnew.FromMM(x)


def add_track(brd, x1, y1, x2, y2, net_obj, layer=F_CU, w_mm=W_PWR):
    t = pcbnew.PCB_TRACK(brd)
    t.SetStart(pcbnew.VECTOR2I(_mm(x1), _mm(y1)))
    t.SetEnd(pcbnew.VECTOR2I(_mm(x2), _mm(y2)))
    t.SetWidth(_mm(w_mm))
    t.SetLayer(layer)
    t.SetNet(net_obj)
    brd.Add(t)


def add_via(brd, x, y, net_obj, dia_mm=VIA_DIA, drill_mm=VIA_DRILL):
    v = pcbnew.PCB_VIA(brd)
    v.SetPosition(pcbnew.VECTOR2I(_mm(x), _mm(y)))
    v.SetWidth(_mm(dia_mm))
    v.SetDrill(_mm(drill_mm))
    v.SetNet(net_obj)
    brd.Add(v)


def get_net(brd, name):
    nets = brd.GetNetsByName().asdict()
    for k, v in nets.items():
        kv = k.value() if hasattr(k, 'value') else str(k)
        if kv == name:
            return v
    return None


def gather_pads_with_size(brd, net_names):
    """[(ref, pad_num, x_mm, y_mm, w_mm, h_mm)]"""
    out = {n: [] for n in net_names}
    for fp in brd.GetFootprints():
        if fp.GetPosition().x / 1e6 >= 100:
            continue
        ref = fp.GetReference()
        for pad in fp.Pads():
            nn = pad.GetNetname()
            if nn in out:
                p = pad.GetPosition(); sz = pad.GetSize()
                out[nn].append((ref, pad.GetPadName(),
                                p.x/1e6, p.y/1e6,
                                sz.x/1e6, sz.y/1e6))
    return out


def main():
    print("=== C↔B integration — inner-layer +3V3 plane + B-internal ===", flush=True)
    brd = pcbnew.LoadBoard(PCB)

    pad_map = gather_pads_with_size(brd, ["+3V3", "+5V_BEC", "+3V3_IMU_PRE"])
    n_3v3 = get_net(brd, "+3V3")
    n_5v_bec = get_net(brd, "+5V_BEC")
    n_3v3_imu_pre = get_net(brd, "+3V3_IMU_PRE")

    print(f"+3V3 on-board pads:          {len(pad_map['+3V3'])}")
    print(f"+5V_BEC on-board pads:        {len(pad_map['+5V_BEC'])}")
    print(f"+3V3_IMU_PRE on-board pads:   {len(pad_map['+3V3_IMU_PRE'])}")

    # Classify +3V3 pads by width
    wide_3v3 = [(r, pn, x, y, w, h) for (r, pn, x, y, w, h) in pad_map["+3V3"]
                if min(w, h) >= PAD_WIDE_THRESHOLD]
    narrow_3v3 = [(r, pn, x, y, w, h) for (r, pn, x, y, w, h) in pad_map["+3V3"]
                  if min(w, h) < PAD_WIDE_THRESHOLD]
    print(f"  WIDE pads (via-at-center): {len(wide_3v3)}")
    print(f"  NARROW pads (need stub):   {len(narrow_3v3)}")
    for r, pn, x, y, w, h in narrow_3v3:
        print(f"    {r:6} pad {pn:4} @ ({x:.2f}, {y:.2f}) size=({w:.2f}, {h:.2f})")

    # MUTATE PHASE
    print(f"\n--- MUTATE: +3V3 plane + vias + B-internal traces ---", flush=True)

    # 1. +3V3 plane on In3.Cu — inline zone (function-call indirection
    # causes SIGSEGV on this pcbnew build)
    z = pcbnew.ZONE(brd)
    z.SetLayer(IN3_CU)   # +3V3 plane: was IN4_CU in PR #72; moved per SI stackup lock 2026-05-23
    z.SetNet(n_3v3)
    o = pcbnew.SHAPE_POLY_SET(); o.NewOutline()
    for x, y in PLUS3V3_PLANE_OUTLINE:
        o.Append(_mm(x), _mm(y))
    z.SetOutline(o)
    brd.Add(z)
    print(f"  +3V3 plane on In3.Cu: outline {PLUS3V3_PLANE_OUTLINE}")

    # 2. Vias at WIDE pad centers. SKIP R11 — neighborhood is congested
    # (existing I2C2_SDA via at (52.0, 47.3)) and any via I add stays
    # within 0.55mm — fails 0.2mm clearance to I2C2 via. R11 is the
    # I2C2 pull-up resistor; can be connected in C↔E-extension step
    # with a careful B.Cu trace under the +3V3 plane.
    via_count_pad = 0
    for r, pn, x, y, w, h in wide_3v3:
        if r == "R11":
            print(f"  R11 via DEFERRED — congested I2C2 area, handle in C↔E-2")
            continue
        add_via(brd, x, y, n_3v3)
        via_count_pad += 1
    print(f"  vias at wide-pad centers: {via_count_pad}")

    # 3. NARROW MCU VDD stubs to OWN-DEDICATED VIAS placed in clear space.
    # Plane In3.Cu connects all +3V3 — via locations only need to be
    # NEAR each MCU pin, in clear space (not in pin row, not over Y1,
    # not crossing I2C2). 0.20mm trace fits between adjacent pads.
    #
    # Routes (this PR):
    #   U1.11  → via at (35.5, 34) [west of pin row, south of Y1]
    #   U1.75  → via at C14 location (already via from step 2)
    #   U1.100 → via at (39.0, 25.5) [north of pin row, near C15]
    #
    # DEFERRED (need B.Cu route to clear I2C2_SDA — handle in C↔E
    # extension or post-routing power-plane-fill step):
    #   U1.27  (39.5, 42.67) → vertical south stub crosses I2C2_SDA
    #   U1.50  (51.0, 42.67) → vertical south stub crosses I2C2_SDA
    #
    # These 2 unconnected stubs become "unconnected items" in DRC
    # (expected for unrouted power nets per gate14_drc convention).
    # MCU still has 3 of 5 VDD pins connected — meets PDN spec for
    # this step. Will be completed in C↔B-2 sub-step.
    stub_routes = {
        "11":  [(35.50, 34.00)],            # F.Cu stub + via at (35.5, 34)
        "75":  [(54.48, 29.00)],            # direct east to C14 (existing via)
        "100": [(39.00, 26.00)],            # F.Cu stub + via at (39, 26)
                                            # (was 25.5 — too close to C15.2 GND
                                            # at (39.47, 25.05) — 0.05mm short)
    }
    # Vias to add at the route endpoints (not the existing wide-pad ones)
    extra_vias = [(35.50, 34.00), (39.00, 26.00)]
    W_STUB = 0.20
    stub_count = 0
    for r, pn, x, y, w, h in narrow_3v3:
        if r == "U1" and pn in stub_routes:
            cur_x, cur_y = x, y
            for tx, ty in stub_routes[pn]:
                add_track(brd, cur_x, cur_y, tx, ty, n_3v3, w_mm=W_STUB)
                cur_x, cur_y = tx, ty
            stub_count += 1
            print(f"    F.Cu stub U1.{pn} W={W_STUB} → {stub_routes[pn]}")
    for vx, vy in extra_vias:
        add_via(brd, vx, vy, n_3v3)
        print(f"    extra via at ({vx}, {vy}) → In3.Cu plane")
    print(f"  narrow-pad stubs: {stub_count} routed, 2 deferred (U1.27/U1.50)")

    # 4. +5V_BEC routing — DEFERRED.
    # Discovered during DRC iteration: U2.1 (input) is on net "+5V", not
    # "+5V_BEC". The topology is: +5V_BEC (from A zone OR-FETs Q3/Q4
    # unplaced) → U6 eFuse (also unnetlisted at this snapshot) → +5V →
    # Q2 (rev-pol) → +5V → U2 input. The +5V net source is A-zone parts
    # that aren't on the board yet. So no route to commit at this step.
    # The +5V/+5V_BEC routing comes in at the A↔B integration step.
    print(f"\n  +5V_BEC routing DEFERRED — U2.1 is on +5V net; source is in A zone (unplaced)")

    # 5. +3V3_IMU_PRE chain — FB2.2 → C77.1 → U13.1.
    # Direct C77.1 → U13.1 path goes through C77.2 GND pad (X interp).
    # Route around: from C77.1 go NORTH first to clear C77.2, then east
    # to U13.1.
    fb2_p2 = None; c77_p1 = None; u13_p1_pre = None
    for r, pn, x, y, w, h in pad_map["+3V3_IMU_PRE"]:
        if r == "FB2" and pn == "2": fb2_p2 = (x, y)
        if r == "C77" and pn == "1": c77_p1 = (x, y)
        if r == "U13" and pn == "1": u13_p1_pre = (x, y)
    if fb2_p2 and c77_p1:
        # FB2.2 → C77.1 (south-of-cap-row diagonal, no obstacles)
        add_track(brd, fb2_p2[0], fb2_p2[1], c77_p1[0], c77_p1[1],
                  n_3v3_imu_pre, w_mm=0.20)
        print(f"  +3V3_IMU_PRE: FB2.2 → C77.1  "
              f"({math.hypot(c77_p1[0]-fb2_p2[0], c77_p1[1]-fb2_p2[1]):.2f}mm)")
    if c77_p1 and u13_p1_pre:
        # C77.1 → U13.1. U13 SOT-23-5 pads are 1.10×0.60mm. U13.4 NC pad
        # at (58.7, 25.05) extends Y=24.75..25.35. Route via Y=24.5
        # (south edge 24.4 = 0.95mm gap to U13.4). Turning point at
        # X=60.0 (0.55mm gap to U13.2 pad west edge X=60.75).
        # Use Y=24.0 (south edge 24.1) — gap 0.65mm to U13.4 NC at
        # (58.7, 25.05) north edge Y=24.75. Y=24.5 was 0.15mm gap (FAIL).
        add_track(brd, c77_p1[0], c77_p1[1], c77_p1[0], 24.0,
                  n_3v3_imu_pre, w_mm=0.20)     # N: (56.0, 27) → (56.0, 24.0)
        add_track(brd, c77_p1[0], 24.0, 60.0, 24.0,
                  n_3v3_imu_pre, w_mm=0.20)     # E: (56.0, 24.0) → (60.0, 24.0)
        add_track(brd, 60.0, 24.0, 60.0, u13_p1_pre[1],
                  n_3v3_imu_pre, w_mm=0.20)     # S: (60.0, 24.0) → (60.0, 26.95)
        add_track(brd, 60.0, u13_p1_pre[1], u13_p1_pre[0], u13_p1_pre[1],
                  n_3v3_imu_pre, w_mm=0.20)     # E: → U13.1 (61.3, 26.95)
        print(f"  +3V3_IMU_PRE: C77.1 → U13.1 via (60.0, 24.5) → (60.0, 26.95)")
    # U13.1 → U13.3 around body
    u13_p1 = None; u13_p3 = None
    for fp in brd.GetFootprints():
        if fp.GetReference() == "U13":
            for pad in fp.Pads():
                if pad.GetPadName() == "1":
                    p = pad.GetPosition(); u13_p1 = (p.x/1e6, p.y/1e6)
                if pad.GetPadName() == "3":
                    p = pad.GetPosition(); u13_p3 = (p.x/1e6, p.y/1e6)
    if u13_p1 and u13_p3:
        # NOTE: with the new C77.1→U13.1 route via (60.0, 24.5) →
        # (60.0, 26.95) → U13.1, the route ALSO passes (60.0, 25.05) =
        # SAME Y as U13.3. U13.3 is at X=61.3 (same net). The route
        # IMPLICITLY connects U13.3 because the trace's south leg
        # crosses Y=25.05 at X=60.0 (1.3mm west of U13.3).
        # The TRACE itself doesn't touch U13.3 pad — needs explicit
        # connection. Add a SINGLE WEST stub at Y=25.05 from U13.3 to
        # the C77.1→U13.1 route at X=60.0.
        Y3 = u13_p3[1]   # 25.05
        # Stub: U13.3 (61.3, 25.05) → (60.0, 25.05) — 1.3mm west,
        # connects to the existing route vertical at X=60.0.
        add_track(brd, u13_p3[0], Y3, 60.0, Y3, n_3v3_imu_pre, w_mm=0.20)
        print(f"  +3V3_IMU_PRE U13.3 stub W to (60.0, 25.05) — joins C77→U13.1 route")

    pcbnew.SaveBoard(PCB, brd)
    print(f"\n  Saved {PCB}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
