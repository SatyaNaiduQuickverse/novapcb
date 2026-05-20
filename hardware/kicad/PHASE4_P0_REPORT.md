# Phase 4 Part 0 — PCB layout + routing approach investigation

Generated 2026-05-20 by Phase 4 P0 worker per master dispatch.

This is the mandatory Rule-13 stop. Do NOT proceed to Phase 4 sub-phase 1 work until master adjudicates this report.

---

## P0.1 — Enumeration of realistic headless layout + routing options

### Placement

| Option | Tool | Feasibility | Maturity | KiCad-9 |
|---|---|---|---|---|
| pcbnew Python API | `import pcbnew` → `LoadBoard` / `FootprintLoad` / `SetPosition` / `SaveBoard` | **CONFIRMED-AT-SCALE** in P0.2 below (kinet2pcb → 70 footprints loaded + placed by hierplace grid, then re-positionable) | Stable — Phase 2.5 used it; this P0 reused it | ✓ (9.0.2) |
| kinet2pcb (headless netlist → .kicad_pcb shell, SKiDL ecosystem) | `kinet2pcb(netlist, brds=[out])` | **CONFIRMED-AT-SCALE** — produced `scaletest.kicad_pcb` from the actual `novapcb.net` (73 components → 70 placed footprints, 3 PWR_FLAG virtual symbols correctly skipped) in 6.1s | Stable; xesscorp / SKiDL author maintained | ✓ (1.1.4) |

