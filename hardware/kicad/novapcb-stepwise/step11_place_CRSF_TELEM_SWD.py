#!/usr/bin/env python3
"""step11_place_CRSF_TELEM_SWD — place CRSF + TELEM + SWD subsystems.

Per docs/REMAINING_REAL_ESTATE_MAP.md (master signed off all 5 decisions
2026-05-24): TELEM (95, 38), SWD (45, 8) N-middle west, CRSF (54, 8)
N-middle east, BUZZER covered by GPS TP5 (no separate placement).

CRSF J10 footprint sync: SKiDL has JST_GH_SM04B-GHS-TB but board still
has legacy CRSF_solder_pad. 2-phase delete-and-re-add pattern.

Sub-step #87 + master's bundled JST-GH amend.
"""
import os, re, sys, subprocess, pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")
NET_PATH = os.path.join(HERE, "..", "novapcb", "novapcb.net")

J10_FP_LIB = "/usr/share/kicad/footprints/Connector_JST.pretty"
J10_FP_NAME = "JST_GH_SM04B-GHS-TB_1x04-1MP_P1.25mm_Horizontal"

PLACEMENTS = [
    # CRSF connector — N-middle east per real-estate map (master 2026-05-24)
    ("J10",  54.0,  8.0,  0.0),   # JST-GH 4P (re-added with correct footprint)
    # CRSF ESD TVS — south of J10
    ("D13",  51.0, 14.0,  0.0),   # USART6_TX ESD
    ("D14",  53.0, 14.0,  0.0),   # USART6_RX ESD
    # TELEM connector — E-mid Y=38 gap between USB-C (Y=24-36) + microSD (Y=58+)
    ("J3",   95.0, 38.0,  0.0),   # JST-GH 6P TELEM
    # TELEM ESDs — moved SOUTH of J3 (Y>40) to clear pre-existing GND
    # stitching vias at (88,32) (88,37) (90,40) plus USART1_TX via at (93,37).
    # Iter-1 placed at (88, 37/39) collided with these vias.
    ("D11",  92.0, 43.0,  0.0),   # USART1_TX ESD — south of J3.MP at (90.03, 39.35)
    ("D12",  94.0, 43.0,  0.0),   # USART1_RX ESD
    # SWD connector — N-middle west per real-estate map
    ("J9",   45.0,  8.0,  0.0),   # 2x05 PinHeader vertical SMD
]


def find_or_create_net(brd, name):
    n = brd.FindNet(name)
    if n is None:
        n = pcbnew.NETINFO_ITEM(brd, name)
        brd.Add(n)
    return n


def parse_netlist_pin_nets(text, ref):
    out = {}
    for m in re.finditer(r'\(net\s+\(code "?\d+"?\)\s+\(name "?([^"\)]+)"?\)(.*?)(?=\(net\s+\(code|\Z)',
                         text, re.DOTALL):
        for n in re.finditer(r'\(node\s+\(ref "?(\w+)"?\)\s+\(pin "?(\w+)"?\)', m.group(2)):
            if n.group(1) == ref:
                out[n.group(2)] = m.group(1).strip()
    return out


def add_j10():
    """Phase 1: Replace J10 (CRSF_solder_pad → JST_GH_SM04B-GHS-TB).
    Pre-load footprint, remove old J10, add new J10 with same ref."""
    print("=== Phase 1: J10 footprint swap (CRSF_solder_pad → JST-GH 4P) ===")
    fp = pcbnew.FootprintLoad(J10_FP_LIB, J10_FP_NAME)
    if fp is None:
        raise RuntimeError(f"FootprintLoad {J10_FP_LIB}:{J10_FP_NAME} failed")
    fp.SetReference("J10")
    fp.SetValue("CRSF_4P")
    fp.SetPosition(pcbnew.VECTOR2I(int(125e6), int(3e6)))  # park before final placement

    brd = pcbnew.LoadBoard(PCB)
    for old in list(brd.GetFootprints()):
        if old.GetReference() == "J10":
            brd.Remove(old)
            print(f"  removed old J10 ({old.GetFPID().GetLibItemName()})")
    brd.Add(fp)
    print(f"  added new J10 ({J10_FP_NAME})")
    pcbnew.SaveBoard(PCB, brd)


def apply_j10_nets_and_place_all():
    """Phase 2: J10 nets from netlist + place all CRSF/TELEM/SWD parts."""
    print("\n=== Phase 2: J10 net assignment + all placement ===")
    with open(NET_PATH) as f:
        text = f.read()
    j10_map = parse_netlist_pin_nets(text, "J10")
    print(f"  J10 nets from netlist: {j10_map}")

    brd = pcbnew.LoadBoard(PCB)
    j10 = next((f for f in brd.GetFootprints() if f.GetReference()=="J10"), None)
    if j10 is None:
        raise RuntimeError("J10 missing after Phase 1")
    for pad in j10.Pads():
        nm = pad.GetPadName()
        if nm in j10_map:
            pad.SetNet(find_or_create_net(brd, j10_map[nm]))

    # Final placements
    print()
    for ref, x, y, rot in PLACEMENTS:
        fp = next((f for f in brd.GetFootprints() if f.GetReference()==ref), None)
        if fp is None:
            print(f"  !!! {ref}: not found"); continue
        fp.SetPosition(pcbnew.VECTOR2I(int(x*1e6), int(y*1e6)))
        fp.SetOrientationDegrees(rot)
        print(f"  {ref}: @ ({x:.2f}, {y:.2f}) rot={rot}°")

    for z in brd.Zones():
        if hasattr(z, "UnFill"): z.UnFill()
    pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
    pcbnew.SaveBoard(PCB, brd)
    print(f"\n  saved {PCB}\n")


def main():
    phase = sys.argv[1] if len(sys.argv) > 1 else "all"
    if phase == "all":
        for ph in ("add", "place"):
            r = subprocess.run([sys.executable, __file__, ph], check=False)
            if r.returncode != 0: raise SystemExit(r.returncode)
    elif phase == "add":
        add_j10()
    elif phase == "place":
        apply_j10_nets_and_place_all()


if __name__ == "__main__":
    sys.exit(main() or 0)
