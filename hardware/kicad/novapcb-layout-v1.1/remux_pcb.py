#!/usr/bin/env python3
"""PCB-level pin re-mux on U1 (master 2026-05-22 directive).

Swaps net assignments on U1 pads to move:
  - SPI1_MOSI N → S
  - SPI3 (SCK/MISO/MOSI) N → S
  - I2C1 (SCL/SDA) N → S
  - GPS1 (TX/RX) N → E
  - 8× MOT → N
  - HEATER_PWM off PA7 (pin 31) since SPI1_MOSI lands there

This is a PCB-level netlist change (pad-net swap). Schematic is NOT
edited (project is PCB-only — no .kicad_sch files exist).

AF VERIFICATION TODO: every new pin assignment must match DS12110
Table 11 LQFP-100 column. Some swaps are clearly valid (PA7=SPI1_MOSI
AF5); others (e.g. MOT outputs to N-side PE pins) need timer-channel
verification. This script does the position swap; AF validation is
a separate pass that requires the datasheet.
"""
import os
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-layout-v1.1.kicad_pcb")

# Re-mux: pin number → new net name
# (Existing nets being moved swap with target pin's existing assignment)
# Format: (old_pin, new_pin, net_name_being_moved)
SWAPS = [
    # SPI1_MOSI: pin 88 (N) → pin 31 (PA7 S, was HEATER_PWM)
    (88, 31, "SPI1_MOSI"),
    # HEATER_PWM lands at pin 88 (N) — relocate later if needed; OK for routability test
    # (HEATER_PWM now on N side, near ESC pads — acceptable; needs timer-capable AF)

    # SPI3 N → S (swap into free or relocatable S-side pins)
    # Pin 89 SPI3_SCK → pin 28 (PA4)
    # Pin 90 SPI3_MISO → pin 32 (PC4)
    # Pin 91 SPI3_MOSI → pin 33 (PC5)
    (89, 28, "SPI3_SCK"),
    (90, 32, "SPI3_MISO"),
    (91, 33, "SPI3_MOSI"),

    # I2C1 N → S
    # Pin 92 I2C1_SCL → pin 36 (PB2)
    # Pin 93 I2C1_SDA → pin 37 (PE7)
    (92, 36, "I2C1_SCL"),
    (93, 37, "I2C1_SDA"),

    # GPS1 N → E
    # Pin 86 GPS1_TX → pin 57 (E-side, likely PD8 or similar)
    # Pin 87 GPS1_RX → pin 58
    (86, 57, "GPS1_TX"),
    (87, 58, "GPS1_RX"),

    # 8× MOT → N
    # Currently:
    #   MOT1 pin 34 (PB0 S), MOT2 pin 35 (PB1 S)
    #   MOT3 pin 22 (PA0 W), MOT4 pin 23 (PA1 W)
    #   MOT5 pin 24 (PA2 W), MOT6 pin 25 (PA3 W)
    #   MOT7 pin 59 (E),     MOT8 pin 60 (E)
    # Move all to N side. Use newly-freed N pins 86/87/89/90/91/92/93 (7 freed
    # by GPS1+SPI3+I2C1 moves above) + pin 95 (free)
    (34, 86, "MOT1"),
    (35, 87, "MOT2"),
    (22, 89, "MOT3"),
    (23, 90, "MOT4"),
    (24, 91, "MOT5"),
    (25, 92, "MOT6"),
    (59, 93, "MOT7"),
    (60, 95, "MOT8"),
]


def main():
    brd = pcbnew.LoadBoard(PCB)
    u1 = None
    for fp in brd.GetFootprints():
        if fp.GetReference() == "U1": u1 = fp; break
    if not u1:
        print("U1 not found"); return

    # Build pin → pad map for U1
    pin_pad = {}
    for p in u1.Pads():
        pn = p.GetNumber()
        if pn.isdigit():
            pin_pad[int(pn)] = p
    print(f"U1 has {len(pin_pad)} numbered pads")

    # Apply swaps: for each (old_pin, new_pin, net):
    # - Get target pad's current net
    # - Move net to target pad
    # - Move target's old net to source pad
    nets = {str(k): v for k, v in brd.GetNetsByName().asdict().items()}
    log = []
    for old_pin, new_pin, net_name in SWAPS:
        p_old = pin_pad.get(old_pin)
        p_new = pin_pad.get(new_pin)
        if not p_old or not p_new:
            print(f"  {net_name}: pin {old_pin} or {new_pin} not found"); continue
        old_net = p_old.GetNetname()
        new_net_existing = p_new.GetNetname()
        if old_net != net_name:
            print(f"  {net_name}: WARN pin {old_pin} has '{old_net}' not '{net_name}'")
        # Swap nets
        net_obj_old = p_old.GetNet()
        net_obj_new = p_new.GetNet()
        p_old.SetNet(net_obj_new)
        p_new.SetNet(net_obj_old)
        log.append((old_pin, new_pin, net_name, new_net_existing))
        print(f"  pin {old_pin} ({old_net}) ↔ pin {new_pin} ({new_net_existing})")

    pcbnew.SaveBoard(PCB, brd)
    print(f"\n[saved] {len(log)} swaps applied")

    # Verify: count pins per side after re-mux
    cx, cy = u1.GetPosition().x/1e6, u1.GetPosition().y/1e6
    sides = {"N":0, "E":0, "S":0, "W":0}
    func_sides = {"N":[], "E":[], "S":[], "W":[]}
    for pn, pad in pin_pad.items():
        pos = pad.GetPosition()
        dx, dy = pos.x/1e6 - cx, pos.y/1e6 - cy
        side = ("E" if dx>0 else "W") if abs(dx)>abs(dy) else ("S" if dy>0 else "N")
        net = pad.GetNetname()
        if net:
            sides[side] += 1
            if net not in ("GND","+3V3","+5V","VDDA","VBAT","VCAP1","VCAP2","+3V3A","VREF_P"):
                func_sides[side].append((pn, net))
    print(f"\n[verify] Pin counts per side (functional+power): {sides}")
    print(f"  N functional: {len(func_sides['N'])} pins")
    print(f"  E functional: {len(func_sides['E'])} pins")
    print(f"  S functional: {len(func_sides['S'])} pins")
    print(f"  W functional: {len(func_sides['W'])} pins")


if __name__ == "__main__":
    main()
