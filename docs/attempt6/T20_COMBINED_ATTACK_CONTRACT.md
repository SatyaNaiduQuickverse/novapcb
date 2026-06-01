# T20 combined-attack contract — multi-subsystem move + multi-sim re-validation

> **Sai 2026-06-02 escalation pick:** Combined attack — move USB + BATT2 + CAN
> + USART6 simultaneously to free the USART1 corridor. Selected over board-grow
> + cluster re-place + v2-defer.
>
> Master commits the multi-sim contract as audit trail per Rule 17 no-loose-threads.

## Decision path

1. Original T20 attempts: 4-wall structural diagnosis
2. Master 2026-06-01: attempt 6 sequence (6a→6e cheap-first)
3. 6f BATT2 re-pin alone: insufficient (+104 DRC cascade)
4. 6e USB re-route alone: insufficient (+52 DRC cascade)
5. **Sai 2026-06-02 picks combined attack** over board-grow

## What worker moves (4 subsystems simultaneously)

| # | Subsystem | Type | Sim re-validation | Cost est |
|---|---|---|---|---|
| 1 | BATT2 sense re-pin | analog DC | Sim 6h ADC settling | ~1 hr |
| 2 | USART6 CRSF re-pin | slow UART | none (bench-validate) | ~1 hr |
| 3 | CAN bus re-route | hands-off Z_diff | **Sim 4** Z_diff | ~2 hr |
| 4 | USB diff pair re-route | hands-off Z_diff | **Sim 2** Z_diff | ~2 hr |
| — | USART1 route in freed corridor | UART | none | ~1 hr |
| — | Sim 5 PDN spot-check | (plane stitch perturbation) | **Sim 5** | ~30 min |

Total: 8-10 hr worker time. Multi-session OK.

## All-or-nothing PASS gate

**ALL 4 sims must PASS → commit entire combined attack. Any single sim FAIL → revert ALL 4 changes + escalate to master/Sai.**

| Sim | PASS criterion | FAIL action |
|---|---|---|
| **Sim 2 USB Z_diff** | 81-99 Ω (USB 2.0 spec 90Ω ±10%) AND ≥ 74.3 Ω (85% of original 87.4) AND length-match skew ≤ 150 ps | Revert USB re-route. Try alt topology. |
| **Sim 4 CAN Z_diff** | 100-140 Ω (ISO 11898-2 spec 120Ω ±17%) | Revert CAN re-route. Try alt topology. |
| **Sim 5 PDN** | mid-band peak ≤ 100 mΩ (current baseline 79.4 mΩ) | Add bulk cap stitching to recover. |
| **Sim 6h ADC settling** | Mauch V/I ADC sense settle within ±10mV via 1kΩ + 100nF RC | Tighten RC (220nF upgrade option) |
| **Sim 1 thermal** | NOT EXPECTED (no heat sources moved) | spot-check; should match prior 65.05°C MCU Tj |

## Per-net audit gate (concurrent)

After all 4 moves complete + sims pass:
- `audit_unconnected_per_net.py` ABSOLUTE — USART1 must now route in freed corridor
- USART1_TX/RX REMOVED from INTENDED_DEFERRED net set
- DRC severity-error within scope-creep cap 4/4 (new exceptions must be FAB-TIER package-inherent)

## Failure escalation

If combined attack FAILs ANY sim contract OR DRC cascades > scope-creep cap:
- Revert all 4 moves (board pristine state preserved)
- Master/Sai escalation for next decision tier:
  - Option (b) cluster re-place (J3/J5/J10) — not yet tried
  - Option (c) board grow 105×85 → 105×100 mm
  - Option (d) accept Telem v2-defer (Sai-override of "no defers" mandate)

## Worker execution order (master suggested)

Cheapest-first within the combined attack (hands-off LAST):
1. BATT2 sense re-pin → DRC check (no sim)
2. USART6 CRSF re-pin → DRC check (no sim)
3. CAN bus re-route → DRC check + Sim 4 Z_diff
4. USB diff pair re-route → DRC check + Sim 2 Z_diff
5. Route USART1 in freed corridor → per-net audit
6. Sim 5 PDN spot-check + Sim 6h ADC settling

If any step's DRC cascades — fix THAT step before moving on. Don't pile incremental cascades.

## Branch hygiene

- New branch: `hw/t20-combined-attack` (fresh from `cd31dec`)
- WIP commits per subsystem move
- Heartbeat at each WIP commit + final PR
- T21 6a continues PARALLEL only during sim wait times (don't time-slice surgery)

## Reference

- Original 4-wall analysis: `docs/TELEM_J3_STRUCTURAL_DIAGNOSIS.md`
- 6f BATT2 insufficient: worker session 2026-06-02 result
- 6e USB insufficient: worker session 2026-06-02 result
- Sai picks: 2026-06-02 (a) USB first → 2026-06-02 combined-attack after (a) insufficient
- Original Sim 2 Z₀: 87.4 Ω
- Original Sim 4 Z_diff: ~120 Ω
- Original Sim 5 PDN: 79.4 mΩ peak
