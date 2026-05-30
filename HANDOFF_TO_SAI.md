# Handoff to Sai — 2026-05-30 (post-raise-the-bar sweep, freeze-ready)

> Master Claude's brief.
> One file, one read, full picture. Read this first.

---

## TL;DR

**Board is LOGICAL FREEZE-READY** with bar-restoration in flight. Real-latent = 0. Power tree complete + sims valid + firmware builds clean. **Raise-the-bar sweep underway** — see §"Raise-the-bar status" below.

Head: `5f40d35` on `sch/option-b-buck` (PR #144 silk script).
Live HTML view: http://100.81.21.121:8765/static/pcb.html

---

## Raise-the-bar status (Sai SOTA + sureshot directive)

13 of 18 tasks done — but **honest count is more like 9 doc/firmware clean wins + 2 honest reverts/reframes + 1 partial + 1 prep doc**. Hardware ADDS pending.

### Done (clean wins)
- **T1** Y1 HSE crystal → ABM8G (5.15× AN2867 margin, was 4.55× sub-spec) ✓
- **T2** SOTA `defaults.parm` — harmonic notch live, 3 IMUs enabled, EKF3, file logging, DShot300 ✓
- **T4** CLAUDE.md honest update — §1 form factor truth + §1.1 lost-vs-6X table ✓
- **T5** STATUS refresh ✓
- **T6** OPEN_QUESTIONS 4 stale-opens adjudicated (HEATER PA15 Option A, LDO-vs-buck → buck RESOLVED, USB fan DFM PASS, MAX7456 v2-defer) ✓
- **T7** CONFIDENCE_MAP rows 11/12 refreshed (artifact-verified, raised LOW → MEDIUM) ✓
- **T10** DFM_REPORT MOT1/2 refresh ✓
- **T15** Conformal-coat fab option in order guide ✓
- **T18** Stitching task closed (was stale-pending) ✓

### Done (honest reverts / reframes — bar held, not raised)
- **T9** U6 DRU cluster — re-place attempts cascaded → audit script refined to classify FAB-TIER (inherent IC package) vs SCOPE-CREEP (placement-density relax). Board pristine. **Reframe, not improvement.** PR #137.
- **T11** ESC TVS on J11 — placed → 3 stub attempts cascaded → master corrected "no half-state" mid-PR → **full revert**. v1 ships without ESC ESD. PR #142 + `docs/T11_REACH_FAILURE.md`.

### Partial
- **T8** Phase 6i transient OV + Phase 6k EMC sims + Phase 6.5 forum review — master prepped specs + forum draft; **worker sim runs pending** (PRs #140 + #141).

### Pending (worker in flight + queue)
- **T12** microSD ESD on J2 — worker in flight under no-half-state standard
- **T3** PGOOD power-rail LEDs (Option A — add 5 LEDs, reuse R41-R44)
- **T13** TP1-5 net assignment + silk labels
- **T14** Piezo buzzer
- **T16** microSD card-detect signal wired
- **T17** Silkscreen cleanup — script committed PR #144; worker executes
- **T8 finale** Sim 6i + 6k worker execution

### Awaiting Sai decision (draft PR #143 ready)
**J3 Telem + J9 SWD connectors** — same half-state pattern as T11. Currently placed + assembled, but routes v2-deferred. Three options:
- A keep status quo (you approved earlier with structural evidence)
- B **mark DNP** — footprints stay, parts don't ship — **draft PR #143 ready to merge**
- C full revert — footprints removed

---

## What ships in v1 (current state)

### Routing
- ✅ Full power tree: D1 buck + D2 +5V dist + D3 eFuse + D4 MCU core + D5 +3V3_IMU + D6 USB-C CC/BATT/HEATER + I²C2 baro
- ✅ All signal nets: CAN, microSD SDMMC1, GPS UART, CRSF UART4 PA0/PA1, 6/8 motors, USB-C diff pair, IMU SPI1/2/3
- ✅ Triple-IMU: U3 ICM-42688 + U8 BMI088 INT-driven; U9 LSM6DSV16X polled
- 0 real-latent unconnected per Rule-23 audit

### Protection (artifact-verified)
- USB ESD: USBLC6-2P6 ✓
- CAN ESD: PESD2CAN ✓
- GPS+mag / I²C1 / BUZZER / USART1 Telem / USART6 CRSF: 9× ESD7L5.0DT5G (D5-D14) ✓
- +5V_BEC TVS: SMAJ6.0A (D1) ✓
- VBAT reverse-input: U11/U12 LM74700-Q1 ORFETs ✓
- eFuse U6 TPS25942 (OVP+ILIM+DVDT) ✓
- Mauch ADC anti-alias: 1k+100nF, 1.59 kHz cutoff ✓
- **GAP**: J11 ESC outputs no TVS (T11 REACH FAILURE)
- **PENDING**: J2 microSD ESD (T12 in flight)

### Sims (valid at HEAD)
- Sim 1 thermal: MCU Tj 65.05°C, +15°C margin ✓
- Sim 2 USB Z_diff: 87.4Ω ✓
- Sim 3 SDMMC SI: 97.8% timing margin @ SDR25 50MHz ✓
- Sim 4 CAN Z_diff: ~120Ω ✓
- Sim 5 PDN: 79.4 mΩ ≤ 100 mΩ gate ✓
- HSE Pierce analytical: 5.15× AN2867 worst-case (post-T1 ABM8G swap) ✓
- **PENDING**: Sim 6i transient OV + Sim 6k EMC (T8 worker execution)

### Firmware
- ArduPilot waf copter builds clean — 1.52 MB / 184 KB free (~12% margin)
- hwdef.dat sync'd to schematic; HEATER PA15 software-PWM via GPIO(33); OSD ROMFS stripped
- defaults.parm SOTA Pixhawk-class — harmonic notch live as the slot-mitigation backstop

### Process
- 23 master process rules codified
- Rule 17 no-loose-threads + Rule 23 per-net unconnected — both live audit gates
- **NEW STANDARD**: hardware adds must be full-route or full-revert, never half-state (codified from T11 live-fire test)

---

## Sai-side work remaining

### Decisions (your call)
1. **J3 + J9 connectors** — A/B/C per draft PR #143
2. **Phase 6.5 forum post** — review + edit `docs/PHASE_6.5_FORUM_DRAFT.md`, pick category, post under your identity

### At JLCPCB portal (~20-30 min)
- BOM sourcing per `docs/BOM_LCSC_SOURCING.md` (8 TBD items researched)
- Form options per `docs/JLCPCB_ORDER_GUIDE.md` (now includes conformal-coat option from T15)
- **CRITICAL**: tick "POFV / Via-in-Pad filled+capped" for 9 VIP pads (FREE on 6L)

### Phase 7a freeze trigger + Phase 7b fab order $
After worker queue lands + you approve final state.

---

## Quick reference docs

- `docs/JLCPCB_ORDER_GUIDE.md` — click-by-click order workflow (with conformal-coat option per T15)
- `docs/BOM_LCSC_SOURCING.md` — 8 TBD components researched
- `docs/T11_REACH_FAILURE.md` — ESC TVS structural diagnosis (why v1 ships without)
- `docs/PHASE_6.5_FORUM_DRAFT.md` — your forum post draft (Sai-gate to post)
- `docs/SIM_6I_TRANSIENT_OV_SPEC.md` + `docs/SIM_6K_EMC_SPEC.md` — worker sim specs
- `docs/SWD_PHYSICAL_DELIVERABLE.md` — 9-wall journey + first-flash procedure
- `docs/DFU_BOOTLOAD_PROCEDURE.md` — exact `dfu-util` command for first flash
- `docs/DECISIONS.md` — all locked v1 decisions
- `STATUS.md` — live status (master keeps current)
- `CLAUDE.md` — canonical project context + §1.1 lost-vs-6X table (refreshed 2026-05-30)

---

**Master + worker continuing the queue.** Standing by.

— master, 2026-05-30 raise-the-bar session.
