# novapcb v1.1 — Redundancy Re-Spin Scope

> **Status**: locked 2026-05-21 by Sai (via master). Scope feasibility confirmed by pin-budget + BOM-PCBA analyses on the current single-IMU board (commit a616b0c, tag `v1.0-pre-redundancy-decision`). Clean re-spin from revised schematic — NOT a patch on the current churned board.
>
> **Why this exists**: the current single-IMU v1.0 board is a fab-ready autopilot but lacks Pixhawk-class redundancy. Sai's decision: ship a v1.1 with triple-IMU + dual-baro + power-input redundancy + connector ESD before fab.

---

## 1. The current baseline (preserved)

- **Tag**: `v1.0-pre-redundancy-decision` (commit eeff854 on branch `sim/step6-precursor-reroute`)
- **State**: signal routing byte-equivalent to reference (629 tracks / 70 vias), 0 inner-layer misroutes, 4 inner planes solid, F.Cu/B.Cu GND pours added, safer-close 5/29 done (24 plane-pad residuals open), 10 documented benign DRC warnings.
- **What works**: single-IMU autopilot, JLC-PCBA-assemblable (33 of 43 BOM line items in JLC library; 10 intentional solder pads for ESC/CRSF + mounting holes). Pin-budget analysis: 45 unassigned GPIOs + 5 free SPI + 2 free I2C + 4 free USARTs — massive headroom for v1.1 additions.
- **Use as fallback**: if v1.1 scope hits an unforeseen blocker, the v1.0 baseline ships.

## 2. v1.1 additions

### Tier 1 (mandatory for v1.1 ship)

**Triple-IMU dissimilar, each on its own SPI bus:**
| slot | proposed part | vendor | family | JLC | bus | notes |
|---|---|---|---|---|---|---|
| IMU1 (existing) | **ICM-42688-P** (LGA-14) | TDK InvenSense | newer 6-axis | C1850418 (Extended) | SPI1 | unchanged |
| IMU2 | **BMI088** (dual-package: gyro LGA-16 + accel LGA-14) | Bosch | independent gyro/accel | LCSC C476030 / C476029 (Extended) | SPI2 | Pixhawk-class standard; dissimilar vendor + dissimilar arch |
| IMU3 | **LSM6DSO** (LGA-14) | STMicroelectronics | 6-axis | LCSC C381650 (Extended) | SPI3 | Third vendor; very common, low-cost, JLC-stocked |

3 vendors covered (TDK + Bosch + STM). Independent SPI buses for fault isolation. Each IMU on its own CS + INT line.

**Dual barometer dissimilar:**
| slot | proposed part | vendor | JLC | bus |
|---|---|---|---|---|
| Baro1 (existing) | **DPS310** (LGA-8) | Bosch | C220330 (Extended) | I2C2 |
| Baro2 | **LPS22HB** (HCLGA-10) | STMicroelectronics | LCSC C247196 (Extended) | I2C3 |

2 vendors. Independent I2C buses. Different sensing principle (capacitive vs piezoresistive).

**ESD on all external connectors:**
- USB-C: existing USBLC6-2P6 (U5) unchanged
- GPS+I2C (J5, 10P): add **ESD7L5.0DT5G** (4-channel array, SOT-23-6) on the 8 signal lines (I2C, GPS UART, BUZZER, safety) — 2 arrays
- CRSF (J10): add **PESD3V3L5UF** or **ESD7L5.0DT5G** on UART RX/TX
- Telem (J3): add **ESD7L5.0DT5G** on UART RX/TX
- CAN (new J*): add **PESD2CAN** (2-channel, dedicated CAN ESD) on each port
- Total: ~5-6 ESD array footprints added; all JLC-library

**IMU heater + clean low-noise IMU supply:**
- Heater resistor: 100Ω 0805 (0.5W rating) dissipating ~250 mW @ 5V control
- Heater control FET: **AO3400** (N-channel, low Vth, SOT-23) — already JLC Basic-tier
- PWM control: 1 MCU GPIO pin (any free)
- Temp sensing: use existing IMU built-in temp sensors (no extra sensor needed)
- IMU supply: dedicated **LP5907MFX-3.3** (250mA, 6.5µVRMS noise, SOT-23-5, JLC Extended C57769) for IMU rail isolated from main +3V3 by a small inductor (ferrite bead FB on input)

**IMU stress-relief slot:**
- 0.8mm-wide slot cut around the 3-IMU island in F.Cu/B.Cu + Edge.Cuts, leaving a small bridge (≥3mm) for board flex isolation. Reduces strain from mounting/temp cycling.
- Validated by Tier-2-sim (b) — mechanical/structural FEA.

### Tier 2 (high-value, included if schematic complexity stays bounded)

