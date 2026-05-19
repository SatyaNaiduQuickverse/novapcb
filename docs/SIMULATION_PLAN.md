# Simulation plan — Phase 6 detail

Per-subsystem simulation spec. Authoritative for Phase 6 sub-phase PRs. Each sim has: tool, scenarios, pass criterion, output location.

All sims run at three corners (nominal / hot 40 °C / cold 0 °C) and Monte Carlo (±10 % on critical analog components).

## Stage 0.5 prerequisite — sim toolchain install

Before Phase 6 starts, install + smoke-test the open-source sim stack. All tools committed at version-pin in `sims/TOOLCHAIN.md`. Each gets a hello-world to prove it runs.

| Tool | Apt / pip | Purpose |
|---|---|---|
| ngspice | `apt install ngspice` | analog SPICE |
| LTspice (via Wine) | manual + `apt install wine` | visual SPICE debugging |
| PySpice | `pip install PySpice` | scriptable Monte Carlo + corner sweeps |
| OpenEMS | `apt install openems` + Octave bindings | 3D FDTD EM solver |
| scikit-rf | `pip install scikit-rf` | RF / S-parameter analysis |
| Elmer FEM | `apt install elmerfem-csc` | thermal / electrostatic FEA |
| matplotlib + numpy + scipy | pip | reporting + analytical work |
| gerbv | apt | gerber inspection |
| interactiveHtmlBom | pip plugin | BOM ↔ board cross-check |
| kicost | pip | live BOM pricing |

OpenEMS + Octave binding on ARM-Bookworm is the highest-risk install per historical flakiness; treat install failures as a blocker, not a workaround target.

Acceptance: every tool's hello-world produces expected output. ArduPilot SITL already confirmed working (Phase 0).

## Output convention

```
sims/
├── TOOLCHAIN.md            installed tool versions + hashes
└── <subsystem>/
    ├── setup.cir          (or .py, .xml — depends on tool)
    ├── corners/{nominal,hot,cold}.log
    ├── monte-carlo/sweep-results.json
    ├── plots/*.png
    └── results.md         pass/fail + key numbers + interpretation
```

Each sub-phase PR adds its `sims/<subsystem>/` tree and updates `CONFIDENCE_MAP.md` with the result.

## 6a — Power tree

| Tool | ngspice + PySpice (Monte Carlo); LTspice via Wine for visual debug |
| Scenarios | 0→500 mA load step on 3.3 V rail; ripple 100 kHz–10 MHz; brownout sweep; inrush at power-on |
| Pass | <5 % rail droop on step; impedance ≤100 mΩ across 100 kHz–10 MHz; BOR matches H743 setting; inrush <2 A peak |

## 6b — USB-CDC differential pair

| Tool | KiCad impedance calc for analytical; OpenEMS FDTD for routed pair |
| Scenarios | Single-ended + differential Zo against 90 Ω target; return loss to 480 MHz; crosstalk to adjacent traces |
| Pass | Zdiff = 90 Ω ±10 %; \|S11\| < −15 dB to 480 MHz; crosstalk margin > 20 dB |

## 6c — IMU SPI bus

| Tool | ngspice + IBIS model (InvenSense ICM-42688 IBIS if published; else estimate from datasheet rise/fall) |
| Scenarios | Rise/fall at 20 MHz SPI clock; ringing on CS line; setup/hold margin |
| Pass | Rise/fall <5 ns; setup/hold margin >2 ns; no ringing past 200 mV |

## 6d — I²C buses (baro + mag)

| Tool | ngspice |
| Scenarios | Pull-up sizing for 400 kHz; rise time vs total bus cap; reflection at long mag-port cable |
| Pass | Rise time <1 µs at 400 kHz; clean transitions; no false triggering |

## 6e — UARTs (GPS, CRSF)

| Tool | ngspice |
| Scenarios | Eye at 420 kbaud (CRSF) and 115200 (GPS); CRSF RX polarity per RP4TD; level-shifter if RX is open-drain or non-3.3 V |
| Pass | Open eye at sim; verified polarity; level translator passes if required |

## 6f — SDMMC (SDR25 target)

| Tool | ngspice + IBIS + KiCad impedance |
| Scenarios | 50 MHz clock skew across CLK/CMD/D[0-3]; SI into microSD socket pin cap; eye diagram approximation |
| Pass | Timing margin met at SDR25 spec; eye open; overshoot <30 % |

## 6g — ESC DShot outputs (8 channels)

| Tool | ngspice + IBIS for STM32 GPIO output buffer |
| Scenarios | DShot300 + DShot600 rise/fall into typical ESC input load (~10 pF + 47 kΩ); ringing on long traces; differential timing across 8 channels |
| Pass | Rise/fall <50 ns at DShot600; overshoot <30 %; channels match ±10 ns at connector |

## 6h — VBAT divider + current sense ADC

| Tool | ngspice with noise analysis |
| Scenarios | ADC accuracy at 4S/5S/6S; settling under switching noise from nearby ESC outputs; voltage/current channel cross-talk |
| Pass | <1 % error at full scale; settling <10 µs to within 0.5 LSB; cross-talk <0.1 % |

## 6i — Reverse polarity + ESD protection

| Tool | ngspice transient with surge models (HBM, IEC-61000-4-2 air) |
| Scenarios | −25 V at VBAT; 8 kV HBM ESD on USB lines; 2 kV ESD on all external connectors; recovery time |
| Pass | No internal rail above absolute max during fault; full recovery within 10 ms after fault clears |

## 6j — Thermal steady-state

| Tool | Elmer FEM with PCB stack-up modeled |
| Scenarios | 25 °C ambient + max load; 40 °C ambient + max load; air-cooling vs still-air |
| Pass | Max junction temp <85 °C for all active components; hotspot ΔT <40 °C from board edge |

## 6k — EMC / clock-harmonic estimate

| Tool | Analytical Python (Fourier decomposition); OpenEMS spot-check for worst offender |
| Scenarios | 480 MHz core clock harmonics to 5 GHz; USB 480 Mbps eye + harmonics; switching noise from any DC-DC |
| Pass | Estimated radiated emission < CISPR-22 Class A by ≥10 dB at every harmonic |

## 6l — ArduPilot SITL functional regression

| Tool | ArduPilot SITL (already installed per Phase 0) |
| Scenarios | Every flight mode (STABILIZE / ALT_HOLD / LOITER / POSHOLD / RTL / LAND from DECISIONS.md §2 CH7 6-position); RC failsafe; battery failsafe; MAVROS connection; mission upload; param sync; CRSF channel mapping per INTERFACE_CONTRACT.md §3.2 |
| Pass | All flight modes engage and disengage in sim; failsafes fire per spec; MAVROS round-trips; channel sign convention matches (no pitch double-flip — CLAUDE.md §4.1) |

## 6m — Manufacturability

| Tool | KiCad DRC + ERC + gerbv + interactiveHtmlBom + JLCPCB DFM rules |
| Scenarios | DRC at JLCPCB 4-layer (min trace 4 mil, min drill 0.2 mm, annular ring 0.13 mm); ERC; gerber visual inspection; BOM ↔ footprint cross-check; pick-and-place sanity |
| Pass | Zero DRC errors at fab capability; zero ERC errors; every footprint has BOM row; no orphan refdes |

## Re-loop policy (per ENGINEERING_RIGOR.md #5)

A sim failure at Phase 6 routes back to Phase 4 (layout) or Phase 3 (schematic) as appropriate. The re-loop is expected. Acceptable loops: re-route for SI, re-place for thermal, re-component for power. Unacceptable: relaxing the pass criterion or skipping the sim re-run.
