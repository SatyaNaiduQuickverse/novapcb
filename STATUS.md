# novapcb v1.1 — live status

> Updated continuously by master Claude during autonomous-loop work.
> Most recent merged PR is at the top of the log.

**Current branch:** `sch/option-b-buck` &middot; **Head:** see latest entry below
**Board:** 105×85 mm, 6-layer, STM32H743VIT6, Pixhawk 6X functional drop-in
**Live HTML view:** http://100.81.21.121:8765/static/pcb.html

## Quick state

| Subsystem | State |
|---|---|
| Foundations (stackup, USB Z, thermal Option B, audit gates) | ✓ done |
| A power input + mirror | ✓ placed + routed |
| B 3V3 buck (TPS62177) | ✓ placed + routed |
| C MCU core (STM32H743 + halo + HSE) | ✓ placed + routed |
| D IMU island (3× ICM-42688-P + heater + 9 decaps) | ✓ placed + routed + +3V3_IMU rail |
| E barometers (DPS310 on I²C2) | ✓ placed + routed |
| F USB-C (J1 + ESD U5) | ✓ placed + routed |
| H ESC outputs (J11 10-pin JST-GH SM10B-GHS-TB) | ✓ placed; routing in flight |
| H↔C MOT* routing (8 + IMU3_INT1 + GND stitch) | 🟡 (α-revised): route MOT3-6 around U4 baro at Y=45.5 (corridor-clear infeasible — U4 sits IN corridor) |
| CAN bus (U14 + U15 + term + J20 NE-corner) | ✓ placed (PR #84 merged) — routing next |
| microSD (J2 east-band-south + SDMMC1 + length-match) | ✓ placed (PR #85 merged) — routing next |
| G-GPS (J5 SW corner + ESD + pulls + safety test pads) | ✓ placed (PR #86) |
| G-CRSF (J10 N-middle east + ESD + dividers + JST-GH 4P amend bundled) | ✓ placed (PR #90) |
| G-Telem UART (J3 E-mid + ESD) | ✓ placed (PR #90) |
| SWD header (J9 N-middle west) | ✓ placed (PR #90) |
| DRU rule cleanup (10 pre-existing DRC) | ⬜ pending |
| U6 decoupling fix | ⬜ pending |
| Full sim suite (thermal + EMC + vibration) | ⬜ pending |
| JLCPCB DFM compliance | ⬜ pending |
| Phase 7a freeze (Sai trigger) | ⬜ awaiting Sai |

## PR stack (most recent first)

### `sch/option-b-buck` head — currently `684e605` (14 PRs landed today 2026-05-24)

| # | Title | Type | Notes |
|---|---|---|---|
| #89 | docs: H↔C corridor-clear survey + per-net re-route plan | doc | Per-net plan for I²C2 south-detour + SPI1 small shifts to vacate Y=44..48 corridor |
| #88 | docs: remaining real-estate map (post-GPS) for CRSF/Telem/SWD | doc | TELEM (95,38), SWD (45,8) west of CRSF (54,8) in N-middle band |
| #90 | hw: CRSF + TELEM + SWD placement + J10 footprint sync to JST-GH | placement + schema bundle | N-middle band; CRSF placeholder→JST-GH 4P (mirrors PR #80 pattern) |
| #86 | hw: GPS+MAG+Buzzer placement (J5 SW corner) | placement | NW Rule-19 catch → re-zoned to SW (15,75); safety test pads + audit-fix (D5-9 are GPS ESDs not A TVS) |
| #85 | docs+hw: microSD subsystem placement (J2 east-band-south + 5 pulls + decap) | placement | DRC 21→20 favorable; SDMMC1 length-matching deferred to routing sub-step |
| #84 | docs+hw: CAN bus subsystem placement + U5 USB VBUS decap C85 fix | placement + schema bundle | NE-corner U14/U15/J20; C83 freed to its real CAN role per schema, new C85 added for U5 USB |
| #83 | sch+fw: pin remap (R-broad) — SKiDL + hwdef + board nets | schematic + firmware | MOT3-6 → south-edge TIM1; MOT7-8 → north-edge TIM4; IMU3_INT1 cascade PE11→PB2. Routing deferred to follow-up. |
| #81 | hw: H placement — J11 single 10-pin JST-GH at (52.5, 80, 0°) | placement | South-center, Pixhawk 6X harness compatible |
| #80 | sch: ESC connector → JST-GH 10-pin | schematic | SM10B-GHS-TB; matches Pixhawk family convention per DECISIONS §7 |
| #79 | docs: defer IMU slot to v2 (DECISIONS §2.1) | doc | Two layout-retrofit attempts failed; analysis preserved at `docs/v2/` |
| #78 | hw: +3V3_IMU rail routing (Topology a F.Cu trace network) | routing | 48 segs + 9 vias; 580×/7400× IMU noise margin preserved |
| #77 | hw: D↔C/B routing — 17 nets MCU↔IMU island (post-stackup-fix) | routing | SPI/INT/HEATER + SPI3 B.Cu wraparound |
| #76 | hw: stackup fix — In1.Cu + In4.Cu GND planes (Rule-9 catch) | hw | DECISIONS §8 was half-applied; USB Z_diff sim invalidated → fixed; 143 stitching vias |

## Discipline summary (master process rules at 19 now)

- **Rule 1-17**: original pcb.ai + novapcb canon
- **Rule 18** (added today): up-front fanout audits enumerate TRACKS **AND COMPONENT PADS** in the routing corridor — caught H↔C cap-field obstacle
- **Rule 19** (added today): up-front fanout audits also enumerate EXISTING ROUTED NETS — caught H↔C I²C2/SPI1 corridor blocker

## Current activity

Sai is offline ~10 hours starting 2026-05-24 ~03:00. Master + worker continue autonomously:
- Worker on H↔C MOT* routing (β Freerouting first → α corridor clear fallback → γ DRU exceptions last resort)
- Then chain through 6 G-subsystems autonomously (CAN → microSD → GPS → CRSF → Telem → SWD)
- Then cleanup (DRU rule scope + U6 decoupling) → full sim suite → JLCPCB DFM
- Phase 7a freeze docs ready for Sai's trigger when he returns

Each sub-step follows established pattern: up-front constraint analysis → master sign-off → worker execute → 5-gate verify → PR → master autonomous-merge if gate-clean.

## Activity log

| Time (UTC) | Event |
|---|---|
| 2026-05-24 05:08 | PRs #86 (GPS J5 SW) + #90 (CRSF/Telem/SWD + JST-GH amend) merged. 14 PRs landed today. All 7 connector subsystems now placed. H↔C escalation #4 caught U4 baro IS in corridor; pivoted to (α-revised) route-around U4. |
| 2026-05-24 04:55 | PRs #88 (real-estate map) + #89 (H↔C corridor-clear survey) merged. 12 PRs landed today. 9 decisions ratified across both. Dispatched 3 parallel exec streams: GPS rebase+placement, CRSF/Telem/SWD layout, H↔C corridor-clear+MOT routing. GPS PR #86 branch needs rebase (stale base discovered). |
| 2026-05-24 04:42 | H↔C Freerouting aborted at 36min (47GB swap, no pass-2 convergence). Pivoted to (α) corridor clear — survey doc + master sign-off → execute pattern. GPS J5 relocated SW (15,75) after NW Rule-19 catch. CRSF/Telem/SWD pending real-estate map sub-step before exec. 3 parallel work streams dispatched. |
| 2026-05-24 04:33 | PRs #85 (microSD) + #84 (CAN bus + C85 U5 decap fix) merged. Branch tip `684e605`. 10 PRs landed today. Worker chained to GPS + CRSF/Telem/SWD layouts. |
| 2026-05-24 03:40 | PRs #86 (GPS) + #87 (CRSF/Telem/SWD) up-front analyses approved; CRSF schematic amend (JST-GH 4P, mirrors PR #80 pattern) bundled per merge-autonomous memory — not separate Sai-gated PR. H↔C Freerouting given hard abort criterion (>20 unrouted at end of pass 2 → pivot to α corridor clear). |
| 2026-05-24 03:10 | PRs #84 (CAN) + #85 (microSD) up-front analyses approved; worker dispatched parallel execution; 4 more analyses (GPS/CRSF/Telem/SWD) queued for drafting |
| 2026-05-24 03:00 | Worker H↔C Freerouting started (PID 2846592, autonomous β-first strategy) |
| 2026-05-24 02:35 | STATUS.md created; autonomous-loop running; PR #83 merged |
| 2026-05-24 02:00 | PR #83 opened (pin remap, schematic + firmware change) |
| 2026-05-24 01:00 | PR #82 (audit DRAFT) → closed; carried into PR #83 |
| 2026-05-24 00:30 | PR #81 (H placement) merged |
| 2026-05-23 22:30 | PR #80 (ESC schematic 10-pin) merged |
| 2026-05-23 18:00 | PR #79 (slot v2-defer) merged |
| 2026-05-23 17:30 | PR #78 (+3V3_IMU rail) merged |
| 2026-05-23 17:00 | PR #77 (D-routing) merged |
| 2026-05-23 16:30 | PR #76 (stackup-fix) merged (Sai direct-merge) |
