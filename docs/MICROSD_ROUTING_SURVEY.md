# microSD (SDMMC1) routing — up-front survey (task #46)

> Branch `hw/microsd-routing` off `sch/option-b-buck` (9e365e3, CAN merged).
> Baseline DRC 18 / unconnected 255. NO LAYOUT TOUCH until master sign-off.

## 1. Topology (6 SDMMC1 nets)

| Net | MCU pad | Edge | J2 slot pad | Pull-up |
|---|---|---|---|---|
| SDMMC1_CLK | U1.80 (49.0, 27.32) | N | J2.5 (93.38, 59.27) | — (clock, no PU) |
| SDMMC1_CMD | U1.83 (47.5, 27.32) | N | J2.2 (96.67, 59.27) | R51 47k |
| SDMMC1_D0  | U1.65 (52.67, 34.0) | E | J2.7 (91.17, 59.27) | R52 47k |
| SDMMC1_D1  | U1.66 (52.67, 33.5) | E | J2.8 (90.08, 59.27) | R53 47k |
| SDMMC1_D2  | U1.78 (50.0, 27.32) | N | J2.9 (89.12, 59.27) | R54 47k |
| SDMMC1_D3  | U1.79 (49.5, 27.32) | N | J2.1 (97.78, 59.27) | R55 47k |

- **J2** microSD slot @ (95,67), contact row Y=59.27, X=89–98 (D2 west → D3 east).
- **R51–R55** = 47k pull-ups to +3V3 @ (86, 62–70), SW of J2 (CMD + D0–D3; CLK
  has none — standard SD). They TAP the lines near J2; signals route MCU→J2
  directly, pull-ups branch off locally. Not in-line.
- MCU exits: CLK/CMD/D2/D3 on N-edge (X=47.5–50, 0.5mm pitch); D0/D1 on E-edge
  (X=52.67, Y=33.5–34).

## 2. Corridor (Rule 18/19/20) — DENSE

MCU (NW, Y=27–34) → J2 (SE, X=95 Y=59). The direct corridor (X=52–88, Y=30–58)
overlaps the **D-zone IMU island + SPI bus region**. Existing routed nets crossing:
- **F.Cu**: +3V3_IMU(18), SPI2_MISO(18), IMU1_CS(11), SPI1_MISO(11),
  IMU2_ACC_CS(9), SPI1_MOSI(7), I2C2_SDA(6), IMU2_GYR_INT3(6), SPI3_MISO(6),
  SPI2_SCK/MOSI(5), IMU3_CS(4)
- **B.Cu**: +3V3_IMU(15), IMU2_GYR_INT3(5), SPI3_MOSI(4), HEATER_PWM(2), SPI1/2/3 …

This is a CAN-NE-corner-class congestion, ×6 nets. Plus length-matching (#77).

Geometry note: the D-zone IMU island is X=56–86, Y=51–63. **J2 (X=95) is EAST of
the island**; a path that stays NORTH of the island (Y<51) then turns SOUTH east
of it (X>88) may avoid the worst SPI density — to be confirmed.

## 3. Decisions for sign-off

1. **Approach**: recommend **scoped Freerouting** (6 SDMMC nets, F.Cu+B.Cu) as
   primary — proven on CAN (solved the dense NE bus); same scoped-DSN +
   via-padstack-strip technique. Manual fallback if it leaves nets unrouted
   (as CAN's MCU signals did). Confirm.
2. **Path**: (a) Freerouter's choice; or (b) constrain to N-of-island-then-E
   (X>88 down to J2). Recommend (a) first, evaluate result.
3. **Length-matching tolerance**: task #77 implies tight match. But ArduPilot SD
   logging runs SDMMC at modest clock (≤48 MHz, 4-bit); SD spec tolerance is
   loose. **Question**: hold ±0.5mm (tight, needs post-route serpentine on a
   dense board) or relax to a SD-appropriate skew budget (e.g. CLK-to-data
   ≤ a few mm) given the use case? Recommend defining the budget from the actual
   SDMMC clock before committing to serpentine real-estate.
4. **CLK reference + return**: keep CLK over a continuous GND plane; data lines
   referenced to same plane. B.Cu segments over In4 GND, F.Cu over In1 GND.

## 4. Gates (planned)

- DRC ≤ baseline(18)+3; unconnected −11 (6 nets close + pull-up taps)
- STACKUP/MIRROR/DECOUPLING audit PASS (unchanged)
- Per-net cluster walk (GND reference) for all 6 nets
- Length-match report vs the agreed tolerance

---

**Awaiting master sign-off on approach (Freerouting-first) + the length-match
tolerance question before execution.**
