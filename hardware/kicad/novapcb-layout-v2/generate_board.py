#!/usr/bin/env python3
"""
novapcb pivot Step 3 P1 — placement execution (6-layer, rectangular).

Generates `novapcb-layout-v2.kicad_pcb` with all 83 components POSITIONED on
a 52×38mm 6-layer board per the approved PLACEMENT_STRATEGY (4-zone layout,
generous spacing, dimension freedom). Supersedes the dense 36×36 / 4-layer
`novapcb-layout/` which was set aside in the 2026-05-20 sim-driven re-design
pivot.

NO planes (deferred to Step 5 routing PR per pivot plan). NO routing
(Step 5). NO copper pours (Step 5).

## Inputs

  - Netlist:        hardware/kicad/novapcb/novapcb.net (Step 2 final, 83 comps)
  - Footprint libs: KICAD9_FOOTPRINT_DIR + ./lib/novapcb.pretty
  - Strategy:       docs/PLACEMENT_STRATEGY.md (zoning + sizing)
  - Layer count:    DECISIONS §8 — 6-layer (master adjudicated PR #57)
  - Mounting:       4 × M3 corners, ≥ 3 mm edge inset

## 6-layer stackup (per PLACEMENT_STRATEGY §3.5)

  L1 (top, F.Cu): components + signal
  L2 (In1.Cu):    GND plane
  L3 (In2.Cu):    +3V3 power plane
  L4 (In3.Cu):    +5V power plane (LDO thermal-pad fan-out target)
  L5 (In4.Cu):    GND plane
  L6 (bottom, B.Cu): signal + bottom-side sensors (U4 DPS310, J2 microSD)

## Board outline + envelope

  Rectangle 52 × 38 mm (centred in the 50-55 × 35-40 mm envelope target).
  Aspect ratio 52/38 = 1.37 (within 1.3-1.6 target).
  Area 1976 mm² (within 1750-2200 mm² target).
  Origin (0,0) = bottom-left corner.

## 4-zone layout

  Zone 1 (X = 0 → 15 mm):  POWER — Mauch J4 → Q2 → D1 → U6 eFuse → +5V bulks
                              → AP2112K U2 LDO → +3V3 bulks. Heat + transient.
  Zone 2 (X = 15 → 37 mm): MCU CENTRE — U1 LQFP-100 at (26, 19) + Y1 crystal
                              + decoupling halo + USB-C J1 + USBLC6 U5 +
                              microSD J2 (B.Cu) + SWD J9 (B.Cu).
  Zone 3 (X = 37 → 52 mm): SENSORS — ICM-42688-P U3 (TOP, vibration-iso
                              region) + DPS310 U4 (B.Cu) + ADC LPFs. FAR
                              from Zone 1 heat.
  Zone 4 (long edges):     CONNECTORS — JST-GH (J3 telem + J5 GPS+mag)
                              along one long edge; ESC pads (J11-J18) along
                              the opposite long edge.

## What this script does NOT do (Step 5 territory)

  - Power-plane pours (3V3 / 5V / GND)
  - Trace routing (signal + power)
  - LDO thermal-pour copper area (Step 5 places it on L4 +5V plane;
    Step 4 sim-iterates the area)
  - Final via-stack patterns
  - Edge cuts beyond the simple rectangle

This is the FIRST strategy-driven placement (master 2026-05-21 directive).
Step 4 sim-validates + iterates via the place→sim→adjust loop.

Usage:
    KICAD9_FOOTPRINT_DIR=/usr/share/kicad/footprints python3 generate_board.py

Outputs:
    novapcb-layout-v2.kicad_pcb  — the board scaffolding (committed)
    novapcb-layout-v2.kicad_pro  — companion project file (separate)
"""

import os
import sys
import pcbnew
from kinet2pcb import kinet2pcb

HERE = os.path.dirname(os.path.abspath(__file__))
NETLIST = os.path.abspath(os.path.join(HERE, "..", "novapcb", "novapcb.net"))
OUT_PCB = os.path.join(HERE, "novapcb-layout-v2.kicad_pcb")

