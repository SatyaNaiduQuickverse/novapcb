# Subsystem confidence map

Per-subsystem confidence tracking. Each row updates over the lifecycle — confidence rises by **evidence** (sim pass, forum review pass, bench measurement), never by argument.

## Confidence levels

| Level | Range | Verification budget |
|---|---|---|
| HIGH | ≥90 % | sim per Phase 6; visual + analytical cross-check |
| MEDIUM | 70–89 % | sim per Phase 6 + targeted forum review optional |
| LOW | <70 % | full sim suite + sensitivity sweeps + Phase 6.5 forum review mandatory |
| PROVEN | post-lab | confidence retired; subsystem validated on real hardware |

## v1 subsystem map (initial estimate 2026-05-18, worker-side update 2026-05-19)

| # | Subsystem | Confidence | Reasoning | Updates expected at |
|---|---|---|---|---|
| 1 | MCU + clock + reset + decoupling | HIGH (~98%) | H743 minimum reference is in every app note; identical across all 5 reference designs | 3.5 (reference audit), 6a |
| 2 | USB-CDC interface | HIGH (~97%) | USB diff pair routing well-documented; CDC class is standard | 3.5, 6b |
| 3 | 5 V → 3.3 V LDO + decoupling | HIGH (~95%) | Pixhawk-family power tree published and widely copied | 3.5, 6a |
| 4 | IMU SPI bus (ICM-42688-P) | HIGH (~92%) | Single-IMU SPI is textbook; ArduPilot driver mature | 3.5, 6c |
| 5 | Barometer I²C (DPS310) | MEDIUM-HIGH (~88%) → MEDIUM-HIGH (~90%) | Phase 2b 2026-05-20: locked to DPS310 on I²C2 at 0x76, single driver line (legacy MS5611+BMP280 probes removed). SOTA cite: MatekH743 hwdef.dat:214 (same chip, bus, addr). Pixhawk6X uses BMP388/BMP581/ICP201XX, not DPS310 — divergence intentional per CLAUDE.md §3.5 (noise-floor preference). Addr 0x76 confirmed per SDO-tied-GND convention. | 6d |
| 6 | External mag + GPS I²C/UART | HIGH (~93%) → HIGH (~95%) → HIGH (~96%) | Phase 2c 2026-05-20: mag locked to IST8310 (0x0E) + RM3100 (0x20), both on I²C ALL_EXTERNAL, ROTATION_NONE + HAL_COMPASS_AUTO_ROT_DEFAULT 2. Dropped AP_COMPASS_PROBING_ENABLED. SOTA: CUAV-Nora hwdef.dat:253-254, CUAV-X7:261-266, CarbonixF405:131. Phase 2d 2026-05-20: GPS UART config verified + locked — GPS1 on USART2 (MatekH743 hwdef.dat:108-110, SERIAL3 in SERIAL_ORDER), GPS2 on USART3 (lines 112-114, SERIAL4). I²C buses exposed: I2C1 (PB6/PB7) and I2C2 (PB10/PB11) per MatekH743 hwdef.dat:60-69; HAL_I2C_INTERNAL_MASK 0 (line 199) makes both external — ALL_EXTERNAL mask consistency-checks against Phase 2c COMPASS lines ✓. Specific I²C bus → GPS connector pin still Phase 4 layout. Zero hwdef.dat change in 2d (MatekH743 inheritance correct). | 3.5 ✓, 6d, 6e |
| 7 | microSD via SDMMC (SDR25 target) | MEDIUM (~80%) | SDR25 at 50 MHz has real SI requirements; faster speeds skipped per ENGINEERING_RIGOR.md | 6f |
| 8 | 8-channel ESC outputs (DShot300/600) | MEDIUM (~75%) → MEDIUM-HIGH (~88%) | Phase 2e amended 2026-05-20: locked PWM 1-8 = MatekH743-bdshot variant inheritance — PB0/PB1 TIM3_CH3/CH4 (PB0 BIDIR), PA0/PA1 TIM2_CH1/CH2 (PA0 BIDIR), PA2/PA3 TIM5_CH3/CH4 (PA2 BIDIR), PD12/PD13 TIM4_CH1/CH2 (PD12 BIDIR). Cite MatekH743-bdshot hwdef.dat:23-30, production-validated. 4/8 channels BIDIR-DShot capable (one per timer per the H743 "one BIDIR per timer" constraint); 4/8 standard DShot300/600 direction-only. DMA_NOSHARE extended with TIM3* TIM2* TIM5* TIM4* to give motor timers dedicated DMA streams (cite bdshot DMA_NOSHARE pattern). Switch from base to bdshot variant accepted by master 2026-05-20 because bdshot's trade-offs (RC-via-UART required, GPIO-only buzzer) are FREE for novapcb v1 (DECISIONS §4 + no buzzer req). Per-pin DMA stream assignment is implicit via ArduPilot DMAMUX allocator; not tabulated against H743 RM (deferred to Phase 6g sim). | 2e ✓ (amended), 6g |
| 9 | CRSF UART for ELRS | MEDIUM (~75%) → MEDIUM-HIGH (~85%) | Phase 2f 2026-05-20: locked to SERIAL7 = USART6 on PC7 (RX) / PC6 (TX) — inherited from MatekH743-bdshot hwdef.dat:19-20 via the Phase 2e amendment. defaults.parm created with `SERIAL7_PROTOCOL 23` (RCIN, inherited from bdshot/defaults.parm) + `SERIAL7_BAUD 420` (novapcb-CRSF-specific per DECISIONS §4; 1-number deviation from bdshot's BAUD 115). Inversion / half-duplex not required in hwdef — ArduPilot CRSF driver handles polarity at protocol layer (CRSF is non-inverted at TTL; grep across both MatekH743 + MatekH743-bdshot shows zero RXINV/TXINV/HALF_DUPLEX flags). FT-pin verification deferred — PC7 is bdshot-inherited (production-validated on shipping MatekH743-bdshot hardware). Phase 6e sim can measure edge-rate / 5V-tolerance on real silicon. | 3.5 ✓, 6e |
| 10 | VBAT divider + current sense ADC | MEDIUM (~80%) → MEDIUM-HIGH (~88%) | Phase 2g 2026-05-20: ADC pin assignments locked — PC0/PC1 for BATT1 (ADC1 ch10/11 = `HAL_BATT_VOLT_PIN 10`/`HAL_BATT_CURR_PIN 11`), PA4/PA7 for BATT2 scaffolding (ADC1 ch18/7, BATT_MONITOR2=0 default, removal → Phase 2-exit). Pin lines inherited from MatekH743 hwdef.dat:71-77; bdshot inherits without divergence. **BATT1 SCALE values DIVERGED from Matek to researched Mauch HS-200-LV typicals** per DECISIONS §5 (Mauch 200A pinned) + CLAUDE.md §3.6 (4-6S → LV variant): `HAL_BATT_VOLT_SCALE 9.0` (9:1 LV divider, Mauch product page) + `HAL_BATT_CURR_SCALE 60.6` (200A/3.3V analog full-scale, ACS-250U hall sensor). HAL_BATT2_VOLT_SCALE stays Matek-inherited 11.0 (harmless). HAL_BATT_MONITOR_DEFAULT 4 (analog VBAT+CURR) retained, correct for Mauch. Per-unit final-test calibration card refines for precision (±1-3%); failsafes function pre-calibration. Option chain: A (Matek inherit) → B (drop SCALEs, BUILD FAILS — ArduPilot #error-enforces SCALE-with-PIN) → C5 (researched Mauch HS-200-LV typicals, this option). ADC1 DMA does not conflict with the Phase 2e DMA_NOSHARE SPI1*/TIM* protections. Sources: mauch-electronic.com/076 + craftandtheoryllc.com/075 + ardupilot.org Mauch wiki page. | 2g ✓, 6h |
| 11 | Reverse polarity + ESD on VBAT | LOW (~65%) | Easy to under-design; field failures catastrophic | 3.5, 6i, 6.5 forum |
| 12 | EMC / RF coupling | LOW (~60%) | Not designed around explicitly; depends on layout | 6k, 6.5 forum |
| 13 | Thermal under full load | MEDIUM (~80%) | H743 + sensors ≈ 1–2 W total on small board | 6j |
| 14 | Brownout / POR behavior | MEDIUM (~75%) | H743 BOR configurable; mis-set = unreliable boot | 6a |

## v1 subsystem map — worker-flagged additions pending follow-up PR

These items aren't in any phase yet but worker flagged them on 2026-05-19 as LOW-confidence gaps. Will be added in a follow-up doc PR after this consolidated PR merges:

- 30.5 × 30.5 mm mechanical envelope reality — has anyone opened KiCad to verify all selected peripherals + connectors actually fit?
- 4-layer USB diff-pair impedance — no analysis yet
- Power tree decoupling + thermal cross-section — no SPICE pass yet

## How rows update

Each PR that touches a subsystem updates that row's "Updates" column or adds an evidence note:

```
| 1 | MCU + clock + reset + decoupling | HIGH (~98%) → HIGH (~99%) | 3.5 reference audit passed 2026-XX-XX, identical to MatekH743 §A. 6a SPICE passed. | 3.5 ✓ 6a ✓ |
```

When a subsystem completes a bench test in Phase 9, confidence rating becomes `PROVEN (YYYY-MM-DD)` and is retired from active tracking.

## What's NOT in this table (intentionally)

- IMU vibration isolation / mechanical mounting — user-domain (per direction 2026-05-18). IMU SPI bus is our concern; mechanical context is not.
- Antenna design — no on-board RF in v1 (DECISIONS.md §4).
- Battery cell management — external Mauch (DECISIONS.md §5).
