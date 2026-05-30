# CRSF / Telem / SWD routing (#48) — NE-quadrant congestion analysis

> Branch `hw/crsf-telem-swd`. Captures the routing-feasibility analysis for the
> 7 #48 nets after a fresh scoped-Freerouting run (5/7 partial) + manual probing.
> Master-approved approach (2026-05-26): manual B.Cu/F.Cu-weave escapes + targeted
> Rule-20 nudges + pre-authorized ≤1mm SDMMC1_CMD nudge fallback (Sim 3 = 99%
> timing margin). This doc records the obstacle map so execution is efficient.

## 1. Net inventory + status

| Net | MCU pad | Dest | FR result | Notes |
|---|---|---|---|---|
| NRST | U1.14 (37.3,35.5) | J9.10 (47,5.5) | **ROUTED** | W/NW edge, uncongested |
| USART6_TX | U1.63 (52.7,35.0) | J10.2 (53.4,6.2) | stub only | CRSF; connector-side routed to TVS D13 ~Y14.4 |
| USART6_RX | U1.64 (52.7,34.5) | J10.3 (54.6,6.2) | stub only | CRSF; stub to D14 ~Y14.4 |
| USART1_TX | U1.68 (52.7,32.5) | J3.2 (93.1,36.1) | stub only | Telem; goes EAST ~40mm |
| USART1_RX | U1.69 (52.7,32.0) | J3.3 (94.4,36.1) | stub only | Telem; EAST |
| SWDIO | U1.72 (52.7,30.5) | J9.2 (47,10.5) | unrouted | SWD; W to J9 |
| SWCLK | U1.76 (51.0,27.3) | J9.4 (47,9.3) | unrouted | SWD; W to J9 |

The 6 unrouted are all **MCU east/north-edge escapes**, interleaved with
already-routed USB_DP/DM (U1.70/71) + SDMMC1_D0/D1 (U1.65/66) + VCAP2/+3V3.

## 2. The doubly-walled corridor (root cause)

Connectors J9 (X47,Y6-10) and J10 (X54,Y6) sit NORTH of the MCU; the escape
pads are at Y27-35. Every vertical escape Y27→Y9 must cross a stack of
**horizontal nets that span the full board width on BOTH layers**:

| Y | Net | Layer | X-span |
|---|---|---|---|
| 15.14 | BATT2_VOLTAGE_SENS | F.Cu | 46.55–80.87 |
| 16.0 | CAN1_RX | F.Cu | 49.40–91.50 |
| 19.0 | CAN1_TX | F.Cu | 48.40–92.20 |
| 21.2 | BATT2_CURRENT_SENS | F.Cu | 45.11–79.36 |
| 24.4 | SDMMC1_CMD | B.Cu | 48.08–63.87 |

Plus B.Cu verticals (BATT2_VOLTAGE_SENS @X46.55 Y15-37; SDMMC1_CMD descent
@X47.23 Y25-28) and the CAN via field (X48.4–49.4, Y17-22). A vertical escape
must **F↔B weave** — cross each F.Cu wall on B.Cu and vice-versa — needing a via
per wall at a clear X.

## 3. Per-net tractability (the execution plan)

- **CRSF (USART6_TX/RX → J10 @X54):** most tractable. Route up the **X54-55 east
  side**, where the *vertical* descending traffic (CAN verticals @48.4/49.4,
  SDMMC descent @47.23) is absent — only the horizontal walls remain, crossed by
  F↔B weave. Connector stubs already reach ~Y14.4.
- **Telem (USART1_TX/RX → J3 @X93):** route EAST. Candidate B.Cu lane Y37-44 has
  SDMMC1_CMD/D2/D3 + SPI fragments + a GND-stitch via grid (≈2-3mm pitch) —
  weave between the stitch vias, or F.Cu over the B.Cu SDMMC fragments. Separate
  corridor from the north knot.
- **SWD (SWDIO/SWCLK → J9 @X47):** hardest. The X47 lane is boxed by the
  SDMMC1_CMD descent (47.23) + CAN verticals (48.4/49.4) + BATT2_VOLTAGE_SENS
  (46.55) + GND via (47,12). Getting the MCU pads (X51-52.7) **west** to X47
  crosses the CAN/SDMMC/SPI3 descent on both layers. This is where the
  **pre-authorized ≤1mm SDMMC1_CMD nudge** (shift the X47.23 descent / Y24.4 west
  end east of the CAN column, or open the X47 lane) is the intended unlock —
  Sim 3 verified 99% SDMMC timing margin so a ≤1mm length delta (~7ps) is
  electrically irrelevant.

## 4. Verification gates (per master)

- Don't touch USB diff pair (PR #75 impedance-tuned) or SDMMC D0-D3/CLK.
- SDMMC1_CMD ≤1mm nudge only; cite Sim 3 margin; re-cluster-walk SDMMC1_CMD after.
- Per-net cluster walk (F.Cu over In1 GND, B.Cu over In4 GND). DRC ≤ baseline+3.
- Unconnected −7 (6 escapes + NRST, NRST already closed by FR).

## 5. Status

NRST routed (FR). **All 6 MCU escapes are blocked** — confirmed by two scoped
Freerouting runs (7-net: 6 unrouted; 4-net CRSF+Telem only: still 4 unrouted) plus
a manual SWCLK attempt (16 DRC violations). FR routes the connector-side stubs but
**cannot complete any MCU-pad escape**.

**Correction to §3's tractability estimate:** CRSF is NOT meaningfully easier than
SWD. The CRSF pads (U1.63/64 @Y34.5-35) are boxed immediately north by the
**USB_DM/DP F.Cu traces (@Y31-31.5, untouchable per PR #75)** plus the same
horizontal-wall stack; Telem (U1.68/69) is boxed by USB + the east-band SDMMC/SPI.
So the split "ship CRSF/Telem now, defer SWD" does not hold — **all 6 escapes are
the same surgical class** (drop-to-B.Cu-at-pad + multi-wall F↔B weave + the
pre-authorized ≤1mm SDMMC1_CMD nudge).

**Recommendation:** the entire #48 escape-routing (6 nets) is the focused
fresh-context surgical task (task #56), not just SWD. NRST's FR result folds into
that PR. This doc + the `integ_crsf_freeroute.py`/`apply_crsf_ses.py` scoped-FR
tooling preserve the obstacle map + per-net plan so the focused pass is efficient.
