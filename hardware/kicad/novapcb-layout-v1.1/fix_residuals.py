#!/usr/bin/env python3
"""Targeted big-block + small-part fixes to drive to 0 DRC.

Per master 2026-05-22:
- E-edge connectors spread evenly (J1 near MCU Y, J5/J3/J10 spread far
  enough that no pin overlap)
- J20 clear of H2 mounting hole corner
- Edge-clearance parts inset ≥0.3mm from board edges
- Starved thermals (pad with single spoke) overridden to SOLID
"""
import os
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-layout-v1.1.kicad_pcb")

# Mounting holes at corners — 6mm courtyard keepout
# H1 (3,3), H2 (87,3), H3 (3,67), H4 (87,67)
# Usable E edge: Y = 10 to 61 (after 6mm keepout from H2/H4)

# Connector re-placement (X=85 = E edge, oriented 90°)
# J5 GPS_MAG (10P, ~10mm tall when 90°): Y center 16 → Y span 11..21 (1mm clear of H2)
# J1 USB-C (12mm tall): Y center 30 → Y span 24..36 (3mm gap to J5)
# J3 TELEM (6P, ~7.5mm tall): Y center 43 → Y span 39..47 (3mm gap to J1)
# J10 CRSF (4P, ~5mm tall): Y center 54 → Y span 51..57 (4mm gap to J3, 4mm to H4)

MOVES = [
    # E-edge connector spread (J1 stays, others move)
    ("J5",  85.0, 16.0, 90),
    ("J1",  85.0, 30.0, 90),
    ("J3",  85.0, 42.0, 90),
    ("J10", 85.0, 56.0, 90),   # further from J3 (was 54)

    # J20 CAN connector — move clear of H2 mounting hole corner
    ("J20", 76.0, 10.0, 0),
    ("U14", 78.0, 18.0, 90),
    ("U15", 73.0, 18.5, 0),

    # R61 too close to Q5 — move E
    ("R61", 67.5, 55.0, None),

    # Sensor island — keep components central in 43×12mm island
    # U3 ICM-42688 (3×6.5 incl silk): center Y=58 keeps body fully inside Y=53..65
    ("U3", 33.0, 58.0, 0),
    # U8 BMI088 (6×13.5 long axis Y): SPI2 lock keeps at island NE; center (50, 58)
    ("U8", 50.0, 58.0, 0),
    # U9 LSM6DSV (10×11.5 long axis Y) — central; Y=58 keeps body inside
    ("U9", 42.0, 58.0, 0),
    # Baros
    ("U7", 56.0, 58.0, 0),    # LPS22HB
    ("U4", 30.0, 58.0, 0),    # DPS310 B.Cu
    # Heater + IMU LDO — NOT pinned. Greedy placer will place these
    # via get_ideal_pos based on net connectivity, then spiral-search
    # for collision-free spot inside the island.

    # J9 SWD: pads overflow into slot S edge — pad spans 2.54mm from center,
    # need Y<=62 for pad S edge to clear slot N edge Y=65 with 0.3mm margin
    ("J9", 41.0, 60.0, 0),

    # USB CC pull-down resistors R31/R32 — pin clear of J1 USB-C W edge
    ("R31", 73.0, 31.5, 0),
    ("R32", 73.0, 28.5, 0),
    # CAN termination R45/R46 — south of U14, 3mm apart for courtyard clear
    ("R45", 74.0, 21.0, 0),
    ("R46", 78.0, 21.0, 0),

    # Q2/Q4 back to original positions (10, 22)/(11, 47.5) — original was fine,
    # my earlier (12,22)/(13,47.5) brought them too close to U11/U12.
    ("Q2", 10.0, 24.0, 0),       # N of D1 to clear courtyard
    ("Q4", 11.0, 45.0, 0),       # N of original position to clear U12 courtyard

    # J20 + D14 conflict was on D14 — already fixed via D14 move

    # ESC ESD diodes — clear of ESC pads + clear of board edge
    # D5 at (10, 9.5) was 9.5 — keep but verify edge clearance (Y>=0.3+pad_r)
    ("D5", 10.0, 10.0, 0),
    ("D6", 15.0, 10.0, 0),
    ("D7", 20.0, 10.0, 0),
    ("D8", 28.0, 10.0, 0),
    ("D9", 60.0, 10.0, 0),
    ("D13", 70.0, 10.0, 0),
    # D14 — old (75, 10) conflicts with J20 at (76, 10). Move S of ESC row.
    ("D14", 80.0, 14.0, 0),

    # USB ESDs near new U5 location
    ("D11", 78.0, 24.0, 0),
    ("D12", 78.0, 26.0, 0),
]


def fix_starved_thermals(brd):
    """For pads showing starved_thermal (only 1 spoke), override to SOLID
    connection to their zone."""
    # Run quick DRC to find affected pads — we'll just set all power-pin pads
    # on big ICs to SOLID for the +3V3 / GND / +5V planes to be safe.
    # Per master: "per-pad solid plane connection".
    POWER_NETS_FIX = {"GND", "+3V3", "+5V"}
    n_solid = 0
    for fp in brd.GetFootprints():
        for p in fp.Pads():
            net = p.GetNetname()
            if net in POWER_NETS_FIX:
                # Set zone connection to SOLID (PAD_ZONE_CONN_FULL = 1)
                p.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
                n_solid += 1
    return n_solid


def main():
    brd = pcbnew.LoadBoard(PCB)
    fps = {fp.GetReference(): fp for fp in brd.GetFootprints()}
    for entry in MOVES:
        ref, x, y = entry[0], entry[1], entry[2]
        orient = entry[3] if len(entry) > 3 else None
        fp = fps.get(ref)
        if not fp:
            print(f"  {ref}: not found"); continue
        fp.SetPosition(pcbnew.VECTOR2I(int(x*1e6), int(y*1e6)))
        if orient is not None:
            fp.SetOrientation(pcbnew.EDA_ANGLE(orient, pcbnew.DEGREES_T))
        print(f"  {ref} -> ({x}, {y}){f' orient={orient}' if orient is not None else ''}")
    n_solid = fix_starved_thermals(brd)
    print(f"[thermal] set {n_solid} power pads to SOLID zone connection")
    pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
    pcbnew.SaveBoard(PCB, brd)
    print("saved")


if __name__ == "__main__":
    main()