**Power-input redundancy with ideal-diode OR-ing:**
- 2nd power input: another JST-GH 6P connector (J4-like) for a 2nd BEC source
- Ideal-diode OR-ing: **LM74700-Q1** (TI ideal-diode controller, MSOP-8, JLC Extended) per input — controls a P-FET to act as low-loss diode
- Auto-switchover: whichever input is higher takes over without brownout
- Validated by Tier-1-sim (a) — power-failover transient

**CAN bus (2 ports if both FDCAN free):**
- STM32H743 has FDCAN1 + FDCAN2 — both available (currently unused per pin-budget analysis)
- Transceiver: **TJA1051TK/3** (NXP, SOIC-8 or TSSOP-8) — 5V supply, 3.3V logic, JLC library
- 2 ports × 1 transceiver each + 1 JST-GH 4P connector each (CAN_H, CAN_L, +5V, GND)
- Pixhawk-standard UAVCAN/DroneCAN compatibility

### Unchanged

- 8 ESC outputs (J11-J18, DShot300/600 + GND solder pads)
- MCU STM32H743VIT6 (U1) + 8 MHz crystal (Y1) — pin budget confirms triple-IMU+dual-baro fits trivially
- USB-C host (J1) + USBLC6 ESD (U5)
- microSD slot (J2, J3 telemetry, J4 Mauch power, J5 GPS, J9 SWD, J10 CRSF)
- Power tree: eFuse front-end (U6 TPS25940), Q2 reverse-polarity P-FET, D1 SMAJ6.0A TVS, AP2112K LDO main +3V3
- Form factor: 80 × 60 mm 6-layer JLC06161H-7628 stackup (any growth post-revision is plus-size)

## 3. Carry-forward (do NOT redo)

- **Corrected JLC ruleset** (`docs/JLCPCB_MANUFACTURABILITY.md` + `hardware/kicad/novapcb-layout-v2/jlcpcb.kicad_dru`): min trace 0.10, min space 0.10, min drill 0.20, min via 0.46, annular ≥0.13mm, hole-to-hole ≥0.50, silk/mask clearances enforced. Reuse verbatim.
- **Footprint library**: all custom footprints (ICM-42688-P, mounting holes, JST-GH variants, eFuse QFN, etc.) — carry forward as-is.
- **Stackup**: JLC06161H-7628 6-layer locked; 1oz outer / 0.5oz inner; 0.21mm prepreg L1↔L2 for USB controlled-impedance.
- **Sim harnesses** in `sims/` — 6a power tree, 6c IMU SPI, 6f SDMMC, 6g DShot, 6i ESD, 6j thermal, 6k EMC, 6l SITL — all re-runnable on new geometry with minimal updates.
- **Routing recipe**: pristine 2-layer Freerouting DSN patch (omit inner-layer + plane decls + clean padstacks → run + import + SES) — proven 2.8 min run on 80×60.
- **Validated subsystems**: USB pair geometry (94.4Ω symmetric stackup, F.Cu+B.Cu acceptable with GND-stitch), MCU + crystal, power-tree iter 4 (eFuse + Q2 + D1), microSD, ESC, basic UART/I2C connectors.
- **Phase 7a freeze procedure** (`docs/PHASE7A_FREEZE_PROCEDURE.md`): the gate definition (0 DRC errors + 0 unconnected + every warning verified+documented). Carry forward.

## 4. Phase plan

| phase | inputs | outputs | gate |
|---|---|---|---|
| **R1: schematic revision** | this scope doc | revised `novapcb-v1.kicad_sch` family + netlist + ERC clean | master reviews schematic + parts list BEFORE placement |
| **R2: footprint check** | parts list | confirmed footprints (library or custom) + pad geometry verified | every new part has a verified footprint, JLC LCSC ID, datasheet ref |
| **R3: placement** | netlist + footprints | new `.kicad_pcb` with components placed (+ IMU stress-relief slot in Edge.Cuts) | thermal budget reasonable; controlled-impedance corridor preserved; placement strategy documented |
| **R4: routing** | placement | full routed board (pristine 2-layer Freerouting + USB hand-route per the master-validated approach) | 0 inner-layer misroutes; USB F.Cu+B.Cu microstrip 94.4Ω with GND stitching |
| **R5: plane stitch** | routed signals | every plane-net pad connected (pour + via + short trace as needed) | 0 unconnected; outer-pour + cluster-via discipline from v1.0 |
| **R6: sim suite** | finalized board | full Phase-6 re-run + 3 NEW sims (see §5) | per-sim PASS or honest-disposition; Phase 6.5 forum review queue updated |
| **R7: JLCPCB DFM** | board + ruleset | corrected DRC + gerber DFM verified | 0 errors + warnings documented |
| **R8: Phase 7a freeze** | DFM-clean board | tag `v1.1-fab-ready-frozen` | Sai sign-off only |

