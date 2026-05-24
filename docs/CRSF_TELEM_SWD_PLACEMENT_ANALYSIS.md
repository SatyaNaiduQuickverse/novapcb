# CRSF + TELEM + SWD Subsystems — Combined Placement + Routing Analysis

> **Status**: DRAFT for master sign-off (autonomous mode 2026-05-24).
> NO LAYOUT TOUCH until sign-off.
> **Branch**: `hw/crsf-telem-swd-placement-routing`.

Combined because each is a simple single-connector subsystem with
2-3 UART/debug signals — analyzing together saves PR overhead.

---

## ⚠️ FLAG: J10 CRSF footprint discrepancy

`crsf_usb_3g.py:151` uses **`CRSF_solder_pad`** footprint, not JST-GH.
DECISIONS.md §7 mandates JST-GH for ALL connectors. This is the SAME
class of placeholder-vs-spec violation as the ESC J11 case (resolved
2026-05-24 in PR #80 by amending to JST-GH 10P).

**Recommend separate SAI-GATED SKiDL amend PR** (CRSF → JST-GH 4P
horizontal) before this CRSF placement sub-step proceeds. Or master
ratifies retaining solder_pad as an explicit DECISIONS.md §7
exception.

The remainder of this analysis assumes CRSF stays solder_pad OR
amends to JST-GH 4P (similar bbox in both cases — placement geometry
nearly identical).

---

## 1. CRSF (RC receiver UART)

### Components
- J10: 4-pin CRSF (currently `CRSF_solder_pad`, bbox 7.46 × 10.45mm) → flag §7
- TVS × 2 (USART6_TX + USART6_RX ESD)

### Nets
| Pin | Net | MCU pad |
|---:|---|---|
| 1 | +5V | (power) |
| 2 | USART6_TX | PC6 pad 63 E (X=52.67, Y=34) |
| 3 | USART6_RX | PC7 pad 64 E (X=52.67, Y=34.5) |
| 4 | GND | (zone) |

MCU pins: 2 EAST adjacent pads.

### Zone: East-band Y=15-25 (between A-subsystem J19 at Y=5 and CAN at Y=20-30)
- J10 at (~94, 18) — east band, north of CAN block
- Fanout reach: PC6/PC7 (52.67, 34) → J10 (~94, 20) = ~45mm

### Recommend (90° rotation if JST-GH for east entry direction).

---

## 2. TELEM (USART1)

### Components
- J3: JST-GH 6P (bbox 9.5 × 12mm) — already correct JST-GH ✓
- TVS × 2

### Nets
| Pin | Net | MCU pad |
|---:|---|---|
| 1 | +5V | (power) |
| 2 | USART1_TX | PA9 pad 68 E (X=52.67, Y=32.5) |
| 3 | USART1_RX | PA10 pad 69 E (X=52.67, Y=32) |
| 4 | — | (NC) |
| 5 | — | (NC) |
| 6 | GND | (zone) |

MCU pins: 2 EAST adjacent pads.

### Zone: East-band Y=35-50
- J3 at (~95, 42) — east mid
- Fanout reach: PA9/PA10 (52.67, 32) → J3 (~95, 42) = ~45mm
- Adjacent to USB-C (J1 already at (83.78, 30)) — same column orientation

---

## 3. SWD (debug ribbon)

### Components
- J9: 2x05 1.27mm SMD pin header (bbox 8.63 × 10.27mm)
- 5 active pins (+3V3, SWDIO, GND, SWCLK, GND, NC, NC, NC, GND, NRST)

### Nets
| Pin | Net | MCU pad |
|---:|---|---|
| 1 | +3V3 | (power) |
| 2 | SWDIO | PA13 pad 72 E (X=52.67, Y=30.5) |
| 3 | GND | (zone) |
| 4 | SWCLK | PA14 pad 76 N (X=51, Y=27.32) |
| 5 | GND | (zone) |
| 10 | NRST | NRST pad 14 W (X=37.33, Y=35.5) — **W EDGE!** |

MCU pins: 1 EAST (SWDIO) + 1 NORTH (SWCLK) + 1 WEST (NRST). Spread.

### Zone: East/NE corner Y=8-18 (top-right of board, beside J1 USB-C)
- J9 at (~97, 12) — small footprint, NE corner
- Fanout: SWDIO/SWCLK short to J9 (~15-30mm), NRST is FAR (~70mm from W edge)
- NRST will need long F.Cu trace W→E. Verify no obstacles. Could also
  route on B.Cu if F.Cu corridor busy.

### Pixhawk convention: SWD is usually a 10-pin debug ribbon in NE corner. Confirm.

---

## 4. Combined zone map (post-this-PR)

| Subsystem | Zone | Anchor |
|---|---|---|
| CAN (J20) | NE corner | (97, 5) |
| TELEM (J3) | East mid | (95, 42) |
| CRSF (J10) | East upper | (94, 18) |
| SWD (J9) | NE corner | (97, 12) |
| GPS (J5) | NW | (30, 6) |
| microSD (J2) | East south | (95, 67) |

**East band X=88-103 hosts CAN + TELEM + CRSF + SWD + microSD.** Dense
but manageable since each takes <17mm Y. Fits in Y=5..80 = 75mm with
margins.

Vertical layout (Y order top-to-bottom in east band):
- Y=5: J20 CAN (NE corner anchor)
- Y=12: J9 SWD
- Y=18: J10 CRSF
- Y=30: J1 USB-C (already placed)
- Y=42: J3 TELEM
- Y=67: J2 microSD

Gaps:
- Y=18-30: 12mm (room for CRSF + ESD)
- Y=30-42: 12mm (room for TELEM ESD)
- Y=42-67: 25mm (room for microSD pulls)

## 5. Decisions for sign-off

1. CRSF SKiDL amend to JST-GH 4P (Sai-gated separate PR) vs keep solder_pad
2. Connector anchor positions (CRSF, TELEM, SWD) — flex ±3mm each
3. SWD position NE vs central-north — Pixhawk DS-014 standard?
4. NRST long-trace (W→E) routing layer (F.Cu vs B.Cu)

## 6. Gates plan (each subsystem within its PR)

Same 5-gate template per subsystem. DRC ≤ baseline + 0 net new per
subsystem. Rule 18 + 19 corridor pre-flight at placement time.

---

**Awaiting master sign-off (sequencing: post-H↔C + CAN + microSD + GPS).**
