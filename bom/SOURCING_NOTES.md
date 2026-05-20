# novapcb v1 — Sourcing Notes

Companion to `bom/novapcb-bom.csv`. Captures fab/assembly target, two-sided-SMT context, carry-forward footprint risks, externally-procured items, and Sai-decision flags. **Read this before placing a fab order.**

Last revised: 2026-05-20 (Phase 5 BOM).

---

## 1. Fab + assembly target — JLCPCB

**Choice: JLCPCB SMT assembly + 4-layer PCB.**

Per Phase 5 `decision_forks_watched.fab-target`. Reasoning:

| Criterion | JLCPCB | PCBWay | OSHPark+sep-asm |
|---|---|---|---|
| 4-layer free tier ≤100×100mm | ✓ (we are 36×36) | paid | paid |
| Min drill | 0.20 mm (we use 0.25) | 0.20 mm | 0.20 mm |
| Min track / clearance | 0.0889/0.0889 mm (we use 0.13/0.13) | 0.0889 | 0.0889 |
| Basic-part library (lowest assembly cost) | ~3000 parts | ~700 | N/A (no asm) |
| Two-sided SMT assembly | ✓ supported | ✓ | manual |
| ENIG / HASL options | both | both | HASL only |
| Typical lead time | 5-7 days fab + 3 days asm | similar | 14+ days |

JLCPCB also accepts IPC-2581 + standard Gerber + KiCad CPL files — our Phase 4f `run_gerber_export.py` produces exactly that bundle.

**For Sai when ordering**: the LCSC part numbers in `novapcb-bom.csv` map directly to JLCPCB's parts library. "Basic" parts have no per-design loading fee; "Extended" parts incur ~$3/part one-time loading. Of our ~25 assembled line items, **~19 are Basic** (all passives + ferrite + USBLC6 + AP2112K-3.3) and **~6 are Extended** (STM32H743VIT6, ICM-42688-P, DPS310, USB-C connector, microSD socket, 3× JST-GH connectors, SWD header, crystal). Total extended-part loading is roughly **$18–24** on first run.

---

## 2. Two-sided SMT assembly — REQUIRED

This is a two-sided board. **Both F.Cu (top) and B.Cu (bottom) carry SMD parts.** When ordering JLCPCB SMT, select "Assembly side: both sides" — not the cheaper top-only option.

**B.Cu (bottom) assembled parts (per Phase 4b/4c placement):**
- **J2** — microSD socket (Hirose DM3AT-SF-PEJM5)
- **J9** — SWD header (2×5 1.27mm SMD)
- **U4** — DPS310 barometer (LGA-8)
- **R51, R52, R53, R54, R55** — SDMMC1 pullups (47kΩ 0402)

Everything else (U1 MCU, U2 LDO, U3 IMU, U5 USB ESD, Y1 crystal, J1 USB-C, J3-J5 JST-GH, all decoupling + bulk caps + remaining resistors + FB1 ferrite) is on **F.Cu (top)**. Solder pads (J10, J11-J18) are PCB-only — no parts to assemble.

If you skip "both sides" in the JLCPCB quote, **the bottom-side components will not be populated** and the board cannot be flashed (no SWD), cannot record logs (no microSD), and will mis-baro (no DPS310).

---

## 3. Carry-forward — ICM-42688-P footprint (HARD pre-fab item)

`OPEN_QUESTIONS.md` entry **phase4a-1** is still HARD-status and must be resolved **before Phase 6m DFM gate / before the JLCPCB fab order ships**.

**Current state**: BOM cites U3 = ICM-42688-P (LCSC C1850418, TDK part). The footprint used on the schematic + board is the standard KiCad library `Package_LGA:LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y`. This **is a generic LGA-14 land pattern**, not specifically the ICM-42688-P land pattern from TDK's datasheet (DS-000347 §11.2).

**Risk**: pad geometry mismatch (pad pitch, pad size, pin-1 marker, thermal pad if any) could cause the part to not solder reliably, or to enumerate but produce off-axis bias readings, or to short between pads.

