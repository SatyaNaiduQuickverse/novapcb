#!/usr/bin/env python3
"""Apply Option B (master 2026-05-23) footprint changes to
novapcb-stepwise.kicad_pcb:

  1. Swap U2's footprint: SOT-23-5 (AP2112K LDO) → DFN-10-1EP_3x3
     (TPS62177DQC buck). Same reference, same position; old 5 pads
     destroyed, new 15 pads (10 numbered + 4 EP-subdivision + 1 EP)
     created with pad-net assignments from novapcb.net.
  2. Add L1 (Inductor_SMD:L_Coilcraft_XAL4020-XXX) — XAL4020-2R2
     shielded power inductor. Net assignments: pin 1 = U2_SW,
     pin 2 = +3V3.
  3. Add R47 (Resistor_SMD:R_0402_1005Metric, value 562k) — FB
     divider top. Pin 1 = +3V3, pin 2 = U2_FB.
  4. Add R48 (Resistor_SMD:R_0402_1005Metric, value 180k) — FB
     divider bot. Pin 1 = U2_FB, pin 2 = GND.

After this script: step5_place_B.py re-runs idempotently and parks
+ re-places U2, L1, R47, R48 at the buck-discipline anchors.
"""
import os
import re
import sys
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")
NET = os.path.join(HERE, "..", "novapcb", "novapcb.net")

PARK_X = 130.0  # off-board park position so step5 can re-park
PARK_Y_BASE = 5.0

NEW_PARTS = {
    # ref: (lib_path, footprint_name, value, park_y_offset)
    "U2":  ("/usr/share/kicad/footprints/Package_DFN_QFN.pretty",
            "DFN-10-1EP_3x3mm_P0.5mm_EP1.58x2.35mm",
            "TPS62177DQC", 0.0),
    "L1":  ("/usr/share/kicad/footprints/Inductor_SMD.pretty",
            "L_Coilcraft_XAL4020-XXX",
            "2.2uH XAL4020", 5.0),
    "R47": ("/usr/share/kicad/footprints/Resistor_SMD.pretty",
            "R_0402_1005Metric",
            "562k", 10.0),
    "R48": ("/usr/share/kicad/footprints/Resistor_SMD.pretty",
            "R_0402_1005Metric",
            "180k", 12.0),
    # C31..C34 — Option B buck Cin/Cout topology (replaces AP2112K-era
    # values). Old on-board state was C31/C33 = 0402 1uF, C32/C34 = 0805
    # 4.7uF. New per TI SLVSC73 §10: C31 = 0805 10µF (Cin bulk),
    # C32 = 0402 100nF (Cin HF), C33 = 0805 22µF (Cout bulk),
    # C34 = 0402 100nF (Cout HF). Footprint swaps required to match
    # netlist; pad-net assignments stay (pin 1 = + side, pin 2 = GND).
    "C31": ("/usr/share/kicad/footprints/Capacitor_SMD.pretty",
            "C_0805_2012Metric",
            "10uF", 14.0),
    "C32": ("/usr/share/kicad/footprints/Capacitor_SMD.pretty",
            "C_0402_1005Metric",
            "100nF", 16.0),
    "C33": ("/usr/share/kicad/footprints/Capacitor_SMD.pretty",
            "C_0805_2012Metric",
            "22uF", 18.0),
    "C34": ("/usr/share/kicad/footprints/Capacitor_SMD.pretty",
            "C_0402_1005Metric",
            "100nF", 20.0),
}


def parse_netlist_nets(net_path, ref_filter):
    """Parse the .net S-expression and return {ref: {pin: net_name}}."""
    with open(net_path) as f:
        text = f.read()
    out = {ref: {} for ref in ref_filter}
    for m in re.finditer(
            r'\(net\s+\(code \"?\d+\"?\)\s+\(name \"?([^\"\)]+)\"?\)(.*?)(?=\(net\s+\(code|\Z)',
            text, re.DOTALL):
        net_name = m.group(1).strip()
        body = m.group(2)
        for n in re.finditer(
                r'\(node\s+\(ref \"?(\w+)\"?\)\s+\(pin \"?(\w+)\"?\)', body):
            ref, pin = n.groups()
            if ref in out:
                out[ref][pin] = net_name
    return out


def ensure_net(brd, name):
    n = brd.FindNet(name)
    if n is None:
        n = pcbnew.NETINFO_ITEM(brd, name)
        brd.Add(n)
        print(f"    + created missing net '{name}'")
    return n


def apply_pad_nets(brd, fp, ref, mapping):
    """Apply netlist pin→net mapping to footprint pads. EP/unnamed pads
    auto-routed to GND (matches TPS62177 EP-to-GND requirement and is
    correct for inductor/resistor 0-pad cases since those have none)."""
    n_gnd = brd.FindNet("GND")
    if n_gnd is None:
        raise RuntimeError("GND net missing")
    assigned = 0
    ep_to_gnd = 0
    for pad in fp.Pads():
        name = pad.GetPadName()
        if name in mapping:
            net_name = mapping[name]
            net = ensure_net(brd, net_name)
            pad.SetNet(net)
            assigned += 1
        elif name == "" or (name.isdigit() and int(name) == 11 and ref == "U2"):
            # Pad 11 on DFN-10 = thermal EP, must go to GND.
            # Empty-name pads (EP subdivisions) → also GND.
            pad.SetNet(n_gnd)
            ep_to_gnd += 1
        else:
            # E.g. pad numbers in netlist but absent in physical fp (rare)
            pass
    print(f"    {ref}: {assigned} pads assigned, {ep_to_gnd} EP→GND")


