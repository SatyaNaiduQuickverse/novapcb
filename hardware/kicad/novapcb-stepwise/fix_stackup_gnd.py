#!/usr/bin/env python3
"""Stackup fix v3 — text-edit + post-process refill.

KiCad 9 SWIG ZONE creation segfaults at SaveBoard. Workaround:
1. Edit .kicad_pcb S-expression text directly:
   - Re-net In4.Cu +3V3 zones to GND (text substitution)
   - Insert 2 In1.Cu GND zone blocks (template from In3 +3V3 zone +
     full-board outline + cleared filled_polygon for re-fill)
2. Load board in pcbnew (no SWIG creation), refill all zones, save
   (refill works fine, only creation segfaults)
"""
import os
import re
import sys
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")

# Full-board outline minus edge clearance 0.5mm (JLC DFM)
ZONE_OUTLINE_PTS = "(xy 0.5 0.5) (xy 104.5 0.5) (xy 104.5 84.5) (xy 0.5 84.5)"

# Full-board GND zone template (S-expression). Used for both In1.Cu
# (primary GND) and In4.Cu (secondary GND) per master 2026-05-23:
# "Same outline for In1.Cu GND (primary) and In4.Cu GND (secondary).
# Symmetric coverage = symmetric return current paths = clean EMC."
GND_ZONE_TEMPLATE = """\t(zone
\t\t(net 29)
\t\t(net_name "GND")
\t\t(layer "{layer}")
\t\t(uuid "{uuid}")
\t\t(hatch edge 0.5)
\t\t(connect_pads
\t\t\t(clearance 0.5)
\t\t)
\t\t(min_thickness 0.25)
\t\t(filled_areas_thickness no)
\t\t(fill yes
\t\t\t(thermal_gap 0.5)
\t\t\t(thermal_bridge_width 0.5)
\t\t)
\t\t(polygon
\t\t\t(pts
\t\t\t\t{outline}
\t\t\t)
\t\t)
\t)
"""

NEW_UUIDS = {
    "In1.Cu": "a1b2c3d4-0000-4000-8000-00000000in01",
    "In4.Cu": "a1b2c3d4-0000-4000-8000-00000000in04",
}


def find_zone_block(text, layer_pattern, net_name_pattern):
    """Walk parens to find a top-level (zone ...) block whose body contains
    matching layer and net_name. Returns (start, end) offsets or None."""
    i = 0
    while True:
        m = re.search(r'\n\t\(zone\b', text[i:])
        if not m:
            return None
        start = i + m.start() + 1  # skip leading \n
        depth = 0; k = start
        while k < len(text):
            if text[k] == '(': depth += 1
            elif text[k] == ')':
                depth -= 1
                if depth == 0:
                    k += 1; break
            k += 1
        block = text[start:k]
        if re.search(layer_pattern, block) and re.search(net_name_pattern, block):
            return (start, k)
        i = k


def main():
    print("=== Stackup fix v3 — text-edit + refill ===", flush=True)
    with open(PCB) as f:
        text = f.read()

    # Step 1: Remove all existing In4.Cu +3V3 zones (will be replaced by
    # 1 full-board In4.Cu GND zone matching In1.Cu — symmetric coverage).
    print("\n--- Step 1: remove In4.Cu +3V3 zones (old sub-rect outline) ---", flush=True)
    n_in4_removed = 0
    while True:
        blk = find_zone_block(text, r'\(layer "In4\.Cu"\)', r'\(net_name "\+3V3"\)')
        if blk is None:
            break
        s, e = blk
        # Also consume the leading \n if present
        if s > 0 and text[s-1] == '\n':
            s -= 1
        text = text[:s] + text[e:]
        n_in4_removed += 1
    print(f"  removed {n_in4_removed} In4.Cu +3V3 zone(s)", flush=True)

    # Step 2: Insert In1.Cu + In4.Cu GND zones (both full-board outline)
    # Find a good insertion point: just before the closing ) of the (kicad_pcb ...) block,
    # or just after the last (zone ...) block.
    print("\n--- Step 2: insert 2 In1.Cu GND zones ---", flush=True)
    # Find last (zone ...) end
    last_zone_end = 0
    i = 0
    while True:
        m = re.search(r'\n\t\(zone\b', text[i:])
        if not m: break
        s = i + m.start() + 1
        depth = 0; k = s
        while k < len(text):
            if text[k] == '(': depth += 1
            elif text[k] == ')':
                depth -= 1
                if depth == 0: k += 1; break
            k += 1
        last_zone_end = k
        i = k
    if last_zone_end == 0:
        print("ERROR: no existing zones found to anchor insertion")
        return 1
    # Insert 1 zone per GND layer (In1.Cu primary + In4.Cu secondary).
    # Both full-board outline → symmetric GND coverage.
    new_zones = "\n" + GND_ZONE_TEMPLATE.format(
        layer="In1.Cu", uuid=NEW_UUIDS["In1.Cu"], outline=ZONE_OUTLINE_PTS)
    new_zones += "\n" + GND_ZONE_TEMPLATE.format(
        layer="In4.Cu", uuid=NEW_UUIDS["In4.Cu"], outline=ZONE_OUTLINE_PTS)
    text = text[:last_zone_end] + new_zones + text[last_zone_end:]
    print(f"  inserted In1.Cu + In4.Cu GND zones at offset {last_zone_end}", flush=True)

    with open(PCB, 'w') as f:
        f.write(text)
    print(f"\nText-edit saved {PCB}", flush=True)

    # Step 3: Load + refill in pcbnew (refill works, only creation segfaults)
    print("\n--- Step 3: load + refill zones (pcbnew, no SWIG create) ---", flush=True)
    brd = pcbnew.LoadBoard(PCB)
    if brd is None:
        print("ERROR: LoadBoard returned None — text edit broke parse")
        return 1
    print(f"  loaded board, zones: {len(list(brd.Zones()))}", flush=True)
    for z in brd.Zones():
        if hasattr(z, "UnFill"):
            z.UnFill()
    filler = pcbnew.ZONE_FILLER(brd)
    filler.Fill(list(brd.Zones()))
    print(f"  refilled {len(list(brd.Zones()))} zones", flush=True)
    pcbnew.SaveBoard(PCB, brd)
    print(f"  saved", flush=True)

    # Verify
    print("\n--- POST-FIX VERIFICATION ---", flush=True)
    brd2 = pcbnew.LoadBoard(PCB)
    by_layer_net = {}
    for z in brd2.Zones():
        k = (brd2.GetLayerName(z.GetLayer()), z.GetNetname())
        a = z.GetFilledArea() / 1e6
        by_layer_net.setdefault(k, []).append(a)
    for (l, n), areas in sorted(by_layer_net.items()):
        total = sum(areas)
        print(f"  {l} \"{n}\": {len(areas)} zone(s), {total:.0f} mm² filled", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