# ---------- board spec (Step 3+4-rev — Sai Path B: grow for thermal) ----------
# Iteration history:
#   55×40 (P1-iter1): 20 zone-boundary violations, untenable
#   62×42 (P1-rev, PR #58 merged): 0 placement violations, 14 U3-footprint-internal
#                                    → Step 4 FEA: LDO Tj=92°C FAIL at h=5/50°C
#   85×62 (THIS, P1-rev2, post-Sai-Path-B):
#     Master 2026-05-21: Sai adjudicated Path B — grow the board, design for
#     h=5 dead-still-air worst case. Target LDO+MCU Tj ≤ 80°C.
#
#     Sizing math from Step 4 baseline:
#       62×42=2604mm² gave ΔT_max=45.2°C at P=1.33W, h=5 → T_max=95.2°C.
#       For T_max ≤ 80°C (ΔT_max ≤ 30°C): A_new/A_old = 45.2/30 = 1.51×
#       → A_new ≥ 3935 mm². With ~5°C T_max-T_avg buffer for hot spot,
#       conservative target A ≥ 5300 mm².
#     85×62 = 5270 mm² (right at conservative analytical floor — first try,
#     FEA-verify, grow if needed).
#     Aspect 1.37 (in 1.3-1.6 strategy band).
BOARD_W_MM = 80.0   # long axis (X)  — was 62 → +37%
BOARD_H_MM = 60.0   # short axis (Y) — was 42 → +48%
COPPER_LAYERS = 6
HOLE_INSET = 3.0    # mm from each edge to mounting-hole centre
MOUNT_REFS = ["H1", "H2", "H3", "H4"]
MOTOR_CONN_REFS = [f"J{i}" for i in range(11, 19)]
NOVAPCB_LIB = os.path.join(HERE, "lib", "novapcb.pretty")


def _mm(x_mm):
    """mm → nm (KiCad internal unit)."""
    return int(x_mm * 1_000_000)


# ============================================================
# Step 1 — kinet2pcb netlist → board with placeholder positions
# ============================================================
print(f"[1/7] kinet2pcb {os.path.basename(NETLIST)} -> board", flush=True)
assert os.path.exists(NETLIST), f"Netlist not found: {NETLIST}"
if os.path.exists(OUT_PCB):
    os.remove(OUT_PCB)
kinet2pcb(NETLIST, OUT_PCB)
brd = pcbnew.LoadBoard(OUT_PCB)
brd.SetCopperLayerCount(COPPER_LAYERS)
print(f"      footprints loaded: {len(list(brd.GetFootprints()))}", flush=True)
print(f"      copper layer count: {brd.GetCopperLayerCount()}", flush=True)


# ============================================================
# Step 2 — board outline (single closed rectangle on Edge.Cuts)
# ============================================================
print(f"[2/7] outline = closed {BOARD_W_MM}×{BOARD_H_MM} mm rectangle", flush=True)
out = pcbnew.PCB_SHAPE(brd)
out.SetShape(pcbnew.SHAPE_T_RECT)
out.SetLayer(pcbnew.Edge_Cuts)
out.SetStart(pcbnew.VECTOR2I(_mm(0), _mm(0)))
out.SetEnd(pcbnew.VECTOR2I(_mm(BOARD_W_MM), _mm(BOARD_H_MM)))
out.SetWidth(int(0.15e6))
out.SetFilled(False)
brd.Add(out)


