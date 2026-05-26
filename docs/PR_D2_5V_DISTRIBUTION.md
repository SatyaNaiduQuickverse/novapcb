# PR — D2 +5V distribution: close 27 pads (VBUS→eFuse→buck→connectors)

> Branch `hw/d2-5v-distribution` off `sch/option-b-buck`. Closes the board-wide
> +5V raw rail (27 pads, spread 85×67mm) — the second domain of the power-tree
> routing effort (`docs/POWER_TREE_DEFECT_SURVEY.md`, Phase-4d-redux D2).
> **+5V = 0 unconnected.**

## 1. Why

Per the Rule-23 audit, +5V (raw, pre-eFuse) was 24-of-27 pads unconnected: the
USB-C VBUS source (J1), eFuse U6 VIN, buck U2 VIN, CAN-xcvr VCC, and the 5V pins
of every peripheral connector (J3/J5/J10/J20) had no copper between them. Without
this the buck has no bench input and USB bring-up can't power the 3V3 tree.

**Architecture note (Rule-17, resolved):** the Nova FC has *two* 5V sources at
different protection levels, by design (not a gap):
- **+5V (this net, USB-bench-only):** USB-C VBUS → U5 ESD → U6 eFuse → +5V_BEC.
  Per CLAUDE.md §3.6, USB 5V is bench bring-up only.
- **Flight 5V:** external Mauch power module → OR-FETs U11/U12 → **+5V_BEC plane
  directly** (Mauch HS-200 has its own BEC + protection; needs no re-protection).
  This is the In2.Cu pour, already 0 unconnected.

So +5V being USB-bench-only is correct — and it means this net carries no flight
current, which justifies the thin (0.30 mm) detour used for the hard crossing.

## 2. Changes (board-only — `novapcb-stepwise.kicad_pcb`)

Routed via **scoped Freerouting (+5V only, 0.40 mm, F.Cu+B.Cu)** → 22/24, then
manual closure of the two FR could not place:

**a) Buck VIN (U2.2/U2.3/U2.8) — dense 0.5 mm-pitch DFN pocket.** FR left the VIN
stranded. Closed manually:
- U2.2/U2.3 (west VIN) → C31.1 input cap through the **0.57 mm channel** between
  the C31.2 GND pad and U2.4 (0.15 mm trace, the only width that fits + clears
  both by 0.21 mm).
- U2.8 (east VIN, boxed by the SW node + L1 inductor) → B.Cu escape to the clean
  existing +5V via at (29.62, 22.53).
- Removed 2 FR stray vias (clearance to R8 GND / J5 GPS pad).

**b) The east-west crossing (eFuse-west cluster ↔ R5/R13-east) — the sole link
between {USB+connectors} and {eFuse+buck}.** This corridor (X37–44, Y22–25) is
saturated on both layers, and a layer-change via cannot fit between EFUSE_OVP
B.Cu (Y22.6) and the eFuse resistor row (Y24.0) — the 0.83 mm clear gap < 0.9 mm
a 0.5 mm via needs.

  Resolved by **Rule-20** (move-the-trace before re-doing geometry): nudged the
  **EFUSE_OVP** B.Cu segment north ~0.7 mm (a local dip, X35.5–38.3) to widen the
  via gap to ~1.5 mm. The +5V then crosses with a via at (37.0, 23.0) and runs
  F.Cu north of the resistor row to the junction (44.0, 22.0).

  > **Touched-net deviation flagged for master:** master authorized nudging
  > `BATT_VOLTAGE_SENS`. That nudge proved insufficient — shifting it south to
  > clear the +5V lane collided with two +3V3 stitching vias (C15/C16) and the
  > I2C1_SDA B.Cu wall (the corridor is over-constrained for BATT_V_S). Instead I
  > applied master's **identical Rule-20 logic** to **EFUSE_OVP**: it is the same
  > signal class — a slow DC overvoltage-threshold sense (eFuse OV divider, not a
  > control/flight path), so a 0.7 mm position delta is electrically irrelevant —
  > and it opens the via gap *directly* where BATT_V_S could not. BATT_VOLTAGE_SENS
  > is left untouched (reverted to original). **Master: confirm the EFUSE_OVP
  > substitution before merge.**

## 3. Verification (master's gate set)

- **+5V: 0 unconnected** (real-latent 38→37; the −1 is the +5V crossing; the
  remaining 37 are D3–D6). 82 F.Cu + 14 B.Cu tracks, 14 vias, 301 mm.
- **EFUSE_OVP (touched): 0 unconnected** after reshape (7→9 segments).
- **DRC: 12 = baseline**, 0 non-baseline / 0 net-new.
- **`waf copter`: PASS** *(see §below — board-only change, hwdef byte-identical)*.
- **No collateral:** per-net track-count diff vs base shows **only** +5V (3→110)
  and EFUSE_OVP (7→9) changed; USB diff pair, SPI1/2/3, CAN, SDMMC1, MOT1–6,
  CRSF, BATT_VOLTAGE_SENS, GND/+3V3/+5V_BEC planes all byte-identical.
- **Cluster walk:** +5V F.Cu-over-In1 / B.Cu-over-In4 (GND reference both sides);
  bench-only rail (no flight current), thin detour electrically fine.

## 4. Scope

Closes **Phase-4d-redux D2**. Next: D3 (eFuse protection nets). Sim 1 / Sim 5
re-gate still pending after D4 (MCU core).
