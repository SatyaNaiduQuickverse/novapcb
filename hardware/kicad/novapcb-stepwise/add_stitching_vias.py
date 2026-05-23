#!/usr/bin/env python3
"""Add GND stitching vias per master 2026-05-23 Flag-1 option (b):
- 5mm pitch in HF/high-current regions
- 10mm pitch in calm regions
- Constraint: no via on existing pad/track (clearance check)

HF regions (5mm pitch):
- MCU + decap halo: X=38..58, Y=28..50
- Buck U2 + L1 + caps: X=14..36, Y=22..32
- USB-C J1 + U5 + diff-pair corridor: X=68..99, Y=27..38
- IMU island D zone: X=56..86, Y=51..63
- A subsystem OR-FET fanout + sense band: X=12..96, Y=2..18
- Buck SW node corridor (extra-tight): X=23..32, Y=23..27

Calm regions (10mm pitch): rest of board.

Stitching via: 0.40mm OD, 0.20mm drill (smaller than signal vias).
"""
import os
import sys
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")

VIA_DIA = 0.50      # 0.50mm OD (standard small via)
VIA_DRILL = 0.30    # 0.30mm drill (above board min 0.30mm)
# Min center-to-center to OTHER items. For via-to-pad: VIA_radius (0.25) +
# PAD_half (~0.3 for 0402 worst-case) + CLEARANCE (0.20) = 0.75mm. For
# via-to-via: 0.25 + 0.25 + 0.20 = 0.7mm. For via-to-track: 0.25 +
# track_half (added per-track) + 0.20 = base 0.45 + track_half. Use 0.85mm
# as safe min for pads/vias; track-clearance computed dynamically.
CLEARANCE = 0.60    # min center-to-center to other pads/vias (0.85mm total = 0.25+0.40+0.20)

# HF regions (5mm pitch)
HF_REGIONS = [
    (38, 28, 58, 50, 5.0, "MCU + decap halo"),
    (14, 22, 36, 32, 5.0, "Buck + L1 + Cin/Cout"),
    (68, 27, 99, 38, 5.0, "USB + ESD + diff-pair"),
    (56, 51, 86, 63, 5.0, "IMU island D zone"),
    (12, 2,  96, 18, 5.0, "OR-FET + sense band"),
]
# Whole board calm pitch
CALM_PITCH = 10.0

# Mounting hole keep-outs (don't place via on H1-H4 + 5mm radius)
HOLE_KEEPOUTS = [(3.25, 3.25), (101.75, 3.25), (3.25, 81.75), (101.75, 81.75)]
HOLE_RADIUS_KEEPOUT = 5.0

# Mid-edge mounting holes
MID_KEEPOUTS = [(3.0, 42.5), (102.0, 42.5)]
MID_RADIUS_KEEPOUT = 5.0

# Board outline (avoid edge)
BOARD_MARGIN = 1.0  # don't place stitching vias within 1mm of board edge
BOARD_X = (0, 105)
BOARD_Y = (0, 85)


def _mm(x):
    return pcbnew.FromMM(x)


def in_hf_region(x, y):
    for x0, y0, x1, y1, _pitch, _ in HF_REGIONS:
        if x0 <= x <= x1 and y0 <= y <= y1:
            return True
    return False


def is_in_keepout(x, y):
    """Mounting-hole + edge keep-outs."""
    if x < BOARD_X[0] + BOARD_MARGIN or x > BOARD_X[1] - BOARD_MARGIN:
        return True
    if y < BOARD_Y[0] + BOARD_MARGIN or y > BOARD_Y[1] - BOARD_MARGIN:
        return True
    for (kx, ky) in HOLE_KEEPOUTS:
        if ((x - kx) ** 2 + (y - ky) ** 2) ** 0.5 < HOLE_RADIUS_KEEPOUT:
            return True
    for (kx, ky) in MID_KEEPOUTS:
        if ((x - kx) ** 2 + (y - ky) ** 2) ** 0.5 < MID_RADIUS_KEEPOUT:
            return True
    return False


def point_to_segment_dist(px, py, x1, y1, x2, y2):
    """Min distance from point (px, py) to line segment (x1,y1)→(x2,y2)."""
    dx = x2 - x1; dy = y2 - y1
    if dx == 0 and dy == 0:
        return ((px - x1) ** 2 + (py - y1) ** 2) ** 0.5
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    cx = x1 + t * dx; cy = y1 + t * dy
    return ((px - cx) ** 2 + (py - cy) ** 2) ** 0.5


