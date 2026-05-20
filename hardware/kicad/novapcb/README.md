# hardware/kicad/novapcb/

The novapcb KiCad board project. Hosts the schematic (SKiDL-generated netlist; per-sub-phase Python source) and — at Phase 4 — the PCB layout.

## Files

| File | Role |
|---|---|
| `sym-lib-table` / `fp-lib-table` | Committed library references — point at `/usr/share/kicad/symbols/` and `/usr/share/kicad/footprints/` (KiCad 9 standard libs). |
| `sheets/` | Per-sheet SKiDL Python modules. One file per Phase 3 sub-phase (`mcu_3a.py`, etc.). `common.py` has shared SKiDL setup + footprint string constants. |
| `generate.py` | Top-level assembler. Imports each sheet module, runs SKiDL ERC, generates the netlist. |
| `novapcb.net` | Generated netlist — committed for diff-reviewability. Phase 4 PCB layout consumes this. |
| `generate.log` / `generate.erc` | SKiDL build log + ERC report from the last `python3 generate.py` run. |
| `generate_sklib.py` | SKiDL symbol library cache (gitignored — regenerated each run). |

## What this directory does NOT contain (yet)

- **`novapcb.kicad_sch`** — the drawn schematic. SKiDL `generate_schematic()` does not scale to the MCU sheet (hangs on auto-router). Phase 3 mode is **netlist-only**. The drawn schematic is needed for Phase 6.5 forum review only; tracked as `docs/OPEN_QUESTIONS.md phase3-render-1` with a scheduled investigation in the Phase 3.5–6 window. See `hardware/kicad/KICAD9_NOTES.md` for the SKiDL scaling-limit details.
- **`novapcb.kicad_pcb`** — the PCB layout. Phase 4 work.
- **`novapcb.kicad_pro`** — the KiCad project file. Held until Phase 4 / drawn-schematic generation lands; the netlist + Python source don't require it.

## Regenerate

```bash
cd hardware/kicad/novapcb
python3 generate.py
```

Produces `novapcb.net` (load-bearing — Phase 4 consumes it), `generate.log` (audit trail), `generate.erc` (SKiDL ERC report).

The pipeline runs SKiDL ERC + `generate_netlist()`. It does NOT run `generate_schematic()` — see the "What this directory does NOT contain" section above.

## Phase 3 sub-phase status

| Sub-phase | Sheet | Module | Status |
|---|---|---|:---:|
| 3a | MCU + clock + reset + decoupling | `sheets/mcu_3a.py` | in this PR |
| 3b | Power tree | `sheets/power_3b.py` | TBD (next sub-phase) |
| 3c | IMU SPI | `sheets/imu_3c.py` | TBD |
| 3d | Baro I²C | `sheets/baro_3d.py` | TBD |
| 3e | GPS+mag JST-GH 10P | `sheets/gps_3e.py` | TBD |
| 3f | ESC outputs | `sheets/esc_3f.py` | TBD |
| 3g | CRSF UART + USB-C | `sheets/crsf_usb_3g.py` | TBD |
| 3h | Power mon + microSD + SWD + mounting | `sheets/power_mon_sd_swd_3h.py` | TBD |

## Tooling

- KiCad 9.0.2 (Debian trixie apt main; see `CLAUDE.md §10.2`)
- SKiDL 2.2.3 (`pip install --user skidl`)
- KiCad standard symbol + footprint libs at `/usr/share/kicad/symbols/` + `/usr/share/kicad/footprints/`

For KiCad-9-specific quirks (pcbnew Flip API, SKiDL gotchas, kicad-cli capabilities), see `../KICAD9_NOTES.md`.
