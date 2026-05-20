# Phase 2 re-audit (Phase 2-exit)

Re-audit gate before Phase 3 builds on top. Generated 2026-05-20 by Phase 2-exit per master dispatch + 01:00 retro cross-review action item.

Source main HEAD: `ea4ed98` (Phase 2h merged).
Audit branch: `fw/hwdef-phase2-exit-2026-05-20`.

---

## Part A — re-audit (gate-quality verification)

### A1 — cold-clean rebuild sha reproduce ✓

Procedure:
```
cd ~/ardupilot
rm -rf build/novapcb-v1
CCACHE_DISABLE=1 ./waf configure --board=novapcb-v1
CCACHE_DISABLE=1 ./waf copter
```

Result:
- Wall-clock: **5 min 18.228 s** (vs warm-ccache build at 3m27s — 1.5× longer confirms ccache was NOT assisting).
- BUILD SUMMARY: text `1,518,576` / data `4,528` / bss `136,676` / total `1,523,104` / free `180,828`.
- sha256: `9ddb37d420c166ab7b425cf6aa0fd7cdaf234dc250ecd31adf2a9419c06b1db7`.
- **MATCHES** the recorded Phase 2g + Phase 2h hash exactly.

The Phase 2 binary chain is byte-for-byte reproducible from a cold-clean checkout of main + no-ccache build. **A1 PASS.**

### A2 — per-phase flash arithmetic chain ✓

| Phase | Total used (B) | Δ from prior | Recorded BUILD_BASELINE Δ | Match |
|---|---:|---:|---:|:---:|
| 1 | 1,545,872 | — | — | — |
| 2a | 1,534,644 | −11,228 | "−11,224 B" | ✓ (±4 B alignment) |
| 2b | 1,534,572 | −72 | "−72 B" | ✓ |
| 2c | 1,519,948 | −14,624 | "−14,624 B" | ✓ |
| 2d | 1,519,948 | 0 | bit-identical | ✓ |
| 2e | 1,521,688 | +1,740 | "+1,740 B" | ✓ |
| 2f | 1,523,100 | +1,412 | "+1,412 B" | ✓ |
| 2g | 1,523,104 | +4 | "+4 B" | ✓ |
| 2h | 1,523,104 | 0 | bit-identical | ✓ |

Cumulative Phase 1 → Phase 2h: −22,768 B used / +22,768 B free. Top BUILD_BASELINE.md summary table (`firmware/hwdef-novapcb/BUILD_BASELINE.md:6-15`) matches each row.

