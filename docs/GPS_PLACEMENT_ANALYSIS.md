# GPS+MAG+Buzzer Subsystem — Placement + Routing Constraint Analysis

> **Status**: DRAFT for master sign-off (autonomous mode 2026-05-24).
> NO LAYOUT TOUCH until sign-off.
> **Branch**: TBD (`hw/gps-placement-routing` after microSD merge).

---

## 1. Component inventory

| Ref | Part | Footprint | Function |
|---|---|---|---|
| J5 | JST-GH 10P horizontal | 9.5 × 17.01mm | Pixhawk DS-009 GPS+MAG+SAFETY+BUZZER 10-pin |
| R(?)_SDA | 4.7kΩ 0402 | I²C SDA pull-up |
| R(?)_SCL | 4.7kΩ 0402 | I²C SCL pull-up |
| TVS × N | D_TVS array | ESD on each external signal |

## 2. Net contract (Pixhawk DS-009 GPS pinout, 9 signal + GND)

| Pin | Net | MCU pad | Edge |
|---:|---|---|---|
| 1 | +5V | (power) | — |
| 2 | GPS1_TX | PD5 pad 86 N (X=46, Y=27.32) | N |
| 3 | GPS1_RX | PD6 pad 87 N (X=45.5, Y=27.32) | N |
| 4 | I2C1_SCL | PB6 pad 92 N (X=43, Y=27.32) | N |
| 5 | I2C1_SDA | PB7 pad 93 N (X=42.5, Y=27.32) | N |
| 6 | SAFETY_SW_TP | (test point) | — |
| 7 | SAFETY_LED_TP | (test point) | — |
| 8 | +3V3 | (power) | — |
| 9 | BUZZER | PD7 pad 88 N (X=45, Y=27.32) | N |
| 10 | GND | (zone) | — |

5 MCU pins, ALL on N edge (X=42.5..46). Tight cluster of 5 consecutive
pads minus pad 88 (gap). Clean fanout potential to N-side connector.

## 3. Zone candidates

### A: North band Y=5-15 — recommend
- J5 anchor at (~30, 6) — far W of CAN/microSD zones, fits standard "GPS connector at top-left" Pixhawk convention
- J5 bbox 9.5 × 17.01 occupies X=25..35, Y=−2.5..14.5 — south edge of J5 at Y=14.5
- Adjacent to J4 Mauch (16, 5) but ≥9mm spacing
- 5 MCU N-edge nets fanout NE from MCU at X=42..46 to J5 connector pads — short ~25mm reach

### B: North band Y=5-15 east of CAN
- Conflicts with CAN J20 + future SWD location

**Recommend A: NW of MCU.**

## 4. Proposed placement

| Ref | Anchor (X, Y) | Rotation |
|---|---|---|
| J5 | (30, 6) | 0° |
| R_SDA pull | (~28, 16) | — |
| R_SCL pull | (~28, 17) | — |
| TVS array | clustered at (~28, 14) | — |

## 5. Fanout reach (Rule 18 + 19)

5 nets: GPS1_TX/RX, I2C1_SCL/SDA, BUZZER.

| Net | MCU pad XY | J5 pad XY | Path | Est. length |
|---|---|---|---|---|
| GPS1_TX | (46.0, 27.32) | J5.2 ~(26.875, 8) | NW | 25mm |
| GPS1_RX | (45.5, 27.32) | J5.3 ~(28.125, 8) | NW | 25mm |
| BUZZER | (45.0, 27.32) | J5.9 ~(35.625, 8) | NW (short E) | 22mm |
| I2C1_SCL | (43.0, 27.32) | J5.4 ~(29.375, 8) | NW | 25mm |
| I2C1_SDA | (42.5, 27.32) | J5.5 ~(30.625, 8) | NW | 25mm |

All paths ~22-25mm. ALL F.Cu feasible (no obstacles in NW band from MCU
N pads to J5 NW area).

### Corridor pre-flight (Rule 18 + 19) — TODO at placement time
- X=26..47 Y=8..27 corridor — survey tracks + pads + existing routes
- Likely clean (no existing routes in NW band)

## 6. Decisions

1. Zone A (NW, recommend) vs B
2. J5 anchor (30, 6) — ±3mm flex
3. SAFETY_SW + SAFETY_LED test points — physical test pads near J5 (5x ~Φ1mm)?

## 7. Gates

1. DRC ≤ baseline
2. STACKUP-SPEC-MATCH PASS
3. MIRROR_PAIRS 11/11
4. DECOUPLING: TVS within 2mm of J5 each pin
5. I2C1 pull-ups SCL/SDA visible to net

---

**Awaiting master sign-off after microSD PR lands.**
