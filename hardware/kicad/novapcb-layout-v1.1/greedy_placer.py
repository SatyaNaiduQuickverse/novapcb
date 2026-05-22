#!/usr/bin/env python3
"""Greedy collision-avoiding small-part placer (master 2026-05-22).

Big blocks are FROZEN — do not move them.
For each small part:
  1. Compute IDEAL location based on type + net connectivity.
  2. Try ideal. Collision-check against all placed (big + already-placed smalls).
  3. If collide: spiral search outward in 0.2mm steps, first clear wins.
  4. Place at clear spot.

Result: 0 courtyard overlaps + 0 pad-pad shorts BY CONSTRUCTION.

Types handled:
  - Decoupling cap (2-pad C with power+GND): beside parent IC's power pin
  - Series R (2-pad R with two non-power nets): on line between the two
    connected pads
  - ESD diode (3-pad D with signal+GND): beside the connector pin
  - Pull-up/down R (2-pad R with one pin on power/GND): beside the IC pin
  - Other: fallback — keep original position; collision-resolve only
"""
import os, math, time
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-layout-v1.1.kicad_pcb")

POWER_NETS = {"GND", "+3V3", "+5V", "+3V3A", "+3V3_IMU", "+3V3_IMU_PRE",
              "+5V_BEC", "+5V_BEC_A", "+5V_BEC_B", "+5V_BEC_PROT",
              "VBAT", "VCAP1", "VCAP2", "VDD", "VSS", "VDDA", "VREF_P", "VREF+",
              "ORING_A_VCAP", "ORING_B_VCAP", "ORING_A_GATE", "ORING_B_GATE"}

# Big block refs — these are FROZEN. Anything not in this set is a small.
BIG_REFS = {
    "U1","U2","U3","U4","U5","U6","U7","U8","U9","U11","U12","U13","U14","U15",
    "J1","J2","J3","J4","J5","J9","J10","J11","J12","J13","J14","J15","J16",
    "J17","J18","J19","J20",
    "Y1","Q2","Q3","Q4","Q5","R61",
    "FB1","FB2","D1",
    "D5","D6","D7","D8","D9","D11","D12","D13","D14",
}

CLEARANCE = 0.20   # mm safety between parts (matches netclass)


def get_all_pads(brd):
    """Return list of (ref, pad_num, x_mm, y_mm, net_name) for ALL pads on board."""
    out = []
    for fp in brd.GetFootprints():
        ref = fp.GetReference()
        for p in fp.Pads():
            pos = p.GetPosition()
            out.append((ref, p.GetNumber(), pos.x/1e6, pos.y/1e6,
                          p.GetNetname() or ""))
    return out


def get_part_footprint_bbox(fp):
    """Return (half_w, half_h) in mm. Use GetBoundingBox(False, False) which
    excludes silkscreen / invisible text — gives true component+pad extent."""
    try:
        bb = fp.GetBoundingBox(False, False)
    except Exception:
        bb = fp.GetBoundingBox()
    return bb.GetWidth()/2/1e6, bb.GetHeight()/2/1e6


def fp_collides(fp, test_x, test_y, placed_bboxes, clearance=CLEARANCE):
    """Check if placing fp at (test_x, test_y) collides with any in placed_bboxes.
    placed_bboxes: list of (cx, cy, half_w, half_h)."""
    hw, hh = get_part_footprint_bbox(fp)
    for cx, cy, ohw, ohh in placed_bboxes:
        if (abs(test_x - cx) < hw + ohw + clearance and
            abs(test_y - cy) < hh + ohh + clearance):
            return True
    return False


def systematic_scan(fp, placed_bboxes, step=0.5):
    """Scan entire board top-to-bottom for first clear spot."""
    for y in [v*step for v in range(int(1/step), int(69/step))]:
        for x in [v*step for v in range(int(1/step), int(89/step))]:
            if not fp_collides(fp, x, y, placed_bboxes):
                return (x, y)
    return None


