# Phase 2.5 Part 0 — setup gate report

Generated 2026-05-20 by Phase 2.5 worker per master dispatch.

This is the mandatory Rule-13 stop. Do NOT proceed to Part 1 work until master confirms the items below.

---

## P0.1 — KiCad install (status: ALREADY INSTALLED — Rule-13 escalation #1)

**Surprise finding:** KiCad is already installed on `novarobotics64` via `apt`, and it's **version 9.0.2**, not the KiCad 8 master's contract assumed.

| Property | Value |
|---|---|
| Method | apt (Debian repo) |
| Version | `9.0.2+dfsg-1` |
| Source repo | `http://deb.debian.org/debian trixie/main arm64` |
| Install size (total) | 570 MB (`/usr/share/kicad`) |
| Footprint libs size | 176 MB (`/usr/share/kicad/footprints`) |
| Symbol libs | present (`kicad-symbols 9.0.2-1`) |
| Templates | present (`kicad-templates 9.0.0-1`) |
| Demos | present (`kicad-demos 9.0.2+dfsg-1`) |
| `kicad-cli` | available at `/usr/bin/kicad-cli`, version 9.0.2 |

**Root cause:** `novarobotics64` is on **Debian 13 "trixie"** (per `/etc/os-release`), not Bookworm. Trixie ships KiCad 9 in main; Bookworm (which master's contract implicitly assumed) ships KiCad 7.

**No install action was taken.** Sudo would have required a password (passwordless sudo NOT configured on this Pi) — but no install was needed since the package was already present from prior provisioning.

**Memory baseline note:** `reference_machine_setup.md` did not record KiCad as installed. That memory predates this discovery; should be updated after master adjudication.

### Escalation: CLAUDE.md §6.1 says "KiCad 8 default"

> `CLAUDE.md §6.1`: "KiCad sources committed in plain-text S-expression form (KiCad 8 default)."

That line was written when CLAUDE.md was bootstrapped on 2026-05-18 (master earlier was on Bookworm). Reality moved: this Pi has KiCad 9. Implications:

- **File-format forward-compatibility:** KiCad 9 reads KiCad 8 files; KiCad 8 may NOT read KiCad 9 files (forward-incompatible). If we commit KiCad-9-generated `.kicad_pcb`, anyone on KiCad 8 can't open them.
- **Currently single-developer:** Only worker on `novarobotics64` is making KiCad files. Master (on `novaedge1`) may or may not have KiCad; supermaster (off for this autonomous window) likely uses GUI on their own machine.
- **Python API:** `pcbnew` Python module on KiCad 9 has the same basic shape as KiCad 8 (NewBoard / FootprintLoad / SaveBoard), but some method signatures differ. Scripts written against 9 may not run on 8 unchanged.

**Options for master adjudication:**

| Option | Pros | Cons |
|---|---|---|
| **(A) Use KiCad 9** + update CLAUDE.md §6.1 "KiCad 9 default" | Simplest. Trixie ecosystem-native. No install gymnastics. | Anyone on Bookworm/older can't open files without upgrading. |
| (B) Force-install KiCad 8 via flatpak or pinning older repo | Honors CLAUDE.md §6.1 as-written. | Adds install complexity + diverges from trixie's package management. Need sudo (password gate). Maintenance cost. |
| (C) Use KiCad 9 but only commit 8-compatible file format | Avoids the version-pin issue | Brittle — KiCad 9 doesn't have a "save as 8" mode that's guaranteed lossless. |

**Worker recommendation: (A).** CLAUDE.md was written when trixie-on-this-Pi was unclear; reality moved. Update §6.1 to "KiCad 9 default" with a note that anyone on KiCad 8 needs to upgrade. Single-developer-novarobotics64 makes this low-risk.

---

## P0.2 — headless KiCad approach (status: CONFIRMED)

Worker has no GUI on `novarobotics64`. Verified the headless workflow end-to-end:

### Imports check

```
$ python3 -c "import pcbnew; print('pcbnew.Version():', pcbnew.Version()); print('module:', pcbnew.__file__)"
pcbnew.Version(): 9.0.2
module: /usr/lib/python3/dist-packages/pcbnew.py
```

`pcbnew` Python module is importable headlessly. No `DISPLAY` env required.

### End-to-end test

```python
import pcbnew
b = pcbnew.NewBoard("/tmp/headless_test.kicad_pcb")
lqfp = pcbnew.FootprintLoad("/usr/share/kicad/footprints/Package_QFP.pretty", "LQFP-100_14x14mm_P0.5mm")
lqfp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(15.25), pcbnew.FromMM(15.25)))
b.Add(lqfp)
pcbnew.SaveBoard("/tmp/headless_test.kicad_pcb", b)
```

Result: clean execution, 27,462-byte `.kicad_pcb` file produced. Confirmed pcbnew API works headless for Part 1's placement work.

### Tooling matrix

| Tool | Use | Available? |
|---|---|:---:|
| `pcbnew` Python API | Board/footprint scripting (create + place + save) | ✓ (`/usr/lib/python3/dist-packages/pcbnew.py`) |
| `kicad-cli` | DRC, gerber/STEP export, rendering | ✓ (`/usr/bin/kicad-cli`, 9.0.2) |
| KiCad GUI | n/a (no DISPLAY on this Pi) | n/a |

**Workflow confirmed for Part 1:** scripted board generation via `pcbnew` API + DRC/rendering via `kicad-cli`. No GUI dependency.

---

## P0.3 — project structure proposal

Proposed layout under `hardware/kicad/footprint-check/`:

```
hardware/kicad/footprint-check/
├── P0_REPORT.md              # this file (setup gate report)
├── generate.py               # pcbnew API script — AUTHORITATIVE SOURCE
├── footprint-check.kicad_pcb # generated by generate.py — committed for diff-reviewability
├── footprint-check.kicad_pro # KiCad project file (minimal, enables GUI open if desired)
├── notes.md                  # Part 1 findings (fit assessment + reasoning)
└── README.md                 # how to regenerate + how to view in GUI
```

### Design decisions in this layout

1. **`generate.py` is the authoritative source.** The `.kicad_pcb` is its output, regeneratable from scratch with `python3 generate.py`. This matches the project's code-driven philosophy (`CLAUDE.md §6.1`) — board files are reproducible artifacts, not hand-edited binaries. Anyone can re-run the script and get a bit-identical `.kicad_pcb`.

2. **Commit the `.kicad_pcb` output anyway.** KiCad files are text S-expression in 9.x; they diff well in PR review and let a reviewer open them in KiCad GUI without re-running the script. This is the same pattern as committing generated `BUILD_BASELINE.md` numbers (text artifacts of a reproducible process).

3. **No in-repo footprint library** initially. All 8 component classes have suitable footprints in KiCad's standard libraries (per P0.4). If a custom footprint is genuinely needed (e.g. production ICM-42688-P with TDK-specific pad geometry), add `hardware/kicad/footprint-check/lib/` then — but Phase 2.5 scope is placement-only, generic geometries suffice.

4. **`README.md`** documents the regenerate workflow (`cd hardware/kicad/footprint-check && python3 generate.py && kicad-cli pcb export ...`) so Phase 3 inherits a clear handoff.

5. **`notes.md`** is the Part 1 deliverable — fit assessment, per-component placement reasoning, tight spots. Master's contract spec.

**Master adjudication needed:** approve this layout or propose changes before Part 1 creates files.

---

## P0.4 — footprint availability inventory

Master listed 8 major component classes for inventory. Each grep'd against `/usr/share/kicad/footprints/`:

| # | Component | Package | KiCad standard-lib footprint | Status |
|---|---|---|---|:---:|
| 1 | STM32H743VIT6 | LQFP-100 14x14mm 0.5mm pitch | `Package_QFP.pretty/LQFP-100_14x14mm_P0.5mm.kicad_mod` | ✓ exact |
| 2 | ICM-42688-P | LGA-14 2.5x3mm 0.5mm pitch (TDK InvenSense datasheet) | `Package_LGA.pretty/LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y.kicad_mod` | ⚠ generic-geom-match — sub-fork (see below) |
| 3 | DPS310 | LGA-8 2x2.5mm 0.65mm pitch (Infineon datasheet) | `Package_LGA.pretty/Bosch_LGA-8_2x2.5mm_P0.65mm_ClockwisePinNumbering.kicad_mod` | ✓ exact-geom-match (commonly reused for DPS310 by ArduPilot-class designs; same body as BMP280-family) |
| 4 | USB-C receptacle | 16-pin or 24-pin | `Connector_USB.pretty/` — multiple options (HRO_TYPE-C-31-M-12, GCT_USB4085, GCT_USB4110, etc.) | ✓ multiple vendor options — pick compact mid-mount for Part 1 |
| 5 | microSD push-push socket | standard µSD | `Connector_Card.pretty/microSD_HC_Hirose_DM3AT-SF-PEJM5.kicad_mod` | ✓ DM3AT is common push-push variant |
| 6 | 4× JST-GH connectors (Pixhawk std) | per `DECISIONS §7` | `Connector_JST.pretty/JST_GH_SM{03,05,06,07,08,09,10}B-GHS-TB_…_Horizontal.kicad_mod` — full family | ✓ all standard pin counts available |
| 7 | 8× ESC output (JST-SH or solder pads) | per `hwdef.dat` 8-channel cap | `Connector_JST.pretty/JST_SH_…` — 1x04, 1x07, 1x09, 1x13, 1x14, 1x15 variants present | ✓ partial — Part 1 picks 2× 4-pin or scheme TBD per master |
| 8 | SWD debug header | 2x5 1.27mm Cortex standard | `Connector_PinHeader_1.27mm.pretty/PinHeader_2x05_P1.27mm_Vertical.kicad_mod` | ✓ exact |

### Sub-fork: ICM-42688-P footprint

ICM-42688-P (TDK InvenSense) is a LGA-14 in a 2.5mm × 3mm body with 0.5mm pitch. KiCad's standard `Package_LGA.pretty` has:

- `LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y.kicad_mod` — generic 3×2.5 outline, 0.5 pitch, 3×4 border pad arrangement. Matches ICM-42688-P body geometry under rotation.
- `Bosch_LGA-14_3x2.5mm_P0.5mm.kicad_mod` — Bosch-specific (wrong vendor for our part, but same geometry).

**For Phase 2.5 placement-fit check**, the generic 3×2.5 footprint is acceptable — we only need the right body outline + pad area to verify it fits in the 30.5×30.5 envelope. **For Phase 4 production layout**, a TDK-specific footprint drawn from the InvenSense datasheet is what should ship — pad-precision matters for solder yield.

This is a real REMOVE-vs-DEFER style judgement, but lighter — it's "use generic now (Phase 2.5)" with an explicit "draw custom at Phase 4" follow-up. Documented in the contract `decision_forks_watched.icm42688p-footprint`.

### Custom-footprint candidates for future PRs

None for Phase 2.5. For Phase 4 production layout:
- ICM-42688-P: draw TDK-precision footprint.
- Possibly: custom STM32H743VIT6 if KiCad standard LQFP-100 pad-precision doesn't match ST's recommended.
- All others: standard-lib footprints are production-quality.

---

## P0.5 — STOP. Rule-13 gate. Awaiting master adjudication.

### Items requiring master decision before Part 1

1. **KiCad 9 vs 8 fork (escalation_log #1):** Recommend (A) use KiCad 9, update CLAUDE.md §6.1 to reflect reality. Master adjudication needed.
2. **Project structure (P0.3):** Layout proposed; master approve or revise.
3. **ICM-42688-P footprint (sub-fork):** Use generic LGA-14 3×2.5 P0.5 for Phase 2.5 placement-fit; draw custom at Phase 4. Master confirm.

### Items NOT requiring master decision (worker classifications, sound per the contract)

- pcbnew Python API workflow (confirmed working, no fork)
- KiCad install method (already installed, no action)
- Footprint availability for items 1, 3-8 (all standard-lib hits)
- No in-repo footprint library needed initially (P0.4 inventory complete)

### Pre-confirmation: Worker stops here.

Worker has NOT created:
- `hardware/kicad/footprint-check/generate.py`
- `hardware/kicad/footprint-check/footprint-check.kicad_pcb`
- `hardware/kicad/footprint-check/footprint-check.kicad_pro`
- `hardware/kicad/footprint-check/notes.md`
- `hardware/kicad/footprint-check/README.md`

Worker HAS created (committable as Part 0 deliverables):
- `tasks/phase-2.5-footprint-check.yaml` (contract with formal `decision_forks_watched` + `escalation_log` blocks per Phase 2-exit retro action item #2)
- `hardware/kicad/footprint-check/P0_REPORT.md` (this report)

Awaiting master decisions on items 1-3 above. Will resume at Part 1 after master ping.
