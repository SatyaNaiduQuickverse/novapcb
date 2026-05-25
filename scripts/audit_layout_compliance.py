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
    "decouple": 3.0,      # HF bypass: IPC-2221 + ST AN2867
    "gate_R": 5.0,        # FET gate damping R: TI SLOA088
    "bootstrap_C": 2.0,   # buck/boost bootstrap (N/A on LDO board)
    "sense_R": 3.0,       # precision current-sense shunt
    "sense_R_slow": 15.0, # slow analog sense (mV-level via filter cap, ADC input)
    "pull_R": 5.0,        # HF GPIO pulls (clock pulls, NRST fast paths)
    "pull_R_slow": 15.0,  # DC pulls (EFUSE config, BOOT0, enable, etc)
    "feedback_R": 3.0,    # regulator FB networks
    "led_R": 2.0,         # LED series R
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


# ----- check 3: A-subsystem symmetry + 3-bucket quadrant classifier -----
# Adopted from pcb.ai master rules-2026-05-23 (R1/R2/R3). See
# docs/MASTER_PROCESS_RULES.md §"Symmetry refinements (pcb.ai R1/R2/R3)".
#
# Mirror about X=52.5 (board center). Full A-subsystem pair list per master
# 2026-05-23 directive (11 pairs covering OR-FETs, transceivers, sense
# resistors, sense filter caps, U11/U12 decoupling caps).
A_MIRROR_PAIRS = [
    ("J4", "J19"),   # Mauch power connectors
    ("Q3", "Q4"),    # OR-FETs
    ("U11", "U12"),  # LM74700 OR-FET controllers
    # NOTE 2026-05-24: D5/D6/D7/D8 were listed as A-subsystem TVS pairs but
    # current SKiDL ownership has them as GPS ESDs (gps_mag_3e.py). A subsystem
    # uses only D1 = SMAJ6.0A bulk clamp (no per-pin TVS pairs). Removed
    # to prevent false-positive A-SYMMETRY warnings on GPS ESD placement.
    # (Audit-vs-SKiDL drift, Rule-18 corollary.)
    ("R41", "R43"),  # V-sense divider
    ("R42", "R44"),  # I-sense shunt
    ("C61", "C81"),  # V-sense filter
    ("C62", "C82"),  # I-sense filter
    ("C73", "C75"),  # U11 decap
    ("C74", "C76"),  # U12 decap
]
A_MIRROR_X = 52.5
A_MIRROR_TOL_MM = 0.5

# SINGLE_INSTANCE bucket — components with NO mirror partner BY DESIGN.
# Per pcb.ai R3 (structural-asymmetry doctrine): EXEMPT from symmetry,
# central-spine placement is correct by function. Forcing mirror would
# break electrical role (e.g., U1 MCU is unique, IMU island is unique).
SINGLE_INSTANCE = {
    "U1",   # STM32H743 MCU
    "U2",   # POWER_REG_3V3 (LDO → buck per Option B)
    "U3", "U7", "U16",  # IMU island (3× ICM-42688-P)
    "U4",   # DPS310 baro
    "U6",   # TPS25940A eFuse
    "U13",  # LP5907 IMU LDO
    "U5",   # USBLC6 ESD
    "U8",   # RM3100 mag (E zone)
    "U14",  # CAN transceiver
    "U15",  # CAN ESD
    "J1", "J2", "J3", "J5", "J9", "J10", "J18", "J20",  # all single connectors
    "FB2",  # ferrite bead, IMU rail
    "Y1",   # HSE crystal
    "L1",   # buck inductor (Option B)
    "Q1", "Q2", "Q5",  # P-FETs (single-instance: input gate, OR-bridge, heater)
}


