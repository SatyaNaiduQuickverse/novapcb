# T20 Attempt 6 Step 2 — Progress Log (session 2, 2026-06-01)

> Sai mandate "no defers". Multi-session WIP per master explicit OK.
> This session: empirical test of single-net SDMMC1_CLK shift cascade.

## Session-2 empirical finding

Tested: Remove SDMMC1_CLK F.Cu blocking segment (54.57, 32.35)→(64.18, 32.35);
re-route via B.Cu south detour Y=38; route USART1 in freed corridor.

**DRC delta: +37** (29 → 66).

Categories: 18 clearance + 9 shorting + 7 tracks_crossing + 4 mask_bridge +
others. Per-net audit still shows USART1_TX/RX in INTENDED_DEFERRED (routed
but not consistent endpoints).

## Why Step 2a alone is insufficient

Shifting just SDMMC1_CLK frees Y=32-32.35 in X=54-64. But USART1 corridor
needs X=53-93 free at Y=32-33. Other SDMMC1 nets still block:
- SDMMC1_D0 L0 (52.67, 34.0)→(57.68, 34.0) — Y=34 blocks
- SDMMC1_D1 L0 (52.67, 33.5)→(57.77, 33.55) — Y=33.5 blocks
- SDMMC1_D2 L2 vertical at X=76.48 Y=37.66→48.69 — blocks at X=76
- SDMMC1_D3 L2 (79.18, 39.05)→(69.13, 29.00) — diagonal crossing Y=32-33
- Multiple SDMMC1_CMD L2 segments at Y=38-40

## Required Step 2 scope (multi-net shifts)

To free X=53-93, Y=32-33 corridor, must shift:
- SDMMC1_CLK: F.Cu detour south Y=38 (DONE in tests)
- SDMMC1_D0: short F.Cu stub (52.67-57.68, 34) → either drop via at MCU and B.Cu south OR shift exit to Y=44+
- SDMMC1_D1: similar to D0
- SDMMC1_D2: B.Cu vertical at X=76 → shift to X=50 (west of USART1 corridor)
- SDMMC1_D3: diagonal at X=69, Y=29 → re-route via different layer
- SDMMC1_CMD: B.Cu segments at Y=38-40 → shift south or to different layer

Each shift creates cascade risk. Estimated total work: 4-8 hours focused
with per-shift DRC iteration + final Sim 3 re-validation.

## Session-handoff pickup point

- Branch: `hw/t20-attempt6-sdmmc-westward`
- Last clean commit: 5d7f652 (Step 1 baseline)
- This session: empirical Step 2a test confirmed single-net shift insufficient
- Next session: bulk shift all 6 SDMMC1 nets per per-net plan

## Per-net shift plan (for next-session execution)

| Net | Current blocking segment | New target |
|---|---|---|
| SDMMC1_CLK | F.Cu (54.57, 32.35)→(64.18, 32.35) | B.Cu Y=38 detour ✓ tested |
| SDMMC1_D0 | F.Cu (52.67, 34.0)→(57.68, 34.0) | Drop via at MCU, B.Cu Y=42 to dest |
| SDMMC1_D1 | F.Cu (52.67, 33.5)→(57.77, 33.55) | Drop via at MCU, B.Cu Y=42 to dest |
| SDMMC1_D2 | B.Cu vertical X=76.48 | Move to X=50 vertical, then east |
| SDMMC1_D3 | B.Cu diagonal X=69, Y=29 | Re-route to L0 via north corridor |
| SDMMC1_CMD | B.Cu at Y=38-40 | Shift south to Y=44+ |

## Sim 3 re-validation contract

Per master directive: after bulk shift complete:
- Run sim/sdmmc-6f/ runner
- ≥97% margin: commit
- 95-97%: marginal commit + Phase 9 bench flag
- <95%: revert + escalate to Attempt 6b (re-pin SDMMC1) per Sai no-defers
