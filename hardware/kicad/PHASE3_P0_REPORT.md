# Phase 3 Part 0 — schematic-capture approach investigation

Date: 2026-05-20
Master dispatch: Phase 3 Part 0 (after Phase 2.5 fit-confirmed merged at `2347b4a`)
Status: P0 gate report; awaiting master adjudication at P0.7.
**Bottom line: recommend SKiDL 2.2.3 (Python source-of-truth + generated `.kicad_sch` for forum review) with kicad-cli render pipeline.**

---

## P0.1 — Realistic headless schematic-capture options

Five candidates evaluated against installability on novarobotics64 (no sudo — apt needs password; pip is fine), maintenance status, KiCad 9 compatibility:

| # | Candidate | Installed? | Active? | KiCad 9? | Verdict |
|---|---|---|---|---|---|
| 1 | **SKiDL** (devbisme/skidl 2.2.3, PyPI) | YES (pip --user) | YES (active GitHub, recent releases) | YES (KiCad 9 schematic generation added) | **VIABLE** |
| 2 | **kicad-skip** (psychogenic/kicad-skip 0.2.5, PyPI) | YES (pip --user) | YES | KiCad 7+ (covers 9) | VIABLE for modify-existing; weaker for create-from-scratch |
| 3 | **atopile** (atopile/atopile, PyPI) | not installed (avoided extra pip churn until needed) | YES (active 2024+) | YES (compiles to KiCad-compatible netlists) | VIABLE but newer ecosystem; smaller community |
| 4 | **Hand-write `.kicad_sch` S-expressions** | n/a — no tooling needed | n/a | Yes if format-faithful | VIABLE but brutal: ~200-line S-expr per simple sheet, error-prone, no symbol-from-library convenience |
| 5 | **`kicad-cli sch`** (built into KiCad 9) | YES | n/a (KiCad maintained) | YES | **NOT VIABLE FOR CAPTURE** — only has `erc` + `export` subcommands; no creation API |
| 6 | **`pcbnew` Python API schematic side** | YES (KiCad 9) | n/a | n/a | **NOT VIABLE** — pcbnew has SCH_* type constants but zero schematic creation API; pcbnew is PCB-only |
| 7 | **eeschema GUI scripting / plugins** | n/a | n/a | requires GUI | **NOT VIABLE HEADLESS** |

Worker installed SKiDL + kicad-skip via `pip install --user` (no sudo, no system change beyond `~/.local/lib/python3.13/site-packages/`). atopile deferred — would only install if SKiDL/kicad-skip failed the smoke test.

---

## P0.2 — 5-axis assessment of viable options

| Axis | SKiDL | kicad-skip | atopile | Hand-write `.kicad_sch` |
|---|:---:|:---:|:---:|:---:|
| (i) Headless-feasible | ✓ pure Python | ✓ pure Python | ✓ pure Python | ✓ text editor |
| (ii) PR-reviewable | ✓✓ Python source diffs cleanly | ⚠ S-expr manipulation scripts are reviewable; output churn is opaque | ✓ `.ato` source diffs cleanly | ✗ S-expr blobs are huge + hard to review |
| (iii) Netlist for Phase 4 layout | ✓✓ `generate_netlist()` built-in | ⚠ can manipulate netlists; not generation-first | ✓ compiles to KiCad netlist | ✗ would have to hand-export via kicad-cli after open-in-GUI |
| (iv) Forum-review artifact (drawn schematic) | ✓✓ `generate_schematic()` produces `.kicad_sch` → kicad-cli renders PDF | ⚠ can produce `.kicad_sch` but creating-from-scratch is awkward | ⚠ KiCad-compatible netlist; less clear about drawn schematic | ⚠ have `.kicad_sch` text but no auto-rendering pipeline without manual layout |
| (v) Maintainable + reproducible per CLAUDE.md §6.1 | ✓✓ Python source = SoT, generated outputs reproducible | ✓ scripts on top of existing schematic | ✓ `.ato` SoT, but ecosystem is newer | ✗ brittle; no SoT abstraction |