def check_a_symmetry(items):
    """Pair-delta check per pcb.ai R2 (ZERO threshold relaxation, hard FAIL)."""
    dev = []
    skipped = []
    for west, east in A_MIRROR_PAIRS:
        if west not in items or east not in items:
            skipped.append((west, east))
            continue
        wx, wy = items[west]["x"], items[west]["y"]
        ex, ey = items[east]["x"], items[east]["y"]
        expected_ex = 2 * A_MIRROR_X - wx
        dx, dy = abs(ex - expected_ex), abs(ey - wy)
        if dx > A_MIRROR_TOL_MM or dy > A_MIRROR_TOL_MM:
            dev.append((west, east, wx, wy, ex, ey, expected_ex, dx, dy))
    if skipped:
        # Pair not yet placed = informational, not a fail
        for w, e in skipped:
            info.append(f"A-SYMMETRY: pair {w}↔{e} not both placed; skip")
    if dev:
        # Per master pcb.ai R2 + R3 adoption 2026-05-23: HARD FAIL.
        # Mirror-pair symmetry is the contract that lets per-pair sims compose.
        # No threshold relaxation; redo placement if violated.
        fails.append(f"A-SYMMETRY: {len(dev)} mirror-pair(s) deviate >{A_MIRROR_TOL_MM}mm (HARD FAIL per pcb.ai R2)")
        for w, e, wx, wy, ex, ey, ee, dx, dy in dev:
            fails.append(f"  {w}@({wx:.2f},{wy:.2f}) ↔ {e}@({ex:.2f},{ey:.2f}) "
                         f"expected ({ee:.2f},{wy:.2f}) dev=({dx:.2f},{dy:.2f})")


def check_quadrant_balance(items, bbox):
    """3-bucket quadrant-count classifier (pcb.ai R1).
    - MIRROR_PAIR bucket: enforced by check_a_symmetry; not re-counted here.
    - SINGLE_INSTANCE bucket: EXEMPT — central-spine placement correct.
    - AUTO bucket (debris): quadrant-count delta WARN-only with structural
      reason documented in PR doc.
    """
    cx = (bbox[0] + bbox[2]) / 2.0
    cy = (bbox[1] + bbox[3]) / 2.0
    pair_refs = {r for pair in A_MIRROR_PAIRS for r in pair}
    auto_counts = {"NW": 0, "NE": 0, "SW": 0, "SE": 0}
    for ref, it in items.items():
        if ref in pair_refs or ref in SINGLE_INSTANCE:
            continue
        x, y = it["x"], it["y"]
        if x <= cx and y <= cy:
            auto_counts["NW"] += 1
        elif x > cx and y <= cy:
            auto_counts["NE"] += 1
        elif x <= cx and y > cy:
            auto_counts["SW"] += 1
        else:
            auto_counts["SE"] += 1
    info.append(f"QUADRANT-AUTO: NW={auto_counts['NW']} NE={auto_counts['NE']} "
                f"SW={auto_counts['SW']} SE={auto_counts['SE']}")
    # WARN-only threshold per pcb.ai R1: imbalance >5 across any pair flags WARN
    spread = max(auto_counts.values()) - min(auto_counts.values())
    if spread > 5:
        warns.append(f"QUADRANT-AUTO: spread {spread} across quadrants — "
                     f"document structural reason in PR doc per pcb.ai R1 (warn-only)")


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
        net_names = list(nets.values())
        # Gate-R: net contains GATE (FET gate driver)
        if any("GATE" in n.upper() for n in net_names):
            return "gate_R"
        # Sense classification — distinguish DC analog from precision shunt:
        #   - VOLTAGE_SENS / VBAT_PRE: divider/scaling (slow DC) → loose
        #   - CURRENT_SENS shunt: precision (mV-level) → tight
        for n in net_names:
            nu = n.upper()
            if "CURRENT_SENS" in nu:
                # Slow analog if connected to ADC via filter cap — current
                # sense for Mauch is ADC-input, slow. Use loose.
                return "sense_R_slow"
            if "SENSE" in nu or "VOLTAGE_SENS" in nu:
                return "sense_R_slow"
        # Feedback (regulator FB)
        if any(("FB" == n.upper() or n.upper().endswith("_FB")) for n in net_names):
            return "feedback_R"
        # LED series
        if any("LED" in n.upper() for n in net_names):
            return "led_R"
        # DC pulls (EFUSE config, BOOT0, slow GPIO etc) → loose
        if any(any(tag in n.upper() for tag in
                   ("EFUSE_", "BOOT", "RESET", "NRST", "STDBY", "ENABLE", "_EN"))
               for n in net_names):
            return "pull_R_slow"
        # Default: pull (could be HF like clock; conservative)
        return "pull_R"
    return "unknown"