def remove_footprint(brd, ref):
    for fp in list(brd.GetFootprints()):
        if fp.GetReference() == ref:
            brd.Remove(fp)
            return True
    return False


def add_footprint(brd, lib_path, fp_name, ref, value, x_mm, y_mm):
    fp = pcbnew.FootprintLoad(lib_path, fp_name)
    if fp is None:
        raise RuntimeError(f"FootprintLoad failed for {lib_path}:{fp_name}")
    fp.SetReference(ref)
    fp.SetValue(value)
    fp.SetPosition(pcbnew.VECTOR2I(int(x_mm * 1_000_000), int(y_mm * 1_000_000)))
    brd.Add(fp)
    return fp


def phase_add(mappings):
    """Phase 1 — pre-load + add footprints to board. Runs in its own process
    to keep the SWIG plugin wrapper state clean for FootprintLoad."""
    print("=== Phase 1: pre-load footprints + add to board ===\n")
    print("  pre-loading footprints (KiCad 9 SWIG workaround)...")
    preloaded = {}
    for ref, (lib, fp_name, _value, _y_off) in NEW_PARTS.items():
        fp = pcbnew.FootprintLoad(lib, fp_name)
        if fp is None:
            raise RuntimeError(f"FootprintLoad failed for {lib}:{fp_name}")
        preloaded[ref] = fp
        print(f"    pre-loaded {ref}: {fp_name} ({len(list(fp.Pads()))} pads)")

    brd = pcbnew.LoadBoard(PCB)

    # Remove every ref we're re-adding (idempotent over re-runs).
    # SWIG: must iterate GetFootprints() ONCE — repeated calls after
    # any board mutation corrupt the proxy.
    targets = set(NEW_PARTS.keys())
    to_remove = [f for f in brd.GetFootprints() if f.GetReference() in targets]
    for fp in to_remove:
        ref = fp.GetReference()
        brd.Remove(fp)
        print(f"  removed old {ref}")

    for net_name in ("+3V3", "+5V", "GND", "U2_SW", "U2_FB"):
        ensure_net(brd, net_name)

    for ref, (_lib, _fp_name, value, y_off) in NEW_PARTS.items():
        fp = preloaded[ref]
        fp.SetReference(ref)
        fp.SetValue(value)
        fp.SetPosition(pcbnew.VECTOR2I(int(PARK_X * 1_000_000),
                                       int((PARK_Y_BASE + y_off) * 1_000_000)))
        brd.Add(fp)
        print(f"  added {ref}: {_fp_name}")

    pcbnew.SaveBoard(PCB, brd)
    print(f"\n  Phase 1 saved {PCB}\n")
    return 0


def phase_nets(mappings):
    """Phase 2 — apply pad-net assignments to the freshly-added footprints.
    Runs in a separate process so brd.GetFootprints() returns proper
    wrappers (not SwigPyObjects)."""
    print("=== Phase 2: apply pad-net assignments ===\n")
    brd = pcbnew.LoadBoard(PCB)
    for ref in NEW_PARTS:
        fp_on_board = None
        for f in brd.GetFootprints():
            if f.GetReference() == ref:
                fp_on_board = f
                break
        if fp_on_board is None:
            raise RuntimeError(f"{ref} not found in board after phase 1")
        apply_pad_nets(brd, fp_on_board, ref, mappings[ref])
    pcbnew.SaveBoard(PCB, brd)
    print(f"\n  Phase 2 saved {PCB}\n")

    print("=== POST-PATCH VERIFICATION ===")
    brd2 = pcbnew.LoadBoard(PCB)
    fail = False
    for ref in NEW_PARTS:
        fp = next((f for f in brd2.GetFootprints() if f.GetReference() == ref), None)
        if fp is None:
            print(f"  FAIL: {ref} not in board")
            fail = True
            continue
        fpid = fp.GetFPID()
        pads = list(fp.Pads())
        empty = sum(1 for p in pads if not p.GetNetname())
        print(f"  {ref}: fp={fpid.GetLibItemName()} pads={len(pads)} empty-nets={empty}")
        if empty > 0:
            for p in pads:
                if not p.GetNetname():
                    print(f"    UNASSIGNED pad: name='{p.GetPadName()}'")
    return 1 if fail else 0


def main():
    print("=== Option B footprint patch (U2 swap + L1/R47/R48 add) ===\n")
    print(f"Source netlist: {NET}")
    print(f"Target PCB:     {PCB}\n")

    mappings = parse_netlist_nets(NET, set(NEW_PARTS.keys()))
    for ref, m in mappings.items():
        print(f"  {ref} net mapping ({len(m)} pins): " +
              ", ".join(f"{p}={n}" for p, n in sorted(
                  m.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 99)))
    print()

    phase = sys.argv[1] if len(sys.argv) > 1 else "all"
    if phase == "add":
        return phase_add(mappings)
    if phase == "nets":
        return phase_nets(mappings)
    if phase == "all":
        # Run phase 2 as a subprocess to escape the SWIG-contaminated state.
        import subprocess
        rc = phase_add(mappings)
        if rc != 0:
            return rc
        rc = subprocess.call([sys.executable, __file__, "nets"])
        return rc
    print(f"unknown phase: {phase}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
