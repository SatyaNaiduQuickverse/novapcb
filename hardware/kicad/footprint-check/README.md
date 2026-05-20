# hardware/kicad/footprint-check/

novapcb Phase 2.5 placement-only KiCad sketch — verifies the Phase 2 peripheral set fits on a Pixhawk-standard mini-FC outline (36 × 36 mm board, 30.5 × 30.5 mm c-to-c M3 mounting holes).

## Files

| File | Role |
|---|---|
| `generate.py` | **Authoritative source.** pcbnew Python API script that constructs the board from scratch. |
| `footprint-check.kicad_pcb` | Generated output of `generate.py`. Committed for diff-reviewability + GUI inspection. |
| `notes.md` | Fit-check assessment + tight-spot callouts + Phase 4 carry-forward. |
| `P0_REPORT.md` | Phase 2.5 Part 0 setup-gate report (KiCad install + headless API + footprint inventory + 4 forks). |
| `drc-report.txt` | DRC output from `kicad-cli pcb drc` (regenerated each run). |
| `README.md` | This file. |

## Regenerate

```bash
cd hardware/kicad/footprint-check
python3 generate.py
kicad-cli pcb drc --output drc-report.txt --format report footprint-check.kicad_pcb
```

Re-running yields a bit-identical `.kicad_pcb` (modulo KiCad's internal UUIDs). Edit `generate.py` to change placements — never hand-edit `footprint-check.kicad_pcb`.

## Inspect in GUI

```bash
kicad footprint-check.kicad_pcb
```

(Requires KiCad GUI; `novarobotics64` build host is headless so this is for human-machine inspection elsewhere.)

## Tooling baseline (this Pi)

- KiCad 9.0.2+dfsg-1 (Debian trixie apt main)
- pcbnew Python API at `/usr/lib/python3/dist-packages/pcbnew.py` (headless, no DISPLAY)
- kicad-cli 9.0.2

See `P0_REPORT.md` §P0.1 + §P0.2 for full tooling verification.

## Scope boundary

This is **placement-only**. No schematic, no netlist, no routing, no passives. Phase 3 (schematic init) + Phase 4 (real layout) build on the placement reality this artifact confirmed.

The artifact is not a production layout — it's a "fail cheap" gate per master's Phase 2.5 contract. See `notes.md` "Does it fit?" section + "Phase 4 carry-forward" for the work this sketch deferred to Phase 4.