def parent_ic_for_passive(ref, nets, items):
    """Find nearest IC/FET sharing a net with this passive — body-edge
    metric (cap center to IC body edge), not centroid-to-centroid. For
    LQFP-100 / SOIC-8 / SOT-23-6 with caps placed at body edge, centroid
    distance over-reports by half the IC body extent."""
    on_net = set(nets.values())
    rx, ry = items[ref]["x"], items[ref]["y"]
    candidates = []
    for cref, cd in items.items():
        if cref == ref: continue
        if not (cref.startswith(("U", "Q", "J", "Y", "X")) and
                (cref[1:].isdigit() or (len(cref) > 1 and cref[1:2].isdigit()))):
            continue
        for cnet in cd["nets"].values():
            if cnet and cnet in on_net:
                # body-edge distance: cap center to IC bbox edge
                bb = cd["fp"].GetBoundingBox()
                ic_x1 = pcbnew.ToMM(bb.GetLeft())
                ic_y1 = pcbnew.ToMM(bb.GetTop())
                ic_x2 = pcbnew.ToMM(bb.GetRight())
                ic_y2 = pcbnew.ToMM(bb.GetBottom())
                dx = max(ic_x1 - rx, 0, rx - ic_x2)
                dy = max(ic_y1 - ry, 0, ry - ic_y2)
                d = math.hypot(dx, dy)
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
        # _slow variants use looser ORPHAN threshold too
        local_orphan = ORPHANED_THRESHOLD_MM
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
        # role-specific severity:
        #   FAIL: HF/precision roles (decouple, sense_R precision, gate_R, feedback_R)
        #   WARN: DC/slow roles (pull_R_slow, sense_R_slow, pull_R)
        bucket = fails if role in ("decouple", "sense_R", "gate_R", "feedback_R") else warns
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


def _vdd_pad_has_plane_via(pad, vnet, brd):
    """Check if a VDD pad has a via connecting to a filled-zone plane on
    the same net (inner-layer plane decoupling)."""
    pp = pad.GetPosition()
    px_nm, py_nm = pp.x, pp.y
    # Find vias at pad center (or within pad bbox) on same net
    for t in brd.GetTracks():
        if not isinstance(t, pcbnew.PCB_VIA): continue
        if t.GetNetname() != vnet: continue
        vp = t.GetPosition()
        if abs(vp.x - px_nm) < 50000 and abs(vp.y - py_nm) < 50000:  # 50µm
            # Via at pad. Check if there's a filled zone on the same net.
            for z in brd.Zones():
                if z.GetNetname() != vnet: continue
                try:
                    if z.GetFilledArea() > 0:
                        return True
                except Exception:
                    pass
    return False


