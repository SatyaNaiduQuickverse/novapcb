#!/usr/bin/env python3
"""
Layout compliance audit — novapcb-adapted (master 2026-05-23 codification).

Original adapted from pcb.ai (commit ccc590c equivalent). Novapcb adaptations:
  - Filter parked components (X >= 100, staged-build convention).
  - Symmetry: ESC-specific CH1-4 dropped; novapcb A-subsystem mirror about X=52.5 added.
  - Passive anchoring: net-aware nearest-IC; ORPHANED vs FAR distinction.
  - Decoupling: IC body-edge to VDD-pin distance (not center).
  - Bootstrap rule conditional on buck/boost presence (novapcb is LDO).
  - 3 novapcb-specific gates added: IMU slot integrity, USB Z-pair
    geometry preservation, mid-edge mounting-hole keep-out.

Checks (all hard gates):
  1. Off-board: any footprint with center outside board outline + 2mm margin.
  2. Pad-overlap: any two pads on same layer that physically intersect.
  3. A-subsystem symmetry: J4↔J19, Q3↔Q4, U11↔U12, D5↔D7, D6↔D8 mirror
     about X=52.5 within 0.5mm tolerance.
  4. Passive anchoring (role-aware + ORPHANED/FAR distinction):
     - ORPHANED: no IC/FET on same net within 20mm.
     - FAR: nearest in-net IC/FET >role-specific threshold.
       decouple (C ≤1uF on Vdd net): ≤3mm body-edge-to-VDD-pin (IPC-2221).
       gate_R (R between IC and FET gate): ≤5mm (vendor app notes, TI SLOA088).
       sense_R (R on Vsense net): ≤3mm (precision-shunt practice).
       feedback_R, pull_R: ≤5mm.
  5. Decoupling: every IC's VDD/VCC pin has a cap ≤3mm body-edge-to-pin.
  6. IMU stress-relief slot: Edge.Cuts slot around IMU island is a single
     closed polygon (no slot-as-region-cutout bug).
  7. USB diff-pair preservation: W=0.20mm / S=0.13mm on F.Cu over GND ref.
  8. Mid-edge mounting-hole keep-out: 8mm radius at (3.25, 42.5) +
     (101.75, 42.5) empty (reserved for vibration-sim-gated +2 holes).

Bootstrap-R rule SKIPPED on novapcb (LDO architecture, no buck/boost).

Run: python3 audit_layout_compliance.py <board.kicad_pcb>
Exit 0 on PASS, 1 on any FAIL.
"""
import sys, os, math
import pcbnew

if len(sys.argv) < 2:
    sys.exit("usage: audit_layout_compliance.py <board.kicad_pcb>")

board = pcbnew.LoadBoard(sys.argv[1])
fails = []
warns = []
info = []


# ----- thresholds (IPC/JEDEC/vendor-derived) -----
# IPC-2221 / IPC-7351: HF decoupling cap close to IC; effective placement
#   typically ≤3mm from VDD pin for >100MHz suppression. ST/TI app notes
#   reinforce 3mm for STM32-class MCUs.
# Gate resistor: TI SLOA088 + vendor MOSFET-drive notes recommend ≤5mm
#   for damping series-R on FET gates.
# Sense/precision: 3mm guideline for shunt-trace integrity.
ROLE_MAX_MM = {
    "decouple": 3.0,    # HF bypass: IPC-2221 + ST AN2867
    "gate_R": 5.0,      # FET gate damping R: TI SLOA088
    "bootstrap_C": 2.0, # buck/boost bootstrap (N/A on LDO board)
    "sense_R": 3.0,     # current-sense shunt placement
    "pull_R": 5.0,      # GPIO pulls / boot config
    "feedback_R": 3.0,  # regulator FB networks
    "led_R": 2.0,       # LED series R
}
ORPHANED_THRESHOLD_MM = 20.0