def conflicts_with_existing(brd, x, y, min_dist):
    """Check if a stitching via at (x, y) conflicts with existing pads,
    vias, or signal tracks. Returns True if any item is within min_dist."""
    # Pads — compute pad bbox + 0.20mm clearance + via radius
    via_radius = VIA_DIA / 2
    clearance = 0.20
    for fp in brd.GetFootprints():
        if fp.GetPosition().x / 1e6 >= 100:
            continue
        for pad in fp.Pads():
            pp = pad.GetPosition()
            ps = pad.GetSize()
            half_w = ps.x / 2e6
            half_h = ps.y / 2e6
            pad_x = pp.x / 1e6
            pad_y = pp.y / 1e6
            # Min distance from via center to pad bbox edge
            dx = max(0, abs(x - pad_x) - half_w)
            dy = max(0, abs(y - pad_y) - half_h)
            edge_dist = (dx * dx + dy * dy) ** 0.5
            # If via lands on or near pad, conflict (unless same net later)
            if edge_dist < via_radius + clearance:
                return True
    # Vias (any net — even other vias need clearance)
    # Tracks (segments — measure point-to-segment distance)
    for trk in brd.GetTracks():
        n = trk.GetNetname()
        if trk.GetClass() == "PCB_VIA":
            tp = trk.GetPosition()
            dist = ((x - tp.x / 1e6) ** 2 + (y - tp.y / 1e6) ** 2) ** 0.5
            if dist < min_dist:
                return True
        else:
            # Track segment — check distance to centerline
            s = trk.GetStart(); e = trk.GetEnd()
            x1, y1 = s.x / 1e6, s.y / 1e6
            x2, y2 = e.x / 1e6, e.y / 1e6
            # Skip far-away tracks (early bail)
            if abs(x - x1) > 50 and abs(x - x2) > 50:
                continue
            track_w = trk.GetWidth() / 1e6
            track_half = track_w / 2
            dist = point_to_segment_dist(x, y, x1, y1, x2, y2)
            if dist < min_dist + track_half:
                return True
    return False


def main():
    print("=== Add GND stitching vias (region-based pitch) ===", flush=True)
    brd = pcbnew.LoadBoard(PCB)
    gnd_net = brd.FindNet("GND")
    if gnd_net is None:
        print("ERROR: GND net missing"); return 1

    # Strip prior stitching vias (idempotent re-run).
    # Identify: via on GND net with diameter == VIA_DIA, drill == VIA_DRILL.
    # We can't easily distinguish "stitching" vs "signal" vias by metadata,
    # so we look for vias at GRID positions only (multiples of CALM_PITCH/2).
    # Simpler heuristic: track count of pre-existing GND vias for reporting.
    pre_gnd_vias = sum(1 for t in brd.GetTracks()
                       if t.GetClass() == "PCB_VIA" and t.GetNetname() == "GND")
    print(f"  pre-existing GND vias: {pre_gnd_vias}", flush=True)

    # Generate candidate positions
    candidates = []
    # HF region vias (5mm pitch)
    for x0, y0, x1, y1, pitch, name in HF_REGIONS:
        x = x0
        while x <= x1:
            y = y0
            while y <= y1:
                candidates.append((x, y, pitch, name))
                y += pitch
            x += pitch

    # Calm region vias (10mm pitch, full board minus HF regions)
    x = CALM_PITCH
    while x <= BOARD_X[1] - CALM_PITCH:
        y = CALM_PITCH
        while y <= BOARD_Y[1] - CALM_PITCH:
            if not in_hf_region(x, y):
                candidates.append((x, y, CALM_PITCH, "calm"))
            y += CALM_PITCH
        x += CALM_PITCH

    print(f"  {len(candidates)} candidate positions", flush=True)

    # Filter + place
    n_placed = 0
    n_keepout = 0
    n_conflict = 0
    min_dist = VIA_DIA / 2 + CLEARANCE  # via radius + clearance
    region_counts = {}
    for x, y, pitch, name in candidates:
        if is_in_keepout(x, y):
            n_keepout += 1
            continue
        if conflicts_with_existing(brd, x, y, min_dist):
            n_conflict += 1
            continue
        # Place
        v = pcbnew.PCB_VIA(brd)
        v.SetPosition(pcbnew.VECTOR2I(_mm(x), _mm(y)))
        v.SetWidth(_mm(VIA_DIA))
        v.SetDrill(_mm(VIA_DRILL))
        v.SetNet(gnd_net)
        brd.Add(v)
        n_placed += 1
        region_counts[name] = region_counts.get(name, 0) + 1

    print(f"  placed: {n_placed}, keepout-rejected: {n_keepout}, "
          f"existing-conflict: {n_conflict}", flush=True)
    for n, c in sorted(region_counts.items(), key=lambda x: -x[1]):
        print(f"    {n}: {c} vias", flush=True)

    # Refill zones (anti-pads around stitching vias on +5V_BEC + +3V3 planes;
    # solid-connect on GND zones)
    print("\n--- refill all zones ---", flush=True)
    for z in brd.Zones():
        if hasattr(z, "UnFill"):
            z.UnFill()
    filler = pcbnew.ZONE_FILLER(brd)
    filler.Fill(list(brd.Zones()))
    pcbnew.SaveBoard(PCB, brd)
    print(f"  saved", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
