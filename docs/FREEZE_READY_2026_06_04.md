# FREEZE-READY snapshot — 2026-06-04 (Sai-facing)

> Master Claude's one-shot freeze-readiness brief.
> Read this when you're ready to authorize Phase 7a freeze trigger.

---

## TL;DR

**Board is LOGICAL FREEZE-READY at 105 × 100 mm.** Worker delivered final freeze-gate audit. Sim cascade re-validated at 105×100. T22 chain closed. One residual (+5V orphan stub) being cleaned up before freeze-trigger.

Ask: **authorize Phase 7a freeze trigger** (`git tag v1.0-fab-ready-frozen`) when you're ready, OR redirect.

---

## Freeze-gate audit results (worker on `hw/board-grow-105x100`)

| Gate | Spec | Result | Status |
|---|---|---|---|
| DRC severity-error count | baseline 29 + scope-creep cap 4 | **31** (baseline + 2 T22.4 ESC TVS routing residual) | ✓ within cap |
| Sim 1 thermal (MCU Tj) | ≤80 °C with ≥15 °C margin | **61.40 °C, +18.60 °C margin** (was 66.32 °C at 105×85, -4.92 °C improvement from board grow) | ✓ PASS |
| Sim 5 PDN | ≤100 mΩ mid-band | **79.4 mΩ** (unchanged — board grow improved thermal without disturbing PDN topology) | ✓ PASS |
| Sim 2 USB Z_diff | 90 ±10 Ω | 87.4 Ω (unchanged) | ✓ PASS by inspection |
| Sim 3 SDMMC1 SI | ≥90% timing margin @ SDR25 | 97.8% (unchanged) | ✓ PASS by inspection |
| Sim 4 CAN Z_diff | 120 ±5 Ω | ~120 Ω (unchanged) | ✓ PASS by inspection |
| Sim 6h ADC settling | <1 LSB at 1 kSPS | unchanged | ✓ PASS by inspection |
| Sim 6i transient OV | 5 scenarios | 5/5 PASS | ✓ PASS |
| Sim 6k EMC coupling | 6 gates | 6/6 PASS | ✓ PASS |
| HSE Pierce | AN2867 ≥5× | 5.15× (Y1 ABM8G) | ✓ PASS |
| BOM line count | matches schematic | **55 lines** (includes new D15-D20 ESC TVS) | ✓ |
| audit_unconnected_per_net | 0 real-latent | **1 real-latent residual** (+5V orphan stub at (48.65, 60.49), 1.07 mm) — being cleaned up now | ⏳ cleanup in flight |

---

## What ships in v1 (artifact-verified at HEAD)

### Board outline
- **105 × 100 mm rectangular**, 6-layer JLC06161H stackup
- **6-hole mounting pattern**: H1–H4 at 98.5 × 93.5 mm c-to-c + H5/H6 at (3.25, 96.75) and (101.75, 96.75) — Option B from your 2026-06-02 pick
- **New airframe tray required** (one-time mech — see [JLCPCB_ORDER_GUIDE.md](JLCPCB_ORDER_GUIDE.md))

### Routing — flight-critical (all clean)
- ✅ Power tree (D1 buck + D2 +5V dist + D3 eFuse + D4 MCU core + D5 +3V3_IMU + D6 USB-C/BATT/HEATER + I²C2 baro)
- ✅ Triple-IMU SPI1/2/3 (ICM-42688 INT + BMI088 INT + LSM6DSV16X polled)
- ✅ DPS310 + LPS22HB baros I²C2
- ✅ GPS UART + I²C1 + ESD
- ✅ CRSF UART4 PA0/PA1 (copper verified after worker Rule-9 catch)
- ✅ 6/8 ESC outputs MOT1-6 DShot
- ✅ SDMMC1 (SDR25 50 MHz)
- ✅ USB-CDC + CAN bus
- ✅ HSE Y1 ABM8G crystal

### Protection (artifact-verified)
- USB ESD: USBLC6-2P6
- CAN ESD: PESD2CAN
- 9× ESD7L5.0DT5G arrays on GPS/I²C1/BUZZER/USART1/USART6 (D5-D14)
- **NEW (T22.4): 6× ESD7L5.0DT5G on MOT1-6 ESC outputs** (D15-D20, via-in-pad GND + 90° rotation, +2 DRC)
- +5V_BEC TVS: SMAJ6.0A (D1)
- VBAT reverse: U11/U12 LM74700-Q1 ORFETs (dual Mauch hot-swap)
- eFuse U6 TPS25942 OVP+ILIM+DVDT
- Mauch ADC anti-alias 1k+100nF, 1.59 kHz cutoff

