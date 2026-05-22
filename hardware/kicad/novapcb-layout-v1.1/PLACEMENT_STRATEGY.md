# Placement Strategy — v1.1 R4 routability-driven re-placement (2026-05-22)

Per master direction, executed by worker. Records the strategy verbatim
and the Step-0 pin-side load check that gates placement.

## Core principle

Each peripheral goes on the MCU side where its pins exit. The MCU's
current 0° orientation already puts the PIN-LOCKED peripherals on the
right sides (SDMMC → N, USB → E, HSE → W) — so **U1 stays ~central
at 0°**, and the fix is moving the peripherals to match + re-muxing
the movable buses.

## 4 regional domains around U1 (keep U1 central, 0°)

### N region + N edge — digital aggressors
- **microSD J2 → N** (SDMMC1 pin-LOCKED to MCU-N). Place at the N
  edge, card slot opening off the N edge. Kills the worst current
  mismatch (the 50 mm SDMMC route).
- **8 ESC pads J11-J18 → N edge.** Re-mux ALL 8 MOT outputs to MCU-N
  pins (all GPIO/timer, movable).
- **CAN: U14 + J20 → N.** CAN1 is already on N — keep it (do NOT mux
  away). J20 connector on the N edge.
- **EMI rationale:** SDMMC1_CLK, DShot, CAN are all aggressors —
  clustering them on N, far from the S sensor island, is correct
  EMI practice.

### E region + E edge — USB + serial comms
- **USB-C J1 → E edge** (OTG_FS pin-LOCKED to MCU-E). U5 USBLC6
  between J1 and the MCU's E side. Route the USB pair as the
  controlled-impedance pair.
- **Telem J3 (USART1, E), CRSF J10 (USART6, E) → E edge.**
- **GPS J5 → E edge**; re-mux GPS1's UART to a MCU-E pin set.

### W region + W edge — power + crystal
- **Crystal Y1 → hug U1's W side, tight** (HSE pin-LOCKED, pins 12/13).
  Keep traces minimal.
- **Power section → W region:** J4/J19 power-in on the W edge, eFuse
  U6, OR-ing Q3/Q4/U11/U12, reverse-pol Q2, TVS D1, +5 V LDO U2.
  BATT-sense ADC pins are on MCU-W — the sense lines reach directly.
- **Honest EMI trade-off:** the crystal (sensitive + aggressor) is
  pin-locked W, same region as the switching power section.
  Mitigation: crystal hugs U1 tight; push the power-switching parts to
  the FAR W; keep a gap. Acceptable.

### S region + S edge — the sensor island (the protected zone)
- The 3 IMUs + 2 baros + IMU LDO U13 + heater Q5/R61, as the
  stress-relief-slotted island, on the S edge, bridge to U1.
- **Re-mux SPI1 and SPI3 fully to MCU-S** (SPI1_MOSI currently N,
  SPI3 currently N → move to S; SPI1_SCK/MISO already S).
- **I2C2 (DPS310 baro) already on S — keep.** Re-mux I2C1 to S so
  LPS22HB baro joins the island. HEATER_PWM already S — keep.
- **SPI2: CONFIRM its mux options** (you did not list it movable).
  If SPI2 can move to S, all 3 IMUs cluster cleanly. If SPI2 is
  genuinely locked to E, place the SPI2-IMU (U8/IMU2) at the island's
  NE corner nearest MCU-E and route SPI2 down. Report which.
- **EMI:** S is the region farthest from power (W) and USB (E);
  ESC/SDMMC aggressors are on N. The S island is the protected zone
  — keep ALL aggressors out of it.

## Step 0 — pin-side load check (gate before placing)

After the re-mux, count pins per MCU side (must be ≤25/side).
Re-mux list:
- SPI1 → S
- SPI3 → S
- I2C1 → S
- 8× MOT → N
- GPS1 → E
- Confirm SPI2

If any side exceeds 25 or a conflict appears, report before placing.

**Step 0 result is in the next section.**

## Pin re-mux = a schematic revision

The re-mux changes U1 pin assignments → a schematic edit + ERC re-run +
hwdef.dat update later. That is expected and authorized — do it
properly.

## Gate (non-negotiable, all three)

1. **Route-validate:** Freerouting on the new placement reaches ~100%
   (or you can see a clean path for every residual). THIS is the gate
   that was missing.
2. **Thermal:** FEM the placement (after R61 heater value is set) — or
   analytical with margin.
3. **EMI:** confirm aggressor/victim separation per the regions above.
   0 DRC, connectors edge-accessible.

Execute order: record this doc, do Step 0 (pin-side check + SPI2),
report it to master, THEN place. Commit + push throughout.
