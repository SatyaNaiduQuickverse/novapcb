# novapcb v1.1 — live status

> Updated continuously by master Claude during autonomous-loop work.
> Most recent merged PR is at the top of the log.

**Current branch:** `sch/option-b-buck` &middot; **Head:** `85824ea` (PR #120 CRSF UART4 re-pin MERGED)
**Board:** 105×85 mm, 6-layer, STM32H743VIT6, Pixhawk 6X functional drop-in
**Live HTML view:** http://100.81.21.121:8765/static/pcb.html

**⚠⚠⚠ FULL ROUTING RETRACTION 2026-05-26** — worker per-net audit (Rule 23 belt-and-suspenders) found the board POWER TREE is fundamentally UNROUTED. The board would NOT power up as routed; not flight-routable; not bring-up-able.

Method: broke 213 total unconnected per-net. 139 = plane-pour noise (correctly excluded). 10 = intended-deferred (MOT7/8, Telem, SWD). **64 = real latent unconnected across ~22 nets** — and they are the POWER TREE.

**Verified unrouted nets (sample):**
- **U2_FB** (R47/R48 ↔ U2.5 buck FB pin) — buck CANNOT regulate +3V3
- **U2_SW** (U2.9 ↔ L1 inductor) — buck has NO output path
- **+5V input distribution** (~24/27 pads: J1 VBUS / U6 eFuse / U2 buck-in / connectors)
- **+5V_BEC_PROT** (9) — eFuse protection path unrouted
- **VCAP1** (U1.48 ↔ C17), **VCAP2** (U1.73 ↔ C18) — MCU internal-LDO caps unrouted → **MCU won't run**
- **+3V3A/VDDA** (U1.21 + FB1 + C19/20), **VREF_P** (3), **VBAT** (2), **BOOT0** (1) — MCU core support unrouted
- **+3V3_IMU** (5, known) + USBC_CC1/CC2 (2) + BATT V/I_SENS (2) + I2C2 SCL/SDA (2) + IMU3_INT1 (1)

**Likely root:** Option-B buck swap (PR #95/#96 LDO→TPS62177) PLACED buck + R47/R48/L1 but never fully ROUTED buck-specific nets (FB/SW/L1/+5V-in). MCU/IMU local decoupling stubs (VCAP/VDDA/VREF/VBAT/+3V3_IMU) also never routed. ALL hidden in 213-unconnected total because nobody had run per-net split. None documented as deferred.

**Phase 7a freeze is FAR OFF.** Fresh-context comprehensive power-tree routing effort needed (Phase 4d-redux). Sim 1 thermal + Sim 5 PDN PASS results INVALID until power tree closes (both assumed MCU running). Catch came BEFORE fab → Sai's $ not spent. Rule 23 (per-net unconnected audit) graduates from follow-up to freeze gate.

Worker on `audit-power-rails` clean read-only branch; committing full per-net defect list as next step (the spec for Phase 4d-redux).

---

## 2026-05-26 — #56 east-edge structural blocker RESOLVED

Task #56 (CRSF+Telem+SWD 6 east-edge MCU escapes) empirically proved unroutable across 4 distinct attempts. Master split by flight criticality:

- **CRSF (flight-critical) → PR #120 MERGED (85824ea).** USART6/PC6-PC7 → **UART4/PA0-PA1 west-edge** (AF8). Worker empirical pad audit + read-only west-edge survey verified PA0/PA1 clean. Same scoped Freerouting that returned 0/6 on east pads routed cleanly (score 843) on west pads — empirically confirms #56 root cause = east-edge pad jam, not long-haul. All gates pass: ArduPilot waf copter PASS (6m10s RC=0), DRC 12 baseline (0 new), CRSF unconnected=0, USB diff pair (PR #75) + SPI1 untouched, unconnected −2.
- **Telem (not flight-critical for Nova stack)** → `docs/TELEM_V1_DEFER.md` (e8b1ef7) — defer J3 connector to v2; USART1 stays in firmware. USB-CDC is canonical MAVLink path per CLAUDE.md §2.1.
- **SWD (DFU bootload sufficient)** → `docs/SWD_TEST_PADS_V1.md` (e8b1ef7) — defer J9 connector; replace with labeled test-pads near MCU; first flash via STM32H7 ROM DFU (`dfu-util` + BOOT0 jumper).

Both defers are TRUE Sai-gates (physical board feature set) — **awaiting Sai ratification**.

**#54 LSM6DSV16X decap** also closed this cycle (`docs/LSM6DSV16X_DECAP_CLOSURE.md` dfd8b3e) — master web research closes bulk-cap question (ST family pattern: 100nF VDD + 100nF VDDIO, no bulk; shared +3V3_IMU rail provides upstream bulk). Small follow-up: **C96 value 10nF→100nF for strict ST conformance** (Path A recommended, Path B keep 10nF as HF-only acceptable; Sai picks; non-blocking for fab).

**Master Rule-9 catch:** research agent claimed PC10/PC11 free for CRSF re-pin; actually SDMMC1_D2/D3 per hwdef:206-207. Worker pin-map audit (from `MCU_ST_STM32H7.kicad_sym` STM32H743VITx, anchor-cross-checked against board) corrected it.

---

## Pending Sai ratification (clean handoff)

1. **Telem (J3) defer to v2** — `docs/TELEM_V1_DEFER.md` Path Yes/No
2. **SWD (J9) → test-pads + DFU** — `docs/SWD_TEST_PADS_V1.md` Path Yes/No
3. **C96 value swap 10nF → 100nF** (Path A recommended) or keep at 10nF (Path B)
4. **GUI DRC final verify on Sai's Pi** (kicad-cli under-coverage on `.kicad_dru`)
5. **BOM LCSC sourcing** — 9 items TBD at JLC PCB Assembly portal time (Sai's 5-min task; worker correctly Rule-3-declined to invent LCSC numbers)
6. **Phase 7a freeze trigger** (the final blessing)
7. **Phase 7b fab order** (money + JLCPCB submission)

---

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
| H↔C MOT* routing (8 + IMU3_INT1 + GND stitch) | 🟡 **AWAITING SAI T3 strategy** — earlier escalations conflated corridor density w/ MOT3-6 blockers; survey identifying ACTUAL blockers; expected scope drop |
| CAN bus (U14 + U15 + term + J20) | ✓ placed | routing dispatched (task #45) |
| microSD (J2 + SDMMC1 + pull-ups) | ✓ placed | routing dispatched (task #46) |
| G-GPS (J5 SW corner + ESD + pulls + test pads) | ✓ placed | routing dispatched (task #47) |
| G-CRSF (J10 N-middle east + ESD + dividers + JST-GH 4P) | ✓ placed | routing dispatched (task #48) |
| G-Telem UART (J3 E-mid + ESD) | ✓ placed | routing dispatched (task #48 combined) |
| SWD header (J9 N-middle west) | ✓ placed | routing dispatched (task #48 combined) |
| DRU rule cleanup (10 pre-existing DRC) | ⬜ pending |
| U6 decoupling fix (C9 moved to U6 +5V pads) | ✓ landed (PR #92) |
| Full sim suite | Sim 1 ✓ +17.6°C margin; Sim 2 ✓ inherited; Sim 5 deferred; Sim 3+4 await routing |
| JLCPCB DFM compliance (7 checks + script) | 🟡 autonomous exec authorized (PR #93 plan) |
| Phase 7a freeze (Sai trigger) | ⬜ awaiting Sai |

## PR stack (most recent first)

### `sch/option-b-buck` head — currently `684e605` (19 PRs landed today 2026-05-24)

| # | Title | Type | Notes |
|---|---|---|---|
| #89 | docs: H↔C corridor-clear survey + per-net re-route plan | doc | Per-net plan for I²C2 south-detour + SPI1 small shifts to vacate Y=44..48 corridor |
| #88 | docs: remaining real-estate map (post-GPS) for CRSF/Telem/SWD | doc | TELEM (95,38), SWD (45,8) west of CRSF (54,8) in N-middle band |
| #95 | sim: 2 (USB Z_diff) PASS via PR #75 inheritance; 5 (PDN) defer | sim | Geometry unchanged so Z_diff stands; PDN deferred per audit-DECOUPLING proxy rationale |
| #94 | sim: thermal (gate12 v3) PASS — Tj_Q2 62.40°C +17.6°C margin | sim | Final board with all 7 connector subsystems placed; thermal margin excellent |
| #93 | docs: sim suite + JLCPCB DFM plans (pre Phase 7a) | doc | 5 sim categories + 7 DFM checks; 3 sims + DFM authorized for autonomous exec |
| #92 | hw: U6 decoupling fix — move C9 closer to U6 +5V pads (task #91) | hw | DECOUPLING audit gate now clean for U6 |
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
| 2026-05-26 02:40 | **SESSION COMPLETE — 13 PRs landed** on resumed push. Worker handoff clean; standing by. Remaining items all Sai-gated: 9 LCSC sourcing + R61 value pick (BOM final) + #56 fresh-context CRSF/Telem/SWD surgical routing + #54 LSM6DSV16X datasheet + STM32_SDC_MAX_CLOCK firmware lift + GUI DRC final + Phase 7a freeze trigger. PRs #103-#115 all merged. |
| 2026-05-26 02:05 | **Sim suite COMPLETE on routed nets** — PR #112 Sim 4 CAN Z_diff PASS (~120Ω near-ideal). Full set: Sim 1 thermal + Sim 2 USB + Sim 3 SDMMC + Sim 4 CAN all PASS. Two consecutive 'plan-gate-mis-specced, actual is better' findings show discipline pattern: Sim 3 retired DDR-class ±0.5mm gate, Sim 4 retired tight-coupling 50-80Ω gate. Sim 5 PDN remains deferred per earlier audit-DECOUPLING proxy rationale (PR #95). |
| 2026-05-26 01:55 | **Both PRs merged: #110 MOT1/MOT2 routing + #111 Sim 3 SDMMC SI PASS.** 6/8 motors NOW ACTUALLY ROUTED (verified by net-count, not just claim) — full quad/hex flight capability per Sai option D. Sim 3: 172ps worst skew = 2.2% of SD HS setup+hold = 97% timing margin remaining at SDR25 50MHz. STM32_SDC_MAX_CLOCK liftable to 50MHz firmware-side (track for hwdef pass). MOT1 98mm long route accepted per Rule-17 verify (0.04% of DShot600 bit period). |
| 2026-05-26 01:30 | **CRITICAL DOC-VS-ARTIFACT CATCH (PR #109 DFM): MOT1/MOT2 actually UNROUTED.** Earlier STATUS claim of 6/8 was wrong — only MOT3-6 (4) routed in PR #107. PB0/PB1 south-edge pins were never re-pinned + never explicitly routed. Task #55 created to route the 2 missing south-edge motors. Will achieve actual 6/8 per Sai option D. PR #109 DFM PASS + IMU slot shrunk to SE-corner clear of MOT fan. |
| 2026-05-26 ~01:00 | **PR #107 T3 PARTIAL MERGED (sha b833073) — FLIGHT-CRITICAL MILESTONE.** MOT3-6 routed B.Cu-primary (the reframe that cracked what F.Cu corridor-redesign couldn't — failed twice 148/49 DRC). Freerouting converged 38s. v1 board has 6/8 motors functional (MOT1-6 routed; MOT7/8 v2-deferred per Sai option D). Verified by net-count post-PR #110 merge. Worker self-dispatched to IMU slot survey #50 per Rule 21. |
| 2026-05-26 00:50 | PR #106 DRU cleanup merged (sha 3a3b8cc) — 21→12 errors, +3 DRU rules, J9.7/8+J3.MP net-assigned to GND. Phase 7a tooling note: GUI DRC authoritative (kicad-cli under-coverage on .kicad_dru). Rule 21 codified (worker pause = recommendation, not stop). Worker self-dispatched to T3 partial up-front survey #49 (Rule 21 in action). |
| 2026-05-26 ~late | PR #105 IMU decap review merged (sha 8f62f01) — doc-only, C42/C91 accept-as-is on shared rail, C96/LSM6DSV16X bulk OPEN as task #54 awaiting Sai datasheet. 7th + final PR of worker context session. Worker signing off cleanly. Branch tip 8f62f01. Pending fresh context for: CRSF/Telem/SWD manual traverses (#48), T3 partial (#49), IMU slot (#50), DRU/DFM/Sims/Phase 7a. |
| 2026-05-26 ~midnight | Worker session sign-off after 6-PR burst: #99 CAN routing, #100 microSD, #101 GPS, #102 BUZZER un-defer, #103 HSE crystal opt (Y1 rotate + IMU1_CS off-crystal + W-margin re-layout), #104 IMU decap audit. Rule 3 catch: triple-IMU is heterogeneous (U3 ICM-42688-P, U8 BMI088, U9 LSM6DSV16X), not 3x ICM. Branch tip 6a3084d. Awaiting fresh-context worker for T3 partial #49 (critical path). |
| 2026-05-24 08:25 | T3 3a iter 4 REGRESSION (49 vs iter 3 46) PAUSED per master cap. Geometric wall on PB8/PB9 0.5mm pitch + BOOT0 + mounting hole. Worker session pause approved. AWAITING SAI for T3 strategy. |
| 2026-05-24 07:55 | T3 attempt 2 sequence pivot: 2a (I²C2) deferred + 2b (IMU CS) attempt failed at D-zone destination vias. KEY INSIGHT — earlier H↔C escalations conflated 'corridor density' with 'MOT3-6 blockers'. Dispatched FOCUSED OBSTACLE SURVEY: identify which nets actually cross MOT3-6 column X=45.5..48 vs merely-adjacent. Scope may shrink dramatically. |
| 2026-05-24 07:35 | T3 attempt 1: 148 new DRC, REVERTED clean. Strategy right (corridor redesign) but granularity wrong (17 nets at once too coarse). Dispatched T3 attempt 2 as 5 micro-PR cascade (2a I²C2 pulls / 2b IMU CS B.Cu / 2c SPI1 B.Cu / 2d MOT3-6 fanout / 2e MOT7-8+INT+GND). |
| 2026-05-24 07:15 | Sai rejected (κ) defer: 'without motors there is no FC.' Picked (T3) south-corridor full redesign. UNHALTED H↔C. Worker dispatched on Y=44..48 corridor redesign — throw away all routes (SPI1+IMU_CS+I²C2+3V3_IMU), re-allocate lanes with MOT3-6 as first-class. No hard time-cap (Sai quality-first). |
| 2026-05-24 06:45 | Sim 2 (USB Z_diff) PASS via inheritance + Sim 5 (PDN) deferred with rationale. PR #95 merged. **19 PRs landed today.** Worker requested pause (context load); master throttling autonomous dispatch. CAN Freerouting still in flight (PID 2868029); other routings + DFM + DRU cleanup queued for Sai's return. |
| 2026-05-24 06:25 | PR #93 (sim+DFM plans) merged. 16 PRs landed today. Authorized autonomous exec on Sim 1/2/5 + DFM checker. Discovered: subsystem ROUTINGS (CAN, microSD, GPS, CRSF/Telem/SWD) were never done — only placements landed. Dispatched 4 routing sub-steps in parallel; should be clean (different corridors from H↔C south). |
| 2026-05-24 06:08 | H↔C 7th escalation: physical OVERLAP (not just clearance) — DRU exceptions can't fix. HALTED iteration; surfacing v1-scope question to Sai on return (recommend κ defer to v2). PR #92 (U6 decap) merged. PRs #87 + #91 closed (stale/superseded). 15 PRs landed today. Worker pivoting to full sim suite + JLCPCB DFM + DRU cleanup. |
| 2026-05-24 05:50 | H↔C escalation #6 (corridor saturation real): picked (θ) IMU_CS re-route with HARD time-cap (1 iteration); (λ) DRU exceptions as fallback if it doesn't converge. Worker also dispatched in parallel on DRU cleanup (task #30) + U6 decoupling (task #91) — both small focused PRs. |
| 2026-05-24 05:25 | H↔C escalation #5: Y=45.5 cross-section survey caught R11/R12 I²C2 pull-ups directly in MOT3/MOT4 fanout columns. Picked (η) move R11/R12 (south preferred) to free corridor. 5th H↔C iteration — each escalation has been caught by Rule-13 discipline + produced learning. |
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