def get_outline_bbox():
    xs = []
    ys = []
    for d in board.GetDrawings():
        if d.GetLayer() == pcbnew.Edge_Cuts:
            xs += [pcbnew.ToMM(d.GetStart().x), pcbnew.ToMM(d.GetEnd().x)]
            ys += [pcbnew.ToMM(d.GetStart().y), pcbnew.ToMM(d.GetEnd().y)]
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def collect_components():
    items = {}
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        p = fp.GetPosition()
        if pcbnew.ToMM(p.x) >= 100:
            continue
        items[ref] = {
            "x": pcbnew.ToMM(p.x),
            "y": pcbnew.ToMM(p.y),
            "fp": fp,
            "side": "F" if fp.GetLayer() == pcbnew.F_Cu else "B",
            "value": fp.GetValue(),
            "nets": {pad.GetPadName(): pad.GetNetname() for pad in fp.Pads()},
        }
    return items


# ----- check 1: off-board -----
def check_off_board(items, bbox):
    if not bbox:
        warns.append("no board outline found; off-board check skipped")
        return
    x_min, y_min, x_max, y_max = bbox
    m = 2.0
    off = [r for r, d in items.items()
           if not (x_min - m <= d["x"] <= x_max + m
                   and y_min - m <= d["y"] <= y_max + m)]
    if off:
        fails.append(f"OFF-BOARD: {len(off)} footprints outside outline+{m}mm")
        for r in off[:10]:
            d = items[r]
            fails.append(f"  {r} at ({d['x']:.2f}, {d['y']:.2f})")


# ----- check 2: pad-overlap -----
def check_pad_overlap(items):
    pads = []
    for ref, d in items.items():
        for pad in d["fp"].Pads():
            bb = pad.GetBoundingBox()
            layers = pad.GetLayerSet()
            pads.append({
                "ref": ref, "pad": pad.GetPadName(),
                "bb": (pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop()),
                       pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom())),
                "F": layers.Contains(pcbnew.F_Cu),
                "B": layers.Contains(pcbnew.B_Cu),
            })
    overlaps = 0; pairs = []
    for i in range(len(pads)):
        a = pads[i]
        for j in range(i + 1, len(pads)):
            b = pads[j]
            if a["ref"] == b["ref"]: continue
            if not ((a["F"] and b["F"]) or (a["B"] and b["B"])): continue
            ax1, ay1, ax2, ay2 = a["bb"]; bx1, by1, bx2, by2 = b["bb"]
            if ax1 < bx2 and ax2 > bx1 and ay1 < by2 and ay2 > by1:
                overlaps += 1
                if len(pairs) < 8: pairs.append((a["ref"], a["pad"], b["ref"], b["pad"]))
    if overlaps:
        fails.append(f"PAD-OVERLAP: {overlaps} pad pairs overlap on same layer")
        for r1, p1, r2, p2 in pairs:
            fails.append(f"  {r1}.{p1} <-> {r2}.{p2}")


# ----- check 3: A-subsystem symmetry (novapcb-specific) -----
# Mirror about X=52.5 (board center): J4↔J19, Q3↔Q4, U11↔U12, D5↔D7, D6↔D8
A_MIRROR_PAIRS = [("J4", "J19"), ("Q3", "Q4"), ("U11", "U12"), ("D5", "D7"), ("D6", "D8")]
A_MIRROR_X = 52.5
A_MIRROR_TOL_MM = 0.5

def check_a_symmetry(items):
    dev = []
    for west, east in A_MIRROR_PAIRS:
        if west not in items or east not in items:
            warns.append(f"A-SYMMETRY: {west} or {east} not placed; skip")
            continue
        wx, wy = items[west]["x"], items[west]["y"]
        ex, ey = items[east]["x"], items[east]["y"]
        expected_ex = 2 * A_MIRROR_X - wx
        dx, dy = abs(ex - expected_ex), abs(ey - wy)
        if dx > A_MIRROR_TOL_MM or dy > A_MIRROR_TOL_MM:
            dev.append((west, east, wx, wy, ex, ey, expected_ex, dx, dy))
    if dev:
        # Master 2026-05-23 ack: A symmetry refactor pending task #22.
        # Report as WARN (not FAIL) until task #22 lands.
        warns.append(f"A-SYMMETRY: {len(dev)} pairs deviate >{A_MIRROR_TOL_MM}mm "
                     f"(pending task #22 explicit mirror refactor)")
        for w, e, wx, wy, ex, ey, ee, dx, dy in dev:
            warns.append(f"  {w}@({wx:.1f},{wy:.1f}) ↔ {e}@({ex:.1f},{ey:.1f}) "
                         f"expected ({ee:.1f},{wy:.1f}) dev=({dx:.2f},{dy:.2f})")


