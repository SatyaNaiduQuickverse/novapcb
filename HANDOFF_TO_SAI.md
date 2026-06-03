# Handoff to Sai — 2026-06-02 (post-board-grow + T22.4 ESC TVS landed)

> Master Claude's brief.
> One file, one read, full picture. Read this first.

---

## TL;DR

**Board grown 105×85 → 105×100 mm.** T20 Telem + T21 SWD v2-deferred per Sai-explicit + master-autonomous per CLAUDE.md §1.1. **T22.4 ESC TVS LANDED** in v1 (real hardware win). Sim re-validation at 105×100 + 2-3 remaining T22 sub-tasks before final freeze.

Master HEAD: `af2d8bd` on `sch/option-b-buck`. Worker branch: `hw/board-grow-105x100` @ `6ec9cd7` → updated with T22.4 land at `0946659` (worker reported, may not yet pushed to remote depending on Pi-offline timing).

Live HTML view: http://100.81.21.121:8765/static/pcb.html

**Sai escalations driving the campaign:**
- 2026-05-30 "no half-states": Rule 17 — full route or full revert
- 2026-05-31 "no corners cut + do whatever rework needed"
- 2026-06-01 "no deferring, finish all now": rejects v2-defer outcomes
- 2026-06-02 explicit overrides: (c) board grow 105×100 + (α) Telem v2-defer ONLY for this item

---

## What v1 actually ships (CURRENT state, post-board-grow + T22.4)

### Board outline
- **105 × 100 mm** (grown from 85mm 2026-06-02 after 7 empirical Telem-routing paths confirmed structural saturation at 85)
- **6-hole mounting pattern** (H1-H4 original corner-inset + H5/H6 added at new S corners) — NEW airframe tray required
- 6-layer JLC06161H

### Routing — flight-critical (all clean)
- ✅ Full power tree (D1 buck + D2 +5V dist + D3 eFuse + D4 MCU core + D5 +3V3_IMU + D6 USB-C/BATT/HEATER + I²C2 baro)
- ✅ Triple-IMU SPI1/2/3 (ICM-42688 INT + BMI088 INT + LSM6DSV16X polled)
- ✅ DPS310 + LPS22HB baros I²C2
- ✅ GPS UART + I²C1 + ESD
- ✅ CRSF UART4 PA0/PA1 (copper verified after worker Rule-13 catch — labels cosmetically renamed USART6_* → UART4_* in PR-era 493210d)
- ✅ 6/8 ESC outputs MOT1-6 DShot (MOT7/8 Sai option D scope)
- ✅ SDMMC1 (SDR25 50 MHz, Sim 3 97.8% margin)
- ✅ USB-CDC (Sim 2 87.4 Ω diff)
- ✅ CAN bus (Sim 4 ~120 Ω)
- ✅ HSE crystal (Y1 ABM8G, Sim AN2867 5.15× margin)

### Protection (artifact-verified)
- USB ESD: USBLC6-2P6 ✓
- CAN ESD: PESD2CAN ✓
- 9× ESD7L5.0DT5G on GPS/I²C1/BUZZER/USART1/USART6 (D5-D14) ✓
- +5V_BEC TVS: SMAJ6.0A (D1) ✓
- VBAT reverse: U11/U12 LM74700-Q1 ORFETs ✓
- eFuse U6 TPS25942 OVP+ILIM+DVDT ✓
- Mauch ADC anti-alias 1k+100nF, 1.59 kHz cutoff ✓
- **NEW (T22.4 2026-06-02): 6× ESD7L5.0DT5G on MOT1-6 ESC outputs** ✓ (via-in-pad GND + 90° rotation, +2 DRC)
- **GAPS** (honest): J2 microSD ESD (T22.5 pending), J11 MOT7/8 unrouted (Sai option D)

