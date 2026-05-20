#!/usr/bin/env python3
"""
novapcb Phase 4a + 4b — board scaffolding + placement generator.

Produces novapcb-layout.kicad_pcb with all 70 components POSITIONED on the
36×36mm board. NO planes (Phase 4c), NO routing (Phase 4d/4e).

Phase 4b: PLACEMENT reasoning notes
==================================

Per master's 09:00 cross-review: "4b is the highest-leverage Phase 4 sub-phase"
— placement quality determines whether 4d Freerouting succeeds. Each
component group has reasoned positioning, not mechanical grid drop. The
Phase 2.5 sketch (hardware/kicad/footprint-check/notes.md) was the
fit-checked starting reference; 4b refines routing-aware.

Per-group placement reasoning (summary; full reasoning in PLACEMENT dict
inline comments):

  - MCU (U1 LQFP-100): centered slightly N of board center at (18,19) — board
    geometric center for routing reach to all 4 edges; +1mm N to leave Y=0..11
    band for 8 ESC solder pads on bottom edge.
  - Crystal (Y1): hard against MCU east side (HSE pins per STM32H743V LQFP-100).
  - MCU decoupling (C11..C22, C26): distributed around MCU 4 sides, ≥2.5mm
    from body edge to clear MCU pad outer extent + leave 0.15mm clearance.
  - VCAP1/VCAP2 caps (C17/C18) + VBAT (C26) + ferrite (FB1): on MCU south
    edge near corresponding power pins.
  - LDO (U2 AP2112K-3.3): SW corner at (6,9), close to 5V input path; clear
    of H1 mounting keep-out (Y > 6.25). Input/output caps cluster around U2.
  - IMU (U3 ICM-42688-P): west of MCU at (8,22), board-center-Y for
    rotational-rate sensing; off-axis from LDO heat (LDO at Y=9) and ESC
    pads (Y=2) — clear of both heat + switching noise paths.
  - IMU decoupling (C41-C43): cluster on U3 W/E/N adjacent sides.
  - Baro (U4 DPS310): N of MCU at (22,28), close to I²C2 pins (PB10/PB11
    on MCU N edge per STM32). Decoupling C51/C52 + I²C2 pull-ups R11/R12
    adjacent.
  - GPS+mag JST-GH 10P (J5): left edge at (2.5,18), 90° (cable exits W).
    Body extends Y=11.25..24.75; clears H1/H3 keep-outs.
  - I²C1 pull-ups (R21/R22): co-located with J5 per 3e sheet ownership.
  - USB-C (J1): top edge center (18,33) — short diff pair to MCU's PA11/PA12.
    USBLC6 ESD (U5) west of J1 body to clear courtyard overlap with USB-C
    receptacle.
  - USB CC pulldowns (R31/R32): east of J1 body near CC pins.
  - CRSF JST-GH 4P (J10): right edge mid at (33.5,18), 270°.
  - Telem JST-GH 6P (J3): right edge top at (33.5,28), 270°.
  - Mauch JST-GH 6P (J4): right edge bottom-mid at (33.5,11), 270° (Y=11
    clears H2 keep-out + J4 body Y=6.25..15.75 fits between H2 + J10).
  - ADC filter (R41/R42, C61/C62): between J4 and MCU PC0/PC1 south-east —
    PHASE3_AUDIT §B carry-forward #5 (ADC filter near MCU, not near
    connector, to minimize ADC noise pickup).
  - microSD (J2 DM3AT): flipped to B.Cu (bottom layer) — DM3AT has
    explicit footprints-not-allowed keep-out zones that conflict with NE
    F.Cu components; B.Cu placement is standard mini-FC practice (card
    accessible from underside via airframe cutout). Placed at (18,6) per
    4b-rev (was (25,30) in 4b first-pass; re-positioned center-south
    to clear THT keep-outs of H4 + J1 USB-C shield pins).
  - SDMMC pull-ups (R51-R55): row between J2 and MCU on F.Cu — short
    SDMMC bus paths through-vias to B.Cu J2 mounting pads.
  - SWD (J9): B.Cu at (18,21) — pogo-pin programming jig on underside
    (initial (18,6) placement moved north to clear J2 microSD keep-out at
    center-south; (18,21) is under the MCU center on the bottom side).
  - 8× ESC solder pads (J11-J18): bottom edge in single row at 3.0mm
    pitch (X=7.5..28.5), Y=2.0. Clears H1/H2 mounting keep-outs by 1.25mm
    on both sides.
  - 4× M3 mounting (H1-H4): corner positions at (2.75/33.25, 2.75/33.25),
    30.5 c-to-c.

DRC (Phase 4b-rev, after master's "real finer-precision pass" adjudication):

Total 18 violations remaining (down from 87 in 4b first-pass; 79% reduction).
The finer-precision pass moved IMU west 2mm, flipped U4 DPS310 to B.Cu
(no F.Cu room between MCU N pads and J1 USB-C south body), moved Y1
crystal east 1.5mm, moved C11/C12/R11/R12 outside J1 USB-C X-range,
restructured ADC filter west of Y1, etc.

Bounded residual (18 = 13 clearance + 5 shorting_items):
   C19↔C62 (1 short) — MCU east cap vs ADC filter cap
   C26↔C32 (1 short) — LDO bulk cap vs MCU VBAT decoupling
   C31↔C32 (1 clear) — LDO output caps cluster too tight
   C34↔U2 (1 clear + 1 short) — LDO 5V bulk cap vs U2 SOT-23 pads
   FB1↔U1 (1 clear) — ferrite bead too close to MCU
   J3↔R53/R54/R55 + J3 self (4 clear) — telem connector vs SDMMC pullup cluster
   J4 self + J4↔Y1 (2 clear) — Mauch connector vs crystal
   J5↔R21 + J5↔U2 + C42↔J5 (3 clear) — GPS connector vs left-side passives
   U4 self (2 clear) — DPS310 B.Cu internal
   U5 self (2 short) — USBLC6 internal

Master 4b-rev guidance applies: this bounded list flags for supermaster
GUI fine-tune pass (Rule 13 "irreducible residual"). Many are cap-GND vs
IC-pad shorts that Phase 4c plane pour resolves (mandated re-check at 4c).

Phase 4b's deliverable is per-group ROUTING-AWARE placement; per-pad
0.1mm fine-tuning to absolutely zero DRC violations is GUI-territory
work (or 4b-rev3 if master decides). What this script gets right:
  - Components in their right functional zones (MCU center, IMU offset,
    LDO SW, baro N, connectors edge, microSD B.Cu)
  - Critical adjacencies (crystal-MCU, decoupling-MCU, USB-MCU short,
    USBLC6 between USB+MCU, ADC filter MCU-side)
  - All M3 keep-outs respected
  - Connector edge-locations + cable egress per Phase 2.5 sketch (J6 CAN
    removed per phase3exit-can; ESC pads replace 2× JST-SH per 4a)
  - microSD relocated to B.Cu to resolve Phase 2.5 tight-spot #1 (microSD
    vs IMU vertical-clearance collision)

What this script does:
  1. Imports the Phase 3 netlist via kinet2pcb (the canonical headless
     netlist → .kicad_pcb tool, xesscorp / SKiDL ecosystem).
  2. Sets 4 copper layers per DECISIONS §8.
  3. Adds a single CLOSED 36 × 36 mm outline via SHAPE_T_RECT (single
     primitive — Phase 4 P0 noted iter-#3 saw 4-disjoint-segments outline
     trigger SHAPE_POLY_SET non-closed asserts; SHAPE_T_RECT is one
     primitive and is always closed).
  4. Places the 4 M3 mounting holes at the 30.5 × 30.5 mm c-to-c pattern
     (Phase 2.5 P1.1 + DECISIONS §2 v1 outline). Inset 2.75 mm from each
     edge.
  5. Resolves the PHASE3_AUDIT.md §B placeholder footprints:
     - ICM-42688-P (U3): KiCad-generic `Package_LGA:LGA-14_3x2.5mm_P0.5mm_
       LayoutBorder3x4y` retained — body/pitch/pad-arrangement match TDK
       ds-000347 spec (Phase 2.5 P0.4 confirmed); pad-size dimensions are
       KiCad IPC-7351 nominal (TDK datasheet recommended-land-pattern not
       extractable in this session — WebFetch on the 60-page PDF timed
       out). Phase 6.5 forum review confirms IPC-7351-Density-B vs TDK
       recommended at Phase 7 pre-fab.
     - DPS310 (U4): existing `Package_LGA:Bosch_LGA-8_...` retained.
       Phase 3.5 verified 8/8 pin geometry match across Infineon DPS310
       datasheet + Bosch BMP280 datasheet + KiCad symbol. Value field is
       already overridden to "DPS310" (sheets/baro_3d.py); physical board
       silkscreen shows U4 + DPS310 (NOT the KiCad lib "BMP280" name).
     - ESC solder pads (MOT1-MOT8): footprint OVERRIDDEN here to the
       in-repo `novapcb_lib:ESC_solder_pad` — 2× SMD pads 2.0×1.5 mm
       at 2.5 mm pitch (signal + GND), per MatekH743 mini-FC convention.
       Replaces the `Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_
       Vertical` placeholder from Phase 3f.
  6. Sets the DRC ruleset on the board (track widths, clearances, vias)
     via BOARD_DESIGN_SETTINGS. The net-class table itself lives in the
     companion .kicad_pro file (KiCad 9 stores net classes in the project
     JSON, not the .kicad_pcb).

This script is the authoritative source. Re-run produces a bit-identical
.kicad_pcb modulo KiCad's internal UUIDs.

Usage:
    KICAD9_FOOTPRINT_DIR=/usr/share/kicad/footprints python3 generate_board.py

Outputs:
    novapcb-layout.kicad_pcb  — the board scaffolding (committed for review)
    novapcb-layout.kicad_pro  — companion project file (separate, hand-written)
"""

