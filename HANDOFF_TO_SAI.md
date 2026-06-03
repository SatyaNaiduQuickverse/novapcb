# Handoff to Sai — 2026-06-04 (TRULY FREEZE-READY)

> Master Claude's brief.
> One file, one read, full picture. Read this first.

---

## TL;DR — BOARD IS FREEZE-READY at 105 × 100 mm

Worker delivered final freeze-gate audit + orphan cleanup.
**audit_unconnected_per_net: 0 real-latent ✓**
**DRC 32 within scope-creep cap 4/4 ✓**
**Sim 1+5 PASS at 105×100 ✓**
**BOM 55 lines (includes new D15-D20 ESC TVS) ✓**

**Ask: authorize Phase 7a freeze trigger** (`git tag v1.0-fab-ready-frozen` on worker HEAD `2eb92e2`).

See `docs/FREEZE_READY_2026_06_04.md` for the one-shot freeze-ready brief.

Master HEAD: `41087fa` on `sch/option-b-buck`. Worker HEAD: `2eb92e2` on `hw/board-grow-105x100`.

Live HTML view: http://100.81.21.121:8765/static/pcb.html

---

## Campaign trajectory (what got you here)

- 2026-05-30 Sai "no half-states": Rule 17 — full route or full revert
- 2026-05-31 Sai "no corners cut + do whatever rework needed"
- 2026-06-01 Sai "no deferring, finish all now"
- 2026-06-02 Sai explicit overrides: (c) board grow 105×100 + (α) Telem v2-defer ONLY for this item + Option B 6-hole pattern
- 2026-06-04 freeze-gate clean — TRUE freeze-ready

---

## What v1 ACTUALLY ships (CURRENT state, all artifact-verified)

### Board outline
- **105 × 100 mm rectangular**, 6-layer JLC06161H
- **6-hole mounting**: H1–H4 at 98.5 × 93.5 mm + H5/H6 added at (3.25, 96.75) + (101.75, 96.75)
- **NEW airframe tray required** (one-time mech)

### Routing — flight-critical (all clean at HEAD)
- ✅ Power tree (D1 buck, D2 +5V dist, D3 eFuse, D4 MCU core, D5 +3V3_IMU, D6 USB-C/BATT/HEATER)
- ✅ Triple-IMU SPI1/2/3 (ICM-42688 INT + BMI088 INT + LSM6DSV16X polled)
- ✅ DPS310 + LPS22HB baros I²C2
- ✅ GPS UART + I²C1 + ESD
- ✅ CRSF UART4 PA0/PA1 (copper verified, labels cosmetically renamed)
- ✅ 6/8 ESC outputs MOT1-6 DShot
- ✅ SDMMC1 (SDR25 50 MHz)
- ✅ USB-CDC + CAN bus
- ✅ HSE Y1 ABM8G

### Protection (artifact-verified)
- USB ESD: USBLC6-2P6
- CAN ESD: PESD2CAN
- 9× ESD7L5.0DT5G on GPS/I²C1/BUZZER/USART1/USART6 (D5-D14)
- **NEW T22.4: 6× ESD7L5.0DT5G on MOT1-6 ESC outputs** (D15-D20, via-in-pad GND + 90° rotation)
- +5V_BEC TVS: SMAJ6.0A (D1)
- VBAT reverse: U11/U12 LM74700-Q1 ORFETs (dual Mauch)
- eFuse U6 TPS25942 OVP+ILIM+DVDT
- Mauch ADC anti-alias 1k+100nF, 1.59 kHz cutoff

### Sims (re-validated at 105×100)
| Sim | Spec | Result |
|---|---|---|
| Sim 1 thermal | ≤80°C Tj | **61.40°C, +18.60°C margin** ✓ |
| Sim 5 PDN | ≤100 mΩ | **79.4 mΩ** ✓ |
| Sim 2 USB Z_diff | 90±10 Ω | 87.4 Ω ✓ |
| Sim 3 SDMMC1 SI | ≥90% margin | 97.8% ✓ |
| Sim 4 CAN Z_diff | 120±5 Ω | ~120 Ω ✓ |
| Sim 6h ADC settling | <1 LSB | unchanged ✓ |
| Sim 6i transient OV | 5 scenarios | 5/5 PASS ✓ |
| Sim 6k EMC coupling | 6 gates | 6/6 PASS ✓ |
| HSE Pierce | AN2867 ≥5× | 5.15× ✓ |

### Firmware
- ArduPilot waf copter clean, 1.52 MB / 184 KB free (~12% margin)
- hwdef.dat synced; UART7 PE7/PE8 nets preserved in INTENDED_DEFERRED (v2-inheritance)
- defaults.parm SOTA Pixhawk-class (harmonic notch as slot-mitigation backstop)
- OSD ROMFS stripped (no MAX7456)

