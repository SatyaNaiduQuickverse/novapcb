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
| kinet2pcb | 1.1.4 | `pip install --user kinet2pcb` (SKiDL ecosystem, xesscorp) | ✓ Phase 4 P0 (netlist → .kicad_pcb headless) / Phase 4a (board scaffolding) / Phase 4b placement |
| OpenJDK 25 JRE (aarch64) | 25.0.3+9 (LTS) | user-space tarball at `~/local/jre/jdk-25.0.3+9-jre/` — see `PHASE4_P0_REPORT.md §P0.1` install table | ✓ Phase 4 P0 (Freerouting runtime) |
| Freerouting | v2.2.4 | user-space JAR at `~/local/freerouting/freerouting.jar` — see `PHASE4_P0_REPORT.md §P0.1` install table | ✓ Phase 4 P0 (DSN parse + auto-route ingest) |

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

### `Net('name')` creates a NEW net even if the name exists (Phase 3b lesson)

**Silent topology bug.** SKiDL's `Net('+3V3')` constructor creates a new Net object even when another Net with the same name already exists in the default Circuit. It auto-appends `_1`, `_2` to disambiguate (`+3V3`, `+3V3_1`, ...). Across sheet modules, this means:

```python
# WRONG — two sheets both call Net('+3V3'); result: TWO separate nets
# in the netlist (+3V3 and +3V3_1), no electrical connection between them.
# In novapcb's case: MCU VDD pins on +3V3, LDO VOUT on +3V3_1 — power
# wouldn't reach the MCU on real silicon.

# sheet_a.py:
P3V3 = skidl.Net('+3V3')
mcu['VDD'] += P3V3

# sheet_b.py:
P3V3 = skidl.Net('+3V3')   # NEW net, named '+3V3_1' in netlist
ldo['VOUT'] += P3V3
```

**Correct pattern: `skidl.Net.fetch('name')`.** It looks up the existing Net by name and returns it; creates new only if absent.

```python
# CORRECT — fetch returns the singleton Net by name. Both sheets get
# the SAME Net instance; netlist has only '+3V3'.

# sheets/common.py:
def n(name):
    return skidl.Net.fetch(name)

# sheet_a.py + sheet_b.py both:
P3V3 = n('+3V3')   # same instance in both sheets
```

novapcb wraps this as `n()` in `sheets/common.py` and uses it for every shared rail (`+3V3`, `+3V3A`, `+5V`, `VBAT`, `GND`). Verify by grepping the generated netlist for unique `+RAIL` names — any `_1` suffix means a duplicate-net bug.

### `PWR_FLAG` no-footprint error workaround (Phase 3b lesson)

SKiDL's default `empty_footprint_handler` errors on any part without a footprint, but `PWR_FLAG` is a virtual netlist-only ERC marker that has no PCB footprint by design. Override the handler in your setup:

```python
def _virtual_part_footprint_handler(part):
    if getattr(part, "name", "") == "PWR_FLAG":
        return  # silently accept
    # fall through to default error for real parts
    from skidl.logger import active_logger
    active_logger.raise_(ValueError, f"No footprint for {part.name}/{part.ref}")

skidl.empty_footprint_handler = _virtual_part_footprint_handler
```

novapcb does this in `sheets/common.py setup()`. The override preserves the "real part missing footprint" check.

### KiCad ERC pin-conflict on POWER-OUT pins (Phase 3b lesson)

KiCad's ERC allows only ONE `POWER-OUT` pin per net. Both an LDO's `VOUT` pin AND a `PWR_FLAG` are `POWER-OUT` pins; putting both on the same net produces:

```
ERC ERROR: Pin conflict on net +3V3, POWER-OUT pin 1/~ of PWR_FLAG/#FLG_3V3
           <==> POWER-OUT pin 5/VOUT of AP2112K-3.3/U2
           (POWER-OUT connected to POWER-OUT)
```

**Rule for the novapcb power tree:**
- Net DIRECTLY driven by a `POWER-OUT` pin (LDO output, regulator output): **NO PWR_FLAG**. The pin itself is the source.
- Net driven THROUGH passives (ferrite, 0R, inductor) from a `POWER-OUT` pin: **PWR_FLAG needed**. Passives don't propagate the POWER-OUT attribute through ERC's net analysis.
- Net whose real source lives in another sheet (e.g. `+5V` from the BEC connector in 3h): **PWR_FLAG needed** in the consuming sheet until the source sheet lands.

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

## pcbnew Python API gotchas (Phase 4c)

### ZONE.SetOutline(SHAPE_POLY_SET) — holds outline by REFERENCE not by value

KiCad 9 SWIG binding: `zone.SetOutline(outline)` stores a reference to the SHAPE_POLY_SET, NOT a copy. If `outline` is a function-local variable, it gets garbage-collected when the function returns, and the zone's outline becomes empty on save (zones save with 0 outline points; KiCad GUI shows empty zones).