# ============================================================
# Step 3 — 4× M3 mounting holes at corners with HOLE_INSET edge margin
# ============================================================
HOLE_POSITIONS = [
    (HOLE_INSET,                HOLE_INSET),                # H1: SW
    (BOARD_W_MM - HOLE_INSET,   HOLE_INSET),                # H2: SE
    (HOLE_INSET,                BOARD_H_MM - HOLE_INSET),   # H3: NW
    (BOARD_W_MM - HOLE_INSET,   BOARD_H_MM - HOLE_INSET),   # H4: NE
]
H_PAD_SIZE_MM = 5.0  # GND-tied annular pad around 3.2 mm M3 drill
print(f"[3/7] 4× M3 corners at inset {HOLE_INSET} mm (c-to-c {BOARD_W_MM - 2*HOLE_INSET} × {BOARD_H_MM - 2*HOLE_INSET} mm)", flush=True)
for fp in brd.GetFootprints():
    ref = fp.GetReference()
    if ref in MOUNT_REFS:
        x_mm, y_mm = HOLE_POSITIONS[MOUNT_REFS.index(ref)]
        fp.SetPosition(pcbnew.VECTOR2I(_mm(x_mm), _mm(y_mm)))
        for pad in fp.Pads():
            pad.SetSize(pcbnew.VECTOR2I(_mm(H_PAD_SIZE_MM), _mm(H_PAD_SIZE_MM)))
        print(f"      {ref}: ({x_mm:5.2f}, {y_mm:5.2f}) pad={H_PAD_SIZE_MM}mm", flush=True)


# ============================================================
# Step 4 — swap placeholder footprints (custom solder pads)
# ============================================================
print(f"[4/7] custom-fp swap: J11-J18 ESC pads + J10 CRSF pads + U6 eFuse QFN + U3 IMU", flush=True)
# The TPS25940A WQFN-20 4×3 mm symbol-side footprint name doesn't match any
# in the KiCad 9 stock library; the equivalent KiCad-stock footprint is
# `Package_DFN_QFN:QFN-20-1EP_3x4mm_P0.5mm_EP1.65x2.65mm` (same body just
# named 3×4 rather than 4×3; orientation choice).
KICAD_QFN_LIB = "/usr/share/kicad/footprints/Package_DFN_QFN.pretty"
# U3 ICM-42688-P: KiCad-stock LGA-14_3x2.5mm uses STMicro LSM6DS3TR-C-derived
# pads (0.625×0.35 mm) that violate our 0.2 mm netclass clearance with 0.15 mm
# pad-edge gap. Replace with in-repo `novapcb_lib:ICM-42688-P_LGA-14_2.5x3mm_P0.5mm`
# (pads 0.975×0.25 mm, 0.25 mm pad-edge gap — passes DRC). See OPEN_QUESTIONS
# phase4a-1 for the footprint-resolution research history.
swapped = 0
for fp in list(brd.GetFootprints()):
    ref = fp.GetReference()
    custom_lib = None
    custom_name = None
    if ref == "J10":
        custom_lib, custom_name = NOVAPCB_LIB, "CRSF_solder_pad"
    elif ref in MOTOR_CONN_REFS:
        custom_lib, custom_name = NOVAPCB_LIB, "ESC_solder_pad"
    elif ref == "U3":
        custom_lib, custom_name = NOVAPCB_LIB, "ICM-42688-P_LGA-14_2.5x3mm_P0.5mm"
    if custom_lib is None:
        continue
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
        if n is not None:
            pad.SetNet(n)
    brd.Remove(fp)
    brd.Add(new_fp)
    swapped += 1

# U6 (TPS25940A) — kinet2pcb couldn't find its footprint name in any lib
# (BOM names it WQFN-20-1EP_4x3mm; KiCad stock library names it
# QFN-20-1EP_3x4mm). Load + add explicitly with the right footprint, then
# wire up nets by pad number from the netlist.
# Find U6's net assignments from the netlist (parsed via reading the file).
import re
netfile = open(NETLIST).read()
# Find the (comp (ref "U6") ... block + the pad-net assignments
u6_net_map = {}
# Scan all (net ... (code N) (name "X") ...) blocks for nodes with ref="U6".
# Netlist format uses multi-line indented blocks; allow whitespace between tokens.
for net_match in re.finditer(r'\(net\s+\(code (\d+)\)\s+\(name "([^"]*)"\)', netfile):
    block_start = net_match.end()
    # find matching closing paren
    depth = 1
    i = block_start
    while i < len(netfile) and depth > 0:
        if netfile[i] == '(':
            depth += 1
        elif netfile[i] == ')':
            depth -= 1
        i += 1
    block = netfile[block_start:i]
    # find nodes with ref="U6" — multi-line format (whitespace between
    # tokens includes newlines + indentation).
    for node in re.finditer(r'\(ref "U6"\)\s+\(pin "(\d+)"\)', block):
        pin_num = node.group(1)
        u6_net_map[pin_num] = net_match.group(2)  # net name

