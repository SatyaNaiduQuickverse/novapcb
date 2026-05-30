# U9 LSM6DSV16X re-place structural diagnosis — 2026-05-28

> **Status:** in-progress structural diagnosis. Worker has done 3 manual + 1 full-DSN-FR + 1 scoped-FR routing attempts at 2 candidate placements (C2 (55.5, 44.0) and C1 (58, 45.5)) for the U9 re-place to "IMU-at-center." All attempts hit the same density wall. This doc records the empirical evidence.

---

## 1. Context

Sai 2026-05-28: "imu should be at centre right" raised the IMU-at-center quality principle. U9 (LSM6DSV16X tertiary IMU) currently at (78, 56) is 28mm NE of board center (52.5, 42.5) — worst of the 3 IMUs.

Master decision: re-place U9 to under-MCU B.Cu near board center to solve both routing problem (IMU3_INT1 was structurally walled at PB2) and quality problem (CG correlation).

## 2. Empirical attempts log

| Attempt | Method | Placement | Fouls | Outcome |
|---|---|---|---|---|
| 1 | Manual SPI3 (body interior) | C2 (55.5, 44.0) | 88 | Walled by BATT2/USART6/GPS1/inner planes |
| 2 | Manual SPI3 (VIPs + diverge) | C2 (55.5, 44.0) | 79 | Iterative reduction; per-foul rate too slow |
| 3 | Manual SPI3 (N-edge wrap + east drop) | C1 (58, 45.5) | 97 | WORSE — placement change didn't fix routing density |
| 4 | Full-DSN Freerouting | C2 (55.5, 44.0) | n/a | 9h CPU, frozen log, no SES output. FR stuck on search-space explosion |
| 5 | Scoped FR (5 nets + rail tail) | C1 (58, 45.5) | **NO SES at 30-min cap** | Same frozen-log + CPU-pegged pattern as attempt 4. Search-space wedged. |

## 3. Root cause analysis

