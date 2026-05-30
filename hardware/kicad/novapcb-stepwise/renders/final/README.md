# Final board renders — novapcb-stepwise (post 13-PR session)

Captures the FINAL v1.1 layout state at `sch/option-b-buck` head 7af8122
(after CAN / microSD / GPS / BUZZER / HSE-crystal / IMU-decap-audit / DRU /
T3-partial / IMU-slot / DFM / MOT1-2 / Sims / CRSF-analysis / BOM-regen).

Board: 6-layer JLC06161H-7628, 105 × 85 mm, STM32H743VIT6 FC.

| File | View | Notes |
|---|---|---|
| `top.png` / `top.svg` | **F.Cu** copper (top) | central MCU fanout + routing to edge connectors |
| `bot.png` / `bot.svg` | **B.Cu** copper (bottom, mirrored) | B.Cu-primary motor + signal returns |
| `in1.svg` | **In1.Cu** — GND (primary) | F.Cu reference plane |
| `in2.svg` | **In2.Cu** — +5V_BEC | power plane |
| `in3.svg` | **In3.Cu** — +3V3 | power plane |
| `in4.svg` | **In4.Cu** — GND (secondary) | B.Cu reference plane |
| `3d_top.png` | 3D render, top side | assembled-board overview (kicad-cli render) |
| `3d_bot.png` | 3D render, bottom side | assembled-board overview |

Copper PNGs generated from the KiCad SVG export via cairosvg; 3D views via
`kicad-cli pcb render`. All layers exported board-area-only, fit-to-board.

Note: MOT7/8 + CRSF/Telem/SWD MCU escapes are unrouted by design / pending
task #56 — visible as missing traces near the MCU east edge.