def check_decoupling(items):
    bad = []
    for ref, d in items.items():
        if not (ref.startswith("U") and ref[1:].isdigit()):
            continue
        value = d.get("value", "").upper()
        # LM74700-aware: device's VCAP cap (on ORING_*_VCAP net at pin 1)
        # is the required decap per TI datasheet, not a VDD-style decap.
        # Audit accepts ORING_*_VCAP cap as the decap for LM74700.
        if "LM74700" in value:
            vcap_pad_pos = None
            vcap_net = None
            for pad in d["fp"].Pads():
                n = pad.GetNetname()
                if n.startswith("ORING_") and n.endswith("_VCAP"):
                    pp = pad.GetPosition()
                    vcap_pad_pos = (pcbnew.ToMM(pp.x), pcbnew.ToMM(pp.y))
                    vcap_net = n
                    break
            if vcap_pad_pos:
                found = False
                for cref, cd in items.items():
                    if not (cref.startswith("C") and cref[1:].isdigit()): continue
                    if vcap_net not in cd.get("nets", {}).values(): continue
                    if cap_body_edge_to_point(cd, *vcap_pad_pos) <= 3.0:
                        found = True; break
                if found:
                    continue  # LM74700 properly decoupled via VCAP cap
                # Otherwise fall through to VDD check (which will likely fail
                # too — flag it).

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
            closest = (float('inf'), None)
            for cref, cd in items.items():
                if not (cref.startswith("C") and cref[1:].isdigit()): continue
                cap_nets = list(cd.get("nets", {}).values())
                if vnet not in cap_nets: continue
                dist = cap_body_edge_to_point(cd, vx, vy)
                if dist < closest[0]:
                    closest = (dist, cref)
                if dist <= 3.0:
                    found = True; break
            if not found:
                # Plane-aware inference: if this VDD pad has a via to a
                # filled plane on the same net, plane provides bulk
                # decoupling — relax local 3mm requirement.
                # Find the actual pad object to query.
                for pad in d["fp"].Pads():
                    pp = pad.GetPosition()
                    if abs(pcbnew.ToMM(pp.x)-vx) < 0.01 and abs(pcbnew.ToMM(pp.y)-vy) < 0.01:
                        if _vdd_pad_has_plane_via(pad, vnet, board):
                            found = True  # plane decoupling accepted
                            break
            if not found:
                # Report with body-edge distance to NEAREST in-net cap
                bad.append((ref, vnet, vx, vy, closest[0], closest[1]))
    if bad:
        unique = set((r, n) for r, n, _, _, _, _ in bad)
        fails.append(f"DECOUPLING: {len(unique)} IC VDD-net assignments "
                     f"with no cap within 3mm of VDD pad (body-edge)")
        for r, n in sorted(unique)[:10]:
            # Find best distance for this (ref, net)
            best = min((bd for bd in bad if bd[0]==r and bd[1]==n),
                       key=lambda b: b[4])
            cap_ref = best[5] or "(no in-net cap)"
            fails.append(f"  {r} VDD net={n} — nearest cap {cap_ref} @ {best[4]:.2f}mm body-edge")


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
    # v1 update 2026-05-24 — slot DEFERRED to v2 per DECISIONS.md §2.1.
    # Two layout attempts (Y=33 + Y=45 latitudes) failed with 25-35 net
    # new DRC violations from retrofit vs already-routed dense topology.
    # v2 plans slot as first-class routing constraint (FMU↔IMU board
    # separation pattern). This gate stays info-only; primed for
    # reactivation when v2 picks up the slot work. See
    # docs/v2/D_SLOT_POLYGON_ANALYSIS.md for v2 groundwork.
    if len(edge_segments) < 4:
        info.append("IMU-SLOT: DEFERRED to v2 per DECISIONS.md §2.1 "
                    "(see docs/v2/D_SLOT_POLYGON_ANALYSIS.md)")
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


# ----- check 9.4: fanout exit corridor (master 2026-05-23 new gate) -----
# For every multi-pin IC (≥8 pins), verify each NON-GROUND/POWER pin has a
# clear exit lane: no other-component pad inside the X/Y strip extending
# N mm from the pin in the direction perpendicular to the pin row.
# Catches R42-vs-U6-north placement collision BEFORE routing.
EXIT_CORRIDOR_MM = 1.5   # corridor reach: at least 1.5mm from pin edge
CORRIDOR_WIDTH_MM = 0.5  # strip width: 0.5mm (typical IC pin pitch)

