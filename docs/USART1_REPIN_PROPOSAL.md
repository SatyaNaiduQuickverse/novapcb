# USART1 re-pin PA9/PA10 → PB14/PB15 (Telem J3 unblock)

> Master 2026-06-02 authorization after worker's pin-escape geometry analysis.
> 7 prior re-route attempts walled at MCU east edge pad-level constraint
> independent of board outline. PB14/PB15 are on MCU south-east corner with
> clean escape into the freed Y=85-100 south area from board grow.

## Trigger (empirical evidence)

Worker session 2026-06-02 (post-board-grow):
- J3 re-place to freed S area (54, 95): clean DRC ✓
- BUT routing USART1 from PA9/PA10 to J3 walled with +28 DRC
- Root cause: pad-level geometry at X=53-55, Y=31-34
  - Y-window between SDMMC1_CLK (Y=32.35) and pin 67 NC (Y=32.85) = 0.5mm
  - Required: 0.6mm for 0.20mm trace + 2×0.2mm clearance
  - **IMPOSSIBLE — board grow doesn't fix pad-level wall**
- West escape blocked by GPS1_RX vertical F.Cu at X=51.57

## Solution: USART1 alternate function pin remap

STM32H743 USART1 alternate function map (RM0433 §11.4):
- AF7: PA9 (TX) / PA10 (RX) — CURRENT, pad-level wall
- AF4: PB6 (TX) / PB7 (RX) — south-side, used by I²C1
- **AF7: PB14 (TX) / PB15 (RX) — south-east MCU corner, CLEAN**

PB14/PB15 are currently free (per `docs/attempt6/T20_MCU_FREE_PINS.md`).

## Worker scope

1. **hwdef.dat:**
   ```
   # USART1 (Telem) — re-pinned PA9/PA10 → PB14/PB15 (2026-06-02 board grow campaign)
   # Original PA9/PA10 pad-level wall: 0.5mm Y-window between SDMMC1_CLK + pin 67
   # PB14/PB15 are south-east MCU corner with clean B.Cu south escape into Y=85-100
   # freed area (Sai board-grow option c).
   PB14 USART1_TX USART1
   PB15 USART1_RX USART1
   # Remove old PA9 USART1_TX + PA10 USART1_RX lines.
   ```

2. **SKiDL re-gen + netlist update:**
   - Re-run novapcb.net generation
   - D11/D12 ESD diodes follow nets (no schematic re-place)

3. **Board route:**
   - PB14/PB15 → south escape via B.Cu → J3 at re-placed position in freed Y=85-100 area
   - No need to traverse the impossible Y=30-35 corridor

4. **Per-net audit ABSOLUTE:**
   - USART1_TX + USART1_RX REMOVED from INTENDED_DEFERRED
   - 0 real-latent target

5. **DRC + scope-creep cap:**
   - severity-error within 4/4 cap
   - No new DRU exceptions

## Sim impact

- **Sim 1 thermal**: no change (no heat sources moved)
- **Sim 2/3/4**: not touched
- **Sim 5 PDN**: stitching unchanged (USART1 isn't on power planes)
- **Sim 6h ADC**: not affected

USART1 PB14/PB15 are slow UART (115200 baud per CLAUDE.md §3.1 contract) — no SI concern.

## Why this is not a half-state

- USART1 PHYSICALLY ROUTED via PB14/PB15 → J3
- J3 connector + D11/D12 ESD assembled
- User plugs Telem cable → MAVLink works on USART1
- No strap-wire needed
- No v2-defer
- Hwdef pin change is a clean engineering call (alternate-function remap is standard STM32 design pattern)

## Reference

- STM32H743 RM0433 §11.4 USART1 AF map: AF7 PA9/PA10 and PB14/PB15
- Worker pin-escape analysis: empirical 0.5mm Y-window
- Master MCU free-pin survey: PR #170 (PB14/PB15 listed as free)
- Board grow option (c): Sai pick 2026-06-02, PR #174
- Worker branch: hw/board-grow-105x100 @ 14fc1e5