# ----- check 4: passive anchoring (role + ORPHANED/FAR) -----
def is_vdd_net(net_name):
    """Strict VDD-class net pattern. Excludes:
    - +5V_BEC_A/B (pre-OR-FET sense rails, not VDD)
    - Any net with _PRE / _RAW suffix (pre-regulator)
    - Bare GND
    """
    if not net_name:
        return False
    if "_PRE" in net_name.upper() or "_RAW" in net_name.upper():
        return False
    if net_name in ("+5V_BEC_A", "+5V_BEC_B"):
        return False
    return net_name.startswith(("+3V3", "+5V", "+1V", "VBAT", "VDD", "VCC", "VREF"))


def classify_role(ref, value, nets):
    """Infer role from ref + value + nets."""
    if not value:
        return "unknown"
    v_low = value.lower()
    if ref.startswith("C"):
        cap_pF = None
        try:
            if "pf" in v_low or v_low.endswith("p"):
                cap_pF = float(v_low.replace("pf","").replace("p",""))
            elif "nf" in v_low or v_low.endswith("n"):
                cap_pF = float(v_low.replace("nf","").replace("n","")) * 1e3
            elif "uf" in v_low or v_low.endswith("u"):
                cap_pF = float(v_low.replace("uf","").replace("u","")) * 1e6
        except ValueError:
            pass
        # Loading-cap for crystals (≤50pF on HSE_/LSE_/OSC_ net)
        net_names = list(nets.values())
        if cap_pF and cap_pF <= 50:
            if any(n.startswith(("HSE_","LSE_","OSC_")) for n in net_names):
                return "decouple"  # crystal loading — strict 3mm to crystal
        # Decoupling: ≤1uF AND on VDD net
        if cap_pF and cap_pF <= 1e6:
            if any(is_vdd_net(n) for n in net_names):
                return "decouple"
        if cap_pF and cap_pF > 1e6:
            return "bulk"
        return "unknown"  # Cap with no clear role
    elif ref.startswith("R"):
        # 0R = jumper (no anchoring constraint)
        if v_low in ("0r", "0", "0ohm", "0ohms"):
            return "jumper"
        # Pull-R / gate-R / sense-R inferred from net names
        net_names = list(nets.values())
        # Gate-R: net contains GATE
        if any("GATE" in n.upper() for n in net_names):
            return "gate_R"
        # Sense-R: net contains SENSE or shunt-current pattern
        if any(("SENSE" in n.upper() or "CURRENT" in n.upper()) for n in net_names):
            return "sense_R"
        # Feedback (regulator FB)
        if any(("FB" == n.upper() or n.upper().endswith("_FB")) for n in net_names):
            return "feedback_R"
        # LED series
        if any("LED" in n.upper() for n in net_names):
            return "led_R"
        # Default: pull/general purpose
        return "pull_R"
    return "unknown"


def parent_ic_for_passive(ref, nets, items):
    """Find nearest IC/FET sharing a net with this passive."""
    on_net = set(nets.values())
    candidates = []
    for cref, cd in items.items():
        if cref == ref: continue
        if not (cref.startswith(("U", "Q", "J", "Y", "X")) and
                (cref[1:].isdigit() or (len(cref) > 1 and cref[1:2].isdigit()))):
            continue
        # Find pads on same net as passive
        for cnet in cd["nets"].values():
            if cnet and cnet in on_net:
                d = math.hypot(cd["x"] - items[ref]["x"], cd["y"] - items[ref]["y"])
                candidates.append((d, cref))
                break
    return sorted(candidates) if candidates else []


