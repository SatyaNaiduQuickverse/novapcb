# Sim 6i Run Log

Scenario A (lightning surge): PASS — see scenario_A_lightning_surge.out
Scenario B (Mauch BEC over-voltage): pending TI TPS25940 SPICE model download
Scenario C (Hot-swap from J19): pending LM74700-Q1 SPICE model
Scenario D (Reverse polarity): pending LM74700-Q1 SPICE model
Scenario E (DShot ripple feedthrough): can use analytical Mauch source model — pending

## Session-2 update 2026-06-01

TI SPICE models OBTAINED:
- TPS25940A: sim/spice-models/tps25940/SLVMAB0B/TPS25940A_TRANS.LIB (SLVMAB0)
- LM74700-Q1: sim/spice-models/lm74700/LM74700-Q1_TRANS.lib (SNOM667)
- Bonus N-FET: sim/spice-models/lm74700/CSD18540Q5B.lib (CSD18540Q5B for LM74700 driving FET)

Sai authorized WebFetch → curl direct download of these TI .ZIP files. Extracted text-only .LIB files committed; ZIPs gitignored.

Scenario B SPICE deck scaffolded at sim/transient-6i/scenario_B_mauch_overvoltage.cir. PSPICE → ngspice syntax compatibility may need adjustment on first run (TPS25940A_TRANS uses encrypted PSPICE-only subcircuit blocks — ngspice may not parse all). If parse fails: use ngspice's .INCLUDE with PSPICE-compatibility flag, or use LTSpice as alternative simulator.

Scenarios C-E pending. Multi-session work per Sai's "we finish all now" directive.
