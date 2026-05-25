# Plane-stitch GUI hand-off — 28 residual plane-net vias

> Quick GUI session task (~15 min). Per master 2026-05-21: autonomous
> push-and-shove is impractical; these need KiCad's interactive router.

**Branch / commit baseline**: `sim/step6-precursor-reroute` @ commit `19ceed4`
**Board file**: `hardware/kicad/novapcb-layout-v2/novapcb-layout-v2.kicad_pcb`
**State going in**: 0 DRC errors / 31 unconnected items / 102 of 130 plane pads stitched.

## What to do per residual

For each row below: place a small via (0.40 mm pad / 0.30 mm drill, JLC advanced spec — already the project default) at-or-near the listed pad center, using KiCad's interactive router push-and-shove to nudge the listed conflicting signal segment(s) out of the way. Net assignment must match the plane net listed.

After all 28 are placed:
- Run DRC (Tools → DRC). Expect **0 DRC errors, 0 unconnected items**.
- Refill zones (Edit → Fill All Zones).
- Save board. The Step 6 plane stitching is complete.

## Conventions

- **Layer**: outer copper layer the pad lives on (so via lands on it cleanly).
- **(x, y)**: pad center in mm.
- **Conflict net**: which existing signal segments need to be shoved by interactive router.
- Through-via 0.40/0.30 connects F.Cu↔B.Cu and lands on the appropriate inner plane layer automatically (GND→In1.Cu+In4.Cu, +3V3→In2.Cu, +3V3A→In2.Cu, +5V→In3.Cu).

## The 28 residuals

| # | Refdes.Pad | Net | (x, y) mm | Pad layer | Conflict net(s) |
|---:|---|---|---|---|---|
| 1 | FB1.2 | +3V3A | (29.6500, 29.5150) | F.Cu | SDMMC1_CMD (B.Cu) |
| 2 | C20.1 | +3V3A | (29.1700, 31.9400) | F.Cu | SDMMC1_CMD, SDMMC1_D3, USART1_TX (all B.Cu) |
| 3 | U1.11 | +3V3 | (31.8550, 29.0000) | F.Cu | HSE_IN (F.Cu) — crystal trace, route carefully |
| 4 | U1.19 | GND | (31.8550, 33.0000) | F.Cu | (no signal conflict — likely under-1mm-radius blocked by adjacent U1 pin pads only; nudge marginal) |
| 5 | U1.21 | +3V3A | (31.8550, 34.0000) | F.Cu | (no signal conflict — same, U1 pin density) |
| 6 | U1.27 | +3V3 | (34.0300, 37.6750) | F.Cu | SDMMC1_D2 (B.Cu) |
| 7 | U1.49 | GND | (45.0300, 37.6750) | F.Cu | (no signal conflict — U1 pin density) |
| 8 | U1.75 | +3V3 | (47.2050, 24.0000) | F.Cu | (no signal conflict — U1 pin density) |
| 9 | U1.99 | GND | (34.0300, 22.3250) | F.Cu | USART1_RX (B.Cu) |
| 10 | U1.100 | +3V3 | (33.5300, 22.3250) | F.Cu | (no signal conflict — U1 pin density) |
| 11 | C24.2 | GND | (51.3000, 27.1000) | F.Cu | MOT7, USART6_RX, USART6_TX (all B.Cu) — 4 conflicts |
| 12 | C18.2 | GND | (31.5400, 20.8100) | F.Cu | GPS1_RX, SPI1_MOSI (B.Cu) |
| 13 | R3.2 | GND | (30.1600, 24.6800) | F.Cu | USART1_TX (B.Cu) |
| 14 | C23.2 | GND | (40.0100, 20.8100) | F.Cu | SWDIO (B.Cu) |
| 15 | U3.8 | +3V3 | (71.1125, 30.7500) | F.Cu | I2C2_SDA (B.Cu) — see if Step-5 resA-bridge area still has free B.Cu room |
| 16 | C17.2 | GND | (34.3600, 20.8100) | F.Cu | GPS1_RX, I2C1_SCL, I2C1_SDA (all B.Cu) |
| 17 | Y1.2 | GND | (51.9200, 30.8500) | F.Cu | USB_DP (B.Cu) — careful, USB pair; minor nudge OK |
| 18 | C11.1 | +3V3 | (33.4000, 39.1900) | F.Cu | SDMMC1_CMD, SDMMC1_D3 (B.Cu) |
| 19 | C11.2 | GND | (34.3600, 39.1900) | F.Cu | SDMMC1_CMD, SDMMC1_D3 (B.Cu) |
| 20 | C12.1 | +3V3 | (36.2300, 39.1900) | F.Cu | SDMMC1_CMD, SDMMC1_D3 (B.Cu) |
| 21 | C12.2 | GND | (37.1900, 39.1900) | F.Cu | SDMMC1_CMD, SDMMC1_D3 (B.Cu) |
| 22 | R53.1 | +3V3 | (47.9600, 26.1300) | B.Cu | USB_DM, USB_DP (F.Cu) — USB hand-routed pair area |
| 23 | J2.3 | GND | (40.1050, 37.7250) | B.Cu | (no signal conflict — pin density in connector) |
| 24 | J2.4 | +3V3 | (39.0050, 37.7250) | B.Cu | (no signal conflict — pin density) |
| 25 | J2.6 | GND | (36.8050, 37.7250) | B.Cu | (no signal conflict — pin density) |
| 26 | R54.1 | +3V3 | (47.9600, 28.0600) | B.Cu | SDMMC1_D1 (F.Cu) |
| 27 | R52.1 | +3V3 | (30.0800, 28.0600) | B.Cu | GND (F.Cu) — a GND trace; nudge it slightly to make room |
| 28 | R55.1 | +3V3 | (30.0800, 24.1900) | B.Cu | BOOT0 (F.Cu) |

## Special notes

- **#3 (U1.11 — HSE_IN crystal trace)**: crystal traces are EMI-sensitive. Push HSE_IN minimally; if possible, place the +3V3 via on the side of U1.11 away from HSE.
- **#11 (C24.2 — 4 conflicts)**: tightest case. May need to push 2-3 traces simultaneously. Alternatively if push-and-shove can't resolve all 4, accept a small fanout stub (≤1 mm) to a clear via spot.
- **#17 (Y1.2 — USB pair adjacent)**: the USB B.Cu segment passes close. Place the via without disturbing USB pair geometry (W=0.30/S=0.10).
- **#22 (R53.1 — USB pair on F.Cu)**: similar — pair geometry is sacred, the GND via here goes on B.Cu next to where the USB pair is on F.Cu, so it shouldn't actually conflict; verify in the GUI.

## Acceptance

- 0 DRC errors
- 0 unconnected items (all 28 stitched + the 3 stragglers from rounding noise)
- Save → commit on a fresh branch (`gui/plane-stitch-cleanup` is suggested).

## Why this is a GUI task

KiCad's interactive router has push-and-shove. The autonomous tooling here does not. Each of the 28 sites is a local rearrangement: drop a via, nudge 0-4 traces by < 1 mm. Push-and-shove is the right tool for this job. The autonomous routing exhausted the "no-shove" methods (Freerouting hangs with constrained layers; coded-shove would require ~90 min to implement crudely with cascade risk). 15 min of interactive routing here vs hours of autonomous coding — correct tool choice.