# Find or add U6 footprint
u6_fp = None
for fp in brd.GetFootprints():
    if fp.GetReference() == "U6":
        u6_fp = fp
        break
if u6_fp is None:
    new_u6 = pcbnew.FootprintLoad(KICAD_QFN_LIB, "QFN-20-1EP_3x4mm_P0.5mm_EP1.65x2.65mm")
    if new_u6 is None:
        print(f"      !!! FootprintLoad failed for QFN-20 (U6)", flush=True)
        sys.exit(2)
    new_u6.SetReference("U6")
    new_u6.SetValue("TPS25940A")
    # Set nets per netlist (NETNAMES_MAP uses has_key/find API)
    nl = brd.GetNetsByName()
    nets_dict = nl.asdict()
    for pad in new_u6.Pads():
        n = u6_net_map.get(pad.GetNumber())
        if n and n in nets_dict:
            pad.SetNet(nets_dict[n])
    brd.Add(new_u6)
    swapped += 1
    print(f"      added U6 (QFN-20 3x4mm, {len(u6_net_map)} pads wired)", flush=True)

print(f"      swapped {swapped} placeholders", flush=True)


# ============================================================
# Step 5 — DRC ruleset (JLCPCB 6-layer capability)
# ============================================================
print(f"[5/7] DRC ruleset (JLCPCB 6-layer)", flush=True)
ds = brd.GetDesignSettings()
ds.m_TrackMinWidth = _mm(0.10)
ds.m_MinClearance = _mm(0.10)
ds.m_ViasMinSize = _mm(0.40)
ds.m_ViasMinAnnularWidth = _mm(0.05)
ds.m_HoleClearance = _mm(0.20)
ds.m_CopperEdgeClearance = _mm(0.30)


# ============================================================
# Step 6 — PLACEMENT per 4-zone strategy (refdes → (x, y, rotation_deg))
# ============================================================
# Coordinate system: (0,0) bottom-left, +X = long axis (52mm), +Y = short axis (38mm).
# Mounting holes at the 4 corners with a 3mm radius keep-out implicit.
#
# Zone 1 POWER  : X = 1 → 14   (Mauch, Q2, D1, U6 eFuse + support, U2 LDO + caps)
# Zone 2 MCU    : X = 15 → 37  (U1 LQFP-100 centered + decoupling halo + USB + microSD)
# Zone 3 SENSORS: X = 38 → 51  (IMU U3 TOP, DPS310 U4 BOTTOM, ADC LPFs)
# Zone 4 LONG-EDGE CONNECTORS: spanning X (telem/GPS on one Y-edge; ESC pads on the other)
#
# B.Cu (bottom-layer) components flagged with layer="B" — flipped after position.

# Board grown to 85×62 → MCU re-centred at (42, 31):
# MCU pad-outer bounding box on a 14×14mm LQFP-100 body at (42, 31):
#   pads extend ~0.85mm past body edge → effective extent X=34.15..49.85,
#   Y=23.15..38.85. Decoupling caps placed ≥ 1.5 mm clear of these edges.
# Zone widths: Zone 1 X=0..20 (POWER), Zone 2 X=20..62 (MCU), Zone 3 X=62..85 (SENSORS).

