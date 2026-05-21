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
| slot | proposed part | vendor | family | AP driver | bus | notes |
|---|---|---|---|---|---|---|
| IMU1 (existing) | **ICM-42688-P** (LGA-14) | TDK InvenSense | newer 6-axis | `AP_InertialSensor_Invensensev3` | SPI1 | CONFIRMED — unchanged, Pixhawk6X standard |
| IMU2 | **BMI088** (dual-package: gyro 6-pin LGA + accel 14-pin LGA, requires TWO chip-selects) | Bosch | independent gyro/accel | `AP_InertialSensor_BMI088` | SPI2 | CONFIRMED — Pixhawk6X standard; dissimilar vendor + dissimilar arch |
| IMU3 | **LSM6DSV16X** (LGA-14) | STMicroelectronics | 6-axis (HAODR) | `AP_InertialSensor_LSM6DSV` | SPI3 | CONFIRMED 2026-05-21 — driver in ArduPilot @ libraries/AP_InertialSensor/AP_InertialSensor_LSM6DSV.cpp, used by Pixhawk6C hwdef. (LSM6DSO has NO ArduPilot driver — hard-fail, rejected.) |

3 vendors covered (TDK + Bosch + STM). Independent SPI buses for fault isolation. Each IMU on its own CS + INT line. BMI088 needs 2× CS (gyro + accel).

**Dual barometer dissimilar:**
| slot | proposed part | vendor | AP driver | bus |
|---|---|---|---|---|
| Baro1 (existing) | **DPS310** (LGA-8) | **Infineon** (Rule-17 vendor correction — not Bosch) | `AP_Baro_DPS280` (covers DPS3xx) | I2C2 |
| Baro2 | **LPS22HB** (HCLGA-10) | STMicroelectronics | `AP_Baro_LPS2XH` (WHOAMI 0xB1 explicit) | I2C3 |

2 vendors. Independent I2C buses. Different sensing principle (capacitive vs piezoresistive).

**ESD on all external connectors:**
- USB-C: existing USBLC6-2P6 (U5) unchanged
- GPS+I2C (J5, 10P): add **ESD7L5.0DT5G** (4-channel array, SOT-23-6) on the 8 signal lines — 2 arrays. Acceptance pending verify: standoff 5.0V (>3.3V — OK), capacitance ≤3 pF typ (OK for ≤420 kbaud), JLC library status. R2 footprint phase confirms.
- CRSF (J10): add **ESD7L5.0DT5G** on UART RX/TX (same part — keep BOM consolidated)
- Telem (J3): add **ESD7L5.0DT5G** on UART RX/TX
- CAN (new ports): **PESD2CAN** (2-channel CAN-rated ESD) on each port
- Total: ~5-6 ESD array footprints added; all JLC-library

**IMU heater + clean low-noise IMU supply:**
- Heater resistor: value + **package TBD — sized from Tier-1-sim (b) IMU-heater thermal output**. (Master flag 2026-05-21: 100Ω 0805 on 5V ≈ 0.25W exceeds 0.125W 0805 rating. Heater power is a sim output, not a guess. Expect 2512 ~1W single resistor, or small array.)
- Heater control FET: **AO3400** (N-channel, low Vth, SOT-23) — JLC Basic-tier
- PWM control: 1 MCU GPIO pin (any free TIM channel)
- Temp sensing: use existing IMU built-in temp sensors (no extra sensor needed)
- IMU supply: dedicated **LP5907MFX-3.3** (250mA, 6.5µVRMS noise, SOT-23-5, JLC Extended C57769) for IMU rail isolated from main +3V3 by a ferrite bead on input

**IMU stress-relief slot:**
- 0.8mm-wide slot cut around the 3-IMU island in F.Cu/B.Cu + Edge.Cuts, leaving a small bridge (≥3mm) for board flex isolation. Reduces strain from mounting/temp cycling.
- Validated by Tier-2-sim (b) — mechanical/structural FEA.

### Tier 2 (high-value, included if schematic complexity stays bounded)

**Power-input redundancy with ideal-diode OR-ing:**
- 2nd power input: **JST-GH 6P, mirror of J4** (proper monitored power connector — VBAT, VCC, GND, I_sense, V_sense, ID — consistent with J4 schema). Locked 2026-05-21.
- Ideal-diode OR-ing: **LM74700-Q1** (TI ideal-diode controller, MSOP-8, JLC Extended) per input — controls a P-FET to act as low-loss diode
- Auto-switchover: whichever input is higher takes over without brownout
- Validated by Tier-1-sim (a) — power-failover transient

**CAN bus (2 ports — both FDCAN free per pin-budget):**
- STM32H743 has FDCAN1 + FDCAN2 — both available (currently unused per pin-budget analysis)
- Transceiver: **TJA1051TK/3** (NXP, TSSOP-8) — 5V supply, 3.3V-compatible I/O, JLC library. Locked 2026-05-21.
- 2 ports × 1 transceiver each + 1 JST-GH 4P connector each (CAN_H, CAN_L, +5V, GND)
- **Bus termination 120Ω per port — solder-jumper-selectable** (Pixhawk-class practice — whether FC terminates depends on its bus position; jumper closed = terminate, open = not terminate). Two pads + 120Ω 0603 + cuttable trace.
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