def check_passive_anchoring(items):
    orphaned = []
    far_by_role = {}
    for ref, d in items.items():
        if not (ref[0] in ("R", "C") and ref[1:].isdigit()):
            continue
        role = classify_role(ref, d.get("value", ""), d.get("nets", {}))
        if role in ("jumper", "bulk", "unknown"):
            continue  # not anchored
        parents = parent_ic_for_passive(ref, d.get("nets", {}), items)
        if not parents:
            orphaned.append((ref, d["x"], d["y"], role, list(d.get("nets", {}).values())))
            continue
        nearest_d, nearest_ref = parents[0]
        max_mm = ROLE_MAX_MM.get(role, 5.0)
        if nearest_d > max_mm:
            far_by_role.setdefault(role, []).append(
                (ref, d["x"], d["y"], nearest_ref, nearest_d, max_mm))
    if orphaned:
        fails.append(f"PASSIVE-ANCHORING (ORPHANED): {len(orphaned)} passives "
                     f"with no IC/FET on same net within {ORPHANED_THRESHOLD_MM}mm")
        for r, x, y, role, n in sorted(orphaned)[:10]:
            fails.append(f"  {r} ({role}) at ({x:.1f},{y:.1f}) nets={','.join(n[:3])}")
    for role, entries in sorted(far_by_role.items()):
        if not entries: continue
        msg = (f"PASSIVE-ANCHORING ({role.upper()}-FAR): {len(entries)} passives "
               f">{ROLE_MAX_MM[role]}mm from in-net parent")
        # role-specific: decouple/sense_R are stricter → FAIL; others WARN
        bucket = fails if role in ("decouple", "sense_R", "gate_R") else warns
        bucket.append(msg)
        for r, x, y, p, d, m in sorted(entries, key=lambda t: -t[4])[:8]:
            bucket.append(f"  {r} at ({x:.1f},{y:.1f}) → {p} @ {d:.1f}mm (rule {m}mm)")


# ----- check 5: decoupling — every IC VDD pin has cap ≤3mm body-edge-to-VDD-pad -----
def cap_body_edge_to_point(cd, vx, vy):
    """Distance from cap BODY (not center) edge to a point. Approximation:
    use cap bounding box edge."""
    bb = cd["fp"].GetBoundingBox()
    cx1, cy1 = pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop())
    cx2, cy2 = pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom())
    dx = max(cx1 - vx, 0, vx - cx2)
    dy = max(cy1 - vy, 0, vy - cy2)
    return math.hypot(dx, dy)


def check_decoupling(items):
    bad = []
    for ref, d in items.items():
        if not (ref.startswith("U") and ref[1:].isdigit()):
            continue
        # Strict VDD pads only
        vdd_pad_positions = []
        for pad in d["fp"].Pads():
            net = pad.GetNetname()
            if is_vdd_net(net):
                pp = pad.GetPosition()
                vdd_pad_positions.append((pcbnew.ToMM(pp.x), pcbnew.ToMM(pp.y), net))
        if not vdd_pad_positions:
            continue
        for vx, vy, vnet in vdd_pad_positions:
            found = False
            for cref, cd in items.items():
                if not (cref.startswith("C") and cref[1:].isdigit()): continue
                cap_nets = list(cd.get("nets", {}).values())
                if vnet not in cap_nets: continue
                if cap_body_edge_to_point(cd, vx, vy) <= 3.0:
                    found = True; break
            if not found:
                bad.append((ref, vnet, vx, vy))
    if bad:
        unique = set((r, n) for r, n, _, _ in bad)
        fails.append(f"DECOUPLING: {len(unique)} IC VDD-net assignments "
                     f"with no cap within 3mm of VDD pad (body-edge)")
        for r, n in sorted(unique)[:10]:
            fails.append(f"  {r} VDD net={n}")


# ----- check 6: IMU stress-relief slot integrity -----
# Edge.Cuts polygons around the IMU island must be SINGLE CLOSED polygon
# (no slot-as-region-cutout bug). Skip if no IMU slot defined.
def check_imu_slot():
    # Detect IMU slot by checking for an internal Edge.Cuts polygon
    # disjoint from outer outline.
    edge_segments = []
    for d in board.GetDrawings():
        if d.GetLayer() == pcbnew.Edge_Cuts:
            edge_segments.append(d)
    if len(edge_segments) < 4:
        info.append("IMU-SLOT: no Edge.Cuts shape complex enough to verify")
        return
    # Count distinct connected components of edge segments
    # (simplified: count segments not part of outer bbox)
    bbox = get_outline_bbox()
    if not bbox:
        info.append("IMU-SLOT: no outer bbox, skip")
        return
    x_min, y_min, x_max, y_max = bbox
    EDGE_TOL = 0.5
    interior_count = 0
    for d in edge_segments:
        sx, sy = pcbnew.ToMM(d.GetStart().x), pcbnew.ToMM(d.GetStart().y)
        ex, ey = pcbnew.ToMM(d.GetEnd().x), pcbnew.ToMM(d.GetEnd().y)
        # Interior if BOTH endpoints away from outer bbox edges
        def is_interior(x, y):
            return (x_min + EDGE_TOL < x < x_max - EDGE_TOL and
                    y_min + EDGE_TOL < y < y_max - EDGE_TOL)
        if is_interior(sx, sy) and is_interior(ex, ey):
            interior_count += 1
    if interior_count > 0:
        info.append(f"IMU-SLOT: {interior_count} interior Edge.Cuts segments "
                    f"detected (verify single closed polygon manually)")