PLACEMENT = {
    # ============ Zone 1 — POWER FRONT-END (X = 1 → 20 mm) ============
    # Mauch J4 on the WEST short edge. Vertical orientation, cable exits W.
    "J4":  ( 3.5, 18.0,   90),   # JST-GH 6P vertical (cable exits W edge)

    # Reverse-polarity P-FET Q2 east of J4.
    "Q2":  (10.35, 13.55,    0),

    # TVS D1: between Q2 drain and U6 IN.
    "D1":  (16.5, 13.55,    0),

    # eFuse U6 (TPS25940A, QFN-20 3×4 mm). Centred in Zone 1 with generous
    # cluster spacing on the 20 mm-wide Zone 1.
    "U6":  (12.24, 21.29,    0),

    # eFuse configuration network — spread across Zone 1.
    "C7":  (16.00, 21.29,   90),   # dVdT 100nF (E of U6)
    "C8":  (12.24, 25.65,    0),   # IN bypass 100nF (N of U6)
    "C9":  (14.59, 18.39,    0),   # OUT bypass 1µF (SE of U6, clear of R8)
    "R4":  ( 7.0, 26.5,    0),   # ILIM 42.2k (NW of U6)
    "R5":  (17.41, 23.23,    0),   # FLT pullup 10k (E of U6)
    "R7":  (17.41, 17.42,    0),   # UVLO upper 30.1k
    "R8":  (17.41, 19.35,    0),   # UVLO lower 10k
    "R9":  (15.06, 16.45,    0),   # OVP upper 51k (SE of U6)
    "R10": (12.24, 16.45,    0),   # OVP lower 10k (S of U6)
    "R13": (17.41, 25.16,    0),   # PGOOD pullup 10k (NE of U6)

    # +5V bulks (post-eFuse, feeding LDO).
    "C31": (9.41, 28.06,    0),   # 1µF LDO IN bypass
    "C32": (13.18, 28.06,    0),   # 4.7µF LDO IN bulk (0805)

    # AP2112K LDO U2 + heat-spreading reservation. Plenty of room in Zone 1
    # for L4 +5V thermal pour (≥ 100 mm²) extending around U2.
    "U2":  (9.41, 32.42,    0),   # SOT-25; thermal-pad fan-out into L4 plane

    # LDO output caps.
    "C33": (13.18, 32.42,    0),   # 1µF LDO OUT
    "C34": ( 7.0, 38.0,    0),   # 4.7µF +3V3 bulk (0805)
    "C16": (14.12, 36.77,    0),   # 4.7µF +3V3 bulk near Zone 2

    # ============ Zone 2 — MCU + USB + SDMMC (X = 20 → 62 mm; grown big) ============
    # U1 STM32H743 LQFP-100 — Zone 2 centre at (42, 31). Body 14×14 →
    # X=35..49, Y=24..38; pad outer X=34.15..49.85, Y=23.15..38.85.
    "U1":  (39.53, 30.00,    0),

    # Y1 8 MHz crystal east of MCU.
    "Y1":  (50.82, 30.00,    0),
    "C24": (50.82, 27.10,    0),   # 18pF load cap (S of Y1)
    "C25": (50.82, 32.90,    0),   # 18pF load cap (N of Y1)

    # MCU 100nF decoupling halo — placed ≥ 1.5 mm clear of MCU pad-outer.
    # N halo Y ≥ 40.5; S halo Y ≤ 21.5; W halo X ≤ 32.5; E halo X ≥ 51.5.
    "C11": (33.88, 39.19,    0),  # N halo
    "C12": (36.71, 39.19,    0),  # N halo
    "C13": (39.53, 39.19,    0),  # N halo
    "C14": (42.35, 39.19,    0),  # N halo
    "C15": (45.18, 39.19,    0),  # N halo (E corner)
    "C19": (45.18, 20.81,    0),  # S halo (E corner)
    "C21": (42.35, 20.81,    0),  # S halo
    "C23": (39.53, 20.81,    0),  # S halo
    "C26": (36.71, 20.81,    0),  # S halo

    # MCU power-pin support.
    "C17": (33.88, 20.81,    0),  # 2.2µF VCAP1 (S halo W)
    "C18": (31.06, 20.81,    0),  # 2.2µF VCAP2 (S halo W far)
    "C20": (29.65, 31.94,    0),  # 1µF MCU VDD bulk (W halo, ≥ 1.5mm clear of MCU pad X=34.15)
    "C22": (29.65, 28.06,    0),  # 1µF MCU VDD bulk (W halo)
    "C43": (50.82, 35.81,    0),  # 2.2µF VREF+ (E halo, N of crystal)
    "FB1": (29.65, 30.00,   90),  # 600Ω ferrite +3V3→VDDA filter (W halo mid)

    # MCU reset support.
    "R3":  (29.65, 24.68,    0),  # NRST pullup 10k (W halo S)

    # USB-C J1 mid-mount on N edge — extra room for clean placement.
    # Centred at X=45 → body X=40.5..49.5; H4 at (82, 59) pad starts X=79.5
    # → 30mm gap. MCU N pad outer X=49.85 → 0.35mm gap to J1 W edge (J1 Y
    # starts at Y=54.25 vs MCU N pad outer Y=38.85 → 15mm vertical clear).
    "J1":  (45.0, 56.13,    0),  # USB-C mid-mount; body Y=54.25..61.75. E body X=49.5 clears H4 pad X_W=74.5

    # USBLC6 U5 + CC pull-downs between J1 and MCU.
    "U5":  (48.94, 48.39,    0),  # SOT-23-6; clear of J1 S body + MCU N pads
    "R31": (52.0, 51.5,    0),  # USB-C CC1 pulldown 5.1k (E of J1 body X_E=49.5)
    "R32": (52.0, 53.5,    0),  # USB-C CC2 pulldown 5.1k

    # microSD J2 (B.Cu) — DM3AT body ~14×15mm. Centred on MCU centre.
    "J2":  (39.53, 30.00,    0, "B"),

    # SDMMC bus pull-ups + reset on B.Cu — OUTSIDE J2 body keepout
    # (DM3AT at (42,31) body X=35..49, Y=23.5..38.5). Cluster on either side.
    "R51": (30.59, 26.13,    0, "B"),  # W of J2
    "R52": (30.59, 28.06,    0, "B"),  # W of J2
    "R53": (48.47, 26.13,    0, "B"),  # E of J2
    "R54": (48.47, 28.06,    0, "B"),  # E of J2
    "R55": (30.59, 24.19,    0, "B"),  # SW of J2

    # SWD J9 (B.Cu, S edge for pogo-pin jig access).
    "J9":  (40.0, 11.0,    0, "B"),  # 2x5 1.27mm

    # ============ Zone 3 — SENSORS / ANALOG (X = 62 → 85 mm) ============
    # ICM-42688-P IMU U3 on TOP, centre of Zone 3.
    "U3":  (69.65, 30.00,    0),

    # IMU decoupling.
    "C41": (66.35, 30.00,    0),  # 100nF VDDIO (W of U3)
    "C42": (66.35, 32.90,    0),  # 100nF VDD

    # DPS310 baro on B.Cu. Bosch_LGA-8 ~2×2.5mm body; courtyard ~3×3mm.
    "U4":  (69.65, 40.65,    0, "B"),
    "C51": (66.35, 40.65,    0, "B"),  # 100nF W of U4
    "C52": (72.94, 40.65,    0, "B"),  # 100nF E of U4

    # I²C pullups for the on-board I2C2 baro bus.
    "R11": (73.88, 27.10,    0),
    "R12": (73.88, 29.03,    0),

    # GPS+mag external I²C1 pullups (near J5 — pulled S to clear J5 body).
    "R21": (18.82, 49.35,    0),
    "R22": (20.71, 49.35,    0),

    # ADC input network for VBAT/current sense (signal from Mauch via J4).
    "R41": (60.24, 21.29,    0),  # VBAT divider top
    "R42": (62.12, 21.29,    0),  # current sense
    "C61": (60.24, 23.23,    0),  # VBAT LPF
    "C62": (62.12, 23.23,    0),  # current LPF
    "C63": (64.00, 21.29,    0),  # ADC bypass

    # R1/R2 0R jumpers.
    "R1":  (65.88, 21.29,    0),
    "R2":  (67.76, 21.29,    0),

    # ============ Zone 4 — Connectors on long edges ============
    # N long edge: J3 + J5 + J1 with H3 (3, 59) and H4 (82, 59) mounting
    # corners. Total usable N edge X = 5.5..79.5 = 74 mm. Plenty of room.
    "J3":  (14.0, 57.0,    0),  # JST-GH 6P telem (W edge X=9.5 clears H3 pad X=5.5)
    "J5":  (30.0, 57.0,    0),  # JST-GH 10P GPS+mag (W X=24, E X=36; clear of J3 E=18.5 + J1 W=37.85)

    # S long edge: 8× ESC pads in a row. H1 (3,3) + H2 (82,3) pad edges at
    # X=5.5 and X=79.5. ESC strip X=10..76 (66mm range), pitch 66/7 = 9.4 mm.
    "J11": (9.41, 2.42,    0),
    "J12": (18.35, 2.42,    0),
    "J13": (27.29, 2.42,    0),
    "J14": (36.24, 2.42,    0),
    "J15": (45.18, 2.42,    0),
    "J16": (54.12, 2.42,    0),
    "J17": (63.06, 2.42,    0),
    "J18": (72.00, 2.42,    0),

    # CRSF solder pads J10 on B.Cu — in Zone 3 SE area (clear of J9 SWD +
    # top-side ESC row).
    "J10": (60.0, 9.0,    0, "B"),  # CRSF pads — further E, clear of J9 SWD at X=40
}