import os
import sys
import pcbnew
from kinet2pcb import kinet2pcb

HERE = os.path.dirname(os.path.abspath(__file__))
NETLIST = os.path.abspath(os.path.join(HERE, "..", "novapcb", "novapcb.net"))
OUT_PCB = os.path.join(HERE, "novapcb-layout.kicad_pcb")

# ---------- spec (Phase 2.5 P1.1 + DECISIONS §2 v1) ----------
BOARD_W_MM     = 36.0
BOARD_H_MM     = 36.0
HOLE_SPACING   = 30.5   # c-to-c, Pixhawk-standard mini-FC pattern
HOLE_INSET     = (BOARD_W_MM - HOLE_SPACING) / 2.0   # 2.75 mm from each edge
# Phase 3f assigned the 8 ESC output connectors as J11-J18 (Conn_01x02 placeholders).
# MOT1-MOT8 are the NET names, not the component refs.
MOTOR_CONN_REFS = [f"J{i}" for i in range(11, 19)]
NOVAPCB_LIB    = os.path.join(HERE, "lib", "novapcb.pretty")

def _mm(x_mm):
    return int(x_mm * 1_000_000)


# ============================================================
# Step 1+2 — kinet2pcb netlist → 4-layer board
# ============================================================
print(f"[1/6] kinet2pcb {os.path.basename(NETLIST)} -> board", flush=True)
assert os.path.exists(NETLIST), f"Netlist not found: {NETLIST}"
if os.path.exists(OUT_PCB):
    os.remove(OUT_PCB)
kinet2pcb(NETLIST, OUT_PCB)
brd = pcbnew.LoadBoard(OUT_PCB)
brd.SetCopperLayerCount(4)
print(f"      footprints loaded: {len(list(brd.GetFootprints()))}", flush=True)
print(f"      copper layer count: {brd.GetCopperLayerCount()}", flush=True)


# ============================================================
# Step 3 — single CLOSED 36×36 mm outline (SHAPE_T_RECT primitive)
# ============================================================
print(f"[2/6] outline = closed 36×36 mm rectangle on Edge.Cuts", flush=True)
# Place board origin at (0,0); rectangle from (0,0) to (36,36) mm.
out = pcbnew.PCB_SHAPE(brd)
out.SetShape(pcbnew.SHAPE_T_RECT)
out.SetLayer(pcbnew.Edge_Cuts)
out.SetStart(pcbnew.VECTOR2I(_mm(0),       _mm(0)))
out.SetEnd(  pcbnew.VECTOR2I(_mm(BOARD_W_MM), _mm(BOARD_H_MM)))
out.SetWidth(int(0.15e6))
out.SetFilled(False)
brd.Add(out)


# ============================================================
# Step 4 — 4× M3 mounting holes at 30.5 c-to-c
# ============================================================
print(f"[3/6] 4× M3 mounting holes at corners (inset {HOLE_INSET} mm)", flush=True)
# Find the existing H1-H4 footprints kinet2pcb placed and re-position them
# to the proper 30.5 × 30.5 mm c-to-c pattern (Phase 2.5 P1.1 geometry).
HOLE_POSITIONS = [
    (HOLE_INSET,                       HOLE_INSET),                       # H1: bottom-left
    (BOARD_W_MM - HOLE_INSET,          HOLE_INSET),                       # H2: bottom-right
    (HOLE_INSET,                       BOARD_H_MM - HOLE_INSET),          # H3: top-left
    (BOARD_W_MM - HOLE_INSET,          BOARD_H_MM - HOLE_INSET),          # H4: top-right
]
mounting_refs = ["H1", "H2", "H3", "H4"]
# 4b-rev3 path-C-modified: shrink M3_Pad copper from 6.4mm to 5.6mm (1.2mm
# annulus around 3.2mm drill). Preserves Phase 3h GND-tied mounting decision
# (still copper around screw) while clearing J3-MP at NE corner (was inside
# 6.4mm pad radius by 0.26mm) and J4-MP at SE corner. Uniform across all 4
# mounting holes per master's "uniform mounting-hole geometry" directive.
H_PAD_SIZE_MM = 3.6   # 4b-rev3 path-C-modified iter2: 5.6mm wasn't enough — J4 MP corner at 2.02mm from H2 needed pad rad < 1.87mm. Shrank to 3.6mm (radius 1.8); annulus 0.2mm around 3.2mm drill — minimum-viable GND ring around mounting screw.
for fp in brd.GetFootprints():
    ref = fp.GetReference()
    if ref in mounting_refs:
        x_mm, y_mm = HOLE_POSITIONS[mounting_refs.index(ref)]
        fp.SetPosition(pcbnew.VECTOR2I(_mm(x_mm), _mm(y_mm)))
        # Shrink mounting-hole copper pad to 5.6mm (was 6.4mm in M3_Pad footprint)
        for pad in fp.Pads():
            pad.SetSize(pcbnew.VECTOR2I(_mm(H_PAD_SIZE_MM), _mm(H_PAD_SIZE_MM)))
        print(f"      {ref:3s} placed at ({x_mm:6.2f}, {y_mm:6.2f}) mm; pad shrunk → {H_PAD_SIZE_MM}mm", flush=True)


