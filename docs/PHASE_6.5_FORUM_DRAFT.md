# Phase 6.5 — ArduPilot forum review draft (DRAFT — NOT POSTED)

> **Status:** DRAFT 2026-05-30 by master Claude per Sai T8 raise-the-bar directive.
> **Gate:** Sai-side review + approve before posting to https://discuss.ardupilot.org.
> **Purpose:** community technical review of novapcb v1 by experienced ArduPilot hardware/firmware contributors. Targets CONFIDENCE_MAP rows 11 (reverse-polarity + ESD) and 12 (EMC/RF coupling) — both LOW → MEDIUM (post raise-the-bar) → forum-review feedback raises to HIGH per the map's rule "confidence rises by evidence, never by argument."

---

## Forum post — title

> **[hardware-review] novapcb v1 — STM32H743 ArduCopter board, Pixhawk 6X functional drop-in — pre-fab community review request**

## Forum post — body

Hi all,

I'm finalising a custom STM32H743VIT6 flight controller (novapcb v1) as a Pixhawk 6X functional drop-in for the Nova drone. Software side already validated against a Pixhawk 6X running ArduCopter v4.6.3 (USB-CDC MAVLink, 115200 baud, `usb-ArduPilot_*` udev pinning matched). Hardware is about to go to JLCPCB; before placing the fab order I'd like a community technical review on three subsystems where my own confidence is MEDIUM rather than HIGH, plus a sanity check on a few unconventional choices.

Repo: https://github.com/SatyaNaiduQuickverse/novapcb (sch/option-b-buck branch is the freeze candidate).

### Board summary

- 105 × 85 mm rectangular, 6-layer JLC06161H-3313 stackup (F.Cu / In1 GND / In2 +5V_BEC / In3 +3V3 / In4 GND / B.Cu), 1.6 mm thick
- STM32H743VIT6 LQFP-100 + HSE 8 MHz (ABM8G), TPS62177 buck for +3V3, TPS25942 eFuse on +5V_BEC, dual Mauch via LM74700-Q1 ORFETs
- Triple-IMU island: ICM-42688-P (SPI1, INT-driven), BMI088 (SPI2, INT-driven), LSM6DSV16X (SPI3, polled — INT routing v2-deferred per structural walls)
- Dual baro: DPS310 (I²C2) + LPS22HB
- External GPS+mag on J5 (UART4 + I²C1), CRSF on UART4-PA0/PA1 via J10
- 6/8 motor outputs via JST-GH (MOT7/8 v2-deferred — quad/hex covers v1; MOT3-PA0 reassigned to MOT3 since CRSF re-pin)
- microSD logging via SDMMC1 SDR25
- Telem J3 (USART1) + SWD J9 connector physically present; net routes v2-deferred (4-wall + 9-wall structural diagnoses documented)
- Partial stress-relief slot at IMU island (SE-corner 1.2 × 24.5 mm); full island isolation deferred to v2. **Software backstop: harmonic notch enabled in `defaults.parm`** (INS_HNTCH_ENABLE 1, throttle-based, 80 Hz initial freq, double-notch + dynamic update).

### What I'd appreciate review on

#### 1. Reverse-polarity + ESD protection topology (CONFIDENCE_MAP row 11)

VBAT path uses two LM74700-Q1 ORFETs (U11/U12) for dual-Mauch hot-swap and reverse-input-protection. Behind those, +5V_BEC has a SMAJ6.0A unidirectional 600W TVS clamp + TPS25942 eFuse (OVP trip at 6.04 V, ILIM ~2 A, DVDT slew control). Mauch ADC sense lines go through 1 kΩ + 100 nF RC anti-alias (1.59 kHz cutoff) before MCU ADC1.

Specific questions:
- Is the LM74700-Q1 + SMAJ6.0A + TPS25942 sequencing right for a 4-6S Mauch input? I have the TPS25942 ILIM at ~2 A based on FC load + sensor budget; that feels tight for momentary inrush. Would you raise ILIM or add a separate inrush limiter?
- I do not have separate **TVS on the J11 ESC outputs** (8 DShot signals direct to JST-GH); is the ESC pigtail field-failure mode (lead pulled hot, motor short on crash) common enough to warrant adding a quad-channel TVS array near the connector? I'm planning T11 to add this; would like sanity check.

#### 2. EMC / RF coupling — buck switching node + IMU SPI proximity (row 12)

The TPS62177 buck switching node runs ~1.8 MHz. The IMU island sits ~25–35 mm from U2 (I followed the "buck-to-IMU ≥ 25 mm" master condition from the thermal-architecture decision doc); switching loop is minimized; magnetic axis is rotated away from the IMUs; output filter has bulk + HF caps per datasheet typical-application.