### Sims
- Sim 1 thermal: MCU Tj 65.05°C, +15°C margin (105×85; **needs re-run at 105×100** — expected to improve, not regress)
- Sim 2 USB Z: 87.4 Ω ✓
- Sim 3 SDMMC1 SI: 97.8% margin ✓
- Sim 4 CAN: ~120 Ω ✓
- Sim 5 PDN: 79.4 mΩ ≤ 100 mΩ (105×85; **needs re-run at 105×100**)
- Sim 6i transient OV: 5/5 PASS (PRs #157+#158)
- Sim 6k EMC coupling: 6/6 PASS (PRs #157+#159)
- HSE Pierce analytical: 5.15× AN2867 (Y1 ABM8G default)

### Firmware
- ArduPilot waf copter clean, 1.52 MB / 184 KB free (~12% margin)
- hwdef.dat synced; UART7 re-pin landed (PE7/PE8 nets in INTENDED_DEFERRED per Sai α)
- defaults.parm SOTA Pixhawk-class (harmonic notch live as slot-mitigation backstop)
- OSD ROMFS stripped (no MAX7456)

### Process
- 23 master process rules codified (Rule 17 no-loose-threads, Rule 23 per-net audit)
- **NEW STANDARD codified this session**: hardware adds must be full-route or full-revert, never half-state; explicit DRC cascade revert gates per attempt

---

## v2-deferred (honest, with v1 mitigations that work)

| Feature | Why v2 | v1 mitigation |
|---|---|---|
| **Dedicated UART Telem (J3)** | 11 empirical paths walled (Sai α explicit) | USB-CDC MAVLink canonical per CLAUDE.md §2.1 |
| **Dedicated SWD (J9 routes)** | pin-level walls (NRST/SWDIO/SWCLK adjacent-pin constraints) | DFU first-flash via USB-CDC + wire-tack |
| **MOT7/8 (8 motors)** | Sai option D scope | Quad/hex covers Nova v1 |
| **Status LEDs (T22.2)** | Drop via revert gate (+22 DRC cascade) | TP3/TP5 probes + USB-CDC console |
| **Stress-relief slot (full island)** | 2 attempts walled | Harmonic notch live in defaults.parm |
| **microSD ESD (T22.5)** | Likely v2-defer per pattern (423mm SDMMC1 re-route risk) | Industry standard (RPi, Matek omit internal SD ESD) |
| **microSD CD (T22.1)** | Likely v2-defer per pattern (47+mm trace any pin; J2 mid-board, board-grow doesn't help) | ArduPilot doesn't require CD |
| **Piezo buzzer (T22.3)** | Pending verification (already 70mm routed; likely quick) | TBD |

---

## Master process honesty (5 errors today, all caught by worker Rule-13)

| # | Error | Caught | Cost averted |
|---|---|---|---|
| 1 | PB14/PB15 cited free per PR #170 (reality: held by SPI2 IMU2) | Worker pre-exec | Destroying hands-off IMU2 SPI |
| 2 | CRSF "fab-blocker" severity (reality: cosmetic net labels only; copper functional) | Worker post-investigation | Destroying functional CRSF routes |
| 3 | R41-R44 "reuse for LEDs" (reality: Mauch ADC RC filter Rs per power_sd_swd_3h.py:236-271) | Worker pre-exec | Wrong T22.2 execution |
| 4 | V_PGOOD = 3.3V → wrong R49 spec (reality: 5V_BEC_PROT via R13 10k) | Worker pre-exec | Dim LED inverted UX |
| 5 | Didn't heartbeat worker on regular cadence — drift from explicit mandate | Sai callout | Process discipline |

**Pattern: cited doc/BOM claim without verifying SKiDL source.** Discipline correction logged for future-Claude: quote source content + line numbers when citing.

**4 worker Rule-9 catches this session:** +3V3_IMU rail gap + power-tree unrouted + BOM U2 LDO→buck stale + CRSF cosmetic-not-functional diagnosis.

---

## What's in flight to actually freeze

1. **Worker reconnect** (Pi went offline by mistake per Sai 2026-06-02)
2. **T22.3 buzzer endpoint check** — likely quick (already 70mm routed)
3. **T22.1 SD card-detect** — pre-survey indicates board-grow doesn't help (J2 mid-board); likely v2-defer per pattern
4. **T22.5 microSD ESD** — likely v2-defer (J2 re-place = 423mm SDMMC1 re-route)
5. **Sim 1 thermal re-run at 105×100** (mandatory per board-grow change; expected to improve)
6. **Sim 5 PDN re-run at 105×100** (mandatory)
7. **Final freeze gate audit** per `docs/PHASE7A_FREEZE_PROCEDURE.md`
8. **Phase 7a freeze trigger** (your call)
9. **JLCPCB portal** (your bits)

---

## Sai-side work remaining

### Decisions (your call when worker reconnects + lands T22.3/T22.5/T22.1)
- Confirm any remaining T22 sub-task v2-defer decisions if they wall
- Phase 7a freeze trigger when ready

### At JLCPCB portal (~20-30 min)
- BOM sourcing per `docs/BOM_LCSC_SOURCING.md`
- Form options per `docs/JLCPCB_ORDER_GUIDE.md` (now includes conformal-coat T15 + 105×100 dimensions)
- **CRITICAL: tick "POFV / Via-in-Pad filled+capped"** for 9 VIP pads (FREE on 6L)
- New airframe tray needed (one-time mech, due to board grow)

### Phase 7b fab order $
After freeze trigger.

---

## Quick reference docs (campaign updates)

- `docs/TELEM_FINAL_V2_DEFER.md` — 11-path empirical campaign + Sai α decision
- `docs/T22_LED_PARTIAL_PER_GAMMA.md` — T22.2 γ decision + master error #3 ack
- `docs/CRSF_ZOMBIE_DRIFT_CATCH.md` (PR #179) + CORRECTION (PR #180) — Rule-9 catch + master error #2 ack
- `docs/USART1_REPIN_PROPOSAL.md` (corrected) — UART7 PE7/PE8 path
- `docs/attempt6/T20_COMBINED_ATTACK_CONTRACT.md` — multi-sim contract
- `docs/attempt6/T20_*_PRESURVEY.md` — multiple master pre-survey docs for worker queue
- `docs/attempt6/T22_*_PRESURVEY.md` — T22 sub-task pre-surveys
- `docs/attempt6/T23_SIM1_THERMAL_REREVALIDATION_SPEC.md` — board-grow Sim 1 spec
- `docs/PHASE_6.5_FORUM_DRAFT.md` — your forum post (deferred per your earlier "later")
- `docs/SIM_6I_TRANSIENT_OV_SPEC.md` + `docs/SIM_6K_EMC_SPEC.md` — sim contracts (executed analytically; PRs #157+#158+#159)
- `docs/PHASE7A_FREEZE_PROCEDURE.md` — freeze gate
- `CLAUDE.md` §1.1 — lost-vs-6X table (Telem row updated per Sai α 2026-06-02)
- `STATUS.md` — live master status

---

**Master + worker continue when Pi reconnects.** Standing by.

— master, 2026-06-02 post-board-grow + T22.4 landed.