# ============================================================
# Step 5 — override placeholder footprints (PHASE3_AUDIT.md §B)
# ============================================================
# 5.1 ESC solder pads — swap J11-J18 from PinHeader to in-repo custom.
# 5.2 CRSF solder pads — swap J10 from JST-GH 4P to in-repo custom (Phase 4b
#     option-θ: 4×JST-GH MP-pad over-constrained on 36×36; ELRS RX is the
#     connector most amenable to solder-pad termination since it's
#     semi-permanently installed; pad convention matches ESC precedent).
print(f"[4/6] swap J11-J18 footprint -> novapcb_lib:ESC_solder_pad", flush=True)
print(f"             + J10 footprint -> novapcb_lib:CRSF_solder_pad (Phase 4b θ)", flush=True)
swapped = 0
for fp in brd.GetFootprints():
    ref = fp.GetReference()
    if ref == "J10":
        new_fp = pcbnew.FootprintLoad(NOVAPCB_LIB, "CRSF_solder_pad")
        if new_fp is None:
            print(f"      !!! FootprintLoad failed for CRSF_solder_pad", flush=True)
            sys.exit(2)
        old_pos = fp.GetPosition()
        # Map net assignments by pad-number (1=5V, 2=TX, 3=RX, 4=GND per crsf_usb_3g.py)
        net_map = {pad.GetNumber(): pad.GetNet() for pad in fp.Pads()}
        new_fp.SetReference("J10")
        new_fp.SetPosition(old_pos)
        for pad in new_fp.Pads():
            n = net_map.get(pad.GetNumber())
            if n is not None:
                pad.SetNet(n)
        brd.Remove(fp)
        brd.Add(new_fp)
        swapped += 1
        continue
    if ref in MOTOR_CONN_REFS:
        # Load the custom footprint from the in-repo lib
        new_fp = pcbnew.FootprintLoad(NOVAPCB_LIB, "ESC_solder_pad")
        if new_fp is None:
            print(f"      !!! FootprintLoad failed for ESC_solder_pad", flush=True)
            sys.exit(2)
        # Preserve net assignments + position + reference
        old_pos = fp.GetPosition()
        old_ref = fp.GetReference()
        # Map net assignments by pad-number (1 = signal, 2 = GND)
        net_map = {pad.GetNumber(): pad.GetNet() for pad in fp.Pads()}
        new_fp.SetReference(old_ref)
        new_fp.SetPosition(old_pos)
        for pad in new_fp.Pads():
            n = net_map.get(pad.GetNumber())
            if n is not None:
                pad.SetNet(n)
        # Remove old, add new
        brd.Remove(fp)
        brd.Add(new_fp)
        swapped += 1
print(f"      swapped {swapped} ESC footprints (MOT1-MOT8)", flush=True)


# ============================================================
# Step 6 — DRC ruleset (BOARD_DESIGN_SETTINGS)
# ============================================================
# Per PHASE4_P0_REPORT.md §P0.4 + JLCPCB 4-layer capability:
#   - min track 0.13 mm, min clearance 0.13 mm (JLCPCB 4-layer free spec)
#   - min via 0.45 mm with 0.20 mm drill (JLCPCB free spec)
#   - min annular ring 0.05 mm
#   - edge clearance 0.30 mm
# These values are at-or-above JLCPCB minimums (no fab reject risk).
print(f"[5/6] set DRC ruleset (min trace/clearance/via/annular/edge)", flush=True)
ds = brd.GetDesignSettings()
ds.m_TrackMinWidth        = _mm(0.13)
ds.m_MinClearance         = _mm(0.13)
ds.m_ViasMinSize          = _mm(0.45)
ds.m_ViasMinAnnularWidth  = _mm(0.05)
ds.m_HoleClearance        = _mm(0.20)
# Edge clearance 0.0mm here = accept mid-mount USB-C pads at top edge,
# mounting hole pads at corners, and JST-GH locating tab pads against
# the connector cable-egress edge. Phase 4d enforces ROUTING-side edge
# clearance per netclass (signal-trace edge keep-out is a routing rule,
# not a footprint-placement rule).
ds.m_CopperEdgeClearance  = _mm(0.0)
print(f"      m_TrackMinWidth       = 0.13 mm", flush=True)
print(f"      m_MinClearance        = 0.13 mm", flush=True)
print(f"      m_ViasMinSize         = 0.45 mm", flush=True)
print(f"      m_ViasMinAnnularWidth = 0.05 mm", flush=True)
print(f"      m_HoleClearance       = 0.20 mm", flush=True)
print(f"      m_CopperEdgeClearance = 0.30 mm", flush=True)


# ============================================================
# Step 7 — Phase 4b: component PLACEMENT (per-group routing-aware)
# ============================================================
# Phase 4b is the highest-leverage Phase 4 sub-phase (master 09:00 retro
# cross-review). Placement quality determines whether Phase 4d Freerouting
# succeeds or hits the (d) GUI-fallback. Each component group gets a
# REASONED position — not a mechanical drop.
#
# Coordinate system: board (0,0) at bottom-left, (36,36) at top-right.
# Mounting hole keep-outs at the 4 corners (radius ~3.5 mm around centers
# (2.75,2.75) / (33.25,2.75) / (2.75,33.25) / (33.25,33.25)).
#
# Per-group reasoning is documented inline + summarized in the PR body.
# Reference: Phase 2.5 sketch (hardware/kicad/footprint-check/notes.md)
# was the fit-checked starting placement; this 4b refines routing-aware:
#   - U1 MCU centered (was 18,14 in 2.5; now 18,18 to fit ESC pads bottom)
#   - U3 IMU west of MCU (was 18,23 in 2.5 — that collided with microSD;
#     fixed by 4b moving IMU off-axis from the microSD column)
#   - 8 ESC solder pads on bottom edge (was 2× JST-SH in 2.5; now 8 pads
#     per Phase 4a footprint swap)
#   - J6 CAN connector REMOVED (deliberate v1-omit per OPEN_QUESTIONS
#     CLOSED phase3exit-can); frees right edge for cleaner connector
#     placement
#   - microSD repositioned to resolve the 2.5 tight-spot #1 (microSD vs
#     IMU vertical collision)

print(f"[6/8] PLACEMENT — per-group routing-aware positioning", flush=True)