### v2-deferred (honest, with v1 mitigations)
| Feature | Why | v1 mitigation |
|---|---|---|
| Telem UART J3 routes | 11 empirical paths walled (Sai α explicit 2026-06-02) | USB-CDC MAVLink canonical per CLAUDE.md §2.1 |
| SWD J9 routes | pin-level walls (NRST/SWDIO/SWCLK adjacent) | DFU first-flash via USB-CDC + wire-tack |
| MOT7/8 (8 motors) | Sai option D scope | Quad/hex covers Nova v1 |
| Status LEDs (T22.2) | +22 DRC cascade revert | TP3/TP5 probes + USB-CDC console |
| Stress-relief slot (full island) | 2 attempts walled | Harmonic notch live in defaults.parm |
| microSD ESD (T22.5) | placement-only marginal | Industry std (RPi/Matek omit) |
| microSD CD (T22.1) | +25 cascade — J2 mid-board structural | ArduPilot doesn't require CD |
| 5th BMI088 decap (C93.1) | 3/3 placement walls | Sim 5 PDN PASS 79.4 mΩ confirms adequate mid-band |

All v2-deferreds tracked in [CLAUDE.md §1.1](../CLAUDE.md) "What v1 does NOT deliver vs 6X" honest table.

---

## What v1 GAINS over the 6X
- 3 IMUs (vs 2)
- Second baro (LPS22HB + DPS310)
- Mauch direct-analog telemetry
- Dual-Mauch hot-swap via U11/U12 LM74700-Q1 ORFETs
- TPS25942 eFuse +5V_BEC protection
- 6-layer JLC06161H stackup with isolated +5V_BEC + +3V3 planes
- **ESC TVS protection on MOT1-6** (T22.4 win)

---

## Sai-side bits remaining

### 1. Freeze trigger (your call)
```
git tag -a v1.0-fab-ready-frozen -m "Nova FC v1 logical freeze — 105×100mm 6L JLC06161H"
git push origin v1.0-fab-ready-frozen
```

### 2. JLCPCB portal (~20-30 min)
- BOM sourcing per [BOM_LCSC_SOURCING.md](BOM_LCSC_SOURCING.md) — 8 TBD items + D15-D20 ESC TVS (new from T22.4)
- Form options per [JLCPCB_ORDER_GUIDE.md](JLCPCB_ORDER_GUIDE.md)
- **CRITICAL**: tick "POFV / Via-in-Pad filled+capped" for 9 VIP pads (FREE on 6L per JLC 2025 promo)
- Expected cost: ~$120-250 (5-board first article, with conformal coat)

### 3. Phase 7b fab order $
After freeze trigger. ~8-12 days door-to-door.

### 4. New airframe tray
One-time mech (due to 105×100 + 6-hole pattern; 30.5×30.5 Pixhawk pattern is gone in v1)

---

## Master process honesty (5 errors this campaign, all caught by worker Rule-13)

| # | Error | Caught by | Cost averted |
|---|---|---|---|
| 1 | PB14/PB15 cited free (reality: held by SPI2 IMU2) | Worker pre-exec | Destroying IMU2 SPI |
| 2 | CRSF "fab-blocker" severity (reality: cosmetic labels, copper functional) | Worker post-investigation | Destroying functional routes |
| 3 | R41-R44 "reuse for LEDs" (reality: Mauch ADC RC filter) | Worker pre-exec | Wrong T22.2 exec |
| 4 | V_PGOOD = 3.3V → wrong R49 (reality: 5V_BEC_PROT via R13) | Worker pre-exec | Dim/inverted UX |
| 5 | Heartbeat drift from explicit cadence mandate | Sai callout | Process discipline |

**Pattern:** cited doc/BOM claim without verifying SKiDL source. Correction: quote source content + line numbers when citing.

**4 worker Rule-9 catches this session:** +3V3_IMU rail gap + power-tree unrouted + BOM U2 LDO→buck stale + CRSF cosmetic-not-functional diagnosis.

---

## Live HTML view
http://100.81.21.121:8765/static/pcb.html

---

## Master + worker continue

Standing by for freeze authorization OR redirect to post-freeze direction (release prep / fab file generation / gerber compilation).

— master Claude, 2026-06-04
