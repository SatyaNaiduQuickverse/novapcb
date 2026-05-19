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
| 6 | External mag + GPS I²C/UART | HIGH (~93%) | Pixhawk-standard pin header; well-documented | 3.5, 6d, 6e |
| 7 | microSD via SDMMC (SDR25 target) | MEDIUM (~80%) | SDR25 at 50 MHz has real SI requirements; faster speeds skipped per ENGINEERING_RIGOR.md | 6f |
| 8 | 8-channel ESC outputs (DShot300/600) | MEDIUM (~75%) | Worker flagged: per-pin DShot/BIDIR capability must be verified against H743 alt-func table before Phase 4 layout | 2e, 6g |
| 9 | CRSF UART for ELRS | MEDIUM (~75%) | Worker flagged: pin must be FT-rated 5V-tolerant in H743V package; 420 kbaud is fast | 3.5, 6e |
| 10 | VBAT divider + current sense ADC | MEDIUM (~80%) | Simple divider + filter cap; ADC settling matters for accuracy | 6h |
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