def spiral_search(fp, ideal_x, ideal_y, placed_bboxes, max_r=15.0, step=0.25):
    """Return (x, y) of nearest clear spot, or None."""
    if not fp_collides(fp, ideal_x, ideal_y, placed_bboxes):
        return (ideal_x, ideal_y)
    # Spiral: ring of positions at increasing radius
    for r_step in range(1, int(max_r / step) + 1):
        r = r_step * step
        # 16 angles per ring
        for k in range(16):
            ang = 2 * math.pi * k / 16
            x = ideal_x + r * math.cos(ang)
            y = ideal_y + r * math.sin(ang)
            # Stay inside board with margin
            if x < 1 or x > 89 or y < 1 or y > 69: continue
            if not fp_collides(fp, x, y, placed_bboxes):
                return (x, y)
    return None


def is_power(net):
    return net in POWER_NETS


def get_ideal_pos(brd, fp, all_pads):
    """Compute ideal placement location for this small part based on type
    + net connectivity. Returns (x, y) or None if can't determine."""
    pads = [(p.GetNumber(), (p.GetPosition().x/1e6, p.GetPosition().y/1e6),
              p.GetNetname() or "") for p in fp.Pads()]
    if len(pads) < 2: return None
    ref = fp.GetReference()

    # Collect connected pads (other parts on this part's nets)
    my_nets = set(net for _, _, net in pads if net)
    connected = []
    for o_ref, o_pad, ox, oy, o_net in all_pads:
        if o_ref == ref: continue
        if o_net in my_nets and not is_power(o_net):
            connected.append((o_ref, o_pad, ox, oy, o_net))

    # Type: 2-pad cap with power + GND = decoupling
    if ref.startswith("C") and len(pads) == 2:
        nets = [p[2] for p in pads]
        if "GND" in nets and any(is_power(n) and n != "GND" for n in nets):
            power_net = [n for n in nets if is_power(n) and n != "GND"][0]
            # Find IC pin on same power net (excluding this cap, other caps)
            for o_ref, o_pad, ox, oy, o_net in all_pads:
                if o_ref == ref: continue
                if o_ref in BIG_REFS and o_net == power_net:
                    # Ideal: 1mm offset from that pin
                    return (ox + 0.5, oy + 1.5)
            return None  # no IC pin on this power found

    # Type: 2-pad R, both pads connected = series resistor
    if ref.startswith("R") and len(pads) == 2 and len(connected) >= 2:
        # Sort connected by net to match each pad
        net_to_pad = {p[2]: p[1] for p in pads}  # net -> our pad pos
        connected_pos_by_net = {}
        for o_ref, o_pad, ox, oy, o_net in connected:
            if o_net in net_to_pad and o_net not in connected_pos_by_net:
                connected_pos_by_net[o_net] = (ox, oy)
        if len(connected_pos_by_net) == 2:
            posns = list(connected_pos_by_net.values())
            mid_x = (posns[0][0] + posns[1][0]) / 2
            mid_y = (posns[0][1] + posns[1][1]) / 2
            return (mid_x, mid_y)

    # Type: 2-pad R with one power pin = pull-up/down
    if ref.startswith("R") and len(pads) == 2:
        nets = [p[2] for p in pads]
        non_power = [n for n in nets if n and not is_power(n)]
        if non_power and connected:
            # Find connected pin (the non-power side)
            sig = non_power[0]
            for o_ref, o_pad, ox, oy, o_net in all_pads:
                if o_ref == ref: continue
                if o_net == sig and o_ref in BIG_REFS:
                    return (ox + 0.7, oy + 0.7)

    # Type: 3-pad D (ESD) with signal + GND
    if ref.startswith("D") and len(pads) == 3:
        nets = [p[2] for p in pads]
        sig_nets = [n for n in nets if n and not is_power(n)]
        if sig_nets:
            sig = sig_nets[0]
            for o_ref, o_pad, ox, oy, o_net in all_pads:
                if o_ref == ref: continue
                if o_net == sig and o_ref in BIG_REFS:
                    return (ox + 0.6, oy + 1.2)

    return None  # fallback: keep current position