**SKiDL wins on all 5 axes for novapcb's needs.** kicad-skip is excellent as a tool but oriented toward modifying existing schematics, not creating from scratch. atopile is genuinely competitive but is a newer ecosystem (2024+) with smaller community; SKiDL has the maturity advantage. Hand-write is the fallback if everything else fails — which the smoke test shows it doesn't have to.

---

## P0.3 — The core tension, resolved

**Tension as master framed it:** code-driven approaches (SKiDL) are headless-native + maximally PR-diffable but produce NO human-drawn schematic sheet; a drawn `.kicad_sch` is the EE-universal artifact (needed for Phase 6.5 forum review) but is GUI-native to create. Can any approach give BOTH?

**Resolution: YES — SKiDL gives BOTH.**

SKiDL 2.2.3 has `generate_schematic()` which produces a real KiCad-9-format `.kicad_sch` file from the Python circuit definition. The pipeline is:

```
   Python script (SoT, PR-diffable)
       │
       ▼  skidl.generate_netlist()
   .net file  ────────────────────────►  Phase 4 layout (KiCad PCB)
       │
       ▼  skidl.generate_schematic()
   .kicad_sch file (KiCad-native, GUI-openable)
       │
       ▼  kicad-cli sch export pdf
   .pdf  ────────────────────────────►  Phase 6.5 forum review
```

The Python source-of-truth is what reviewers see in PR diffs. The generated `.kicad_sch` is what EE forum reviewers open in KiCad GUI. The PDF is what gets posted to ArduPilot forum / Discord for review. ERC runs against either the SKiDL `ERC()` call (Python-side) OR the kicad-cli ERC against the .kicad_sch (KiCad-native).

This is the win-win path. The tension master flagged DOES dissolve with SKiDL specifically — not with kicad-skip, not with hand-writing, not (clearly) with atopile.

---

## P0.4 — End-to-end smoke test

Performed a minimal smoke test with SKiDL: 1 resistor + 1 capacitor + 3 nets (VCC, GND, MID).

### Commands

```bash
mkdir -p /tmp/skidl-test && cd /tmp/skidl-test
KICAD9_SYMBOL_DIR=/usr/share/kicad/symbols python3 <<'PY'
import skidl
skidl.set_default_tool(skidl.KICAD9)
skidl.lib_search_paths['kicad9'].append('/usr/share/kicad/symbols')

r = skidl.Part('Device', 'R', value='10k', footprint='Resistor_SMD:R_0402_1005Metric')
c = skidl.Part('Device', 'C', value='100n', footprint='Capacitor_SMD:C_0402_1005Metric')
vcc = skidl.Net('VCC'); gnd = skidl.Net('GND'); mid = skidl.Net('MID')
vcc += r[1]; r[2] += mid; mid += c[1]; c[2] += gnd

skidl.ERC()
skidl.generate_netlist(file_='rc-test.net')
skidl.generate_schematic(file_='rc-test')
PY

kicad-cli sch erc --output erc.txt --format report skidl_REPL.kicad_sch
kicad-cli sch export pdf --output sch.pdf skidl_REPL.kicad_sch
```

### Results

| Artefact | Size | Status |
|---|---:|---|
| `rc-test.net` | 2,730 B | ✓ KiCad netlist format |
| `skidl_REPL.kicad_sch` | 14,084 B | ✓ KiCad 9 schematic (S-expression) |
| `skidl_REPL.erc` | 237 B | ✓ SKiDL ERC output (0 errors, 2 warnings — both expected for 2-component test) |
| `sch.pdf` | 21,259 B | ✓ kicad-cli PDF render |
| `erc.txt` | 1 KB | ⚠ kicad-cli ERC found 6 issues — all `lib_symbol_issues` / `power_pin_not_driven`; resolvable by configuring `sym-lib-table` for the project (Phase 3a setup) |

