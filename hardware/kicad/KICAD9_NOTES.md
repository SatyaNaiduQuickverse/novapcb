# KiCad 9 + tooling notes for novapcb

Committed cross-machine source-of-truth for KiCad-9 / pcbnew / SKiDL / kicad-cli quirks discovered during novapcb development. Promoted from per-machine memory per `CLAUDE.md §9` ("anything load-bearing into a committed doc"). New gotchas land here as Phase 3+/4+ work surfaces them.

Created 2026-05-20 (03:00 retro action item; landed in Phase 3a PR per master directive).

---

## Tooling baseline

| Component | Version | Source | Verified working on `novarobotics64` |
|---|---|---|:---:|
| KiCad GUI | 9.0.2 | `apt` (Debian trixie main) | n/a (no GUI on this Pi) |
| `pcbnew` Python module | 9.0.2 | bundled w/ KiCad apt package, at `/usr/lib/python3/dist-packages/pcbnew.py` | ✓ Phase 2.5 (placement) |
| `kicad-cli` | 9.0.2 | bundled w/ KiCad apt package, at `/usr/bin/kicad-cli` | ✓ Phase 2.5 (`pcb drc`) + Phase 3 P0 (`sch erc`, `sch export pdf`) |
| SKiDL | 2.2.3 | `pip install --user skidl` | ✓ Phase 3 P0 smoke (small circuit) / Phase 3a (netlist) |
| kicad-skip | 0.2.5 | `pip install --user kicad-skip` | candidate for `phase3-render-1`; not yet exercised |

