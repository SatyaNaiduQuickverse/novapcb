# +3V3 worst-case current budget (rigorous derivation)

> **Purpose.** Derive U2 (AP2112K-3.3 LDO) worst-case dissipation from
> per-consumer datasheet currents. Per master directive 2026-05-23 in
> the gate12 thermal-architecture pass: do NOT assume a number —
> derive from datasheets. ENGINEERING_RIGOR §2 (don't fudge sim inputs
> to pass).
>
> **Status.** Initial draft 2026-05-23. Numbers traceable to manufacturer
> datasheets cited inline. Open for refinement (e.g., realistic-vs-
> absolute-peak combinations) at the v1.1 thermal-architecture review.

## 1. Consumers on +3V3 rail

| Refdes | Part | Datasheet | I (typ) | I (max) | Notes |
|---|---|---|---|---|---|
| U1 | STM32H743VIT6 | ST DS12110 §6.3 (Table 27/28) | ~150 mA @ 280MHz | **280 mA** @ 480MHz all peripherals | Worst case at f_HCLK=480MHz with cache+I/O active |
| U3 | ICM-42688-P (IMU1) | TDK DS-000347 §7.1 | 0.65 mA gyro+accel low-noise | **1.5 mA** gyro+accel max | LGA-14, 6-axis |
| U8 | BMI088 (IMU2) | Bosch BST-BMI088-DS001 §3.1 | accel 5 mA + gyro 4 mA = 9 mA | **10 mA** combined max | Dual-die LGA-16 |
| U9 | LSM6DSV16X (IMU3) | ST DS13727 §4.2 | 0.55 mA (XL+G HP) | **0.6 mA** max | LGA-14, 6-axis |
| U4 | DPS310 (Baro1) | Infineon DS DPS310 §6 | 1.7 mA standard mode | **7 mA** high-precision oversample | I²C, addr 0x76 |
| U7 | BMP388 (Baro2) | Bosch DS BMP388 §3.1 | 0.49 mA standard | **1.5 mA** ultra-high resolution | I²C alternate |
| J2 | microSD (write) | various ~50mA at 25MHz writes | ~20 mA avg writing | **50 mA** burst | Logging active |
| U14 | TJA1051TK/3 CAN xcvr | NXP DS §6 | 5 mA recessive | **17 mA** dominant transmit | High-speed CAN bus |
| Misc | LEDs / pull-ups / ESD quiescent | n/a | — | **10 mA** | Conservative bucket |

## 2. Sum scenarios

### 2.1 Absolute worst case (all maxes simultaneous)

Sum of all `I (max)` columns:

| Item | Current |
|---|---|
| MCU @ 480MHz | 280 mA |
| 3 × IMU max | 12.1 mA |
| 2 × Baro max | 8.5 mA |
| microSD write burst | 50 mA |
| CAN dominant transmit | 17 mA |
| Misc | 10 mA |
| **Total** | **377.6 mA** |

U2 dissipation = (5.0 − 3.3) V × 0.378 A = **0.642 W**

Note: this combination (MCU peak + microSD writing + CAN transmitting + all sensors max simultaneously) is unrealistic during steady flight — but consistent with the "won't fail" mandate as the load envelope the LDO must handle without exceeding 80°C junction.

### 2.2 Realistic peak (one transient at a time)

Conservative envelope assuming peripherals don't all peak at once:

| Item | Current |
|---|---|
| MCU @ 480MHz | 280 mA |
| Sensors avg (all on, not maxing) | 15 mA |
| microSD active (write bursts) | 50 mA |
| CAN typical (mostly recessive) | 5 mA |
| Misc | 10 mA |
| **Total** | **360 mA** |

U2 dissipation = 1.7 V × 0.360 A = **0.612 W**

### 2.3 STEP4 assumption

STEP4 used U2 = 595 mW directly (no derivation shown). This corresponds to a +3V3 load of 350 mA.

## 3. Conclusions

- The **absolute worst case** (sum of all maxes) is 378 mA → 0.642 W.
- The **realistic peak** is 360 mA → 0.612 W.
- STEP4's 595 mW assumption ≈ 350 mA load — slightly optimistic vs realistic peak.

Per master's rigor directive, the thermal architecture should size for the **absolute worst case 0.642 W** unless a specific operational constraint rules out the simultaneous-peak combination.

## 4. MCU power dissipation note

U1 STM32H743 internal dissipation = V_DD × I_DD = 3.3 V × 0.280 A = **0.924 W** worst case.

STEP4 used 700 mW for MCU dissipation — corresponds to ~212 mA average instead of 280 mA peak. The 700 mW figure under-represents the absolute worst-case dissipation; the 0.924 W is the rigorous-worst.

## 5. Thermal load summary (hot-case = 50°C ambient, heater OFF)

Per master 2026-05-23: Q5 IMU heater is thermostatic (PWM-controlled by MCU PA15 per `power_3b.py`) — in hot ambient, the heater closes the loop at lower duty (or fully OFF when board hot). Hot-case Q5 dissipation = **0 W**.

| Source | Power (rigorous-worst) |
|---|---|
| U1 MCU | 0.924 W (or 0.700 W STEP4-assumption) |
| U2 LDO | 0.642 W (or 0.612 W realistic) |
| U6 eFuse | 0.018 W |
| U13 LP5907 IMU LDO | 0.050 W |
| Q2 P-FET (rev-pol) | 0.006 W |
| Q3 OR-FET A | 0.050 W |
| Q4 OR-FET B | 0.050 W |
| U11 LM74700-Q1 ctrl A | 0.050 W |
| U12 LM74700-Q1 ctrl B | 0.050 W |
| U14 TJA1051 CAN | 0.100 W |
| Q5 IMU heater | **0 W (hot case)** |
| **Total** | **1.940 W (worst) / 1.686 W (realistic)** |

vs the prior estimate (1.97 W including heater at 0.30 W which was double-pessimism per master).

Total board dissipation 1.94 W at h=5 W/m²·K, T_amb=50°C, target Tj ≤ 80°C (with ≥5°C margin per STEP4 standard).
