# Phase 3.5 — reference design audit

Cross-check of the novapcb v1 schematic (8 sheets, Phase 3a-3h) against available reference designs. Audit gate before Phase 4 layout.

Generated 2026-05-20 per master Phase 3.5 dispatch.

---

## Honest framing on reference availability

This audit's depth varies per subsystem based on what reference designs are obtainable.

**Strong cross-check available:**
- ArduPilot `hwdef.dat` files for the H743 family — MatekH743, MatekH743-bdshot, Pixhawk6X, CUAV-Nora, CUAV-X7, CarbonixF405. All in-tree at `~/ardupilot/libraries/AP_HAL_ChibiOS/hwdef/`. Provide pin maps + driver bindings + some inline comments — NOT full schematics.
- Component datasheets — STM32H743 (ST DS12110), AP2112 (Diodes DS39724), ICM-42688-P (TDK ds-000347 v1.6), DPS310 (Infineon v01.02), BMP280 (Bosch v1.26), USBLC6-2P6 (ST), Mauch HS-200-LV (Infineon product page).
- Pixhawk Connector Standard DS-009 (canonical, GitHub `pixhawk/Pixhawk-Standards`) — JST-GH connector pinouts.
- SD Association 4-bit SDMMC spec.
- ARM Cortex Debug Connector standard (verified via KiCad symbol pin labels matching).

**Weak / no cross-check:**
- **MatekH743 full schematic** — NOT obtainable. ArduPilot tree has only the hwdef (firmware pin map). Worker tried web research at Phase 3b for the LDO part; Matek does not publish full schematics for their FCs. This is a real gap that affects the LDO part choice + ADC filter + 5V-input protection cross-checks.
- **Pixhawk Autopilot v6X Reference (DS-012)** — open hardware (CC BY-SA 3.0) but the canonical board uses STM32H753 (cryptographic peripherals) + a two-board FMU+IMU mechanical pattern, not a single-board 36×36 mini-FC. Reference topology concepts cross over (H7 power tree, ESD topologies) but pin-map cross-check is limited.
- **ST AN5354 (H743 hardware development guide)** — published PDF; webfetch couldn't parse binary content within the audit window. Datasheet typical-circuit refs used as proxy.

**Per the DESIGN_PHASES Phase 3.5 rule:** when ≥3 references agree on a value/topology → novapcb MUST match (any mismatch = Rule-13 NEEDS-FIX); when references diverge → pick one + document; when no reference is obtainable → confidence stays LOW + Phase 6.5 forum review is mandatory.

**Per master's 3.5 directive:** "Do not fake a cross-check. Where a reference cross-check genuinely can't be made, SAY SO and route that subsystem to Phase 6.5 forum review (external EE eyes ARE a form of reference review)."

---

## Audit summary

