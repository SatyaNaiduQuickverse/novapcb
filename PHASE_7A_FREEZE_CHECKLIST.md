# Phase 7a Freeze Checklist — novapcb v1.1

> Comprehensive close-out for fab-ready trigger. **Sai-only gate** (the freeze itself + Phase 7b fab order).
> Last updated: 2026-05-26 (master draft; will refine as remaining PRs land).

---

## TL;DR — Status at this draft

**Stack:** `sch/option-b-buck` head — see latest commit
**v1 functional scope per locked DECISIONS:** STM32H743VIT6 FC, 6-layer 105×85mm, Pixhawk 6X functional drop-in, quad/hex airframe support (6/8 motors)

### What's locked
- All 7 connector subsystems placed + routed (CAN, microSD, USB-C, GPS, CRSF, Telem, SWD-partial)
- All subsystem-internal routing complete (A power, B buck, C MCU, D IMU island + +3V3_IMU rail, E baros, F USB-C)
- 6/8 motors routed (MOT1-6 functional; MOT7/8 v2-deferred per Sai option D)
- IMU stress-relief slot (SE-corner 25.5mm, S-edge dominant flex axis)
- HSE crystal optimized (Y1 rotated, caps ≤1.5mm, IMU1_CS off-crystal per ST AN2867)
- 4 sims PASS: Sim 1 thermal (+17.6°C MCU margin), Sim 2 USB Z_diff (87.4Ω), Sim 3 SDMMC SI (97% timing margin), Sim 4 CAN Z_diff (~120Ω near-ideal)
- DFM PASS: JLC06161H 6-layer capability all clear
- 22 master process rules + 14 audit gates + DRU cleanup landed
- ~26 PRs landed on the sch/option-b-buck stack

### Pending (before freeze)
- [ ] SWD focused routing (task #56) — small surgical PR, SDMMC1_CMD ≤1mm nudge + SWDIO/SWCLK manual
- [ ] LSM6DSV16X datasheet check (task #54) — Sai input needed (datasheet OR design-intent confirmation)
- [ ] STM32_SDC_MAX_CLOCK firmware lift to 50MHz (hwdef.dat optimization — track for firmware revision)
- [ ] GUI DRC final verify on freeze head (Sai runs on his Pi; kicad-cli under-coverage on .kicad_dru)
- [ ] BOM final verify with LCSC sourcing

---

## Freeze gate checklist (Sai validates each)

### Foundation
- [ ] 6-layer stackup matches DECISIONS §8 (verified via zone-spec-match audit gate)
- [ ] Board outline 105×85mm + 4 corner M3 mounting holes
- [ ] Edge clearance ≥0.5mm all components (JLC DFM)

### Schematic / Firmware
- [ ] ERC clean
- [ ] hwdef.dat matches SKiDL pin assignments (post the multiple pin remaps this session)
- [ ] SERIAL_ORDER correct (USART6 CRSF, USART1 Telem, etc.)
- [ ] 6/8 PWM channels routed (MOT1-6); MOT7/8 declared but unrouted in hwdef
- [ ] CAN1 transceiver U14 SILENT tied GND = normal mode
- [ ] BUZZER on PA3 (re-pinned from PD7 to dodge GPS BATT2 wall)
- [ ] GPS1_TX on PA2 (re-pinned from PD5 to dodge BATT2 wall)
- [ ] CAN_SILENT on PD15 (re-pinned from PD3 to avoid MCU east saturation)
- [ ] IMU3_INT1 on PB2 (re-pinned from PE11 to free MOT4)

### Routing
- [ ] All placed subsystems fully routed OR explicitly tracked unrouted (MOT7/8, possibly SWD pre-#56)
- [ ] DRC GUI run = 0 functional errors (.kicad_dru applied — kicad-cli under-coverage noted)
- [ ] Per-net cluster walks documented for all critical nets (USB, CAN diff, SPI, SDMMC, +3V3_IMU rail)
- [ ] No foreign switching net under HSE crystal body (ST AN2867 compliance)
- [ ] GND stitching vias bridge In1+In4 GND planes (143 vias from PR #76 stackup-fix)

### Sims
- [x] Sim 1 thermal: MCU Tj 62.4°C / +17.6°C margin (PR #94)
- [x] Sim 2 USB Z_diff: 87.4Ω diff, K-J bracket validated (PR #95 inherits PR #75)
- [x] Sim 3 SDMMC SI: 172ps worst skew = 97% timing margin at SDR25 50MHz (PR #111)
- [x] Sim 4 CAN Z_diff: ~120Ω near-ideal vs CAN nominal (PR #112)
- [ ] Sim 5 PDN: deferred per audit-DECOUPLING-as-proxy (PR #95 doc); run if Sai wants explicit verification

### DFM
- [x] JLC06161H 6-layer capability PASS (PR #109): trace 0.100≥0.09mm, via OD 0.450≥0.40mm, drill 0.250≥0.15mm, annular 0.100≥0.09mm, TH 0.600mm
- [x] Edge clearance ≥0.5mm (PR #109 caught + fixed MOT-vs-slot)
- [x] 0 copper_edge_clearance violations
- [ ] Final BOM matched to LCSC catalog (basic vs extended parts noted)

### Discipline + Process
- [x] 22 master process rules in `docs/MASTER_PROCESS_RULES.md`
- [x] 14+ audit gates codified in `scripts/audit_layout_compliance.py`
- [x] Rule 9 verify-artifact applied throughout (caught stackup partial-apply, MOT1/2 unrouted, HSE gate-vs-channel, IMU slot rectangle survey, MOT-vs-slot merge regression)
- [x] All PR docs use 4-section template (Symptom/Fix/Root cause/Prevention)
- [x] Spec deviations documented per PR per Rule 4

### Open items for v2
- IMU slot full 3-side U (current is SE-corner only); requires placement-aware design from v2 start
- MOT7/8 routing (octocopter capability)
- CAN_SILENT firmware control (currently hard-tied GND for normal mode)
- BUZZER pin reassignment cleanup if PA3 wanted for something else
- HSE crystal area routing density (IMU1_CS off-crystal but adjacent W margin tight)

---

## After Sai's freeze trigger

### Phase 7b — Fab order (Sai-only)
- Final Gerber export via `kicad-cli` headless
- Drill file export
- Pick-and-place export
- BOM CSV export
- Upload to JLCPCB ordering portal
- Quantity decision (5x typical for first article)
- Solder mask + silkscreen color choice
- Surface finish (HASL vs ENIG — ENIG recommended for fine-pitch QFN)

### Phase 8 — Bring-up (Sai + hardware)
- Visual inspection of bare board
- Continuity checks (power rails, GND, critical nets)
- USB-C connection test (board enumeration before flashing)
- ArduPilot v4.6.3 flash via SWD (J9 header) or DFU mode
- Sensor I/O check (IMUs, baros via I²C2/SPI)
- ESC harness test (motor pins respond to ArduPilot output)
- Tethered hover (5 min stable hover before unrestricted flight)
