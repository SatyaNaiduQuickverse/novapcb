#!/usr/bin/env python3
"""
novapcb v1.1 R3 placement — physics-guided 5-zone layout with IMU island.

Generates `novapcb-layout-v1.1.kicad_pcb` with all components positioned per
the R3 placement strategy (master directive 2026-05-21):

  - Subsystems separated; generous spacing; thermal/SI-aware
  - 3-IMU cluster placed WELL: center-board over solid GND plane, away from
    edges/mounting-holes/high-current traces; IMUs + baros + LP5907 + heater
    grouped as the "IMU island"
  - First-cut IMU stress-relief slot: perimeter kerf + ≥3mm bridge around
    the IMU island (FEA-output refines at R6)
  - 2 power inputs (J4 + J19) + OR-ing FETs (Q3 + Q4) + LM74700s (U11/U12)
    grouped in the power zone (west)
  - 1 CAN port (J20 + U14 TJA1051 + U15 PESD2CAN) on the connector edge

## Board geometry

  90 × 70 mm 6-layer JLC06161H-7628 stackup (carried forward from v1.0
  layout-v2; +12.5% area to accommodate the v1.1 additions while keeping
  thermal margin from Step 4 FEA).
  4× M3 mounting holes at 3 mm corner inset.

## Zones (X-axis layout, board 90 mm wide):

  Zone POWER     X = 0  → 22 mm   J4, J19, Q2, Q3, Q4, U6 eFuse, U11, U12,
                                  D1, U2 LDO, +5V/+3V3 bulks
  Zone MCU       X = 22 → 60 mm   U1 STM32H743 centered, Y1 crystal,
                                  USB-C J1, microSD J2 (B.Cu), SWD J9 (B.Cu)
  Zone IMU ISLAND X = 60 → 80 mm  3 IMUs (U3+U8+U9) + 2 baros (U4 B.Cu + U7)
                                  + LP5907 U13 + heater (Q5 + R61) — with
                                  PERIMETER KERF (stress-relief slot)
  Zone CAN+TELEM X = 80 → 90 mm   J20 CAN connector + U14 TJA1051 + U15 PESD2CAN
                                  (east short edge)

  Long edges (Y-axis):
    Y = 0 → 8 mm    ESC pads J11-J18 + J9 SWD (B.Cu)
    Y = 62 → 70 mm  Connector edge: J3 telem + J5 GPS+mag + J10 CRSF

## IMU stress-relief slot (first-cut, FEA-refined later)

  U-shape kerf in Edge.Cuts:
    - Top arm at Y=58 mm from X=62 to X=78 mm (1 mm wide)
    - Right arm at X=78 mm from Y=12 to Y=58 mm
    - Bottom arm at Y=12 mm from X=62 to X=78 mm
    - West side OPEN (≥3 mm bridge connects the IMU island to the main
      board at the west boundary).
  This isolates the 16×46 mm IMU island from board flex stress through
  3 of 4 sides; the west bridge maintains mechanical/electrical continuity
  for the SPI/I2C bus traces from the MCU.

  Tier-2-sim (c) structural FEA at R6 refines kerf width + bridge width.

## What this script does NOT do (R4 territory)

  - Routing (signal + power planes)
  - Copper pours
  - Via stitching
  - Trace impedance tuning

Usage:
    KICAD9_FOOTPRINT_DIR=/usr/share/kicad/footprints python3 generate_board.py
"""

import os
import sys
import pcbnew
from kinet2pcb import kinet2pcb

HERE = os.path.dirname(os.path.abspath(__file__))
NETLIST = os.path.abspath(os.path.join(HERE, "..", "novapcb", "novapcb.net"))
OUT_PCB = os.path.join(HERE, "novapcb-layout-v1.1.kicad_pcb")

BOARD_W_MM = 90.0
BOARD_H_MM = 70.0
COPPER_LAYERS = 6
HOLE_INSET = 3.0
MOUNT_REFS = ["H1", "H2", "H3", "H4"]
MOTOR_CONN_REFS = [f"J{i}" for i in range(11, 19)]
NOVAPCB_LIB = os.path.join(HERE, "lib", "novapcb.pretty")
KICAD_QFN_LIB = "/usr/share/kicad/footprints/Package_DFN_QFN.pretty"