# ============================================================
# Step 7 — Apply placement + B.Cu flip + final accounting
# ============================================================
print(f"[6/7] PLACEMENT — apply per-refdes positions ({len(PLACEMENT)} entries)", flush=True)

placed_refs = set()
unplaced_refs = []
for fp in list(brd.GetFootprints()):
    ref = fp.GetReference()
    if ref in MOUNT_REFS:
        placed_refs.add(ref)
        continue   # mounting holes already placed in Step 3
    spec = PLACEMENT.get(ref)
    if spec is None:
        unplaced_refs.append(ref)
        continue
    if len(spec) == 4:
        x_mm, y_mm, rot_deg, layer = spec
    else:
        x_mm, y_mm, rot_deg = spec
        layer = "F"
    fp.SetPosition(pcbnew.VECTOR2I(_mm(x_mm), _mm(y_mm)))
    # Set rotation (KiCad uses tenths of degrees internally via EDA_ANGLE)
    fp.SetOrientation(pcbnew.EDA_ANGLE(rot_deg * 10, pcbnew.TENTHS_OF_A_DEGREE_T))
    if layer == "B":
        # Flip to bottom layer (KiCad 9 API: Flip(centre, FLIP_DIRECTION))
        fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
    placed_refs.add(ref)

if unplaced_refs:
    print(f"      !!! UNPLACED REFS ({len(unplaced_refs)}): {sorted(unplaced_refs)}", flush=True)
    print(f"      placed: {len(placed_refs)} / {len(list(brd.GetFootprints()))}", flush=True)
    print(f"      adding the unplaced refs to the PLACEMENT dict is required.", flush=True)
    sys.exit(3)


