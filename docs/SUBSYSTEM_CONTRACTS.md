# SUBSYSTEM_CONTRACTS — novapcb v1.1 placement decomposition

> **Status:** **APPROVED by master 2026-05-22** with the 6 refinements
> in §3 applied. Pairs with `docs/PLACEMENT_ROUTING_GATES.md` as the
> governing process. Every placement PR scopes to exactly one subsystem
> from this doc.
>
> **Board outline (per `docs/DECISIONS.md §2`, master sign-off
> 2026-05-23 of gate12 v3 corrected sweep):**
> **105 × 85 mm rectangle**, 6-layer JLC06161H-7628. Was 90 × 70 mm
> until 2026-05-23 — the gate12 v3 + rigorous-powers sweep showed
> that size FAILS the ≥5°C MCU margin (MCU=83.86°C); 105×85 is the
> smallest size meeting the target. The zone coordinates below were
> originally drawn for 90×70 and are gradually being updated. **A
> zone update in progress 2026-05-23**: B zone scaled to use the
> extra board area (X=10..85, Y=13..30 — U2 pushed MAX-west to
> 32.7mm from U1 vs 23mm on 90×70). A/D/H/G zones not yet rescaled —
> the extra 15mm width + 15mm height is "available area" to be used
> by those subsystems when placed.
>
> All Y-down coords below are valid as RELATIVE positions; the board
> edges move from 90×70 to 105×85 but MCU stays at (45, 35) so
> existing C/E/F/G placements remain physically valid.
>
> **Coordinate convention (RECONCILED 2026-05-22 per master directive)**:
> all zones use **pcbnew-native Y-DOWN** — origin (0, 0) at the **NW
> (top-left) corner**, X increases east, **Y increases SOUTH (down in
> the render)**. So Y=0 is the top edge, Y=70 is the bottom edge. This
> matches `pcbnew` Python API, KiCad's GUI, all `kicad-cli pcb render`
> outputs, and every `step*_place_*.py` script in
> `hardware/kicad/novapcb-stepwise/`. The earlier draft used math
> (Y-up) for some descriptions which caused E to be mis-placed in
> Step 2 — see Step-2 PR audit. Never mixing conventions again.
>
> All zone coordinates below: `X = column (mm, east-positive)`,
> `Y = row (mm, south-positive)`, both starting at NW corner (0, 0).
>
> **Source of truth for component list:** `hardware/kicad/novapcb/sheets/`
> SKiDL netlist (immutable for v1.1, including the 3-swap re-mux
> SPI1_MOSI=PA7, HEATER_PWM=PA15, BUZZER=PD7).

---

## 0. Global constraints driving zone assignment

These are the cross-cutting constraints. Each subsystem inherits them.

1. **EMI separation.** CRSF UART (≥420 kbaud), ESC PWM (DShot300/600,
   ≥30 MHz harmonics), and the GPS receiver band (1.575 GHz) cannot
   share zones with the IMU sensor island. ELRS/CRSF carries sub-GHz
   activity that couples into MEMS gyros; ESC switching creates the
   loudest in-band noise on the IMU rails. The IMU island must be
   physically and electrically isolated.

2. **USB short-trace constraint.** USB 2.0 full-speed (12 Mbps) is
   forgiving on length but the differential pair impedance (90 Ω,
   per `docs/CONTROLLED_IMPEDANCE.md`) requires controlled W/S. Place
   J1 (USB-C) on an edge with ≤30 mm trace to U1 PA11/PA12.

3. **Power-input mech.** J4 (Mauch 6-pin) and J19 (Mauch backup)
   cables enter from the airframe battery bay; place on the same
   edge as the battery bay. Cable strain relief mass concentrates
   here.

4. **Connector access.** J5 (GPS+MAG), J3 (telem), J10 (CRSF), J9
   (SWD), J20 (CAN), J2 (microSD) all need mechanical access from
   the top of the drone. Cluster on an edge where the airframe
   canopy clears.

5. **Mounting holes.** **4 corner-inset M3 holes** at ~5 mm inset
   from each corner of the 90×70 board: **(5, 5), (85, 5), (5, 65),
   (85, 65)**. Keep-out ≥1 mm around each hole. Master directive
   2026-05-22: the `DECISIONS §2` 30.5×30.5 c-to-c pattern was for
   the original 36×36 form factor; on a 90×70 board the centered
   30.5×30.5 leaves ~30 mm overhang per side (mechanically poor).
   See `docs/OPEN_QUESTIONS.md` entry "Mounting-hole-pattern-90x70"
   for Sai's ratification of this supersession.

6. **Reference teardowns (for Gate 6).** Pixhawk 6X (FMUv6X family),
   Holybro Kakute H7, mRo Control Zero H7, Matek H743-Slim. Each
   subsystem PR cites which teardown(s) inform its placement.

---

## 1. Subsystem index

All zones in **pcbnew Y-down** (Y=0 = top edge, Y=70 = bottom edge):

