# T20 USART1 corridor residual blockers — master pre-survey (2026-06-02)

> **CRITICAL pre-execution finding.** Surveyed all segments in the USART1
> target corridor (X=53-93, Y=30-35) on `.kicad_pcb` HEAD `d50058b`.
> After all 6 SDMMC1 nets shift per `T20_STEP2_PROGRESS.md`, **30
> segments** on OTHER nets still cross the corridor — and SOME are
> HANDS-OFF.
>
> Worker MUST review this before executing the 4-8 hr SDMMC1 bulk shift.

## Total residual blockers: 30 segments (excluding the 5 cited SDMMC1 nets being shifted)

### Breakdown by net + layer

| Layer | Net | Count | Type | Hands-off? |
|---|---|---|---|---|
| F.Cu | +5V | 7 | power rail | NO (re-routable) |
| F.Cu | USB_DM | 3 | USB diff pair | **YES** (CLAUDE.md §3.7 + Sim 2) |
| F.Cu | USB_DP | 3 | USB diff pair | **YES** |
| F.Cu | USBC_D_M_PRE | 2 | USB pre-ESD diff | **YES** |
| F.Cu | USBC_D_P_PRE | 2 | USB pre-ESD diff | **YES** |
| B.Cu | SDMMC1_CMD | 3 | (6th SDMMC1 net) | already in shift plan |
| F.Cu | USBC_CC1 | 1 | USB Type-C config | sensitive, but re-routable |
| B.Cu | USBC_CC1 | 1 | same | same |
| B.Cu | USBC_D_M_PRE | 1 | USB pre-ESD diff | **YES** |
| B.Cu | USBC_D_P_PRE | 1 | USB pre-ESD diff | **YES** |
| B.Cu | +3V3_IMU | 1 | IMU power | sensitive |
| B.Cu | HEATER_PWM | 1 | low-speed | re-routable |
| B.Cu | IMU2_GYR_INT3 | 1 | IMU interrupt | sensitive |
| B.Cu | SPI3_MISO | 1 | IMU SPI | **HANDS-OFF** (>5MHz CLAUDE.md §3.7) |
| B.Cu | SPI3_SCK | 1 | IMU SPI | **HANDS-OFF** |
| F.Cu | VCAP2 | 1 | MCU internal LDO cap | DO NOT TOUCH (MCU stability) |

## Hands-off count

**12 segments on HANDS-OFF nets:**
- 11 USB-related (DM/DP + USBC_D_*_PRE + same nets on B.Cu)
- 2 SPI3 (MISO + SCK)
- 1 VCAP2 (MCU internal-LDO cap to PSU)

**Conclusion:** The 6-net SDMMC1 westward shift is NECESSARY but **NOT
SUFFICIENT.** Even with all SDMMC1 nets shifted, the USB diff pair +
SPI3 + VCAP2 still block the X=53-93, Y=30-35 corridor.

## What this means for T20 Attempt 6

Option A: **Narrow the USART1 corridor target.** Instead of X=53-93, use
a smaller strip (e.g., X=60-80) that avoids USB-cluster area (X~70-85)
and clears USB DM/DP + USBC_D_*_PRE bands.

Option B: **Route USART1 on a non-corridor path.** Use deeper south
trajectory (Y=45+) that loops AROUND the USB cluster instead of through
it. Longer trace but doesn't fight hands-off.

Option C: **Re-pin USART1 closer to clear B.Cu lane.** PE7/PE8 was
tested earlier (SE corridor 42 fouls) — but with the SDMMC1 westward
shift the SE corridor may also open. Re-survey with SDMMC1 shifted.

Option D (last resort): **Re-pin USART1 to a completely different MCU
edge.** Some H743 USARTs might re-pin to currently-clear lanes.

## Recommendation to worker

Before executing the 4-8 hr SDMMC1 bulk shift:
1. **Quick option A test:** narrow corridor to X=60-80; see if USART1
   fits there without SDMMC1 shifts at all. Cheap check (~30 min).
2. If A fails: execute SDMMC1 shifts AND simultaneously plan
   USART1 route to avoid the USB cluster (option B trajectory).
3. Per Sai 'no defers' — do not accept v2-defer; escalate per Attempt
   6b/6c/6d as needed.

## Master action

Surfacing this finding to worker via /send/worker so the next session
opens with this context, not after they've burned 4-8 hr on shifts.

Verification method: text-only regex parse of `.kicad_pcb`. Worker's
pcbnew is authoritative for actual routing decisions; this survey is
a "before you start, check the wider geometry" pre-flight.
