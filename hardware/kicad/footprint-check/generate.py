#!/usr/bin/env python3
"""
novapcb Phase 2.5 — footprint placement reality check.

Authoritative source for hardware/kicad/footprint-check/footprint-check.kicad_pcb.
Re-run with: python3 generate.py
Produces the .kicad_pcb deterministically (re-run yields the same file modulo
KiCad's internal UUIDs).

Goal: verify that the Phase 2 peripheral set physically fits on a Pixhawk-standard
mini-FC board outline (36 x 36 mm, with 30.5 x 30.5 mm c-to-c M3 mounting holes).
Placement-only — no schematic, no netlist, no routing, no passives.

Sources for the spec:
  - CLAUDE.md §1 (updated 2026-05-20): "board outline ~36 x 36 mm, mounting holes
    30.5 x 30.5 mm c-to-c M3 (Pixhawk-standard pattern)"
  - DECISIONS.md §2 (clarified 2026-05-20)
  - Master Phase 2.5 dispatch + escalation_log #2 adjudication (2026-05-20T02:28Z)

Component selection per Phase 2 hwdef.dat + master Phase 2.5 contract P0.4 inventory
(see hardware/kicad/footprint-check/P0_REPORT.md §P0.4).

Fit-check methodology: this is a gross-fit sketch. Courtyard overlaps from
connector locating-tabs / cable-egress keep-outs that extend off-PCB are
EXPECTED and not real fit issues. Component-body overlaps are real and indicate
the layout doesn't fit. The DRC report should be read with that distinction in
mind — see notes.md for the assessment.
"""

import os
import sys
import pcbnew

# ---------- spec ----------
BOARD_W = 36.0      # mm — board outline (Phase 2.5 master decision A, 2026-05-20)
BOARD_H = 36.0      # mm — board outline (square)
HOLE_SPACING = 30.5 # mm — c-to-c, Pixhawk-standard mini-FC mount pattern
HOLE_INSET = (BOARD_W - HOLE_SPACING) / 2.0  # 2.75 mm inset from each edge
HOLE_DRILL = 3.2    # mm — M3 clearance (finished hole)
KICAD_FP_ROOT = "/usr/share/kicad/footprints"

OUT_PCB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "footprint-check.kicad_pcb")

# ---------- helpers ----------
def mm(x):
    return pcbnew.FromMM(float(x))

def pt(x_mm, y_mm):
    return pcbnew.VECTOR2I(mm(x_mm), mm(y_mm))

def rotation(deg):
    return pcbnew.EDA_ANGLE(float(deg), pcbnew.DEGREES_T)

def load_fp(lib_pretty, fp_name):
    path = os.path.join(KICAD_FP_ROOT, lib_pretty)
    fp = pcbnew.FootprintLoad(path, fp_name)
    if fp is None:
        raise RuntimeError(f"FootprintLoad failed: {path} / {fp_name}")
    return fp