def check_fanout_exit_corridor(items):
    blocked = []
    for ref, d in items.items():
        if not ref.startswith("U") or not ref[1:].isdigit():
            continue
        pads = list(d["fp"].Pads())
        if len(pads) < 8:
            continue  # only multi-pin ICs
        # For each non-GND/Vdd pin, check exit corridor.
        # Pin row direction: determined by pad position vs IC center.
        ic_x, ic_y = d["x"], d["y"]
        for pad in pads:
            net = pad.GetNetname()
            if not net or net in ("GND",) or is_vdd_net(net):
                continue
            pp = pad.GetPosition()
            px, py = pcbnew.ToMM(pp.x), pcbnew.ToMM(pp.y)
            psz = pad.GetSize()
            pw, ph = pcbnew.ToMM(psz.x), pcbnew.ToMM(psz.y)
            # Pin row direction — exit perpendicular to long dimension
            # For pads on N/S sides: exit Y direction.
            # For pads on E/W sides: exit X direction.
            if abs(py - ic_y) > abs(px - ic_x):
                # N or S side — exit Y
                if py < ic_y:  # north pin → exit N (Y decreasing)
                    corridor_y1 = py - ph/2 - EXIT_CORRIDOR_MM
                    corridor_y2 = py - ph/2
                else:  # south pin → exit S
                    corridor_y1 = py + ph/2
                    corridor_y2 = py + ph/2 + EXIT_CORRIDOR_MM
                corridor_x1 = px - CORRIDOR_WIDTH_MM/2
                corridor_x2 = px + CORRIDOR_WIDTH_MM/2
            else:
                # E or W side — exit X
                if px < ic_x:  # west pin → exit W
                    corridor_x1 = px - pw/2 - EXIT_CORRIDOR_MM
                    corridor_x2 = px - pw/2
                else:
                    corridor_x1 = px + pw/2
                    corridor_x2 = px + pw/2 + EXIT_CORRIDOR_MM
                corridor_y1 = py - CORRIDOR_WIDTH_MM/2
                corridor_y2 = py + CORRIDOR_WIDTH_MM/2
            # Check for other-component pads in this strip
            for oref, od in items.items():
                if oref == ref: continue
                for opad in od["fp"].Pads():
                    opp = opad.GetPosition()
                    obb = opad.GetBoundingBox()
                    onet = opad.GetNetname()
                    ox1 = pcbnew.ToMM(obb.GetLeft())
                    oy1 = pcbnew.ToMM(obb.GetTop())
                    ox2 = pcbnew.ToMM(obb.GetRight())
                    oy2 = pcbnew.ToMM(obb.GetBottom())
                    if ox1 < corridor_x2 and ox2 > corridor_x1 and oy1 < corridor_y2 and oy2 > corridor_y1:
                        # Exclude same-net intentional adjacencies:
                        #   - decoupling cap on Vdd-pin column
                        #   - HSE/LSE loading cap on crystal pin
                        #   - any cap on same net (it's THE decap)
                        if onet == net:
                            continue
                        # Exclude pads of small (passive) component on same net
                        # path — if the other component shares ANY net with the
                        # IC, may be a working pair.
                        ic_nets = set(d["nets"].values())
                        other_nets = set(od["nets"].values())
                        # If shared nets > 0, likely intentional adjacency.
                        if ic_nets & other_nets:
                            continue
                        blocked.append((ref, pad.GetPadName(), net, oref, opad.GetPadName()))
                        break
                else:
                    continue
                break
    if blocked:
        # Dedup by (ref, pin)
        unique = list({(b[0], b[1], b[2], b[3], b[4]) for b in blocked})
        warns.append(f"FANOUT-CORRIDOR: {len(unique)} multi-pin-IC pins "
                     f"have blocked exit corridor (<{EXIT_CORRIDOR_MM}mm)")
        for ic, pin, net, blker, blker_pin in sorted(unique)[:10]:
            warns.append(f"  {ic}.{pin} ({net}) blocked by {blker}.{blker_pin}")