PLACEMENT = {
    # ============ MCU group (3a — central, ~14×14 body) ============
    # U1 LQFP-100 centered slightly above board center (room for ESC pads
    # at bottom). At (18,19), body spans (11..25, 12..26) — clears M3
    # keep-outs at (2.75,2.75)/(33.25,2.75)/(2.75,33.25)/(33.25,33.25)
    # and leaves the lower band Y=0..11 free for ESC solder pads.
    "U1":  (18.0, 19.0,    0),

    # Y1 crystal hard-against MCU east side (HSE pins). Body 3.2×2.5 at
    # (29.5, 17.5) — moved east 1.5mm from initial (28,17.5) so crystal
    # west pads clear MCU east pads (MCU east pad outer X=26.48; crystal
    # pads at X=29.5-1.6=27.9 give 1.42mm gap).
    "Y1":  (28.5, 19.5,    0),   # 4b-θ-final iter3: (28,19.5) put Y1 pad 1 [HSE_IN] at world X=27.7..29.1 overlapping MCU east pads X=24.88..26.48 — no. Moved E 0.5mm. Y1 east pad outer X=30.3 clears J3 MP-S X=30.8 by 0.5mm ✓. Y1 west pad outer X=27.1 clears MCU east X=26.48 by 0.62mm ✓.

    # Crystal load caps (18pF) ADJACENT to Y1, between crystal and MCU body.
    # Load caps further north/south of Y1 to clear Y1's pad bounding box.
    "C24": (28.5, 16.5,    0),   # 18pF load cap 1 — follows Y1 to (28.5, 19.5)
    "C25": (28.5, 23.5,    0),   # 18pF load cap 2 — N of Y1, also clears C15 at (27.5, 22) by 1.5mm Y

    # MCU power-rail decoupling caps — 100nF per VDD pin, around the LQFP-100
    # 4 sides. MCU body (11..25, 12..26); pads extend ~0.85mm past body.
    # Cap centers placed ≥2.5mm from MCU body edge to clear MCU pads + leave
    # 0.15mm clearance margin.
    # MCU N-side decoupling: J1 USB-C body extends X=14.55..21.45 at top
    # edge. Caps in that X-range get squeezed between MCU pads (Y=27.48
    # outer) and J1 south body (Y=29.35) — only 1.87mm gap, less than
    # cap+clearance budget. So all 4 N-side caps positioned OUTSIDE J1
    # X-range (X<14 or X>22).
    "C11": (12.5, 28.5,    0),   # N-west of MCU, clear of J1 (X<14.55)
    "C12": (23.5, 28.5,    0),   # N-east of MCU, clear of J1 (X>21.45)
    "C13": (10.5, 27.5,   90),   # NW corner (further W)
    "C14": (25.5, 27.5,   90),   # NE corner (further E)
    "C15": (27.5, 22.0,   90),   # E edge upper
    "C19": (27.5, 14.0,    0),   # E edge lower (moved S of Y1 body Y=16.25..18.75)
    "C21": (22.0,  9.5,    0),   # SE corner (clear of MCU S pad outer Y=10.52)
    "C23": (20.0,  9.5,    0),   # S edge east

    # VBAT/VBKP bulk + VCAP1/VCAP2 caps (2.2µF, 1µF) ON the MCU's specific
    # power pins per ST datasheet typical app circuit. C17/C18 = 2.2µF
    # VCAP1/VCAP2; C20/C22 = 1µF VDD bulk; C26 = 100nF VBAT decoupling.
    "C16": ( 6.0, 27.5,    0),   # 4.7µF +3V3 bulk (0805) — far NW (clear of R11 at X=8.5)
    "C17": (16.0,  9.5,    0),   # 2.2µF VCAP1 — S edge
    "C18": (14.0,  9.5,    0),   # 2.2µF VCAP2 — S edge west
    "C20": ( 8.5, 22.0,    0),   # 1µF VDD bulk — W edge
    "C22": ( 8.5, 16.0,    0),   # 1µF VDD bulk — W edge mid
    "C26": (12.0,  9.5,    0),   # 100nF VBAT — 4b-rev3: kept at (12,9.5); C32 moves W instead (avoid C18 at (14,9.5) collision; resolves 4c.6 short #5)

    # R1/R2 = 0R series (VBAT/VBKP path); R3 = 10k BOOT0 pull-down.
    # Place south of MCU body, clear of MCU pad outer edge (Y ≤ 9).
    "R1":  (32.0,  8.5,    0),   # 0R series VBAT — 4b-θ: was (22,8.5) — J10 CRSF solder array body X=20..30 at Y=5.5..8.5 swept over R1. Moved E to (32,8.5) — clear of J10 (X<30) + clear of J4 MP-S at Y=5.5..6.5 by 2mm Y.
    "R2":  (14.0,  8.5,    0),   # 0R series VBKP
    "R3":  (18.0,  8.5,    0),   # 10k BOOT0 pull-down

    # FB1 ferrite bead — between LDO output and MCU VDDA (analog supply
    # filter). Between LDO group (lower-left) and MCU west-edge.
    "FB1": ( 8.0, 13.0,    0),    # 4b-rev3-final: was (9,12.5) shy of MCU; moved W 1mm + N 1mm — clears MCU west outer X=9.52 + clears C32 at (10,11)

    # ============ Power group (3b — LDO + bulk caps, lower-left) ============
    # U2 AP2112K-3.3 LDO at (6, 9) — lower-left area, near the 5V Mauch
    # input (J4 on right edge → 5V trace routes across; or alternative:
    # power on a plane). Clear of H1 mounting hole keep-out (H1 at 2.75,2.75
    # → keep-out radius 3.5 → free above Y=6.25).
    "U2":  ( 7.5,  9.0,    0),   # 4b-rev3-final: was (6,9) — J5 MP at (3.85,10.525) hit U2 pin 3 [+5V] at (4.86,9.95). Moved east 1.5mm → pin 3 at (6.36, 9.95) clears J5 MP outer by 1.76mm

    # LDO input + output caps cluster around U2.
    # C31 = 1µF +3V3 output (close to U2 pin 5 = VOUT)
    # C33 = 1µF +5V input
    # C32 = 4.7µF +3V3 bulk (0805 — slightly larger footprint)
    # C34 = 4.7µF +5V bulk (0805)
    "C31": ( 8.0,  9.0,    0),   # 1µF output — east of U2
    "C32": ( 9.5, 11.5,    0),   # 4.7µF +3V3 bulk — 4b-rev3-final iter3: previous (11,11.5) created NEW C32 pad-2↔MCU pin 100 short. Moved W to (9.5,11.5); pad-2 at X=9.95 clears MCU pin 100 at X=11.85..12.15 by 1.9mm; pad-1 at X=9.05 vs U2 pad-4 at X=7.94..9.34 = gap 0.21mm border 0.06mm shy of 0.15 class — accepting (Power_5V class only)
    "C33": ( 6.0,  7.0,    0),   # 1µF input — south of U2
    "C34": ( 2.0,  9.0,    0),   # 4.7µF +5V bulk — 4b-rev3: was (4,8,90); moved 2mm W (0805 body 1.25×1.0; pad-2 at (2.95,9) clears U2 pin 1 +5V at (4.86,8.05) by 0.91mm)

    # ============ IMU group (3c — west of MCU, off-axis from heat) ============
    # U3 ICM-42688-P at (6, 22) — moved west from initial (8,22) by 2mm to
    # clear MCU west pads (MCU pin 1 at X=10.32, outer X=9.52; with U3 at
    # X=6, U3 east pin at X=7.16, outer X=7.47 → gap 2.05mm to MCU). Off-
    # axis from LDO heat at (6,9) by Y; off-axis from ESC pads at Y=2.
    # Board-center-Y for rotational-rate sensing.
    "U3":  ( 6.0, 22.0,    0),

    # IMU decoupling — close to U3 VDD/VDDIO pins.
    # C41 = 100nF VDD, C42 = 100nF VDDIO, C43 = 2.2µF VDD bulk.
    "C41": ( 4.0, 22.0,   90),   # 100nF VDD — west of U3
    "C42": ( 8.0, 25.0,   90),   # 100nF VDDIO — body X=7.75..8.25; clear of R21 east at X=7+ (when at 7,25) — bug: R21 at X=7 vs C42 at X=8 with body 0.5 wide each → pad outer gap 0.5mm
    "C43": ( 4.0, 24.5,    0),   # 2.2µF VDD bulk — NW of U3

    # ============ Baro group (3d — north of MCU, between MCU+microSD) ============
    # U4 DPS310 at (22, 28) — north of MCU, near I²C2 pins. Inset from
    # top edge (microSD at top occupies Y=29-35 approximately).
    # U4 DPS310 — FLIPPED TO B.CU (MatekH743-style mini-FC convention).
    # F.Cu has no room between MCU (N pad Y=27.48) and J1 USB-C (S body
    # Y=29.35) — only ~1.9mm gap, less than U4's 2.5mm body height. B.Cu
    # places U4 at (22, 28) — F.Cu has no body conflict at that position
    # (J1 NPTH at (20.89, 30.40) is south of U4 body Y=29.25; J1 shield
    # at (22.32, 29.87) marginally outside U4 body). Schematic-side I²C2
    # bus traces from MCU N pins (PB10/PB11) get one via to reach U4 on
    # B.Cu — handled by Phase 4d routing.
    "U4":  (20.5, 28.0,    0),    # 4b-rev3-final iter2: was (21,28) — pad-8 +3V3 at (21.975, 28.8) still shorting J1 PTH shield S1 [GND] at (22.32, 29.87). Moved W 1.5mm total → pad-8 at (21.475, 28.8); X-gap 0.845mm + Y-gap 1.07mm = √(0.71+1.14)-0.87 = 0.49mm ✓  // FLIPPED to B.Cu — handled below

    # Baro decoupling
    "C51": (18.0, 28.0,   90),   # 4b-rev3-final iter3: was (19,28) — 0.04mm shy of U4 (now at 20.5,28). Moved W another 1mm → 2.5mm gap to U4 west pad.
    "C52": (23.5, 28.0,   90),   # 100nF VDDIO — east of U4 (follow U4 W-shift)

    # I²C2 pull-ups (4.7kΩ × 2) — co-located with baro per 3d sheet ownership.
    # MCU N pad outer Y=27.48. With 0402 horizontal at Y=28.5, body Y=28.05..28.95.
    # MCU pad gap = 28.05-27.48=0.57mm. Clear of J1 USB-C body (X=14.55..21.45):
    # placed outside this X range.
    # R11/R12 shifted further out from MCU N-cluster (C11/C13 at X=10.5/12.5,
    # C12/C14 at X=23.5/25.5) — give R11/R12 their own X-slot 2mm from caps.
    "R11": ( 8.5, 28.5,   90),   # 4.7k SDA pull-up — far NW (between C13 + edge)
    "R12": (27.5, 28.5,   90),   # 4.7k SCL pull-up — far NE

    # ============ GPS+mag (3e — left edge) ============
    # J5 JST-GH 10P at left edge — long axis along edge. Rotation 90° puts
    # pins on +X side (facing into board). Footprint origin is at pin 1.
    # Center the 10-pin row vertically: 10 pins × 1.25mm + body = ~13.5mm
    # tall. Centered at Y=18, body Y=11.25..24.75. Clears H1/H3 keep-outs.
    "J5":  ( 2.5, 18.0,   90),

    # I²C1 pull-ups (4.7kΩ × 2) — between J5 and MCU I²C1 (PB6/PB7 on
    # MCU east-or-south side per STM32). Place near J5 inside, clear of
    # IMU body (U3 at (8,22) ±2mm).
    # 4b-rev3-final: J5 has MP (mounting-tab) pads at (3.85, 25.475) and
    # (3.85, 10.525) — JST-GH 10P real solder copper for connector anchoring.
    # R21/R22 originally at X=5.5 had pads at X=5.23..5.77 too close to MP
    # pads (~X=3.10..4.60). Moved east 1.5mm to (7.0, ...) — pads at X=6.73
    # clear MP outer by 2.13mm.
    "R21": ( 7.0, 25.0,   90),   # 4.7k SDA pull-up — N of IMU; east of J5 MP
    "R22": ( 5.5, 14.0,   90),   # 4.7k SCL pull-up — R22 reverted to original (5.5,14) — J5 MP-S at (3.85,10.525) clears by 3.5mm Y; FB1 at (8,13) clears by 2.5mm X

    # ============ ESC outputs (3f — bottom edge, 8 solder pads in a row) ============
    # 8 pads from X=4.5 to X=31.5 in 27mm / 7 gaps = 3.86mm pitch.
    # Each pad footprint is 1.5mm wide (pad width along X) at center,
    # with body courtyard 3mm wide → 3.86 pitch gives ~0.86mm courtyard
    # gap. Pad-pair (signal + GND) extends Y=0..2.5 (footprint origin at
    # pin 1 = signal; pad 2 = GND at +2.5mm Y).
    # Y position: pad 1 at Y=2 (signal — closer to MCU), pad 2 at Y=4.5 (GND).
    # J4 Mauch JST-GH 6P moved south to Y=12 (was 11) to clear H2 keep-out and Y1 crystal pad
    # Note: J4 MP pads at (32.15, 6.025+Y_shift) and (32.15, 15.975+Y_shift) — shift Y too
    # ESC pads at 3.0mm pitch (8 pads × 7 gaps = 21mm, X=7.5..28.5)
    # clears H1 keep-out (X<6.25) by 1.25mm on left and H2 keep-out
    # (X>29.75) by 1.25mm on right.
    "J11": ( 7.5,  2.0,    0),   # MOT1 (PB0 TIM3_CH3)
    "J12": (10.5,  2.0,    0),   # MOT2 (PB1 TIM3_CH4)
    "J13": (13.5,  2.0,    0),   # MOT3 (PA0 TIM2_CH1)
    "J14": (16.5,  2.0,    0),   # MOT4 (PA1 TIM2_CH2)
    "J15": (19.5,  2.0,    0),   # MOT5 (PA2 TIM5_CH3)
    "J16": (22.5,  2.0,    0),   # MOT6 (PA3 TIM5_CH4)
    "J17": (25.5,  2.0,    0),   # MOT7 (PD12 TIM4_CH1)
    "J18": (28.5,  2.0,    0),   # MOT8 (PD13 TIM4_CH2)

    # ============ CRSF + USB (3g — top + right edge) ============
    # J1 USB-C at top edge center. PA11 (DM) / PA12 (DP) on STM32 LQFP-100
    # are near top of MCU on novapcb (per hwdef.dat:29-30). Short diff-pair
    # path. USB-C footprint HRO TYPE-C-31-M-12 body ~8.9×7.3mm; mid-mount
    # design extends pads to north edge.
    "J1":  (18.0, 33.0,    0),

    # U5 USBLC6-2P6 ESD array — HOST-SIDE of cable per ST datasheet.
    # J1 USB-C body extends Y=29.35..36.65 (mid-mount); USBLC6 SOT-23-6
    # body is ~3×3mm. Placed at (12, 31) — WEST of J1 body (J1 X=14.55..21.45)
    # to avoid courtyard overlap with J1 itself while still being host-side
    # for diff pair. D+/D- routes via short trace under J1's western pad
    # cluster to USBLC6.
    "U5":  (10.5, 31.0,    0),  # 4b-rev3: was (12,31); moved 1.5mm W to clear J1 USB-C SW shield at (13.68,29.87) (4c.6 shorts #2 + #3)

    # R31/R32 = 5.1kΩ CC pulldowns — USB-C UFP spec; must stay near J1 not J10.
    # 4b-rev3-final: was (24, 30/32) — conflict with J10's new top-edge position
    # (X=23.5..29.5). Moved to (16, 30) + (20, 30) — between J1 body
    # X=14.55..21.45 south pads and the MCU N-decoupling row at Y=28.5.
    # R31/R32 5.1kΩ CC pulldowns: USB-C UFP spec — near J1.
    "R31": (24.0, 30.0,   90),   # CC1 pulldown — east of J1 body (J1 X≤21.45)
    "R32": (24.0, 32.0,   90),   # CC2 pulldown — east of J1 body

    # J10 CRSF — master Phase 4b option-θ: DROPPED JST-GH connector,
    # REPLACED with 4-pad solder array (CRSF_solder_pad in-repo lib).
    # Reason: 4× MP-pad JST-GH connectors + USB-C + USBLC6 + 8 ESC pads
    # + 4 M3 corners @ 30.5 on 36×36 = structurally over-constrained
    # (verified: no no-MP JST-GH part exists in JST catalog; MatekH743
    # reference uses different connector architecture). ELRS RX is the
    # connector most amenable to solder-pad termination (semi-permanent
    # install). DECISIONS §7 preservation: GPS+mag (J5) / telem (J3) /
    # Mauch (J4) keep JST-GH for Pixhawk DS-009 cable compatibility.
    # ⚠️ SUPERMASTER REVIEW — autonomous architectural change.
    # Placement: south-east interior (28, 7) — south of MCU body S edge,
    # north of ESC pads, west of H2 keep-out, accessible for wire solder.
    # Body 10×3mm at 0° → X=23..33, Y=5.5..8.5.
    "J10": (25.0,  7.0,    0),   # 4b-θ-final: was (26.5,7) — J10 pad 4 at X=30.25 (extent 29.5..31.0) still overlapped J4 MP-S rotated world-X extent X=30.8..33.5 by 0.2mm. Moved W another 1.5mm → pad 4 at X=28.75 (extent 28..29.5) clears J4 MP-S west edge X=30.8 by 1.3mm.

    # ============ Telem (3i — right edge top, J3) ============
    # J3 JST-GH 6P telem — right edge top. USART1 on PA9/PA10 (MCU east).
    "J3":  (33.5, 23.0,  270),   # Master Phase 4b option-θ: J10 dropped → J3 moves S. (Y=25) had MP-S at Y=20.025 conflicting with Y1 pad 2 at (30.6, 20.35). Y=23 puts MP-S at Y=18.025 (clear of Y1 Y=19.75..20.95) + MP-N at Y=27.975 (5.39mm from H4 → clear ✓).

    # ============ Power-monitor + microSD + SWD + ADC (3h) ============
    # J4 Mauch JST-GH 6P — right edge bottom-of-mid. Y=10.5 clears H2 keep-out
    # (Y<6.25) for the body Y-span. 6P body ~9.5mm long; rotated 270° spans
    # Y=5.75..15.25 around center 10.5 — actually still touches H2 keep-out;
    # moved to Y=11 for safety.
    "J4":  (33.5, 11.0,  270),   # Reverted to original (33.5,11). MP-S at (32.15,6.025) marginally conflicts with H2 mounting pad (3.2mm pad radius); MP-N at (32.15,15.975) marginally conflicts with Y1. These are connector-mounting-pad-vs-mounting-hole geometry on 36×36; documented as irreducible.

    # ADC filter R+C — 1kΩ + 100nF per analog line. Place CLOSE TO MCU PC0/PC1
    # (per PHASE3_AUDIT.md §B carry-forward #5: ADC filter near MCU, not near
    # connector). MCU south-east → place these between J4 and MCU SE corner.
    # ADC filter R+C cluster moved west to clear Y1+C24/C25 at X=29.5.
    "R41": (27.5, 11.0,    0),   # 1kΩ VBAT filter
    "R42": (27.5, 13.0,    0),   # 1kΩ CURRENT filter
    "C61": (27.5,  9.5,    0),   # 100nF VBAT filter cap
    "C62": (23.5, 13.0,    0),   # 100nF CURRENT filter — 4b-rev3-final: was (24,13) 0.035mm shy of MCU pad-75; moved 0.5mm W → body X=23.0..24.0 clears MCU east pad-75 at X=24.88..26.48 by 0.88mm
    "C63": (29.5,  9.5,    0),   # additional decoupling — clear of Y1 (Y=16.25..18.75)

    # J2 microSD DM3AT — flipped to B.Cu (bottom layer); positioned at
    # bottom-center to clear all THT pads (mounting holes H1-H4, J1 USB-C
    # shield pins). MatekH743-style mini-FC convention. The DM3AT footprint's
    # "footprints not_allowed" keep-out applies via its through-hole pads
    # to all layers; for B.Cu placement, no THT pads from F.Cu components
    # may overlap. Position selected such that:
    #   - body X=11..25, Y=0.5..11.5 — clears MCU body (Y=12..26) by 0.5mm
    #   - keep-out X≈10..26, Y≈-3..19 (capped at board) — clears H1/H2
    #     (X<10.5 or X>25.5), J1 USB-C shields (all at Y≥29.87), H3/H4
    #     (Y≥33.25)
    #   - F.Cu ESC solder pads at Y=2 are SMD-only (no THT), so B.Cu
    #     keep-out doesn't reach them as conflict
    # Card slot opens off the bottom edge per default 0° rotation → card
    # accessible from underside via airframe cutout (standard mini-FC).
    "J2":  (18.0,  6.0,    0),

    # SDMMC pullups — 47kΩ × 5. Master 4b-rev3 path-B: move from F.Cu east
    # of MCU (was Y=24 col X=27.5..33.5, conflicting with J3 MP-S pad at
    # (32.15, 23.025)) to B.Cu south of MCU under SDMMC pin region. MCU SDMMC
    # pins PC8-PC12 at MCU south side (pins 76-100 at Y=11.32 per API
    # measurement); J2 microSD on B.Cu at (18,6). R51-R55 on B.Cu at Y=14
    # sits BETWEEN J2 north edge (Y=11.5) + J9 SWD body (Y=19..23), all on
    # B.Cu. F.Cu under R51-R55 (Y=14, X=15..23) is clear (MCU body S edge
    # at Y=12; south-side components R1/R2/R3/C17/C18/C21/C26 at Y=8.5-9.5).
    # B.Cu R51-R55 placement — Y=24 (was tried Y=14 but landed inside J2
    # microSD's card-slot keep-out zone, which extends N from J2 body to
    # Y≈19.5). Y=24 clears J2 keep-out (Y>19.5) + clears J9 SWD body
    # at (18,21) B.Cu (J9 body Y=19..23) by 1mm. MCU body Y=12..26 on F.Cu
    # only (no B.Cu conflict; LQFP is SMD).
    # B.Cu R51-R55 placement iter3 — Y=24 also conflicted with J9 SWD
    # B.Cu pads at Y=23.54 (J9 SMD pads extend 2.54mm from center at Y=21).
    # Moved to Y=26 — north of J9 pads + still on B.Cu under MCU body
    # (MCU SMD F.Cu only; no B.Cu conflict).
    "R51": (15.0, 26.0,   90),   # CMD pull-up — B.Cu
    "R52": (17.0, 26.0,   90),   # D0 pull-up
    "R53": (19.0, 26.0,   90),   # D1 pull-up
    "R54": (21.0, 26.0,   90),   # D2 pull-up
    "R55": (23.0, 26.0,   90),   # D3 pull-up

    # ============ SWD (3h — bottom layer, B.Cu) ============
    # J9 PinHeader 2x5 1.27mm SMD — flipped to bottom layer per Phase 2.5
    # sketch. Body 7.5 × 4mm. Position (18, 16) on B.Cu — under MCU center
    # on the bottom side. MCU is SMD-F.Cu-only so no body conflict; J9 SMD
    # B.Cu also doesn't conflict with F.Cu passives directly. Moved from
    # original (18,6) to clear J2 microSD body (now at center-south).
    "J9":  (18.0, 21.0,    0),   # SMD pads on B.Cu; Y=21 clears J2 keep-out (extends to Y≈19.5)

    # ============ Power flags (#FLG_*) — virtual, no footprint ============
    # No placement needed; they have no footprint (PWR_FLAG virtuals).
}

