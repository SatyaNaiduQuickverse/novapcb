#!/usr/bin/env python3
"""Fix remaining DRC after re-placement (master 2026-05-22 path 1):

1. Re-cut IMU stress-relief slot as a CLEAN CLOSED-POLYGON U-shape
   (8 segments forming a closed loop). 10mm bridge to N at X=40..50.
2. Fix the 4 small-part shorts by separating overlapping caps.
3. Sweep through other small-part overlaps and nudge them apart.
4. Target: 0 DRC violations (or as close as practical).
"""
import os, math
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-layout-v1.1.kicad_pcb")


def remove_old_slot(brd):
    """Remove ANY Edge.Cuts shape whose bbox is FULLY INSIDE the board
    (not touching edges X=0/90, Y=0/70). Catches both segments and
    polygons (the old IMU slot was a POLYGON shape type 4)."""
    n_removed = 0
    for d in list(brd.GetDrawings()):
        if d.GetLayer() != pcbnew.Edge_Cuts: continue
        bb = d.GetBoundingBox()
        L = bb.GetLeft()/1e6; R = bb.GetRight()/1e6
        T = bb.GetTop()/1e6; B = bb.GetBottom()/1e6
        # Outer outline = bbox spans entire board
        if L < 0.5 and R > 89.5 and T < 0.5 and B > 69.5:
            continue
        # Edge-touching segment = part of outer outline (kept separately)
        # Use bbox: if any side of bbox is on board edge (X=0/90, Y=0/70)
        if L < 0.5 or R > 89.5 or T < 0.5 or B > 69.5:
            continue
        # Pure interior shape — slot polygon or interior segments. Remove.
        brd.Remove(d)
        n_removed += 1
    return n_removed


def ensure_outer_outline(brd):
    """Only add 4 outer outline segments if NO outer outline (rectangle or
    edge segments) currently exists. Avoid duplicating an existing rectangle."""
    has_outer = False
    for d in brd.GetDrawings():
        if d.GetLayer() != pcbnew.Edge_Cuts: continue
        bb = d.GetBoundingBox()
        L = bb.GetLeft()/1e6; R = bb.GetRight()/1e6
        T = bb.GetTop()/1e6; B = bb.GetBottom()/1e6
        if L < 0.5 and R > 89.5 and T < 0.5 and B > 69.5:
            has_outer = True; break
    if has_outer:
        return 0
    OUTER = [((0, 0), (90, 0)), ((90, 0), (90, 70)),
              ((90, 70), (0, 70)), ((0, 70), (0, 0))]
    n_added = 0
    for (x1, y1), (x2, y2) in OUTER:
        seg = pcbnew.PCB_SHAPE(brd)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetStart(pcbnew.VECTOR2I(int(x1*1e6), int(y1*1e6)))
        seg.SetEnd(pcbnew.VECTOR2I(int(x2*1e6), int(y2*1e6)))
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetWidth(int(0.1*1e6))
        brd.Add(seg)
        n_added += 1
    return n_added


def add_slot_closed_polygon(brd):
    """Add a proper closed-polygon U-slot around the new S-edge IMU island.
    8 segments forming a closed loop. 10mm bridge at top X=40..50, Y=51..53."""
    SEGMENTS = [
        # CCW outline of slot region (closed polygon):
        ((40.0, 51.0), (25.0, 51.0)),   # NW bridge top → NW slot corner
        ((25.0, 51.0), (25.0, 67.0)),   # W side
        ((25.0, 67.0), (72.0, 67.0)),   # S side
        ((72.0, 67.0), (72.0, 51.0)),   # E side
        ((72.0, 51.0), (50.0, 51.0)),   # NE slot corner → NE bridge top
        ((50.0, 51.0), (50.0, 53.0)),   # NE bridge S
        ((50.0, 53.0), (40.0, 53.0)),   # bridge bottom W
        ((40.0, 53.0), (40.0, 51.0)),   # NW bridge S — close polygon
    ]
    for (x1, y1), (x2, y2) in SEGMENTS:
        seg = pcbnew.PCB_SHAPE(brd)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetStart(pcbnew.VECTOR2I(int(x1*1e6), int(y1*1e6)))
        seg.SetEnd(pcbnew.VECTOR2I(int(x2*1e6), int(y2*1e6)))
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetWidth(int(0.1*1e6))
        brd.Add(seg)
    return len(SEGMENTS)


