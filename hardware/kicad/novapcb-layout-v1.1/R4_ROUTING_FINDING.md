# R4 routing — per-net DRC-aware re-route honest finding (2026-05-22)

## Summary

Per master's directive (2026-05-22) for per-net DRC-aware re-route in
batches with master review between:

- **Baseline state:** commit `1e91717` (-mp 30 v2.2.3 Freerouting output
  + planes + stitch). 906 tracks, 259 vias, 61 errors, 44 unconnected.
- **Result:** **0 of 36 residual nets routable** with template-based
  geometric strategies at strict 0.20mm clearance (matches Default
  netclass). PCB reverted to clean baseline — no routing changes
  committed.

This is the honest finding. The board is genuinely too congested in
residual-net regions for template-based routing to find clean paths.
Freerouting itself plateau'd at -mp 30 because the same constraints
apply to it.

## Strategy attempted

`per_net_router.py` (slow, full DRC per strategy) and `opt_router.py`
(fast, in-process collision check via `fast_check.py`) tried:

1. **Direct trace** same-layer
2. **L-horizontal-first** and **L-vertical-first** same-layer
3. **Via-pair + L** to opposite signal layer
4. **U-detour** at 3/5/8/10/12/15/20mm offsets, north/south/east/west,
   on pad layer and via-pair to opposite layer
5. **Plane-stitch with direct/L_HF/L_VF traces** at 8 directions × 5+
   scales (1.0 to 5.0mm offsets)

Total ~50 candidates evaluated per net. All failed fast_check at
0.20mm clearance.

Sample stuck-net congestion (from fast_check diagnostics):

- **R53.1 (+3V3 stitch, B.Cu @ 53.01, 33.00):** sandwiched between
  SDMMC1_D1 (south side) and SDMMC1_D2 (north side) tracks. East
  blocked by MOT7 tracks within 5mm.
- **U1.100 (+3V3 stitch, F.Cu @ 35.00, 27.32):** corner MCU pin.
  North-blocked by BATT_CURRENT_SENS track running across that area.
- **HSE_IN (U1.12 ↔ Y1.1):** 17.6mm trace required; goes across
  entire U1 pad field on both F.Cu and B.Cu. (Also: see schematic
  caveat below.)
- **Most IMU SPI / CAN / SDMMC / motor nets:** dense routing in MCU
  east edge and U-shape IMU island region from -mp 30 routing left
  no clean paths.

## Schematic concern flagged

While routing HSE_IN/OUT, noticed:
- U1 pin 12 = `PC14/OSC32_IN` (LSE 32 kHz crystal pin per STM32H743VIT6
  pinout)
- U1 pin 13 = `PC15/OSC32_OUT` (LSE)
- HSE 8 MHz crystal pins are 23 (PH0) and 24 (PH1)

Schematic uses net names `HSE_IN/HSE_OUT` and connects Y1 (8 MHz value)
to U1 pins 12/13 (which are LSE pins, not HSE). An 8 MHz crystal on
LSE pins will not oscillate properly; CPU will not boot from HSE.

**This is a schematic bug, not a routing problem.** Pinging master to
escalate — should be fixed before fab.

## What worked / what didn't (clean output)

- **Tried:** 1 plane-stitch via that initially passed fast_check at
  0.10mm clearance (R54.1) was REJECTED at 0.20mm — final DRC would
  have shown 2 new violations.
- **No false-positives commited.** Per master directive: "do not force
  a bad route."

## Per-net stuck list (for master vision-propose)

### Batch 1 — 5 stuck
- R53.1 (+3V3 stitch, B.Cu): sandwiched between SDMMC1_D1/D2
- R54.1 (+3V3 stitch, B.Cu): sandwiched between SDMMC1_D1/D2
- U1.100 (+3V3 stitch, F.Cu): north blocked by BATT_CURRENT_SENS
- HSE_IN (U1.12 ↔ Y1.1, 17.6mm): schematic LSE/HSE mismatch
- HSE_OUT (U1.13 ↔ C25.1, 18mm): schematic LSE/HSE mismatch

### Batch 1b — 3 stuck
- +3V3A (FB1.2 → C19.1, C20.1, R1.1): star route, 16-21mm legs

### Batch 2 — 6 stuck
- SDMMC1_CMD, SDMMC1_D0, SDMMC1_D3
- SPI1_SCK, SPI1_MISO, SPI1_MOSI

### Batch 3 — 6 stuck
- SPI3_SCK, SPI3_MISO, SPI3_MOSI
- IMU1_CS, IMU2_GYR_CS, IMU3_CS

### Batch 4 — 5 stuck
- CAN1_RX, CAN1_TX, GPIO_CAN1_SILENT
- IMU2_GYR_INT3, IMU3_INT1

### Batch 5 — 5 stuck
- MOT1, MOT2, MOT5
- HEATER_PWM, VCAP1

### Batch 6 — 5 stuck
- GPS1_RX, USART6_TX
- USBC_CC1, USBC_CC2
- GND (U1.19 ↔ U1.74)

### Batch 7 — pending (USB diff pair, dedicated controlled-impedance route)
### Batch 8 — pending (1-pad residuals: VREF_P, SPI2_MISO, I2C1_SCL,
   I2C1_SDA — investigate; may already be partially routed)

## Recommended next steps (master to choose)

1. **Vision-propose each stuck net.** Master draws hand routes per the
   stated fallback. ~36 hand-routes to design.
2. **Component re-placement.** Identify which placements force the
   congestion (likely the dense MCU east edge + IMU island bridge) and
   re-place. Re-run -mp 30, expect fewer residuals.
3. **KiCad interactive push-and-shove router.** P&S may find paths
   that template-based router cannot (mid-trace bends, layer-switch
   mid-segment, push existing tracks aside). Requires GUI session.

## Tools committed (reusable for any future routing)

- `per_net_router.py` — slow but rigorous: full DRC per strategy.
  ~30 min per batch.
- `opt_router.py` — fast: in-process collision check + final DRC.
  ~10 sec per batch.
- `fast_check.py` — in-process segment/via collision check.
  0.7ms per via check (~67000× faster than kicad-cli DRC).
- `batch_*.json` — per-batch net specifications.
- `batch_report.py` — generates markdown reports from log JSON.

## Renders

- `~/novapcb-preview-v1.1/render_baseline_top.png` (board top)
- `~/novapcb-preview-v1.1/render_baseline_bot.png` (board bottom)
- Served at `http://100.91.55.18:8771/`
