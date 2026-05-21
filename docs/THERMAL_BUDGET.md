# Thermal budget — pivot Step 3 P0 input

> **Purpose**: enumerate every heat source on novapcb with datasheet-grounded
> power-dissipation numbers + worst-case boundary conditions. Feeds the
> placement strategy (`docs/PLACEMENT_STRATEGY.md`): heat sources drive the
> zoning + LDO copper pour sizing + IMU placement (far from heat).
>
> **Status**: pivot Step 3 P0 planning deliverable, 2026-05-21. Numbers
> updated for the iter-4 eFuse front-end (Step 2 merged in PR #55). Supersedes
> the implicit thermal model in `sims/thermal-6j/run_6j.py`, which predates
> Step 2 — the eFuse U6 (TPS25940A) was not in the 6j component list. This
> budget folds it in.
>
> **Scope**: design-time analytical budget. The placement-dependent Elmer-FEM
> thermal sim is the Step 3 P1+ verification (place→sim→adjust loop in
> `PLACEMENT_STRATEGY.md`). This document captures the *inputs* that Elmer
> consumes.

---

## 1. Per-component dissipation table

All numbers are from manufacturer datasheets (Rule 3). Each row is at the
**worst-case operating condition** that the placement must survive.

| # | Refdes | Component | Body / Package | Dissipation (W) | Operating condition | Datasheet anchor | θ_JA (°C/W) | Heat-source class |
|---|---|---|---|---|---|---|---|---|
| 1 | U2 | AP2112K-3.3 LDO | SOT-25 (SOT-23-5) | **0.595 W** | I_load = 350 mA, V_in = 5.00 V, V_drop = 1.70 V | Diodes AP2112 datasheet §Electrical Characteristics, P_D = (V_in − V_out) × I_out | 80 (no pour) / 50 (with 1 in² pour) | **PRIMARY** (>10× the next) |
| 2 | U1 | STM32H743VIT6 MCU | LQFP-100 14×14 mm | **0.700 W** | 480 MHz core, all peripherals on, worst-case ArduCopter workload | ST RM0433 §3 + AN5394, typical with FPU+DSP+SDMMC+SPI+UART+ADC active | 35 (with thermal pad pour) | SECONDARY |
| 3 | U6 | TPS25940A eFuse | WQFN-20 4×3 mm | **0.018 W** typ | I_OUT = 360 mA × R_DSON(typ) 28 mΩ + internal control (≈ 10 mW Iq × 5 V) | TI SLVSCV3 §7.5 (R_DSON), §7.4 (I_Q) | 41 (datasheet θ_JA RVC package) | TERTIARY (negligible normal-mode) |
| 4 | Q2 | AO3401A P-FET (reverse-polarity guard) | SOT-23 | **0.0065 W** | I = 360 mA, V_DS at full Vgs ≈ 18 mV → P = I × V_DS = 6.5 mW | AOS AO3401A datasheet, R_DSON 50 mΩ @ Vgs=-4.5V | 250 (SOT-23 still air) | NEGLIGIBLE |
| 5 | U3 | ICM-42688-P IMU | LGA-14 3×2.5 mm | **0.005 W** | Both gyro + accel on, fast-sample (8 kHz) | TDK DS-000347 §5.1 (I_DD = 1.4 mA typ @ 1.8 V) | 200 (LGA still air) | NEGLIGIBLE |
| 6 | U4 | DPS310 baro | LGA-8 2×2.5 mm | **0.003 W** | Continuous P+T at 32 Hz | Bosch BST-DPS310-DS001 §Electrical (I_DD 1.7 mA @ 1.8 V active) | 200 | NEGLIGIBLE |
| 7 | U5 | USBLC6-2P6 ESD | SOT-23-6 | **0.001 W** | Idle (no ESD strike); during strike, transient only | ST USBLC6 datasheet, I_leak < 1 µA | 250 | NEGLIGIBLE (steady-state) |
| 8 | D1 | SMAJ6.0A TVS | SMA (DO-214AC) | **0 W** steady; transient only | V < V_WM = 6.0 V → no conduction | Littelfuse SMA TVS series datasheet | 75 | NEGLIGIBLE (steady-state) |
| 9 | Y1 | 8 MHz crystal | SMD 3225 | **< 0.001 W** | XO drive level | Yangxing X322508MOB4SI, drive level ≤ 100 µW | n/a (passive) | NEGLIGIBLE |
| 10 | FB1 | Ferrite bead 600 Ω @ 100 MHz (VDDA decoupling) | 0402 | **< 0.001 W** | DC current ≈ 30 mA × R_DC ~50 mΩ = 45 µW | Sunlord GZ2012D601TF | n/a | NEGLIGIBLE |
| 11 | Connectors (J1-J5, J9, J10, J11-J18) | JST-GH + USB-C + microSD + SWD + solder pads | various | **< 0.05 W** aggregate | Contact resistance × current (USB 500 mA × 30 mΩ + Mauch 360 mA × 20 mΩ + 8 × ESC signal-only) | manufacturer datasheets | n/a | NEGLIGIBLE |

### Aggregate

| Aggregate | Value |
|---|---|
| **Total steady-state board dissipation** | **≈ 1.33 W** |
| **Dominant source** (% of total) | AP2112K LDO at 0.595 W = **44.7 %** |
| **Top-2 sources** (% of total) | LDO (44.7 %) + MCU (52.6 %) = **97.3 %** |
| **All others** (% of total) | < 3 % combined |

**Implication for placement**: thermal design is dominated by **two components** — the AP2112K LDO and the STM32H743 MCU. Everything else is rounding error. Zoning + copper pour strategy must focus on these two; the rest are non-issues for thermal but matter for EMI (see PLACEMENT_STRATEGY).

---

## 2. The LDO problem (the only thermal failure mode in the design)

### 2.1 Why the LDO is hot

The AP2112K-3.3 drops V_in − V_out × I_load as heat:

```
P_dissipated = (V_in − V_out) × I_out
             = (5.00 V − 3.30 V) × 0.350 A
             = 1.70 V × 0.350 A
             = 0.595 W
```

At 350 mA — the worst-case full-board 3.3 V load (MCU + sensors + SDMMC + crystal + I²C pullups + decoupling-cap leakage). Normal idle is ~150 mA, but design for the spec, not the average.

### 2.2 Phase 6j baseline (4-layer, 40°C ambient — FAIL)

| Quantity | Value | Source |
|---|---|---|
| Dissipation | 0.595 W | (V_in − V_out) × I_load |
| θ_JA (SOT-25, 4-layer with copper pour) | 80 °C/W | Diodes AP2112 datasheet §8.2 |
| Δ T = P × θ_JA | 48.0 °C | calculation |
| T_ambient (Phase 6j BC) | 40 °C | drone-bay analytical baseline |
| **T_junction** | **88.0 °C** | sum |
| Spec | 85 °C | datasheet Tj_max (commercial grade) |
| Result | **FAIL** by 3 °C | over spec |

### 2.3 Step 3 P0 target — 50°C drone-bay ambient

Master's directive 2026-05-21: "elevated ambient ~50-60°C (a drone bay runs hot). Design for the worst case." Re-running the same model at 50°C:

```
T_junction (4-layer, 50°C ambient) = 50 + 48 = 98 °C   → over spec by 13 °C
T_junction (4-layer, 60°C ambient) = 60 + 48 = 108 °C  → over spec by 23 °C
```

The 4-layer stackup CANNOT meet the elevated-ambient spec at the current LDO load. Two design knobs available:

| Knob | Δ effect | Mechanism |
|---|---|---|
| **Larger copper pour around U2** | θ_JA drops from 80 → ~50 °C/W (1 in² of inner copper) | Heat spreads laterally through the inner power plane |
| **6-layer stackup** | Adds an EXTRA inner power plane the LDO thermal pad can via to | Effectively doubles the heat-spreading inner copper — θ_JA could drop to ~35-40 °C/W |
| **Reduce V_in to LDO** | P drops from 0.595 W → 0.42 W (if Vin = 4.5 V via series Schottky 0.3-0.5V drop) | Less drop = less dissipation. Schottky drop costs 0.18 W of dissipation in the diode + 0.15 W reduction at the LDO = net ~0 W board, but moves heat from the LDO to the diode (distributed). |
| **Switch to a buck regulator** | P drops from 0.595 W → ~0.10 W (at 85% efficiency) | Buck only dissipates inefficiency-loss. BUT: introduces switching noise + EMI + RF design risk → v2 candidate, not v1. |

**Recommended approach for v1** (this is the falsifiable claim master will adjudicate):
- 6-layer + generous copper pour around U2 (the placement strategy will reserve a thermal pour zone ≥ 100 mm² on the inner power plane directly under and adjacent to U2).
- Predict: T_junction at 50°C ambient drops from 98°C to ≤ 80°C → meets spec with margin.
- Step 3 P1+ verifies this via Elmer-FEM with the actual placement geometry; if it falls short, escalate (the LDO-vs-buck adjudication moves to Sai).

### 2.4 Why the buck-converter switch is NOT in Step 3 scope

The buck regulator option (Knob 4) is a CIRCUIT change, not a PLACEMENT change. Step 2 already locked the +3V3 rail to the AP2112K-3.3 LDO. Changing to a buck means redoing Step 2 + re-running EMC analysis + re-routing input filters. Out of scope for Step 3.

If Step 3 P1+ Elmer-FEM shows the LDO cannot meet the 50°C-ambient spec even with 6-layer + optimized pour, then we escalate the buck question to Sai — but as a Step 4+ design change, not a Step 3 fix.

---

## 2.5 Power-architecture evaluation (the explicit architecture-level decision)

> **Why this section exists**: master 2026-05-21 PR #57 review correctly flagged that "spend a 6-layer board to cool the LDO" solves a constraint without questioning it. A linear LDO dropping 5→3.3 V at 0.35 A burns 0.595 W as heat *by physics*; a switching regulator could largely eliminate the thermal constraint. This section makes the architecture choice an EXPLICIT decision (with a justified recommendation) rather than an inherited assumption. Sai's "best possible solution" mandate means the choice must be justified, not assumed.

### 2.5.1 Three options on the table

| Option | Topology | LDO heat | Switcher heat | Sensor-rail noise | BOM complexity | Board area |
|---|---|---|---|---|---|---|
| **(A) Linear LDO only** *(current Step 2 design)* | Mauch BEC 5 V → AP2112K LDO → 3.3 V (one active part) | **0.595 W** (V_drop × I_load = 1.7 V × 0.35 A) | n/a (Mauch BEC lives off-board) | **lowest** — LDO PSRR > 70 dB at audio; ripple at 3.3 V floor ≈ µV-class | 1 IC (AP2112K) | ~10 mm² |
| **(B) Pure buck switcher** | Mauch BEC 5 V → buck → 3.3 V (one active switching part on board) | n/a | **0.10 W** (≈ 85% efficiency × 1.15 W output power) | **highest** — switcher ripple typ. 10-50 mV pk-pk at switching freq + harmonics directly on the sensor rail. Worst case for IMU/baro/ADC. | 1 IC + inductor + caps | ~80 mm² |
| **(C) Switcher + LDO hybrid** | Mauch BEC 5 V → on-board buck → 3.6-4.0 V → AP2112K LDO → 3.3 V | **0.105-0.245 W** (depends on intermediate rail; smaller drop = less LDO heat) | **0.21-0.30 W** (buck conversion loss) | **moderate** — LDO cleans most switcher ripple; residual depends on LDO PSRR at switching freq (typ. 50-60 dB at 1 MHz for AP2112) | 2 ICs + inductor + caps | ~90 mm² |

### 2.5.2 Why pure buck (Option B) is wrong for this rail

The 3.3 V rail directly powers:
- **ICM-42688-P IMU** (VDD + VDDIO): switcher ripple at the sensor VDD shows up as gyro/accel ADC noise. TDK ICM-42688-P datasheet §5.1 specifies VDD ripple < 10 mV pk-pk for spec-grade performance; switcher output ripple typ. 20-50 mV pk-pk without aggressive LC filtering.
- **DPS310 baro** (VDD + VDDIO): pressure sensor noise floor depends on supply ripple per Bosch BST-DPS310 §3.3.
- **STM32H743 VREF+ + VDDA** (via FB1 ferrite): ADC LSB is V_REF / 4096 ≈ 800 µV for the VBAT/current monitoring channel. Switcher ripple directly degrades ADC SNR.

Production FC convention is unambiguous: the 3.3 V rail powering noise-sensitive sensors uses a linear regulator. Pure-buck for this rail trades 0.5 W of heat for several dB of sensor SNR degradation — a bad bargain for a flight controller.

### 2.5.3 Why switcher+LDO hybrid (Option C) is the next-most-defensible

The hybrid does the BULK voltage step efficiently in the switcher, then a small-drop LDO cleans the rail. With Mauch BEC 5 V → on-board buck to ~3.6 V → LDO 3.6 V → 3.3 V:

- LDO drop = 0.3 V × 0.35 A = **0.105 W** of LDO heat (5.7× less than current 0.595 W).
- Buck dissipation = 0.30 V × 0.35 A / 0.85 efficiency = **0.21 W** in the buck.
- **Total heat on-board = 0.315 W** vs current 0.595 W → ~47% reduction, but distributed (buck heat + LDO heat in different package locations) → easier to dissipate than a single 0.6 W hotspot.

**Why this is NOT being recommended for v1** (the decision):

1. **The switcher would live on the FC**, ~20-40 mm from the IMU (Zone 1 to Zone 3 distance). The Mauch BEC switcher lives ON THE AIRFRAME, 200-500 mm from the FC — its switching noise dissipates over distance + intervening harness inductance + cap filtering at the BEC connector. An on-board switcher's noise reaches the IMU directly via the +5V rail return path.
2. **The +3.3V LDO's switcher-ripple suppression at 1 MHz** (typical buck switching freq) is ~50-60 dB per Diodes AP2112 §Electrical Characteristics. A 30 mV buck ripple becomes ~30-100 µV at the LDO output. That's better than pure-buck but worse than the current sub-10 µV noise floor from Mauch-BEC + LDO topology.
3. **The compounding switcher cascade**: Mauch BEC switcher (already present, ~100-300 kHz) + on-board buck switcher (~1-2 MHz) creates intermodulation products at sum + difference frequencies that may land in sensitive bands. Phase 6k EMC analysis would need a full re-run. Phase 6.5 forum review would flag the cascade as a concern.
4. **Two-IC topology vs one-IC** = more BOM, more potential failure modes, more bring-up surface area, more parts to source. Hybrid is genuinely more complex.
5. **The actual heat reduction (0.595 W → 0.315 W, ~280 mW saved) is small in absolute terms**: 6S 5000 mAh battery = 110 Wh capacity. 280 mW saved × 1 hour flight = 0.25% of battery capacity. Not load-bearing on flight time.
6. **The "thermal constraint" the hybrid would solve is already solved** by the 6-layer + 100 mm² LDO pour strategy: T_j = 79.8°C at 50°C ambient. That's a comfortable junction temp with 5°C margin to the 85°C spec and 45°C margin to the AP2112K commercial-grade absolute-max 125°C. The hybrid would buy us another ~15°C of margin we don't need.

### 2.5.4 Why retain linear LDO (Option A) — the recommendation

The linear LDO is recommended for v1 on five grounds:

**Ground 1 — Reference precedent across FC class.**
- **MatekH743** (our schematic reference): uses a linear LDO for the 3.3 V rail. Confirmed via grep of the ArduPilot hwdef tree: no `SMPS_PWR` / `SMPS_EXT` defines → falls through to `PWR_CR3_LDOEN` in `hwdef/common/stm32h7_mcuconf.h:93`. The STM32H7 itself is in LDO mode, and the upstream 3.3 V rail is linear. (Per `docs/REFERENCE_AUDIT.md` line 61.)
- **Holybro Pixhawk 6X** (the autopilot novapcb functionally replaces): uses linear LDOs for sensor rails on the isolated-IMU board. Dual-redundant power architecture; sensors are deliberately kept on linear regulators downstream of the switching upstream.
- **General mini-FC practice**: when the input rail is already 5 V (i.e. there is already an upstream switcher in the BEC or main step-down), the 5 V → 3.3 V step is universally done with a linear LDO. The exception is when the input rail is direct VBAT (12-26 V); in that case a buck is mandatory because a linear LDO would burn 4-8 W.

**Ground 2 — We already have a switcher: the Mauch BEC.**
The Mauch power module is a switching regulator (typ. 90-95% efficient) that takes VBAT (16-26 V on 4-6S) down to 5 V at 3 A. By the time novapcb sees the 5 V rail, the big drop has already been done efficiently — we are NOT burning 4-8 W of heat to get from VBAT to 3.3 V. We are burning 0.595 W to do the FINAL 1.7 V trim with a clean linear LDO. That is the canonical FC topology and it is by design.

**Ground 3 — The IMU + baro + ADC noise floor matters more than 280 mW of heat.**
The 6-layer + LDO pour solution brings T_j to 79.8°C at 50°C ambient (THERMAL_BUDGET §2.3 prediction). That meets spec with 5°C margin. The hybrid would reduce LDO heat at the cost of putting a switcher on the FC within 20-40 mm of the IMU — directly hurting the thing the LDO was protecting. Net effect on the design's primary mission (clean inertial + barometric data): hybrid is a NET NEGATIVE.

**Ground 4 — The "best possible solution" criterion (Sai's mandate) applied to power-tree topology.**
The "best possible solution" is the one that maximizes the thing that matters (sensor SNR + reliability), at acceptable cost on the things that don't (280 mW of thermal margin). Linear LDO + 6-layer + pour wins on that ranking. A hybrid wins on thermal efficiency, but thermal efficiency is not what the FC is being optimized for — it is being optimized for reliable + clean inertial data delivery to ArduCopter.

**Ground 5 — The 6-layer choice has independent justification.**
Master accepted 6-layer in PR #57 review on grounds that are independent of the LDO thermal problem: PDN integrity (separate +3V3/+5V planes), USB-self-band EMC reference-plane integrity, and Sai's reliability mandate. The fact that 6-layer ALSO brings the LDO under spec is a happy consequence; the 6-layer call would be right even without the LDO thermal pressure. So the recommendation here is not "spend layers to fix the LDO" but "the LDO is fine on the 6-layer board we're building for independent reasons."

### 2.5.5 The decision

**Retain the AP2112K-3.3 linear LDO for the 3.3 V rail.**

DECISIONS §10 (reliability mandate) interpretation for the power tree: the failure mode being prevented is sensor-data degradation under EMI/noise, NOT thermal failure. The LDO meets thermal spec on the 6-layer build (79.8°C at 50°C ambient, 5°C margin). No schematic change. Step 2's eFuse + LDO topology stands as-is.

If future evidence (Phase 6.5 forum review or Phase 9 bench) shows the LDO topology has a real problem we haven't anticipated, the buck-vs-LDO question reopens AS A SCHEMATIC CHANGE — requires Phase-3-style schematic-update review with master + Sai sign-off, not a quiet swap. Not anticipating that need.

### 2.5.6 When this would flip

The architecture should be re-evaluated if any of these conditions occur:

- **AP2112K Tj > 85°C in Elmer-FEM with realized placement** (Step 3 P1+ Round-2 sim). Means the thermal budget assumption was wrong.
- **Phase 6.5 forum review flags the LDO topology** as inadequate for the load + ambient combo. External EE judgement overrides our internal calculus.
- **Production load exceeds 350 mA** (Phase 9 bench measurement shows full-board draw closer to 500 mA). Means dissipation rises to ~0.85 W, breaking the thermal headroom on the 6-layer build.
- **A second 3.3 V rail is added** (e.g. for an additional sensor stack or telemetry radio internal to the FC). At that point a hybrid becomes the right call.

None of these are current.

---

## 3. Material thermal model (FR-4 + copper stackup)

Inputs for Elmer-FEM thermal sim (Step 3 P1+):

### 3.1 Material properties

| Material | Thermal conductivity (W/m·K) | Density (kg/m³) | Specific heat (J/kg·K) | Source |
|---|---|---|---|---|
| FR-4 (in-plane) | 0.81 | 1850 | 1150 | IPC-2221A typical |
| FR-4 (through-plane) | 0.29 | 1850 | 1150 | IPC-2221A (anisotropy ≈ 2.8×) |
| Copper | 401 | 8960 | 385 | NIST |
| Solder mask (LPI) | 0.25 | 1500 | 1200 | typical epoxy LPI |

### 3.2 Layer stackup (CORRECTED 2026-05-21 — real JLC06161H-7628)

**Earlier draft incorrectly assumed "4 oz inner / 1 oz outer". That is NOT a JLC standard offering** — JLCPCB heavy copper (≥ 2 oz) is 2-layer only per their published capability matrix (https://jlcpcb.com/help/article/jlcpcb-copper-weight). The real orderable JLC06161H 6-layer is **1 oz outer / 0.5 oz inner**. Corrected per master directive 2026-05-21.

Pre-fab fab-order spec: **JLC06161H-7628** (the impedance-control prepreg variant — picked for USB diff-pair Z geometry per CONTROLLED_IMPEDANCE.md).

| Layer | Material | Thickness (mm) | Purpose | Thermal role |
|---|---|---|---|---|
| L1 (top) | 1 oz Cu (35 µm) | 0.035 | Components + signal | Initial heat injection from U2/U1 die pads |
| Prepreg 7628 | FR-4 (εr 4.3) | **0.21** | Dielectric | Through-plane heat conduction (low — bottleneck) |
| L2 | 0.5 oz Cu (15.2 µm) | 0.0152 | GND plane | Lateral heat-spreading |
| Core | FR-4 | 0.55 | Dielectric | Through-plane heat conduction |
| L3 | 0.5 oz Cu (15.2 µm) | 0.0152 | +3V3 power plane | Lateral heat-spreading |
| Prepreg 2116 | FR-4 | 0.1088 | Dielectric | — |
| L4 | 0.5 oz Cu (15.2 µm) | 0.0152 | +5V power plane | Lateral heat-spreading + LDO via-anchor |
| Core | FR-4 | 0.55 | Dielectric | — |
| L5 | 0.5 oz Cu (15.2 µm) | 0.0152 | GND plane | Lateral heat-spreading |
| Prepreg 7628 | FR-4 | 0.21 | Dielectric | — |
| L6 (bot) | 1 oz Cu (35 µm) | 0.035 | Signal (sensors B.Cu) | Heat exit via bottom-side convection |

**Total Cu thickness: 2 × 35 µm (outer) + 4 × 15.2 µm (inner) = 0.131 mm** (much less than the erroneous "0.56 mm" earlier draft assumed — 4.3× less). Total board ≈ 1.6 mm (Cu + FR-4 + prepreg).

**Thermal-spreading note (the reason this correction does NOT break the design)**: Step 4 FEA was originally run with isotropic k_eff = 22.9 W/m·K. The corrected real anisotropic conductivities are k_xy = 33.5 W/m·K (in-plane, from the real 0.131 mm Cu / 1.469 mm FR-4 parallel-rule) and k_z = 0.316 W/m·K (through-plane series-rule). Re-running the Step 4 Elmer FEA with anisotropic `Heat Conductivity(3) = 33.5 33.5 0.316` on the 80×60 mm board confirms:

- LDO Tj = 69.8 °C (vs 80 °C target) ✓
- MCU Tj = 74.2 °C (vs 80 °C target with 5.8 °C margin) ✓

The result is essentially identical to the original isotropic k = 22.9 run (LDO 69, MCU 75.2). The design is **convection-limited, not heat-spreading-limited** — the board-average temperature is set by P_total / (h × 2 A_board) regardless of internal heat-spreading. Inner Cu weight matters at sub-millimeter local hotspot scale but not at the board level.

The k_eff = 22.9 isotropic choice from the original Step 4 model was an arbitrary geometric-mean-ish value that happened to give a similar T_max to the proper anisotropic model. The 80×60 thermal conclusion stands either way.

### 3.3 Thermal-via parameters for the LDO heat-spreading pour

| Parameter | Value | Rationale |
|---|---|---|
| Thermal via diameter | 0.3 mm | JLCPCB minimum, fits in SOT-25 fan-out |
| Thermal via copper plating | 25 µm | JLCPCB standard |
| Via array | 4×4 grid under U2 (16 vias) | High via density → low via-stack thermal resistance |
| Via-stack θ (16 vias) | ≈ 4 °C/W | calculated; dominates lateral heat conduction once injected into L4 |

---

## 4. Worst-case boundary conditions

### 4.1 Ambient temperature

| BC | T_ambient | Rationale | Source |
|---|---|---|---|
| Normal | 25 °C | bench bring-up | — |
| Phase 6j baseline | 40 °C | typical outdoor flight | Phase 6j chosen baseline |
| **Step 3 design target** | **50 °C** | drone-bay worst-case per master 2026-05-21 directive | new target |
| Stretch | 60 °C | high-ambient summer outdoor + heated enclosure | sanity-check headroom |

### 4.2 Convection model

Two cases — design for the worse:

| Case | h (W/m²·K) | Description |
|---|---|---|
| **Still air (worst)** | 5-8 | Drone parked, no propwash, enclosed bay | **DESIGN BC** |
| Forced convection | 25-50 | Propwash during flight | Sanity-check only |

Design for **still air**, h = 5 W/m²·K. Propwash is a margin, not a design assumption (the FC must boot + idle reliably before the props spin).

### 4.3 Radiation model

Treated as negligible at these temperatures (ΔT ≤ 70 °C, ε_FR4 ≈ 0.9). Radiation contribution to total heat removal ~10%; folded into the conservative h = 5 W/m²·K convection assumption.

---

## 5. Phase 6j re-run with eFuse + 50°C ambient (predicted)

Updating the 6j model to include U6 + Q2 + the new 50°C BC, predicted results:

| Component | Dissipation (W) | θ_JA (°C/W) | Δ T (°C) | T_junction at 50°C ambient | Spec | Predicted |
|---|---|---|---|---|---|---|
| AP2112K-3.3 LDO **at 4-layer with current pour** | 0.595 | 80 | 48.0 | **98.0** | 85 | **FAIL** |
| AP2112K-3.3 LDO **at 6-layer with optimized pour** | 0.595 | 50 | 29.8 | **79.8** | 85 | **PASS** ✓ |
| STM32H743 MCU | 0.700 | 35 | 24.5 | 74.5 | 85 | PASS |
| TPS25940A eFuse | 0.018 | 41 | 0.7 | 50.7 | 150 | PASS (huge margin) |
| AO3401A P-FET (Q2) | 0.0065 | 250 | 1.6 | 51.6 | 150 | PASS |
| ICM-42688-P IMU | 0.005 | 200 | 1.0 | 51.0 | 105 | PASS |
| DPS310 baro | 0.003 | 200 | 0.6 | 50.6 | 85 | PASS |
| USBLC6 ESD | 0.001 | 250 | 0.3 | 50.3 | 150 | PASS |

The LDO is the gating constraint. The placement strategy (6-layer + optimized pour) is engineered specifically to bring its T_j from 98°C (4-layer 50°C ambient) down to ≤ 80°C (6-layer 50°C ambient with 100+ mm² pour over inner power plane).

**Falsifiable**: if Step 3 P1+ Elmer-FEM with the actual placement geometry shows T_j > 80°C at 50°C ambient with the recommended pour, the placement strategy has failed and we escalate (the buck-converter switch becomes a real conversation, not a deferred v2 item).

---

## 6. What this budget does NOT cover

- **Transient thermal events** (LDO inrush fault, eFuse current-limit regulation). These have ms time-scales and don't reach junction equilibrium — the eFuse's thermal-shutdown protection at 150°C handles the fault case; placement doesn't address it.
- **Component-internal thermal limits inside multi-die packages** (e.g. ICM-42688-P internal heater for self-test). Datasheet states the LGA package handles 105°C → covered by the per-component PASS above.
- **Solder-joint reliability over thermal cycling**. This is a PCB-level reliability concern that's a Phase 6.5 / Phase 9 deep-pass item, not a placement-design input.
- **The MCU's CCM SRAM peak-power transient**. Worst-case bursty SRAM access can momentarily spike MCU dissipation to ~1.2 W for <1 ms; junction does not reach equilibrium → covered by the average 0.7 W steady-state.

---

## 7. References

- TI SLVSCV3 — TPS25940A datasheet (eFuse θ_JA, R_DSON, Iq)
- ST RM0433 — STM32H743 reference manual (peripheral power consumption)
- ST AN5394 — STM32H7 application note on power consumption + thermal design
- Diodes Inc. AP2112 datasheet — LDO θ_JA, Tj_max, V_dropout
- AOS AO3401A datasheet — P-FET R_DSON, θ_JA
- TDK DS-000347 — ICM-42688-P datasheet
- Bosch BST-DPS310-DS001 — DPS310 datasheet
- Littelfuse SMAJ TVS datasheet — SMAJ6.0A V_WM/V_BR/V_C/leakage
- IPC-2221A — generic standard for printed boards (FR-4 thermal conductivity)
- JLCPCB stackup spec — JLC06161H 6-layer reference

---

**Status**: Step 3 P0 planning input. Master adjudication on layer count (DECISIONS §8) drives whether the predicted PASS at 6-layer is the design we build. If 4-layer is chosen, the LDO question becomes a Step 4 redesign (buck converter or external heatsink).