## 5. Simulation plan (Phase-6 re-run + 3 NEW)

### Phase 6 re-run on new geometry

- 6a power tree (eFuse + new OR-ing + LP5907 IMU rail)
- 6b USB diff-pair SI (analytical H-J + Phase 9 bench floor — unchanged geometry, expected unchanged result)
- 6c IMU SPI SI — **now THREE buses** (SPI1/SPI2/SPI3), each at its own routed length; check setup/hold + ringing per bus; **inter-bus crosstalk** if buses run adjacent
- 6d I2C (2 buses), 6e UART, 6f SDMMC, 6g DShot — re-run on new routed geometry
- 6h ADC noise (LP5907 IMU rail will reduce digital coupling)
- 6i ESD — re-assess with new connector arrays installed
- 6j thermal — re-run with IMU heater dissipation added to the budget
- 6k EMC — new clocks (3 IMUs each at 24 MHz SPI, 2nd baro at I2C bus rate) added to Fourier analysis
- 6l SITL — unchanged, still valid

### NEW required sims (R6 gate)

**(a) Power-failover transient** — required
- Models: 2 inputs with realistic source-impedance + cap network on each side
- Trigger: input-1 cut at t=0; OR-ing IC switches to input-2
- Verify: +5V rail dips < 4.0V for < 10ms (UVLO threshold), no brownout reaching downstream LDO
- Tool: ngspice transient (validated tool)
- Pass criterion: rail held ≥ 4.5V throughout switchover

**(b) IMU-heater active thermal model** — required
- Models: 3 IMUs + heater resistor + ambient + heater control loop
- Goal: prove heater holds IMU temp at 40-50°C (Pixhawk-typical setpoint) without overheating (>85°C) or disturbing the adjacent barometer (>1°C drift)
- Tool: Elmer FEM transient thermal (validated in Phase 0.6); steady-state + step-disturbance cases
- Pass criterion: IMU temp 40-50°C ±5°C; baro adjacent temp drift < 1°C

**(c) Mechanical/structural FEA for IMU stress-relief slot** — required
- Models: 80×60 board with slot, 4 mounting points, 1g + temp-cycle strain loads
- Goal: prove the slot reduces strain at the IMUs by ≥50% vs no-slot baseline (Pixhawk-class spec); 1st mode > 200 Hz (avoid vibrational resonance with motors)
- Tool: Elmer FEM structural (validated in Phase 0.6 for thermal; structural module also available)
- Pass criterion: strain reduction ≥ 50% at IMU centers; 1st modal freq > 200 Hz

### Extensions (high-value)

- **CAN-bus SI** — TJA1051 + JST-GH connector + 5-meter cable model; verify dominant/recessive edge times + 1 Mbit/5 Mbit CAN-FD eye
- **3-IMU SPI inter-bus crosstalk** — adjacent-bus interference at the routed-trace level (capacitive coupling at GHz harmonics)
- **ESD impulse on each new connector** — HBM 2kV pulse through ESD array, verify clamped voltage at downstream pin

## 6. Risks & contingencies

- **Placement complexity**: triple-IMU + 2 CAN + 2 power inputs + heater + LP5907 = 7-10 more components vs v1.0. Board may grow from 80×60 to ~85×65 to maintain margin. Acceptable; thermal margin only improves.
- **Stress-relief slot**: cuts a physical kerf in the board — needs careful routing of the IMU SPI buses to AVOID crossing the slot. Adds layout constraint.
- **Cost**: +5 Extended parts × ~$0.50 setup each = ~$2.50 extra non-recurring per board at JLC. Negligible.
- **Sim-time**: 3 new sims add ~half-day of sim work each on first pass. Within Phase R6 scope.

## 7. Open questions to resolve at R1 (schematic review)

1. **3rd IMU choice**: LSM6DSO confirmed, or alternative like ICM-20649 (TDK older family for vendor-internal redundancy)? Sai/master picks.
2. **IMU heater setpoint**: 40°C, 45°C, or 50°C? (Trade: lower = less power, higher = better vibration stability; Pixhawk default is 45°C.)
3. **CAN voltage**: 5V transceiver (TJA1051 + level-shifted to 3.3V MCU) or 3.3V-only (SN65HVD230)? TJA1051 more robust; SN65HVD230 simpler.
4. **2nd power input style**: JST-GH 6P (mirror J4) for Mauch-style, or a generic 2-pin solder pad for raw 5-30V?

These get answered at R1 review.

---

**Authorized**: Sai 2026-05-21 (autonomous execution, master review per phase gate). Master to review schematic + parts list at R1 gate before placement. **Phase 7b fab order** remains Sai sign-off only.
