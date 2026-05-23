# D Placement — Up-Front Constraint Analysis

> **Status**: DRAFT for master review. NO placement committed until master
> approves the 5 decisions below + this full analysis (per master
> 2026-05-23 directive + Rule 8).
> Written 2026-05-23 after sense sub-step (`d82f08a`).

---

## 1. Subsystem I/O contract for D (zone-crossing nets)

All nets crossing into/out of D zone via the bridge or wraparound:

| Direction | Net | MCU pin | MCU edge | D-side endpoint | Notes |
|---|---|---|---|---|---|
| C→D | SPI1_SCK | U1.29 | **SOUTH** Y=42.67 | U3.11 (ICM-42688-P) | Cleanest exit — south straight |
| C→D | SPI1_MOSI | U1.31 | SOUTH Y=42.67 | U3.12 | same |
| C→D | SPI1_MISO | U1.30 | SOUTH Y=42.67 | U3.9 | same |
| C→D | IMU1_CS | U1.9 | **WEST** Y=33.00 | U3.10 | wraparound SW |
| C→D | SPI2_SCK | U1.52 | **EAST** Y=40.50 | U8.8 (BMI088) | east-then-south wrap |
| C→D | SPI2_MOSI | U1.54 | EAST Y=39.50 | U8.9 | same |
| C→D | SPI2_MISO | U1.53 | EAST Y=40.00 | U8.10 + U8.15 (BMI088 has 2 MISO pads) | same |
| C→D | IMU2_ACC_CS | U1.51 | EAST Y=41.00 | U8.14 | east-then-south |
| C→D | IMU2_GYR_CS | U1.85 | **NORTH** Y=27.32 | U8.5 | north-then-east-then-south wrap |
| D→C | IMU2_ACC_INT1 | U1.4 | WEST Y=30.50 | U8.16 | west-then-south |
| D→C | IMU2_GYR_INT3 | U1.5 | WEST Y=31.00 | U8.12 | west-then-south |
| C→D | SPI3_SCK | U1.89 | **NORTH** Y=27.32 | U9.13 (LSM6DSV16X) | wraparound — see note 1 |
| C→D | SPI3_MOSI | U1.91 | NORTH Y=27.32 | U9.14 | same |
| C→D | SPI3_MISO | U1.90 | NORTH Y=27.32 | U9.1 | same |
| C→D | IMU3_CS | U1.1 | WEST Y=29.00 | U9.12 | west-then-south |
| D→C | IMU3_INT1 | U1.41 | SOUTH Y=42.67 | U9.4 | clean south exit |
| C→D | HEATER_PWM | U1.77 | NORTH Y=27.32 | Q5.G | north-then-east-then-south wrap |
| D internal | HEATER_DRAIN | — | — | Q5.D ↔ R61.2 | local |
| C↔D power | +3V3_IMU | (FB2→U13→C78) | from B zone | C91-96, U8.3, U8.11, U9.5, U9.8 | rail entry at Y=51, X≈45 |
| C↔D power | +3V3 | (multiple) | from B zone planes | U3 (NOT +3V3_IMU — see decision 2) | rail via plane |
| C↔D power | +5V | (multiple) | from B zone planes | R61 series → Q5.D | rail via plane |
| C↔D return | GND | (multiple) | plane | All caps + IC GND pins | plane |

**Note 1 (R13 FLT corridor)**: SPI3 SCK/MOSI/MISO at U1.89-91 (NORTH
edge, Y=27.32) need to exit north then wrap around to reach D at Y≥51.
R13 (EFUSE_FLT pull-up to +5V) sits at (44.30, 24.75), 2.57mm NORTH of
the SPI3 pin row. R13 obstructs the north-exit fanout corridor for
those 3 pins.

R13 itself only connects R13.1↔U6.20 (open-drain FLT) and R13.2↔+5V.
**R13 does NOT connect to the MCU** — it's a U6-side pull-up, no FLT
readback on U1 in the current netlist. So R13 can be moved to any
location along the EFUSE_FLT trace between R13 and U6.20, OR removed
entirely if FLT is unused.

