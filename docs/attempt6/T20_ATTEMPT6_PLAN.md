# T20 Attempt 6 — SDMMC1 westward re-route plan (2026-06-01)

> WIP. Multi-session work per master 2026-06-01 explicit OK.
> Sai authorized "whatever rework is needed".

## Step 1 (DONE this session)

Captured SDMMC1 current routing geometry — see `SDMMC1_PRE_REROUTE_STATE.log`.

**Summary:** 6 SDMMC1 nets totaling ~80+ track segments + 12+ vias spread across E half of board (X=50-98, Y=25-70). 19 segments specifically cross the X=53-93, Y=32-44 corridor that USART1 needs.

## Step 2 (NEXT SESSION) — westward shift execution

For each SDMMC1 net, shift trace endpoints westward by 5-10mm to free the X=53-93, Y=32-44 corridor:

| Net | Strategy |
|---|---|
| SDMMC1_CLK | Move L0 segment from (54.57→64.18, 32.35) westward — drop via earlier, route on L2 |
| SDMMC1_CMD | Move L2 segments from (71-79, 31-40) westward + add via to L0 alt routing |
| SDMMC1_D0 | Move L0 segment (57.68, 34.00)→(73.69, 50.01) — re-route via NW corridor |
| SDMMC1_D1 | Similar to D0 |
| SDMMC1_D2 | L2 (76.48, 37.66)→(76.48, 48.69) — move west of X=53 |
| SDMMC1_D3 | L2 (79.18, 40.09)→(92.56, 53.47) — full re-route through W corridor |

## Step 3 — route USART1 in freed corridor

After SDMMC1 westward shift, USART1_TX/RX route from U1.68/69 east → J3.2/3 with the L0+L2 corridor X=53-93 Y=32-44 now clear.

## Step 4 — Sim 3 re-validation (MANDATORY)

Run `sim/sdmmc-6f/` runner on new SDMMC1 geometry. Gate per master:
- ≥97% timing margin: commit as-is, no flag
- 95-97%: marginal commit + Phase 9 bench priority flag
- <95%: FULL REVERT both SDMMC1 + USART1 changes; document Sim 3 result; proceed to Attempt 7 (v2-defer doc) with honest "we tried the wall-push and Sim 3 failed" evidence

## Step 5 — per-net audit + commit decision

`audit_unconnected_per_net.py` ABSOLUTE pass required regardless of Sim 3 outcome.

## Multi-session handoff state

- **Branch**: `hw/t20-attempt6-sdmmc-westward`
- **Step 1 complete**: SDMMC1 geometry captured (this commit)
- **Step 2-5 pending**: next session pickup point

## Session-end status (2026-06-01 ~02:00 UTC)

Committed Step 1 analysis. Step 2 starts next session. Heartbeat sent to master with explicit "session-handoff WIP at Attempt 6 Step 1 complete" per master's brief.
