#!/usr/bin/env python3
"""Add power-plane zones to novapcb-layout-v1.1 6-layer board.

Per DECISIONS §8 + PLACEMENT_STRATEGY §3.5 + CONTROLLED_IMPEDANCE.md:
  L1 (top, F.Cu):   signal
  L2 (In1.Cu):      GND plane  ← this script adds
  L3 (In2.Cu):      +3V3 plane ← this script adds
  L4 (In3.Cu):      +5V plane  ← this script adds
  L5 (In4.Cu):      GND plane  ← this script adds
  L6 (bot, B.Cu):   signal + bottom sensors

KiCad 9 pcbnew.SaveBoard() segfaults when saving boards with
SHAPE_POLY_SET zones added via the Python API (known issue with
headless pcbnew + zones). Workaround: inject zone S-expressions
directly into the .kicad_pcb text file. Net codes pulled via
pcbnew API; geometry written as raw S-expr.
"""
import os
import re
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB_PATH = os.path.join(HERE, "novapcb-layout-v1.1.kicad_pcb")

PLANE_LAYERS = [
    # (layer_name, net_name) for each inner-layer plane
    ("In1.Cu", "GND"),    # L2
    ("In2.Cu", "+3V3"),   # L3
    ("In3.Cu", "+5V"),    # L4
    ("In4.Cu", "GND"),    # L5
]
# Edge keep-in
EDGE_KEEPIN_MM = 0.3

def _mm(x):
    return int(x * 1_000_000)

def get_board_outline(brd):
    """Read the board outline rectangle from Edge.Cuts."""
    edges = [d for d in brd.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts]
    # Look for the SHAPE_T_RECT
    for e in edges:
        if e.GetShape() == pcbnew.SHAPE_T_RECT:
            s = e.GetStart()
            E = e.GetEnd()
            return (s.x / 1_000_000, s.y / 1_000_000,
                    E.x / 1_000_000, E.y / 1_000_000)
    # Fallback: bbox of edges
    bbox = pcbnew.BOX2I()
    for e in edges:
        bbox.Merge(e.GetBoundingBox())
    return (bbox.GetX() / 1_000_000, bbox.GetY() / 1_000_000,
            (bbox.GetX() + bbox.GetWidth()) / 1_000_000,
            (bbox.GetY() + bbox.GetHeight()) / 1_000_000)


def main():
    print(f"[1/4] load board: {PCB_PATH}")
    brd = pcbnew.LoadBoard(PCB_PATH)

    x_min, y_min, x_max, y_max = get_board_outline(brd)
    print(f"      outline: ({x_min:.2f}, {y_min:.2f}) → ({x_max:.2f}, {y_max:.2f}) mm")

    # Shrink by keep-in
    x0, y0 = x_min + EDGE_KEEPIN_MM, y_min + EDGE_KEEPIN_MM
    x1, y1 = x_max - EDGE_KEEPIN_MM, y_max - EDGE_KEEPIN_MM
    print(f"      zone polygon: ({x0:.2f}, {y0:.2f}) → ({x1:.2f}, {y1:.2f}) mm (edge keep-in {EDGE_KEEPIN_MM} mm)")

    # Look up nets — KiCad returns wxString keys; map to plain strings.
    raw_nets = brd.GetNetsByName().asdict()
    nets = {str(k): v for k, v in raw_nets.items()}

    # Remove any existing zones first (in case re-run)
    existing_zones = list(brd.Zones())
    if existing_zones:
        print(f"[2/4] remove {len(existing_zones)} existing zones (re-run cleanup)")
        for z in existing_zones:
            brd.Remove(z)

    # Collect (layer_name, net_name, net_code) per plane
    plane_specs = []
    for layer_name, net_name in PLANE_LAYERS:
        net = nets.get(net_name)
        if net is None:
            print(f"      !! net '{net_name}' not found; skipping {layer_name}")
            continue
        plane_specs.append((layer_name, net_name, net.GetNetCode()))
        print(f"      plane: {layer_name} ← {net_name} (net code {net.GetNetCode()})")

    print(f"[3/4] inject zone S-expressions directly into .kicad_pcb")

    # Read current file
    with open(PCB_PATH) as f:
        content = f.read()

    # Build zone blocks
    zone_blocks = []
    import uuid
    for layer_name, net_name, net_code in plane_specs:
        zid = str(uuid.uuid4())
        # KiCad 9 zone format
        block = f"""	(zone
		(net {net_code})
		(net_name "{net_name}")
		(layer "{layer_name}")
		(uuid "{zid}")
		(hatch edge 0.5)
		(connect_pads
			(clearance 0.5)
		)
		(min_thickness 0.25)
		(filled_areas_thickness no)
		(fill yes
			(thermal_gap 0.5)
			(thermal_bridge_width 0.5)
		)
		(polygon
			(pts
				(xy {x0:.4f} {y0:.4f}) (xy {x1:.4f} {y0:.4f}) (xy {x1:.4f} {y1:.4f}) (xy {x0:.4f} {y1:.4f})
			)
		)
	)
"""
        zone_blocks.append(block)
    zones_text = "".join(zone_blocks)

    # Inject zones BEFORE the TOP-LEVEL `(embedded_fonts no)` line (which is
    # the LAST occurrence; each footprint also contains the same string).
    marker = "\t(embedded_fonts no)"
    last_idx = content.rfind(marker)
    if last_idx == -1:
        print(f"      !! could not find embedded_fonts marker; aborting")
        return
    injected = content[:last_idx] + zones_text + content[last_idx:]

    print(f"[4/4] write {PCB_PATH}")
    with open(PCB_PATH, "w") as f:
        f.write(injected)
    print(f"      saved: {PCB_PATH} ({os.path.getsize(PCB_PATH)} bytes)")

    # Verify by reloading
    brd2 = pcbnew.LoadBoard(PCB_PATH)
    zones = list(brd2.Zones())
    print(f"      zones loaded: {len(zones)}")
    for z in zones:
        print(f"        {z.GetLayerName()}: net={z.GetNetname()}")


if __name__ == "__main__":
    main()
