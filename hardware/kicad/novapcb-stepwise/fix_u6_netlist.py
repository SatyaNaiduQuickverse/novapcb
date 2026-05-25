#!/usr/bin/env python3
"""Apply U6 (TPS25940A eFuse) pad net assignments from the SKiDL netlist
to novapcb-stepwise.kicad_pcb.

CORRECTIVE FIX per master 2026-05-23: U6 pads in novapcb-stepwise.kicad_pcb
are all on net code 0 (empty). The SKiDL source (hardware/kicad/novapcb/
sheets/power_3b.py:209) DOES assign nets to U6 pins 1-20, and the
generated novapcb.net file has the correct mapping. But the .kicad_pcb
was built at a stage where U6 pads were not patched in. Without these
assignments, the +5V_BEC → U6 → +5V chain is broken and the board does
not power up.

This script:
  1. Parses hardware/kicad/novapcb/novapcb.net for U6 pin-net mappings.
  2. For each U6 pad in novapcb-stepwise.kicad_pcb, looks up the net by
     pad name and applies it via pad.SetNet(brd.FindNet(net_name)).
  3. Pad 21 (thermal exposed pad, EP) is left on the GND net by
     convention (matches TPS25940A datasheet — EP must connect to GND
     for thermal dissipation + IC reference).
  4. The 4 unnamed pads (footprint EP subdivisions) get GND too.

Verification: re-list U6 pad nets after the patch — all 25 pads should
have a non-empty net.
"""
import os
import re
import sys
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")
NET = os.path.join(HERE, "..", "novapcb", "novapcb.net")


def parse_u6_nets(net_path):
    """Parse the .net S-expression for U6 pin → net mappings."""
    with open(net_path) as f:
        text = f.read()
    mapping = {}
    # Each (net (code N) (name STRING) ...nodes...) block
    for m in re.finditer(
            r'\(net\s+\(code \"?\d+\"?\)\s+\(name \"?([^\"\)]+)\"?\)(.*?)(?=\(net\s+\(code|\Z)',
            text, re.DOTALL):
        net_name = m.group(1).strip()
        body = m.group(2)
        for n in re.finditer(
                r'\(node\s+\(ref \"?(\w+)\"?\)\s+\(pin \"?(\w+)\"?\)', body):
            ref, pin = n.groups()
            if ref == "U6":
                mapping[pin] = net_name
    return mapping


def main():
    print("=== U6 netlist patch ===\n")
    print(f"Source: {NET}")
    print(f"Target: {PCB}\n")

    u6_mapping = parse_u6_nets(NET)
    print(f"U6 pin→net mapping from .net file: {len(u6_mapping)} pins")
    for pin, net in sorted(u6_mapping.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0):
        print(f"  pin {pin}: {net}")

    brd = pcbnew.LoadBoard(PCB)

    # Find U6 footprint
    u6 = None
    for fp in brd.GetFootprints():
        if fp.GetReference() == "U6":
            u6 = fp; break
    if u6 is None:
        print("\nERROR: U6 not found in .kicad_pcb"); return 1

    print(f"\nU6 footprint at ({u6.GetPosition().x/1e6:.2f}, {u6.GetPosition().y/1e6:.2f})")

    # Apply nets
    n_gnd = brd.FindNet("GND")
    if n_gnd is None:
        print("ERROR: GND net not found"); return 1

    # Ensure all U6 nets exist in the board — create missing ones
    # (EFUSE_IMON is in the netlist but wasn't added to the .kicad_pcb
    # initially because it's a test-point net with no other consumers.)
    for net_name in set(u6_mapping.values()):
        if brd.FindNet(net_name) is None:
            print(f"  creating missing net: {net_name}")
            new_net = pcbnew.NETINFO_ITEM(brd, net_name)
            brd.Add(new_net)

    patched = 0
    skipped = 0
    ep_assigned = 0
    for pad in u6.Pads():
        name = pad.GetPadName()
        if name in u6_mapping:
            net_name = u6_mapping[name]
            net = brd.FindNet(net_name)
            if net is None:
                print(f"  WARN: pad {name}: net '{net_name}' not in board")
                skipped += 1
                continue
            pad.SetNet(net)
            print(f"  pad {name}: assigned net '{net_name}'")
            patched += 1
        elif name == "21" or name == "":
            # Thermal pad (pad 21 + 4 subdivision pads) → GND per
            # TPS25940A datasheet (page 1: EP "must connect to GND")
            pad.SetNet(n_gnd)
            ep_assigned += 1
        else:
            print(f"  pad {name}: not in mapping, skipped")
            skipped += 1

    print(f"\n  {patched} pads net-assigned from netlist")
    print(f"  {ep_assigned} thermal/EP pads assigned to GND")
    print(f"  {skipped} pads skipped")

    pcbnew.SaveBoard(PCB, brd)
    print(f"\n  Saved {PCB}")

    # Verify
    print(f"\n=== POST-PATCH VERIFICATION ===")
    brd2 = pcbnew.LoadBoard(PCB)
    for fp in brd2.GetFootprints():
        if fp.GetReference() == "U6":
            empty = 0
            for pad in fp.Pads():
                if not pad.GetNetname():
                    empty += 1
            print(f"  U6 pads with empty net AFTER patch: {empty}")
            if empty > 0:
                print(f"  FAIL: still has unassigned pads")
                return 1
            print(f"  PASS: all U6 pads have nets")
    return 0


if __name__ == "__main__":
    sys.exit(main())
