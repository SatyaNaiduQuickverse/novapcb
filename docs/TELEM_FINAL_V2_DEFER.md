# T20 Telem — FINAL v2-defer per Sai 2026-06-02 explicit override

> **Sai pick 2026-06-02:** α — accept Telem v2-defer for THIS item ONLY
> (explicit one-item override of the "no defers" mandate).
>
> Empirical campaign exhausted across 10+ paths over 2 days. MCU
> west-bridge structural saturation independent of board size. Sai
> picked α over (β) cascade nudges / (γ) MCU re-place / (δ) wire-tack
> hybrid.

## Empirical campaign log

| # | Approach | Outcome |
|---|---|---|
| 1 | Original 4-wall analysis (PR #130) | Walled NE + SE corridors saturated |
| 2 | 6f BATT2 sense re-pin alone | +104 DRC cascade |
| 3 | 6e USB diff pair re-route alone | +52 DRC cascade |
| 4 | 6c J3 re-place (16 candidates) | +36 to +96 DRC across all |
| 5 | T21 6a v1 SWD area exploration | +71 (different sub-problem but tests adjacent corridor) |
| 6 | T21 6a v2 SWD area exploration | +112 |
| 7 | T21 6c J9 re-place (10 candidates) | +52 best |
| 8 | Combined attack 5-step (Sai 2026-06-02 pick) | +108 DRC + USART1 partial-gap |
| 9 | Board grow 105×85 → 105×100 (Sai 2026-06-02 pick c) | Board outline ✓, but pad-level wall at MCU east edge persists |
| 10 | UART7 PE7/PE8 re-pin (south-east MCU corner) | hwdef ✓, but MCU south-bridge zone saturated by routes |
| 11 | (c1) CRSF cosmetic rename + (c2-g) BATT2 nudge attempt | Cascade +26 reverted; MCU west bridge zone fully saturated F.Cu + B.Cu |

## Structural conclusion

The 6-month-routed PCB has the MCU west-bridge zone (X=37-46, Y=29-42)
fully saturated across BOTH F.Cu Y-bands AND B.Cu X-columns AND via slots.
Every Y-band Y=29 through Y=42 is occupied by an essential live signal.

Per H743 LQFP-100 MCU pin alternates for UART/USART:
- PA9/PA10 (USART1 AF7): walled at east edge pad-level (0.5mm Y-window)
- PB6/PB7 (USART1 AF7): held by I²C1 (sensor bus)
- PB14/PB15 (USART1 AF4): held by SPI2 (IMU2 BMI088)
- PE0/PE1 (UART8 AF8): held (per master MCU free-pin survey PR #170)
- PC6/PC7 (USART6 AF7): east-side same wall as PA9/PA10
- PE7/PE8 (UART7 AF7): south-east corner, blocked by MCU south-bridge
  saturation when escape attempted

No MCU pin remap path that doesn't hit a wall.

## What v1 ships

- **J3 connector + D11/D12 ESD ASSEMBLED** at (54, 95) freed-area placement
- **UART7 hwdef declaration ACTIVE** (PE7/PE8 with stub routing to ESD)
- **UART7_TX/RX nets ADDED to INTENDED_DEFERRED** — won't show as real-latent in audit
- **Telem functional via USB-CDC MAVLink** (CLAUDE.md §2.1 canonical, already validated end-to-end with ArduPilot + drone-control container)

## v2 inheritance value

When v2 happens (post-flight, separate FMU + isolated-IMU board):
- J3 connector placement at (54, 95) preserved — v2 routes into known position
- UART7 PE7/PE8 hwdef preserved — v2 just routes
- Board grow to 105×100 preserved
- v2 starts from cleaner-than-v1 state

## Industry precedent

Compact Pixhawk-class FCs commonly ship without dedicated TELEM UART
hardware (Holybro Kakute, MatekH743 mini-FC variants). USB-CDC MAVLink
is the de-facto v1 Telem path. RC-CRSF (working) + USB-CDC + ELRS telem
back-channel cover the full v1 Nova drone stack per CLAUDE.md §2.1.

## Master process learnings (Rule 17 honesty)

- Sai's "no defers" mandate held for 24+ hours of focused work + ~10
  empirical paths. The defer is honest after exhaustive evidence.
- Defer of ONE item under explicit Sai override is materially different
  from systematic defers (which the mandate exists to prevent)
- Master made 2 errors today (PB14/PB15 cited wrong + CRSF severity
  cited wrong). Worker Rule-13 catches saved both. Master discipline
  improvement: quote source content directly, don't infer from net names.

## Cross-reference

- T20 task history: master burst-1 through burst-22 + worker hw/board-grow-105x100 branch
- Original v2-defer doc: `docs/TELEM_V1_DEFER.md` (now obsolete per the post-board-grow campaign)
- CLAUDE.md §1.1 lost-vs-6X table — UPDATE NEEDED to reflect Telem v2-defer is now Sai-explicit (was reach-failure before)
- HANDOFF, STATUS — UPDATE NEEDED