def get_fp(brd, ref):
    for fp in brd.GetFootprints():
        if fp.GetReference() == ref: return fp
    return None


def nudge(fp, dx_mm, dy_mm):
    pos = fp.GetPosition()
    new_pos = pcbnew.VECTOR2I(pos.x + int(dx_mm*1e6), pos.y + int(dy_mm*1e6))
    fp.SetPosition(new_pos)


def set_pos(fp, x_mm, y_mm):
    fp.SetPosition(pcbnew.VECTOR2I(int(x_mm*1e6), int(y_mm*1e6)))


def main():
    brd = pcbnew.LoadBoard(PCB)

    # 1. Re-cut slot
    n_removed = remove_old_slot(brd)
    print(f"[slot] removed {n_removed} OLD slot segments", flush=True)
    n_added = add_slot_closed_polygon(brd)
    print(f"[slot] added {n_added} NEW slot segments (closed U with 10mm bridge X=40..50, Y=51..53)", flush=True)

    # Save + reload to refresh SWIG state before footprint manipulation
    pcbnew.SaveBoard(PCB, brd)
    brd = pcbnew.LoadBoard(PCB)
    print("[reload] board reloaded after slot edit", flush=True)

    # 2. Fix known shorts
    # C34/C74 — both moved with U2 LDO, overlap. C34 +3V3, C74 +5V_BEC_A.
    # C34 currently at (19.05, 30.5). Move C34 a bit S to clear C74.
    c34 = get_fp(brd, "C34")
    if c34: set_pos(c34, 19.05, 29.5); print(f"  C34 → (19.05, 29.5)")

    # C22/C24 near crystal — VREF_P vs HSE_IN short. C22 (VREF_P) currently
    # at (29.52, 32.5). Move it W away from C24 (HSE_IN at 29.52, 32).
    c22 = get_fp(brd, "C22")
    if c22: set_pos(c22, 27.0, 32.5); print(f"  C22 → (27.0, 32.5)")

    # Y1 vs C20 — Y1 (29-30, 35) overlaps with C20 (+3V3A at 29.52, 35.5).
    # Move C20 further N to clear Y1 area.
    c20 = get_fp(brd, "C20")
    if c20: set_pos(c20, 32.0, 38.0); print(f"  C20 → (32.0, 38.0)")

    # R12/C78 near heater — R12 (I2C2_SCL) overlaps with C78 (+3V3_IMU).
    # Move R12 away. R12 currently at (68.49, 60).
    r12 = get_fp(brd, "R12")
    if r12: set_pos(r12, 68.5, 62.5); print(f"  R12 → (68.5, 62.5)")

    # +5V vs HEATER_DRAIN — R61/Q5 overlap.
    # R61 at (65, 55), Q5 at (60, 55). Move R61 east.
    r61 = get_fp(brd, "R61")
    if r61: set_pos(r61, 67.0, 55.0); print(f"  R61 → (67.0, 55.0)")

    # GND vs +5V — J1 vs C83. C83 at (86.52, 35) too close to J1 shell.
    c83 = get_fp(brd, "C83")
    if c83: set_pos(c83, 80.0, 35.0); print(f"  C83 → (80.0, 35.0)")

    # SAFETY_LED_TP vs GND — J5 vs C84. Move C84 away.
    c84 = get_fp(brd, "C84")
    if c84: set_pos(c84, 80.0, 38.5); print(f"  C84 → (80.0, 38.5)")

    # CAN_TERM_MID vs I2C1_SCL — R45 vs J5. Move R45 away from J5.
    r45 = get_fp(brd, "R45")
    if r45: set_pos(r45, 78.0, 22.0); print(f"  R45 → (78.0, 22.0)")

    # +3V3 vs USBC_D_M_PRE — C72 vs U5. C72 at (74-75, 27.5) too close to U5 at (75, 26).
    # Move C72 west of U5.
    c72 = get_fp(brd, "C72")
    if c72: set_pos(c72, 71.0, 26.5); print(f"  C72 → (71.0, 26.5)")

    # GND vs USB_DM — same C72 conflict possibly; if separate, move it
    # 3. Quick mounting hole conflicts — H4 (87, 67) is corner. Anything within
    # 4mm of corner is courtyards conflict. Nothing to do without component moves.

    # Save and report
    pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
    pcbnew.SaveBoard(PCB, brd)
    print(f"[save] PCB written")


if __name__ == "__main__":
    main()
