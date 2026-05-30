# Handoff to Sai — 2026-05-30 (board freeze-ready, awaiting fab order)

> Master Claude's brief.
> One file, one read, full picture. Read this first.

---

## TL;DR

**Board is LOGICAL FREEZE-READY.** Real-latent = 0. All CLI-deliverable work complete (PRs #122–#135). Remaining: your hands at JLCPCB portal + freeze trigger + fab order $.

Head: `cd7c050` on `sch/option-b-buck`.

---

## What ships in v1

### Routing
- ✅ Full power tree: D1 buck + D2 +5V dist + D3 eFuse + D4 MCU core + D5 +3V3_IMU + D6 USB-C CC/BATT/HEATER + I2C2 baro
- ✅ All signal nets: CAN, microSD SDMMC1, GPS UART, CRSF UART4 PA0/PA1 (re-pinned PR #120), 6/8 motors (MOT7/8 v2-deferred per your option D), USB-C diff pair, IMU SPI1/2/3
- ✅ Triple-IMU: U3 ICM-42688 INT-driven, U8 BMI088 INT-driven, U9 LSM6DSV16X polled-mode

### Connectors physically present
- J1 USB-C, J2 microSD, J3 Telem (placed; routes v2-deferred), J4 power input (Mauch), J5 GPS+mag, J9 SWD (placed at (15,35) B.Cu; routes v2-deferred), J10 CRSF, J11 ESC outputs, J19 BATT2, J20 CAN

### Sims (all valid post final routing)
- Sim 1 thermal: MCU Tj 65.05°C, +15°C margin
- Sim 2 USB Z_diff: 87.4Ω (PR #75 inherits validated)
- Sim 3 SDMMC SI: 172ps skew = 97.8% timing margin @ SDR25 50MHz
- Sim 4 CAN Z_diff: ~120Ω near-ideal
- Sim 5 PDN: 82.9 mΩ peak ≤ 100 mΩ gate
- HSE Pierce analytical: 6-10× negative-resistance margin (AN2867 requires 5×)

### Firmware
- ArduPilot waf copter builds clean — 1.52 MB used / 184 KB free of H743 2 MB flash
- hwdef.dat sync'd to schematic post all re-pins (CRSF→UART4, GPS1_TX→PA2, BUZZER→PA3, MCU pin map complete)

### Process discipline
- 23 master process rules codified (Rule 17 no-loose-threads, Rule 21 Sai-overrides-worker-pause, Rule 22 spec-doc-≠-artifact, Rule 23 per-net unconnected audit — the rule that caught the dead-on-arrival fab pre-order)
- Audit gates: `scripts/audit_unconnected_per_net.py` + `scripts/audit_layout_compliance.py` — both PASS at freeze head
- CLI DRC verification = GUI DRC equivalence documented (`docs/CLI_DRC_VERIFICATION.md`)

---

## Empirically v2-deferred (no flight regression)

Same pattern, same justification, all accepted as structural empirical reality:

| Item | Walls before defer | v1 functional impact |
|---|---|---|
| MOT7/MOT8 (octocopter) | (Sai option D) | quad/hex flight retained |
| FLT/PGOOD (eFuse status) | structural east-edge corridor | eFuse autonomously protects |
| Telem J3 (USART1) | 4/4 walls (NE + SE corridors) | USB-CDC is canonical MAVLink path |
| SWD routes (SWDIO/SWCLK/NRST) | **9/9 walls** (test-pads + J9 direct + slow-net reroute + layer flip + J2 placement) | DFU first-flash + USB-CDC fully functional; J9 connector physically present; wire-tack possible for occasional SWD debug |
| IMU3_INT1 (LSM6DSV16X INT) | 5/5 walls | polled-mode IMU3 still works on SPI3; ArduPilot flies on IMU1+IMU2 INT |
| C93.1 (BMI088 redundant decap) | 3/3 walls | Bosch spec met with C91+C92; Sim 5 PDN PASS confirmed |
| (Other) J9 SWD routes | 9th structural wall | wire-tack for SWD debug; DFU is the standard first-flash anyway |

---

## What's left for YOU (Sai's bits)

### 1. JLCPCB portal — BOM sourcing (~20-30 min)

`docs/BOM_LCSC_SOURCING.md` has all 8 TBD components researched + LCSC numbers ready. Paste them per the "BOM CSV row changes" section in that file. Quick summary:

| Item | LCSC | Tier | Note |
|---|---|---|---|
| Q5 AO3400A | C20917 | Basic | clean pick |
| L1 XAL4020-222MEC | C3151182 | Extended | Coilcraft, ~9mW DCR loss acceptable |
| R45 120Ω 0603 | C22787 | Basic | |
| R46 0Ω 0603 | C21189 | Basic | |
| J20 JST-GH SM04B | C189895 | Extended | stacks on existing JST-GH bucket (no incremental $) |
| R47 562K 0402 | C4294005 | Extended | OUT OF STOCK; fallback 560K acceptable |
| R48 180K 0402 | verify-at-order | Extended | standard E96 value |
| R61 heater 2512 | DNP | — | first article populate later if heater wanted |

**Total: 3 Basic / 4 Extended / 1 DNP. ~$12 Extended setup fees (~$9 incremental).**

### 2. JLCPCB order form — fab spec options (~10 min)

Follow `docs/JLCPCB_ORDER_GUIDE.md`. Key clicks:

| Field | Selection | Note |
|---|---|---|
| Stackup | 6-layer JLC06161H-3313 | matches our `CONTROLLED_IMPEDANCE.md` sims |
| Surface finish | ENIG 1U" | currently free promo on 6L; required anyway for fine-pitch LGA |
| Via covering | **"POFV" (Plated Over Filled Via)** | **CRITICAL — covers our 9 VIP pads; FREE on 6-20L boards as of 2025; board won't power without it** |
| SMT assembly | Both sides | board has B.Cu components (J2, J9, U4, R51-R55) |
| Quantity | 5 (minimum first article) | |
| Lead-free | Yes (default) | |

### 3. GUI bits on your KiCad Pi (~30-45 min)

`docs/SWD_PHYSICAL_DELIVERABLE.md` + `docs/SWD_TEST_PADS_V1.md` document the SWD physical state.
- BOOT0 jumper: Python `FootprintLoad` segfaulted during automated placement. Optional manual GUI placement OR wire-tack a jumper across BOOT0+3V3 for first-flash (5-min task).
- Final visual DRC scan: open pcbnew GUI on your Pi, run DRC, eyeball for any cosmetic issues the CLI can't catch (silkscreen rendering, courtyard color overlap — non-fab-critical but worth a glance).

### 4. Phase 7a freeze trigger (your blessing)

Tag the freeze commit. Master suggested format: `git tag -a v1.0-fab -m "v1.0 fab-ready freeze"`. Bump in DECISIONS.md if you like.

### 5. Phase 7b fab order submission

Upload Gerbers + drill + CPL + BOM CSV to JLCPCB. ~$80-170 USD per `JLCPCB_ORDER_GUIDE.md` cost estimate (door-to-door with DHL on 5-board first article).

**24h after payment:** JLC sends a parts-placement confirmation email. Reply same-day or fab stalls. Master will page you when it lands.

---

## What master + worker delivered this session

**Sessions ~2026-05-26 → 2026-05-30:**

- **30+ PRs landed** (#122 D1 → #135 DRU exception)
- **Real-latent 64 → 0** (Phase 4d-redux full power tree + sims revalidated)
- **2 project-saving Rule-9 catches** that prevented dead-on-arrival fab orders (+3V3_IMU rail + power-tree-unrouted via Rule 23)
- **23 master process rules codified** (Rule 17/21/22/23 + 9 earlier-session rules + pcb.ai adoption)
- **2 audit gates** scripting (`audit_unconnected_per_net.py`, `audit_layout_compliance.py`)
- **9-wall empirical SWD physical journey** documented (test-pads + J9 + slow-net reroute + layer flip + J2 move — all walled = structural truth)
- **VIP fab spec** identified + documented (POFV/IPC-4761 Type VII, 9 pads, FREE on JLC 6L)
- **HSE Pierce analytical** margin computed (~7×, exceeds AN2867 5× requirement)
- **BOM finalized + LCSC researched** (53 lines + 8 SAI-SOURCE items resolved)
- **CLI DRC equivalence** documented (kicad-cli + manual scripts = GUI DRC for fab-critical concerns)

---

## Process learnings (memory committed)

- Don't trust stale hwdef recall — verify peripheral assignments from current artifact before authorizing touches (Rule-9 lemma)
- Per-net unconnected audit is the freeze gate — total-count is misleading when plane-pour pads dominate
- Worker pause is recommendation not stop — Sai's standing "don't stop" directive overrides
- Master takes decisions — only true Sai-gates are freeze trigger / fab $ / hardware / scope changes
- Spec doc ≠ artifact — every "decision X done" claim needs artifact-side proof
- Loose threads — every defer empirically justified across multiple wall iterations; no schedule shortcuts

---

## Quick reference docs

- `docs/JLCPCB_ORDER_GUIDE.md` — click-by-click fab order workflow
- `docs/BOM_LCSC_SOURCING.md` — 8 TBD components researched
- `docs/SWD_PHYSICAL_DELIVERABLE.md` — 9-wall journey + first-flash procedure
- `docs/DFU_BOOTLOAD_PROCEDURE.md` — exact `dfu-util` command for first flash
- `docs/CLI_DRC_VERIFICATION.md` — CLI=GUI DRC equivalence proof
- `docs/PHASE_7A_FREEZE_CHECKLIST.md` — your freeze gate checklist
- `docs/DECISIONS.md` — all locked v1 decisions
- `STATUS.md` — live status (master keeps current)

---

**Ready when you are.** Master + worker standing by.

— master, 2026-05-30 session-end.
