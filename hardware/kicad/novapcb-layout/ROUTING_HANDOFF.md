# Phase 4 routing handoff — 17 nets for Sai's KiCad 9 GUI pass

**Status**: Freerouting cleared 96.1% of the board (771 tracks + 153 vias). 17 signal nets remain incomplete — they need hand-routing in KiCad GUI. After this pass + DRC 0-errors confirmation, Phase 4f exports gerbers/drill and the design is fab-ready.

---

## How to open

```
KiCad 9 GUI required (not KiCad 8 — file format incompatible)
File: hardware/kicad/novapcb-layout/novapcb-layout.kicad_pcb
Project: hardware/kicad/novapcb-layout/novapcb-layout.kicad_pro
```

If you've cloned the repo and `git pull`'d the merged main, you're ready. The .kicad_pro carries the net classes + DRC ruleset already; nothing to set up.

---

## What's already routed — DO NOT MOVE

- **771 tracks + 153 vias from Freerouting**, locked. Routing-around them only; do not rip them up.
- **All 7 copper zones** (In1.Cu GND, In2.Cu +3V3/+5V/VBAT/+3V3A, B.Cu GND fill) — they auto-connect plane-served pads. Don't worry about routing GND/+3V3/+5V/VBAT power nets; they're plane-served.
- The locked tracks have `(locked yes)` in the file. KiCad GUI marks them with a small lock icon. Click "B" to fill zones if they appear unfilled.

---

## The 17 nets to route

Below: each net, the unconnected endpoints (`refdes.pad`), the net class, and any geometry constraint. Coordinates are in mm (KiCad world coords).

### USB diff pair — IMPEDANCE-CONTROLLED, ROUTE TOGETHER

**Critical**: this is the 90Ω differential pair. Route D+ as a length-matched pair next to D- (which Freerouting already routed). USB 2.0 is tolerant but mismatch costs SI margin.

| Net | Class | Pads to connect | Geometry |
|---|---|---|---|
| **USB_DP** (only D+ failed; D- is already routed) | `USB_diffpair` | `U5.6` (11.64, 30.05) F.Cu → `U1.71` (25.68, 15.00) F.Cu | **W=0.25mm trace / S=0.10mm gap** (Hammerstad-Jensen for 90Ω diff on 4a stackup F.Cu over In1.Cu GND, h=0.21mm, εr=4.3). Route ALONGSIDE the existing USB_DM track from U5.4 to U1.70 — keep parallel + length-matched. The class is already set; KiCad's diff-pair router (`Route → Differential Pair`) gives you that geometry from the netclass automatically. |

### HSE crystal — short + isolated

The MCU clock crystal. Critical for boot.

| Net | Class | Pads to connect | Hint |
|---|---|---|---|
| **HSE_OUT** | Default | `Y1.3` (29.60, 18.65) F.Cu → `U1.13` (10.32, 19.00) F.Cu → `C25.1` (28.02, 23.50) F.Cu (load cap N) | Short, direct. Keep AWAY from switching nets (DShot, USB). The Y1↔U1 trace is the load-bearing one for the MCU's HSE oscillator. C25 is the load cap and connects to HSE_OUT alongside Y1. |

### SDMMC bus — F.Cu↔B.Cu transitions

microSD socket J2 is on B.Cu. SDMMC pullup resistors R51-R55 are also on B.Cu. MCU is F.Cu. Every SDMMC net needs a via. Class set to `SDMMC` (0.15mm).

| Net | Class | Pads to connect | Hint |
|---|---|---|---|
| **SDMMC1_CLK** | SDMMC | `U1.80` (22.00, 11.32) F.Cu → `J2.5` (19.62, 1.27) B.Cu | Via from F.Cu MCU south down to B.Cu, route to J2. **CLK should be shortest of the 6** — clock skew. |
| **SDMMC1_CMD** | SDMMC | `U1.83` (20.50, 11.32) F.Cu → `J2.2` (16.32, 1.27) B.Cu → `R51.2` (15.00, 25.49) B.Cu | T-junction: route MCU→J2, branch to R51 on B.Cu. |
| **SDMMC1_D0** | SDMMC | `U1.65` (25.68, 18.00) F.Cu → `J2.7` (21.82, 1.27) B.Cu → `R52.2` (17.00, 25.49) B.Cu | MCU east-side pin; via then B.Cu route. |
| **SDMMC1_D1** | SDMMC | `U1.66` (25.68, 17.50) F.Cu → `J2.8` (22.93, 1.27) B.Cu → `R53.2` (19.00, 25.49) B.Cu | Same pattern as D0. |
| **SDMMC1_D2** | SDMMC | `U1.78` (23.00, 11.32) F.Cu → `J2.9` (23.88, 1.27) B.Cu → `R54.2` (21.00, 25.49) B.Cu | MCU south pin → J2 → R54 pullup. |
| **SDMMC1_D3** | SDMMC | `U1.79` (22.50, 11.32) F.Cu → `J2.1` (15.22, 1.27) B.Cu → `R55.2` (23.00, 25.49) B.Cu | Same. |