**Required action before fab**:
1. Pull TDK datasheet DS-000347 v1.6 §11.2 "Package Outline Drawing" + §11.3 "Land Pattern Recommendation".
2. Compare each pad's X/Y/width/height against the KiCad library `LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y` in pcbnew.
3. If mismatch ≥0.05 mm on any pad, **derive a custom footprint** matching TDK's land pattern + commit to `hardware/kicad/lib/novapcb.pretty/ICM-42688-P.kicad_mod`.
4. Re-run `generate_board.py` so the board uses the corrected footprint.
5. Close OPEN_QUESTIONS phase4a-1.

This is **Phase 6m DFM gate work**, not Phase 5. Phase 5 sources the part; Phase 6m validates the footprint matches the datasheet. **Do not place the JLCPCB order until phase4a-1 is closed.**

---

## 4. Externally-procured items (NOT on this PCB BOM)

These are listed for the integrator (Sai) but are **not** part of the novapcb fab order. They are sourced separately and mate to the FC's JST-GH connectors via cables.

### 4.1 Mauch power module + DF-13→JST-GH 6P adapter cable

- **Module**: Mauch PL series (e.g. PL-200 for 4S–6S / ≤200A) — DECISIONS §5.
- **Adapter cable**: Mauch ships DF-13 connectors by default; novapcb uses JST-GH 6P. Either buy a Mauch model with JST-GH option (preferred — Mauch sells JST-GH variants directly), OR fabricate an adapter cable (DF-13 6P female ↔ JST-GH 6P female, pinout 1:1 per Pixhawk DS-009 §3.4 power-module pinout).
- **Pinout on J4** (FC side, JST-GH 6P): 1=VBAT_sense, 2=CURRENT_sense, 3=N/C, 4=N/C, 5=GND, 6=+5V_BEC (Pixhawk DS-009 standard).

### 4.2 GPS + external magnetometer module

- Module is downstream of **J5** (JST-GH 10P GPS+Mag combined connector — Pixhawk DS-009 standard).
- Recommended: Holybro M9N / M10 GPS+mag, or Matek M9N (DS-009-compatible).
- Pinout per DS-009: 1=+5V, 2=GPS_TX, 3=GPS_RX, 4=I2C_SCL, 5=I2C_SDA, 6=BUTTON, 7=BUTTON_LED, 8=N/C, 9=SAFETY_SWITCH, 10=GND. The FC honours this exactly (Phase 3e sheet).
- **Sai decision**: pick GPS module based on airframe + ArduPilot config. Not blocking for fab.

### 4.3 ELRS RX module + CRSF cable

- DECISIONS §4 — external RX module, on-board CRSF UART.
- The receiver (e.g. ExpressLRS RP4TD per CLAUDE.md §2.1) connects to FC via the **J10 CRSF solder pads** (option-θ — wire pads, not a connector). Sai solders the 4-pin CRSF lead (+5V / GND / UART_TX / UART_RX) directly.
- **Sai decision**: RX module choice depends on regulatory region (868 vs 915 vs 2.4 GHz). Not blocking for fab.

### 4.4 ESC pigtails

- 8× ESC outputs on **J11-J18 solder pads** (option-θ — wire pads, not connectors).
- DECISIONS §3 — DShot300/600 preferred, PWM fallback. 3.3V logic (most modern ESCs accept).
- **Sai decision**: ESC choice + which 4 of 8 channels are used (the airframe is a quad → 4 channels active, 4 reserved for hex/octo upgrade). Not blocking for fab.

---

## 5. Sai-decision flags (decisions blocking fab order)

Marked items that need supermaster (Sai) explicit decision before the JLCPCB order goes out:

| # | Decision | Default if Sai is silent | Risk if wrong |
|---|---|---|---|
| 1 | ICM-42688-P footprint (phase4a-1) — accept current KiCad library, or derive from TDK datasheet? | derive (recommend) | bias drift / solder failure |
| 2 | Surface finish — ENIG (smoother, better for fine-pitch QFN/LGA, +$8) or HASL (cheaper, default JLCPCB) | ENIG (LGA-14 + LGA-8 sensors benefit) | cold solder on LGA pads with HASL |
| 3 | Soldermask color (default green) | green | none — cosmetic |
| 4 | Silkscreen — include refdes + value labels (default yes) | yes | none |
| 5 | Stencil order (for hand-rework) — yes/no | no (JLCPCB asm includes stencil for in-house run) | only matters if rework expected |
| 6 | Quantity — how many boards on first run | 5 (JLCPCB minimum) | rework spare buffer affected |
| 7 | Lead-free / RoHS — JLCPCB default is lead-free SAC305 | lead-free | regulatory only |

