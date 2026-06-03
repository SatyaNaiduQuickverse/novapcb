# T23 board-grow sim spot-check spec — Sim 2/3/4/6h

> Lighter spot-check companion to mandatory full re-runs of Sim 1 thermal
> (PR #176) + Sim 5 PDN (PR #189). These four sims have lower
> board-area-sensitivity but still need verification post board-grow.

## Why spot-check vs full re-run

The mandatory full re-runs (Sim 1 + Sim 5) measure properties that scale
with board area. The spot-check sims measure properties tied to specific
trace/connector geometry; board grow doesn't change them unless those
specific elements were touched.

| Sim | Tied to | Board-grow impact |
|---|---|---|
| Sim 1 thermal | board area + heat-source positions | YES (re-run mandatory) |
| Sim 5 PDN | plane area + cap network | YES (re-run mandatory) |
| Sim 2 USB Z_diff | USB diff pair geometry | NO (unless USB re-routed) |
| Sim 3 SDMMC1 SI | SDMMC1 traces + length matching | NO (unless SDMMC re-routed) |
| Sim 4 CAN Z_diff | CAN H/L diff pair | NO (unless CAN re-routed) |
| Sim 6h Mauch ADC | RC filter values + parasitic | NO (unless touched) |

In the combined-attack-reverted-then-board-grow sequence:
- USB diff pair: UNCHANGED on board grow branch (combined attack reverted)
- SDMMC1: UNCHANGED
- CAN: UNCHANGED
- Mauch ADC: UNCHANGED

**Conclusion: spot-checks should PASS with values within ±5% of baseline.**

## Spot-check PASS gates

### Sim 2 USB Z_diff
| Check | Baseline | PASS gate |
|---|---|---|
| Z₀_diff at coupled section | 87.4 Ω | within ±5% (83.0 - 91.8 Ω) |
| Length-match skew | within USB 2.0 ±150 ps | unchanged |
| At fan-out region | spec ≥ 0.10 mm clearance | unchanged |

**Source**: original openEMS run PR #75-era + DRU `usb-diff-pair-in-pair`.
**Spot-check trigger**: NONE — USB pair not touched on board grow branch.
**Action**: confirm Sim 2 baseline carries forward; spot-check is informational.

### Sim 3 SDMMC1 SI
| Check | Baseline | PASS gate |
|---|---|---|
| Timing margin @ SDR25 50 MHz | 97.8% | within ±2% (95.8-99.8%) |
| Length matching skew | spec ≤ 600 ps | unchanged |
| Z₀ each line | nominal 50 Ω microstrip | unchanged |

**Source**: PR #111 era (Sim 3 PASS confirmed).
**Spot-check trigger**: NONE — SDMMC1 not touched.
**Action**: confirm baseline carries forward.

### Sim 4 CAN Z_diff
| Check | Baseline | PASS gate |
|---|---|---|
| Z_diff (ISO 11898-2) | ~120 Ω | within ±10% (108-132 Ω) |
| 120 Ω termination | R45 present | unchanged |

**Source**: PR #112 era (Sim 4 PASS confirmed).
**Spot-check trigger**: NONE — CAN not touched.
**Action**: confirm baseline carries forward.

### Sim 6h Mauch ADC
| Check | Baseline | PASS gate |
|---|---|---|
| RC cutoff | 1.59 kHz (1k+100nF) | within ±5% (1.51-1.67 kHz) |
| Settling to 0.1% | 158 µs | within ±10% (142-174 µs) |
| Anti-alias at DShot 600 kHz | 51.5 dB rejection | within ±2 dB |

**Source**: Phase 3h capture + Sim 6i.E re-validation (PR #158).
**Spot-check trigger**: BATT2_SENS was nudged in combined-attack but COMBINED ATTACK REVERTED. BATT2 paths are now back to baseline.
**Action**: confirm Mauch RC paths still at baseline; verify R41/R42 cap C61/C62 untouched.

## Worker action sequence

After T22 chain closes (T22.1 attempt, T22.5 attempt, both within gates):

1. **Sim 1 thermal re-run** (mandatory per PR #176)
2. **Sim 5 PDN re-run** (mandatory per PR #189)
3. **Sim 2/3/4/6h spot-checks** (this doc; informational only since none of those subsystems touched)
4. **Per-net audit ABSOLUTE** at HEAD
5. **DRC severity-error within scope-creep cap 4/4**
6. **Final freeze gate** per `docs/PHASE7A_FREEZE_PROCEDURE.md`

If any spot-check shows >5% deviation: investigate (may indicate something touched that wasn't expected); flag for master.

If all PASS: **board freeze-ready at 105×100**, Sai-side bits remain.