The kicad-cli ERC `lib_symbol_issues` warnings are because the generated `.kicad_sch` doesn't reference an explicit symbol-library-table path. This is a SKiDL output convention; in production novapcb work, a project-level `sym-lib-table` will reference `/usr/share/kicad/symbols/` and resolve these warnings. Not a blocker for the approach.

The `power_pin_not_driven` ERC error is because the trivial test has VCC + GND as just net names without a defined power source — expected for a 2-component test; real novapcb sheets will have proper power-flag/power-source symbols.

**Pipeline confirmed end-to-end:** Python → netlist + `.kicad_sch` → ERC + PDF render. All headless. All on KiCad 9. All from standard tools (pip + kicad-cli, no exotic deps).

---

## P0.5 — Recommendation: SKiDL with kicad-cli render pipeline

**Recommend: SKiDL 2.2.3 (`pip install --user skidl`) as the primary Phase 3 schematic-capture tool, with `kicad-cli sch export pdf` for the Phase 6.5 forum-review artifact.**

### Why SKiDL

1. **Resolves the code-vs-drawn tension natively** (per §P0.3). Python source AND `.kicad_sch` output AND PDF render — all three artifacts from one source.
2. **Smoke test passes** (per §P0.4) — pipeline genuinely works headless on novarobotics64 today.
3. **KiCad 9 supported** explicitly (per SKiDL PyPI page + readme).
4. **Maintained** — devbisme/skidl active 2024+, version 2.2.3 current on PyPI.
5. **Mature** — well-documented, large community, used in production EE projects.
6. **Matches CLAUDE.md §6.1 code-driven philosophy** — Python source is fully diff-reviewable in PRs; generated outputs are reproducible from script.
7. **ERC built-in** at both layers (SKiDL `ERC()` for Python-side checks; kicad-cli ERC against `.kicad_sch` for KiCad-native checks).
8. **Netlist for Phase 4** — `generate_netlist()` is the primary SKiDL output; consumable by KiCad PCB layout (or by `pcbnew` Python API for scripted layout if Phase 4 stays headless).

### Caveats (honest downsides)

1. **Generated `.kicad_sch` layout will not be hand-aesthetic.** SKiDL auto-arranges; a human EE drawing the same circuit would place differently. Forum reviewers may comment on layout. This is acceptable IF the SCHEMATIC content (nets, symbols, values) is correct — and that's what SKiDL guarantees.
2. **`lib_symbol_issues` ERC warnings** require project-level `sym-lib-table` configuration. Easy fix at Phase 3a setup; documented here so future-worker knows about it.
3. **SKiDL output may need Phase 3-side `.kicad_pro` + `sym-lib-table` files** committed so the project opens cleanly in KiCad GUI. Phase 3a sets these up.
4. **Power flags** (`#PWR_FLG`, `#PWR`) need explicit Python-side declaration for power nets; trivial smoke test skipped this. Standard SKiDL pattern; documented in SKiDL docs.
5. **Hierarchical sheets** (typical for multi-sheet schematics) — SKiDL supports them but each sheet is a separate Python module. Phase 3 sub-phase rhythm (one sheet per PR) maps cleanly to this.
6. **Newer SKiDL features (schematic generation specifically) may have edge cases.** Version 2.2.3 is current; if a Phase 3 sheet exposes a SKiDL bug, fallback is hand-write that one sheet's `.kicad_sch` (using kicad-skip to validate the S-expression).

### Fallback if SKiDL fails on a complex sheet