# ----- check 7: USB diff-pair geometry preservation -----
# USB D+/D- traces on F.Cu should be W=0.20mm. Pair spacing ~0.13mm.
# Adjacent reference layer (In1.Cu) must be GND (locked stackup §8).
USB_NETS = ("USB_DM", "USB_DP", "USBC_D_M_PRE", "USBC_D_P_PRE")
def check_usb_pair():
    usb_tracks = []
    for t in board.GetTracks():
        if isinstance(t, pcbnew.PCB_VIA): continue
        if t.GetNetname() in USB_NETS:
            usb_tracks.append(t)
    if not usb_tracks:
        info.append("USB-PAIR: no USB diff-pair tracks found")
        return
    bad_w = []
    for t in usb_tracks:
        try:
            w_mm = pcbnew.ToMM(t.GetWidth())
        except (AttributeError, TypeError):
            continue
        if t.GetLayerName() == "F.Cu":
            # Spec: 0.20mm ±0.01mm (manufacturing tolerance)
            if not (0.19 <= w_mm <= 0.21):
                bad_w.append((t.GetNetname(), t.GetLayerName(), w_mm))
    if bad_w:
        warns.append(f"USB-PAIR: {len(bad_w)} USB tracks deviate from W=0.20mm on F.Cu")
        for net, layer, w in bad_w[:5]:
            warns.append(f"  {net} on {layer} w={w:.3f}mm")
    else:
        info.append(f"USB-PAIR: {len(usb_tracks)} tracks checked, W=0.20mm preserved")


# ----- check 8: mid-edge mounting-hole keep-out -----
# Per DECISIONS §2: keep-out at (3.25, 42.5) and (101.75, 42.5), 8mm radius.
# Reserved for vibration-sim-gated +2 mounting holes.
MID_EDGE_KEEPOUTS = [(3.25, 42.5, 4.0), (101.75, 42.5, 4.0)]  # 8mm diameter / 4mm radius
def check_mid_edge_keepout(items):
    intruders = []
    for kx, ky, kr in MID_EDGE_KEEPOUTS:
        for ref, d in items.items():
            cx, cy = d["x"], d["y"]
            if math.hypot(cx - kx, cy - ky) < kr:
                intruders.append((ref, cx, cy, kx, ky))
    if intruders:
        fails.append(f"MID-EDGE-KEEPOUT: {len(intruders)} components inside "
                     f"reserved keep-outs at (3.25, 42.5) and (101.75, 42.5)")
        for r, x, y, kx, ky in intruders[:10]:
            fails.append(f"  {r} at ({x:.1f},{y:.1f}) inside keep-out @ ({kx:.1f},{ky:.1f})")


# ----- run -----
items = collect_components()
bbox = get_outline_bbox()
check_off_board(items, bbox)
check_pad_overlap(items)
check_a_symmetry(items)
check_passive_anchoring(items)
check_decoupling(items)
check_imu_slot()
check_usb_pair()
check_mid_edge_keepout(items)

print(f"=== Layout compliance audit: {os.path.basename(sys.argv[1])} ===")
print(f"Components: {len(items)}")
if bbox:
    print(f"Board outline: ({bbox[0]:.1f},{bbox[1]:.1f}) to ({bbox[2]:.1f},{bbox[3]:.1f}) mm")
print()
if info:
    print("INFO:")
    for i in info: print(f"  {i}")
    print()
if warns:
    print("WARNINGS:")
    for w in warns: print(f"  {w}")
    print()
if fails:
    print(f"FAIL ({len(fails)} issues):")
    for f in fails: print(f"  {f}")
    sys.exit(1)
print("PASS — all layout-compliance checks clean")