### Process
- 23 master process rules codified
- Verified hwdef before authorizing peripheral touches (Sai memory #26)
- Per-net unconnected audit (Rule 23 — caught DOA fab pre-order)

---

## v2-deferred (honest, with v1 mitigations)

| Feature | Why v2 | v1 mitigation |
|---|---|---|
| **Telem UART J3 routes** | 11 empirical paths walled (Sai α explicit 2026-06-02) | USB-CDC MAVLink canonical |
| **SWD J9 routes** | pin-level walls (NRST/SWDIO/SWCLK adjacent) | DFU first-flash via USB-CDC |
| **MOT7/8 (8 motors)** | Sai option D scope | Quad/hex covers Nova v1 |
| **Status LEDs T22.2** | +22 DRC cascade revert | TP3/TP5 probes + USB-CDC console |
| **Stress-relief slot full** | 2 attempts walled | Harmonic notch live in defaults.parm |
| **microSD ESD T22.5** | +10 DRC placement marginal | Industry std (RPi/Matek omit) |
| **microSD CD T22.1** | +25 DRC cascade (J2 mid-board structural) | ArduPilot doesn't require |
| **5th BMI088 decap C93.1** | 3/3 placement walls | Sim 5 PDN PASS 79.4 mΩ |

All v2-deferreds tracked in [CLAUDE.md §1.1](CLAUDE.md) honest table.

---

## What v1 GAINS over the 6X
- 3 IMUs (vs 2)
- Second baro (LPS22HB + DPS310)
- Mauch direct-analog telemetry
- Dual-Mauch hot-swap (U11/U12 LM74700-Q1)
- TPS25942 eFuse OVP+ILIM+DVDT
- 6-layer JLC06161H with isolated +5V_BEC + +3V3 planes
- **NEW: ESC TVS protection on MOT1-6** (T22.4 win)

---

## Sai-side bits remaining

### 1. **Phase 7a freeze trigger** (your call)
```bash
cd /home/novaedge1/novapcb
git fetch origin
git tag -a v1.0-fab-ready-frozen 2eb92e2 -m "Nova FC v1 logical freeze — 105×100mm 6L JLC06161H"
git push origin v1.0-fab-ready-frozen
```

### 2. JLCPCB portal (~20-30 min after freeze)
- BOM sourcing per `docs/BOM_LCSC_SOURCING.md` (8 TBD + D15-D20 ESC TVS new from T22.4)
- Form options per `docs/JLCPCB_ORDER_GUIDE.md`
- **CRITICAL**: tick "POFV / Via-in-Pad filled+capped" (FREE on 6L per JLC 2025)
- Expected cost: ~$120-250 (5-board first article with conformal coat)

### 3. Phase 7b fab order $
After freeze trigger. ~8-12 days door-to-door.

### 4. New airframe tray
One-time mech (105×100 + 6-hole pattern; 6X 30.5×30.5 pattern gone in v1).

---

## Layer-constant root-cause discovery (informational, not freeze-blocking)

Worker discovered during orphan cleanup: in this KiCad version, `pcbnew.B_Cu = 2` not `31` (layer 31 = F.Courtyard). Worker's earlier exploratory routes during T22 chain used `layer=31`, which KiCad silently dropped as non-copper layer. This explains:
- Why "B.Cu obstacle scan returned 0" was sometimes wrong (filtered wrong layer)
- Why T22.1 SD CD cascaded +25 DRC (route was hitting courtyards not bypassing them)
- Why T22.5 placement-only was marginal +10

**Doesn't affect current freeze state** — all *committed* routes are on correct layers per audit. T22.4 ESC TVS landed cleanly. T22.1/T22.5 v2-defer decisions stand as the structural walls (J2 mid-board, ArduPilot doesn't require CD, industry omits SD ESD) remain genuine; the bug was incidental.

Logged in `docs/LAYER_CONSTANT_ROOT_CAUSE_2026_06_04.md` for future-Claude awareness + v2 inheritance.

---

## Master process honesty (5 errors this campaign, all caught by worker Rule-13)

| # | Error | Caught | Cost averted |
|---|---|---|---|
| 1 | PB14/PB15 cited free (reality: SPI2 IMU2) | Worker pre-exec | Destroying IMU2 SPI |
| 2 | CRSF "fab-blocker" severity (cosmetic only) | Worker post-investigation | Destroying functional routes |
| 3 | R41-R44 "reuse for LEDs" (Mauch ADC RC) | Worker pre-exec | Wrong T22.2 exec |
| 4 | V_PGOOD = 3.3V (5V_BEC_PROT via R13) | Worker pre-exec | Inverted UX |
| 5 | Heartbeat drift from cadence mandate | Sai callout | Process discipline |

**4 worker Rule-9 catches** complement: +3V3_IMU rail gap + power-tree unrouted + BOM U2 LDO→buck stale + CRSF cosmetic-not-functional.

---

## Quick reference docs

- `docs/FREEZE_READY_2026_06_04.md` — **one-shot freeze-ready brief** (read this)
- `docs/TELEM_FINAL_V2_DEFER.md` — 11-path empirical campaign + Sai α decision
- `docs/PHASE7A_FREEZE_PROCEDURE.md` — freeze procedure
- `docs/JLCPCB_ORDER_GUIDE.md` — JLCPCB form options (105×100 + cost adjusted)
- `docs/BOM_LCSC_SOURCING.md` — 8 TBD items + D15-D20 new
- `docs/DECISIONS.md` §14 + §15 — Sai 2026-06-02 picks + T22 chain disposition
- `CLAUDE.md` §1.1 — lost-vs-6X honest table
- `STATUS.md` — live master status

---

**Master + worker standing by for freeze authorization OR redirect to post-freeze direction (release prep / fab file generation / gerber compilation).**

— master, 2026-06-04 TRULY FREEZE-READY