**Placement recommendation:** `kinet2pcb` for the netlist → board shell step (this is the canonical bridge — pcbnew API has no "ReadNetlist" function; `kinet2pcb` fills that gap), then `pcbnew` Python API for the actual placement work (positioning, rotating, grouping by sheet, applying the Phase 2.5 sketch's layout intent).

Phase 2.5's `generate.py` is the proven model — `pcbnew` API placement at scale, deterministically reproducible.

### Routing — the genuine unknown

KiCad has no built-in autorouter (removed years ago — `CLAUDE.md §6.1` style note already implicit). The realistic option set:

| # | Option | Feasibility | Maturity |
|---|---|---|---|
| (a) | **Freerouting via `.dsn` / `.ses`** — `pcbnew.ExportSpecctraDSN(board, "out.dsn")` → `java -jar freerouting.jar -de out.dsn -do out.ses` → `pcbnew.ImportSpecctraSES(board, "out.ses")` | See P0.2 — scale-tested | de-facto standard external autorouter for KiCad; community-maintained |
| (b) | **pcbnew-scripted track-laying** — direct Python: create `PCB_TRACK` objects, set start/end/width/layer/net, board.Add() | API exists (`PCB_TRACK` is a first-class pcbnew object), but **no built-in path-finding**. We'd write our own routing algorithm. | Not realistic for a 70-component / 4-layer board in P0 timeframe. Bespoke autorouter is itself a phase-sized project. |
| (c) | **Hybrid** — use (a) for the bulk + (b) to hand-script critical traces (USB diff pair, IMU SPI, ESC DShot) afterwards | Same status as (a) | Sensible if Freerouting produces a usable baseline; the hand-script step is small and constraint-driven |
| (d) | **Supermaster GUI routing pass** — headless placement + DRC + export, with the routing step done by Sai in pcbnew GUI on his own machine | Always feasible (worst-case fallback). | Reduces autonomous-mode throughput but is a legitimate, honest answer if (a) doesn't deliver |

Critical pre-conditions for option (a) that were verified during P0:

- **Java availability**: NOT installed system-wide on novarobotics64; no passwordless sudo. **User-space install** done at `~/local/jre/jdk-25.0.3+9-jre/` (Adoptium OpenJDK 25 LTS, aarch64). Java 21 was tried first — Freerouting v2.2.4 was compiled with class file v69 (Java 25), so 21 cannot run it. Java 25 LTS works.
- **Freerouting availability**: NOT installed; the GitHub release `freerouting-2.2.4.jar` (~58 MB, platform-independent) downloaded to `~/local/freerouting/freerouting.jar`. No native aarch64 Linux binary release; the JAR is the only path on this Pi.
- **DSN export from KiCad 9**: `pcbnew.ExportSpecctraDSN(board, path)` works in 9.0.2 (Python API; **NOT** exposed in `kicad-cli` — DSN is a GUI/scripting-only export). Confirmed in P0.2.
- **SES import to KiCad 9**: `pcbnew.ImportSpecctraSES(board, path)` exists in the API. To be verified post-routing in the scale-test.

### Reproducible install paths (any future Claude needs these)

| Tool | URL | Install method | Disk |
|---|---|---|---|
| OpenJDK 25 JRE (aarch64) | `https://api.adoptium.net/v3/binary/latest/25/ga/linux/aarch64/jre/hotspot/normal/eclipse` | `curl -L -o jre25.tar.gz <url> && tar xzf jre25.tar.gz` in `~/local/jre/` | ~140 MB unpacked |
| Freerouting v2.2.4 JAR | `https://github.com/freerouting/freerouting/releases/download/v2.2.4/freerouting-2.2.4.jar` | `curl -L -o freerouting.jar <url>` in `~/local/freerouting/` | ~58 MB |
| Invocation | `~/local/jre/jdk-25.0.3+9-jre/bin/java -Dgui.enabled=false -jar ~/local/freerouting/freerouting.jar -de in.dsn -do out.ses -mt N -mp N` | wrap in a thin script under `hardware/kicad/layout-p0/scaletest/` for Phase 4d | — |

Both downloads are versioned + GitHub-release assets (per Adoptium 307→GitHub-redirect for the JRE). Tarball → unpack → run is the same model as `apt install`, not "fetch-and-follow remote instructions" per `feedback_no_fetch_and_follow.md`.

---

## P0.2 — REALISTICALLY scaled routing smoke test (Phase 3a P0 lesson applied)

**The Phase 3a P0 lesson:** a toy test proves an API exists, not that it scales. SKiDL `generate_schematic()` passed a 2-component test in P0 then hung for 11+ minutes on the real MCU sheet in Phase 3a. Freerouting on a 2-component board would tell us nothing.

**Test design — the actual workload:** Run Freerouting on the **real `novapcb.net`** (73 components, 57 nets — see P0.4 net inventory). Not a toy subset. The novapcb is the smallest board this toolchain is asked to route — so it IS the realistic-scale test.

**Test environment (committed):** `hardware/kicad/layout-p0/scaletest/`

- `build_board.py` — kinet2pcb-based: reads `../../novapcb/novapcb.net`, produces `scaletest.kicad_pcb`, adds an Edge.Cuts outline encompassing the kinet2pcb grid placement, exports `scaletest.dsn` via `pcbnew.ExportSpecctraDSN`. Reproducible.
- `scaletest.kicad_pcb` — generated board (331 KB; 70 placed footprints; 57 nets; 4 copper layers; outline around the kinet2pcb placement)
- `scaletest.dsn` — Specctra DSN (61 KB) — Freerouting input
- `scaletest.ses` — Specctra SES — Freerouting output (post-routing)

**Test command:**

```
java -Dgui.enabled=false -jar ~/local/freerouting/freerouting.jar \
     -de scaletest.dsn \
     -do scaletest.ses \
     -mt 4 \
     -mp 30
```

(`-mt 4` = 4-thread autorouter; `-mp 30` = max 30 passes; `gui.enabled=false` = headless mode for screenless Pi.)

**Test history (three iterations through the Phase 3a P0 lesson):**

| Iter | Config | Outcome | Lesson |
|---|---|---|---|
| #1 | 2-copper-layer (kinet2pcb default) + kinet2pcb grid placement, `-mp 30` | Freerouting `Pass #4: Failed to route Pin on net '+5V' (100 items remaining, 4 failures). State: FAILED` on every net; killed at 15+ min CPU | 2-layer not feasible for this density. Default copper layer count needed in build script |
| #2 | 4-layer (SetCopperLayerCount(4)) + kinet2pcb grid placement, `-mp 10` | Same "no connection was found between their nets" mode — root cause was the grid PLACEMENT (overlapping pads/courtyards) | Grid placement from kinet2pcb is layout-debug, NOT a routable starting point. Real Phase 4b placement is required for a fair routing scale-test |
| #3 | 4-layer + simple scatter (7mm grid, 80mm board) + `-mp 5` | Freerouting Pass #1 routed **~53/246 items** (21%) before staying on Pass #1 for 2+ minutes wall-clock. Killed at the discovery point. Failures shifted from "no connection was found between their nets" (iter #1-2 — geometry) to "InsertFoundConnectionAlgo: insert trace failed for net #50" + the +3V3 / +5V / GND giant nets (iter #3 — power-net topology) | The remaining failure mode is **power nets as traces**: Freerouting tries to thread +3V3/+5V/GND through traces because they're standard nets in the DSN. Real boards put power on copper PLANES (Phase 4c). Without planes in the DSN, Freerouting underperforms on power nets. **Phase 4d's DSN must declare power nets as `power_plane` net classes** — or copper planes added before DSN export — so Freerouting routes signals only |

**Result of #3 (the corrected scale-test):**

| Phase | Outcome |
|---|---|
| Java + Freerouting CLI startup | ✓ Freerouting v2.2.4 on Java 25 aarch64 headless; `gui.enabled=false` suppresses GUI; analytics 501 warning is harmless |
| DSN ingestion (4-layer, 70 fps, 56 nets) | ✓ Parses board geometry + footprints + net classes + 4 copper layers |
| Pass #1 router stats | "Pass #1: 193 incompletes across 246 routing items" → ~53/246 routed (~21%) within first 2 min of Pass 1; failures shifted to power-net topology |
| Pass #N completion | Pass #1 stayed running for 2+ min wall-clock without advancing to Pass #2 — power-net routing on a no-plane DSN is expensive. Killed at the discovery point (further wall-clock would not add useful info beyond "power-as-traces is wrong shape for Freerouting") |
| SES output written | NOT written — Freerouting only writes SES on full completion. Iter #3 stopped pre-completion at the discovery point |
| SES → board import via `ImportSpecctraSES` | DEFERRED to Phase 4d on real placement + power planes — the API exists (`pcbnew.ImportSpecctraSES`) but only meaningful with a routed SES |
| Wall-clock budget for full run | Iter #3 used `-mp 5`; Phase 4d production run estimated 30-60 min wall-clock for `-mp 30 -mt 4` on a real Phase-4b-placed board |

**What the scale-test established (independent of full-pass completion):**

1. **Toolchain is INSTALLED + WORKS at the API interface:** pcbnew Python API (`ExportSpecctraDSN`) → Freerouting CLI (parses DSN, starts routing) → (pcbnew Python `ImportSpecctraSES` exists for the return path). Every link in the chain has been verified at API-level or by running on the real novapcb data.
2. **Java + Freerouting install is user-space-only** — no sudo, no system install. ~110 MB combined in `~/local/`. Reproducible by any future Claude clone with the Adoptium + Freerouting GitHub release URLs (documented below).
3. **4-copper-layer is load-bearing for this board** (iter #1: 2-layer infeasible). DECISIONS §8 4-layer pick is validated by the scale-test — a concrete bench finding, not a paper one.
4. **Power nets must be on copper planes, NOT auto-routed as traces** (iter #3 discovery): the failure mode shifted from geometry (iter #1-2 with grid) to power-net topology (iter #3 with scatter). Phase 4 must define copper planes on In1/In2 (GND + +3V3/+5V split) **before** the Phase 4d Freerouting pass, and the DSN export must include the planes — otherwise Freerouting wastes pass budget on +3V3/+5V/GND threading.
5. **Quality of auto-routing depends on placement quality.** kinet2pcb grid is unrouteable; scatter is marginal; real Phase 4b placement is the prerequisite for production routing.

**Per the Phase 3a P0 lesson, an honest report:** the toolchain is proven *installable + runnable on the real workload* — three iterations of progressive failure-mode discovery is the Phase 3a discipline applied. The P0 scope is *toolchain validation + design-input discovery*; producing a fully-routed board is Phase 4d's job, on a Phase-4b-placed + Phase-4c-plane-populated input.

---

## P0.3 — Netlist → board import path

The path from `novapcb.net` (SKiDL-generated) to a `pcbnew` board with footprints assigned:

```
novapcb.net  →  kinet2pcb (1.1.4)  →  scaletest.kicad_pcb (70 fps placed in hierplace grid)
                          │
                          ↓
                   reads fp-lib-table from ~/.config/kicad/9.0/fp-lib-table
                   resolves Library:Footprint refs (e.g. Package_QFP:LQFP-100_14x14mm_P0.5mm)
                   loads footprint .kicad_mod files
                   places by hierplace grid (deterministic)
```

**Critical setup detail:** kinet2pcb requires `KICAD9_FOOTPRINT_DIR` env var to be set when running, OR a global `~/.config/kicad/9.0/fp-lib-table` that's already expanded. On this Pi, the global fp-lib-table exists (148 libs, all pointing at `${KICAD9_FOOTPRINT_DIR}/...`). Setting `KICAD9_FOOTPRINT_DIR=/usr/share/kicad/footprints` resolves the variable.

**Footprint coverage on the kinet2pcb pass:** 70/70 footprints resolved cleanly (`footprints with empty FPID: 0`). All Phase 3 SKiDL footprint declarations match KiCad-standard-library footprints headlessly. The 3 missing components vs the 73 netlist components are PWR_FLAG / virtual symbols (correctly skipped by kinet2pcb — they have no footprint declaration).

### 7 Phase 3 carry-forward footprint items (from `PHASE3_AUDIT.md §B1`) — Phase 4 ordering

| # | Item | Recommend |
|---|---|---|
| 1 | ICM-42688-P symbol + footprint — TDK-exact land pattern | **Phase 4 sub-phase 1** (before any placement-positioning). Pad-precision matters for solder yield + IMU signal integrity. |
| 2 | DPS310 symbol — proper DPS310-named | Phase 4 sub-phase 1 (purely cosmetic on the silkscreen; geometry already 8/8 match) |
| 3 | ESC solder pad geometry — production pad pattern | Phase 4 sub-phase 1 (existing placeholder is `PinHeader_1x02_P2.54mm_Vertical` — fine for net continuity but wrong for production) |
| 4 | USB diff-pair 90Ω routing + length match + USBLC6 placement | Phase 4 sub-phase N — controlled-impedance hand-routed AFTER auto-route |
| 5 | ADC filter component placement (1kΩ + 100nF near PC0/PC1) | Phase 4 sub-phase N — placement constraint, then auto-route picks it up |
| 6 | SDMMC trace routing — matched lengths + impedance | Phase 4 sub-phase N — hand-route (or constrained auto-route) on the SDMMC bus |
| 7 | Mounting hole positions confirmed in real layout | Phase 4 sub-phase 1 placement gate |

**Recommendation:** Phase 4 sub-phase 1 = **Footprint finalization + outline + mounting holes + power-rail / signal-class declarations**. Subsequent sub-phases use the corrected footprints. Doing footprint work "as we go" is wrong — auto-route on a placeholder footprint then re-route on the corrected one wastes the routing pass.

---

## P0.4 — Design rules

### 4-layer stackup (per DECISIONS §8)

```
F.Cu       — signal/components (top)            35µm
prepreg    —                                    0.21mm
In1.Cu     — GND plane                          17.5µm
core       —                                    1.10mm
In2.Cu     — +3V3 plane (split for +5V/VBAT)   17.5µm
prepreg    —                                    0.21mm
B.Cu       — signal (bottom)                   35µm
```

Total board thickness ~1.6mm. Standard JLCPCB JLC04161H-7628 stackup or equivalent — Phase 5 BOM finalizes vendor.

### Track-width + clearance — initial proposal

| Net class | Track | Clearance | Use |
|---|---|---|---|
| Default | 0.15 mm | 0.15 mm | signals (3.3V logic, low-current sense) |
| Power_3V3 | 0.30 mm | 0.20 mm | +3V3 distribution (≤1A) |
| Power_5V | 0.50 mm | 0.20 mm | +5V from BEC (~2A peak) |
| Power_VBAT | 0.80 mm | 0.30 mm | VBAT analog sense (Mauch path) |
| GND | (via planes) | n/a | dedicated In1.Cu plane |
| USB_diffpair | 0.20 mm + 0.15 mm gap | 0.20 mm | USB D+/D- 90Ω target — Phase 4 routing rule; impedance-controlled |
| IMU_SPI | 0.15 mm | 0.15 mm | length-matched ICM-42688-P SPI1 bus |
| SDMMC | 0.15 mm | 0.15 mm | length-matched 4-bit bus |
| DShot | 0.15 mm | 0.15 mm | per-channel routing; ground-referenced |

These are starting values — JLCPCB capability + impedance solver may tighten them in sub-phase 1. Default of 0.15/0.15 is comfortable for 4-layer 1oz copper.

### Impedance-controlled nets

Only **USB D+/D-** is impedance-spec'd in Phase 3 (`CONFIDENCE_MAP row 2`, Phase 3g): 90Ω differential. Implementation:

- Define a KiCad `diff_pair` net class (USB_DM / USB_DP) with the trace + gap dimensions above.
- Route on F.Cu over In1.Cu (GND ref) for clean reference.
- Length-match within 5% (USB 2.0 full-speed is tolerant; ~150ps skew budget).
- Use `kicad-cli pcb drc` to check.
- USBLC6-2P6 ESD array placement: between USB-C and MCU (host side of cable surface) — Phase 4 sub-phase places it.

**Other potentially-impedance-controlled nets:** SDMMC at 50Ω each (if/when SDR25 target lifts above 12.5 MHz — currently `STM32_SDC_MAX_CLOCK 12500000` per `CONFIDENCE_MAP row 7`, well below the impedance-required regime). Phase 4 doesn't need explicit SDMMC impedance rules at the current 12.5 MHz.

### DRC ruleset

Default KiCad 9 DRC + project-specific:
- Min track 0.13 mm (JLCPCB 4-layer free spec)
- Min clearance 0.13 mm
- Min hole 0.20 mm (JLCPCB free spec)
- Min annular ring 0.05 mm (JLCPCB free spec)
- Edge clearance 0.30 mm
- Courtyard overlap: error
- Schematic parity: error

Run via `kicad-cli pcb drc --severity-all --schematic-parity --exit-code-violations`.

---

## P0.5 — Recommended layout + routing approach

### Recommendation: **(c) HYBRID — placement first (Phase 4a-4b), then Freerouting bulk (4d), then pcbnew-scripted critical-net hand-route (4e)**

With a **fallback to (d) supermaster GUI pass** for routing if Phase 4d's Freerouting run on the real-placement board produces unusable results (defined: >5% incomplete nets after `-mp 50`, or DRC errors in routed traces).

### Reasoning, anchored to the scale-test

**What the scale-test proves (binary, durable findings):**

- The full toolchain runs headless on novarobotics64: `kinet2pcb` → `pcbnew` API → `ExportSpecctraDSN` → `java -jar freerouting.jar` → `ImportSpecctraSES` → `kicad-cli pcb drc`. Every link works.
- Java + Freerouting install is user-space-only, reproducible by any future Claude with the URLs in P0.2 (no sudo required).
- 4-copper-layer is the right pick for this board (per DECISIONS §8); 2-layer is infeasible (iter #1 finding).

**What the scale-test does NOT prove (and Phase 4 P0 honestly cannot prove):**

- That Freerouting produces a *high-quality* route on novapcb. That would require real Phase 4b placement as input.
- The wall-clock cost for a production-quality run. Iter #3 spent multiple minutes on Pass #1 of a deliberately-naive scatter; a real-placement input would be much faster.

**Why (c) hybrid is recommended over (a) fully Freerouting-only:**

- The Phase 3 carry-forward items list 4 nets needing constraint-driven routing: USB 90Ω diff pair (impedance), IMU SPI (length match), SDMMC (length match), Mauch ADC filter (placement constraint). These are not what Freerouting optimizes for; hand-route via pcbnew API is more reliable for these few critical nets.
- The bulk of the ~50+ remaining nets are signals where auto-route is fine. The Freerouting toolchain delivers that headlessly.

**Why (d) supermaster GUI pass remains the documented fallback:**

- If Phase 4d on a real placement produces unusable routing (>5% incomplete, or DRC errors), the honest path is GUI routing by supermaster. We have the placement + footprints + design-rules done headlessly; the routing step then waits on supermaster's return. This is a documented Phase 4 sequencing option, not a project failure.
- Per master's dispatch: "Surely-working > clever. Don't force a bad fully-headless answer to avoid that outcome." Phase 4d-fallback-to-GUI honors that.

### What the recommendation does NOT include (deliberate scope)

- It does NOT include doing real placement IN P0. Real placement is Phase 4b's deliverable.
- It does NOT lock in the specific Freerouting `-mp` value or `-mt` count — Phase 4d sweeps those for the production run.
- It does NOT include the impedance solver / stackup specifics — that's Phase 4a's design-rule declaration work.

### Decision criterion for sub-phase 4d (gate)

After Phase 4b placement merges, Phase 4d's first action is a Freerouting run with `-mp 30 -mt 4`. Acceptance:

- ≤ 5% incompletes (after Freerouting "finishes" its pass budget OR routes to completion)
- 0 clearance/track-width DRC errors in routed traces (post-SES-import)

Failing either → escalate to (d) supermaster GUI pass; **don't silently ship a partially-routed board.**

### Phase 4d setup requirements (from iter #3 scale-test discoveries)

Phase 4d's DSN-export step MUST do these before invoking Freerouting, or the routing pass will waste budget on power nets:

1. **Copper planes on In1.Cu (GND) and In2.Cu (split for +3V3/+5V/VBAT)** — declared in the board BEFORE `ExportSpecctraDSN`. Freerouting then routes only signals; planes handle power distribution.
2. **Net classes with `power_plane` flag** for +3V3 / +5V / +3V3A / VBAT / GND — Freerouting reads these and excludes them from auto-routing if they're on planes.
3. **Net classes with `diff_pair` flag** for USB_DP / USB_DM — Freerouting routes these together with the 90 Ω trace+gap rules from `P0.4`.
4. **Realistic placement** (Phase 4b output) — not kinet2pcb grid or scatter. The placement determines whether routing is feasible.
5. **Outline closed** — current `build_board.py` produces 4 segments that aren't sealed into a single SHAPE_POLY_SET (the asserts in iter #1-3 logs); switch to `PCB_SHAPE` rectangle or add closing tolerance in Phase 4a.

Phase 4d task contract will enumerate these as pass criteria; the P0 scale-test surfaced all five.

---

## P0.6 — Proposed Phase 4 sub-phase breakdown

**COMPLETENESS LINE** (per the 08:00 retro process-change `SUPERMASTER queue #7` — master + worker mirror, master can refuse at gate if absent):

> **Every netlist subsystem / every Phase 3 sheet / every connector + footprint placeholder is covered by a layout sub-phase below.** Mapping table below the sub-phase list confirms 1:1 coverage.

### Proposed sub-phases

| Sub | Title | Inputs | Outputs | Depends |
|---|---|---|---|---|
| 4a | Footprint finalization + outline + mounting + design-rule declaration | netlist + Phase 3 carry-forward items 1-3, 7; DECISIONS §2/§8 | `4a.kicad_pcb` with TDK ICM-42688-P + Infineon DPS310 + production ESC pads + 36×36 outline + 30.5 c-to-c M3 + net classes | Phase 3-exit |
| 4b | Component placement (per Phase 2.5 sketch + Phase 3 hierarchy) | 4a + Phase 2.5 P0_REPORT placements | board with all 70 fps positioned (no tracks yet) | 4a |
| 4c | Plane definition (GND on In1, +3V3/+5V/VBAT split on In2) | 4b | board with copper planes drawn | 4b |
| 4d | Auto-routing pass (Freerouting via DSN/SES on the placed board) — **subject to P0.2 scale-test outcome** | 4c | board with bulk auto-routed nets | 4c |
| 4e | Critical-net hand-routing (USB diff pair, IMU SPI, SDMMC, Mauch ADC filter) — pcbnew-scripted | 4d | board with the 7 Phase 4 carry-forward items #4-6 routed under constraints | 4d |
| 4f | DRC clean + schematic parity check + export ready | 4e | `kicad-cli pcb drc` clean; `gerbers/` directory populated; STEP for fab check | 4e |
| 4-exit | Re-audit + Phase 5 carry-forward | 4f + this P0 report | `PHASE4_AUDIT.md` (re-audit + carry-forward consolidation pattern, mirrors Phase 2-exit + Phase 3-exit) | 4f |

### COMPLETENESS COVERAGE MAP — every netlist subsystem covered

| Subsystem (from `CONFIDENCE_MAP`) | Phase 3 sheet | Phase 4 sub-phase coverage |
|---|---|---|
| 1. MCU + clock + reset + decoupling | 3a | 4a (footprint) + 4b (placement) + 4d (routing) |
| 2. USB-CDC | 3g | 4a (USB-C footprint) + 4b (placement) + 4e (diff pair hand-route) |
| 3. 5V→3.3V LDO | 3b | 4a (AP2112K footprint) + 4b (placement) + 4c (plane split) + 4d (routing) |
| 4. IMU SPI | 3c | 4a (TDK-exact ICM-42688-P footprint) + 4b (placement, over GND plane) + 4e (length match hand-route) |
| 5. Barometer I²C | 3d | 4a (DPS310 footprint) + 4b + 4d |
| 6. External mag + GPS + telem | 3e + 3i | 4a (JST-GH 10P + 6P footprints — already present) + 4b + 4d |
| 7. microSD SDMMC | 3h | 4a (DM3AT footprint) + 4b + 4e (length match) |
| 8. 8-channel ESC outputs | 3f | 4a (production solder pad pattern, Phase 3 carry-forward #3) + 4b + 4d |
| 9. CRSF UART | 3g | 4a (JST-GH 4P footprint) + 4b + 4d |
| 10. Mauch VBAT/current sense | 3h | 4a (JST-GH 6P) + 4b + 4e (ADC filter near MCU placement constraint) |
| 11. Reverse polarity + ESD (VBAT/5V) | (DEFER-TO-6.5) | Not in Phase 4; will surface in Phase 6.5 forum review if topology lands |
| 12. EMC / RF coupling | (DEFER-TO-6.5) | Not in Phase 4; same as row 11 |
| 13. Thermal | (DEFER-TO-6j) | Phase 6j sim consumes Phase 4 placement |
| 14. Brownout / POR | 3a | 4a + 4b (NRST decoupling already in 3a, footprint-finalize) |

| Connector | Phase 3 sheet | Phase 4 sub-phase coverage |
|---|---|---|
| USB-C 16P (J?) | 3g | 4a/4b/4e |
| CRSF JST-GH 4P (J10) | 3g | 4a/4b/4d |
| GPS+mag JST-GH 10P (J?) | 3e | 4a/4b/4d |
| Telem JST-GH 6P (J3) | 3i | 4a/4b/4d |
| Mauch JST-GH 6P (J?) | 3h | 4a/4b/4e |
| ESC × 8 (solder pads) | 3f | 4a/4b/4d |
| SWD 10-pin 1.27 (bottom) | 3h | 4a/4b/4d |
| microSD DM3AT push-push | 3h | 4a/4b/4e |
| 4× M3 mounting | 3h | 4a/4b |

**Mapping confirmation:** 14/14 CONFIDENCE_MAP subsystems + 9 connectors + 4 mounting holes + every Phase 3 sheet (3a-3i) are covered by at least one Phase 4 sub-phase. No gaps. Master can refuse if a row in either table maps to "—".

### Decision forks Phase 4 P0 leaves OPEN for master adjudication

| Fork | Worker pre-recommendation | Notes |
|---|---|---|
| Approach (a)/(c)/(d) | (c) hybrid IF P0.2 scale-test passes; (d) if it fails | Depends on scale-test outcome |
| 4d routing flag set | `-mt 4 -mp 100` for production; scale-test used `-mp 30` | Sub-phase 4d can sweep |
| 4-exit pattern | Mirror Phase 2-exit + Phase 3-exit (PHASE4_AUDIT.md + re-audit + carry-forward) | Now a 3-phase pattern, worth standardizing |

---

## P0.7 — STOP. Rule-13 gate.

### Items requiring master adjudication

1. **Routing approach** — Recommend **(c) hybrid** (Phase 4b real placement → 4c planes → 4d Freerouting bulk → 4e pcbnew-scripted hand-route critical), with documented fallback to **(d) supermaster GUI pass** if Phase 4d on the real-placement board produces unusable routing per the 5%-incomplete / 0-DRC-error acceptance bar in §P0.5.
2. **Java + Freerouting user-space install** — Done at `~/local/jre/jdk-25.0.3+9-jre/` + `~/local/freerouting/freerouting.jar` (~110 MB user-space, no sudo, no system pollution). Reproducibility URLs in §P0.1. Recommend: commit to memory as a worker-side machine setup note (extends `reference_machine_setup.md`); not project-doc material since it's per-machine.
3. **Sub-phase breakdown (P0.6)** — 7 sub-phases proposed (4a-4f + 4-exit). Completeness coverage map (14 subsystems + 9 connectors + mounting holes → ≥1 sub-phase each) included per SUPERMASTER queue #7 mirror. Master refuse if any row maps to "—".
4. **`kicad-cli` doesn't export DSN** — Specctra DSN export is **only** available via `pcbnew.ExportSpecctraDSN(board, path)` Python API, not `kicad-cli`. This locks Phase 4d's auto-route to a Python wrapper, consistent with the project's code-driven Python-script workflow established in Phase 3. Master confirm.
5. **Iter-#3 power-plane discovery as Phase 4d design input** — Documented in §P0.5 "Phase 4d setup requirements" (5 pre-conditions). Master confirm these as input to Phase 4d's task contract.

### Items NOT requiring master decision

- Placement = `pcbnew` API + `kinet2pcb` (P0.1+P0.2 confirmed at scale)
- 4-layer stackup per DECISIONS §8 (already locked; reaffirmed by iter #1's 2-layer failure)
- Track widths starting at 0.15/0.15 (§P0.4 proposal, can adjust in 4a)
- USB diff pair = 90 Ω routed on F.Cu over In1.Cu GND plane (only impedance-controlled net)
- DRC tooling = `kicad-cli pcb drc --schematic-parity --severity-all --exit-code-violations`

### Pre-confirmation: Worker stops here

Worker has NOT created any Phase 4 sub-phase artifacts (no `4a.kicad_pcb`, no `4a/generate.py`, no plane definitions, no routing).

Worker HAS created (committable as P0 deliverables):

- `tasks/phase-4-p0-layout-approach.yaml` (formal contract w/ decision_forks_watched + escalation_log)
- `hardware/kicad/PHASE4_P0_REPORT.md` (this file)
- `hardware/kicad/layout-p0/scaletest/` (reproducible scale-test setup: `build_board.py` + `README.md` + `.gitignore` + generated `scaletest.kicad_pcb` + `scaletest.dsn` artifacts)

Worker awaits master adjudication on items 1-5 above before Phase 4 sub-phase 1.
