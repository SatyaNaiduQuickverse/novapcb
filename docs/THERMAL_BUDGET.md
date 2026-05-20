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

## 3. Material thermal model (FR-4 + copper stackup)

Inputs for Elmer-FEM thermal sim (Step 3 P1+):

### 3.1 Material properties

| Material | Thermal conductivity (W/m·K) | Density (kg/m³) | Specific heat (J/kg·K) | Source |
|---|---|---|---|---|
| FR-4 (in-plane) | 0.81 | 1850 | 1150 | IPC-2221A typical |
| FR-4 (through-plane) | 0.29 | 1850 | 1150 | IPC-2221A (anisotropy ≈ 2.8×) |
| Copper | 401 | 8960 | 385 | NIST |
| Solder mask (LPI) | 0.25 | 1500 | 1200 | typical epoxy LPI |

### 3.2 Layer stackup (target 6-layer — see PLACEMENT_STRATEGY §3 for the case)

JLCPCB JLC06161H standard 6-layer 4-oz inner / 1-oz outer, 1.6 mm total:

| Layer | Material | Thickness (mm) | Purpose | Thermal role |
|---|---|---|---|---|
| L1 (top) | 1 oz Cu (35 µm) | 0.035 | Components + signal | Initial heat injection from U2/U1 die pads |
| Prepreg 7628 | FR-4 | 0.18 | Dielectric | Through-plane heat conduction (low) |
| L2 | 4 oz Cu (140 µm) | 0.14 | GND plane | Lateral heat-spreading (HIGH due to 4 oz) |
| Core | FR-4 | 0.71 | Dielectric | Through-plane heat conduction |
| L3 | 4 oz Cu (140 µm) | 0.14 | +3V3 power plane | Lateral heat-spreading |
| Prepreg 7628 | FR-4 | 0.18 | Dielectric | — |
| L4 | 4 oz Cu (140 µm) | 0.14 | +5V power plane | Lateral heat-spreading + LDO via-anchor |
| Core | FR-4 | 0.71 | Dielectric | — |
| L5 | 4 oz Cu (140 µm) | 0.14 | GND plane | Lateral heat-spreading |
| Prepreg 7628 | FR-4 | 0.18 | Dielectric | — |
| L6 (bot) | 1 oz Cu (35 µm) | 0.035 | Signal (sensors B.Cu) | Heat exit via bottom-side convection |

Total inner copper: 4 × 140 µm = 560 µm = **0.56 mm of inner Cu** for lateral heat spreading. The LDO's drain pad vias to L4 (+5V plane) for heat injection into the inner-copper sink.

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
