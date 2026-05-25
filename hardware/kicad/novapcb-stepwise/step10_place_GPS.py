#!/usr/bin/env python3
"""step10_place_GPS — place GPS+MAG+BUZZER subsystem.

Per docs/GPS_PLACEMENT_ANALYSIS.md (master signed off 3 decisions
+ test pads 2026-05-24): NW band placement, J5 at (30, 6), 5x test
pads (TP1-TP5) for SAFETY_SW/LED/GPS_TX/I2C1_SCL/BUZZER bench access.

Two-phase: add TP1-TP5 (new components) → place all.
"""
import os, re, sys, subprocess, pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")
NET_PATH = os.path.join(HERE, "..", "novapcb", "novapcb.net")

TP_LIB = "/usr/share/kicad/footprints/TestPoint.pretty"
TP_NAME = "TestPoint_Pad_D1.5mm"
TP_REFS = ["TP1", "TP2", "TP3", "TP4", "TP5"]

# Placement targets (X, Y in mm)
PLACEMENTS = [
    # GPS connector — SW CORNER (master 2026-05-24 revised from NW after
    # Rule-19 catch: NW band fully occupied by A subsystem + J4).
    # J5 bbox 9.5×17mm at anchor (15, 75): X=10..20 Y=66.5..83.5.
    # H3 mount NPTH at (3.25, 81.75) Φ6 keep-out: J5 nearest corner
    # (10.25, 83.5) → 7.2mm from H3 ✓. Board south edge Y=85 → 1.5mm
    # clear (JLC DFM 0.5mm min ✓).
    ("J5",  15.0, 75.0,   0.0),     # JST-GH 10P horizontal, SW corner
    # TVS array — east of J5, 2mm Y pitch (SOT-723 1.2×0.8 + 0.5mm ctyd)
    ("D5",  24.0, 67.0,   0.0),     # GPS_TX ESD
    ("D6",  24.0, 69.0,   0.0),     # GPS_RX ESD
    ("D7",  24.0, 71.0,   0.0),     # I2C1_SCL ESD
    ("D8",  24.0, 73.0,   0.0),     # I2C1_SDA ESD
    ("D9",  24.0, 75.0,   0.0),     # BUZZER ESD
    # Pull-ups — east of TVS column, near J5 I²C pads
    ("R21", 27.0, 71.0,  90.0),     # I2C1_SDA pull-up 4.7k
    ("R22", 27.0, 73.0,  90.0),     # I2C1_SCL pull-up 4.7k
    # Test pads — Φ1.5mm courtyard 2.55mm — use 3mm pitch
    # Row at Y=62 (north of J5 north edge 66.5, clear)
    ("TP1",  10.0, 62.0,  0.0),     # SAFETY_SW
    ("TP2",  13.0, 62.0,  0.0),     # SAFETY_LED
    ("TP3",  16.0, 62.0,  0.0),     # GPS_TX (test)
    ("TP4",  19.0, 62.0,  0.0),     # I2C1_SCL (test)
    ("TP5",  22.0, 62.0,  0.0),     # BUZZER (test)
]


def find_or_create_net(brd, name):
    n = brd.FindNet(name)
    if n is None:
        n = pcbnew.NETINFO_ITEM(brd, name)
        brd.Add(n)
    return n


def parse_netlist_for_ref(text, ref):
    out = {}
    for m in re.finditer(r'\(net\s+\(code "?\d+"?\)\s+\(name "?([^"\)]+)"?\)(.*?)(?=\(net\s+\(code|\Z)',
                         text, re.DOTALL):
        for n in re.finditer(r'\(node\s+\(ref "?(\w+)"?\)\s+\(pin "?(\w+)"?\)', m.group(2)):
            if n.group(1) == ref:
                out[n.group(2)] = m.group(1).strip()
    return out


def add_test_pads():
    """Phase 1: preload TestPoint footprints + add TP1-5 to board."""
    print("=== Phase 1: add TP1-5 ===")
    preloaded = {}
    for ref in TP_REFS:
        fp = pcbnew.FootprintLoad(TP_LIB, TP_NAME)
        if fp is None:
            raise RuntimeError(f"FootprintLoad failed for {ref}")
        preloaded[ref] = fp
    brd = pcbnew.LoadBoard(PCB)
    # Idempotent: remove existing TP1-5
    for old in list(brd.GetFootprints()):
        if old.GetReference() in TP_REFS:
            brd.Remove(old)
    for ref, fp in preloaded.items():
        fp.SetReference(ref)
        fp.SetValue(f"TP_{ref}")
        # Park at X>100 so net-assignment phase finds them
        fp.SetPosition(pcbnew.VECTOR2I(int(120e6), int((10 + TP_REFS.index(ref)*2)*1e6)))
        brd.Add(fp)
        print(f"  added {ref}")
    pcbnew.SaveBoard(PCB, brd)


def apply_tp_nets():
    """Phase 2: net assignment + final placement of all GPS components."""
    print("\n=== Phase 2: net + placement ===")
    with open(NET_PATH) as f:
        text = f.read()
    brd = pcbnew.LoadBoard(PCB)

    # Assign TP nets from netlist
    for ref in TP_REFS:
        mapping = parse_netlist_for_ref(text, ref)
        fp = next((f for f in brd.GetFootprints() if f.GetReference()==ref), None)
        if fp is None: continue
        for pad in fp.Pads():
            nm = pad.GetPadName()
            if nm in mapping:
                pad.SetNet(find_or_create_net(brd, mapping[nm]))
                print(f"  {ref}.{nm} net = {mapping[nm]}")

    # Place all GPS components
    print()
    for ref, x, y, rot in PLACEMENTS:
        fp = next((f for f in brd.GetFootprints() if f.GetReference()==ref), None)
        if fp is None:
            print(f"  !!! {ref}: not found")
            continue
        fp.SetPosition(pcbnew.VECTOR2I(int(x*1e6), int(y*1e6)))
        fp.SetOrientationDegrees(rot)
        print(f"  {ref}: placed at ({x:.2f}, {y:.2f}) rot={rot}°")

    for z in brd.Zones():
        if hasattr(z, "UnFill"): z.UnFill()
    pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
    pcbnew.SaveBoard(PCB, brd)
    print("\n  saved\n")


def main():
    phase = sys.argv[1] if len(sys.argv) > 1 else "all"
    if phase == "all":
        for ph in ("add", "place"):
            r = subprocess.run([sys.executable, __file__, ph], check=False)
            if r.returncode != 0: raise SystemExit(r.returncode)
    elif phase == "add":
        add_test_pads()
    elif phase == "place":
        apply_tp_nets()


if __name__ == "__main__":
    sys.exit(main() or 0)