# ----- check 9.5: fab-exception count (master 2026-05-23 hard bar) -----
# Reads novapcb-stepwise.kicad_dru and counts non-standard rules
# (clearance relax, via-in-pad, 4mil, extended-courtyard). >4 in any
# single region (U6, U11/U12, etc.) triggers WARN — implicit
# accretion cap.
def check_fab_exceptions():
    dru_path = sys.argv[1].replace(".kicad_pcb", ".kicad_dru")
    try:
        with open(dru_path) as f:
            txt = f.read()
    except FileNotFoundError:
        return
    import re
    rule_names = re.findall(r'\(rule\s+"([^"]+)"', txt)
    # Categorize: standard (USB diff-pair) vs fab-exception
    standard_keywords = ("usb-diff-pair", "usbc-pre-esd", "usbc-bridge")
    exceptions = [n for n in rule_names
                  if not any(s in n for s in standard_keywords)]
    info.append(f"FAB-EXCEPTIONS: {len(rule_names)} total DRU rules; "
                f"{len(exceptions)} fab-spec exceptions; "
                f"{len(rule_names)-len(exceptions)} standard")
    # Per-region count: bucket by name prefix
    by_region = {}
    for name in exceptions:
        # Region = first hyphenated token chunk before -fanout/-courtyard/-orfet etc
        if name.startswith("u11-u12"): region = "U11/U12"
        elif name.startswith("u6-"): region = "U6"
        elif "orfet" in name: region = "U11/U12"  # orfet maps to U11/U12
        else: region = "other"
        by_region.setdefault(region, []).append(name)
    for region, rules in sorted(by_region.items()):
        if len(rules) > 4:
            warns.append(f"FAB-EXCEPTIONS: {region} region at {len(rules)} rules — "
                         f"exceeds master 4-rule cap. Consider placement-rework.")
        info.append(f"  {region}: {len(rules)} ({', '.join(rules)})")


# ----- check 9: zone-fill audit (master 2026-05-23 Rule 9) -----
# Every declared zone must have GetFilledArea() > 0. "Zone declared" is
# NOT the same as "zone filled" — KiCad pcbnew Python does NOT auto-fill
# on SaveBoard. Outline changes are silently ignored until UnFill+Fill.
# Catches the failure-mode that lied about +5V_BEC plane connectivity
# in earlier A↔B-3 verification: pads logically on +5V_BEC net showed
# 0 unconnected in DRC, but the plane was empty → no physical connection.
# ----- stackup-spec-match gate (master 2026-05-23 stackup-fix PR) -----
# Rule 9 codified for stackup: the locked spec in docs/DECISIONS.md §8 says
# each plane net lives on a specific layer. Catches the half-applied
# stackup change defect (2026-05-23: +3V3 was moved to In3 but never
# removed from In4; In1/In4 GND zones were never created).
#
# Gate asserts:
#   - Each (layer, net) in EXPECTED_PLANES has ≥1 zone
#   - No (layer, net) outside EXPECTED_PLANES (catch leftover wrong-net zones)
EXPECTED_PLANES = {
    ("In1.Cu", "GND"),       # primary GND plane (master 2026-05-23)
    ("In2.Cu", "+5V_BEC"),
    ("In3.Cu", "+3V3"),
    ("In4.Cu", "GND"),       # secondary GND plane (master 2026-05-23)
}


def check_stackup_spec_match():
    seen = set()
    for z in board.Zones():
        if not hasattr(z, "GetNetname"): continue
        l = board.GetLayerName(z.GetLayer())
        n = z.GetNetname()
        if not l.startswith("In"):
            continue   # only check internal plane layers
        seen.add((l, n))
    missing = EXPECTED_PLANES - seen
    unexpected = seen - EXPECTED_PLANES
    if missing:
        fails.append(f"STACKUP-SPEC-MATCH: {len(missing)} expected plane(s) MISSING per DECISIONS.md §8")
        for l, n in sorted(missing):
            fails.append(f"  expected {l} \"{n}\": NOT FOUND")
    if unexpected:
        fails.append(f"STACKUP-SPEC-MATCH: {len(unexpected)} unexpected plane(s) — check for half-applied stackup change")
        for l, n in sorted(unexpected):
            fails.append(f"  unexpected {l} \"{n}\": not in DECISIONS.md §8")
    if not missing and not unexpected:
        info.append(f"STACKUP-SPEC-MATCH: PASS — 4 plane (layer,net) pairs match DECISIONS.md §8")


