# T20 Step 2 — J10 re-place candidate survey + plan revision (2026-06-02)

## J10 re-place test (master option c)

Iterative DRC test of J10 N-edge positions (over Step 1 baseline 61):

| XY | DRC delta | Note |
|---|---:|---|
| (20, 8) | +13 | far west |
| (25, 8) | +35 | ORFET cluster conflict |
| (30, 8) | +20 | |
| (35, 8) | +41 | |
| (40, 8) | **+5** | BEST |
| (42, 8) | +5 | tied best |
| (45, 8) | +5 | tied best |
| (50, 8) | +14 | |
| (38, 8) | +13 | |
| (46, 8) | +10 | |
| (45, 12) | +11 | |
| (50, 12) | +16 | |

**Best candidates**: (40, 8), (42, 8), (45, 8) at +5 placement-only.

## CRITICAL CAVEAT

The +5 result is PLACEMENT ONLY. USART6_TX/RX traces (19+23 F.Cu + 7+4 B.Cu = ~53 segments) still route to OLD J10 position (54, 8). Implementing path (c) requires full USART6 re-route — significantly higher cost than placement test suggests.

## Plan revision — switch to master option (a)

Re-examining USB south detour cascade (+52 in 6e test):
- USART6_TX L2 vertical at X=45.91 is WEST of USB south corridor X=53-72
- USART6 doesn't actually block USB south detour directly
- The Y=22 blockers in X=53-72 are: +5V L2 diagonal + +3V3_IMU_PRE + I2C2_SDA

**Conclusion**: Step 2 may not need full USART6 re-pin/re-place. Master's option (a) "Push USART6_TX vertical to X=42" is surgical 1-segment move; option (c) full J10 re-place is heavier than needed.

## Step 2 next-session pickup

Execute master option (a): move USART6_TX L2 vertical from X=45.91 to X=42 (~1hr). Verify corridor freed.

May also need: Step 2b — re-route +5V L2 diagonal that crosses Y=22 USB corridor (separate sub-step).

## Multi-session WIP discipline

Step 1 v2 BATT2 LANDED at f8a97e7. Step 2 next session.