**SDMMC routing hint**: Keep the 4 data lines (D0-D3) roughly length-similar (skew matters at SDR50 + higher; at our current 12.5 MHz it's tolerant, but good practice).

### ESC outputs — MOT1, MOT2, MOT3

8 ESC solder pads on bottom edge. MOT4-MOT8 already routed by Freerouting; MOT1-3 not.

| Net | Class | Pads to connect | Hint |
|---|---|---|---|
| **MOT1** | DShot | `U1.34` (16.00, 26.68) F.Cu → `J11.1` (7.50, 2.00) F.Cu | MCU N pin (PB0 TIM3_CH3) to bottom-edge ESC pad. Long N→S route; route AWAY from analog (Mauch sense lines on MCU west). |
| **MOT2** | DShot | `U1.35` (16.50, 26.68) F.Cu → `J12.1` (10.50, 2.00) F.Cu | Same pattern, adjacent pad. |
| **MOT3** | DShot | `U1.22` (10.32, 23.50) F.Cu → `J13.1` (13.50, 2.00) F.Cu | MCU W pin (PA0 TIM2_CH1). Route south. |

### Telem UART — USART1_RX

| Net | Class | Pads to connect | Hint |
|---|---|---|---|
| **USART1_RX** | Default | `U1.69` (25.68, 16.00) F.Cu → `J3.3` (35.35, 22.38) F.Cu | MCU east → J3 telem connector E side. Short hop on F.Cu. |

### Baro I²C — B.Cu transitions

DPS310 U4 is on B.Cu at (20.5, 28). MCU + pullups (R11/R12) on F.Cu. Need vias.

| Net | Class | Pads to connect | Hint |
|---|---|---|---|
| **I2C2_SDA** | Default | `U4.3` (20.18, 27.20) B.Cu — link to the existing F.Cu net (already connects R11 + U1.47) | One via to bring B.Cu pad up to F.Cu net (the rest is already routed). |
| **I2C2_SCL** | Default | `U4.4` (19.52, 27.20) B.Cu — link to existing F.Cu net (R12 + U1.46) | Same — one via. |

### SWD — J9 on B.Cu

J9 SWD header is on B.Cu under MCU. MCU SWD pins are on F.Cu. Vias needed.

| Net | Class | Pads to connect | Hint |
|---|---|---|---|
| **SWDIO** | Default | `U1.72` (25.68, 14.50) F.Cu → `J9.2` (16.05, 18.46) B.Cu | One via + short B.Cu route. |
| **SWCLK** | Default | `U1.76` (24.00, 11.32) F.Cu → `J9.4` (16.05, 19.73) B.Cu | Same. |
| **NRST** | Default | `U1.14` (10.32, 19.50) F.Cu (already routed to C26) → `J9.10` (16.05, 23.54) B.Cu | One via to extend the existing F.Cu NRST trace to J9. |

---

## DRC + acceptance

After routing all 17 nets:

```bash
cd hardware/kicad/novapcb-layout
kicad-cli pcb drc --severity-error --units mm novapcb-layout.kicad_pcb
```

**Target: 0 violations + 0 unconnected items.** The DRC ruleset already accommodates:
- min track 0.13mm / min clearance 0.13mm (JLCPCB 4-layer free spec)
- min via 0.45mm / min drill 0.25mm
- min annular 0.05mm
- min copper-edge clearance 0.0mm (mid-mount USB-C pads at edge expected)

`courtyards_overlap` is severity=warning (mini-FC density convention — decoupling caps overlap MCU courtyards by design). `unconnected_items` is severity=warning too, but should be 0 after routing.

---

## After routing

1. Save the .kicad_pcb (KiCad GUI: File → Save).
2. Commit + push the routed board. The repo's `novapcb-layout.kicad_pcb` is the load-bearing artifact; commit message can be terse, e.g. `Phase 4 GUI routing — 17-net residual completed`.
3. Phase 4f gerber/drill export is pre-staged (`run_gerber_export.py`) and will fire on the routed board.

---

## Reference

- Phase 4e Freerouting result: PR #48 (merged) — 96.1% routed, 0 DRC errors (after `min_through_hole_diameter` rule fix to 0.25mm).
- USB 90Ω geometry derivation: PR #47 (Phase 4d) — Hammerstad-Jensen calc on the 4a stackup.
- Net class definitions: `novapcb-layout.kicad_pro` "net_settings" section.
- Open questions: `docs/OPEN_QUESTIONS.md` (especially `phase4a-1` — ICM-42688-P land pattern, still HARD carry-forward before Phase 6m DFM).