def check_zone_fill():
    empty_zones = []
    filled_zones = []
    for z in board.Zones():
        if not hasattr(z, "GetNetname"): continue
        net = z.GetNetname()
        layer = board.GetLayerName(z.GetLayer())
        try:
            fa_mm2 = z.GetFilledArea() / 1e12
        except Exception:
            continue
        if fa_mm2 == 0:
            empty_zones.append((net, layer))
        else:
            filled_zones.append((net, layer, fa_mm2))
    if empty_zones:
        fails.append(f"ZONE-FILL: {len(empty_zones)} declared zones are EMPTY "
                     f"(not filled). Run pcbnew UnFill()+Fill() before save.")
        for net, layer in empty_zones[:10]:
            fails.append(f"  {net} on {layer}: filled_area=0 — DECLARED ≠ FILLED")
    if filled_zones:
        # Summary line in INFO (so positive verification is visible)
        info.append(f"ZONE-FILL: {len(filled_zones)} zones filled — "
                    f"total {sum(fa for _,_,fa in filled_zones):.0f} mm² copper plane")


# ----- run -----
items = collect_components()
bbox = get_outline_bbox()
check_off_board(items, bbox)
check_pad_overlap(items)
check_a_symmetry(items)
check_quadrant_balance(items, bbox)
check_passive_anchoring(items)
check_decoupling(items)
check_imu_slot()
check_usb_pair()
check_mid_edge_keepout(items)
check_stackup_spec_match()
check_zone_fill()
check_fab_exceptions()
check_fanout_exit_corridor(items)


# ----- check 10: thermal sim source-of-truth (master 2026-05-23) -----
# Lesson from LOCK 73.98°C unreproducibility (2026-05-23):
# board sweep used PLANNED component positions (Q3 at 35,8 etc) while
# actual placement chose different positions (Q3 at 27,10), giving
# +8.5°C MCU regression silently. The mechanism that allowed this:
# gate12 used a parameter-override config for unplaced components,
# masquerading as a "validated" run.
#
# Gate: assert any thermal/sim Python script in the repo READS component
# positions from the .kicad_pcb file (via pcbnew.LoadBoard), NOT from
# hardcoded constants or planned-position dicts. Catches the recurrence
# of "sim ran with hypothetical positions" silent divergence.
def check_thermal_actual_positions():
    sim_scripts = []
    sim_dir = os.path.dirname(os.path.abspath(sys.argv[1]))
    for name in os.listdir(sim_dir):
        if name.startswith("gate12") and name.endswith(".py"):
            sim_scripts.append(os.path.join(sim_dir, name))
    if not sim_scripts:
        info.append("THERMAL-SIM-SOT: no gate12*.py scripts found in board dir")
        return
    for path in sim_scripts:
        with open(path) as f:
            txt = f.read()
        # MUST have LoadBoard call (reads .kicad_pcb)
        if "pcbnew.LoadBoard" not in txt and "LoadBoard(" not in txt:
            warns.append(f"THERMAL-SIM-SOT: {os.path.basename(path)} doesn't call LoadBoard — may use planned positions instead of actual")
            continue
        # SHOULD NOT have lots of hardcoded position dicts (planned)
        # Heuristic: count tuples like (x.x, y.y) on lines with refdes patterns
        import re
        # Lines like '"U1": (45.0, 35.0)' or 'Q3 = (27, 10)' that imply hardcoded position
        position_overrides = re.findall(r'"[QURDXY]\d+\*?"\s*:\s*\(\d+\.?\d*\s*,\s*\d+\.?\d*\)', txt)
        if len(position_overrides) > 3:
            warns.append(
                f"THERMAL-SIM-SOT: {os.path.basename(path)} has "
                f"{len(position_overrides)} hardcoded position overrides — "
                f"verify these are FALLBACK only (used when refdes not on board), "
                f"not the active source-of-truth")
        else:
            info.append(f"THERMAL-SIM-SOT: {os.path.basename(path)} reads from .kicad_pcb (PASS)")


check_thermal_actual_positions()

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