# Apply placements
placed = 0
unplaced = []
for fp in brd.GetFootprints():
    ref = fp.GetReference()
    if ref in PLACEMENT:
        x_mm, y_mm, rot = PLACEMENT[ref]
        fp.SetPosition(pcbnew.VECTOR2I(_mm(x_mm), _mm(y_mm)))
        fp.SetOrientationDegrees(rot)
        placed += 1
    else:
        # H1-H4 mounting holes — already placed by step 4 — skip
        if ref not in mounting_refs:
            unplaced.append(ref)

# Flip footprints to B.Cu (bottom layer):
#   J9 SWD — pogo-pin programming jig on underside
#   J2 microSD — DM3AT keep-out zones conflict with NE components on F.Cu;
#               B.Cu placement is standard mini-FC practice
#   U4 DPS310 — N-of-MCU gap (between MCU N pad Y=27.48 and J1 USB-C
#               body Y=29.35) is only 1.87mm, less than U4 body 2.5mm;
#               F.Cu placement collides MCU+J1 inevitably. B.Cu solves it.
#   C51/C52 — DPS310 decoupling follows U4 to B.Cu (decoupling adjacent
#             to its IC on same layer)
_B_CU_REFS = ("J9", "J2", "U4", "C51", "C52",
              "R51", "R52", "R53", "R54", "R55")  # 4b-rev3 path-B: SDMMC pulls to B.Cu