def _mm(x_mm):
    return int(x_mm * 1_000_000)


# ============================================================
# Step 1 — netlist → board (placeholder positions)
# ============================================================
print(f"[1/8] kinet2pcb {os.path.basename(NETLIST)} -> board", flush=True)
assert os.path.exists(NETLIST), f"Netlist not found: {NETLIST}"
if os.path.exists(OUT_PCB):
    os.remove(OUT_PCB)
kinet2pcb(NETLIST, OUT_PCB)
brd = pcbnew.LoadBoard(OUT_PCB)
brd.SetCopperLayerCount(COPPER_LAYERS)
print(f"      footprints loaded: {len(list(brd.GetFootprints()))}", flush=True)


# ============================================================
# Step 2 — board outline (90 × 70 mm rectangle)
# ============================================================
print(f"[2/8] outline = closed {BOARD_W_MM}×{BOARD_H_MM} mm rectangle", flush=True)
out = pcbnew.PCB_SHAPE(brd)
out.SetShape(pcbnew.SHAPE_T_RECT)
out.SetLayer(pcbnew.Edge_Cuts)
out.SetStart(pcbnew.VECTOR2I(_mm(0), _mm(0)))
out.SetEnd(pcbnew.VECTOR2I(_mm(BOARD_W_MM), _mm(BOARD_H_MM)))
out.SetWidth(int(0.15e6))
out.SetFilled(False)
brd.Add(out)


# ============================================================
# Step 3 — IMU stress-relief slot (first-cut, FEA-refined at R6)
# ============================================================
# U-shape kerf isolating the IMU island (X=60..80, Y=12..58 mm) on 3 sides;
# west side stays bridged for SPI/I2C bus traces from the MCU.
print(f"[3/8] IMU stress-relief slot (U-shape kerf, 0.8 mm width)", flush=True)

def add_slot(brd, x1, y1, x2, y2, width_mm=0.8):
    """Add a slot in Edge.Cuts (router will route this as a cutout)."""
    seg = pcbnew.PCB_SHAPE(brd)
    seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
    seg.SetLayer(pcbnew.Edge_Cuts)
    seg.SetStart(pcbnew.VECTOR2I(_mm(x1), _mm(y1)))
    seg.SetEnd(pcbnew.VECTOR2I(_mm(x2), _mm(y2)))
    seg.SetWidth(_mm(width_mm))
    brd.Add(seg)

# Kerf at X=78 mm (east boundary of IMU island, slot inside the island)
# from Y=12 to Y=58.
add_slot(brd, 78.0, 12.0, 78.0, 58.0)
# Top kerf at Y=58 mm from X=62 to X=78 mm.
add_slot(brd, 62.0, 58.0, 78.0, 58.0)
# Bottom kerf at Y=12 mm from X=62 to X=78 mm.
add_slot(brd, 62.0, 12.0, 78.0, 12.0)
# West side (X=62 mm) intentionally OPEN — leaves a >=3 mm bridge between
# the IMU island and the MCU zone for SPI/I2C bus traces.
# Bridge width = 62-22 = 40 mm wide tie at the west; but the actual
# narrow neck is at the kerf level — keep wide for now.