def place(board, fp, x_mm, y_mm, rot_deg=0, ref="REF", value="VAL", flip_bottom=False):
    fp.SetPosition(pt(x_mm, y_mm))
    if rot_deg:
        fp.SetOrientation(rotation(rot_deg))
    fp.SetReference(ref)
    fp.SetValue(value)
    board.Add(fp)
    # Flip requires the footprint to be in the board first (KiCad 9 quirk;
    # calling Flip on an unowned footprint segfaults).
    if flip_bottom:
        fp.Flip(pt(x_mm, y_mm), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    return fp

def add_edge_segment(board, x1_mm, y1_mm, x2_mm, y2_mm):
    seg = pcbnew.PCB_SHAPE(board)
    seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
    seg.SetStart(pt(x1_mm, y1_mm))
    seg.SetEnd(pt(x2_mm, y2_mm))
    seg.SetLayer(pcbnew.Edge_Cuts)
    seg.SetWidth(mm(0.15))
    board.Add(seg)

def add_m3_hole(board, x_mm, y_mm, label):
    fp = load_fp("MountingHole.pretty", "MountingHole_3.2mm_M3_Pad")
    fp.SetPosition(pt(x_mm, y_mm))
    fp.SetReference(label)
    fp.SetValue("M3")
    board.Add(fp)
    return fp

# ---------- main ----------
def main():
    board = pcbnew.NewBoard(OUT_PCB)

    # --- board outline: 36 x 36 mm square ---
    add_edge_segment(board, 0.0,     0.0,     BOARD_W, 0.0)
    add_edge_segment(board, BOARD_W, 0.0,     BOARD_W, BOARD_H)
    add_edge_segment(board, BOARD_W, BOARD_H, 0.0,     BOARD_H)
    add_edge_segment(board, 0.0,     BOARD_H, 0.0,     0.0)

    # --- 4× M3 mounting holes at 30.5 c-to-c spacing (Pixhawk-standard) ---
    hole_xs = (HOLE_INSET, BOARD_W - HOLE_INSET)
    hole_ys = (HOLE_INSET, BOARD_H - HOLE_INSET)
    add_m3_hole(board, hole_xs[0], hole_ys[0], "H1")  # bottom-left
    add_m3_hole(board, hole_xs[1], hole_ys[0], "H2")  # bottom-right
    add_m3_hole(board, hole_xs[0], hole_ys[1], "H3")  # top-left
    add_m3_hole(board, hole_xs[1], hole_ys[1], "H4")  # top-right

    # --- MCU: STM32H743VIT6 LQFP-100 14×14 mm ---
    # Centered slightly south of board center to give the top edge room for
    # USB-C + microSD without invading MCU body. At (18, 14): body (11..25, 7..21).
    mcu = load_fp("Package_QFP.pretty", "LQFP-100_14x14mm_P0.5mm")
    place(board, mcu, 18.0, 14.0, rot_deg=0, ref="U1", value="STM32H743VIT6")

    # --- IMU: ICM-42688-P (generic LGA-14 3x2.5 P0.5) ---
    # Place north of MCU in the gap between MCU north edge (Y=21) and microSD
    # south edge. At (18, 23): body (16.5..19.5, 21.75..24.25). Clear of MCU
    # (Y=21) by 0.75mm. Vibration-sensitive — center placement is fine.
    imu = load_fp("Package_LGA.pretty", "LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y")
    place(board, imu, 18.0, 23.0, rot_deg=0, ref="U2", value="ICM-42688-P")

    # --- Barometer: DPS310 (Bosch LGA-8 2x2.5 P0.65 geom-match) ---
    # Place east of MCU. MCU east edge X=25; baro at (27, 14): body (26..28, 12.75..15.25).
    # Clear of MCU by 1mm. Phase 4 may want it isolated by venting holes — Phase 2.5
    # ignores that.
    baro = load_fp("Package_LGA.pretty", "Bosch_LGA-8_2x2.5mm_P0.65mm_ClockwisePinNumbering")
    place(board, baro, 27.0, 14.0, rot_deg=0, ref="U3", value="DPS310")

    # --- USB-C receptacle: HRO TYPE-C 31-M-12 (mid-mount, 16-pin) ---
    # Top edge LEFT. Body ~8.9 × 7.3, mid-mount. At (12, 33) rot=180: pads at
    # Y~29.5..33.5, body X=7.55..16.45. Clear of H3 keepout (X<5.95) by 1.6mm.
    # Clear of MCU body (Y=7..21) by 8.5mm. Cable egress: top edge.
    usbc = load_fp("Connector_USB.pretty", "USB_C_Receptacle_HRO_TYPE-C-31-M-12")
    place(board, usbc, 12.0, 33.0, rot_deg=180, ref="J1", value="USB-C")

    # --- microSD push-push: Hirose DM3AT-SF-PEJM5 ---
    # Top edge RIGHT. Body ~12 × 11.5 (card slot orientation). At (25, 30) rot=180:
    # body X=19..31, Y=24..36. Conflict: X=31 clips H4 keepout (X=30.05..36.45)
    # by ~1mm. Push west to (23, 30): body X=17..29 (H4 keepout starts X=30.05,
    # clear 1.05mm). Y=24 clear of MCU body Y=21 by 3mm. Card slot exits top
    # edge (Y=36).
    msd = load_fp("Connector_Card.pretty", "microSD_HC_Hirose_DM3AT-SF-PEJM5")
    place(board, msd, 23.0, 30.0, rot_deg=180, ref="J2", value="microSD")

    # --- JST-GH connectors (Pixhawk-standard 4 ports) ---
    # Standard ports: telem 6-pin, GPS+mag+safety+buzzer 10-pin (combined per
    # Pixhawk spec), power 6-pin, CAN/aux 4-pin.

    # Telem 6-pin: left edge lower. Body ~8.5×4.5 (Horizontal SM06B-GHS).
    # Rot 90 → body Y=Yc-4.25..Yc+4.25, X=Xc-2.25..Xc+2.25.
    # At (3.5, 11) rot=90: body Y=6.75..15.25, X=1.25..5.75. H1 keepout
    # X<5.95, Y<5.95 — Y range 6.75..15.25 clear of H1. X range 1.25..5.75
    # within left edge.
    jgh_telem = load_fp("Connector_JST.pretty",
                        "JST_GH_SM06B-GHS-TB_1x06-1MP_P1.25mm_Horizontal")
    place(board, jgh_telem, 3.5, 11.0, rot_deg=90, ref="J3", value="TELEM_6P")

    # Power 6-pin: left edge upper. Same footprint.
    # At (3.5, 25) rot=90: body Y=20.75..29.25, X=1.25..5.75. H3 keepout
    # Y>29.55 — clear. Power module needs to be at standardized Pixhawk
    # pinout (matches Mauch 6-pin connector from DECISIONS §5).
    jgh_power = load_fp("Connector_JST.pretty",
                        "JST_GH_SM06B-GHS-TB_1x06-1MP_P1.25mm_Horizontal")
    place(board, jgh_power, 3.5, 25.0, rot_deg=90, ref="J4", value="POWER_6P")

    # GPS combined 10-pin: right edge. Body ~13.5×4.5 (SM10B-GHS Horizontal).
    # Rot 270 → body Y=Yc-6.75..Yc+6.75, X=Xc-2.25..Xc+2.25.
    # At (32.5, 13) rot=270: body Y=6.25..19.75, X=30.25..34.75. H2 keepout
    # Y<5.95 — clear. X=30.25..34.75 within right edge (board X=36).
    jgh_gps = load_fp("Connector_JST.pretty",
                      "JST_GH_SM10B-GHS-TB_1x10-1MP_P1.25mm_Horizontal")
    place(board, jgh_gps, 32.5, 13.0, rot_deg=270, ref="J5", value="GPS_10P")

    # CAN/aux 4-pin: right edge upper. Body ~6×4.5 (SM04B-GHS Horizontal).
    # Rot 270 → body Y=Yc-3..Yc+3, X=Xc-2.25..Xc+2.25.
    # At (32.5, 24) rot=270: body Y=21..27, X=30.25..34.75. Gap to J5 (Y<19.75)
    # is 1.25mm. H4 keepout Y>29.55 — clear (27 < 29.55).
    jgh_aux = load_fp("Connector_JST.pretty",
                      "JST_GH_SM04B-GHS-TB_1x04-1MP_P1.25mm_Horizontal")
    place(board, jgh_aux, 32.5, 24.0, rot_deg=270, ref="J6", value="CAN_AUX_4P")

    # --- ESC outputs: 2× JST-SH 1x04 horizontal = 8 channels ---
    # Bottom edge. Body ~6×4.5 each (SM04B-SRSS Horizontal).
    # At (11, 3.5) rot=0: body X=8..14, Y=1.25..5.75. H1 keepout X<5.95 —
    # clear of X=8.
    # At (22, 3.5): body X=19..25, Y=1.25..5.75. H2 keepout X>30.05 — clear.
    # MCU body Y>7 — clear of Y<5.75 by 1.25mm.
    esc1 = load_fp("Connector_JST.pretty",
                   "JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal")
    place(board, esc1, 11.0, 3.5, rot_deg=0, ref="J7", value="ESC_1-4")

    esc2 = load_fp("Connector_JST.pretty",
                   "JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal")
    place(board, esc2, 22.0, 3.5, rot_deg=0, ref="J8", value="ESC_5-8")

    # --- SWD debug header: 2x5 1.27mm Cortex standard ---
    # Place on BOTTOM layer (B.Cu) — keeps top side free. Many production
    # mini-FCs do this (MatekH743 has SWD pads on bottom).
    # Use the vertical SMD variant + flip to bottom.
    # On bottom: place south-of-MCU horizontally. At (28.5, 8) on B.Cu rot=0:
    # body X=24.75..32.25, Y=6.5..9.5. Conflict candidates: J8 (X=19..25, Y=1.25..5.75)
    # — clear (X>24.75 starts where J8 ends). H2 keepout (X>30.05, Y<5.95) —
    # SWD Y>6.5 clear of H2 Y zone.
    swd = load_fp("Connector_PinHeader_1.27mm.pretty",
                  "PinHeader_2x05_P1.27mm_Vertical_SMD")
    place(board, swd, 28.5, 8.0, rot_deg=0, ref="J9", value="SWD",
          flip_bottom=True)

    # --- save ---
    pcbnew.SaveBoard(OUT_PCB, board)
    print(f"Wrote {OUT_PCB}")
    print(f"  size: {os.path.getsize(OUT_PCB)} bytes")
    print(f"  KiCad: {pcbnew.Version()}")
    print(f"  board: {BOARD_W} x {BOARD_H} mm, "
          f"M3 holes @ {HOLE_SPACING} x {HOLE_SPACING} c-to-c "
          f"(inset {HOLE_INSET:.2f} mm)")
    print(f"  components: MCU (center-S) + IMU (N of MCU) + baro (E of MCU) "
          f"+ USB-C (top-L) + microSD (top-R) + 4×JST-GH (sides) "
          f"+ 2×JST-SH (bot, ESC) + SWD (BOTTOM layer)")

if __name__ == "__main__":
    main()