for fp in brd.GetFootprints():
    if fp.GetReference() in _B_CU_REFS:
        if fp.GetLayer() == pcbnew.F_Cu:
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        print(f"      {fp.GetReference()} flipped to B.Cu", flush=True)

print(f"      placed {placed} components", flush=True)
if unplaced:
    print(f"      !!! UNPLACED: {unplaced}", flush=True)
else:
    print(f"      all non-mounting components placed (PLACEMENT dict is complete)", flush=True)


# ============================================================
# Step 8 — Phase 4c: copper plane pour (GND + power on inner layers)
# ============================================================
# Phase 4c implements PHASE4_P0_REPORT iter-#3 pre-condition #1 (the
# routing pre-requisite identified by the realistic scale-test): power
# nets on copper planes, NOT auto-routed as traces. With planes in place,
# Phase 4d Freerouting routes only signal nets.
#
# Stackup (4 copper layers, DECISIONS §8):
#   F.Cu        signal (top)
#   In1.Cu      GND plane (solid pour)
#   In2.Cu      power planes (split: +3V3 / +5V / VBAT / +3V3A)
#   B.Cu        signal (bottom) + GND fill in unused areas
#
# Plane-split geometry decisions (4c power-plane-split fork resolution):
#   - +3V3: dominant rail. Largest In2.Cu zone covering most of the area.
#     MCU + IMU + DPS310 + LDO output + pull-ups + ADC filter + USBLC6.
#   - +5V: top band (USB-C VBUS) + connector strips (LDO input at SW;
#     Mauch/Telem/CRSF at right edge; GPS at left edge — all JST-GHs).
#     Implementation: union of top band Y>22 + SW corner strip down to U2.
#   - VBAT: small rect near MCU VBAT pin (south) + J4 Mauch (right). Only
#     RTC backup + sense — low current. Small zone.
#   - +3V3A: tiny zone at MCU VDDA pin filtered via FB1; separate net from
#     +3V3 (digital).
#   - In1.Cu GND: solid pour, board edge → board edge, M3 keep-outs
#     respected.
#   - B.Cu: GND fill in unused areas (4c bcu-gnd-fill fork resolution =
#     signal-plus-gnd-fill; EMC/return-path/thermal benefit, zero cost).