### 5.0 Sim-validation requirement (Sai/master directive 2026-05-21)

Before any sim's novapcb verdict is trusted, that sim must first be validated:

1. **Canonical/analytical benchmark** (always): NAFEMS validated thermal cases for Tier-2 (b); Hammerstad-Jensen + Pozar microstrip for 6b SI; OpenEMS notch-filter reference for 6k EMC; Newmark-beta integrator + analytical modal for Tier-2 (c) FEA. Already in the Phase 6 harnesses.
2. **Known-reference-PCB validation** (where one exists): run our sim on a published reference design and confirm we reproduce the published result. Where this exists, it is non-negotiable. Where it does not exist, **say so plainly in the per-sim disposition** and document that Phase 9 bench is the ultimate ground truth.

Mapping where reference PCBs DO and do NOT exist:

| Sim | Canonical benchmark | Reference-PCB validation | If no reference: |
|---|---|---|---|
| 6a power tree | Spice node-eqns, eFuse datasheet curves | **DOES exist** — TPS25940 EVM (TI eval board) published curves; LM74700 EVM data | reproduce + check |
| 6b USB SI | Hammerstad-Jensen, Pozar | **DOES exist** — KiCad demo USB project + measured TDR data from USB-IF compliance reports | publish notes if mismatch |
| 6c IMU SPI SI | Pozar transmission-line | Pixhawk6X open-source layout + ArduPilot SPI logs available — usable as reference | partial — Pixhawk lengths differ; treat as guide not gold |
| 6d I2C / 6e UART | Lumped RC + datasheet rise/fall | weak — no good published reference at our trace lengths | bench is ground truth |
| 6f SDMMC | clk/data setup-hold per JESD84 | weak | bench is ground truth |
| 6g DShot | rise-time + DShot datasheet | **DOES exist** — Betaflight/Holybro published DShot scope captures | reproduce one and cross-check |
| 6h ADC | LP5907 datasheet noise + 6a coupling | **DOES exist** — TI LP5907 EVM PSRR + ADC eval boards | reproduce |
| 6i ESD | HBM IEC-61000-4-2 standard | **DOES exist** — ESD7L/PESD2CAN datasheets contain reference clamp curves | reproduce datasheet curve |
| 6j thermal | NAFEMS thermal sets | **DOES exist** — NAFEMS T1/T2 cases + Pixhawk6X published thermal photos (qualitative) | reproduce NAFEMS quantitative; Pixhawk only qualitative cross-check |
| 6k EMC | OpenEMS notch | weak — no good drone-FC EMC reference public | bench is ground truth |
| 6l SITL | ArduPilot SITL self-check | **DOES exist** — ArduCopter SITL regression suite | already used as reference |
| **NEW (a) power-failover** | LTspice transient w/ measured cap+ESR | **DOES exist** — LM74700 EVM transient datasheet; PMP21998 TI ref design | reproduce + then run our geometry |
| **NEW (b) IMU heater** | NAFEMS thermal | **partial** — Pixhawk6X HAL_IMU_TEMP_DEFAULT=45 default + published P/I gains; no published thermal curves of that board | NAFEMS quant; Pixhawk6X qualitative only |
| **NEW (c) structural FEA** | Newmark-beta + analytical plate-modes | weak — no published FEA of a Pixhawk-class board | analytical only; Phase 9 bench measures actual board |

Sim-validation work runs **in parallel** with R3 placement / R4 routing — no schedule serialization required. Where a reference PCB is missing, the per-sim report must say so explicitly (Rule 17 — no waving off; honest disposition) and call out Phase 9 bench as the actual gate.



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

## 7. Open-question disposition (master adjudicated 2026-05-21)

**Decided (locked):**
1. IMU3 = **LSM6DSV16X** (STM) — driver `AP_InertialSensor_LSM6DSV` confirmed in ArduPilot source; LSM6DSO has no driver and was rejected.
2. IMU heater setpoint = **45°C** (ArduPilot/Pixhawk default `HAL_IMU_TEMP_DEFAULT=45`).
3. CAN transceiver = **TJA1051TK/3** (5V supply, 3.3V-compatible I/O, robust noise margin).
4. 2nd power input = **JST-GH 6P mirror of J4** (consistent monitored-power schema; not bare pads).
5. IMU1 = **ICM-42688-P kept** (unchanged from v1.0).

**Outputs of sim — decided at R6, not now:**
6. Stress-relief slot geometry/orientation — **output of Tier-2 (c) structural FEA**. Concept locked (perimeter kerf + ≥3 mm bridge); exact width/orientation FEA-decided.
7. Heater resistor value + package — **output of Tier-1 (b) IMU-heater thermal sim**. Master flag 2026-05-21: 100Ω 0805 on 5V (~0.25 W) exceeds the 0.125 W 0805 rating. Sim sizes both value and package.

**Verify-at-R2 (footprint phase):**
8. ESD7L5.0DT5G acceptance: standoff 5.0V > 3.3V signal (OK in datasheet), capacitance ≤3 pF typ vs 420 kbaud signals (OK), JLC library/tier status — confirm at footprint check.

---

**Authorized**: Sai 2026-05-21 (autonomous execution, master review per phase gate). Master to review schematic + parts list at R1 gate before placement. **Phase 7b fab order** remains Sai sign-off only.
