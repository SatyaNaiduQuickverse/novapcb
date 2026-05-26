# Phase 7a Freeze Checklist — novapcb v1.1

> Comprehensive close-out for fab-ready trigger. **Sai-only gate** (the freeze itself + Phase 7b fab order).
> Last updated: 2026-05-26 (master draft; will refine as remaining PRs land).

---

## TL;DR — Status at this draft

**Stack:** `sch/option-b-buck` head — see latest commit
**v1 functional scope per locked DECISIONS:** STM32H743VIT6 FC, 6-layer 105×85mm, Pixhawk 6X functional drop-in, quad/hex airframe support (6/8 motors)

### What's locked
- All 7 connector subsystems PLACED (CAN, microSD, USB-C, GPS, CRSF, Telem, SWD)
- Subsystems FULLY routed: CAN (#99), microSD (#100), USB-C (PR #75 earlier), GPS (#101)
- All subsystem-internal routing complete (A power, B buck, C MCU, D IMU island + +3V3_IMU rail, E baros, F USB-C)
- 6/8 motors routed (MOT1-6 functional; MOT7/8 v2-deferred per Sai option D)
- IMU stress-relief slot (SE-corner 25.5mm, S-edge dominant flex axis)
- HSE crystal optimized (Y1 rotated, caps ≤1.5mm, IMU1_CS off-crystal per ST AN2867)
- 4 sims PASS: Sim 1 thermal (+17.6°C MCU margin), Sim 2 USB Z_diff (87.4Ω), Sim 3 SDMMC SI (172ps worst skew = **97.8% margin vs SD HS setup+hold window**, equivalent to 99.1% vs 50MHz bit period), Sim 4 CAN Z_diff (~120Ω near-ideal)
- DFM PASS: JLC06161H 6-layer capability all clear (PR #109)
- 143 GND stitching vias from PR #76 (stackup-fix) bond In1+In4 GND planes
- 22 master process rules + 14 audit gates + DRU cleanup landed (PR #106)
- ~26 PRs landed on the sch/option-b-buck stack

### Pending (before freeze)
- [x] **#56 CRSF east-edge escape — RESOLVED via PR #120 (85824ea)**. Re-pinned USART6/PC6-PC7 → UART4/PA0-PA1 west edge. All gates pass: waf copter PASS (6m10s RC=0), DRC 12 baseline, CRSF unconnected=0, USB/SPI1 untouched. Same scoped FR that returned 0/6 on east pads routed cleanly (score 843) on west pads. See `docs/PR_CRSF_UART4_REPIN.md`.
- [ ] **#56 Telem + SWD defers — Sai ratification pending.** Per `docs/TELEM_V1_DEFER.md` + `docs/SWD_TEST_PADS_V1.md`: J3 (Telem) defer to v2 since USB-CDC is canonical MAVLink path; J9 (SWD) → 5 labeled test-pads + DFU first-flash. Master-recommended both. Worker awaits Sai go.
- [x] **#54 LSM6DSV16X bulk-cap question — CLOSED via master web research.** ST family pattern (LSM6DSV/DSO/DSV16X): 100nF VDD + 100nF VDDIO, NO bulk. Shared +3V3_IMU rail provides upstream bulk. See `docs/LSM6DSV16X_DECAP_CLOSURE.md`. Follow-up: **C96 value 10nF→100nF for strict ST conformance** (Path A recommended; Path B keep 10nF as HF-only acceptable). Sai picks; non-blocking for fab.
- [x] **STM32_SDC_MAX_CLOCK firmware lift to 50MHz** — landed in PR #119 (firmware build verified).
- [x] **ArduPilot build verify** — `waf configure --board novapcb-v1 && waf copter` succeeds on current head (verified in PR #119 + PR #120). Explicit freeze gate met.
- [ ] **GUI DRC final verify on freeze head** (Sai runs on his Pi; kicad-cli under-coverage on .kicad_dru known per PR #106). Latest head 85824ea (post-PR #120 CRSF re-pin).
- [ ] **BOM final verify** — deterministic refresh DONE (PR #115, 54 lines, 0 missing/dead). **9 LCSC numbers + R61 value pending Sai**:
  - 9 LCSC TBD: AO3400A (Q5), XAL4020 2.2µH (L1), 10nF 0402 (C96), 120R 0603 (R45), 0R 0603 (R46), 562k 0402 1% (R47), 180k 0402 1% (R48), JST-GH SM04B-GHS-TB (J20), JLCPCB basic/extended classification on 18 new lines
  - R61 placeholder value (heater resistor, 2512 footprint, TBD_SIM_OUT) — needs Sai to RESOLVE (pick a value) or mark DNP for fab populate-later
  - 9 of 12 ICs already sourced from in-design KiCad footprint fields (legit per Rule 3): ESD7L5 C605398, AO4262E C431178, LPS22HB C94049, BMI088 C194919, LSM6DSV16X C5267406, LM74700-Q1 C2653623, LP5907 C80670, TJA1051 C124020, PESD2CAN C75176

---

## Freeze gate checklist (Sai validates each)

### Foundation
- [ ] 6-layer stackup matches DECISIONS §8 (verified via zone-spec-match audit gate)
- [ ] Board outline 105×85mm + 4 corner M3 mounting holes
- [ ] Edge clearance ≥0.5mm all components (JLC DFM)

### Schematic / Firmware
- [ ] ERC clean
- [ ] hwdef.dat matches SKiDL pin assignments (post the multiple pin remaps this session)
- [x] SERIAL_ORDER correct: **UART4 CRSF** (post PR #120 re-pin), USART1 Telem, USART2/3 GPS1/2, UART8 spare
- [x] 6/8 PWM channels routed (MOT1-6); MOT7/8 declared but unrouted in hwdef (Sai option D v2-defer)
- [x] CAN1 transceiver U14 SILENT tied GND = normal mode (per PR #99)
- [x] BUZZER on PA3 (re-pinned from PD7 — verified hwdef)
- [x] GPS1_TX on PA2 (re-pinned from PD5 — verified hwdef)
- [x] CRSF on UART4 PA0/PA1 (re-pinned from USART6/PC6-PC7 — PR #120; ArduPilot build-verified)
- [x] CAN_SILENT removed from hwdef GPIO (PD15 freed; CAN tied to normal mode hardware-side)
- [x] IMU3_INT1 on PB2 (re-pinned from PE11)

### Routing
- [x] All placed subsystems routed OR explicitly tracked unrouted: **CRSF routed UART4 west edge (PR #120)**; **MOT7/8 v2-deferred** (Sai option D); **Telem (J3) + SWD (J9) defer to v2 pending Sai ratification** (TELEM_V1_DEFER.md / SWD_TEST_PADS_V1.md)
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
