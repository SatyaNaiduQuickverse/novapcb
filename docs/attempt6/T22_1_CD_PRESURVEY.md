## T22.1 microSD CD escape pre-survey

J2 position: (95.0, 67.0)
U1 MCU center: (45.0, 35.0)

## Free MCU pins for CD assignment (per docs/attempt6/T20_MCU_FREE_PINS.md)

| Pin | Notes |
|---|---|
| PA4 | N (~pin 28) |
| PA8 | E (~pin 53) |
| PC6 | S (~pin 35) |
| PC7 | S (~pin 36) |
| PC13 | NW (~pin 7) |
| PC14 | NW (~pin 8) |
| PD3 | W (~pin 82) |
| PD5 | W (~pin 84) |
| PD7 | W (~pin 86) |
| PD12 | SW (~pin 60) |
| PD13 | SW (~pin 61) |
| PD14 | SW (~pin 62) |
| PD15 | SW (~pin 63) |
| PE7 | S (~pin 38) |
| PE8 | S (~pin 39) |
| PE10 | S (~pin 41) |
| PE12 | S (~pin 43) |
| PE15 | S (~pin 46) |

## Distance to J2 (95, 67) — approximate

Closest by physical position to J2 east-side at Y=67:
- East-edge pins (PA8 at ~pin 53, roughly (X=52+w/2, Y~=22)) would still need ~45mm trace
- PE7/PE8 already used by UART7 (Sai α v2-defer Telem)
- PC6/PC7 south-edge ~pin 35/36 = south-center MCU
- No pin is geometrically close to J2 (95, 67) — they all need ~30-50mm trace

## Likely wall pattern

Per worker session 2026-06-02: original T16 ALL 18 free MCU pins yield 47+mm trace.
Board grow Y=85-100 doesn't help here — J2 is at Y=67 (mid-board), not in freed area.
Even if J2 re-placed to (e.g.) (54, 92) freed area, still need ~50mm trace from any MCU pin.
LIKELY OUTCOME: same wall as original T16; v2-defer expected per pattern.