**Density pattern:** the board area X43-58 Y28-46 (between MCU N-edge and the U9 target region) is densely transited by **existing correct routing**:
- BATT2 voltage/current sense
- USART6 (legacy CRSF net name; physically UART4 traces post PR #120)
- HEATER_PWM (IMU heater FET drive)
- IMU2_GYR_CS, IMU2_ACC_CS, IMU2_GYR_INT3, IMU2_ACC_INT1
- I2C1_SCL/SDA + via stitching
- SDMMC1_CMD/D0/D1/D2 transit lanes
- USB-C diff pair + CC pulldowns (NE corner)
- +3V3 plane stitching vias
- +5V_BEC In2 zone (B.Cu plane below MCU)

The above routes were placed when U9 was at (78, 56). They form a density "shape" that left clean corridors going TO the old U9 location, not to the under-MCU center.

**Moving U9 to center means re-routing 5 new nets THROUGH this density.** The density itself can't be efficiently re-routed (touches hands-off SPI1/SPI2/SDMMC1/USB) without massive blast radius.

**Self-referential constraint:** the board's existing density is what it is BECAUSE OF U9's prior position. Moving U9 creates a routing problem that wasn't there when U9's location set the density.

## 4. Scope considerations

**To complete U9-at-center cleanly:**
- 5 new signal routes through the dense area
- Continue per-foul iteration (rate ~5 min/foul → 8-10h on C1's 97 fouls or 2-3 days on full C2)
- OR re-route the existing density (touches hands-off, regresses validated PRs)
- OR re-place additional components to free corridors (Phase 4a-level redesign)

**Alternative — accept original placement:**
- Roll back U9 to (78, 56) F.Cu — original position
- Keep all original SPI3/IMU3_CS routing (already merged in PR #105 etc., clean DRC)
- Accept IMU3_INT1 v2-defer (option t): pad-deferred whitelist entry; polled-mode IMU3 in firmware
- ArduPilot polled-mode IMU3 is electrically functional (~1 kHz polling vs INT-driven sample-ready)
- IMU1 (ICM-42688) primary remains INT-driven on SPI1 at 5mm from center
- IMU2 (BMI088) secondary INT-driven on SPI2 at 16mm from center
- IMU3 (LSM6DSV16X) tertiary polled-mode at 28mm from center
- Triple-IMU redundancy: 2× INT + 1× polled (still functional for vote-disagree at lower update rate)

## 5. Honest assessment

The U9-at-center principle is correct. But **its execution in late Phase 4d-redux exceeds reasonable v1 blast radius.** v2 board respin should:
- Design IMU-at-center from Phase 4a placement
- Use INT-driven all 3 IMUs from initial layout
- Avoid the density-creates-routing-impossibility trap

For v1: the brutally-honest answer is **accept the structural limit + ship clean v1 + design v2 properly**.

This is NOT a corner cut per Sai's directive. A corner cut would be SHIPPING with the 97-foul C1 v5 state or the unfinished U9 re-place. The honest answer is rolling back to the working state.

## 6. Recommendation — LOCKED 2026-05-28 21:55 UTC

**5 of 5 attempts walled (3 manual + 2 FR).** Structural impossibility confirmed within reasonable blast radius.

**Option (ε)+(t) RECOMMENDED:** Roll back U9 to (78, 57) F.Cu original position. Restore prior SPI3/IMU3_CS routing. Accept IMU3_INT1 v2-defer to pad-deferred whitelist (same pattern as C93.1 in PR #127). v1 ships with documented 2-INT + 1-polled triple-IMU. v2 redesigns for IMU-at-center from Phase 4a.

Worker recommends. Master agrees. Awaiting Sai's ratification (this IS a true Sai-gate: scope reduction on IMU3 INT-driven sampling).

## 7. Trade-off table for Sai

| | Roll back (ε)+(t) | Continue grind (η) |
|---|---|---|
| v1 IMU CG offset | 28mm (U3 IMU1 is the primary; still 5mm) | C1: 6.3mm OR C2: 3.5mm |
| Routing health | Clean (back to PR #105 baseline) | Hours-to-days of foul-cleanup; risk of latent SI defects |
| IMU3 INT | v2-deferred, polled-mode v1 functional | Routed in v1 |
| ArduPilot impact | Vote-disagree at lower rate on IMU3; primary EKF on IMU1 unaffected | Full triple-INT |
| Time to freeze-ready | ~2-3 hours (rollback + verify) | 8-10h (C1 η) or 2-3 days (C2 completion) |
| v2 work needed | IMU-at-center redesign from Phase 4a | Same — v2 still needs proper IMU placement |
| Fab risk | None — back to validated state | Latent SI defects from manual-iteration cleanup |

Master read: (ε)+(t) is brutally-honest no-corner-cut answer. Worker recommends. Master agrees pending Sai ratification.

---

## 8. Closure — (ε)+(t) EXECUTED 2026-05-29

Sai (delegated to master) ratified the recommendation. Worker executed:

**Phase 1 — Rollback** (`git checkout HEAD` on .pcb + .dru):
- U9 + C94 + C95 + C96 restored to original positions (U9 @(78, 57) F.Cu)
- SPI3_SCK / SPI3_MISO / SPI3_MOSI / IMU3_CS routing restored (52 segs + 8 vias total)
- +3V3_IMU rail tail (the 18 items deleted for the U9 move) restored
- DRC: 0 non-baseline violations
- waf copter: PASS (1515288 text, 184116 free flash)

**Phase 2 — IMU3_INT1 net-defer**:
- `IMU3_INT1` added to `INTENDED_DEFERRED` net set in `scripts/audit_unconnected_per_net.py`
- Same pattern as `MOT7`/`MOT8`/`USART1_*`/`SW*`/`EFUSE_FLT`/`EFUSE_PGOOD` (and the C93.1 pad-defer pattern in PR #127)
- Audit verdict: PASS — 0 real latent unconnected

**Phase 3 — Docs**:
- `docs/IMU3_INT1_V2_DEFER.md` (new) — net-defer rationale + ArduPilot polled-mode firmware reference + v2 plan
- This document — closure section added
- `STATUS.md` — Phase 4d-redux table updated to reflect IMU3_INT1 v2-defer

**Phase 4 — Verify gates all PASS**:
- audit_unconnected_per_net.py: real-latent = 0
- audit_layout_compliance.py: PASS
- DRC: 0 non-baseline
- waf copter: PASS
- No sim re-run needed — board geometry restored to PR #127 head; Sim 1 thermal (65.05 °C, +15 °C margin) and Sim 5 PDN (82.9 mΩ, ≤ 100 mΩ gate) remain valid as-of PR #126/127.

**v1 IMU summary post-closure**:
- IMU1 (ICM-42688-P, primary, SPI1) — INT-driven, chip ODR
- IMU2 (BMI088, secondary, SPI2) — INT-driven (ACC_INT1 + GYR_INT3), chip ODR
- IMU3 (LSM6DSV16X, tertiary, SPI3) — **polled @ ~1 kHz** (INT1 unrouted, v2-deferred)

ArduPilot drop-in compatibility preserved. Triple-IMU redundancy retained (2 INT + 1 polled).

PR opened on `hw/u9-replace-rollback-imu3int1-v2defer` branch — gate-clean, awaiting master pre-merge.
