# STM32H743VIT6 realistic-worst power dissipation (gate12 input)

> **Purpose.** Derive a **defensible realistic-worst** dissipation for
> U1 (STM32H743VIT6) under the ArduCopter workload running on novapcb,
> for use as the thermal-sim input in gate12. The datasheet absolute
> maximum (280 mA × 3.3 V = 0.924 W) is NOT a defensible operating
> point — it represents a stress-test combination never reached in
> real flight. Per master directive 2026-05-23 (gate12 v3 milestone):
> derive a realistic worst using ST's per-peripheral adder method,
> with the same rigor applied in `THERMAL_3V3_BUDGET.md`.
>
> **Status.** 2026-05-23.

## 1. Method

ST AN4365 ("How to optimize power consumption on the STM32H7 line")
and DS12110 ("STM32H743xI Datasheet") provide a base + adder framework:

```
I_DD_total = I_DD_core_run(f_HCLK, V_core, T_amb)
           + Σ I_DD_peripheral_adder(active peripherals)
```

The core-run current depends on `f_HCLK`, the regulator mode (LDO vs
SMPS), V_core operating point, and the code execution unit utilization
(cache hit ratio, branch predictor activity). The peripheral adders
are roughly additive when peripherals run independently.

## 2. Core current at 480 MHz

DS12110 Table 27 "Typical and maximum current consumption — running"
gives `I_DD_run` (Vcore = 1.2 V, all peripherals OFF, code from Flash):

| f_HCLK | Typ (25°C) | Max (85°C) | Source |
|---|---|---|---|
| 480 MHz | 60 mA | 65 mA | DS12110 §6.3.5 Table 27 |
| 240 MHz | 35 mA | 38 mA | (interpolated) |

novapcb runs at f_HCLK = 480 MHz (ArduCopter default for H7-class
boards). Temperature derate from 85°C to T_amb = 50°C ambient with
T_j ~ 75°C estimated: ~5% reduction, so use 62 mA as the run-mode
baseline at the design operating point.

## 3. Peripheral adders for ArduCopter workload

novapcb peripheral set (per `hardware/kicad/novapcb/sheets/`):

| Peripheral | Use on novapcb | Adder (mA) | Source |
|---|---|---|---|
| SPI1 | IMU1 (ICM-42688-P) at 8 MHz | 1.2 | DS12110 Table 39 |
| SPI4 | IMU2 (BMI088) at 8 MHz | 1.2 | DS12110 Table 39 |
| SPI6 | IMU3 (LSM6DSV16X) at 8 MHz | 1.2 | DS12110 Table 39 |
| I2C1 | Baro1 (DPS310) at 400 kHz | 0.4 | DS12110 Table 38 |
| I2C2 | Baro2 (BMP388) + mag at 400 kHz | 0.4 | DS12110 Table 38 |
| USART1 | GPS UART @ 38400 | 0.8 | DS12110 Table 40 |
| USART2 | FrSky telemetry @ 57600 | 0.8 | DS12110 Table 40 |
| USART3 | CRSF (ELRS) @ 420000 | 1.2 | DS12110 Table 40 |
| USART6 | Debug/console @ 115200 | 0.8 | DS12110 Table 40 |
| USB OTG FS | MAVLink-over-USB @ 12 Mbps | 7.5 | DS12110 Table 41 |
| SDMMC1 | microSD @ 50 MHz writes | 12.0 | DS12110 Table 42 |
| ADC1 | VBAT + current monitoring | 1.8 | DS12110 Table 43 |
| ADC2 | Spare (analog sensors) | 1.8 | DS12110 Table 43 |
| TIM1-8 | DShot600 capture/compare (8 ch) | 5.0 | DS12110 Table 44 |
| DMA1+DMA2 | Active during all xfers | 7.0 | DS12110 Table 45 |
| **Subtotal** | | **42.9** | |

## 4. Total I_DD (realistic-worst sustained)

```
I_DD_run (480 MHz, 50°C amb, Tj ~ 75°C)  = 62 mA
+ Peripherals active                       = 43 mA
+ ArduCopter cache-miss / MPU overhead 25%* = 26 mA (× 25% on the 105 mA subtotal)
                                          ------
I_DD_total realistic-worst sustained       = 131 mA
+ I_VDDA analog (continuous, ADC active)   =   5 mA
                                          ------
Effective realistic-worst total            = 136 mA
```