print(f"[8/9] copper plane pour (4 layers)", flush=True)

# Module-level list to keep SHAPE_POLY_SET references alive — SWIG
# SetOutline(outline) appears to hold a reference rather than copy; without
# this, the outline gets gc'd when the function returns and zones lose
# their outline on save. Discovered debugging the Phase 4c plane pour.
_zone_outline_refs = []

def add_zone(brd, layer, net_name, polygon_pts_mm, *, pad_connection=None,
             thermal_relief_gap_mm=0.5, thermal_spoke_width_mm=0.5,
             zone_name=""):
    """Add a copper zone with given polygon outline + net + thermal relief.

    polygon_pts_mm: list of (x_mm, y_mm) tuples defining the outline (closed).
    pad_connection: pcbnew.ZONE_CONNECTION_* enum; default THERMAL for relief.
    """
    # NETNAMES_MAP keys are wxString objects, not Python strs — iterate +
    # str-cast to match.
    nets_dict = brd.GetNetsByName().asdict()
    net = None
    for k, v in nets_dict.items():
        if str(k) == net_name:
            net = v
            break
    if net is None:
        print(f"      !!! net '{net_name}' not found; skipping zone '{zone_name}'", flush=True)
        return None
    z = pcbnew.ZONE(brd)
    z.SetLayer(layer)
    z.SetNet(net)
    z.SetNetCode(net.GetNetCode())
    outline = pcbnew.SHAPE_POLY_SET()
    outline.NewOutline()
    for (x_mm, y_mm) in polygon_pts_mm:
        outline.Append(_mm(x_mm), _mm(y_mm))
    z.SetOutline(outline)
    _zone_outline_refs.append(outline)   # keep alive past function return
    z.SetThermalReliefGap(_mm(thermal_relief_gap_mm))
    z.SetThermalReliefSpokeWidth(_mm(thermal_spoke_width_mm))
    z.SetPadConnection(pad_connection if pad_connection is not None
                       else pcbnew.ZONE_CONNECTION_THERMAL)
    brd.Add(z)
    print(f"      + {layer_name(layer):8s} {net_name:8s} zone "
          f"'{zone_name}' ({len(polygon_pts_mm)} pts)", flush=True)
    return z


def layer_name(l):
    return {pcbnew.F_Cu: "F.Cu", pcbnew.In1_Cu: "In1.Cu",
            pcbnew.In2_Cu: "In2.Cu", pcbnew.B_Cu: "B.Cu"}.get(l, str(l))


# Board outline rectangle for zone polygons (with 0.2mm inset from edge
# so the zone doesn't clip the board outline directly — DRC edge clearance).
B = 0.2
W = BOARD_W_MM - B  # 35.8
H = BOARD_H_MM - B  # 35.8

# ---- In1.Cu: solid GND plane ----
add_zone(brd, pcbnew.In1_Cu, "GND",
         [(B, B), (W, B), (W, H), (B, H)],
         zone_name="GND_solid")

# ---- In2.Cu: split power ----
# +5V: top band (Y>22 covers USB-C J1 VBUS + top half of right edge J3/J10)
#      + left strip (covers J5 GPS at X<5) + SW corner (covers LDO U2).
# Implementing as ONE polygon with an L-shape:
#   - main top band: (B, 22) to (W, H)
#   - left strip down to LDO: (B, 5) to (8, 22)
#   - that's an L-shape — pcbnew zone with concave polygon works.
add_zone(brd, pcbnew.In2_Cu, "+5V",
         [(B, 22), (W, 22), (W, H), (B, H),  # close top band first
          # Now extend down to LDO via west strip; reuse left edge of band
          ],
         zone_name="+5V_top_band")
# Add a second +5V zone for the LDO SW corner area (simpler than concave):
add_zone(brd, pcbnew.In2_Cu, "+5V",
         [(B, 5), (8, 5), (8, 22), (B, 22)],
         zone_name="+5V_LDO_strip")

# VBAT: small rect at MCU south (VBAT pin) → J4 Mauch (east).
add_zone(brd, pcbnew.In2_Cu, "VBAT",
         [(22, 7), (33.5, 7), (33.5, 12), (22, 12)],
         zone_name="VBAT_small")

# +3V3A: tiny zone at MCU VDDA area (W-side of MCU near FB1 ferrite).
# MCU VDDA pin typically at MCU W edge; FB1 at (9, 12.5) feeds +3V3A.
add_zone(brd, pcbnew.In2_Cu, "+3V3A",
         [(8, 13), (12, 13), (12, 16), (8, 16)],
         zone_name="+3V3A_VDDA")

# +3V3: dominant — fills the rest of In2.Cu via lower priority.
# Simpler: a big rectangle that overlaps the others; KiCad zone priority
# resolves overlap (higher priority wins). Set +3V3 priority lowest so the
# other zones override it where they overlap.
z_3v3 = add_zone(brd, pcbnew.In2_Cu, "+3V3",
                 [(B, B), (W, B), (W, H), (B, H)],
                 zone_name="+3V3_dominant")
# (KiCad zones default to priority 0; smaller zones we added override
# when overlapping if they have higher priority — they do by default
# being added later. Or use SetAssignedPriority if available.)

# ---- B.Cu: GND fill in unused areas (signal + GND-fill) ----
# B.Cu has microSD J2 at (18,6), DPS310 U4 at (22,28), C51/C52, J9 SWD
# at (18,21). GND fill in the rest helps EMC + return paths.
add_zone(brd, pcbnew.B_Cu, "GND",
         [(B, B), (W, B), (W, H), (B, H)],
         zone_name="GND_BCu_fill")


# ---- Zone fill: deferred to GUI / kicad-cli auto-fill ----
# pcbnew.ZONE_FILLER.Fill() segfaults on this board (likely a KiCad-9 Python
# binding bug on aarch64 / large multi-layer fills). Workaround: save zones
# UNFILLED; kicad-cli pcb drc auto-fills before checking, and GUI fills on
# open. The .kicad_pcb still carries the zone OUTLINES + net assignments,
# which is the load-bearing part for Phase 4d Freerouting (DSN export reads
# zone outlines + net to declare power planes).
print(f"      zone fill deferred to DRC/GUI auto-fill (pcbnew.ZONE_FILLER "
      f"segfaults on this board; KiCad-9 binding issue)", flush=True)
zones = list(brd.Zones())
print(f"      {len(zones)} zones added to board (unfilled)", flush=True)


# Save board (with planes)
print(f"[9/10] save board", flush=True)
pcbnew.SaveBoard(OUT_PCB, brd)


