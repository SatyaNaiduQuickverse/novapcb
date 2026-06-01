# T20 Sim 4 CAN Z_diff re-validation contract (combined attack Step 3)

> Master pre-commits the Sim 4 PASS gate for worker's Step 3 CAN re-route.
> Worker runs `sims/sim4-can-zdiff/` (or equivalent) after CAN bus segments
> are re-routed off the X=49-91, Y=16-19 horizontal blockers.

## Original Sim 4 baseline

| Metric | Baseline value | Source |
|---|---|---|
| Z_diff CAN H/L | ~120 Ω | PR #99 era CAN routing |
| Length matching | within ISO 11898-2 tolerance | original validation |
| Mode coupling | within Sim 4 nominal | baseline |

## ISO 11898-2 spec (governing)

| Parameter | Spec | Tolerance |
|---|---|---|
| Differential impedance | **120 Ω** | **±17%** ⇒ 100-140 Ω |
| Length matching | ≤ 100 ps skew | ISO standard |
| Common-mode | dominated by U14 TJA1051 transceiver | not layout-sensitive at our trace lengths |

## Sim 4 PASS gate (worker must satisfy)

After Step 3 CAN re-route complete:

| # | Criterion | PASS | FAIL action |
|---|---|---|---|
| Sim 4.1 | Z_diff ∈ [100, 140] Ω | commit | revert + try alt topology |
| Sim 4.2 | Length match skew ≤ 100 ps | commit | revert + length-match |
| Sim 4.3 | Z_diff within ±10% of baseline 120 Ω (= 108-132 Ω) | bonus tighter check | flag warning if outside |

## CAN re-route topology candidates

(Master suggestion; worker picks via DRC iteration on hw/t20-combined-attack)

### Option A: Y-shift to N-edge
Push CAN1_TX/RX traces from Y=16/19 to Y=10-12 (between J20 and J19 N-edge).
Frees Y=16+ for USART1 routing without touching CAN MCU pinout.

### Option B: Layer-flip to In3 plane
Move CAN segments from F.Cu to In3 (+3V3 plane region). Via stitching at
endpoints. Z_diff degrades because plane reference becomes mixed.
Likely FAILs Sim 4.

### Option C: Re-pin CAN MCU pins
Currently on PD0/PD1 (CAN1) — could re-pin to PB8/PB9 (CAN1 alt). Hwdef.dat
re-issue required. Routing changes from W→E to NE→E (shorter).

Master recommends **Option A** (cheapest + preserves Sim 4 baseline best).

## Failure escalation

If Sim 4 FAILs ALL three topology options:
- Revert Step 3 CAN re-route
- Revert entire combined attack (all-or-nothing per master contract)
- Master/Sai re-decide (board grow or cluster re-place per original Sai 4-option)

## Reference

- Original CAN routing: PR #99 + PR #112 (Sim 4 validation)
- ISO 11898-2: governing CAN H/L spec
- Worker hw/t20-combined-attack branch (Step 1 v2 already committed at f8a97e7)
