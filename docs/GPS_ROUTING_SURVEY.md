# GPS routing — up-front survey (task #47)

> Branch `hw/gps-routing` off `sch/option-b-buck` (ed82c54, CAN+microSD merged).
> Baseline DRC 18 / unconnected 244. NO LAYOUT TOUCH until master sign-off.

## 1. Topology (5 signal nets, all currently unrouted)

J5 GPS+MAG connector @ (15,75) SW corner, contacts Y=73.15. ESD D5–D9 @ X=24,
Y=67–75; I2C pull-ups R21/R22 @ (27,71/73).

| Net | MCU pad (N-edge) | Path / endpoints |
|---|---|---|
| GPS1_TX | U1.86 (46.0,27.3) | → ESD D5 (24,67) → J5.2 (10.6,73.15) |
| GPS1_RX | U1.87 (45.5,27.3) | → ESD D6 (24,69) → J5.3 (11.9,73.15) |
| BUZZER  | U1.88 (45.0,27.3) | → ESD D9 (24,75) → J5.9 (19.4,73.15) |
| I2C1_SCL| U1.92 (43.0,27.3) | **multi-drop**: U7.2 (54,47 LPS22 baro) + R22 (27,73 PU) + ESD D7 (24,71) + J5.4 |
| I2C1_SDA| U1.93 (42.5,27.3) | **multi-drop**: U7.4 (55,48) + R21 (27,71 PU) + ESD D8 (24,73) + J5.5 |

SAFETY_SW_TP / SAFETY_LED_TP are single-pad J5 test-point nets — no routing.

## 2. Corridor (Rule 18/19/20)

MCU N-edge (X=42–46) → SW J5 (X=9–20, Y=73). Corridor X=8–47, Y=28–72 crossings:
- F.Cu: IMU1_CS(9), +3V3(7), I2C2_SCL(6), SPI1 SCK/MISO/MOSI, BATT/BATT2 sense
- B.Cu: BATT2_CURRENT_SENS(3), IMU2_ACC_INT1(3), SPI3_MOSI, BATT sense
- **Moderate density** — far lighter than the microSD D-zone (no IMU island here).
- SW quadrant (J5/ESD/PU/TPs) is open. ESD + pull-ups already placed.

## 3. Decisions for sign-off

1. **Approach**: scoped Freerouting (5 nets, F+B) — proven on CAN #99 + microSD
   #100 (DSN net-scope + via-padstack-strip). Manual fallback per net if needed.
   Recommend.
2. **I2C1 multi-drop**: route SCL/SDA as single nets reaching MCU + U7 + J5 +
   pull-up + ESD (Freerouting handles multi-drop). Confirm.
3. **Length-match**: NOT required — UART (≤460 kbaud), I2C1 (400 kHz), BUZZER
   (DC). All low-speed; no skew budget.
4. **GND reference**: F.Cu→In1.Cu, B.Cu→In4.Cu; per-net cluster walk.

## 4. Gates (planned)

- DRC ≤ baseline(18)+3; unconnected −N (5 nets + multi-drop taps close)
- STACKUP/MIRROR/DECOUPLING audit PASS (unchanged)
- Per-net cluster walk (GND reference) for all 5 nets

---

**Awaiting master sign-off on Freerouting-first + I2C1-multi-drop before execute.**