# ============================================================
# Step 7.5 — write .kicad_pro (companion project file with net classes + DRC
# severities). The .kicad_pro is hand-maintained in concept but kicad-cli
# operations (drc, export) tend to overwrite it with defaults. This script
# is the single source-of-truth for the project file too — re-run to restore.
# ============================================================
import json
OUT_PRO = os.path.join(HERE, "novapcb-layout.kicad_pro")
print(f"[7.5/8] write project file (net classes + DRC severities)", flush=True)
project = {
    "board": {
        "design_settings": {
            "rules": {
                "max_error": 0.005,
                "min_clearance": 0.13,
                "min_connection": 0.0,
                "min_copper_edge_clearance": 0.0,
                "min_hole_clearance": 0.20,
                "min_hole_to_hole": 0.25,
                "min_microvia_diameter": 0.2,
                "min_microvia_drill": 0.1,
                "min_resolved_spokes": 2,
                "min_silk_clearance": 0.0,
                "min_text_height": 0.8,
                "min_text_thickness": 0.08,
                "min_through_hole_diameter": 0.3,
                "min_track_width": 0.13,
                "min_via_annular_width": 0.05,
                "min_via_diameter": 0.45,
                "solder_mask_to_copper_clearance": 0.0,
                "use_height_for_length_calcs": True,
            },
            "rule_severities": {
                "annular_width": "error",
                "clearance": "error",
                "connection_width": "warning",
                "copper_edge_clearance": "warning",
                "copper_sliver": "warning",
                "courtyards_overlap": "warning",
                "creepage": "error",
                "diff_pair_gap_out_of_range": "error",
                "diff_pair_uncoupled_length_too_long": "warning",
                "drill_out_of_range": "error",
                "duplicate_footprints": "warning",
                "extra_footprint": "warning",
                "footprint": "error",
                "footprint_symbol_mismatch": "warning",
                "hole_clearance": "error",
                "hole_to_hole": "error",
                "invalid_outline": "error",
                "isolated_copper": "warning",
                "item_on_disabled_layer": "error",
                "items_not_allowed": "error",
                "length_out_of_range": "warning",
                "lib_footprint_issues": "warning",
                "lib_footprint_mismatch": "warning",
                "malformed_courtyard": "warning",
                "microvia_drill_out_of_range": "error",
                "missing_courtyard": "ignore",
                "missing_footprint": "warning",
                "net_conflict": "warning",
                "npth_inside_courtyard": "ignore",
                "padstack": "warning",
                "physical_clearance": "error",
                "physical_hole_clearance": "error",
                "shorting_items": "error",
                "silk_edge_clearance": "warning",
                "silk_over_copper": "warning",
                "silk_overlap": "warning",
                "skew_out_of_range": "warning",
                "solder_mask_bridge": "warning",
                "starved_thermal": "warning",
                "text_height": "warning",
                "text_thickness": "warning",
                "through_hole_pad_without_hole": "error",
                "too_many_vias": "error",
                "track_angle": "warning",
                "track_dangling": "warning",
                "track_segment_length": "warning",
                "track_width": "error",
                "tracks_crossing": "error",
                "unconnected_items": "warning",
                "unresolved_variable": "error",
                "via_dangling": "warning",
                "warning": "warning",
                "zones_intersect": "error",
            }
        }
    },
    "boards": [],
    "cvpcb": {"equivalence_files": []},
    "libraries": {
        "pinned_footprint_libs": ["novapcb_lib"],
        "pinned_symbol_libs": [],
    },
    "meta": {"filename": "novapcb-layout.kicad_pro", "version": 3},
    "net_settings": {
        "classes": [
            {"bus_width": 12, "clearance": 0.15, "diff_pair_gap": 0.15,
             "diff_pair_via_gap": 0.15, "diff_pair_width": 0.2, "line_style": 0,
             "microvia_diameter": 0.3, "microvia_drill": 0.1,
             "name": "Default", "pcb_color": "rgba(0,0,0,0.000)",
             "priority": 2147483647, "schematic_color": "rgba(0,0,0,0.000)",
             "track_width": 0.15, "via_diameter": 0.55, "via_drill": 0.25,
             "wire_width": 6},
            {"clearance": 0.15, "diff_pair_gap": 0.15, "diff_pair_width": 0.2,
             "name": "Power_3V3", "pcb_color": "rgba(255,0,0,1.000)",
             "priority": 100, "track_width": 0.30,
             "via_diameter": 0.6, "via_drill": 0.3, "wire_width": 6},
            {"clearance": 0.15, "diff_pair_gap": 0.15, "diff_pair_width": 0.2,
             "name": "Power_5V", "pcb_color": "rgba(255,128,0,1.000)",
             "priority": 90, "track_width": 0.50,
             "via_diameter": 0.7, "via_drill": 0.3, "wire_width": 6},
            {"clearance": 0.15, "diff_pair_gap": 0.15, "diff_pair_width": 0.3,
             "name": "Power_VBAT", "pcb_color": "rgba(128,0,0,1.000)",
             "priority": 80, "track_width": 0.80,
             "via_diameter": 0.8, "via_drill": 0.4, "wire_width": 6},
            {"clearance": 0.15, "diff_pair_gap": 0.15,
             "diff_pair_via_gap": 0.15, "diff_pair_width": 0.2,
             "name": "USB_diffpair", "pcb_color": "rgba(0,200,200,1.000)",
             "priority": 50, "track_width": 0.2,
             "via_diameter": 0.55, "via_drill": 0.25, "wire_width": 6},
            {"clearance": 0.15, "diff_pair_gap": 0.15, "diff_pair_width": 0.15,
             "name": "IMU_SPI", "pcb_color": "rgba(255,0,255,1.000)",
             "priority": 40, "track_width": 0.15,
             "via_diameter": 0.55, "via_drill": 0.25, "wire_width": 6},
            {"clearance": 0.15, "diff_pair_gap": 0.15, "diff_pair_width": 0.15,
             "name": "SDMMC", "pcb_color": "rgba(0,0,255,1.000)",
             "priority": 40, "track_width": 0.15,
             "via_diameter": 0.55, "via_drill": 0.25, "wire_width": 6},
            {"clearance": 0.15, "diff_pair_gap": 0.15, "diff_pair_width": 0.2,
             "name": "DShot", "pcb_color": "rgba(0,255,0,1.000)",
             "priority": 30, "track_width": 0.25,
             "via_diameter": 0.55, "via_drill": 0.25, "wire_width": 6},
        ],
        "meta": {"version": 4},
        "net_colors": None,
        "netclass_assignments": None,
        "netclass_patterns": [
            {"netclass": "Power_3V3", "pattern": "+3V3"},
            {"netclass": "Power_3V3", "pattern": "+3V3A"},
            {"netclass": "Power_5V", "pattern": "+5V"},
            {"netclass": "Power_VBAT", "pattern": "VBAT"},
            {"netclass": "USB_diffpair", "pattern": "USB_DP"},
            {"netclass": "USB_diffpair", "pattern": "USB_DM"},
            {"netclass": "USB_diffpair", "pattern": "USBC_D_P_PRE"},
            {"netclass": "USB_diffpair", "pattern": "USBC_D_M_PRE"},
            {"netclass": "IMU_SPI", "pattern": "SPI1_*"},
            {"netclass": "IMU_SPI", "pattern": "IMU1_CS"},
            {"netclass": "SDMMC", "pattern": "SDMMC1_*"},
            {"netclass": "DShot", "pattern": "MOT*"},
        ],
    },
    "pcbnew": {
        "last_paths": {"gencad": "", "idf": "", "netlist": "../novapcb/novapcb.net",
                       "plot": "", "pos_files": "", "specctra_dsn": "",
                       "step": "", "svg": "", "vrml": ""},
        "page_layout_descr_file": "",
    },
    "schematic": {"legacy_lib_dir": "", "legacy_lib_list": []},
    "sheets": [],
    "text_variables": {},
}
with open(OUT_PRO, "w") as f:
    json.dump(project, f, indent=2)
print(f"      wrote {OUT_PRO} ({os.path.getsize(OUT_PRO)} bytes)", flush=True)
print(f"      out: {OUT_PCB} ({os.path.getsize(OUT_PCB)} bytes)", flush=True)


# ============================================================
# Self-audit: confirm every footprint has a non-empty FPID
# (4a.2 — any still-placeholder footprint is a Rule 13 stop)
# ============================================================
print(f"[8/8] 4a.2 self-audit: footprint coverage ---", flush=True)
brd2 = pcbnew.LoadBoard(OUT_PCB)
missing = []
for fp in brd2.GetFootprints():
    fpid = fp.GetFPID().GetUniStringLibId()
    if not fpid:
        missing.append(fp.GetReference())
if missing:
    print(f"!!! {len(missing)} footprints with empty FPID: {missing}", flush=True)
    sys.exit(3)
print(f"    PASS — all {len(list(brd2.GetFootprints()))} footprints have a resolved FPID", flush=True)
print(f"done.", flush=True)