**None of items 1-7 are decided in this BOM** — they go in the fab-order request (Phase 7) when Sai is ready.

---

## 6. Long-lead / sole-source / regional-restriction flags

Each assembled non-passive part was checked for sourcing risk. Status as of 2026-05-20:

| Part | Status | Mitigation |
|---|---|---|
| STM32H743VIT6 | In stock LCSC ~9k pcs; >$8/part extended | Alt: STM32H743VIT6TR (same die, T&R packaging) |
| ICM-42688-P | In stock; TDK fully active. Allocations easing post-2024 shortage. | Alt: ICM-42605 (lower-cost same family) if needed |
| DPS310 | In stock; Bosch active part | Alt: BMP388 (Bosch — similar form factor, slightly higher noise floor) |
| AP2112K-3.3 | In stock LCSC ~50k pcs; basic part | Alt: LP5907 / TLV70033 (TI) |
| USBLC6-2P6 | In stock; basic part | Alt: TPD2E007 (TI) |
| HRO USB-C TYPE-C-31-M-12 | In stock; commodity | Alt: GCT USB4105 |
| Hirose DM3AT-SF-PEJM5 | Limited stock; check at order time | Alt: Molex 5031822892 |
| JST SM06B/SM10B-GHS-TB | In stock; JST volume part | none — no no-MP variant exists (catalog-verified) |

**No sole-source items, no regional-restricted items, no parts with >12-week stated lead.** All passives are commodity-multiple-source.

---

## 7. PCB-only land patterns (no parts to order)

These BOM rows have `Assembled=no` and exist on the board as copper-only PCB features. They do **not** appear on the JLCPCB BOM upload — they are part of the gerbers.

| RefDes | PCB feature |
|---|---|
| J10 | CRSF 4-pad solder field (option-θ — PR #44; replaced JST-GH 4P after J3 placement conflict) |
| J11-J18 | 8× ESC 2-pad solder fields (DShot/PWM + GND wire termination) |
| H1-H4 | 4× M3 plated mounting holes, GND-pad ring (Pixhawk 30.5×30.5 mm pattern) |

---

## 8. Cross-check against netlist

70 non-virtual components in `hardware/kicad/novapcb/novapcb.net` (Phase 3 netlist) → 34 BOM rows in `novapcb-bom.csv`. Every refdes is accounted for. Confirmed via:

```bash
cd hardware/kicad/novapcb && python3 -c "
import re
with open('novapcb.net') as f: c = f.read()
refs = re.findall(r'\(comp\s*\(ref\s*\"([^\"]+)\"\)', c)
non_virtual = [r for r in refs if not r.startswith('#FLG')]
print(f'netlist non-virtual: {len(non_virtual)}')
"
# Expected: 70
```

For the 9 solder-pad refs (J10-J18), the netlist still carries their **old** values (CRSF_4P, ESC*_PAD with old pin-header footprints) because option-θ (PR #44) edited the board directly, not the netlist. The BOM CSV reflects the **board** (source of truth — see `hardware/kicad/novapcb-layout/novapcb-layout.kicad_pcb`), not the stale netlist values. If the netlist is regenerated in a future Phase 3 refresh, it should be updated to match.

---

## 9. Next-phase dependencies

This BOM unblocks:

- **Phase 6 simulation** (DESIGN_PHASES Phase 6) — once footprints stabilize (phase4a-1 closes), SI/PI sim runs against the routed board.
- **Phase 6m DFM gate** — JLCPCB DFM-check the gerbers + this BOM; close phase4a-1.
- **Phase 7 fab order** — translate this BOM into JLCPCB SMT order form (LCSC# columns are already in the format JLCPCB expects).
- **Phase 9 bring-up** — once boards arrive, this BOM is the part-identification reference for any rework.

— end of SOURCING_NOTES.md —
