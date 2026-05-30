# novapcb v1.1 — live status

> Updated continuously by master Claude during autonomous-loop work.
> Most recent merged PR is at the top of the log.

**Current branch:** `sch/option-b-buck` &middot; **Head:** `a0ee44a` (PR #145 HANDOFF refresh; PR #144 silk script; PR #142 T11 REACH FAILURE clean revert; PR #143 J3/J9 Option B DRAFT pending Sai decision)

> Raise-the-bar sweep progress: 13 of 18 (honest: 9 doc/fw wins + 2 reverts + 1 partial + 1 prep). T12 in flight under no-half-state standard. T8 sim runs + 5 hardware-add tasks queued. J3/J9 decision (draft PR #143) pending Sai.

## 2026-05-30 — Raise-the-bar sweep IN PROGRESS (Sai directive: "we finish v1 with full perfection, sota and sureshot")

Honest audit surfaced 12 drifts + 8 rule-shifts where v1 fell short of its own documented goals. Bundling fixes:

### Tier 1 — rule restoration
- **T1** Y1 default → ABM8G (kills HSE AN2867 4.55× worst-case → ≥5× restored)
- **T2** SOTA `defaults.parm` — harmonic notch enabled (the promised software backstop for the partial v1 stress-relief slot), all 3 IMUs enabled, COMPASS_EXTERNAL, file logging, DShot300, BLHeli passthrough, EKF3 — **MASTER COMMITTED ✓**
- **T3** Power-rail LEDs (Option A — adds 5 LEDs, closes orphan R41-R44 BOM line)

### Tier 2 — honest re-scoping
- **T4** CLAUDE.md form-factor + lost-vs-6X table — **MASTER COMMITTED ✓**
- **T6** OPEN_QUESTIONS adjudication (HEATER_PWM Option A + 3 stale-opens resolved) — **MASTER COMMITTED ✓** (hwdef.dat + OPEN_QUESTIONS.md)
- **T8** Phase 6i transient OV + Phase 6k EMC sims + Phase 6.5 forum draft
- **T9** U6 DRU exception cluster root-cause re-place (no codify-the-cap) — **WORKER IN PROGRESS**

### Tier 3 — doc drift cleanup
- **T5** STATUS.md refresh — **THIS COMMIT**
- **T7** CONFIDENCE_MAP rows 11/12 refresh
- **T10** DFM_REPORT §4 refresh (MOT1/2 now routed)
- **T18** Task #8 stitching close (stale-pending) — **DONE**

### Tier 4 — SOTA hardening
- **T11** ESC TVS on J11 (MOT1-8) — MCU GPIO clamp
- **T12** microSD ESD on J2 (SDMMC1)
- **T13** TP1-5 net assignment + silk labels
- **T16** microSD card-detect signal wired

### Tier 5 — sureshot polish
- **T14** Piezo buzzer (board is buzzer-ready)
- **T15** Conformal-coat-ready fab option
- **T17** Silkscreen cleanup (159 warnings)

Standing authorization: B.Cu OK for components not fitting F.Cu; cost increases approved (>$20 BOM or >2 days ask Sai once, don't block).

---

## What ships in v1

### Routing
- ✅ Full power tree: D1 buck + D2 +5V dist + D3 eFuse + D4 MCU core + D5 +3V3_IMU + D6 USB-C CC/BATT/HEATER + I²C2 baro
- ✅ All signal nets: CAN, microSD SDMMC1, GPS UART, CRSF UART4 PA0/PA1, 6/8 motors (MOT7/8 v2-deferred per Sai option D), USB-C diff pair, IMU SPI1/2/3
- ✅ Triple-IMU: U3 ICM-42688 INT-driven, U8 BMI088 INT-driven, U9 LSM6DSV16X polled-mode
- 0 real-latent unconnected per Rule-23 audit (138 plane-pour noise + 13 intended-deferred classified)

### Connectors physically present
J1 USB-C, J2 microSD, J3 Telem (placed; USART1 routes v2-deferred — 4-attempt structural wall), J4 Mauch power, J5 GPS+mag, J9 SWD (placed at (15,35) B.Cu; routes v2-deferred — 9-wall journey), J10 CRSF, J11 ESC outputs (JST-GH SM10B-GHS-TB per PR #136), J19 BATT2, J20 CAN

### Protection (artifact-verified)
- USB ESD: USBLC6-2P6 on D+/D-
- CAN ESD: PESD2CAN
- GPS+mag, I²C1, BUZZER, USART1 Telem, USART6 CRSF: 9× ESD7L5.0DT5G arrays (D5-D14)
- +5V_BEC TVS: SMAJ6.0A (D1)
- VBAT reverse-input: U11/U12 LM74700-Q1 ORFETs (dual Mauch hot-swap)
- eFuse: U6 TPS25942 (OVP+ILIM+DVDT)
- Mauch ADC anti-alias: 1k + 100nF RC, 1.59 kHz cutoff
- (T11/T12 incoming: J11 ESC + J2 microSD ESD)

### Sims (all valid at HEAD per worker provenance audit)
- Sim 1 thermal: MCU Tj 65.05°C, +15°C margin (PR #126 re-validation)
- Sim 2 USB Z_diff: 87.4Ω
- Sim 3 SDMMC SI: 172ps skew = 97.8% timing margin @ SDR25 50MHz
- Sim 4 CAN Z_diff: ~120Ω near-ideal
- Sim 5 PDN: 79.4 mΩ peak ≤ 100 mΩ gate
- HSE Pierce analytical: 6-10× margin in typical scenarios (worst-case 4.55× — T1 ABM8G swap raises floor)
- (T8 incoming: Sim 6i transient OV + Sim 6k EMC + Phase 6.5 forum draft)

### Firmware
- ArduPilot waf copter builds clean — 1.52 MB used / 184 KB free of H743 2 MB flash (~12% margin)
- hwdef.dat sync'd to schematic post all re-pins (CRSF→UART4, GPS1_TX→PA2, BUZZER→PD7, HEATER_PWM PA15 GPIO(33), MCU pin map complete)
- defaults.parm SOTA Pixhawk-class — harmonic notch + IMU enables + COMPASS_EXTERNAL + EKF3 + DShot300 + file logging (this commit)
- OSD ROMFS stripped (no MAX7456 on board) — frees ~10-30 KB flash

### Process discipline
- 23 master process rules codified (Rule 17 no-loose-threads, Rule 21 Sai-overrides-worker-pause, Rule 22 spec-doc-≠-artifact, Rule 23 per-net unconnected audit — the rule that caught the dead-on-arrival fab pre-order)
- Audit gates: `scripts/audit_unconnected_per_net.py` + `scripts/audit_layout_compliance.py` — both PASS at freeze head
- CLI DRC = GUI DRC equivalence documented (PR #134)

---

## Fab spec line items (Sai at JLCPCB SMT order time)

- **9 VIP pads total**: U1.48 (VCAP1), U4.3 + U4.4 (I²C2 baro), plus 4 existing ORING_GATE/+5V_BEC + 2 EFUSE. Tick "Via-in-pad filled+capped" (IPC-4761 Type VII / POFV) on JLC SMT form. **FREE on 6L boards as of 2025** (was ~$10 adder). Documented `docs/DECISIONS.md` §13.1b + `bom/SOURCING_NOTES.md` §5 + `docs/JLCPCB_ORDER_GUIDE.md`.

---

## What's left to freeze-ready (Sai-bits)

JLCPCB portal BOM sourcing (8 TBD items researched in `docs/BOM_LCSC_SOURCING.md`), fab spec options per `docs/JLCPCB_ORDER_GUIDE.md`, Phase 7a freeze trigger, Phase 7b fab order $.

Master + worker continue raise-the-bar sweep until all Tier 1-5 tasks landed.

**Board:** 105×85 mm, 6-layer JLC06161H, STM32H743VIT6, Pixhawk 6X functional drop-in (electrical/software near-parity per CLAUDE.md §1.1).
**Live HTML view:** http://100.81.21.121:8765/static/pcb.html
