# CRSF + Telem + SWD routing — up-front survey (task #48)

> Branch `hw/crsf-telem-swd-routing` off `sch/option-b-buck` (315d9c3).
> **NO LAYOUT TOUCH until master sign-off.** 7 signal nets, all currently
> unrouted (USART1_TX has 1 stray stub to clean).

## 0. Rule-3 corrections to the dispatch (verified vs board + hwdef)

| Dispatch said | Board/hwdef actual |
|---|---|
| CRSF = UART4 | **CRSF = USART6** (J10.2/3 = USART6_TX/RX → U1.63/64). There is **no UART4** in `SERIAL_ORDER` (OTG1 USART1 USART2 USART3 UART8 USART6 OTG2). |
| SWD = SWDIO/SWCLK/NRST/**SWO** | J9 has **SWDIO/SWCLK/NRST** only — **no SWO pin** on this connector. |
| CRSF "dividers" | CRSF path has **ESD only** (D13/D14); no voltage dividers on the signal nets. |

Same class as the GPS PB9→PA2 correction — peripheral verified from the board, not the dispatch shorthand.

## 1. The 7 nets (endpoints + ESD)

| Subsystem | Net | MCU pin | ESD | Connector | Routed? |
|---|---|---|---|---|---|
| CRSF (USART6) | USART6_TX | U1.63 (52.67,35.0) | D13 (51.53,14.4) | J10.2 (53.38,6.15) | no |
| CRSF | USART6_RX | U1.64 (52.67,34.5) | D14 (53.53,14.4) | J10.3 (54.62,6.15) | no |
| Telem (USART1) | USART1_TX | U1.68 (52.67,32.5) | D11 (92.53,43.4) | J3.2 (93.12,36.15) | 1 stub |
| Telem | USART1_RX | U1.69 (52.67,32.0) | D12 (94.53,43.4) | J3.3 (94.38,36.15) | no |
| SWD | SWDIO | U1.72 (52.67,30.5) | — | J9.2 (46.95,10.54) | no |
| SWD | SWCLK | U1.76 (51.0,27.33) | — | J9.4 (46.95,9.27) | no |
| SWD | NRST | U1.14 (37.33,35.5) + C26 (34.56,42.1) | — | J9.10 (46.95,5.46) | no |

Connectors: J10 CRSF @ N-edge (54,8); J3 Telem @ E-edge (95,38); J9 SWD @ N-edge (45,8).

## 2. Corridor density + per-subsystem challenge (Rule 18/19/20)

The MCU **E-edge** pins (X52.67) interleave the new targets among **already-routed**
neighbors: pin65/66 = SDMMC1_D0/D1 (routed E to J2), pin70/71 = USB_DM/DP (routed).
So CRSF(63/64), Telem(68/69), SWDIO(72) must fan out E among live SDMMC1/USB lanes.

N/E corridor existing routing (X37–98, Y3–38) is **dense**: +5V_BEC_B (33 F.Cu segs),
+3V3_IMU_PRE (26), CAN bus CANL/CANH/CAN1_RX/TX (~50), +3V3 (15), SDMMC1 (D0–3/CMD/CLK),
BATT sense, USB. Per-subsystem:

- **CRSF** (MCU E-edge Y34.5–35 → N to J10 @Y6, via ESD D13/D14 @Y14.4): short-ish
  N run in the N-middle band. Moderate.
- **Telem** (MCU E-edge Y32–32.5 → **far E to J3 @95**, via ESD D11/D12 @Y43.4):
  ~43 mm E run across the CAN-bus NE + USB J1 region. **Hardest** — crosses the
  densest area. Likely needs B.Cu for the long traverse.
- **SWD** (slow debug): SWDIO/SWCLK MCU E/N → J9 N; NRST from MCU W-edge + reset
  cap C26 → J9. N-middle band, lower-priority (slow, no SI constraint).

## 3. Decisions for sign-off

1. **Approach**: scoped Freerouting (7 nets, F.Cu + B.Cu) — the proven CAN/microSD/
   GPS/HSE technique (DSN net-scope + inner-layer strip + via-padstack strip).
   Recommend. Manual per-net fallback for any net it can't converge (esp. Telem
   long-E-run — may hand-route on B.Cu).
2. **Length-match**: NOT required — USART6 (CRSF, 420 kbaud), USART1 (telem,
   ≤921 kbaud), SWD (≤~10 MHz debug, slow). No skew budget.
3. **ESD inline**: route MCU → ESD → connector for CRSF (D13/D14) + Telem
   (D11/D12); SWD has no ESD. Freerouting handles the multi-point path.
4. **USART1_TX stub**: clean the 1 stray segment before re-routing.
5. **GND reference**: F.Cu→In1.Cu, B.Cu→In4.Cu; per-net cluster walk.

## 4. Gates (planned)

- DRC ≤ baseline (+0 new); unconnected −N as the 7 nets close.
- STACKUP / MIRROR / DECOUPLING audit PASS (unchanged).
- Per-net cluster walk (GND reference) for all 7 nets.

---

**Awaiting master sign-off on scoped-Freerouting-first (7 nets) + the Rule-3
corrections (USART6 / no-SWO / ESD-not-dividers) before execute.**
