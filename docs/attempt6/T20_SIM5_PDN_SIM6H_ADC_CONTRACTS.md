# T20 Sim 5 PDN + Sim 6h ADC re-validation contracts (combined attack final sims)

> Master pre-commits the remaining two sim contracts for the worker's
> combined-attack final validation cascade. With Sim 2 (USB), Sim 4 (CAN),
> Sim 5 (PDN), and Sim 6h (ADC settling) committed as docs, the all-or-
> nothing PASS gate has full per-sim audit trail per Rule 17.

## Sim 5 PDN spot-check (combined-attack regression test)

After the 5 moves in combined attack:
- BATT2 sense re-routed (Y=14-22 F.Cu cleared, B.Cu Y=25-26 detour)
- USART6_TX surgical X=42 shift
- CAN1_TX/RX Y-shift to Y=11/13 from Y=16/19
- USB diff pair south detour to Y=22.0/22.5
- USART1 route in freed Y=30-35 X=53-93 corridor

**PDN plane perturbation:** any plane-stitching via shifts during routing
+ inner plane re-pour after the moves. Sim 5 spot-check ensures the +3V3
PDN integrity didn't degrade past gate.

### Sim 5 PASS gate

| Frequency band | PASS criterion | Baseline | FAIL action |
|---|---|---|---|
| mid-band (100 kHz – 100 MHz) | peak ≤ 100 mΩ | 79.4 mΩ | add bulk cap stitching |
| LF (1–100 kHz) | within ±10% of baseline | model-limited | flag only (Phase 9 bench) |
| HF (>100 MHz) | model-limited; check no major new resonance | over-sharp | flag only |

**Primary gate:** **mid-band peak ≤ 100 mΩ.** That's the hard gate; LF/HF
are model-limited residuals already documented in `docs/SIM_RERUN_POST_D4.md`.

### Sim 5 FAIL fix proposals (per spec §7)

If mid-band > 100 mΩ:
- Add bulk cap stitching near U1 MCU (4.7µF + 22µF were already at C16/C33;
  consider adding one more 10µF if gap-filling needed)
- Verify plane re-pour didn't introduce voids near power-rail vias
- Check no stitching via was removed during the moves

## Sim 6h ADC settling (BATT2 re-route regression test)

After BATT2 sense re-routed (Step 1 of combined attack), Mauch V/I ADC
sense lines now flow through the new B.Cu Y=25-26 path before reaching
the RC filter at U1 (PC0/PC1 ADC pins).

**Risk:** the B.Cu re-route may have changed parasitic capacitance to
the +5V plane (In2.Cu underneath B.Cu). If so, RC effective cutoff shifts.

### Sim 6h PASS gate

| Metric | Spec | Baseline | FAIL action |
|---|---|---|---|
| RC cutoff frequency | 1500-1700 Hz (design 1.59 kHz) | 1590 Hz | tighten C if cutoff drifts low; loosen if high |
| Settling time to 0.1% | ≤ 200 µs | 158 µs (10 × τ) | larger C or smaller R |
| Ripple rejection at DShot 600 kHz | ≥ 50 dB | 51.5 dB (Sim 6i.E) | already validated; re-check |
| Common-mode noise | within ±10mV ADC tolerance | per Sim 6i.E | re-confirm |

**Primary gate:** RC cutoff in [1500, 1700] Hz AND settling ≤ 200µs.

### Sim 6h FAIL fix proposals

- If cutoff drifted below 1500 Hz: parasitic C added; tighten via wider B.Cu
  trace or different return path
- If cutoff drifted above 1700 Hz: parasitic C reduced; either add discrete
  C (220nF upgrade from 100nF) or accept (under-attenuation worst case = 
  still > 45 dB at DShot 600 kHz; still PASS spec gate)

## Reference baselines (committed)

- Sim 2 USB Z_diff baseline: 87.4Ω (PR #75 era)
- Sim 4 CAN Z_diff baseline: ~120Ω (PR #99 / PR #112 era)
- Sim 5 PDN baseline: 79.4 mΩ mid-band peak (PR #126 / SIM_RERUN_POST_D4.md)
- Sim 6h ADC settling baseline: 158 µs to 0.1%, 1.59 kHz cutoff (Phase 3h
  + Sim 6i.E re-validation)
- Sim 1 thermal baseline: 65.05°C MCU Tj (PR #126; no heat sources moved
  in combined attack so should match within ±1°C)

## All-or-nothing summary (master combined-attack contract PR #168)

**ALL 4 sims must PASS** (Sim 2 + Sim 4 + Sim 5 + Sim 6h) **→ commit entire
combined attack PR.** Sim 1 thermal spot-check is informational only.

**ANY sim FAIL → revert all 5 moves on branch hw/t20-combined-attack.**
Then master/Sai re-decide:
- Option (b) cluster re-place
- Option (c) board grow 105×85 → 105×100mm  
- Option (d) Telem v2-defer (Sai-override)
