#!/usr/bin/env python3
"""step7_place_H — place H subsystem (ESC outputs).

H = 1× JST-GH 1x10 connector (J11) per PR #80 schematic merge
(Pixhawk 6X FMU PWM OUT pinout). Replaces the obsolete J11..J18
ESC_solder_pad layout from Phase 3f placeholder era.

Placement per docs/H_PLACEMENT_CONSTRAINT_ANALYSIS.md (master signed
off 2026-05-24: D1=a centered X=52.5, D2=a Y=80, D3=a rotation 0°).

Three phases — each a separate subprocess so KiCad-9 SWIG state stays
clean (FootprintLoad regression workaround established in
fix_option_b_footprints.py):
  - "add"  : remove old J11..J18, FootprintLoad + add new J11 at anchor
  - "nets" : assign pin 1..8 → MOT1..8, pin 10 → GND, pin 9 NC
  - "fill" : refill all zones (J11.10 GND pin needs new zone-fill)
"""
import os
import re
import subprocess
import sys
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")
NET = os.path.join(HERE, "..", "novapcb", "novapcb.net")

ANCHOR_XY = (52.5, 80.0)
ROTATION_DEG = 0.0
FP_LIB = "/usr/share/kicad/footprints/Connector_JST.pretty"
FP_NAME = "JST_GH_SM10B-GHS-TB_1x10-1MP_P1.25mm_Horizontal"
REF = "J11"
VALUE = "ESC_OUT"
OLD_REFS = [f"J{n}" for n in range(11, 19)]   # J11..J18


def parse_netlist_nets(net_path, ref):
    """Return {pin_name: net_name} for the given ref."""
    with open(net_path) as f:
        text = f.read()
    out = {}
    for m in re.finditer(
            r'\(net\s+\(code \"?\d+\"?\)\s+\(name \"?([^\"\)]+)\"?\)(.*?)(?=\(net\s+\(code|\Z)',
            text, re.DOTALL):
        net_name = m.group(1).strip()
        for n in re.finditer(
                r'\(node\s+\(ref \"?(\w+)\"?\)\s+\(pin \"?(\w+)\"?\)', m.group(2)):
            r, pin = n.groups()
            if r == ref:
                out[pin] = net_name
    return out


def ensure_net(brd, name):
    n = brd.FindNet(name)
    if n is None:
        n = pcbnew.NETINFO_ITEM(brd, name)
        brd.Add(n)
    return n


def phase_add():
    """Pre-load FP, load board, remove J11..J18, add new J11."""
    print("=== Phase 1: pre-load FP + remove old J11..J18 + add new J11 ===")
    fp = pcbnew.FootprintLoad(FP_LIB, FP_NAME)
    if fp is None:
        raise RuntimeError(f"FootprintLoad failed for {FP_LIB}:{FP_NAME}")
    print(f"  pre-loaded {FP_NAME} ({len(list(fp.Pads()))} pads)")

    brd = pcbnew.LoadBoard(PCB)

    targets = set(OLD_REFS)
    to_remove = [f for f in brd.GetFootprints() if f.GetReference() in targets]
    for old in to_remove:
        ref = old.GetReference()
        brd.Remove(old)
        print(f"  removed old {ref}")

    fp.SetReference(REF)
    fp.SetValue(VALUE)
    fp.SetPosition(pcbnew.VECTOR2I(
        int(ANCHOR_XY[0] * 1_000_000),
        int(ANCHOR_XY[1] * 1_000_000)))
    # Rotation 0° (default); pcbnew uses tenths of a degree internally
    if ROTATION_DEG != 0.0:
        fp.SetOrientationDegrees(ROTATION_DEG)
    brd.Add(fp)
    print(f"  added {REF} at ({ANCHOR_XY[0]}, {ANCHOR_XY[1]}) rot={ROTATION_DEG}°")

    pcbnew.SaveBoard(PCB, brd)
    print(f"  saved {PCB}\n")


def phase_nets():
    """Assign nets to J11 pads from netlist."""
    print("=== Phase 2: apply pad-net assignments to J11 ===")
    mapping = parse_netlist_nets(NET, REF)
    print(f"  netlist mapping: {len(mapping)} pins")
    for pin in sorted(mapping.keys(), key=lambda p: int(p) if p.isdigit() else 99):
        print(f"    pin {pin} = {mapping[pin]}")

    brd = pcbnew.LoadBoard(PCB)
    fp = next((f for f in brd.GetFootprints() if f.GetReference() == REF), None)
    if fp is None:
        raise RuntimeError(f"{REF} not found in board after Phase 1")

    assigned = 0
    unassigned_pads = []
    for pad in fp.Pads():
        name = pad.GetPadName()
        if name in mapping:
            pad.SetNet(ensure_net(brd, mapping[name]))
            assigned += 1
        else:
            # Pin 9 NC (Sai-ratified) — leave unbound. MP mech-post pads
            # have empty names — leave unbound.
            unassigned_pads.append(name or "(MP)")

    print(f"  assigned {assigned} pads")
    print(f"  unassigned (intentional): {unassigned_pads}")

    pcbnew.SaveBoard(PCB, brd)
    print(f"  saved {PCB}\n")


def phase_fill():
    """Refill all zones. J11.10 GND pad needs new zone-fill bind."""
    print("=== Phase 3: refill zones ===")
    brd = pcbnew.LoadBoard(PCB)
    filler = pcbnew.ZONE_FILLER(brd)
    zones = list(brd.Zones())
    print(f"  refilling {len(zones)} zones...")
    filler.Fill(zones)
    pcbnew.SaveBoard(PCB, brd)
    print(f"  saved {PCB}\n")


def main():
    phase = sys.argv[1] if len(sys.argv) > 1 else "all"
    if phase == "add":
        return phase_add()
    if phase == "nets":
        return phase_nets()
    if phase == "fill":
        return phase_fill()
    if phase == "all":
        # Each phase in its own subprocess to keep SWIG state clean.
        for ph in ("add", "nets", "fill"):
            r = subprocess.run([sys.executable, __file__, ph], check=False)
            if r.returncode != 0:
                raise SystemExit(r.returncode)
        return 0
    raise SystemExit(f"unknown phase: {phase}")


if __name__ == "__main__":
    sys.exit(main() or 0)