I have **Sim 5 PDN impedance** mid-band peak at 79.4 mΩ (target ≤ 100 mΩ) and **Sim 1 thermal** Tj 65.05 °C (target ≤ 80 °C) — both PASS at HEAD. **Sim 6k EMC/RF coupling sim is in flight** (T8) but not yet run.

Specific questions:
- Does anyone with a TPS62177-on-FC board have empirical IMU noise-floor data they could share? The IMU3 LSM6DSV16X is in polled-mode (INT routing structurally walled in v1); a buck-driven IMU noise increase shows up worse in polled mode than INT mode.
- Spread-spectrum is enabled on the buck. Worth disabling if the FFT lobes happen to fall on the IMU sample-rate harmonics? (My current take: no — the spread-spectrum noise distribution is gentler than a single tone even if it overlaps.)

#### 3. defaults.parm — harmonic notch initial config sanity check

Stress-relief slot is partial only (single SE-corner slit, not full island isolation — 2 routing attempts walled). Software harmonic notch is the documented mitigation. Initial values shipping:

```
INS_HNTCH_ENABLE 1
INS_HNTCH_MODE 1       # throttle-based (no BLHeli telem in stock v1)
INS_HNTCH_REF 0.35     # hover throttle for ~quad
INS_HNTCH_FREQ 80      # initial center freq Hz
INS_HNTCH_BW 40
INS_HNTCH_HMNCS 7      # 3 harmonics
INS_HNTCH_OPTS 6       # double-notch + dynamic update
```

User retunes FREQ + REF post first hover from FFT log. Does this look reasonable for a Pixhawk-class FC with a single SE-corner slot? Anything obviously off for first-flight defaults?

#### 4. Sanity checks (low-confidence corners I'd appreciate eyes on)

- **HSE crystal**: Y1 = Abracon ABM8G-8.000MHZ-4Y-T3 (8 MHz, ESR ≤ 120 Ω max, C0 ≤ 5 pF, CL = 8 pF). C24/C25 = 18 pF NP0 0402, placed ≤ 1.5 mm to Y1 pads. AN2867 worst-case margin = 5.15× (Scenario B). PCB stray Cs assumed 3–5 pF. Acceptable for ArduPilot use?
- **VID/PID**: using ArduPilot global default 0x1209:0x5740 (pid.codes ArduPilot family) — same as Pixhawk 6X. Manufacturer string "ArduPilot", product "novapcb-v1". udev `usb-ArduPilot_*` glob resolves cleanly. Anyone aware of downstream tooling that whitelists specific PID and would reject this?
- **DRU exception count**: 28 KiCad-CLI DRC flags, all covered by documented `.kicad_dru` rules (POFV via-in-pad, SOT-23-6 ORFET courtyard relaxation, WQFN-24 eFuse fine-pitch). Worker audit reclassified 23/28 as FAB-TIER (inherent to IC package choice) and 5/28 as SCOPE-CREEP (placement-density relaxation). The board passes GUI DRC + has 0 unexpected-DRC + 0 copper_edge_clearance. Sane?

### Things I'm intentionally NOT asking about

- ArduPilot dialect / MAVROS compat — already validated against a running Pixhawk 6X
- Form-factor / mounting pattern — v1 is NOT a 6X mechanical drop-in (new airframe tray required); v2 will be FMUv6X
- Connector pinouts — following Pixhawk DS-009 standard
- BOM sourcing — JLCPCB Basic/Extended catalog, researched

### Wrap

Happy to share the .kicad_pcb file + the full STATUS.md + CLAUDE.md (project context) on request. Schematics are SKiDL-generated (`hardware/kicad/novapcb/sheets/*.py`) — netlist is the authoritative source.

Thanks in advance for any eyes. Will summarize the feedback back into a doc in the repo and credit reviewers if any specific issue surfaces. Posted pre-fab so I can incorporate before placing the order at JLCPCB.

— Sai (project owner) / posted with help from Claude (CAD + audit automation)

---

## Posting checklist (Sai-side before clicking submit)

- [ ] Sai reviews this draft text
- [ ] Sai approves or edits the questions
- [ ] Sai picks the appropriate Discuss category (likely "Hardware" or "Custom Autopilot")
- [ ] Sai posts under their forum identity (not Claude's)
- [ ] Master commits a follow-up doc `docs/PHASE_6.5_FORUM_FEEDBACK.md` summarizing any community responses
- [ ] CONFIDENCE_MAP rows 11+12 raised based on feedback evidence (rule: confidence rises by evidence, never by argument)
