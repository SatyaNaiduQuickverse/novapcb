# T3 Sub-attempt 2b — IMU CS B.Cu route survey

> **Status**: SURVEY for master sign-off (T3 micro-PR cascade 2b).
> NO LAYOUT TOUCH.
> **Branch**: hw/t3-2b-imu-cs-bcu off sch/option-b-buck head 88509f9.

## Survey scope

IMU CS endpoints:
- IMU1_CS: PC15 pad 9 W (37.33, 33.00) → U3.10 (61.46, 56.75)
- IMU2_GYR_CS: PD4 pad 85 N (46.50, 27.32) → U8.5 (66.80, 56.50)
- IMU3_CS: PE2 pad 1 W (37.33, 29.00) → U9.12 (77.50, 57.92)

## IMU2_GYR_CS already on B.Cu (PR #77)

Per pcbnew survey, IMU2_GYR_CS has 2 existing B.Cu segments at
(47.17, 28.64)-(37.98)-(62.80, 53.62). Already meets the "drop to B.Cu"
goal — **no re-route needed for 2b**.

## Remaining 2b scope: IMU1_CS + IMU3_CS (2 nets, not 3)

## B.Cu envelope X=35..80 Y=27..60 — Rule 19 occupants

Comprehensive inventory (15 nets):

| Net | B.Cu segments in envelope | Source PR |
|---|---:|---|
| +3V3_IMU | 16 | PR #78 |
| SPI3_MOSI | 10 | PR #77 wraparound |
| IMU2_ACC_INT1 | 6 | PR #77 |
| IMU2_GYR_INT3 | 6 | PR #77 |
| SPI3_SCK | 4 | PR #77 |
| BATT2_CURRENT_SENS | 3 | PR #87 sense |
| HEATER_PWM | 3 | PR #77 |
| BATT2_VOLTAGE_SENS | 2 | PR #87 |
| IMU2_GYR_CS | 2 | PR #77 (target net — already B.Cu) |
| SPI1_MOSI | 2 | PR #77 |
| SPI1_SCK | 2 | PR #77 |
| SPI2_MOSI | 2 | PR #77 |
| SPI3_MISO | 2 | PR #77 |
| BATT_VOLTAGE_SENS | 1 | PR #87 |
| I²C2_SCL/SDA | 1 each | PR #73 |

**Total: 64+ B.Cu segments in 45×33mm envelope (1485mm²). Density ~4.3% area coverage just from tracks. Plus via anti-pads.**

## Proposed IMU1_CS + IMU3_CS B.Cu paths

### IMU1_CS path candidates

A) South perimeter route: (37.33, 33) F.Cu W stub → via → B.Cu south to Y=70 → SE to U3.10 area (61.46, 56.75) via wraparound. Length ~50mm. Avoids dense central area.

B) Diagonal central: (37.33, 33) → straight B.Cu diagonal to (61.46, 56.75). Length ~37mm. Conflicts: SPI3_SCK diagonal (50.57, 27.23)-(73.90, 50.56) crosses; IMU2_ACC_INT1 segments cross.

### IMU3_CS path candidates

A) South perimeter: (37.33, 29) → B.Cu west then south to Y=70 → SE long to (77.50, 57.92). Length ~70mm.

B) Diagonal: direct (37.33, 29) → (77.50, 57.92). Length ~50mm. Conflicts: every B.Cu diagonal in the envelope.

## Risk assessment

**Both A perimeter routes** are LONG (~50-70mm) for slow GPIO CS lines.
SI fine but adds latency negligibly (CS edge ~ns; trace ~250ps).

**Diagonal central routes** would HIT 5-10 existing B.Cu segments each.
Each crossing = mandatory layer-split with extra via (4 more vias per
net) — defeats the "drop to B.Cu to free F.Cu" goal.

## Recommendation

**(A) South-perimeter B.Cu paths for IMU1_CS + IMU3_CS.** Length cost
acceptable for slow GPIO. Avoids existing B.Cu density.

If even south perimeter conflicts (need pcbnew sub-survey), fall to:
- (X) Keep IMU1_CS + IMU3_CS on F.Cu but re-route to clear MOT3-6
  fanout zone — different X column.
- (Y) Accept they cross MOT* via layer hop (each crossing needs a via)
  — defeats purpose.

## Decisions for sign-off

1. IMU1_CS + IMU3_CS path: (A) south perimeter B.Cu (recommend)
2. IMU2_GYR_CS: NO re-route needed (already B.Cu)
3. If (A) hits south-perimeter B.Cu obstacle (uncommon at Y=70+): escalate

## Gates expected

- DRC: ≤ baseline +3 (2 nets re-routed with ~4 vias added)
- STACKUP-SPEC-MATCH PASS
- Unconnected: net unchanged (paths just change layer)
- Per-net cluster walk: B.Cu over In4 GND (continuous full-board)

---

**Awaiting master sign-off on (A) south perimeter approach before 2b execution.**