KiCad 9 vs 8: novapcb is KiCad 9 — per `CLAUDE.md §6.1`, confirmed by master 2026-05-20 (escalation #1 in `tasks/phase-2.5-footprint-check.yaml`). Anyone cloning the project should use KiCad 9.x; KiCad 8 cannot read KiCad 9 `.kicad_sch` files reliably.

---

## pcbnew Python API gotchas (Phase 2.5)

### Footprint.Flip — KiCad 9 API change

KiCad 8: `fp.Flip(VECTOR2I, bool)` — second arg was a bool.
KiCad 9: `fp.Flip(VECTOR2I, FLIP_DIRECTION)` — second arg is an enum.

```python
# WRONG (KiCad 8 idiom; segfaults silently on KiCad 9)
fp.Flip(pcbnew.VECTOR2I(...), False)

# CORRECT (KiCad 9)
fp.Flip(pcbnew.VECTOR2I(...), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
```

`FLIP_DIRECTION_LEFT_RIGHT` is the typical "flip to back layer" direction; `FLIP_DIRECTION_TOP_BOTTOM` exists for the other axis.

### Flip requires the footprint to be on the board first

Calling `Flip()` on a `FOOTPRINT` instance BEFORE `board.Add(fp)` causes a silent segfault — `print()` calls after Flip in the same script don't fire (no traceback). Pattern:

```python
# WRONG — segfaults
fp = pcbnew.FootprintLoad(...)
fp.SetPosition(...)
fp.Flip(..., FLIP_DIRECTION_LEFT_RIGHT)
board.Add(fp)

# CORRECT — Add first, then Flip
fp = pcbnew.FootprintLoad(...)
fp.SetPosition(...)
board.Add(fp)
fp.Flip(..., FLIP_DIRECTION_LEFT_RIGHT)
```

### `.kicad_prl` is per-user cache — gitignore

KiCad creates `.kicad_prl` files alongside `.kicad_pro`. The `.prl` (project local) holds user-specific settings (last-zoom, last-window-position, etc.). It MUST be in `.gitignore`; committing it pollutes diffs and causes merge conflicts. (Already in this repo's `.gitignore`.)

### MountingHole footprints have copper-pad keep-outs that DRC flags

`MountingHole.pretty/MountingHole_3.2mm_M3_Pad.kicad_mod` has a 6.4 mm copper pad on all `*.Cu` layers around the drill. DRC will flag any other footprint whose pads overlap this 6.4 mm copper area as `clearance @ 0.0 mm`. This is correct behavior — mounting holes need clearance — but means board outline + placement must inset other footprints by ~3.5 mm from the hole center. Phase 2.5 placement-fit check used 30.5 mm c-to-c hole spacing on a 36 × 36 mm board, giving 2.75 mm edge inset which is at the limit.

### Headless mode requires no DISPLAY

`pcbnew` Python module is fully headless — no `DISPLAY` env var required. Confirmed end-to-end on `novarobotics64` (no X server) for Phase 2.5 board generation.

---

## SKiDL gotchas (Phase 3)

### `generate_schematic()` does NOT scale past trivial circuits

**The big one.** SKiDL 2.2.3's `generate_schematic()` auto-router hangs indefinitely on real MCU sheets. Discovered Phase 3a 2026-05-20:

- P0 smoke test: 2 components (R + C) — `generate_schematic()` produces `.kicad_sch` in seconds. ✓
- Phase 3a MCU sheet: 27 components (STM32H743VITx + decoupling + crystal + reset + boot) — `generate_schematic()` hangs 11+ minutes in the router retry loop (`"Routing failed on attempt 1/2, expanding area by 1.5x"`), no output produced. Killed.

**Phase 3 mode: netlist-only.** Each 3x sub-phase runs `generate_netlist()` (works instantly + cleanly) + SKiDL `ERC()` (works) but NOT `generate_schematic()`. The Python source-of-truth + netlist + SKiDL ERC are the per-sub-phase artifacts.

**Drawn-schematic deferred** — tracked as `docs/OPEN_QUESTIONS.md` `phase3-render-1`. Needed for Phase 6.5 forum review (EEs expect a schematic); not blocking Phase 3.5 / 4 / 5 / 6 (all consume the netlist). Investigation candidates: SKiDL router flags / kicad-skip programmatic / one-time manual KiCad-GUI cleanup / per-small-sheet generation.

**Lesson.** Investigation-phase smoke tests must be realistically scaled to the actual workload — toy 2-component tests prove an API EXISTS, not that it SCALES. Captured for the 04:00 retro as a shared action item.

### `PWR_FLAG` symbols have no footprint and break `generate_netlist()` if added naively

KiCad's `power:PWR_FLAG` is a virtual symbol — netlist-only ERC marker for "this rail is driven." It has no PCB footprint, so SKiDL's netlist generator errors:

```
ERROR: No footprint for PWR_FLAG/#FLG_3V3 added at .../mcu_3a.py:230.
INFO: 3 errors found while generating netlist.
```

Workaround for novapcb's multi-sheet design: omit `PWR_FLAG` in upstream sheets (3a MCU); put them in the Phase 3b power-tree sheet where the actual LDO output drives the rail (the LDO part itself is the OUTPUT power source). The "Input Power pin not driven by any Output Power pins" ERC warnings in 3a-alone are EXPECTED at this sub-phase and resolve when 3b lands.

If a future use does need `PWR_FLAG` in a generator script, the SKiDL pattern is to suppress the footprint requirement — investigate `pwr_flag.footprint = "Virtual:NONE"` or similar at that time.

### `pip install --user` works; no sudo needed

`pip install --user skidl` and `pip install --user kicad-skip` both succeed without sudo. Python 3.13 (Debian trixie default) finds the user packages at `/home/novatics64/.local/lib/python3.13/site-packages/`. No system-state change required.

### Symbol library paths — set `KICAD9_SYMBOL_DIR` env

SKiDL emits five warnings about missing `KICAD*_SYMBOL_DIR` env vars when the standard libraries can't be auto-found:

```
WARNING: KICAD_SYMBOL_DIR environment variable is missing, ...
WARNING: KICAD9_SYMBOL_DIR environment variable is missing, ...
WARNING: KICAD7_SYMBOL_DIR environment variable is missing, ...
WARNING: KICAD6_SYMBOL_DIR environment variable is missing, ...
WARNING: KICAD8_SYMBOL_DIR environment variable is missing, ...
```

Resolution: in `sheets/common.py setup()`, set `os.environ["KICAD9_SYMBOL_DIR"] = "/usr/share/kicad/symbols"` AND append the path to `skidl.lib_search_paths["kicad9"]`. The env var quiets the warnings; the lib_search_paths actually lets SKiDL find symbols. Both needed.

### `skidl_REPL.*` artefacts appear in cwd when running from repo root

SKiDL writes `skidl_REPL.erc` / `.log` to the current working directory when invoked from a script named anything-other-than-the-circuit-name. Gitignored (`skidl_REPL.*` in `.gitignore`). When running the formal `generate.py`, SKiDL uses `generate.*` prefix — those are committed as the audit trail.

---

## `kicad-cli sch` capabilities

| Subcommand | Available | Use |
|---|:---:|---|
| `kicad-cli sch erc` | ✓ | ERC against a `.kicad_sch` |
| `kicad-cli sch export netlist` | ✓ | export netlist from a `.kicad_sch` |
| `kicad-cli sch export pdf` | ✓ | render `.kicad_sch` to PDF (Phase 6.5 forum artefact path) |
| `kicad-cli sch export bom` | ✓ | BOM CSV |
| `kicad-cli sch export svg` | ✓ | SVG render |
| `kicad-cli sch export dxf/hpgl/ps` | ✓ | other vector formats |
| `kicad-cli sch create` | ✗ | **no create subcommand exists** — schematic creation is GUI-only / programmatic-via-SKiDL-or-kicad-skip |

`kicad-cli pcb` has `drc` + `export` (gerbers, drill, STEP, PDF, etc.) — fully covered for Phase 4 layout + Phase 7 fab work.

---

## When you encounter a new gotcha

Add a section here. Keep it terse — "what broke, the WRONG pattern, the CORRECT pattern, why." Future-Claude on Phase 4+ will read this; reverse-engineering the same problem twice is wasted effort.

Don't move existing notes into local Claude memory — that loses the cross-machine + cross-session value. This file is the source of truth.
