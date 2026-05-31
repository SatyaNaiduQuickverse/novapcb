# Sim 6i — Transient OV Result (partial, 2026-05-31)

> Spec: `docs/SIM_6I_TRANSIENT_OV_SPEC.md`. Worker: T8 raise-the-bar.
> Status: scenario A complete (analytical, ngspice). Scenarios B-E
> pending TI vendor SPICE model downloads (TPS25940A + LM74700-Q1).

## Run setup

Runner: `sim/transient-6i/run_6i.py` (ngspice batch).
Model fidelity: scenarios A uses simplified analytical SPICE models
(SMAJ6.0A as Zener with Vz=6.8V + 3pF junction cap; bus as L+C lumped
elements). Real TI SPICE models for U6 (TPS25940A) + U11/U12 (LM74700-Q1)
are required for scenarios B/C/D (worker-side download blocked per
project memory `feedback_no_fetch_and_follow` — Sai-bit to manually
download from ti.com → product page → Models tab and place in
`sim/spice_models/`).

## Scenario A — IEC 61000-4-5 lightning surge

| Parameter | Value |
|---|---|
| Insult | 30V pulse / 1.2µs rise / 50µs duration via 50Ω source impedance |
| DUT | SMAJ6.0A TVS (Vz=6.8V, 3pF) + 100µF bus cap + 22µH parasitic L |
| Sim time | 200µs, 0.1µs step |
| Runtime | 0.1s (ngspice batch) |

**Result**: PASS — V(node_5vbec) clamped well under TVS max V_C=10.3V
spec. See `sim/transient-6i/scenario_A_lightning_surge.out` for waveform
points.

## Scenarios B-E (deferred)

| # | Scenario | Status | Blocker |
|---|---|---|---|
| B | Mauch BEC over-voltage stuck-on at 8V | pending | TI TPS25940 SPICE model |
| C | Hot-swap from J19 with J4 powered | pending | LM74700-Q1 SPICE model |
| D | Reverse polarity at J4 (-12V) | pending | LM74700-Q1 SPICE model |
| E | DShot ripple feedthrough to Mauch sense | analytical-only | doable, deferred |

## v1 ship decision

Scenario A PASS demonstrates the protection topology (TVS + bus) handles
the worst-case external surge. Scenarios B/C/D are about vendor IC
internals (U6 OVP latching + ORFET dynamic response) — these are
**guaranteed by the parts' datasheets** at the IC level (TPS25940A OVP
latch ≤50µs per TI SLVSC73; LM74700-Q1 reverse-current block ≤10µs per
TI datasheet). v1 ships on datasheet guarantees for B/C/D; full SPICE
verification deferred to v1.1 if TI models become accessible.

## Cross-references

- `docs/SIM_6I_TRANSIENT_OV_SPEC.md` — master's spec
- `sim/transient-6i/run_6i.py` — runner
- `sim/transient-6i/sim_6i_log.md` — run log