| # | Subsystem | Refdes (primary) | Zone (mm, pcbnew Y-down) | Conflict | Adjacent to |
|---|---|---|---|---|---|
| A | POWER_INPUT | J4, J19, Q3, Q4, U11, U12 + caps | **bottom edge** Y=55..70, X=20..70 | **HIGH** | B (immediately above) |
| B | POWER_REG_3V3 | U2, U6, U13, FB2, D1, Q2 + LDO caps | **bottom band** Y=44..55, X=20..70 (south of MCU) | **HIGH** | A (below), C (above) |
| C | MCU_CORE | U1, Y1, R1, R2, R3 + MCU decap (C11..C26) | **center** roughly X=33..58, Y=23..44 (U1 body centered at (45, 35)) | **HIGH (hub)** | E (south, on PB10/PB11), D (north, on bridge), F (east, on PA11/PA12), H (west, on PA0..3) |
| D | IMU_ISLAND | U3, U8, U9, Q5 (IMU heater FET), R_heater (R61), FB-downstream caps (C41..C96) | **top stress-relief island** Y=7..19, X=33..63; mechanical bridge to C at Y=19..21 (10mm wide, X=40..50) | **HIGH (victim)** | C (below, via bridge only) |
| E | BARO_I2C | U4, U7, R11, R12 + decap (C51, C52, C71, C72) | **small block south of U1**, adjacent to PB10/PB11 pins on U1's S edge: Y=44..52, X=42..58 | LOW | C (above; R11/R12 sit at the seam) |
| F | USB_INTERFACE | J1, R31, R32, U5 | **east edge** X=75..90, Y=22..45 (U5 moved south to clear pair Y=31 corridor; borrows Y=38..45 from G — Step-3 re-open 2026-05-22) | LOW | C (west; ≤30mm USB diff pair) |
| G | EXTERNAL_IO | J2, J3, J5, J9, J10, J20, U14, U15, D11..D14, R45, R46 + decap | **east edge** X=75..90, Y=45..70 + **top edge** corners for GPS connector | **MIXED** | C (depending on connector pin) |
| H | ESC_OUTPUTS | J11..J18 (motor pads) | **west edge** X=0..18, Y=10..60 (vertical strip; PWM signals route from MCU PA0..3 W edge, PB0/1 S edge, PD12/13 E edge — H's pads are W edge regardless) | **HIGH (aggressor)** | C (east; PWM routes cross the board) |

Subsystem labels A..H are placement-PR identifiers. Each gets one PR.

**Convention note:** in this doc, terms like "north / south / top / bottom" refer to the **render-frame** (top = Y=0 = pcbnew "north" = math-y "south"). Subsystems are described relative to U1's position (center at X=45, Y=35) and the actual STM32H743VIT6 LQFP-100 pinout (which dictates *which side of U1* a given signal exits). This is the source of truth — not any abstract "north"/"south" notion.

### Conflict-risk rationale (drives integration order per `PLACEMENT_ROUTING_GATES.md` §0)

| # | Subsystem | Conflict | As AGGRESSOR (what it generates) | As VICTIM (what hurts it) |
|---|---|---|---|---|
| A | POWER_INPUT | HIGH | high di/dt at FET OR-ing edges; battery cable EMI; localized heat (Q3/Q4 carry full 5V current) | reverse-bias on D1 transients; J4 cable-pickup of external EMI |
| B | POWER_REG_3V3 | HIGH | LDO ripple on +3V3; LDO heat (U2 250-500mW, U13 ≤100mW); eFuse switching at fault | input bulk-cap inrush; PSRR limited above ~10 kHz, so power-section di/dt couples through |
| C | MCU_CORE | HIGH (hub) | crystal Y1 8MHz fundamental + harmonics; SDMMC1 25MHz clock harmonics; MCU VDD switching at internal clock edges; ADC chopping | every input pin is a victim (especially PC0/PC1 ADC for battery sense). The MCU is the hub — everything routes to/from it, so it appears in EVERY integration step. |
| D | IMU_ISLAND | HIGH (victim) | minor — MEMS oscillator at ~30kHz, SPI clock at 2-16MHz | EVERYTHING: gyros sensitive to sub-GHz RF, accelerometers sensitive to acoustic + vibration, power rail rejection only ~40dB above 1kHz. The slot + bridge is mechanical decoupling; +3V3_IMU (FB2-isolated) is electrical decoupling. |
| E | BARO_I2C | LOW | I2C2 at 400kHz — slow, low-edge-rate. DPS310 doesn't heat. | barometer is acoustic-noise sensitive (not RF/vibe); ESC fan noise and motor coupling can affect it. Place away from H. |
| F | USB_INTERFACE | LOW | USB 2.0 FS = 12 Mbps — fast edges but contained in the diff pair if controlled-impedance is enforced (90 Ω verified by `val_skrf_microstrip.py` + `val_openems_microstrip.py`). | external ESD events (handled by U5 TPD4S014). |
| G | EXTERNAL_IO | MIXED | per-connector. **CRSF (J10)** at 420 kbaud has sub-GHz harmonics that couple into IMU — HIGH risk. **CAN bus** at 1 Mbps is differential, well-contained — LOW. **GPS/MAG UART** is slow — LOW. **SDMMC** at 25 MHz is fast but contained on diff-impedance traces — MEDIUM. **SWD** is only active during programming — LOW. Place high-conflict G connectors (CRSF) as far from D as possible; place LOW-conflict ones first. | external cable-pickup of EMI; ESD via diodes D11..D14. |
| H | ESC_OUTPUTS | HIGH (aggressor) | DShot300/600 = up to 600 kbit/s at sharp edges → harmonics into hundreds of MHz; 8 channels switching simultaneously. **Largest single aggressor on the board.** | not really a victim — pads just carry signal out. |

**Integration-order implication.** Per `PLACEMENT_ROUTING_GATES.md §0`:
1. **C (MCU_CORE)** first — the hub everything routes to. Hub conflict is per-pin and is resolved by the next step's adjacency, not by C alone.
2. **LOW-conflict subsystems next** (E, F, low-risk parts of G — GPS/SWD/CAN connectors) — they integrate cleanly, build up the context.
3. **HIGH-conflict subsystems ONE AT A TIME** (B, A, D, H, CRSF in G) — each integration step adds exactly ONE high-conflict subsystem and runs the relevant aggressor↔victim sim BEFORE locking.
4. **The hardest pairings get their own integration steps:**
   - A↔B (already adjacent by physics; integrate together carefully)
   - C↔D (the bridge pin assignments; verify SPI rise-time + IMU power isolation under realistic load)
   - C↔H (DShot harmonics into MCU ADC pins; verify motor-PWM-to-ADC isolation)
   - C↔D after H added (worst case: motor PWM noise into the IMU island via the C ↔ D bridge — needs explicit EMI sim)
   - G:J10 (CRSF) integrated last; CRSF↔D coupling tested in isolation

---

## A — POWER_INPUT

**Goal.** Convert dual-Mauch BEC power inputs (J4, J19) into a shared
P5V_BEC rail with ideal-diode OR-ing. Sense pre-LDO voltage and current
for ArduPilot battery monitoring.

**Components (per SKiDL, verified 2026-05-22):**
- J4 — Mauch primary 6-pin connector (BEC + sense)
- J19 — Mauch secondary 6-pin (backup)
- Q3, Q4 — N-FET OR-ing pass elements (driven by U11/U12 gate signals)
- U11 — LM74700-Q1 ideal-diode controller for input A
- U12 — LM74700-Q1 ideal-diode controller for input B
- C73, C74 — U11 VCAP + bypass
- C75, C76 — U12 VCAP + bypass
- R41, R42 — primary V/I sense divider+filter (BATT_V_SENSE, BATT_I_SENSE)
- R43, R44 — secondary V/I sense (J19 path; nets BATT_V_SENSE2, BATT_I_SENSE2 — currently unused per `hwdef.dat` BATT2 removal note)
- C61, C62, C81, C82 — sense capacitors

**Input nets (enter zone from outside):** (none — this is the source)

**Output nets (leave zone to other subsystems):**
- `P5V_BEC` → to B (POWER_REG_3V3)
- `BATT_V_SENSE`, `BATT_I_SENSE` → to C (MCU U1.PC0/PC1)
- `BATT_V_SENSE2`, `BATT_I_SENSE2` → to C (reserved; v1 BATT2 inert)

**Zone:** Y=0..15, X=20..70 (south edge, centered horizontally).
J4 and J19 along the south edge for cable strain relief.

**Adjacency:**
- IMMEDIATELY north: B (POWER_REG_3V3) — short P5V_BEC trace, big copper pour
- Must NOT be adjacent to: D (IMU_ISLAND) — high di/dt at OR-ing FET switching couples noise

**Reference teardowns:** Pixhawk 6X mounting bay (power input opposite USB side), Kakute H7 (Mauch input bay along one short edge).

---

## B — POWER_REG_3V3

**Goal.** Regulate P5V_BEC down to clean +3V3 (main) for MCU + most
sensors, and a separate ferrite-isolated +3V3_IMU rail for the IMUs.
Add eFuse protection on the input side.

**Components:**
- U6 — eFuse (TPS25922 or similar) on the P5V_BEC path
- U2 — main +3V3 LDO (e.g. TLV757P / AP7361C class; check `power_3b.py`)
- D1 — TVS diode on input
- Q2 — auxiliary FET (TBD: reverse polarity?)
- R7..R10, R13 — eFuse programming (ILIM, PG pull-up, FLT pull-up)
- C7, C8, C9, C31..C34 — input/output bulk + 100nF decap
- **FB2** — ferrite bead isolating +3V3 → +3V3_IMU
- U13 — secondary LDO for +3V3_IMU (post-FB2)
- C77, C78 — U13 input/output decap

**Input nets:** `P5V_BEC` (from A)

**Output nets:**
- `+3V3` (main rail) → to C, E, F, G plane
- `+3V3_IMU` (filtered rail) → to D only
- `PGOOD`, `FLT` → to C (MCU GPIO, optional)

**Zone (v1.1 105×85 updated 2026-05-23):** Y=13..30, X=10..85. U2 pushed MAX-west (X=15) to maximize separation from U1 MCU at (45, 35) — 32.7mm vs 23mm on old 90×70. Reduces LDO heat funneling into MCU vicinity. Was Y=15..28, X=20..70 on 90×70.

  Old zone description (90×70, kept for traceability): Y=15..28, X=20..70. Locate U2 closer to MCU side (Y=24..28),
U6 closer to power input (Y=15..20). U13 + FB2 along the path to D
(north side), so the +3V3_IMU exit point is at the boundary with D.

**Adjacency:**
- South: A
- North: C (MCU decap consumers)
- North-edge specific: FB2 + U13 placed so +3V3_IMU exits at Y≈28, X≈45 (toward D)

**Thermal vias (Gate 7):**
- U2 (≥9 vias under exposed pad)
- U6 (≥9 vias)
- U13 (≥4 vias)

**Reference teardowns:** Kakute H7 LDO placement under the MCU, Pixhawk 6X eFuse on power-input side of the FMU board.

---

## C — MCU_CORE

**Goal.** STM32H743VIT6 with its HSE crystal, BOOT/NRST circuitry,
power decoupling for VDD/VDDA/VBAT/VREF.

**Components:**
- U1 — STM32H743VIT6 LQFP-100 (the MCU). Centered on the board.
- Y1 — 8 MHz HSE crystal (per `hwdef.dat:OSCILLATOR_HZ 8000000`)
- C24, C25 — HSE crystal load caps (typ 18pF)
- C19, C20 — VDDA decap (100nF + 1µF)
- C21, C22 — VREF decap (100nF + 1µF)
- C23 — VBAT decap
- C26 — NRST cap (debounce)
- R1 — VREF tie
- R2 — VBAT tie
- R3 — BOOT0 pulldown
- C16 — bulk decoupling (10µF)
- Per-VDD pin: 100nF X7R 0402 (multiple, refdes range C17..C30 — verify in `mcu_3a.py`).
  **These belong to C** (placed within ~3 mm of their MCU power pins —
  the point of a decap). They connect to the +3V3 plane, which is a
  global cross-subsystem net (§2), not B's. Master directive 2026-05-22:
  "no real overlap" between B and C — B owns the LDO + regulation
  passives; C owns the MCU decaps; +3V3 plane is global.

**Input nets:**
- `+3V3` (multiple pins: VDD1..VDD11, VDDA, VREF)
- `+3V3_IMU` is NOT input here (only D receives it)
- `GND`

**Output nets:** all MCU pin signals (SPI1/2/3, I2C1/2, USART1/2/3/6, USB, CAN1, SDMMC1, MOT1..MOT8 PWM, ADC inputs, GPIOs, SWD)

**Zone:** Y=28..50, X=20..70. U1 centered roughly at (45, 40).
- HSE crystal Y1 placed at MCU's W or E side, ≤5 mm from PH0/PH1 pins (12/13 on LQFP-100).
- C24/C25 within 2 mm of Y1.
- Per-pin 100nF caps placed within 3 mm of each VDD pin on the same side of the MCU.

**Adjacency:**
- South: B (decap connection to +3V3 plane)
- North: D (SPI1/2/3 + INT lines cross the bridge to IMU island)
- East: F, G (USB short trace; UARTs to connectors)
- West: H (PWM signals to motor pads)

**Thermal vias (Gate 7):** **NOT required for U1**. Verified
2026-05-22: STM32H743VIT6 in `Package_QFP:LQFP-100_14x14mm_P0.5mm`
is a standard gull-wing LQFP — **no exposed thermal pad**. The MCU
dissipates ≤500 mW through its 100 leads to the +3V3 / GND planes;
Gate 7 thermal-via requirement applies to packages with exposed
pads (U2, U6, U13, Q3, Q4) and not to U1.

**Reference teardowns:** Pixhawk 6X FMU center placement of STM32H743; mRo Control Zero center placement; Kakute H7 MCU directly under USB-C.

---

## D — IMU_ISLAND

**Goal.** Three IMUs (ICM-42688-P + BMI088 + LSM6DSO32 or similar)
on a vibration-isolated, EMI-shielded island, **plus the IMU heater
FET + resistor for cold-start temperature stability**. The island
is mechanically decoupled via a stress-relief U-slot.

**Components:**
- U3 — IMU1 (ICM-42688-P, SPI1)
- U8 — IMU2 (BMI088 dual-die accelerometer, SPI2; ACC at U1.PB12, GYR at U1.PD4 per `imu_3c.py`)
- U9 — IMU3 (LSM6DSO32 or equivalent, SPI3)
- C41, C42, C43 — U3 decap (VDD 100nF, VDDIO 100nF, bulk 1µF)
- C91, C92, C93 — U8 decap
- C94, C95, C96 — U9 decap
- **Q5** — AO3400 N-FET driving IMU heater (G = HEATER_PWM from
  U1.PA15, D = HEATER_DRAIN, S = GND). Verified 2026-05-22 against
  `power_3b.py:549-585` — Q5 is the IMU heater driver, NOT a
  power-section FET (originally mis-listed in A).
- **R_heater (R61)** — heater resistor in series from +5V to Q5
  drain. Value TBD by Phase 6 thermal sim (under-IMU heating
  power matched to IMU thermal mass for stable start-up).

**Input nets:**
- `+3V3_IMU` (from B, via short trace across bridge)
- `+5V` (for Q5 heater drain → R61 heater)
- `GND`
- SPI1: `SPI1_SCK`, `SPI1_MISO`, `SPI1_MOSI`, `IMU1_CS` (from C)
- SPI2: `SPI2_SCK`, `SPI2_MISO`, `SPI2_MOSI`, `IMU2_ACC_CS`, `IMU2_GYR_CS` (from C)
- SPI3: `SPI3_SCK`, `SPI3_MISO`, `SPI3_MOSI`, `IMU3_CS` (from C)
- INTs: `IMU2_ACC_INT1` (PE5), `IMU2_GYR_INT3` (PE6), `IMU3_INT1` (PE11), and any IMU1 INT if wired
- `HEATER_PWM` (from C, U1.PA15 to Q5.G)

**Output nets:** (same as inputs — SPI is bidirectional; this lists the
zone-crossing nets, all of which return MOSI/MISO traffic)

**Zone:** Y=51..63, X=33..63. Compact 43×12 mm island. Stress-relief
U-kerf surrounds the island; **bridge starting at 10 mm wide** at
Y=51..53 (X=40..50) is the only mechanical+electrical connection. ALL
signal traces + power must cross the bridge. Master directive
2026-05-22: 10 mm is the *starting point* — the Elmer structural FEA
(validated in Task 9, `sims/validation/elmer_beam/`) refines the
final bridge width at the D-integration step (step 7) before D LOCKs
per Gate 12. Narrower bridge = better EMI isolation but lower
structural margin; FEA picks the trade.

**Adjacency:**
- South: C (across the bridge)
- Must NOT be adjacent to: H (ESC PWM), G connectors carrying CRSF/GPS
- The slot geometry physically enforces separation from all other zones

**Thermal vias (Gate 7):** not required; IMU dissipation ≤10 mW each.

**Reference teardowns:** Pixhawk 6X uses a SEPARATE IMU PCB
mechanically isolated (v2 mech target); v1 emulates this with a slot
+ bridge island. mRo Control Zero uses similar pattern.

---

## E — BARO_I2C

**Goal.** Two barometers (DPS310 primary + BMP388 alternate) on I2C2.
External GPS-mounted compass on I2C1 (compass IC is OFF-board).

**Components:**
- U4 — DPS310 barometer (I2C2 addr 0x76 per hwdef)
- U7 — BMP388 alternate barometer
- C51, C52, C71, C72 — per-baro VDD + VDDIO decap
- R11, R12 — I2C2 pullups (R21, R22 are I2C1 pullups in G)

**Input nets:**
- `+3V3` (NOT +3V3_IMU)
- I2C2: `I2C2_SCL` (PB10), `I2C2_SDA` (PB11)

**Output nets:** (none — sensor only)

**Zone:** Y=44..52, X=42..58 (south of U1, adjacent to PB10/PB11 on U1's
S edge). PB10 = pin 46 at (49.00, 42.67), PB11 = pin 47 at (49.50, 42.67)
on the placed U1. E sits just below U1's S edge for the shortest possible
I2C2 trace. NOT in D — barometer is acoustic-noise sensitive, NOT
vibration sensitive, so it doesn't need the slot.

**Adjacency:** C (immediately above; R11/R12 pullups sit at the seam)

**Reference teardowns:** Pixhawk 6X has BMP388 separate from IMU stack; Matek H743-Slim has DPS310 adjacent to MCU.

---

## F — USB_INTERFACE

**Goal.** USB-C connector (host-side ArduPilot port) + ESD protection
+ CC pull-downs. ≤30 mm differential pair trace from connector to MCU
PA11/PA12.

**Components:**
- J1 — USB-C connector (per `crsf_usb_3g.py` — also handles CRSF via
  separate header J10, but the USB-C connector is in F)
- R31, R32 — CC1/CC2 5.1k pull-downs (defines novapcb as USB device)
- U5 — USB ESD diode array (TPD4S014 or similar)

**Input nets:**
- `USB_DM`, `USB_DP` (from C, PA11/PA12) — controlled-impedance pair
- `VBUS`, `GND`

**Output nets:** (none — connector is the terminus)

**Zone:** X=75..90, Y=22..45 (east edge, lower-to-mid).

**Y-extension to 45** (revised 2026-05-22, Step-3 re-open): the
original Y=20..38 was too tight — the U5 SOT-23-6 ESD diode array
needed to clear the diff-pair Y=31 corridor (post-ESD pair from
U1.PA11/PA12 routes east at Y=31.0..31.33), so U5 moved south to
Y=35. F borrows Y=38..45 from G's allocation; G's net usable Y is
trimmed correspondingly (see §G).

Connector cutout on the east board edge. Trace from C to F runs
roughly horizontal, ≤30 mm (post-ESD U1→U5 + pre-ESD U5→J1 total).

**Adjacency:** C (west). Must NOT be adjacent to D (USB switching
edges can couple to IMU SPI clock).

**Controlled impedance:** USB differential pair Z_diff = 90 Ω ±15%,
**W=0.20 / S=0.13 / h=0.21 on L1** (REVISED 2026-05-22 per openEMS
3D-FDTD sign-off — measured Z_diff = 87.4 Ω, PASS within USB-2 spec
band 76.5..103.5 Ω). The earlier W=0.30 / S=0.10 spec was analytical
H-J only; openEMS measured it at 70 Ω (below the -15% floor). See
`docs/CONTROLLED_IMPEDANCE.md` for the full sign-off + the discrepancy
write-up. Note: openEMS coupled-pair SETUP validation against a
published reference is in flight as a follow-up (task #75).

**Reference teardowns:** Pixhawk 6X USB connector on the east edge; Kakute H7 USB-C on the north edge.

---

## G — EXTERNAL_IO

**Goal.** All other external connectors: telemetry, GPS+MAG, SWD,
microSD, CRSF input, CAN bus. ESD-protect each one.

**Components:**
- J2 — microSD card slot (SDMMC1 on PC8..PC12 + PD2)
- J3 — telemetry connector (UART7 on PE7/PE8 + flow control PE9/PE10)
- J5 — GPS+MAG connector (USART2 = PD5/PD6 + I2C1 = PB6/PB7 + 3V3 + GND)
- J9 — SWD connector (PA13/PA14 + NRST + 3V3 + GND)
- J10 — CRSF connector (USART6 = PC6/PC7 + 3V3 + GND)
- J20 — CAN bus connector (CAN1 from U14)
- U14 — CAN1 transceiver
- U15 — **PESD2CAN ESD diode array** for the CAN bus (verified
  2026-05-22 against `can_3j.py:170-188` — pins I/O1=CANH,
  I/O2=CANL, GND=common cathode). NOT a second CAN transceiver; no
  CAN2 in v1.1 scope; no scope discrepancy to flag.
- D11, D12 — telem RX/TX ESD diodes
- D13, D14 — CRSF RX/TX ESD diodes
- R21, R22 — I2C1 pullups
- R45, R46 — CAN1 termination + jumper
- C83, C84 — U14 decap
- C63 — microSD power decap

**Input nets:**
- `+3V3`, `GND` (to every connector + decap)
- USART1: `USART1_TX` (PA9), `USART1_RX` (PA10) — actually USART1 isn't currently mapped to a connector in G; mapped via telem_3i sheet
- USART2: `GPS1_TX` (PD5), `GPS1_RX` (PD6)
- USART6: `USART6_TX` (PC6), `USART6_RX` (PC7)
- UART7: `UART7_TX` (PE8), `UART7_RX` (PE7), `UART7_CTS` (PE10), `UART7_RTS` (PE9)
- I2C1: `I2C1_SCL` (PB6), `I2C1_SDA` (PB7)
- CAN1: `CAN1_TX` (PD1), `CAN1_RX` (PD0), `GPIO_CAN1_SILENT` (PD3)
- SDMMC1: `SDMMC1_D0..D3` (PC8..PC11), `SDMMC1_CLK` (PC12), `SDMMC1_CMD` (PD2)
- SWD: `SWDIO` (PA13), `SWCLK` (PA14), `NRST`
- BUZZER: `BUZZER` (PD7, on G if a buzzer connector exists; otherwise no connector — pin available)

**Output nets:** (none — connectors are the terminus)

**Zone:** X=75..90, Y=45..70 (east edge, upper portion — revised
2026-05-22; lower 7 mm Y=38..45 ceded to §F for U5 placement) PLUS
specific
corners:
- J5 (GPS+MAG): northeast corner Y=58..70, X=75..90 — clean antenna
  lobe direction
- J9 (SWD): cluster with J2 microSD on the east edge
- J20 (CAN): east edge, isolated from CRSF (J10) to avoid CRSF-RF
  coupling into CAN bus
- J10 (CRSF): east edge, near connector for the RX module

**Adjacency:**
- C (west, signals enter from MCU)
- D not adjacent (USB switching edges already noted; same for CRSF
  spurs into IMU)

**Thermal vias (Gate 7):** U14 CAN xcvr ≤100 mW, ≥4 vias.

**Reference teardowns:** Pixhawk 6X connector field on one short edge of the board; Kakute H7 connector field on the south edge.

---

## H — ESC_OUTPUTS

**Goal.** 8 motor signal pads (DShot300/600 capable, 3.3V logic, no
on-board driver). Plain solder pads or 1.0 mm header connectors per
`DECISIONS §3` (DShot preferred, PWM fallback) + §7 (JST-GH connector
family; for motor pads we use plain solder pad pairs).

**Components:**
- J11..J18 — 8× motor signal+GND pad pairs (`Conn_01x02`)

**Input nets:**
- `+5V_BEC` is NOT required (motors take 3.3V signal directly from MCU)
- `GND`
- `MOT1` (PB0, TIM3_CH3, BIDIR), `MOT2` (PB1, TIM3_CH4)
- `MOT3` (PA0, TIM2_CH1, BIDIR), `MOT4` (PA1, TIM2_CH2)
- `MOT5` (PA2, TIM5_CH3, BIDIR), `MOT6` (PA3, TIM5_CH4)
- `MOT7` (PD12, TIM4_CH1, BIDIR), `MOT8` (PD13, TIM4_CH2)

**Output nets:** (none — pads are the terminus)

**Zone:** X=0..18, Y=8..62 (west edge, vertical strip). 8 pads spaced
~6 mm apart. Cable exit toward the airframe ESC stack.

**Adjacency:**
- C (east of H — short trace from MCU PWM pins to pads)
- Must NOT be adjacent to D (PWM switching noise into IMU)

**Reference teardowns:** Matek H743-Slim motor pads along one long
edge; Kakute H7 motor pads at the south edge.

---

## 2. Cross-subsystem nets (handled in a separate routing PR after all
## subsystem placement PRs are locked)

These nets cross multiple subsystem zones and are NOT internal to any
one PR:

- **+3V3 plane** (global power, all subsystems consume it) — handled as
  L3 zone fill in the cross-subsystem routing PR
- **GND plane** (global ground) — L2 and L5 zones, cross-subsystem PR
- **+5V_BEC** — A → B only, very short (handled in B's PR via the
  immediately-north adjacency)
- **+3V3_IMU** — B → D only, short trace across the bridge (handled in
  B's PR; D consumes only)
- **SPI1/2/3 buses + IMU INTs** — C ↔ D across the bridge (handled in
  a small cross-subsystem PR after both C and D are locked)
- **USB diff pair** — C ↔ F (handled in F's PR with C locked)
- **CRSF UART, GPS UART, telem UART, CAN, SDMMC, SWD, motor PWMs** —
  C ↔ G or C ↔ H (handled per-cluster in cross-subsystem PR)

---

## 3. Resolution log — master's answers (2026-05-22)

The six questions raised in the draft, with master's resolutions
applied above:

1. **Q5 role — RESOLVED.** Verified against `power_3b.py:549-585`:
   Q5 is AO3400 N-FET driving the **IMU heater** (G=HEATER_PWM,
   D=HEATER_DRAIN→R61→+5V, S=GND). Q5 belongs to **D, not A**.
   Subsystem tables and component lists updated. Per Rule 3 — no
   guessing; verified.

2. **U15 role — RESOLVED.** Verified against `can_3j.py:170-188`:
   U15 is **PESD2CAN ESD diode array** (CANH/CANL ESD clamp to GND).
   NOT a 2nd CAN transceiver. v1.1 single-CAN scope is intact; no
   discrepancy to flag in `OPEN_QUESTIONS.md`.

3. **MCU exposed pad — RESOLVED.** Footprint is
   `Package_QFP:LQFP-100_14x14mm_P0.5mm` (per `mcu_3a.py:54`) — a
   standard 14×14 mm gull-wing LQFP. Standard LQFP has **no exposed
   thermal pad**. Gate 7 thermal-vias-under-U1 requirement REMOVED
   from C; the MCU dissipates through its 100 leads to the planes.

4. **Mounting holes — RESOLVED.** **4 corner-inset M3 holes at ~5
   mm** from each corner: **(5, 5), (85, 5), (5, 65), (85, 65)**.
   Master directive 2026-05-22: `DECISIONS §2` 30.5×30.5 c-to-c
   was for the original 36×36; on 90×70 it leaves ~30 mm overhang
   per side (mechanically poor). Corner holes for v1.1; the airframe
   gets a new tray anyway. `docs/OPEN_QUESTIONS.md` entry added
   for Sai's ratification (supersedes `DECISIONS §2`).

5. **Bridge width — RESOLVED.** Start at **10 mm wide** (was 14 mm
   in v13). 10 mm = better EMI isolation, still fits the IMU signal
   bundle across 3 signal layers. **Final width determined by Elmer
   structural FEA at step 7** (D integration) before D LOCKs per
   Gate 12. Validated FEA tool from Task 9 (`sims/validation/elmer_beam/`).

6. **B↔C decap ownership — RESOLVED.** **MCU decaps belong to C**
   (placed within ~3 mm of MCU power pins — the whole point of a
   decap). B owns U2/U13 LDOs + their immediate input/output bulk
   caps. The +3V3 plane is a **global cross-subsystem net** (§2),
   owned by neither A nor B nor C — it's a board-level zone-fill
   handled in the cross-subsystem routing PR.

No remaining open questions for master at the subsystem-decomp
level. Step 1 (C — MCU_CORE) placement PR proceeds.

---

## 4. Integration-order — CONFIRMED by master 2026-05-22

Per `PLACEMENT_ROUTING_GATES.md §0`, place + integrate + sim + LOCK
subsystem-by-subsystem. **Master confirmed this order verbatim:**
`C → E → F → G-partial → B → A → D → H → G-remainder(CRSF) → full-board sim`.
Master also confirmed the explicit hard-pairing steps (A↔B, C↔D bridge,
C↔H, CRSF↔D) are correct.

Each row is one **placement-step PR** followed by an
**integration-step PR** that routes the new cross-subsystem nets and
runs the relevant sims.

| Step | Subsystem | Why this position | Sim focus at integration step |
|---|---|---|---|
| 1 | **C — MCU_CORE** | The hub. Everything else's coordinates are relative to U1's pin positions. | No integration yet — internal MCU decap density + Y1 placement vs PH0/PH1 distance. Thermal: U1 worst-case T_j (validated with Elmer thermal). |
| 2 | **E — BARO_I2C** | LOW-conflict, integrates clean adjacent to C. Builds confidence in the C-zone boundaries. | C↔E I2C2 short-trace SI (negligible at 400 kHz, sanity check only). Thermal: C+E combined T_j. |
| 3 | **F — USB_INTERFACE** | LOW-conflict, anchors east edge. Validates the 90Ω diff pair against the LIVE board's L1 + GND-fill geometry (not theoretical W=0.30/S=0.10 — actual). | C↔F USB diff pair: openEMS field-solver Z_diff vs 90Ω target, eye diagram for USB FS, common-mode rejection. Density: east-edge cluster. |
| 4 | **G partial — GPS/SWD/CAN connectors (J5, J9, J20, U14, U15)** | LOW-conflict G subset. CRSF (J10) deferred to last. | C↔G low-risk paths: USART2 / SWD / CAN SI. Density: east-edge cluster + corners. Thermal: U14 CAN xcvr. |
| 5 | **B — POWER_REG_3V3** | First HIGH-conflict. Feeds C; without B, no further sims have a representative power rail. | C↔B PDN: ngspice + Elmer thermal on the +3V3 and +3V3_IMU paths (FB2 isolation verified). Anti-resonance check at 100 kHz (the Phase 6 P0 finding driving the v1.1 re-spin). |
| 6 | **A — POWER_INPUT** | HIGH-conflict, but only one neighbor (B). Integrate as a 2-subsystem step. | A↔B integration: inrush current into U2/U13 (3.39 A captured in Phase 6 P0), J4/J19 cable EMI radiation into B's region. Validate with both ngspice (transient) + openEMS (radiated). |
| 7 | **D — IMU_ISLAND** | HIGH-conflict victim. Integrate ONLY after B is locked so +3V3_IMU is in place. | C↔D bridge: SPI1/2/3 SI under load, IMU INT line cross-talk. C↔D power: +3V3_IMU PSRR + transient response with B's LDO active. Mechanical: bridge stress (Elmer structural — already validated). |
| 8 | **H — ESC_OUTPUTS** | HIGHEST aggressor. Add LAST so its noise lands on a board with D already locked — surfacing the worst-case C↔D-via-bridge coupling in the presence of motor PWM. | C↔H DShot SI; H↔C↔D worst-case EMI (PWM 0..600 kHz at sharp edges, harmonics into 100s of MHz). openEMS for radiated coupling, ngspice for conducted via shared GND. **This is the make-or-break step.** |
| 9 | **G remainder — CRSF (J10), D11..D14, R45/R46** | Last because CRSF↔D is the second-biggest coupling concern. By this step, D is locked and we can measure CRSF's actual noise floor into D under realistic load. | G:J10↔D coupling: openEMS radiated, plus measured EMI through the placed GND-via fence around J10 (if added). |
| **10** | **Full-board sim suite (no new placement)** | Final validation across the integrated board. | Complete thermal map, full EMI sweep, full SI for all controlled-impedance pairs, structural FEA. Per `PLACEMENT_ROUTING_GATES.md §0 step 5`. |

**At each step:**
- The placement PR must pass Gates 1-7.
- The integration PR must pass Gates 8-12 (scoped to the new nets) AND Gate 13 (validated tool + convergence-clean run).
- If a step fails: fix in that step's narrow context. Do NOT proceed.
- Master audits each step before LOCK.

---

— end of SUBSYSTEM_CONTRACTS.md (DRAFT) —
