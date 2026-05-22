#!/usr/bin/env python3
"""Re-placement per PLACEMENT_STRATEGY.md (master 2026-05-22).

Moves footprints to new positions per the 4-region strategy:
  - N edge: microSD + 8 ESC pads + CAN cluster
  - E edge: USB-C + Telem + CRSF + GPS
  - W edge: power section + HSE crystal hugging U1
  - S edge: sensor island (3 IMUs + 2 baros + heater + IMU LDO)

U1 stays at (41, 35), 0°.

Approach: enumerate (ref, new_x, new_y, new_orient_deg) and apply.
Other small parts (caps, resistors) move with their owner block when
practical, otherwise left in place — final cleanup is manual.
"""
import os, sys, json
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-layout-v1.1.kicad_pcb")

# (ref, new_x_mm, new_y_mm, new_orient_deg or None=keep)
# All coords assume KiCad: Y=0 at top, Y increases downward.
# N edge = small Y, S edge = large Y, W edge = small X, E edge = large X.

PLACEMENT = [
    # === U1 — central, 0° (KEEP) ===
    ("U1", 41.0, 35.0, 0),

    # === N edge: ESC pads (8) split into 2 clusters around microSD ===
    # NW cluster: MOT1-4
    ("J11", 10.0, 3.0, 0),
    ("J12", 15.0, 3.0, 0),
    ("J13", 20.0, 3.0, 0),
    ("J14", 25.0, 3.0, 0),
    # NE cluster: MOT5-8
    ("J15", 60.0, 3.0, 0),
    ("J16", 65.0, 3.0, 0),
    ("J17", 70.0, 3.0, 0),
    ("J18", 75.0, 3.0, 0),

    # === N center: microSD J2 (card slot opening N) ===
    # J2 is 15.8 × 24.1mm; rotate 0° = card opening to N (Y=0).
    ("J2", 39.0, 15.0, 0),

    # === N east: CAN cluster (J20 + U14 + U15 ESD) ===
    ("J20", 84.0, 8.0, 0),       # CAN connector at N-E corner
    ("U14", 82.0, 18.0, 90),     # TJA1051 transceiver below J20
    ("U15", 87.0, 19.0, 0),      # PESD2CAN ESD

    # === W edge: power + crystal ===
    # Y1 crystal: hug U1's W edge (X=33 is U1 W pad row; Y1 at X=29-30)
    ("Y1", 30.0, 35.0, 0),
    # Power input connectors KEEP (already W edge)
    ("J4", 4.0, 18.0, 0),
    ("J19", 4.0, 52.0, 0),
    # OR-ing block A (top) - KEEP
    ("U11", 15.5, 28.5, 0),
    ("Q3", 11.0, 28.5, 0),
    # OR-ing block B (bot) - KEEP
    ("U12", 15.5, 47.5, 0),
    ("Q4", 11.0, 47.5, 0),
    # eFuse + LDO KEEP
    ("U6", 9.0, 36.5, 0),
    ("U2", 22.0, 27.5, 0),       # slight shift E to be near U1 W
    # Reverse-pol + TVS KEEP
    ("Q2", 10.0, 22.0, 0),
    ("D1", 16.5, 21.0, 0),

    # === E edge: USB + serials ===
    # USB-C J1 at E edge, port opening E (rotate 90°)
    ("J1", 85.0, 30.0, 90),
    # USBLC6 ESD between J1 and U1 E side
    ("U5", 75.0, 26.0, 0),
    # ESD diodes near USB
    ("D11", 84.0, 20.0, 0), ("D12", 86.0, 20.0, 0),  # USB diff pair ESD
    # Telem J3 at E edge upper (port opening E)
    ("J3", 85.0, 50.0, 90),
    # CRSF J10 at E edge lower
    ("J10", 85.0, 60.0, 90),
    # GPS J5 at E edge mid
    ("J5", 85.0, 40.0, 90),

    # === S edge: sensor island ===
    # IMU island bridges to U1 with stress-relief slot below.
    # Cluster IMUs around Y=55-60 (below U1)
    # SPI2 IMU (U8 BMI088) at NE corner of island (closest to U1 E side)
    ("U8", 50.0, 55.0, 0),       # BMI088 - SPI2 — NE corner of island
    # SPI1 IMU (U3 ICM-42688) at NW corner of island
    ("U3", 35.0, 55.0, 0),       # ICM-42688-P - SPI1
    # SPI3 IMU (U9 LSM6DSV16X) at island center-S
    ("U9", 42.0, 60.0, 0),       # LSM6DSV16X - SPI3
    # Baros — one F.Cu, one B.Cu
    ("U7", 56.0, 60.0, 0),       # LPS22HB - I2C1
    ("U4", 30.0, 60.0, 0),       # DPS310 - I2C2 (B.Cu)
    # Heater (intentionally near IMUs)
    ("Q5", 60.0, 55.0, 0),       # AO3400A heater FET
    ("R61", 65.0, 55.0, 0),      # heater resistor
    # IMU LDO + ferrite
    ("U13", 65.0, 60.0, 0),
    ("FB2", 60.0, 60.0, 0),

    # === FB1 +3V3A ferrite stays W of U1 (analog supply) ===
    ("FB1", 30.0, 39.0, 0),

    # === J9 SWD KEEP (B.Cu, under U1 S) ===
    # already at (41, 7)... but ESCs are now at Y=3, so SWD conflicts.
    # Move SWD to S edge B.Cu (below sensor island).
    ("J9", 41.0, 65.0, 0),

    # === D6/D7/D8/D9/D13/D14 ESD on N edge — move out since N is full ===
    # These are ESC ESD diodes. Move them next to their ESC pad.
    ("D5", 10.0, 7.0, 0),   # near J11
    ("D6", 15.0, 7.0, 0),   # near J12
    ("D7", 20.0, 7.0, 0),
    ("D8", 25.0, 7.0, 0),
    ("D9", 60.0, 7.0, 0),
    ("D13", 70.0, 7.0, 0),
    ("D14", 75.0, 7.0, 0),
]


def main():
    brd = pcbnew.LoadBoard(PCB)
    moved = []
    not_found = []
    for ref, nx, ny, norient in PLACEMENT:
        fp = None
        for f in brd.GetFootprints():
            if f.GetReference() == ref:
                fp = f; break
        if not fp:
            not_found.append(ref)
            continue
        pos = pcbnew.VECTOR2I(int(nx*1e6), int(ny*1e6))
        fp.SetPosition(pos)
        if norient is not None:
            fp.SetOrientation(pcbnew.EDA_ANGLE(norient, pcbnew.DEGREES_T))
        moved.append(ref)

    # Strip ALL routes — placement changed, routes are invalid
    print(f"[placement] moved {len(moved)} components")
    if not_found: print(f"  NOT FOUND: {not_found}")
    n_t = n_v = 0
    for t in list(brd.GetTracks()):
        if isinstance(t, pcbnew.PCB_VIA):
            brd.Remove(t); n_v += 1
        else:
            brd.Remove(t); n_t += 1
    print(f"[strip] removed {n_t} tracks + {n_v} vias (placement is fresh)")

    # Refill zones
    pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
    pcbnew.SaveBoard(PCB, brd)
    print(f"[save] PCB written")


if __name__ == "__main__":
    main()
