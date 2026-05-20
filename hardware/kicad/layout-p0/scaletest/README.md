# layout-p0/scaletest — Phase 4 P0 routing-toolchain scale-test

Reproducible scale-test for the headless KiCad-9 → Freerouting routing toolchain. Run from this directory:

```bash
KICAD9_FOOTPRINT_DIR=/usr/share/kicad/footprints python3 build_board.py
JAVA25=$(ls -d ~/local/jre/jdk-25*)
$JAVA25/bin/java -Dgui.enabled=false -jar ~/local/freerouting/freerouting.jar \
    -de scaletest.dsn -do scaletest.ses -mt 4 -mp 30
```

## Inputs

- `../../novapcb/novapcb.net` — Phase 3 netlist (73 components / 56 nets / 9 sheets)
- KiCad 9 footprint libs at `/usr/share/kicad/footprints/`
- `~/local/jre/jdk-*` — Adoptium OpenJDK 25 JRE (user-space, see `PHASE4_P0_REPORT.md §P0.1`)
- `~/local/freerouting/freerouting.jar` — Freerouting v2.2.4 (user-space)

## Outputs

- `scaletest.kicad_pcb` — board after kinet2pcb + outline + 4-layer + scatter
- `scaletest.dsn` — Specctra DSN for Freerouting
- `scaletest.ses` — Specctra SES from Freerouting (post-routing; only on completion)
- `scaletest.kicad_pcb` after `ImportSpecctraSES` — routed board (Phase 4d's job, not P0)

## What this proves / doesn't

This is the Phase 4 **P0** scale-test, not the Phase 4d routing run. P0 scope:

- ✓ Toolchain pieces installed and runnable headless
- ✓ KiCad netlist → board → DSN export works on the real netlist
- ✓ Freerouting parses + ingests the DSN
- ✗ NOT proving Freerouting produces a clean route — that requires Phase 4b placement
- ✗ NOT proving wall-clock for production routing — production budget is Phase 4d

See `../../PHASE4_P0_REPORT.md` for the full report including iter-1/2/3 progressive findings.

## Phase 4d will not use this scatter placement

The `build_board.py` scatter on a 10-col grid with 7mm spacing is INTENTIONALLY naive. Phase 4d's real input is the Phase 4b-placed board (per the Phase 2.5 sketch + Phase 3 hierarchy), with copper planes from Phase 4c. This directory is not Phase 4d's starting point.
