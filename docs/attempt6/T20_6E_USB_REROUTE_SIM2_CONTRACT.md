# T20 escalation 6e — USB diff pair re-route + Sim 2 contract

> **Sai 2026-06-02 decision: Option (a) USB diff pair re-route** to unblock the
> USART1 corridor T20 cannot otherwise pass. Worker dispatched.
>
> This doc is the **mandatory Sim 2 re-validation contract** that worker must
> satisfy before merging the re-route PR. Master pre-commits the gate values
> so audit traceability is preserved (per Rule 17 no-loose-threads).

## Scope of re-route

Move these segments OFF the X=53-93, Y=30-35 USART1 corridor:
- `USB_DM` — 19.28 mm total (3 F.Cu segments)
- `USB_DP` — 19.37 mm total (3 F.Cu segments)
- `USBC_D_M_PRE` — 11.61 mm total (4 F.Cu + 1 B.Cu)
- `USBC_D_P_PRE` — 8.88 mm total (3 F.Cu + 1 B.Cu)
- `USBC_CC1`, `USBC_CC2` (optional — can stay if not blocking)

Re-route candidates (worker picks the cleanest):
- **A:** Push USB pair deeper south (Y=20-26 band) — route around USART1
- **B:** Tighter cluster around J1 (~X=80-90 only) — no spread west
- **C:** Layer flip selected segments (F.Cu → B.Cu) — only if Z₀ preserved

## Sim 2 PASS gate (mandatory before merge)

After re-route complete, worker runs `sims/em-fem-builds/` or equivalent Sim 2
infrastructure for the USB differential pair.

| Metric | PASS criterion | Source |
|---|---|---|
| Z₀_diff | **81 Ω ≤ Z₀ ≤ 99 Ω** | USB 2.0 spec: 90 Ω ± 10% |
| Z₀_diff vs original | **Z₀ ≥ 74.3 Ω** (≥85% of original 87.4 Ω) | Sai-pick (a) tolerance |
| Length matching | **skew ≤ 150 ps** | USB 2.0 spec |
| Common-mode coupling | within Sim 2 baseline ±20% | regression check |

**Both Z₀ criteria must satisfy** (USB spec AND Sai-pick contract).

## Failure handling

| Result | Action |
|---|---|
| Z₀ ∈ [81, 99] Ω AND ≥74.3 Ω AND skew ≤150 ps | **COMMIT** — re-route + USART1 route + PR |
| Z₀ < 81 Ω or > 99 Ω | **REVERT** re-route. Try different topology (A/B/C). |
| Z₀ in [74.3, 81) Ω | **MASTER DECISION** — below USB 2.0 spec but above Sai contract. Likely revert; escalate to Sai if no better topology found. |
| skew > 150 ps | **REVERT** + re-do length matching |
| Worker re-route walls (cascade DRC) on all 3 topology options | **MASTER DECISION** — escalate; may need option (b) cluster re-place per original Sai question |

## Per-net audit gate (mandatory)

Concurrent with Sim 2:
- `audit_unconnected_per_net.py` ABSOLUTE — USART1 must now route cleanly in freed corridor
- DRC severity-error sweep
- Scope-creep cap still 4/4

## Why this contract is fair

- Z₀ 87.4 Ω original was already 3% under nominal (USB spec 90 Ω); re-route to 81-99 Ω just preserves the in-spec band
- 85% × 87.4 = 74.3 Ω is below USB 2.0 spec lower bound; if Z₀ drops to that, it's a real degradation worth Sai-level review
- 150 ps skew is the USB 2.0 max; pair was already length-matched per original Sim 2

## What happens after T20 6e lands

- T22 sub-tasks can proceed (T20 corridor opens, downstream surgery doable)
- T21 SWD can leverage same corridor (different MCU pin set but same general area)
- Sim re-validation cascade: Sim 5 PDN spot-check if power-plane stitching shifted; Sim 1 thermal NOT affected (no heat source moved)

## Reference

- Sim 2 baseline: PR #75 era — `sims/em-fem-builds/`
- Original Z₀_diff: 87.4 Ω
- USB 2.0 spec: Z₀ 90 Ω ± 10%, skew ≤ 150 ps
- Sai pick: 2026-06-02 (a) "USB diff pair re-route (Recommended)" per master 4-option survey