# ============================================================
# Step 4 — 4× M3 mounting holes at corners with HOLE_INSET edge margin
# ============================================================
HOLE_POSITIONS = [
    (HOLE_INSET,                HOLE_INSET),                # H1: SW
    (BOARD_W_MM - HOLE_INSET,   HOLE_INSET),                # H2: SE
    (HOLE_INSET,                BOARD_H_MM - HOLE_INSET),   # H3: NW
    (BOARD_W_MM - HOLE_INSET,   BOARD_H_MM - HOLE_INSET),   # H4: NE
]
H_PAD_SIZE_MM = 5.0
print(f"[4/8] 4× M3 corners at inset {HOLE_INSET} mm (c-to-c {BOARD_W_MM - 2*HOLE_INSET} × {BOARD_H_MM - 2*HOLE_INSET} mm)", flush=True)
for fp in brd.GetFootprints():
    ref = fp.GetReference()
    if ref in MOUNT_REFS:
        x_mm, y_mm = HOLE_POSITIONS[MOUNT_REFS.index(ref)]
        fp.SetPosition(pcbnew.VECTOR2I(_mm(x_mm), _mm(y_mm)))
        for pad in fp.Pads():
            pad.SetSize(pcbnew.VECTOR2I(_mm(H_PAD_SIZE_MM), _mm(H_PAD_SIZE_MM)))


# ============================================================
# Step 5 — custom-footprint swap (carry-forward from v1.0)
# ============================================================
print(f"[5/8] custom-fp swap: J11-J18 ESC pads + J10 CRSF pads + U3 IMU", flush=True)
swapped = 0
for fp in list(brd.GetFootprints()):
    ref = fp.GetReference()
    custom_lib = None; custom_name = None
    if ref == "J10":
        custom_lib, custom_name = NOVAPCB_LIB, "CRSF_solder_pad"
    elif ref in MOTOR_CONN_REFS:
        custom_lib, custom_name = NOVAPCB_LIB, "ESC_solder_pad"
    elif ref == "U3":
        custom_lib, custom_name = NOVAPCB_LIB, "ICM-42688-P_LGA-14_2.5x3mm_P0.5mm"
    if custom_lib is None: continue
    new_fp = pcbnew.FootprintLoad(custom_lib, custom_name)
    if new_fp is None:
        print(f"      !!! FootprintLoad failed for {custom_name}", flush=True)
        sys.exit(2)
    old_pos = fp.GetPosition()
    net_map = {pad.GetNumber(): pad.GetNet() for pad in fp.Pads()}
    new_fp.SetReference(ref)
    new_fp.SetPosition(old_pos)
    for pad in new_fp.Pads():
        n = net_map.get(pad.GetNumber())
        if n is not None: pad.SetNet(n)
    brd.Remove(fp)
    brd.Add(new_fp)
    swapped += 1

# U6 eFuse manual add (kinet2pcb can't resolve TPS25940A's KiCad-stock footprint name)
import re
netfile = open(NETLIST).read()
u6_net_map = {}
for net_match in re.finditer(r'\(net\s+\(code (\d+)\)\s+\(name "([^"]*)"\)', netfile):
    block_start = net_match.end()
    depth = 1; i = block_start
    while i < len(netfile) and depth > 0:
        if netfile[i] == '(': depth += 1
        elif netfile[i] == ')': depth -= 1
        i += 1
    block = netfile[block_start:i]
    for node in re.finditer(r'\(ref "U6"\)\s+\(pin "(\d+)"\)', block):
        u6_net_map[node.group(1)] = net_match.group(2)
u6_fp = None
for fp in brd.GetFootprints():
    if fp.GetReference() == "U6":
        u6_fp = fp; break
if u6_fp is None:
    new_u6 = pcbnew.FootprintLoad(KICAD_QFN_LIB, "QFN-20-1EP_3x4mm_P0.5mm_EP1.65x2.65mm")
    if new_u6 is None:
        print(f"      !!! FootprintLoad failed for QFN-20 (U6)", flush=True)
        sys.exit(2)
    new_u6.SetReference("U6")
    new_u6.SetValue("TPS25940A")
    nl = brd.GetNetsByName().asdict()
    for pad in new_u6.Pads():
        n = u6_net_map.get(pad.GetNumber())
        if n and n in nl: pad.SetNet(nl[n])
    brd.Add(new_u6)
    swapped += 1
print(f"      swapped {swapped} placeholders", flush=True)


