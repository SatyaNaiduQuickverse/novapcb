# PR — CRSF re-pin USART6 → UART4 (PA0/PA1 west edge): closes #56 CRSF

> Branch `fw/crsf-uart4-repin` off `sch/option-b-buck` (f3c28f9). Executes the
> master-locked CRSF re-pin (`docs/CRSF_REPIN_PROPOSAL.md`): the CRSF RC UART
> moves from USART6 (PC6/PC7, NE-saturated, empirically unroutable) to UART4
> (PA0/PA1, west edge). **CRSF now routed** — closes the flight-critical 1-of-3
> of #56 (Telem + SWD deferred per `TELEM_V1_DEFER.md` / `SWD_TEST_PADS_V1.md`).

## 1. Why (the #56 structural finding)

The 6 #48 MCU-pad escapes were empirically unroutable (4 attempts: scoped FR
0/6 ×2, manual SWCLK 16-violation, ≤1mm SDMMC nudge → 3 violations + FR still
0/6) — the **MCU east edge** (X52.67) is over-subscribed (USB + SDMMC + CAN +
BATT + sense all converge). CRSF is the only flight-critical one (RC link). Re-
pinning it to a **west-edge UART** moves its escape away from the jam.

PA0/PA1 (UART4 AF8) chosen per the verified pad audit: west edge (X37.33),
cleanest escape (survey: scattered west obstacles + clear top traverse to J10,
vs the impossible NE wall). The ~63mm route is benign — CRSF 420 kbaud is
electrically short at any plausible length (`SIGNAL_CLASS_SI_JUSTIFICATION.md`).

## 2. Changes

**hwdef.dat (4 edits):**
- Removed `PC6/PC7 USART6_TX/RX`; added `PA0 UART4_TX` / `PA1 UART4_RX` (AF8).
- `SERIAL_ORDER`: `…UART8 USART6 OTG2` → `…UART8 UART4 OTG2` (SERIAL5 slot
  unchanged positionally; SERIALn_PROTOCOL=23/RCIN index preserved).
- USART6 block → "FREE" note (PC6/PC7 revert to unused GPIOs).

**SKiDL (`crsf_usb_3g.py`):** CRSF net MCU connection `mcu["PC6"]`/`["PC7"]` →
`mcu["PA0"]`/`["PA1"]`. (Net labels kept as USART6_TX/RX — cosmetic legacy;
physical pins are PA0/PA1.)

**Board (`novapcb-stepwise.kicad_pcb`):** CRSF nets re-pinned U1.63/64 (PC6/7) →
U1.22/23 (PA0/1); routed via scoped Freerouting (west-up-then-across-top to J10).
- USART6_TX (PA0): 26 tracks, 6 vias, 63.6 mm, F.Cu+B.Cu
- USART6_RX (PA1): 27 tracks, 4 vias, 63.3 mm, F.Cu+B.Cu

The west-edge re-pin made FR route the pair cleanly (843 score, 0 unrouted) —
the same FR that returned 0/6 on the east-edge pads. Confirms the #56 root cause
was the east-edge pad jam, not the long-haul.

## 3. Verification (master's gate set)

- **ArduPilot `waf` build:** **PASS** — `copter` finished successfully (6m10s),
  RC=0, fresh `arducopter.bin` (novapcb-v1, not SITL). UART4 in generated
  hwdef.h; no pin-redefine/bad-pin/missing-symbol errors (`-Werror` on).
- **DRC:** 12 = baseline (all `.kicad_dru`-covered); **0 new** violations.
- **CRSF connectivity:** USART6_TX/RX unconnected = **0** (fully routed).
- **Unconnected −2** (CRSF TX/RX closed; Telem/SWD remain by design).
- **USB diff pair (PR #75) + SPI1: untouched** — 0 violations touching them.
- **Cluster walk:** both nets F.Cu-over-In1 / B.Cu-over-In4, PASS.

## 4. Scope

Closes **#56 CRSF (1 of 3)**. Telem (USART1) deferred to v2 with USB-CDC ground
link (`TELEM_V1_DEFER.md`); SWD deferred to test-pads + USB DFU
(`SWD_TEST_PADS_V1.md`). Both are Rule-17 tracked deferrals, not silent drops.
