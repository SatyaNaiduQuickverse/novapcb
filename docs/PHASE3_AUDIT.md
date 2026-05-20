# Phase 3 audit — re-audit + carry-forward consolidation

**Date:** 2026-05-20
**Task contract:** `tasks/phase-3-exit.yaml`
**Inputs:** post-3i schematic (9 sheets: 3a-3i) + Phase 3.5 reference audit (`docs/REFERENCE_AUDIT.md`)
**Headline:** Phase 3 schematic capture is **VERIFIED COMPLETE** at hwdef-pin level. **0 Cat-B real omissions** remaining. Phase 4 layout can proceed.

---

## Part A — Re-audit (gating)

### A1. Cold rebuild + ERC + guard

Method: `rm -f generate.log generate.erc generate_sklib.py novapcb.net && python3 generate.py` from `hardware/kicad/novapcb/`.

| Check | Result | Source |
|---|---|---|
| SKiDL ERC errors | **0** | `generate.erc:0` |
| SKiDL ERC warnings | **67** (unchanged from 3h; +0 from 3i: 2 MCU pins newly connected balanced by 2 connector CTS/RTS NC pins) | `generate.erc` |
| Netlist-generation errors | **0** | `generate.log` |
| Netlist-generation warnings | **150** (SKiDL "tag" cosmetic warnings; harmless per `KICAD9_NOTES.md`) | `generate.log` |
| Rail-uniqueness guard | **PASS** — no `_N`-suffixed shared rails | `generate.py:71-91` |
| Reproducibility from `generate.py` alone | ✓ | (no manual steps required) |

**A1 PASS.**

### A2. hwdef-completeness re-check (post-3i)

Method: re-run the A2 audit script — for every MCU pin assigned a function in `hwdef.dat`, verify the pin is either connected to a net in `novapcb.net` OR classified as a documented-intentional omission.

**Top-line numbers (master 3h.7 housekeeping — exact count):**

| Metric | Count |
|---|---|
| hwdef-assigned MCU pins | **63** |
| Connected in `novapcb.net` (by port name match) | **46** |
| Unconnected in `novapcb.net` | **28** |
| └ **Cat-A** — MatekH743 inherited harmless cruft (no novapcb v1 hardware) | **25** |
| └ **Cat-C** — Deliberate v1 feature-scope omission (CAN; OPEN_QUESTIONS CLOSED `phase3exit-can`) | **3** |
| └ **Cat-B** — Real omission needing schematic fix | **0** |

(Prior pings cited 22 / 25 / 28 across different summaries — those were partial enumerations. Reconciled here: **28 total unconnected = 25 Cat-A + 3 Cat-C + 0 Cat-B**.)

**Per-pin enumeration:**

#### Cat-A: MatekH743 inherited cruft, no novapcb v1 hardware (25 pins)

These were classified in Phase 2-exit Part B (`firmware/hwdef-novapcb/PHASE2_AUDIT.md`) as KEEP-as-inert / harmless. They're hwdef-side firmware capabilities for which novapcb v1 has no corresponding chip, connector, or use case. Cost: <1 KB flash + zero runtime risk.

