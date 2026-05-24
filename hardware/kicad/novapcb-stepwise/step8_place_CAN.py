#!/usr/bin/env python3
"""step8_place_CAN — place CAN subsystem (U14 + U15 + R45 + R46 + C83 + C84 + J20).

Per docs/CAN_PLACEMENT_ANALYSIS.md (master signed off all 4 decisions
2026-05-24): NE corner placement, U14 at (94, 22), J20 at (97, 5),
R45/R46 90° rotation, decap caps near U14 power pins.
"""
import os
import sys
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")

PLACEMENTS = [
    # (ref, x, y, rotation_deg)
    # ITERATION 2 (fixes courtyard + clearance from iter 1):
    # - R45/R46 separated 4mm apart (was 2mm — overlap)
    # - J20 moved W to (95, 8) to clear H2 mount + J19
    # - C83/C84 moved further from U14 to clear pin 1 area
    ("U14", 94.0, 22.0,  0.0),   # TJA1051 transceiver, HVSON-8 EP
    ("U15", 96.0, 27.0,  0.0),   # PESD2CAN TVS SOT-23-3
    ("R45", 99.5, 21.0, 90.0),   # 120Ω termination east of U14
    ("R46", 99.5, 25.0, 90.0),   # 0R jumper south of R45 (4mm apart)
    ("C83", 91.0, 21.5,  0.0),   # U14.VCC decap NW of U14 (clear pin 1)
    ("C84", 91.0, 23.5,  0.0),   # U14.VIO decap SW of U14 (clear pin 5)
    ("J20", 97.0, 11.0,  0.0),   # JST-GH 4P CAN — clear of J19 (right edge ≈95) + H2 keep-out (Y≥9.25)
]


def main():
    print("=== Step 8: place CAN subsystem ===\n")
    brd = pcbnew.LoadBoard(PCB)

    for ref, x, y, rot in PLACEMENTS:
        fp = next((f for f in brd.GetFootprints() if f.GetReference() == ref), None)
        if fp is None:
            print(f"  !!! {ref}: not found, skipping")
            continue
        fp.SetPosition(pcbnew.VECTOR2I(
            int(x * 1_000_000), int(y * 1_000_000)))
        if rot != 0.0:
            fp.SetOrientationDegrees(rot)
        else:
            fp.SetOrientationDegrees(0.0)
        print(f"  {ref}: placed at ({x:.2f}, {y:.2f}) rot={rot}°")

    # Refill zones (in case any GND plane needs new pour around CAN)
    for z in brd.Zones():
        if hasattr(z, "UnFill"): z.UnFill()
    pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))

    pcbnew.SaveBoard(PCB, brd)
    print(f"\n  saved {PCB}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