**R13/FLT contract status** (master callout, still open):
- Option α: keep R13 (FLT pull-up), move R13 east/west away from
  SPI3 fanout corridor (anywhere within U6's local proximity)
- Option β: keep R13 location, route SPI3 via a workaround (under
  R13 on different layer, or wraparound east-of-R13)
- Option γ: re-mux SPI3 in SKiDL to use SOUTH-edge pins (firmware change)
- Option δ: drop R13 entirely if FLT readback not needed and U6 doesn't require external pull (datasheet check)

**Need master sign-off** on which option before SPI3 routing for D.

## 2. Component inventory + footprint sizes

From netlist (verified 2026-05-23):

| Ref | Part | Footprint | Body (mm) | Pin count | VDD net | Notes |
|---|---|---|---|---|---|---|
| U3 | ICM-42688-P | LGA-14_3x2.5mm_P0.5mm | 3.0 × 2.5 | 14 | **+3V3** (NOT +3V3_IMU — flag) | IMU1, SPI1 |
| U8 | BMI088 | LGA-16_L4.5-W3.0-P0.50-BL | 4.5 × 3.0 | 16 | +3V3_IMU | IMU2 dual-die (ACC + GYR), SPI2 |
| U9 | LSM6DSV16X | LGA-14_L3.0-W2.5-P0.50-BR | 3.0 × 2.5 | 14 | +3V3_IMU | IMU3, SPI3 |
| Q5 | AO3400 N-FET | SOT-23-3 | 1.6 × 2.9 | 3 | gate=HEATER_PWM, drain=HEATER_DRAIN, source=GND | heater driver, hot-case 0W |
| R61 | Heater R | **R_2512_6332Metric** | 6.3 × 3.2 | 2 | series +5V → Q5.D | TBD value (Phase 6 sim); LARGE 2512 package |
| C41 | U3 100nF | C_0402_1005Metric | 1.0 × 0.5 | 2 | +3V3 + GND | U3 VDD decap |
| C42 | U3 100nF | C_0402 | same | 2 | +3V3 + GND | U3 VDDIO decap |
| C43 | U3 1µF | C_0402 | same | 2 | +3V3 + GND | U3 bulk |
| C91 | U8 100nF | C_0402 | same | 2 | +3V3_IMU + GND | |
| C92 | U8 100nF | C_0402 | same | 2 | +3V3_IMU + GND | |
| C93 | U8 1µF | C_0402 | same | 2 | +3V3_IMU + GND | |
| C94 | U9 100nF | C_0402 | same | 2 | +3V3_IMU + GND | |
| C95 | U9 100nF | C_0402 | same | 2 | +3V3_IMU + GND | |
| C96 | U9 1µF | C_0402 | same | 2 | +3V3_IMU + GND | |

**Total D footprint area**: ~75 mm² (IMUs 32 mm² + Q5 5 mm² + R61 20 mm² + caps 9× 0.5 mm² = 4.5 mm² + clearances)

**NOT included in D**: U4 DPS310 + U7 LPS22HB (those are E zone — barometers, separate I2C2).

## 3. Proposed zone boundaries

### Current contract (SUBSYSTEM_CONTRACTS §D)
- D zone: Y=51..63, X=33..63 (43 × 12 mm)
- Bridge: 10mm wide at Y=51..53, X=40..50

### Conflict with buck-to-IMU ≥25mm rule
- U2 buck @ (24, 25); L1 inductor east edge @ X=31.4
- Current D west edge X=33 → only **1.6mm** from L1 east edge
- **FAILS** buck-to-IMU ≥25mm directive

### Proposed shifts (Decision 3 — see below)

**Option (a)** — shift D east to X=49..91:
- D west edge X=49 → 17.6mm from L1 east edge X=31.4 → STILL FAILS the ≥25mm rule
- D west edge X=56 = 25mm from L1 east edge ✓; would need 12mm wider east shift (zone X=56..86 — 30mm wide, narrower than current 30mm — actually exactly same width)

**Option (b)** — accept edge-to-edge ≥25mm if measured center-to-center:
- L1 center X=29; D zone center X=48 (current Y=51..63 X=33..63 center). Distance 19mm.
- Move D zone center to X=54 (zone X=39..69) → L1-to-center 25mm. Keeps 30mm width.

**Option (c)** — restrict IMU placement within zone but keep zone bounds:
- D zone X=33..63 unchanged; IMUs placed X≥49 only (effective 14mm × 12mm = 168 mm² island, may not fit all components + spacing)

### Mid-edge mounting-hole keep-outs (master sim-gated 2026-05-23)
- West-mid: (3.0, 42.5) 8mm circular keep-out — D at Y=51..63 is south of mid-edge Y=42.5, no conflict
- East-mid: (102.0, 42.5) — same, no conflict
- D zone bounds well clear of mid-edge keep-outs

### Adjacency
- North: bridge → C zone (MCU)
- South: free, room for H ESC outputs further south
- East: free, possibly G CRSF (separation needed per EMI)
- West: free, separation from buck per Decision 3

## 4. Stress-relief slot geometry

Per SUBSYSTEM_CONTRACTS §D + master 2026-05-22 directive: single closed
Edge.Cuts polygon U-kerf around IMU island. 10mm wide bridge starting
point at the C-side (north of D zone). Audit `IMU-SLOT` check verifies
slot integrity (single closed shape).

### Proposed polygon (12 vertices, clockwise, kerf width 0.8mm)

Assuming D zone shifts per Decision 3 option (a) — example with D
zone Y=51..63, X=49..79 (revised), bridge at Y=51..53 X=56..66:

```
Vertices (mm), CW from SW corner of outer kerf:
 1. (48.6, 50.6)   — outer SW
 2. (79.4, 50.6)   — outer SE
 3. (79.4, 63.4)   — outer NE (south end of D)
 4. (48.6, 63.4)   — outer NW (south end)
 5. (48.6, 53.0)   — outer up to bridge gap south
 6. (55.2, 53.0)   — bridge gap west edge (outer)
 7. (55.2, 51.0)   — bridge top (outer to inner)
 8. (66.8, 51.0)   — bridge top east
 9. (66.8, 53.0)   — bridge east edge (inner)
10. (66.8, 53.0) → (... continue with inner perimeter clockwise ...)
... (closes back to start via inner perimeter)
```

(Full vertex list will be generated programmatically — geometry
generator + Edge.Cuts polygon writer in `generate_board.py` pattern from
prior boards.)

### FEA refinement gate
Per master 2026-05-22: bridge width 10mm = starting point. Elmer
structural FEA refines exact width at D-integration step (Phase 7
post-D-placement) — narrower bridge = better EMI isolation but lower
structural margin.

### Slot constraints
- Width 0.8 mm (fab mill cut)
- Single closed polygon (audit verifies via Edge.Cuts shape integrity)
- 10mm bridge width (initial), 0.5–2mm refinement range expected from FEA

## 5. Heater thermal model

### Component
- Q5 = AO3400 N-FET driver. Gate = HEATER_PWM (PA15 from MCU).
  Drain = HEATER_DRAIN (D-side trace).
- R61 = TBD value (Phase 6 sim out). +5V → R61 → Q5.D → Q5.S=GND.

### Cold-case (heater ON full-time)
- I = (5V − V_DS_on) / R61 ≈ 5V / R61
- For R61 = 10Ω: I = 0.5A, P_R61 = 2.5W (massive — likely too high)
- For R61 = 50Ω: I = 0.1A, P_R61 = 0.5W (reasonable for warmup)
- For R61 = 100Ω: I = 0.05A, P_R61 = 0.25W (gentler)
- Q5 R_DS_on ≈ 22mΩ → P_Q5 = I²·R_DS ≈ negligible (<10mW for ≤0.5A)
- **R61 dissipates essentially all heater power**; Q5 just switches it

### Hot-case (heater OFF — thermostatic above setpoint)
- Q5 OFF, R61 carries no current
- P_R61 = 0W, P_Q5 = 0W
- IMU local temperature rises only from ambient + adjacent components

### Thermal placement implication
- R61 (2512 package) is the LARGEST footprint in D
- R61 should be placed UNDER or ADJACENT to the IMU stack so its
  heat couples into the IMUs (the whole point of the heater)
- For 3 IMUs in island, R61 between U3 and U8 OR between U8 and U9
  (central position) gives most uniform heat distribution

### Add to gate12 COMPONENT_PROFILES for Phase 7a sanity-sweep
```python
"R61": dict(body_x=6.3, body_y=3.2, power_W=R61_VALUE_dependent),  # cold-case
"Q5":  dict(body_x=1.6, body_y=2.9, power_W=0.0),  # hot-case nominal
"U3":  dict(body_x=3.0, body_y=2.5, power_W=0.010),  # ICM-42688-P 3mA × 3.3V
"U8":  dict(body_x=4.5, body_y=3.0, power_W=0.010),  # BMI088
"U9":  dict(body_x=3.0, body_y=2.5, power_W=0.010),  # LSM6DSV16X
```

R61 value pending Phase 6 sim. Defer to that for COMPONENT_PROFILES
absolute number.

## 6. Mid-edge mounting-hole keep-out (enforced)

- H5 at (3.0, 42.5), 8mm circular pad keep-out (5.5mm pad + 1.25mm clearance × 2 = 8mm dia keep-out)
- H6 at (102.0, 42.5), same
- D zone Y=51..63 has NO conflict (mid-edge holes at Y=42.5, ~9mm north of D zone)
- IMU placement check: enforce `_bbox_within_keepout()` against mid-edge positions in step7_place_D.py (same pattern as step5/step6)

## 7. Layer plan for D routing

| Net group | Primary layer | Strategy |
|---|---|---|
| SPI1 (U3) | F.Cu | Straight south from U1 SOUTH-edge pins through bridge to U3 west pads |
| SPI2 (U8) | B.Cu | East-edge wrap around MCU SE corner, B.Cu signal channel |
| SPI3 (U9) | F.Cu + In1.Cu | North-exit + wraparound (pending R13 decision) — In1.Cu signal layer free for wraparound |
| IMU3_INT1 | F.Cu | Straight south from U1.41 |
| IMU_*_CS, INT (west) | F.Cu / B.Cu | West-edge wrap |
| HEATER_PWM | F.Cu / B.Cu | North-exit U1.77 + wraparound |
| +3V3_IMU | F.Cu local fanout | Short trace from FB2/U13/C78 (Y=27) into D north (Y=51) — bridge crossing |
| GND | In3.Cu plane (existing) | via stitching at decap pad pairs |

### Bridge bandwidth
- 10mm bridge × 2 signal layers (F+B) = ~14 trace slots at 0.20mm trace + 0.20mm clearance + 0.20mm via
- Required nets through bridge: SPI1 (4) + SPI2 (if it wraps thru bridge, 5) + SPI3 (4) + 3 INTs + HEATER_PWM + HEATER_DRAIN + +3V3_IMU = ~17 nets
- **Tight**. SPI2 likely wraps OUTSIDE the bridge (east-of-MCU then south) to reduce bridge load to ~12 nets (14-slot capacity OK)

## 8. Proposed placement (PROVISIONAL — pending master decisions)

Assuming Decision 3 = Option (a) shift D east, zone X=49..79 (or
similar), bridge centered at X=63:

| Ref | Anchor (mm) | Rationale |
|---|---|---|
| U3 (IMU1) | (52, 57) | Near bridge south, SPI1 straight down |
| U8 (IMU2) | (60, 57) | East of U3, SPI2 wraps via east-of-MCU |
| U9 (IMU3) | (68, 57) | East of U8, SPI3 wraps via north-then-east-then-south |
| Q5 (heater FET) | (55, 60) | South-east of U3, HEATER_PWM accessible |
| R61 (heater R) | (60, 60) | Central below IMUs for uniform heating |
| C41/C42/C43 (U3 decap) | (50, 58.5)..(54, 58.5) | West/north of U3, ≤1mm body-edge |
| C91/C92/C93 (U8 decap) | (58, 58.5)..(62, 58.5) | Adjacent to U8 |
| C94/C95/C96 (U9 decap) | (66, 58.5)..(70, 58.5) | Adjacent to U9 |

All numbers contingent on master sign-off below.

## 9. Decisions needed from master BEFORE D placement

1. **IMU set**: keep mixed (U3 ICM-42688-P + U8 BMI088 + U9 LSM6DSV16X)
   per netlist OR amend SKiDL to triple ICM-42688-P (firmware impact)?
   Netlist truth ≠ master's "triple ICM" reference.

2. **U3 rail**: stays on +3V3 (per netlist) OR amend SKiDL to put U3 on
   +3V3_IMU (per contracts §D)? Affects EMI isolation consistency.

3. **D zone position**: where? Three options analyzed:
   a. Shift east to X=56..86 — IMU center 25mm from L1
   b. Accept edge-to-edge with plane shielding rationale
   c. Restrict IMU to X≥49 within unchanged zone — fits but tight
   Recommendation: (a) with new bridge X=63 (was 45) — clean 25mm
   compliance, no scope creep on existing buck/sense layouts.

4. **SPI3 wraparound + R13 corridor**: which of these 4 sub-options?
   α. Move R13 east/west (R13 not connected to MCU, only U6 — free to relocate)
   β. Route SPI3 around R13 on different layer
   γ. Re-mux SPI3 in SKiDL to SOUTH-edge pins (firmware change)
   δ. Drop R13 if FLT pull-up not needed (datasheet check — likely
      needed since U6 open-drain output)
   Recommendation: α (move R13 — minimal change, no firmware impact).
   New R13 position: (47, 24) or similar, clear of SPI3 fanout column.

5. **Bridge width**: 10mm starting (Elmer FEA refine post-placement)
   OR commit to specific width now for routing-bandwidth certainty?
   Recommendation: keep 10mm starting; FEA at D-integration is fine
   since routing-bandwidth analysis (§7) shows 14 slot capacity > 12
   required nets.

## 10. Pre-existing issues to resolve before D commit

- **R13 FLT firmware contract** (master callout): tied to Decision 4
  above. Confirm SKiDL doesn't add an MCU-side EFUSE_FLT consumer
  later; if it does, R13 must stay on a routed EFUSE_FLT path.

- **Audit SINGLE_INSTANCE comment drift**: `scripts/audit_layout_compliance.py:177-186`
  comments say "U3, U7, U16 — IMU island (3× ICM-42688-P)" but netlist
  has U3=ICM, U7=LPS22HB(baro), no U16. Will fix comments in cleanup PR.

- **Task #91 (U6 DECOUPLING fail)**: not D-blocking but related to U6
  area — pending separate.

---

**Awaiting master sign-off on decisions 1-5 + the full analysis
package before any D placement script commits.**