# ============================================================
# Step 8 — save + summary
# ============================================================
print(f"[7/7] save board → {os.path.basename(OUT_PCB)}", flush=True)
brd.Save(OUT_PCB)

# Final summary
fps = list(brd.GetFootprints())
on_top = sum(1 for f in fps if f.GetLayer() == pcbnew.F_Cu)
on_bot = sum(1 for f in fps if f.GetLayer() == pcbnew.B_Cu)
print(f"")
print(f"=" * 64, flush=True)
print(f" novapcb-layout-v2 — Step 3 P1 placement DONE", flush=True)
print(f"=" * 64, flush=True)
print(f"  Board:        {BOARD_W_MM} × {BOARD_H_MM} mm ({BOARD_W_MM*BOARD_H_MM:.0f} mm²)", flush=True)
print(f"  Aspect ratio: {BOARD_W_MM/BOARD_H_MM:.2f}", flush=True)
print(f"  Layers:       {COPPER_LAYERS} copper", flush=True)
print(f"  Mounting:     4× M3 at inset {HOLE_INSET} mm (c-to-c {BOARD_W_MM - 2*HOLE_INSET} × {BOARD_H_MM - 2*HOLE_INSET} mm)", flush=True)
print(f"  Components:   {len(fps)} placed ({on_top} F.Cu + {on_bot} B.Cu)", flush=True)
print(f"  Output:       {OUT_PCB}", flush=True)