| Pin | hwdef line | Function | Why intentionally omitted from novapcb v1 schematic |
|---|---|---|---|
| PB12 | hwdef.dat:42 | MAX7456_CS (SPI2 NSS) | OSD deferred — OPEN_QUESTIONS `phase2exit-1` recommends omit (Pixhawk-class doesn't have analog OSD; Nova video is fully digital) |
| PB13 | hwdef.dat:43 | SPI2_SCK | SPI2 dedicated to MAX7456 (deferred) |
| PB14 | hwdef.dat:44 | SPI2_MISO | SPI2 dedicated to MAX7456 (deferred) |
| PB15 | hwdef.dat:45 | SPI2_MOSI | SPI2 dedicated to MAX7456 (deferred) |
| PB3 | hwdef.dat:48 | SPI3_SCK | External SPI3 for pixartflow optical flow — no chip on novapcb v1 (no optical flow sensor) |
| PB4 | hwdef.dat:49 | SPI3_MISO | External SPI3 for pixartflow — no chip on novapcb v1 |
| PB5 | hwdef.dat:50 | SPI3_MOSI | External SPI3 for pixartflow — no chip on novapcb v1 |
| PD4 | hwdef.dat:53 | EXT_CS1 | SPI3 external CS for pixartflow — no chip on novapcb v1 |
| PE2 | hwdef.dat:54 | EXT_CS2 | SPI3 external CS — no chip on novapcb v1 |
| PC4 | hwdef.dat:94 | PRESSURE_SENS | Airspeed sensor input — multirotor doesn't use; Phase 2-exit Item 4 KEEP |
| PC5 | hwdef.dat:97 | RSSI_ADC | Analog RSSI input — CRSF uses digital telemetry; Phase 2-exit Item 5 KEEP |
| PD10 | hwdef.dat:191 | PINIO1 | Matek general-purpose GPIO — Phase 2-exit Item 3 KEEP; no novapcb hardware |
| PD11 | hwdef.dat:192 | PINIO2 | Matek general-purpose GPIO — Phase 2-exit Item 3 KEEP; no novapcb hardware |
| PE3 | hwdef.dat:104 | LED0 | Matek onboard LED — not on novapcb v1 |
| PE4 | hwdef.dat:105 | LED1 | Matek onboard LED — not on novapcb v1 |
| PB8 | hwdef.dat:126 | UART4_TX | Spare UART — no novapcb connector |
| PB9 | hwdef.dat:125 | UART4_RX | Spare UART — no novapcb connector |
| PE0 | hwdef.dat:143 | UART8_RX | Spare UART — no novapcb connector |
| PE1 | hwdef.dat:144 | UART8_TX | Spare UART — no novapcb connector |
| PE7 | hwdef.dat:137 | UART7_RX | Spare UART — no novapcb connector |
| PE8 | hwdef.dat:138 | UART7_TX | Spare UART — no novapcb connector |
| PE9 | hwdef.dat:140 | UART7_RTS | Spare UART — no novapcb connector |
| PE10 | hwdef.dat:139 | UART7_CTS | Spare UART — no novapcb connector |
| PD8 | hwdef.dat:122 | USART3_TX (GPS2) | Second GPS port — novapcb single-GPS by design (MatekH743 dual-GPS inheritance) |
| PD9 | hwdef.dat:121 | USART3_RX (GPS2) | Second GPS port — novapcb single-GPS by design |

**25 / 25 documented; all classified KEEP-inert by Phase 2-exit Part B.**

#### Cat-C: Deliberate v1 feature-scope omission (3 pins)

| Pin | hwdef line | Function | Decision record |
|---|---|---|---|
| PD0 | hwdef.dat:147 | CAN1_RX | OPEN_QUESTIONS.md `CLOSED phase3exit-can` — Nova drone uses zero CAN peripherals; CAN transceiver + connector deliberately not populated v1; hwdef CAN1 retained as harmless firmware capability for future v1.x/v2 |
| PD1 | hwdef.dat:148 | CAN1_TX | Same |
| PD3 | hwdef.dat:149 | GPIO_CAN1_SILENT | Same |

**3 / 3 documented.**

#### Cat-B: Real omissions requiring schematic fix

**0 / 0.**

**A2 PASSES CLEAN.** Every hwdef-assigned pin is either connected in the schematic or a documented-intentional omission with a per-pin reason.

### A3. CONFIDENCE_MAP coherence (rows 1-14)

Method: for each row, verify (a) "Updates" column cites a 3x sub-phase consistent with merged main, (b) confidence trajectory monotonic by evidence, (c) all 3a-3i sheets have ≥1 corresponding row.

| Row | Subsystem | 3x sheet ✓ | Confidence trajectory monotonic | Status |
|---|---|---|---|---|
| 1 | MCU + clock + reset + decoupling | 3a ✓ | HIGH (~98%) (initial) | OK |
| 2 | USB-CDC interface | 3g ✓ | HIGH (~97% → ~98%) | OK |
| 3 | 5V → 3.3V LDO | 3b ✓ | HIGH (~95%) (stable) | OK |
| 4 | IMU SPI bus | 3c ✓ | HIGH (~92% → ~93%) | OK |
| 5 | Barometer I²C | 3d ✓ | MED-HIGH (~88 → ~92%) | OK |
| 6 | External mag + GPS + telem | 3e + 3i ✓ (broadened title) | HIGH (~93% → ~97%) | OK (3i evidence note appended) |
| 7 | microSD SDMMC | 3h ✓ | MED-HIGH (~80% → ~88%) | OK |
| 8 | 8-channel ESC outputs | 3f ✓ | MED-HIGH (~75% → ~89%) | OK |
| 9 | CRSF UART | 3g ✓ | MED-HIGH (~75% → ~87%) | OK |
| 10 | Mauch VBAT/current | 3h ✓ | MED-HIGH (~80% → ~89%) | OK; PRIORITY-Phase-9 flag for 9.0/60.6 cal |
| 11 | Reverse polarity + ESD (VBAT/5V) | — (DEFER-TO-6.5 honest) | LOW (~65%) (stable) | OK |
| 12 | EMC / RF coupling | — (DEFER-TO-6.5 honest) | LOW (~60% → ~62%) | OK; small bump for USB ESD via USBLC6 |
| 13 | Thermal | — (DEFER-TO-6j) | MED (~80%) (stable) | OK |
| 14 | Brownout / POR | 3a + 3.5 ✓ | MED (~75% → ~78%) | OK |

**A3 PASS.** 14/14 rows coherent; every 3x sheet (3a-3i) has ≥1 mapped row.

### A4. OPEN_QUESTIONS.md internal consistency

| Entry | Status | Verified |
|---|---|---|
| v2-1: FMUv6X mechanical drop-in | OPEN, deferred to v2 | ✓ |
| phase2a-1: IMU DRDY pin | OPEN, polled-mode is current | ✓ |
| phase2exit-1: MAX7456 omit | OPEN, master recommendation: omit; Cat-A in A2 enumeration above | ✓ |
| phase3-render-1: Phase 3 drawn-schematic | OPEN, dispatched (Phase 3.5–6 window) | ✓ |
| **CLOSED phase3exit-can** | CLOSED 2026-05-20 (deliberate v1-omit; Cat-C in A2 enumeration) | ✓ |

**A4 PASS.** OPEN/CLOSED labels coherent; CLOSED entries below the `---` separator; all 4 open entries still applicable.

### Part A summary

| Check | Verdict |
|---|---|
| A1 cold rebuild + ERC + guard | **PASS** |
| A2 hwdef-completeness | **PASS clean** (0 Cat-B) |
| A3 CONFIDENCE_MAP coherence | **PASS** |
| A4 OPEN_QUESTIONS consistency | **PASS** |

**No Rule-13 stop.** Phase 3 schematic capture is verified complete.

---

## Part B — Phase 4 carry-forward consolidation

This is a hand-off table, not new analysis. Items are unchanged from `docs/REFERENCE_AUDIT.md` and the per-sheet docstrings — consolidated here for Phase 4 task-contract dispatch.

### B1. Phase 4 carry-forward items (7)

| # | Item | Source row / sheet | Phase 4 action |
|---|---|---|---|
| 1 | ICM-42688-P symbol + footprint | Row 4 / 3c | Replace `Conn_01x14` rename with TDK-datasheet-exact symbol + production-grade LGA-14 land pattern |
| 2 | DPS310 symbol | Row 5 / 3d | Replace `BMP280`-as-`DPS310` with proper `DPS310`-named symbol (pin-identity already verified 8/8) |
| 3 | Solder pad geometry for 8× ESC outputs | Row 8 / 3f | Replace `PinHeader_1x02_P2.54mm_Vertical` placeholder with production solder-pad pattern (~2.5 × 1.5 mm at 2.5 mm pitch) |
| 4 | USB diff-pair impedance + length match | Row 2 / 3g | 90 Ω differential routing + length-matching + USBLC6 placement on host side of cable ESD path |
| 5 | ADC filter component placement | Row 10 / 3h | 1 kΩ + 100 nF on Mauch ADC lines must be physically close to MCU PC0/PC1 (post-trace from connector) |
| 6 | SDMMC trace routing | Row 7 / 3h | Matched lengths + impedance for 4-bit bus; card-detect mechanical switch pin (Phase 2h fork-2 testpoint) |
| 7 | Mounting hole exact positions | Row — / 3h | Phase 2.5 P1.1 spec'd 30.5 c-to-c at corners; Phase 4 confirms in real layout |

### B2. DEFER-TO-Phase-6.5 / Phase-6-sim consolidated table

Routed to external EE review (Phase 6.5 forum) + simulation (Phase 6 series). Unchanged from `REFERENCE_AUDIT.md`.

| Item | Sub-row | Routes to | Status |
|---|---|---|---|
| 5V-input reverse polarity + ESD | Row 11 | Phase 6.5 + Phase 6i sim | DEFER (no schematic ref obtainable) |
| GPS+mag JST-GH 10P ESD | Row 12 | Phase 6.5 + Phase 6k sim | DEFER (standard TVS practice; "don't silently add" master 3e.5) |
| CRSF JST-GH 4P ESD | Row 12 | Phase 6.5 + Phase 6k sim | DEFER (same) |
| Mauch JST-GH 6P ESD | Row 12 | Phase 6.5 + Phase 6k sim | DEFER (same) |
| Telem JST-GH 6P ESD | Row 12 (3i) | Phase 6.5 + Phase 6k sim | DEFER (joins the same row 12 deferred-ESD pile per 3i docstring) |
| AP2112K-3.3 part-choice confirmation | Row 3 | Phase 6.5 | DEFER (Matek actual LDO not sourceable) |
| ADC filter values (1 kΩ + 100 nF) | Row 10 | Phase 6h sim | DEFER (datasheet-grounded; sim refines) |
| SDMMC 47 kΩ pull-up value | Row 7 | Phase 6f sim | DEFER (SD-spec middle; sim refines) |
| DShot ringing on bare lines | Row 8 | Phase 6g sim | DEFER (no series-R; sim validates / sizes) |
| USB-CDC diff-pair SI | Row 2 | Phase 6b sim | DEFER (12 Mbps full-speed) |
| Thermal | Row 13 | Phase 6j sim | DEFER (layout-dependent) |
| **Phase 3 drawn-schematic rendering** | — | Dedicated investigation Phase 3.5–6 window | OPEN_QUESTIONS `phase3-render-1` |

### B3. PRIORITY-Phase-9-bench

| Item | Row | Why PRIORITY | Action |
|---|---|---|---|
| Mauch HS-200-LV calibration values 9.0 / 60.6 | Row 10 | Web-research-sourced (mauch-electronic.com + craftandtheoryllc.com + ardupilot.org wiki) — not datasheet-verified. Per-unit final-test calibration card refines to ±1-3%. | Bench-validate against shunt-meter VBAT + currentclamp at Phase 9. Failsafes function pre-calibration; calibration tightens accuracy. |

### B4. SUPERMASTER-return queue (carried)

5 items in ENGINEERING_RIGOR proposals queue (unchanged from 04:00-07:00 retros — listed here as a Phase 3 close-out reminder so they don't drop):

1. Realistically-scaled smoke-test bar (P0 lesson from Phase 3a)
2. "⚠️ SUPERMASTER REVIEW" PR-body lead-section codification (Phase 3i used it)
3. End-of-Phase re-audit standing pattern (now applied at Phase 2-exit + Phase 3-exit — pattern proving out)
4. Physical-possibility sanity check (master + worker mirror; Phase 2.5 P1.1 lesson)
5. Relax retro cadence hourly → 2-hourly / phase-boundary-triggered (master pushback 05:00 still standing — supermaster sign-off needed)

Plus two new items raised this Phase 3-exit cycle:

6. (Optional) ESD/protection topology elevated to ENGINEERING_RIGOR-grade policy (e.g., "all external connectors carrying signals over 100 mm of cable require TVS protection captured at Phase 3"). Would move row 12 from DEFER-TO-6.5 bucket into Phase 3 default-required. Worth surfacing to supermaster alongside the 5 existing. (Source: `docs/REFERENCE_AUDIT.md` §"Note on adding these to the schematic".)
7. **Sub-phase-breakdown completeness check at P0 approval time** (master + worker mirror). Master 08:00 process-change proposal + worker 08:00 cross-review mirror: when a phase proposes a sub-phase breakdown (e.g., Phase 3 P0 8-sheet plan), include an explicit completeness line — "every relevant hwdef peripheral / every netlist subsystem / every connector is covered by a sub-phase" — in the proposal itself. Master can refuse approval if the completeness line is missing. Catches breakdown gaps at P0 (cheap) instead of at exit-audit (the Phase 3i telem omission was caught at A2 exit-audit; would have been caught at P0 under this rule). Source: `retrospectives/2026-05-20T0800.md` master process-changes + worker cross-review point 2.

---

## Part C — 08:00 retrospective fold

See `retrospectives/2026-05-20T0800.md` for the standalone retro (per RETROSPECTIVES.md cadence). Master section paste-in pending — was attached to the original Phase 3-exit dispatch; post-compaction worker context doesn't have the verbatim text.

---

## Audit conclusion

Phase 3 is **CLOSED**: 3a-3i schematic capture + 3.5 reference audit + 3-exit re-audit all done. A2 hwdef-completeness PASSES CLEAN (0 Cat-B); A1/A3/A4 all PASS.

**Phase 3 deliverables:**
- 9-sheet schematic source (SKiDL Python, `hardware/kicad/novapcb/sheets/*.py`)
- `novapcb.net` — load-bearing artifact for Phase 4 PCB layout
- Phase 3.5 reference audit (`docs/REFERENCE_AUDIT.md`) — no NEEDS-FIX; 9 OK-AS-IS / 3 DEFER-TO-6.5 / 1 DEFER-TO-6j / 1 PRIORITY-Phase-9
- This Phase 3-exit audit (`docs/PHASE3_AUDIT.md`) — 0 Cat-B; 7 Phase 4 carry-forwards consolidated; SUPERMASTER queue updated

**Phase 3 deferred (tracked):**
- Phase 3 drawn-schematic rendering (`OPEN_QUESTIONS phase3-render-1`) — blocks ONLY Phase 6.5 forum review

**Phase 4 entry conditions met:** netlist is correct + complete; 7 carry-forward items inventoried; Phase 4 task contract can proceed with its own P0 routing-approach investigation (master 06:00 heads-up: Freerouting vs pcbnew-scripted vs hybrid; realistic-scale-tested per Phase 3a P0 lesson).

**Recommendation:** Phase 4 (PCB layout) opens after this PR merges.