Notes:
- Phase 2a "−11,228 B" computed vs Phase 1 "1,545,872 − 1,534,644 = 11,228", while BUILD_BASELINE Phase 2a section text records "−11,224 B". Discrepancy = 4 B = a build alignment artifact (image_maxsize jitters between 1,703,928 and 1,703,932 across phases — observed in the top table's free-flash numbers). Not a real regression; mentioning here for completeness.

**A2 PASS.**

### A3 — board_id 5350 preservation ✓

- `firmware/hwdef-novapcb/hwdef.dat:8` → `APJ_BOARD_ID 5350`
- `firmware/hwdef-novapcb/hwdef-bl.dat:8` → `APJ_BOARD_ID 5350`

Build verification: `python3 -c "import json; print(json.load(open('build/novapcb-v1/bin/arducopter.apj'))['board_id'])"` → `5350`.

Preserved across all Phase 2 commits per the BUILD_BASELINE.md Phase 1 → Phase 2h "board_id 5350 ✓" notes. **A3 PASS.**

### A4 — CONFIDENCE_MAP rows 1-10 spot-check ✓

Rows touched by Phase 2 (per cited line numbers + content):

| Row | Subsystem | Phase(s) | Confidence trajectory | Cited refs resolve on main? |
|---|---|---|---|:---:|
| 1 | MCU + clock + reset + decoupling | none (Phase 3.5 territory) | HIGH (~98%) baseline | n/a |
| 2 | USB-CDC interface | 2h | HIGH (~97%) → HIGH (~98%) | ✓ (hwdef.dat:12-13 + hwdef.h cite valid) |
| 3 | 5V → 3.3V LDO + decoupling | none (Phase 3.5) | HIGH (~95%) baseline | n/a |
| 4 | IMU SPI bus (ICM-42688-P) | 2a | HIGH (~92%) baseline | ✓ (hwdef.dat:238 IMU Invensensev3 SPI:icm42688) |
| 5 | Barometer I²C (DPS310) | 2b | MEDIUM-HIGH (~88→90%) | ✓ (hwdef.dat:246 BARO DPS310 I2C:0:0x76) |
| 6 | External mag + GPS I²C/UART | 2c+2d | HIGH (~93→95→96%) | ✓ (hwdef.dat:230-231 COMPASS lines) |
| 7 | microSD via SDMMC (SDR25 target) | 2h | MEDIUM (~80%) → MEDIUM-HIGH (~87%) | ✓ (hwdef.dat:187-192 SDMMC1 lines) |
| 8 | 8-channel ESC outputs (DShot300/600) | 2e (amended) | MEDIUM (~75→88%) | ✓ (hwdef.dat motor block + DMA_NOSHARE line) |
| 9 | CRSF UART for ELRS | 2f | MEDIUM (~75→85%) | ✓ (USART6 PC7/PC6 inherited + defaults.parm) |
| 10 | VBAT divider + current sense ADC | 2g | MEDIUM (~80%) → MEDIUM-HIGH (~88%) | ✓ (hwdef.dat:73-80 BATT block + Mauch SCALEs) |

Monotonicity check: no row regressed; all bumps are evidence-backed (Phase 2 sub-phase locks + grep'd citations). Rows 11-14 unchanged in Phase 2 (LOW/MEDIUM, Phase 3.5/6 territory).

**A4 PASS.**

### A5 — 4 master Rule-3 slip corrections ✓ (with one historical-residual footnote)

Per 00:00 + 01:00 retro action items:

| # | Slip | Status on main | Evidence |
|---|---|:---:|---|
| (a) | "MatekH743+Pixhawk6X consensus on DPS310" | ✓ corrected | `BUILD_BASELINE.md:199` explicitly documents the catch + correction; live docs (CONFIDENCE_MAP row 5, hwdef.dat:243 comment) use CLAUDE.md §3.5 single-reference framing. |
| (b) | "DECISIONS.md sensor selection" | ✓ corrected in live docs (one historical residual) | Live docs use CLAUDE.md §3.5 framing (CONFIDENCE_MAP row 5; hwdef.dat:243). Historical residual at `tasks/phase-2b-baro.yaml:20` `inputs.refs` list — NOT a load-bearing claim (briefing context, frozen as authorization record). `tasks/phase-2c-mag-external.yaml:35` already tracks the corrected language migration. |
| (c) | Phase 2c compass broad-probe | ✓ corrected | `hwdef.dat:224` comment "Dropped AP_COMPASS_PROBING_ENABLED" + explicit `COMPASS IST8310 …` + `COMPASS RM3100 …` lines 230-231. `BUILD_BASELINE.md:265 + 299 + 312` confirm. |
| (d) | Phase 2e BIDIR matrix PB0/PA0/PA2/PD12 | ✓ corrected | `INTERFACE_CONTRACT.md:64` + `hwdef.dat:158` comment + `CONFIDENCE_MAP.md:25` + `BUILD_BASELINE.md:23` all cite `PB0/PA0/PA2/PD12` consistently. |

**Known-residual note (b):** `tasks/phase-2b-baro.yaml:20` retains `"DECISIONS.md §5 sensor selection (DPS310 preferred per noise floor)"` in its `inputs.refs` briefing list. DECISIONS §5 is actually "Voltage / current monitoring," not sensor selection. This is a frozen historical contract — briefing context at dispatch time, not a load-bearing claim. **Per master 2026-05-20 adjudication: DO NOT backfill-edit historical task contracts** — editing them rewrites the record of what was actually authorized at the time. The deliverable docs are corrected (CONFIDENCE_MAP row 5 + `hwdef.dat:243` use CLAUDE.md §3.5 noise-floor framing); the historical contract retains its pre-correction citation, documented here so the residual is honestly acknowledged without record-falsification.

**A5 PASS** (4/4 corrected in deliverable docs; one historical-residual noted per master directive).

### A6 — Part A summary

A1, A2, A3, A4, A5 all PASS. The Phase 2 binary + documentation chain is sound. Phase 3 may build on top.

---

## Part B — Matek-specific inventory + classification

### Inventory

Items in current `firmware/hwdef-novapcb/hwdef.dat` that are Matek-specific (i.e. exist because MatekH743 has the on-board hardware) and may or may not apply to novapcb:

| # | Item | hwdef.dat lines | What it is | What Matek hardware it serves | DECISIONS/CLAUDE commit | Classification |
|---|---|---|---|---|---|---|
| 1 | BATT2 scaffolding | 70-71 (PA4/PA7 ADC pins) + 76-77 (HAL_BATT2_*_PIN) + 80 (HAL_BATT2_VOLT_SCALE) | Secondary battery monitor ADC channels + defines | Matek's onboard 2nd-battery analog inputs | DECISIONS §5 explicit single-Mauch | **REMOVE** |
| 2 | PA15 BUZZER + HAL_BUZZER_PIN | 183-184 | GPIO single-tone buzzer driver | Matek's onboard buzzer | None explicit; master B5 directive lean KEEP | **KEEP** (Phase 3 schematic decides population) |
| 3 | PINIO1/PINIO2 (PD10/PD11) | 195-196 | General-purpose GPIO outputs exposed as ArduPilot RELAY_PINs | Matek "user GPIO" pads | None explicit | **KEEP** (harmless; useful future opt) |
| 4 | HAL_DEFAULT_AIRSPEED_PIN 4 + PC4 PRESSURE_SENS | 99 + (PC4 in ADC block) | Airspeed sensor ADC channel + default pin | Matek's analog airspeed input | None explicit | **KEEP** (harmless; multirotor doesn't use, but driver only loads if user enables) |
| 5 | PC5 RSSI_ADC + BOARD_RSSI_ANA_PIN 8 | 101-102 | Analog RSSI ADC channel | Matek's analog RSSI input | None explicit; ELRS uses CRSF digital telemetry, not analog RSSI | **KEEP** (harmless; analog RSSI fallback) |
| 6 | CAN1 (PD0/PD1 CAN1_RX/TX) | 151-152 | CAN1 bus pins for DroneCAN/UAVCAN | Matek's CAN connector | DECISIONS silent on CAN/DroneCAN | **KEEP** (Phase 3 schematic decides CAN connector population) |
| 7 | MAX7456 OSD chip + SPI2 + driver + ROMFS fonts | 41-44 (SPI2 + PB12 CS) + 208 (SPIDEV osd) + 251-253 (OSD_ENABLED + ROMFS_WILDCARD) | Analog video on-screen-display chip + ArduPilot OSD library + font assets | Matek's onboard analog video OSD chip | CLAUDE.md §2.3 "FC never sees video" (interpretable) | **🛑 Rule-13 stop — judgement call REMOVE vs DEFER** |

### Classification reasoning per master's "don't lose what surely works" calibration

- **Item 1 (BATT2)**: Clean REMOVE per master B4 directive. DECISIONS §5 line 53 "match what the airframe already has — external Mauch" is explicit + singular (one Mauch module, not two). novapcb v1 has no dual-battery commitment in DECISIONS or CLAUDE; v2 mechanical might bring it (FMUv6X has dual-battery support) but that's deferred (OPEN_QUESTIONS v2-1). Strip the 4 BATT2 lines + 1 inherited SCALE define. Strip is safe: ADC pin lines + HAL_BATT2_*_PIN are #ifdef-guarded in AP_BattMonitor_Analog.cpp (line 119-130); their absence makes BATT_MONITOR2 the standard ArduPilot default (0, no monitoring). HAL_BATT2_VOLT_SCALE is optional (line 125 #ifdef HAL_BATT2_VOLT_SCALE). Compile passes; runtime behavior unchanged from "BATT2 = 0 default" current state (which was already the runtime state — the scaffolding was inert).
- **Items 2-6**: KEEP/DEFER per the conservative bar. None have explicit DECISIONS/CLAUDE rejection AND keeping them costs zero runtime risk (drivers only load if user enables corresponding params or wires actual hardware). Following master's asymmetry: "an unused driver costs a few KB of flash and zero runtime risk; removing something we later want costs a re-spin."
- **Item 7 (MAX7456)**: Rule-13 escalated to master 2026-05-20 (R1 REMOVE / D1 DEFER / K1 KEEP options). **Master adjudication: D1 DEFER, with sharpened OPEN_QUESTIONS entry.** Reasoning per master 2026-05-20: "novapcb is a CubeOrange+/Pixhawk-class autopilot replacement (CLAUDE.md §0/§1). Pixhawk-class autopilots do NOT have onboard analog video OSD — the MAX7456 is Matek-FPV-flight-controller DNA (Matek makes mini analog-FPV FCs; that's why MatekH743 has it). Nova drone video is fully digital (Pi Camera + Hailo NPU, §2.1); §2.3 says the FC never sees video. A MAX7456 on novapcb would have no analog signal to overlay and nowhere to send it. RECOMMENDATION: omit at Phase 3 schematic." Strip belongs WITH Phase 3 schematic work (firmware + schematic moving together), not ahead of it. See `docs/OPEN_QUESTIONS.md` entry `phase2exit-1`.

### Strip-applied this PR

- **BATT2 scaffolding** (Item 1): 5 lines removed from `hwdef.dat` (2 inherited BATT2_*_SENS ADC pin lines at PA4/PA7 + 2 inherited HAL_BATT2_*_PIN defines + 1 inherited HAL_BATT2_VOLT_SCALE define). Build sha changes from `9ddb37d4…` to a new hash — expected, not a regression. Captured in BUILD_BASELINE.md Phase 2-exit section.

### Deferred to Phase 3 (master-directed via OPEN_QUESTIONS)

- **MAX7456 OSD** (Item 7): `docs/OPEN_QUESTIONS.md` `phase2exit-1`. Hwdef lines stay until Phase 3 schematic confirms "no MAX7456" (master near-certain recommendation: omit), at which point a follow-up PR strips the 5 hwdef lines (PB12 CS, SPIDEV osd, OSD_ENABLED, HAL_OSD_TYPE_DEFAULT, ROMFS_WILDCARD fonts) for ~10-30 KB flash recovery.

---

## 02:00 UTC Retrospective (folded into Part C per master dispatch)

Per master's dispatch + the 01:00 retro cross-review "watch retro-becomes-ceremony" action: the 02:00 retro folds into this Phase 2-exit PR as a section of PHASE2_AUDIT.md rather than its own ceremony PR. The substance (master + worker sections + cross-reviews) stays; the ritual drops.

### → Master section (verbatim from master 2026-05-20 dispatch)

#### What I did (02:00-03:00 UTC window)

- Audited + merged PR #19 (Phase 2g Mauch power, option C5 — researched HS-200-LV values)
- Audited + merged PR #20 (Phase 2h USB+SDMMC, pure-verify, bit-identical sha256)
- Adjudicated the Phase 2g compile-failure escalation: rejected C1-C4, directed C5 (research Mauch 200A values) — checked DECISIONS §5 first, which pinned the answer
- Dispatched Phase 2h with the new "decision forks to watch" format; it worked (zero escalations on 4 forks)
- Dispatched Phase 2-exit (this contract)

#### Rule adherence

- Rule 6 ✓ — caught PR #18's mergeable=false + diff-discrepancy before merge (the rebase episode); every merge enumerated verified/not-verified
- Rule 13 ✓ — Phase 2g compile-fail adjudication checked DECISIONS §5 before deciding, didn't improvise
- Rigor §10 — ZERO new master Rule-3 slips this hour (the "no specifics from memory in contracts" reflex held; 2g/2h contracts were generic-only). First clean hour.
- Calibration ✓ — C5 (research correct values) over C1 (inherit wrong) over C3/C4 (scream-loud-broken); reframed Phase 2-exit cruft strip toward conservative per "don't lose what works"

#### Patterns spotted

- The "decision forks to watch" contract section measurably reduced Rule-13-stop overhead (Phase 2h: 4 forks, 0 escalations vs 2c/2e/2f/2g: 1 escalation each). Pre-framing the decision CLASS works.
- The PR #18 rebase episode: branch created off pre-squash-merge main. Worker fixed via rebase, self-flagged the two-dot/three-dot diff slip. Real catch.
- Velocity vs audit-depth tension is real — hence this Phase 2-exit re-audit.

#### Process changes to consider

- "decision forks to watch" is now standard contract format — promote to a documented template element when the engineering-rigor docs next get amended (supermaster sign-off needed).
- Phase 2-exit re-audit should become a standing pattern: a re-audit sub-phase at the end of every multi-sub-phase Phase (so Phase 3 schematic gets one too).

### → Worker section (02:00-03:00 UTC window)

#### What I did

- Implemented Phase 2g option C5 after Rule-13 stop on master's option B (build failure: ArduPilot `#error`-enforces SCALE-with-PIN). Researched Mauch HS-200-LV typical calibration values from 3 sources (Mauch product pages + ArduPilot wiki); shipped `HAL_BATT_VOLT_SCALE 9.0` + `HAL_BATT_CURR_SCALE 60.6` with multi-line lock comment + DECISIONS/CLAUDE citations. Build clean; PR #19 merged.
- Implemented Phase 2h as pure-verify sub-phase (zero hwdef change). USB strings already correct from Phase 1; SDMMC1 inherited cleanly from MatekH743. Build bit-identical to Phase 2g (same sha). 4 decision-forks-watched resolved without escalation. PR #20 merged.
- Started Phase 2-exit: cold-clean rebuild reproduce passed, full Part A audit drafted, Part B inventory + classifications drafted, MAX7456 Rule-13 escalated to master.
- Saved feedback memory `feedback_rule13_grep_decisions_first.md` after Phase 2g — "in Rule-13 stops, grep DECISIONS first before drafting option-set." Master cited this exact pattern in their 02:00 retro section ("checked DECISIONS §5 first, which pinned the answer"). Applied prophylactically in Phase 2h prep + Phase 2-exit Part B classifications.

#### Rule adherence

- Rule 3 ✓ — every Phase 2g/2h/2-exit claim grep-then-state; no values pattern-matched from training data. Mauch values came from sourced datasheet research (Rule 3 + master's "research datasheets in detail" directive); SDMMC clock cap came from in-tree mcuconf.h grep; USB VID/PID came from generated hwdef.h.
- Rule 13 ✓ — three Rule-13 stops this hour, all clean: (a) Phase 2g option B compile failure → escalated → master picked C5; (b) Phase 2h had 0 stops (forks-watched contract format absorbed them all); (c) Phase 2-exit Part B MAX7456 OSD judgement call → escalated per criterion B6.
- Rule 6 ✓ — every PR body had SOTA self-audit + verified vs paper-only enumeration. PR #20 explicitly noted "bit-identical sha as strongest possible confirmation" rather than just claiming "build works."
- Rule 7 scope per `feedback_rule7_scope.md` ✓ — no blast-radius recital on routine pushes/PR opens; reserved for the one git config local-set (per-repo identity to match history, not --global).
- Calibration ✓ — applied "decision-aligned surely-working > strict inheritance" in Phase 2g (researched Mauch values, not Matek inheritance) + conservative "don't lose what works" in Phase 2-exit Part B (KEEP/DEFER bias, REMOVE only on master directives).

#### Patterns spotted

- Master's "decision forks to watch" contract format genuinely changed worker behavior: Phase 2h ran without escalations precisely because the fork CLASSES were pre-stated. Worker pre-classified each fork during execution + only stopped when something diverged from the pre-stated class. Reduces wasted Rule-13 cycles.
- The cold-clean-rebuild reproduce check (Phase 2-exit A1) is genuinely high-signal — 5m18s wallclock confirmed no ccache assist + sha matched bit-identically. Single strongest "Phase 2 is sound" signal possible.
- The Phase 2g option B → C5 sequence proved master+worker brutal-honesty mode works in both directions: worker drafted C1-C4 (all wrong by master's read), master picked C5 (different option entirely), but worker's honest C4-flaw-flagging is what let master see C4 was wrong. Both sides over-shooting honesty is the safety mechanism.

#### Process changes to consider

- The `tasks/*.yaml` `decision_forks_watched` block should be a documented template element (matches master's "consider promoting to template" thought). Should also include `escalation_log:` field for Rule-13-stops logged inline rather than scattered across pings.
- For audit sub-phases (like Phase 2-exit Part A), the cold-clean-rebuild + sha-reproduce check should be the FIRST criterion. If A1 fails, nothing else matters.

### Cross-reviews

**Worker → Master (2-3 lines):** Master's "decision forks to watch" format was the cleanest contract improvement so far this session — Phase 2h ran without a single Rule-13-stop because forks were pre-classified. Reframing Phase 2-exit Part B from "strip aggressively" to "inventory + conservative classification with judgement-calls escalated" is the right call; matches the "don't lose anything that surely works" calibration and avoids a Phase 3 re-spin. One ask: when Phase 2-exit retro becomes the standing-pattern end-of-Phase audit, codify the cold-clean-rebuild as criterion A1 explicitly (it was the master's first Phase 2-exit criterion and IS the strongest signal). Master section to be inserted by master via `/send`.

**Master → Worker (cross-review):**

Worker's Phase 2g-2h-2exit execution was the strongest stretch of the session — three clean Rule-13 stops, every value grep-or-research-sourced, the cold-clean-rebuild check executed exactly as specified. Accepting the "codify cold-clean-rebuild as criterion A1" ask: yes, when the end-of-Phase re-audit becomes a standing pattern, the cold-clean ccache-disabled rebuild + sha-reproduce is criterion A1 by definition — if A1 fails nothing else matters. Also accepting the `escalation_log:` task-YAML field idea — lightweight, keeps Rule-13 history in the contract instead of scattered across pings.

Three precision pushbacks for the record — none are faults, they're guards against false confidence:

1. **"Zero silent regressions" is a build-integrity claim, not a design-validation claim.** The Part A re-audit proved the Phase 2 binary is bit-reproducible and the documented flash/sha/board_id numbers are internally consistent. It did NOT prove the board will work. The BIDIR matrix being electrically correct, the Mauch scale values being right, the CRSF pin being genuinely 5V-tolerant, the DShot DMA having no real contention — all of that is still UNVALIDATED until Phase 6 sims + Phase 9 bench. "Phase 2-exit re-audit PASSED" must not read as "Phase 2 design is validated." It reads as "Phase 2 is a sound, reproducible foundation to build Phase 3 on." Keep that distinction sharp in how PHASE2_AUDIT.md is cited later.

2. **"BATT2 stripped" = defaults removed, capability retained.** The −136 B delta is honest precisely because the BATT2 monitor backend stays linked — what Phase 2-exit removed is the compile-time DEFAULT pin assignments + scale defines, not the BATT2 capability. PA4/PA7 are now undeclared-and-free for Phase 3 to reassign or leave. State it that precisely in any future reference — "BATT2 scaffolding defaults removed", not "BATT2 removed".

3. **The Mauch HS-200-LV values (9.0 / 60.6) are the least-verified numbers in the entire Phase 2 hwdef.** Every other Phase 2 value came from reference-design inheritance or in-tree grep — verifiable against files on disk. The Mauch values came from web research of typical/nominal figures. That's not a criticism — it was the right method per the calibration, and you sourced + cited it well. But it means those two numbers carry the most uncertainty. Flag them as PRIORITY items for Phase 6.5 forum review AND Phase 9 bench measurement — they should be the first things a multimeter checks.

Net: Phase 2 is a clean, auditable, bit-reproducible foundation. The re-audit did its job. Carry the build-integrity-vs-design-validation distinction into Phase 3.

---

## Action items (from this re-audit + 02:00 retro)

- [ ] **(both)** End-of-Phase re-audit is a standing pattern; cold-clean ccache-disabled rebuild + sha-reproduce is criterion A1 (if A1 fails, nothing else matters).
- [ ] **(worker)** Add `decision_forks_watched:` + `escalation_log:` as documented task-YAML template elements (lightweight; propose exact schema in next contract).
- [ ] **(both)** Mauch HS-200-LV scale values (`HAL_BATT_VOLT_SCALE 9.0` / `HAL_BATT_CURR_SCALE 60.6`) flagged **PRIORITY** for Phase 6.5 forum review + Phase 9 bench measurement — least-verified numbers in the Phase 2 hwdef (sourced from web research, not in-tree grep or reference-design inheritance).
- [ ] **(both)** PHASE2_AUDIT.md cited as build-integrity evidence, **NOT** design-validation. Design correctness (BIDIR matrix, Mauch scales, CRSF 5V-tolerance, DShot DMA contention) remains Phase 6/9's job. "Phase 2-exit re-audit PASSED" = "Phase 2 is a sound foundation to build Phase 3 on," not "Phase 2 design is validated."

---

## Phase 2-exit summary

- **Part A:** gate-passed. Phase 2 binary + documentation chain is sound. Phase 3 may build on top.
- **Part B:** inventory complete. 1 strip (BATT2 scaffolding). 5 KEEP items (buzzer, PINIO1/2, airspeed pin, RSSI, CAN1). 1 DEFER per master adjudication (MAX7456 OSD → OPEN_QUESTIONS `phase2exit-1`).
- **Part C:** 02:00 retro folded into this report; ceremony PR avoided.
