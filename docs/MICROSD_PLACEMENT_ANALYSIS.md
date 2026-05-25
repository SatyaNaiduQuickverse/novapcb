# microSD Subsystem — Placement + Routing Constraint Analysis

> **Status**: DRAFT for master sign-off (autonomous mode 2026-05-24).
> NO LAYOUT TOUCH until sign-off.
> **Branch**: TBD (likely `hw/microsd-placement-routing` off CAN merge head).
> **Sub-step**: queued behind CAN.

---

## 1. Component inventory

| Ref | Part | Footprint | Pads | Function |
|---|---|---|---|---|
| J2 | DM3AT-SF-PEJM5 | Hirose push-push SDMMC socket | 11 (9 sig + shield) | microSD slot |
| (TBD) | 22kΩ × 5 0402 | R_0402 | 2 each | SDMMC pulls on CMD + D0-D3 |

**J2 BBOX: 15.75 × 24.15mm** — LARGEST connector on the board. Footprint
extends well beyond pad area (includes mechanical card-guides + push-push
spring + shield grounding).

## 2. Net contract (6 nets + power)

| Net | Source (MCU edge) | Dest |
|---|---|---|
| SDMMC1_D0 | PC8 pad 65 E (52.67, 34.0) | J2.7 |
| SDMMC1_D1 | PC9 pad 66 E (52.67, 33.5) | J2.8 |
| SDMMC1_D2 | PC10 pad 78 N (50.0, 27.32) | J2.9 |
| SDMMC1_D3 | PC11 pad 79 N (49.5, 27.32) | J2.1 |
| SDMMC1_CLK | PC12 pad 80 N (49.0, 27.32) | J2.5 |
| SDMMC1_CMD | PD2 pad 83 N (47.5, 27.32) | J2.2 |
| +3V3 | (zone) | J2.4 |
| GND | (zone) | J2.3 + J2.6 + shield |

MCU pin distribution: 2 EAST (PC8, PC9) + 4 NORTH (PC10, PC11, PC12, PD2).

## 3. Length matching

Per SDMMC spec at 12.5-25 MHz (SDR12 to SDR25 typical):
- Skew tolerance: ≤±0.5mm between D0-D3 group
- CLK to data: ≤±2mm (CLK is reference for sampling)
- CMD: independent, looser (≤±5mm)

This is the FIRST length-matched net group in the design. Routing must
honor it — flag for length-tune step after initial route.

## 4. Zone candidates

### A: East band NE (J2 X=88-103, Y=15-40) — recommend
- East-edge mount, card-slot exits east (user inserts card from east side of board)
- Bbox 15.75 × 24.15 fits if J2 anchor at (~95, 27)
- Mounting hole H2 at (101.75, 3.25) — Y=3.25 + 6mm keep-out = Y≥9.25, J2 starts at Y≈15, clear
- CAN block (proposed (94, 22)) — **CONFLICTS** with J2 at (95, 27). Need re-plan.

### B: East band south (J2 X=88-103, Y=55-80)
- J2 anchor at (~95, 67) — south of board mid
- Clear of CAN, GPS, CRSF, TELEM, SWD
- Card insert direction: east (same as A)
- Fanout reach to MCU: 30-40mm (good)
- **Recommend (B)** to deconflict with CAN.

### C: South band (J2 X=20-35, Y=65-85)
- South-edge mount, card insert south
- Conflicts with J11 ESC connector + USB-C (X=84)
- Atypical card direction
- Reject.

**Recommend B: East band south Y=55-80.**

## 5. Proposed placement (provisional)

| Ref | Anchor (X, Y) | Rotation | Rationale |
|---|---|---|---|
| J2 | (95, 67) | 0° | East band south, harness/card exit east |
| R_CMD_pullup | (~88, 65) | — | 22k pull, near J2.2 |
| R_D0_pullup | (~88, 67) | — | 22k pull |
| R_D1_pullup | (~88, 69) | — | 22k pull |
| R_D2_pullup | (~88, 71) | — | 22k pull |
| R_D3_pullup | (~88, 73) | — | 22k pull |

5 × 22kΩ 0402 pulls west of J2.

## 6. Fanout reach + corridor analysis (Rule 18 + 19)

### Long-distance fanout

MCU N pads (4 nets) → J2 at (95, 67):
- PC10 at (50.0, 27.32) → J2.9 at ~(95, 67): ΔX=45, ΔY=40. Manhattan ~85mm.
- PC11, PC12, PD2 similar lengths.

MCU E pads (2 nets) → J2:
- PC8 at (52.67, 34.0) → J2.7 at ~(95, 67): ΔX=42, ΔY=33. ~75mm.
- PC9 at (52.67, 33.5) → J2.8 at ~(95, 67): ~75mm.

**Total path 75-85mm per net.** This is long but within SDMMC SI tolerance
(at 12.5MHz f0, signal wavelength on FR4 ~12m → ¼λ ≈3m. Trace length
matters for skew but not for RF resonance.)

### Length matching budget

To match D0-D3 within ±0.5mm:
- D0/D1 (MCU east) + D2/D3 (MCU north) have DIFFERENT path lengths from MCU
- Use **serpentine** tuning on shorter paths to match the longest

Worst-case match-tune: max(D0..D3) at 85mm → add 5-10mm serpentine to
shorter nets to bring all 4 to 85mm.

CLK to data: aim CLK ±2mm of data avg. Same serpentine approach.

### Corridor pre-flight (Rule 18 + 19) — TODO at placement time

Must enumerate:
- All component pads in X=50..95 Y=27..67 corridor (~45×40 box)
- All routed nets in same corridor
- 6 SDMMC nets + length-match serpentine need clear corridor width

Post-H↔C-merge corridor density will be HIGHER. Allow for layer-split
fallback if F.Cu corridor saturates.

## 7. Power for J2

- J2.4 = +3V3 (card VDD)
- J2.3 + J2.6 = GND
- Shield = GND
- Local +3V3 decap: 1× 100nF + 1× 10uF tantalum/electrolytic at J2.4
  per SD Association recommendation

Need to add to SKiDL if not already (check power_sd_swd_3h.py).

## 8. Mirror analysis

microSD = SINGLE_INSTANCE per R3. EXEMPT from MIRROR_PAIR.

## 9. Decisions for sign-off

1. Zone B (east-band south Y=55-80) vs revisit A with CAN re-placement
2. J2 anchor (95, 67) — ±5mm flexibility
3. Length matching: tolerance ±0.5mm D0-D3 (recommend) vs looser ±1mm
4. Pull resistor placement: tight cluster west of J2 vs distributed near each net pad

## 10. Gates plan

1. DRC ≤ baseline + 0 net new
2. STACKUP-SPEC-MATCH PASS
3. MIRROR_PAIRS 11/11
4. DECOUPLING: J2.4 decap within 3mm of pin
5. **NEW length-matching gate** (codify if cheap): SDMMC1_D0..D3 lengths within ±0.5mm of avg; CLK within ±2mm of data avg; CMD within ±5mm

---

**Awaiting master sign-off after CAN + H↔C PRs land.**