If a specific Phase 3 sub-phase exposes a SKiDL limitation:
- **Hybrid**: SKiDL for circuit topology + kicad-skip to post-process the generated `.kicad_sch` for the failing element (e.g. add specific symbol-library references SKiDL doesn't auto-include).
- **Last resort**: hand-write the offending sheet's `.kicad_sch` using KiCad 9 S-expression format. Brutal but possible.

Both fallbacks have escalation paths (Rule-13 to master at the sub-phase where SKiDL fails).

---

## P0.6 — Phase 3 sub-phase breakdown proposal

Mirroring the Phase 2 one-PR-per-sub-phase rhythm. Each Phase 3 sub-phase produces one or more schematic sheets via SKiDL, an updated netlist, and a kicad-cli-rendered PDF. Per-sheet sub-phases keep PRs reviewable.

| Sub-phase | Sheet(s) | Scope | Depends on |
|---|---|---|---|
| 3a | MCU + clock + reset + decoupling | STM32H743VIT6 LQFP-100 + 8MHz crystal + reset RC + decoupling caps; also creates project structure (`.kicad_pro`, `sym-lib-table`, footprint-lib-table) | 3-P0 |
| 3b | Power tree | 5V input → 3.3V LDO (likely AP2112 or similar per MatekH743 reference); decoupling network; power-flag annotations | 3a |
| 3c | IMU SPI bus + IMU | ICM-42688-P on SPI1; CS = PC15; decoupling; INT pin pad (DRDY deferred per OPEN_QUESTIONS phase2a-1) | 3a, 3b |
| 3d | Barometer I²C | DPS310 on I²C2 at 0x76; decoupling | 3a, 3b |
| 3e | GPS + mag combined connector | JST-GH 10-pin Pixhawk-standard; UART (USART2/USART3) + I²C (ALL_EXTERNAL); safety LED + safety button + buzzer signal wiring | 3a, 3b |
| 3f | ESC outputs + DShot | 8× PWM/DShot outputs on PB0/PB1/PA0/PA1/PA2/PA3/PD12/PD13; output filtering optional | 3a |
| 3g | CRSF UART + USB-C | USART6 (PC7/PC6) → JST-GH CRSF connector; USB-C HRO mid-mount → STM32 OTG_FS pins (PA11/PA12); ESD protection optional | 3a |
| 3h | Power monitor + microSD + remaining I/O | Mauch HS-200-LV connector (6P JST-GH) → ADC inputs PC0/PC1; microSD SDMMC1; SWD header; mounting holes | 3a, 3b |

**Total: 8 sub-phases (3a-3h).** Matches Phase 2 sub-phase density (Phase 2 had 8: 2a-2h).

After 3h: **Phase 3.5 reference-design audit** (per `DESIGN_PHASES.md` Phase 3.5) — cross-check schematic against MatekH743 + Pixhawk6X reference designs, flag any deviation requiring justification.

Then Phase 3-exit (re-audit + cruft sweep + 0n:00 retro fold-in pattern from Phase 2-exit).

---

## P0.7 — STOP. Rule-13 gate. Awaiting master adjudication.

### Worker recommends

**SKiDL 2.2.3** as primary; **kicad-cli sch export pdf** for forum-review artifact; **fallback to hybrid (SKiDL + kicad-skip post-processing) or hand-write** if a specific sheet exposes SKiDL limitations.

### Worker has NOT created

- No schematic sheet (`.kicad_sch` other than the smoke-test artefact in `/tmp`)
- No project file (`.kicad_pro`) for novapcb proper
- No SKiDL script for novapcb proper
- No `hardware/kicad/schematic/` directory
- No `sym-lib-table` / `fp-lib-table` for the novapcb project

### Worker HAS created (committable Phase 3 P0 deliverables)

- `tasks/phase-3-p0-schematic-approach.yaml` (contract with `decision_forks_watched` + `escalation_log`)
- `hardware/kicad/PHASE3_P0_REPORT.md` (this report)

### Items requiring master decision

1. **Approve SKiDL as the Phase 3 primary tool** (vs. alternative).
2. **Approve the 8-sub-phase breakdown** (3a-3h per §P0.6) — or revise sheet boundaries.
3. **Approve the hybrid fallback escalation path** — when a sub-phase hits SKiDL limits, Rule-13 stop with the failing-sheet scope.
4. **Confirm the project structure for Phase 3a** — `hardware/kicad/schematic/` directory layout; whether to bundle multiple SKiDL scripts (`generate_3a_mcu.py`, etc.) or one master script with sheet sub-modules.

Awaiting master's call. Once cleared, Phase 3a dispatch starts the per-sheet rhythm.
