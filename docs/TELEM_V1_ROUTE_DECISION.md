# Telem (USART1) — Sai overrides defer, route in v1

> **Status:** Sai-decided 2026-05-28: route J3 connector + USART1_TX/RX in v1. Master defer recommendation (`docs/TELEM_V1_DEFER.md`) overturned.
> **Reason:** Sai's call. "should do j3".

---

## What this commits to

Route the 4 J3 nets (USART1_TX, USART1_RX, +5V to J3.1, GND to J3.4) for v1. J3 connector stays in the .kicad_pcb. USART1 in hwdef.dat unchanged.

## Scope as a work item

USART1_TX/RX were in the original #56 east-edge structural blocker (per `docs/CRSF_TELEM_SWD_ROUTING_ANALYSIS.md`):
- USART1_TX U1.68 (52.7, 32.5) → J3.2 (93.1, 36.1) — ~40mm east traverse
- USART1_RX U1.69 (52.7, 32.0) → J3.3 (94.4, 36.1) — same direction

The east-edge MCU pad escape was unroutable at pre-#56 board state. Board state has changed significantly since (CRSF re-pinned, full Phase 4d-redux landed, dense W/SW pocket re-spread, via-in-pad capability authorized).

## Execution approach (next-session worker)

**Step 1 — Try existing pin assignment first.**
Worker surveys current MCU east-edge state at head 5f3dd18 (+ wherever IMU3_INT1 + D5 land). If the post-Phase-4d-redux board has freed routing channels at MCU east edge Y=32-32.5, attempt the route on PA9/PA10 directly. The east-edge density has changed substantially.

**Step 2 — If still blocked, re-pin like CRSF was.**
The CRSF re-pin pattern (PR #120) is the proven template: USART6 → UART4 PA0/PA1 west edge. Telem could similarly re-pin from USART1 (PA9/PA10) to another UART on a less-saturated MCU edge.

**Candidate USART/UART alternates** (master would research; subject to verify-the-current-hwdef per `feedback-verify-hwdef-before-authorizing`):
- USART1 alternates: PB6/PB7 (USED — I²C1), PA9/PA10 (current)
- USART2: USED (GPS1)
- USART3: USED (GPS2)
- UART4: USED (CRSF post-#120, PA0/PA1)
- UART5: alt pins available
- UART7: PE7/PE8 free
- UART8: USED (PE0/PE1 spare console)

If Step 2 needed, master surfaces the re-pin proposal similar to `docs/CRSF_REPIN_PROPOSAL.md` pattern, worker executes SKiDL+hwdef+route.

**Step 3 — If both Steps 1 and 2 fail, re-surface to Sai.**
The 1+2 path is bounded; if neither closes, the board is genuinely too dense for an external 4-pin Telem and Sai would need to weigh tradeoffs (drop a different connector, expand board, etc.).

## Sequence

Telem routing is queued AFTER:
1. IMU3_INT1 (currently in flight)
2. D5 +3V3_IMU 5 gaps
3. SWD test-pads swap (small, per `docs/SWD_TEST_PADS_V1.md` — SWD defer is master-decided 2026-05-28)
4. C96 value swap 10nF → 100nF (small, per `docs/LSM6DSV16X_DECAP_CLOSURE.md` Path A — master-decided 2026-05-28)

Then Telem closure work.

## Gates

Same as all Phase 4d-redux PRs:
- `audit_unconnected_per_net.py`: USART1_TX + USART1_RX = 0 unconnected
- DRC ≤ baseline + 0 net-new
- `waf copter` PASS
- No collateral on hands-off list

## What's NOT in scope

This doc covers ROUTING J3 in v1. It does NOT cover:
- Routing the SWD J9 connector — Sai decided 2026-05-28 to use test-pads + DFU instead (saves dense east-edge routing). See `docs/SWD_TEST_PADS_V1.md`.
- Telem peripheral firmware configuration — USART1 stays as declared in hwdef.dat; runtime `SERIAL1_PROTOCOL` parameter is set by Sai later.

## Estimate

Step 1 (try current pins): ~30-60 min worker survey + route attempt. If post-Phase-4d-redux state has freed enough corridor (which is likely since CRSF moved off USART6/PC6-PC7 already), this lands.

Step 2 (re-pin if blocked): ~1-2 hr (master research + worker execute, same pattern as PR #120).

Combined budget: ~1-3 hr to close Telem routing.