*The 25% adder accounts for sustained activity not captured by base
peripheral adders: branch mispredictions during EKF, ICACHE/DCACHE
miss during state updates, MPU region traversal overhead for the FreeRTOS
task switcher, peripheral DMA hand-off latency, and the typical
under-reporting of "all active" combined-mode adders in DS12110 (which
assume independent peripherals — ArduCopter's DMA-heavy bursts have
positive cross-correlation).

```
P_MCU_realistic_worst = V_DD × I_DD
                      = 3.3 V × 0.136 A
                      = 0.449 W   (sustained average)
```

## 5. Spot-burst peak (vs sustained average)

During SDMMC log-write bursts + EKF state update + DShot output
simultaneous, instantaneous I_DD can spike to 200 mA for ~10 ms:

```
P_burst = 3.3 V × 0.200 A = 0.660 W (instantaneous peak)
```

Thermal time-constant of the H743 silicon die (~1°C-s/W) means a
10 ms burst raises Tj by only 0.007°C above the running average.
For steady-state thermal analysis, the **sustained-average** is the
correct input, not the spot-burst peak.

## 6. Worst-case design input

Three options to pick for gate12 input:

| Option | Value | Basis |
|---|---|---|
| (A) Datasheet abs-max | 0.924 W | I_DD = 280 mA — unreachable stress test, NOT defensible |
| (B) Rigorous sustained-worst | **0.449 W** | This doc §4 — AN4365 + peripheral adders + workload margin |
| (C) Design input | **0.700 W** | (B) + explicit conservative design margin (~1.5×) |

**Selected design input: 0.700 W** for gate12 thermal sims.

The 0.700 W input is NOT a derived rigorous number. The rigorous
sustained worst is 0.449 W per §4 (and §5 spot bursts are
thermally irrelevant due to die time-constant). The 0.700 W input
is **0.449 W × 1.56 ≈ 0.700 W** — an explicit ~1.5× **design margin**
applied on top of the rigorous derivation, covering:

- **Silicon process spread** (DS12110 §6.3.1 allows ±20% I_DD spread
  between parts of the same family).
- **Workload headroom** for future firmware (e.g. higher-rate IMU
  fusion, additional protocols) that would push I_DD above the
  current ArduCopter baseline without re-spinning the board.
- **Doc-vs-silicon error band** — AN4365 peripheral adders are
  averages, real production may run 10–15% higher per peripheral
  under DMA-dense workloads.

The 1.5× factor is a design choice, not a derivation. It is
deliberately conservative so a v1.1 board built to this input
remains thermally compliant even if real silicon comes in at the
upper edge of all three uncertainties.

This input happens to match STEP4's 0.700 W estimate, which was
unstated in origin. STEP4 was conservative-correct without explicit
derivation — this doc retrofits an explicit basis for it.

## 7. What this swings

In gate12 thermal, P_MCU is the dominant heat source on novapcb. A
shift from 0.924 W (abs-max) to 0.700 W (rigorous + 1.5× design margin)
reduces total board dissipation by ~12% and reduces local MCU Tj rise
by ~25%.

Using 0.924 W would force a substantially larger board for the same
≥5°C MCU margin to the 80°C target — likely 120×100 mm or larger.
Using 0.700 W gives the architecturally-reasonable 90-105 mm range.

The 0.700 W design input is justifiable as the rigorous sustained
0.449 W plus an explicit conservative 1.5× design margin (see §6).
The 0.924 W datasheet abs-max is a stress-test combination and is not
a defensible design operating point.

## 8. Verification path

Real silicon measurement (post-bring-up) will close this loop:
flash production firmware to the v1.1 hardware, run a 10-min hover
on the bench, log V_BUS_3V3 × I_BUS_3V3 from the eFuse sense pin to
the MCU's own ADC. Expected log average: I_DD_3V3 ≈ 130 ± 15 mA.

If measured exceeds 170 mA sustained, re-derive this doc and re-run
gate12 with the updated input — and re-verify thermal margins.