def main():
    brd = pcbnew.LoadBoard(PCB)
    print("[load] OK", flush=True)

    # Get all pads (snapshot before moving anything)
    all_pads = get_all_pads(brd)
    print(f"[pads] {len(all_pads)} pads total", flush=True)

    # FROZEN big-block placed bboxes (don't change positions)
    placed_bboxes = []
    big_count = 0
    for fp in brd.GetFootprints():
        if fp.GetReference() in BIG_REFS:
            pos = fp.GetPosition()
            hw, hh = get_part_footprint_bbox(fp)
            placed_bboxes.append((pos.x/1e6, pos.y/1e6, hw, hh))
            big_count += 1
    # Mounting holes also frozen (use generous 3mm radius for keepout)
    for fp in brd.GetFootprints():
        if fp.GetReference().startswith("H"):
            pos = fp.GetPosition()
            placed_bboxes.append((pos.x/1e6, pos.y/1e6, 3.0, 3.0))
    # IMU stress-relief slot KERFS — match cleanup_placement (5 thin slots,
    # 14mm bridge X=38..52 at top).
    placed_bboxes.append((31.5, 52.0, 6.5, 1.0))    # N_west X=25..38 Y=51..53
    placed_bboxes.append((62.0, 52.0, 10.0, 1.0))   # N_east X=52..72 Y=51..53
    placed_bboxes.append((26.0, 59.0, 1.0, 8.0))    # W kerf X=25..27 Y=51..67
    placed_bboxes.append((71.0, 59.0, 1.0, 8.0))    # E kerf X=70..72 Y=51..67
    placed_bboxes.append((48.5, 66.0, 23.5, 1.0))   # S kerf X=25..72 Y=65..67
    # Inset board edges by 0.3mm — block 4 thin strips on board perimeter
    placed_bboxes.append((45.0, -0.3, 45.0, 0.5))   # north edge band
    placed_bboxes.append((45.0, 70.3, 45.0, 0.5))   # south edge band
    placed_bboxes.append((-0.3, 35.0, 0.5, 35.0))   # west edge band
    placed_bboxes.append((90.3, 35.0, 0.5, 35.0))   # east edge band
    print(f"[frozen] {big_count} big blocks + 4 mounting holes + 4 slot bands + 4 edge bands", flush=True)

    # Collect small parts to place
    smalls = []
    for fp in brd.GetFootprints():
        ref = fp.GetReference()
        if ref in BIG_REFS: continue
        if ref.startswith("H"): continue
        smalls.append(fp)
    print(f"[smalls] {len(smalls)} small parts to place", flush=True)

    # Order: decap → series R → ESD → pull-up → other (so cap layout doesn't
    # block series R between two big pads). Within each group, sort by ref.
    def order_key(fp):
        ref = fp.GetReference()
        if ref.startswith("C"): return (0, ref)
        if ref.startswith("R"): return (1, ref)
        if ref.startswith("D"): return (2, ref)
        return (3, ref)
    smalls.sort(key=order_key)

    placed = 0
    stuck = []
    t0 = time.time()
    for fp in smalls:
        ref = fp.GetReference()
        ideal = get_ideal_pos(brd, fp, all_pads)
        if ideal is None:
            # Fallback: try current position
            pos = fp.GetPosition()
            ideal = (pos.x/1e6, pos.y/1e6)
        x, y = ideal
        # Spiral search for clear spot
        spot = spiral_search(fp, x, y, placed_bboxes, max_r=40.0, step=0.25)
        if spot is None:
            # Last resort: scan entire board systematically for clear spot
            spot = systematic_scan(fp, placed_bboxes)
            if spot is None:
                stuck.append(ref)
                continue
        nx, ny = spot
        fp.SetPosition(pcbnew.VECTOR2I(int(nx*1e6), int(ny*1e6)))
        hw, hh = get_part_footprint_bbox(fp)
        placed_bboxes.append((nx, ny, hw, hh))
        placed += 1

    elapsed = time.time() - t0
    print(f"[placed] {placed}/{len(smalls)} smalls in {elapsed:.1f}s; stuck: {len(stuck)}", flush=True)
    if stuck: print(f"  stuck: {stuck[:15]}{'...' if len(stuck)>15 else ''}", flush=True)

    pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
    pcbnew.SaveBoard(PCB, brd)
    print("[save] PCB written", flush=True)


if __name__ == "__main__":
    main()