| Subsystem | Confidence | Verdict | References used |
|---|---|---|---|
| 1. MCU + clock + reset + decoupling | HIGH ~98% | **OK-AS-IS** | STM32H743 datasheet + KiCad symbol + MatekH743/bdshot/Pixhawk6X hwdef cross-grep |
| 2. USB-CDC | HIGH ~98% | **OK-AS-IS** | USB-C UFP spec + USBLC6 datasheet + ArduPilot USB-CDC machinery + KiCad symbol pin map |
| 3. 5V → 3.3V LDO + decoupling | HIGH ~95% | OK-AS-IS (no ref disagrees) | AP2112 datasheet + STM32H743 power tree typical |
| 4. IMU SPI (ICM-42688-P) | HIGH ~93% | **OK-AS-IS** | TDK ds-000347 §10/§11.1 + hwdef pin map |
| 5. Baro I²C (DPS310) | MEDIUM-HIGH ~92% (+1) | **OK-AS-IS** ✓ pin-identity load-bearing re-verified | Infineon DPS310 datasheet + Bosch BMP280 datasheet + KiCad BMP280 pin map (×3 cross-confirm) |
| 6. External mag + GPS | HIGH ~97% | **OK-AS-IS** | hwdef + Pixhawk DS-009 + ArduPilot 3-reference convergence (CUAV-Nora/X7 + CarbonixF405) |
| 7. microSD via SDMMC | MEDIUM-HIGH ~88% | OK-AS-IS | SD Association 4-bit spec + MatekH743 hwdef inheritance + Hirose DM3AT datasheet |
| 8. 8-ch ESC outputs | MEDIUM-HIGH ~89% | **OK-AS-IS** | MatekH743-bdshot/hwdef.dat:23-30 (production-validated, shipping reference) |
| 9. CRSF UART | MEDIUM-HIGH ~87% | OK-AS-IS | ELRS RP4TD standard + DECISIONS §7 + ArduPilot CRSF driver |
| 10. VBAT + current sense | MEDIUM-HIGH ~89% | OK-AS-IS (capture); **PRIORITY-for-Phase-9-bench** on calibration values | Mauch HS-200-LV product page + ArduPilot wiki Mauch page + Pixhawk DS-009 + ArduPilot AP_BattMonitor source |
| 11. Reverse polarity + ESD on VBAT/5V | LOW ~65% | **DEFER-TO-6.5** | NO schematic-level ref obtainable (MatekH743 not sourceable; FMUv6X H753-based ref doesn't directly apply) |
| 12. EMC / RF coupling | LOW ~62% | **DEFER-TO-6.5** + Phase 6k EMC sim | NO schematic-level ref for external-connector ESD topology |
| 13. Thermal under full load | MEDIUM ~80% | DEFER-TO-6j (Phase 6 sim) | STM32H743 + AP2112K thermal datasheets; layout-dependent — Phase 6j |
| 14. Brownout / POR behavior | MEDIUM ~78% (+3) | **OK-AS-IS** | STM32H743 BOR datasheet + ArduPilot mcuconf.h defaults + SWD reset access |

**No NEEDS-FIX items.** No Rule-13 stop required before this PR ships.

---

## Subsystem-by-subsystem audit

### 1. MCU + clock + reset + decoupling — OK-AS-IS

**References checked:**
- ST STM32H743 datasheet (DS12110) — power-pin layout (5×VDD/5×VSS/VDDA/VSSA/VREF+/2×VCAP/VBAT), decoupling guidance §6, HSE crystal section §6.3.1
- KiCad symbol `MCU_ST_STM32H7:STM32H743VITx` — datasheet-encoded pin map (verified via SKiDL `Part().pins` query, 100 pins enumerated)
- MatekH743 + MatekH743-bdshot + Pixhawk6X hwdef.dat — pin map cross-reference (LDO mode confirmed via grep: no SMPS_PWR / SMPS_EXT define in any variant → falls through to `PWR_CR3_LDOEN` in `hwdef/common/stm32h7_mcuconf.h:93`)
- ST AN5354 H7 hardware development guide — Datasheet PDF inaccessible in audit; STM32H743 datasheet section §6 typical-circuit used as proxy.

**novapcb capture** (`sheets/mcu_3a.py`):
- 5× 100nF X7R 0402 decoupling (one per VDD pin) + 4.7µF X5R bulk
- 2× 2.2µF X7R VCAP (LDO mode mandatory)
- 100nF + 1µF VDDA filter; 100nF + 1µF VREF filter
- Ferrite bead VDD → VDDA (600R@100MHz)
- VBAT: 0R tie to +3V3 + 100nF (no battery v1)
- HSE 8 MHz (`hwdef.dat:16` OSCILLATOR_HZ) + 2× 18pF C0G load caps
- NRST: 100nF X7R decoupling, internal pull-up
- BOOT0: 10kΩ pull-down (boot from flash)

**Verdict: OK-AS-IS.** Datasheet-textbook decoupling network; LDO power scheme correctly inherited from MatekH743 via grep. 18pF load caps standard for a 12pF crystal (C_load ≈ 2×(CL - C_stray) ≈ 18-22pF). NRST decoupling + internal pull-up + SWD reset access is the standard pattern.

---

### 2. USB-CDC — OK-AS-IS

**References checked:**
- USB-C UFP spec — 5.1 kΩ Rd pulldown on CC1+CC2 MANDATORY for sink-device enumeration
- ST USBLC6-2P6 datasheet — pin map (verified via KiCad symbol query: 1=I/O1 host / 2=GND / 3=I/O2 host / 4=I/O2 MCU / 5=VBUS / 6=I/O1 MCU)
- KiCad `Connector:USB_C_Receptacle_USB2.0_16P` — pin map (verified via SKiDL: 4×GND, 4×VBUS, CC1, CC2, 2×D-, 2×D+, 2×SBU, shield)
- ArduPilot USB-CDC machinery — VID/PID `0x1209:0x5740` (pid.codes-derived ArduPilot family) generated via `chibios_hwdef.py`

**novapcb capture** (`sheets/crsf_usb_3g.py`):
- HRO TYPE-C-31-M-12 16-pin mid-mount receptacle (Phase 2.5 P0.4 inventory)
- CC1 + CC2 each → 5.1 kΩ Rd to GND (R31, R32)
- D+/D- paralleled (A6+B6, A7+B7) for cable-orientation flip
- USBLC6-2P6 ESD-protection array on D+/D- (post-ESD → MCU PA12/PA11)
- VBUS → +5V; GND + shield → GND; SBU NC for USB 2.0

**Verdict: OK-AS-IS.** All hard requirements met (CC pulldowns mandatory; USBLC6 standard practice). USB diff-pair impedance is a Phase 4 layout constraint (already noted). Phase 6b SI sim still needed but not blocking.

---

### 3. 5V → 3.3V LDO + decoupling — OK-AS-IS

**References checked:**
- AP2112 datasheet (Diodes DS39724 Rev 2) — 600 mA fixed-3.3V SOT-25; recommended 1 µF X7R in + 1 µF X7R out
- STM32H743 power tree typical app circuit (datasheet §6)
- 3.3V load estimate: per-component datasheet sums (STM32H743 max 250-300mA + ICM-42688-P 2mA + DPS310 1mA + external GPS module 30-80mA = ~300-400mA worst-case)

**Reference availability gap:**
- **MatekH743 full schematic NOT sourceable.** Worker tried web research at Phase 3b; Matek doesn't publish full FC schematics. Cannot cross-check Matek's actual LDO part choice.

**novapcb capture** (`sheets/power_3b.py`):
- AP2112K-3.3 (600mA SOT-25); ~50% margin over 300-400mA load
- 1 µF X7R + 4.7 µF X5R bulk at LDO input (5V rail)
- 1 µF X7R + 4.7 µF X5R bulk at LDO output (3V3 rail)

**Verdict: OK-AS-IS** (no reference disagrees). AP2112K-3.3 is industry-standard mini-FC LDO (DigiKey/LCSC/JLCPCB stocked; common in Matek-class designs per general practice). Datasheet-grounded part + caps; sizing margin healthy. Phase 6a sim can validate adequacy under load step. Phase 6.5 forum review provides external EE confirmation of part choice if there's any concern.

---

### 4. IMU SPI bus (ICM-42688-P) — OK-AS-IS (with Phase 4 carry-forward)

**References checked:**
- TDK InvenSense ICM-42688-P datasheet (ds-000347 v1.6) — §10 Pin Description (LGA-14 pinout) + §11.1 Typical Operating Circuit (decoupling)
- ArduPilot hwdef.dat:36-39 + 203 — SPI1 pin map (PA5/PA6/PD7/PC15) + SPIDEV declaration
- KiCad symbol survey — no `Sensor_Motion:ICM-42688-P` exists in stdlib; ICM-20602 (LGA-16) wrong package

**novapcb capture** (`sheets/imu_3c.py`):
- `Connector_Generic:Conn_01x14` generic with pins renamed per TDK datasheet §10 (pin 1=INT1, 4=GND, 8=VDDIO, 9=SDO, 10=~CS, 11=SCLK, 12=SDI, 14=VDD; pins 2/3/5/6/7/13 RESV NC)
- Decoupling per datasheet §11.1: 100nF VDD + 100nF VDDIO + 2.2µF X5R bulk on VDD
- VDDIO tied to VDD (SPI-only operating circuit)
- INT1 → IMU_INT1_TP testpoint (DRDY deferred per OPEN_QUESTIONS phase2a-1)

**Verdict: OK-AS-IS.** Datasheet-grounded; pin numbers (1-14) match LGA-14 datasheet exactly (load-bearing fact for netlist).

**Phase 4 carry-forward:** Conn_01x14 has all-passive pin types (ERC-blind to power-in / bidirectional rules). Phase 4 swaps to a TDK-datasheet-exact symbol with proper electrical pin types (same pattern as Phase 3d's BMP280-as-DPS310 improvement over 3c's connector rename). Plus production-grade TDK land pattern footprint.

---

### 5. Baro I²C (DPS310) — OK-AS-IS, ✓ pin-identity load-bearing re-verified

**References checked (this is the master 3.5.4 directive verification):**
- Infineon DPS310 datasheet v01.02 — LGA-8 pinout (web-confirmed 2026-05-20 Phase 3.5)
- Bosch BMP280 datasheet v1.26 — LGA-8 pinout (web-confirmed 2026-05-20 Phase 3.5)
- KiCad `Sensor_Pressure:BMP280` symbol pin map (verified via SKiDL `Part().pins` query)

**Pin-by-pin re-verification:**

| Pin | DPS310 (Infineon) | BMP280 (Bosch) | KiCad BMP280 symbol | novapcb wiring |
|---:|---|---|---|---|
| 1 | GND | GND | GND (func=power) | GND |
| 2 | CSB | CSB | CSB (func=input) | +3V3 (I²C mode HIGH) |
| 3 | SDI | SDI | SDI (func=bidirectional) | I2C2_SDA |
| 4 | SCK | SCK | SCK (func=input) | I2C2_SCL |
| 5 | SDO | SDO | SDO (func=bidirectional) | GND (address 0x76) |
| 6 | VDDIO | VDDIO | VDDIO (func=power_in) | +3V3 |
| 7 | GND | GND | GND (func=passive) | GND |
| 8 | VDD | VDD | VDD (func=power_in) | +3V3 |

**ALL 8 PINS MATCH** across all 3 sources. The Phase 3d BMP280-as-DPS310 stand-in is pin-identity-verified ✓. Master's 3.5.4 directive load-bearing re-confirmation: **PASSED**.

**novapcb capture** (`sheets/baro_3d.py`):
- BMP280 symbol w/ `value="DPS310"` override (correct ERC pin types: power_in/passive/bidirectional/input)
- CSB tied +3V3 (I²C mode per Infineon §6.2)
- SDO tied GND (address 0x76 per `hwdef.dat:242`)
- 100nF VDD + 100nF VDDIO per datasheet typical circuit
- I²C2 pull-ups (4.7 kΩ × 2) co-located here per 3d ownership rule

**Verdict: OK-AS-IS** with pin-identity cross-confirmed ×3 sources. Confidence bumps MEDIUM-HIGH ~91% → ~92%.

**Phase 4 carry-forward:** Proper DPS310-named symbol (BMP280 silkscreen will show in auto-render) + Infineon-DPS310-exact footprint. Same pattern as ICM-42688-P.

---

### 6. External mag + GPS I²C/UART — OK-AS-IS

**References checked:**
- ArduPilot hwdef.dat — `hwdef.dat:60-65` (I²C1/I²C2 pins), `:117-122` (USART2/USART3 GPS), `:230-231` (COMPASS IST8310/RM3100 ALL_EXTERNAL)
- Three-reference SOTA convergence (verified Phase 2c): CUAV-Nora hwdef.dat:253-254 + CUAV-X7:261-266 + CarbonixF405:131 ALL match the explicit-COMPASS-no-broad-probing pattern
- Pixhawk Connector Standard DS-009 — 10-pin JST-GH GPS connector pinout (canonical source: `pixhawk/Pixhawk-Standards` GitHub)
- IST8310 datasheet (Isentek) + RM3100 datasheet (PNI) — 0x0E + 0x20 I²C addresses respectively

**novapcb capture** (`sheets/gps_mag_3e.py`):
- JST-GH 10P per DS-009 pinout: VCC5V / UART_TX / UART_RX / I2C_SCL / I2C_SDA / SAFETY_SW / SAFETY_LED / +3V3 / BUZZER / GND
- GPS UART = USART2 PD5/PD6 per hwdef.dat:117-118
- I²C SCL/SDA = I²C1 PB6/PB7 (separated from baro's I²C2 — cable-fault isolation)
- I²C1 4.7 kΩ pull-ups (×2) on this sheet
- BUZZER → MCU PA15 per hwdef.dat:179
- SAFETY_SW/LED → testpoints (hwdef-unassigned, no invented MCU pin)

**Verdict: OK-AS-IS.** 3-reference convergence + canonical connector standard satisfy the Phase 3.5 ≥3-refs-agree rule. ESD on the connector lines is a separate row (12 — DEFERRED).

---

### 7. microSD via SDMMC — OK-AS-IS

**References checked:**
- SD Association SDMMC 4-bit spec — pull-up convention on CMD + D0-D3 (range 10-100 kΩ, 47 kΩ middle)
- ArduPilot hwdef.dat:183-188 — SDMMC1 pin map (PC8-12 + PD2); inherited cleanly from MatekH743 hwdef.dat:163-168
- KiCad `Connector:SD_Card_Device` 9-pin SD bus symbol
- Hirose DM3AT-SF-PEJM5 datasheet — push-push socket geometry (Phase 2.5 P0.4 inventory)

**Reference availability gap:**
- MatekH743 actual schematic pull-up values not sourceable; 47 kΩ is the industry-standard middle.

**novapcb capture** (`sheets/power_sd_swd_3h.py`):
- SD_Card_Device symbol + DM3AT footprint
- SDMMC1 4-bit pinout per hwdef
- 5× 47 kΩ pull-ups on CMD + D0-D3 to +3V3
- CLK NOT pulled (MCU drives idle)
- 100nF VDD decoupling near socket
- Card-detect mechanical switch pin Phase 4-deferred (Phase 2h fork-2 documented)

**Verdict: OK-AS-IS.** SD spec convention + hwdef pin inheritance. Phase 6f sim validates SDMMC SI at clock rate (currently 12.5 MHz default; SDR25 50 MHz pending sim).

---

### 8. 8-channel ESC outputs (DShot300/600) — OK-AS-IS

**References checked:**
- MatekH743-bdshot/hwdef.dat:23-30 — 8 PWM pin block (PB0-3, PA0-3, PD12-13 with 4 BIDIR markers). **Production-validated** — MatekH743-bdshot ships in volume on real hardware.
- ArduPilot AP_HAL_ChibiOS DShot driver — DMAMUX allocation, BIDIR machinery (TIM3/TIM2 DMA receive path)
- DECISIONS §3 — 8 channels DShot300/600 preferred

**novapcb capture** (`sheets/esc_3f.py`):
- 8 PWM pins exactly matching MatekH743-bdshot lines 23-30
- 4 BIDIR-DShot channels (PB0/PA0/PA2/PD12 — one per timer)
- Solder pads (16 pads = 8 motor + 8 GND) — MatekH743 reference convention
- NO series resistors (MatekH743-bdshot ships bare; BIDIR-correct: R affects both directions)
- NO power passthrough (multirotor topology; ESCs powered direct-from-battery)

**Verdict: OK-AS-IS.** MatekH743-bdshot is the closest available H743 production-validated reference. Phase 6g sim validates ringing on all 8 channels (especially BIDIR-line SI).

---

### 9. CRSF UART for ELRS — OK-AS-IS

**References checked:**
- ArduPilot hwdef.dat:133-134 — USART6 RX/TX (PC7/PC6, Phase 2e bdshot amendment)
- `defaults.parm` — SERIAL7_PROTOCOL 23 + SERIAL7_BAUD 420 (Phase 2f lock)
- ELRS RP4TD wiring convention (community-standard): +5V / UART_TX / UART_RX / GND
- DECISIONS §7 JST-GH connector standard

**novapcb capture** (`sheets/crsf_usb_3g.py`):
- JST-GH 4P (SM04B-GHS-TB horizontal) per DECISIONS §7
- Pin map: 1=+5V / 2=USART6_TX / 3=USART6_RX / 4=GND
- Full-duplex per ELRS standard (half-duplex inverted-S.Port is a different protocol)
- No inversion / no half-duplex flags in hwdef (verified Phase 2f via grep)

**Verdict: OK-AS-IS.** ELRS standard well-documented + hwdef-driven pin map. Phase 6e sim can measure edge-rate at 420 kbaud if needed.

---

### 10. VBAT + current sense ADC (single Mauch) — OK-AS-IS + PRIORITY-for-Phase-9-bench

**References checked:**
- Mauch HS-200-LV product page (mauch-electronic.com 075 + craftandtheoryllc.com 075) — LV variant (≤6S, 28V max) + 9:1 divider + ACS-250U hall sensor
- ArduPilot wiki Mauch page (ardupilot.org/copter/docs/common-mauch-power-modules.html) — 1% resistor divider, per-unit calibration card workflow
- ArduPilot hwdef.dat:68-69 + 74-92 — ADC pin map + Phase 2g Mauch HS-200-LV SCALEs (9.0/60.6)
- Pixhawk DS-009 6-pin power-module connector standard
- Mauch product 065 "Power-Cube output cable JST-GH/6p" — adapter for DF-13→JST-GH

**Reference availability gap:**
- Mauch HS-200-LV internal schematic not sourceable; only the divider ratio (9:1) + sensor part (ACS-250U) + analog output range (0V→0A, 3.3V→200A) are published.

**novapcb capture** (`sheets/power_sd_swd_3h.py`):
- JST-GH 6P per DS-009: 2×VCC5V / VBAT_analog / CURRENT_analog / 2×GND
- 1 kΩ + 100 nF X7R LPF on each ADC input (~1.6 kHz cutoff)
- User-side DF-13→JST-GH adapter requirement documented (Mauch 065)
- hwdef.dat SCALE values: VOLT 9.0 (LV 9:1 divider) + CURR 60.6 (200A/3.3V)

**Verdict: OK-AS-IS** (schematic correct per available references). **PRIORITY-for-Phase-9-bench**: Mauch HS-200-LV calibration values (9.0/60.6) are still the least-verified Phase 2 numbers (master 02:00 retro flagged); web-research-sourced + per-unit calibration card workflow refines. First items a multimeter checks on bench.

---

### 11. Reverse polarity + ESD on VBAT / 5V input — DEFER-TO-6.5

**References sought:**
- MatekH743 schematic for 5V-input protection topology — **NOT obtainable** (Matek doesn't publish full schematics)
- Pixhawk Autopilot v6X (DS-012) — different topology (H753 + 2-board with isolated IMU); 5V handling is different from a single-board 36×36 mini-FC
- Other ArduPilot H743 hwdefs (CUAV, CarbonixF405) — firmware-side only

**novapcb capture:** No 5V-input reverse-polarity or ESD protection captured in schematic. The +5V net is declared (`sheets/power_3b.py`) and sourced via the Mauch connector (3h); a P-FET reverse-polarity gate or series TVS would land here but is NOT in v1 schematic per master 3e.5-pattern ("don't silently omit, don't silently add a non-inherited topology").

**Verdict: DEFER-TO-6.5.** No schematic-level reference obtainable. CONFIDENCE_MAP row 11 stays LOW ~65% pending external EE review (Phase 6.5 forum review) + Phase 6i transient-overvoltage sim. VBAT-side protection lives upstream on the Mauch power module per DECISIONS §5; the FC sees post-divider analog levels only — but the +5V BEC input remains the unprotected surface.

---

### 12. EMC / RF coupling (external-connector ESD) — DEFER-TO-6.5

**References sought:**
- MatekH743 ESD protection topology — not sourceable (same gap as row 11)
- Pixhawk6X / FMUv6X ESD topology — different mechanical assembly (separate FMU + isolated IMU) not directly applicable

**novapcb capture:**
- ✓ USB-C: USBLC6-2P6 ESD-array on D+/D- (`sheets/crsf_usb_3g.py`) — standard practice captured
- ✗ GPS+mag JST-GH 10P (`sheets/gps_mag_3e.py`) — ESD NOT captured (deferred per master 3e.5)
- ✗ CRSF JST-GH 4P (`sheets/crsf_usb_3g.py`) — ESD NOT captured (deferred)
- ✗ Mauch JST-GH 6P (`sheets/power_sd_swd_3h.py`) — ESD NOT captured (deferred)

**Verdict: DEFER-TO-6.5** + Phase 6k EMC sim. Three connectors remain ESD-uncovered. Standard practice would add 5-channel TVS arrays per connector, but worker cannot add without reference confirmation per the "don't silently add" directive. CONFIDENCE_MAP row 12 LOW ~62%; resolves at Phase 6.5 + Phase 6k.

---

### 13. Thermal under full load — DEFER-TO-6j (Phase 6 sim)

**References checked:**
- STM32H743 thermal datasheet (DS12110 §6.5 + §10) — θ_JA for LQFP-100 depends on PCB copper area
- AP2112 thermal — SOT-25 package, ~250°C/W θ_JA without heatsink (small package, thermal-limited at high current)

**novapcb capture:** Passive cooling; no explicit heat-spreader copper pours or thermal vias captured in this phase (layout-dependent, Phase 4 work).

**Verdict: DEFER-TO-6j.** Thermal is fundamentally a layout + sim question, not a Phase 3 schematic-capture question. Phase 6j thermal sim validates after Phase 4 layout.

---

### 14. Brownout / POR behavior — OK-AS-IS (small bump)

**References checked:**
- STM32H743 BOR (Brown-Out Reset) datasheet section — configurable BOR level via PWR_CR1
- ArduPilot `hwdef/common/stm32h7_mcuconf.h` defaults (Phase 2-exit Part A reproduce confirmed the BOR config is inherited from mcuconf defaults)
- NRST reset behavior — STM32 internal pull-up; 100nF decoupling cap standard

**novapcb capture** (`sheets/mcu_3a.py` + `sheets/power_sd_swd_3h.py`):
- NRST: 100nF X7R decoupling to GND + internal pull-up (no external pull-up needed)
- SWD header pin 10 (~RESET) → MCU NRST shared via `n("NRST")` for debugger reset access
- BOOT0: 10kΩ pull-down (boot from main flash by default)
- VBAT: 0R tie to +3V3 (backup domain follows main +3V3 rail)

**Verdict: OK-AS-IS.** Standard STM32 reset pattern. BOR configuration via ArduPilot mcuconf defaults (verified Phase 2-exit). Confidence bumps MEDIUM ~75% → ~78% — schematic-capture-level concerns resolved; Phase 6a + Phase 9 still validate POR + BOR behavior on real silicon.

---

## Phase 4 carry-forward items (consolidated)

NOT NEEDS-FIX — these are routine Phase 4 production work, captured here so they're tracked centrally:

1. **ICM-42688-P symbol + footprint** — Replace `Conn_01x14` connector-rename (3c) with a TDK-datasheet-exact `ICM-42688-P` symbol (proper electrical pin types) + production-grade land pattern.
2. **DPS310 symbol** — Replace `BMP280`-as-`DPS310` (3d) with a proper `DPS310`-named symbol (pin-identity already verified, but BMP280 silkscreen would auto-render on the drawn schematic — Phase 6.5 cosmetic concern).
3. **Solder pad geometry for ESC outputs** — 8× motor pads in Phase 3f use `PinHeader_1x02_P2.54mm_Vertical` placeholder; Phase 4 swaps to production solder-pad land pattern (typical 2.5×1.5 mm at 2.5 mm pitch).
4. **USB diff-pair impedance** — 90 Ω differential routing + length matching + USBLC6 placement on host side of cable ESD path.
5. **ADC filter component placement** — 1 kΩ + 100 nF on Mauch ADC lines should be physically close to MCU PC0/PC1 (post-trace from connector).
6. **SDMMC trace routing** — matched lengths + impedance for 4-bit bus + card-detect mechanical switch pin (Phase 2h fork-2 testpoint).
7. **Mounting hole exact positions** — Phase 2.5 P1.1 already specified (2.75/33.25 inset corners); Phase 4 confirms in real layout.

---

## DEFER-TO-Phase-6.5 / Phase-6-sim items (consolidated)

Items routed to external EE review (Phase 6.5 forum) + simulation (Phase 6 series):

| Item | Sub-row | Routes to | Reason |
|---|---|---|---|
| 5V-input reverse polarity + ESD | Row 11 | Phase 6.5 + Phase 6i sim | No schematic ref obtainable |
| GPS+mag JST-GH 10P ESD | Row 12 | Phase 6.5 + Phase 6k sim | Standard TVS practice; can't add without ref |
| CRSF JST-GH 4P ESD | Row 12 | Phase 6.5 + Phase 6k sim | Same |
| Mauch JST-GH 6P ESD | Row 12 | Phase 6.5 + Phase 6k sim | Same |
| AP2112K-3.3 part-choice confirmation | Row 3 | Phase 6.5 | Matek's actual LDO part not sourceable |
| ADC filter values (1 kΩ + 100 nF) | Row 10 | Phase 6h sim | Datasheet-grounded; sim refines |
| SDMMC 47 kΩ pull-up value | Row 7 | Phase 6f sim | SD-spec-middle; sim refines |
| Mauch HS-200-LV calibration (9.0 / 60.6) | Row 10 | **Phase 9 bench (PRIORITY)** | Web-research-sourced; per-unit card refines |
| DShot ringing on bare lines | Row 8 | Phase 6g sim | No series-R; sim validates / sizes if needed |
| USB-CDC diff-pair SI | Row 2 | Phase 6b sim | 12 Mbps full-speed |
| Thermal | Row 13 | Phase 6j sim | Layout-dependent |

---

## Candidate topologies for Phase 6.5 review (DEFER-TO-6.5 items)

Per master 07:00 cross-review emphasis ("audit deep, not just broad"): for items routed to Phase 6.5 because no in-tree / canonical schematic reference is obtainable, this section documents the **standard topologies that EE forum reviewers would expect to see proposed** — so Phase 6.5 starts with a researched candidate menu rather than blank, but worker is NOT silently adding any of these to the schematic (master 3e.5 directive: "don't silently add a non-inherited topology"). These need master / supermaster authorization before landing.

### 5V-input reverse polarity + overvoltage (row 11)

**Standard topology options (research-surveyed):**

1. **P-MOSFET reverse-polarity gate** — single P-FET in the +5V input path; gate held by a pull-up resistor + zener clamp. Standard ~0.3-0.5 mΩ Rds(on) parts (e.g., DMP3098L-7) drop <50 mV at 3 A; reverse-polarity event drives gate-source to forward-bias the body diode then turns the FET off. Cheap, low BOM, single part.
2. **Schottky OR-ing diode** — single low-Vf Schottky in the +5V input path; reverse-polarity blocks via the diode's reverse junction. Simpler than the FET but drops ~0.3 V (significant headroom loss for the AP2112's 250 mV dropout — borderline at BEC sag).
3. **Dual-BEC OR-ing pattern** (Pixhawk redundant): two BEC inputs (primary + secondary backup) OR'd through a pair of low-dropout Schottkys with per-leg reverse-polarity protection. Higher reliability for safety-critical applications; adds a second BEC connector. Not novapcb v1 scope.
4. **TVS clamp on +5V** — bidirectional TVS diode (SMAJ5.0CA or similar) clamps overvoltage transients to ~6.5 V. Complements but doesn't replace reverse-polarity protection.

**Worker recommendation pre-Phase-6.5**: option 1 (P-FET gate) + option 4 (TVS clamp) is the modern minimal-overhead pair. Master/supermaster decides at Phase 6.5 or earlier.

### External-connector ESD (row 12) — GPS/CRSF/Mauch JST-GH ports

**Standard topology options:**

1. **Littelfuse SP3010-04UTG** — 4-channel TVS diode array, ultra-low capacitance, pre-plated frame leads. Rated for high-speed signals (I²C up to 1 MHz; UART up to 420 kbaud for CRSF). 6-pin SOT-23-equivalent footprint.
2. **TI TPD4S012** — 4-channel TVS array, 6 V clamp on signal pins + 20 V clamp on VBUS-like pin. Designed for USB-OTG but applicable to general 4-line interfaces. Similar package.
3. **Discrete TVS per line** — individual TVS diodes (e.g., PESD3V3L4UF, ESDA6V1U4) one per signal line. Higher BOM count but more flexible (mix signal voltages).

**Per-connector application:**
- **Mauch JST-GH 6P** (analog VBAT + CURRENT + +5V): bidirectional TVS on each analog line (slow signals tolerate higher capacitance); +5V TVS shared with row 11.
- **CRSF JST-GH 4P** (USART6 TX/RX + +5V): SP3010-04UTG or TPD4S012 protects TX/RX/+5V; one part covers all 3 signal lines.
- **GPS+mag JST-GH 10P** (UART + I²C + signals + +5V): two SP3010 / TPD4S012 chips cover the 8 signal lines.

**Worker recommendation pre-Phase-6.5**: SP3010-04UTG for the multi-line external connectors (one per CRSF, two for GPS), discrete TVS for the Mauch analog lines. Per-connector decision better than blanket addition; Phase 6.5 reviewer + Phase 6k EMC sim refine. Standard parts in JLCPCB/LCSC catalogs (jellybean class).

### Note on adding these to the schematic

Per `master 3e.5 directive` (Phase 3e cross-review 2026-05-20): "don't silently add a non-inherited topology." None of the above is added to the novapcb v1 schematic without explicit master / supermaster authorization, even though all are standard practice. The audit's job is to surface the menu; the decision belongs upstream.

If supermaster on return wants to elevate ESD/protection topology to ENGINEERING_RIGOR-grade policy (e.g., "all external connectors carrying signals over 100mm of cable require TVS protection captured at Phase 3"), that's the kind of policy that would move ESD from the DEFER-TO-6.5 bucket into the Phase 3 default-required bucket. Worth noting as a queue item alongside the 5 ENGINEERING_RIGOR proposals already in the supermaster-return list.

---

## Audit conclusion

- **No NEEDS-FIX items** — schematic is correct per available references; no schematic correction required before Phase 4 layout.
- **9 subsystems OK-AS-IS** (rows 1, 2, 3, 4, 5, 6, 7, 8, 9, 14) with cross-check depth ranging from full multi-source (rows 1, 5, 6) to single-reference (rows 3, 7) per honest availability.
- **3 subsystems DEFER-TO-6.5 + Phase 6 sim** (rows 11, 12, 13) — schematic-level reference unavailable; external EE review + sim resolve.
- **1 subsystem with PRIORITY-for-Phase-9-bench flag** (row 10 Mauch calibration values).
- **7 Phase 4 carry-forward items** consolidated (symbols, footprints, trace routing).

Phase 3 schematic capture is **VERIFIED CORRECT AT CAPTURE LEVEL** per all references that could be cross-checked. The remaining open items are properly routed to Phase 4 (layout), Phase 6 (simulation), Phase 6.5 (external review), or Phase 9 (bench measurement) — not waiting on a Phase 3 fix.

**Recommendation:** Phase 3-exit can proceed.