# ============================================================
# Step 6 — DRC ruleset (JLCPCB 6-layer)
# ============================================================
print(f"[6/8] DRC ruleset", flush=True)
ds = brd.GetDesignSettings()
ds.m_TrackMinWidth = _mm(0.10)
ds.m_MinClearance = _mm(0.10)
ds.m_ViasMinSize = _mm(0.46)
ds.m_ViasMinAnnularWidth = _mm(0.13)
ds.m_HoleClearance = _mm(0.20)
ds.m_CopperEdgeClearance = _mm(0.30)


# ============================================================
# Step 7 — PLACEMENT per 5-zone strategy
# ============================================================
# Coords: (0,0) bottom-left, +X = long axis (90 mm), +Y = short axis (70 mm).
# 5 zones (see header docstring):
#   POWER    X = 0-22   IMU ISLAND X = 60-80
#   MCU      X = 22-60  CAN+TELEM  X = 80-90
PLACEMENT = {
    # ============ Zone POWER (X = 0 → 22 mm) ============
    # Two power inputs on W edge: J4 = main BEC (south); J19 = 2nd input (north)
    "J4":  ( 4.0, 18.0,   90),   # JST-GH 6P vertical, S of mid
    "J19": ( 4.0, 52.0,   90),   # JST-GH 6P vertical, N of mid (mirror)

    # Reverse-polarity P-FET (Q2) east of J4 — gap from J4 vertical
    "Q2":  (10.5, 22.0,    0),
    "D1":  (15.5, 22.0,    0),

    # Q3 + U11: ideal-diode OR-ing for input A (J4 path)
    "Q3":  (18.0, 25.0,    0),
    "U11": (15.0, 31.0,    0),
    "C73": (18.5, 31.0,    0),
    "C74": (15.0, 33.5,    0),

    # Q4 + U12: ideal-diode OR-ing for input B (J19 path)
    "Q4":  (18.0, 47.0,    0),
    "U12": (15.0, 41.0,    0),
    "C75": (18.5, 41.0,    0),
    "C76": (15.0, 38.5,    0),

    # eFuse U6 (TPS25940A QFN-20) and its support — POST-OR-ing, mid power zone
    "U6":  ( 8.5, 36.0,    0),
    "C7":  (11.5, 38.5,   90),
    "C8":  ( 8.5, 40.5,    0),
    "C9":  ( 5.5, 40.0,    0),
    "R4":  ( 5.5, 38.0,    0),
    "R5":  ( 5.5, 36.0,    0),
    "R7":  ( 5.5, 34.0,    0),
    "R8":  (11.5, 34.0,    0),
    "R9":  (11.5, 36.0,    0),
    "R10": ( 4.0, 39.5,    0),
    "R13": (11.5, 40.5,    0),

    # +5V bulks (post-eFuse), main LDO U2 + caps
    "C31": ( 4.5, 28.5,    0),
    "C32": ( 7.5, 28.5,    0),
    "U2":  ( 4.5, 26.0,    0),
    "C33": ( 7.5, 26.0,    0),
    "C34": (10.5, 28.5,    0),
    "C16": (10.5, 26.0,    0),

    # 2nd power input ADC sense (J19 side) — R43/R44/C81/C82
    "R43": ( 7.5, 56.5,    0),
    "R44": (10.0, 56.5,    0),
    "C81": ( 7.5, 58.5,    0),
    "C82": (10.0, 58.5,    0),

    # 1st power input ADC sense (J4 side) — R41/R42/C61/C62
    "R41": ( 7.5, 13.5,    0),
    "R42": (10.0, 13.5,    0),
    "C61": ( 7.5, 11.5,    0),
    "C62": (10.0, 11.5,    0),

    # ============ Zone MCU (X = 22 → 60 mm) ============
    # U1 STM32H743VITx LQFP-100 centered at (41, 35); body 14×14
    "U1":  (41.0, 35.0,    0),
    "Y1":  (52.0, 35.0,    0),
    "C24": (52.0, 32.0,    0),
    "C25": (52.0, 38.0,    0),

    # MCU 100nF decoupling halo
    "C11": (35.0, 44.5,    0),
    "C12": (38.0, 44.5,    0),
    "C13": (41.0, 44.5,    0),
    "C14": (44.0, 44.5,    0),
    "C15": (47.0, 44.5,    0),
    "C19": (47.0, 25.5,    0),
    "C21": (44.0, 25.5,    0),
    "C23": (41.0, 25.5,    0),
    "C26": (38.0, 25.5,    0),

    # MCU power-pin support
    "C17": (35.0, 25.5,    0),
    "C18": (32.0, 25.5,    0),
    "C20": (30.5, 36.0,    0),
    "C22": (30.5, 33.0,    0),
    "C43": (52.0, 41.5,    0),
    "FB1": (30.5, 39.5,   90),

    # NRST pull-up + BOOT0 pull-down (BOOT0 has no refdes-only placement; R3 is BOOT0)
    "R3":  (30.5, 29.0,    0),
    "R1":  (52.0, 28.5,    0),   # VREF 0R tie
    "R2":  (52.0, 25.5,    0),   # VBAT 0R tie

    # USB-C J1 (N edge mid-mount, mid-zone MCU X) — body ~10mm wide so 3mm clear
    "J1":  (38.0, 60.0,    0),
    "U5":  (33.0, 53.0,    0),
    "R31": (28.0, 51.0,    0),
    "R32": (28.0, 53.0,    0),

    # microSD J2 on B.Cu, centered on MCU
    "J2":  (41.0, 35.0,    0, "B"),
    # SDMMC pullups on B.Cu (R51-R55) — OUTSIDE J2 body keepout
    "R51": (30.0, 33.0,    0, "B"),
    "R52": (30.0, 35.0,    0, "B"),
    "R53": (52.5, 33.0,    0, "B"),
    "R54": (52.5, 35.0,    0, "B"),
    "R55": (30.0, 31.0,    0, "B"),
    "C63": (30.0, 37.0,    0, "B"),

    # SWD J9 on B.Cu, S edge
    "J9":  (41.0, 7.0,    0, "B"),

    # ============ Zone IMU ISLAND (X = 60 → 78 mm, slot-bounded) ============
    # The IMU island is the strip bounded by the U-shape kerf. 3 IMUs
    # stacked vertically (Y axis) for compact placement; 2 baros + LP5907
    # + heater alongside. All on TOP layer except U4 (DPS310 on B.Cu).
    #
    # X=60 is the western kerf opening (board bridge); X=78 is eastern kerf.
    # Y=12..58 = island span. Center of island at (69, 35).

    # 3 IMUs vertically arranged at X=69 (center of island)
    "U3":  (69.0, 25.0,    0),       # IMU1 ICM-42688-P (existing, SPI1)
    "U8":  (69.0, 35.0,    0),       # IMU2 BMI088 (SPI2, dual-die LGA-16)
    "U9":  (69.0, 45.0,    0),       # IMU3 LSM6DSV16X (SPI3)

    # IMU decoupling caps clustered around each IMU
    # IMU1 (U3) caps (carry-forward from v1.0)
    "C41": (65.5, 24.5,    0),
    "C42": (65.5, 25.5,    0),
    # IMU2 (U8) caps
    "C91": (72.5, 33.5,    0),
    "C92": (72.5, 35.0,    0),
    "C93": (72.5, 36.5,    0),
    # IMU3 (U9) caps
    "C94": (72.5, 43.5,    0),
    "C95": (72.5, 45.0,    0),
    "C96": (72.5, 46.5,    0),

    # 2 baros + ferrite + LP5907 clean rail at island edges
    # Baro1 DPS310 (U4) on B.Cu (carry-forward from v1.0)
    "U4":  (65.0, 30.0,    0, "B"),
    "C51": (62.5, 30.0,    0, "B"),
    "C52": (62.5, 31.5,    0, "B"),
    # Baro2 LPS22HB (U7) on TOP (different bus = visual separation)
    "U7":  (75.0, 30.0,    0),
    "C71": (75.0, 32.5,    0),
    "C72": (75.0, 27.5,    0),

    # LP5907 IMU clean LDO + ferrite (north of IMU3)
    "FB2": (65.5, 52.0,   90),
    "U13": (69.0, 52.0,    0),
    "C77": (72.5, 50.5,    0),
    "C78": (72.5, 52.0,    0),

    # IMU heater FET (Q5) + heater resistor (R61) — south of IMU1
    "Q5":  (65.5, 18.0,    0),
    "R61": (69.0, 18.0,    0),

    # ============ Zone CAN + TELEM (X = 78 → 90 mm east; long edges) ============
    # J20 CAN connector on E edge (vertical-rotated body); cluster N-S
    "J20": (87.0, 50.0,  -90),
    "U14": (84.5, 35.0,    0),       # TJA1051 transceiver
    "C83": (88.0, 35.0,    0),       # VCC bypass
    "C84": (84.5, 39.0,    0),       # VIO bypass
    "U15": (84.5, 42.5,    0),       # PESD2CAN ESD
    "R45": (88.0, 42.5,    0),       # 120Ω termination
    "R46": (88.0, 45.5,    0),       # 0Ω jumper

    # N-edge connectors: J3 telem, J5 GPS+mag, J10 CRSF (spread along long edge)
    "J3":  (28.0, 66.5,    0),       # Telem JST-GH 6P
    "J5":  (50.0, 66.5,    0),       # GPS+mag JST-GH 10P
    "J10": (66.0, 66.5,    0),       # CRSF solder pads (long-form custom fp)

    # ESD diodes south of each connector — 3mm clearance from connector body
    "D11": (24.0, 63.0,   90),       # telem TX
    "D12": (26.0, 63.0,   90),       # telem RX
    "D5":  (43.5, 63.0,   90),       # GPS TX
    "D6":  (45.5, 63.0,   90),       # GPS RX
    "D7":  (47.5, 63.0,   90),       # I2C SCL
    "D8":  (49.5, 63.0,   90),       # I2C SDA
    "D9":  (53.0, 63.0,   90),       # BUZZER
    "D13": (62.5, 63.0,   90),       # CRSF TX
    "D14": (64.0, 63.0,   90),       # CRSF RX

    # GPS I2C pullups on the GPS bus (further south than D7/D8)
    "R21": (47.5, 60.5,    0),
    "R22": (49.5, 60.5,    0),

    # Baro1 (DPS310) I2C2 pullups (carry-forward from v1.0)
    "R11": (75.0, 24.0,    0),
    "R12": (75.0, 22.0,    0),

    # ============ ESC pads on S edge (X = 28-78, Y = 3) ============
    "J11": (30.0, 3.0,    0),
    "J12": (35.0, 3.0,    0),
    "J13": (40.0, 3.0,    0),
    "J14": (45.0, 3.0,    0),
    "J15": (50.0, 3.0,    0),
    "J16": (55.0, 3.0,    0),
    "J17": (60.0, 3.0,    0),
    "J18": (65.0, 3.0,    0),
}


# Apply placement
print(f"[7/8] placing {len(PLACEMENT)} components", flush=True)
placed = 0
unmoved = []
for fp in list(brd.GetFootprints()):
    ref = fp.GetReference()
    if ref in MOUNT_REFS: continue
    if ref in PLACEMENT:
        spec = PLACEMENT[ref]
        x_mm, y_mm, rot = spec[0], spec[1], spec[2]
        layer = spec[3] if len(spec) > 3 else "F"
        fp.SetPosition(pcbnew.VECTOR2I(_mm(x_mm), _mm(y_mm)))
        fp.SetOrientationDegrees(rot)
        if layer == "B":
            fp.Flip(fp.GetPosition(), False)
        placed += 1
    else:
        unmoved.append(ref)

print(f"      placed: {placed}/{len(PLACEMENT)}", flush=True)
if unmoved:
    print(f"      unmoved (no placement spec): {len(unmoved)} - {unmoved[:10]}", flush=True)


# ============================================================
# Step 8 — save
# ============================================================
print(f"[8/8] save {os.path.basename(OUT_PCB)}", flush=True)
pcbnew.SaveBoard(OUT_PCB, brd)

print("done.", flush=True)