Wrong:
```python
def add_zone(brd, ...):
    outline = pcbnew.SHAPE_POLY_SET()
    outline.NewOutline()
    outline.Append(...)
    z = pcbnew.ZONE(brd)
    z.SetOutline(outline)
    brd.Add(z)
    # `outline` gc'd on return → zone's outline now invalid
```

Right:
```python
_zone_outline_refs = []  # module-level keeps SHAPE_POLY_SETs alive

def add_zone(brd, ...):
    outline = pcbnew.SHAPE_POLY_SET()
    # ... build outline ...
    z.SetOutline(outline)
    _zone_outline_refs.append(outline)  # keep alive past function return
    brd.Add(z)
```

Discovered debugging Phase 4c (5/2026) — 7 added zones all appeared in `brd.Zones()` pre-save but saved as 0-point empty zones until the keep-alive list was added.

### ZONE_FILLER.Fill() — segfaults on multi-layer kinet2pcb boards (aarch64)

```python
filler = pcbnew.ZONE_FILLER(brd)
ok = filler.Fill(list(brd.Zones()))   # SEGFAULTS
```

Observed on KiCad 9.0.2 aarch64 (Raspberry Pi 5) with a 4-copper-layer kinet2pcb-derived board + 7 zones across 3 layers. Specific to this combination; the GUI Fill operation works fine.

Workaround: don't call ZONE_FILLER.Fill(). Save zones unfilled; `kicad-cli pcb drc` auto-fills before checking, and KiCad GUI fills on open. Zone outlines + net assignments persist in the .kicad_pcb, which is what 4d Freerouting DSN export reads.

### NETNAMES_MAP keys are wxString, not Python str

```python
nets = brd.GetNetsByName().asdict()
nets.get("GND")   # returns None — key is wxString('GND'), not 'GND'
```

Right:
```python
for k, v in nets.items():
    if str(k) == "GND":
        return v
```

### ZONE.GetLayerName() returns "F.Cu" for all zones (KiCad 9 binding bug?)

`zone.GetLayer()` returns the correct numeric layer ID (e.g. 4 for In1.Cu, 6 for In2.Cu, 2 for B.Cu after `SetCopperLayerCount(4)`), but `GetLayerName()` always returns "F.Cu" regardless. Trust the numeric ID; use a manual lookup table for display:
```python
LAYER_NAME = {0: "F.Cu", 2: "B.Cu", 4: "In1.Cu", 6: "In2.Cu"}
```

## Layout discipline (Phase 4b/4c/4d hard lessons)

### Always API-measure pad extents — don't estimate

The Phase 4b-rev3 zigzag had ONE root cause: estimating pad geometry instead of measuring it. Estimates miss:

- **Pad rotation**: a 1.0×2.7mm MP pad on a connector rotated 270° has world-X extent 2.7mm not 1.0mm; `pad.GetSize()` returns size that's ALREADY rotated with the footprint.
- **0805 vs 0402 pad-extent**: 0805 cap pads are 1.25×1.0mm — wider than 0402 (0.5×0.6mm).
- **Mounting-hole / locating-pad sizes**: JST-GH MP pads = 1.0×2.7mm; M3_Pad mounting holes default to 6.4mm copper.

```python
# CORRECT: measure via API, work in world coordinates
for fp in brd.GetFootprints():
    if fp.GetReference() == "U2":
        for pad in fp.Pads():
            pos = pad.GetPosition()   # world position
            sz  = pad.GetSize()       # rotated with footprint
            # extent: pos ± sz/2 in world coords
```

If you're computing a clearance, you measured via API. If you're estimating, you're about to introduce a DRC violation.

### Headless scripted routing has limits on dense boards

Phase 4d (16 critical nets on 36×36 placement) confirmed: Python `pcbnew.PCB_TRACK + PCB_VIA` scripted Manhattan/Z-routes through a dense placement (~70 components) cannot reliably produce DRC-clean critical-net routing. Three progressive iterations: 53 / 81 / 6 DRC violations.

Scripted routing handles INDIVIDUAL nets but doesn't compose. Multiple nets in the same channel collide; via columns clash; tracks cross. Autorouters have pathfinding intelligence; an L-shape Python helper doesn't.

Scripted routing IS good for:
- Locking pre-determined critical nets (hand-compute geometry, SetLocked(True))
- Test fixtures, single-net routing
- Validation of route quality post-routing

Scripted routing IS NOT good for:
- Composing 10+ routes on a dense placement (the 4d tripwire)
- Replacing Freerouting or a GUI session

Rule 13 stop the scripted-route approach if 2-3 iterations zigzag at scale.

## When you encounter a new gotcha

Add a section here. Keep it terse — "what broke, the WRONG pattern, the CORRECT pattern, why." Future-Claude on Phase 4+ will read this; reverse-engineering the same problem twice is wasted effort.

Don't move existing notes into local Claude memory — that loses the cross-machine + cross-session value. This file is the source of truth.
