# Telem (USART1) — v1 defer decision

> **Status:** master draft 2026-05-26, **awaiting Sai ratification**.
> **Trigger:** task #56 empirically proved USART1_TX/RX (PA9/PA10 → J3 connector) cannot escape the MCU NE-saturated zone in v1 without re-pin or surgical multi-wall F↔B weave. Master scope-pragmatism call: defer the J3 external telem connector to v2; USART1 stays in firmware unchanged.

---

## 1. What this defers

| Item | v1 state | v2 plan |
|---|---|---|
| USART1 peripheral in firmware (hwdef.dat: USART1 PA9/PA10) | **KEPT** — `SERIAL_ORDER` and pin assignment unchanged | (No change) |
| J3 4-pin JST-GH connector on board | **REMOVE from .kicad_pcb** for v1 (or keep as DNP footprint if removal causes BOM churn) | Re-add with cleaner placement (W or N edge clear of the NE-saturated zone) |
| MAVLink secondary telemetry over external radio (SiK / RFD900 / etc.) | **NOT AVAILABLE on v1 wire** | Available via J3 in v2 |

**What v1 still has, end-to-end:**
- MAVLink primary: USB-CDC ACM via J6 USB-C connector (the canonical ArduPilot-to-Pi link per CLAUDE.md §2.1, §3.1). This **is the production telemetry path** for the Nova drone — the drone Pi opens `/dev/serial/by-id/usb-ArduPilot_*-if00` and runs MAVROS over it. v0 Pixhawk 6X uses the same path.
- ELRS RC + telemetry: CRSF UART (separate, task #56 re-pin pending) for stick inputs + 1:2 telem downlink ratio per CLAUDE.md §3.2.

**Net flight capability impact: zero.** USART1/J3 would have been a *spare* in v1 — for an optional external radio modem if Sai wanted to add one later. The Nova drone stack does not use it.

## 2. Why defer (root cause)

Per `docs/CRSF_TELEM_SWD_ROUTING_ANALYSIS.md`:

> Telem (USART1_TX/RX → J3 @X93): route EAST. Candidate B.Cu lane Y37-44 has SDMMC1_CMD/D2/D3 + SPI fragments + a GND-stitch via grid (≈2-3mm pitch) — weave between the stitch vias, or F.Cu over the B.Cu SDMMC fragments.
>
> The CRSF pads (U1.63/64 @Y34.5-35) are boxed immediately north by the USB_DM/DP F.Cu traces (@Y31-31.5, untouchable per PR #75) plus the same horizontal-wall stack; Telem (U1.68/69) is boxed by USB + the east-band SDMMC/SPI.

USART1's MCU pads (PA9/PA10) are at pin numbers ~67/68 — east-edge LQFP-100. The 40mm east traverse to J3 @ X=93 crosses SDMMC1 + GND-stitch + SPI fragments on both layers. Empirically blocked across 4 distinct routing attempts (Freerouting scoped, Freerouting 4-net pared-down, manual, with SDMMC1_CMD nudge).

The CRSF re-pin proposal (`docs/CRSF_REPIN_PROPOSAL.md`, pending worker MCU-pad audit) is the targeted unlock for the **flight-critical** RC signal. Telem is not flight-critical for v1 per the system context above, so master's call is to defer the J3 connector rather than burn worker cycles on a 4-net surgical route that gains zero capability the Nova stack uses.

## 3. Concrete delta

**Board (.kicad_pcb):**
- Remove J3 footprint + the connector-side USART1_TX/RX stub traces (if any committed pre-PR #56).
- Re-add the freed PCB area to GND pour (or leave for v2).
- BOM: remove J3 row (was: 1× JST-GH SM04B-GHS-TB).

**Schematic (SKiDL):**
- Comment out the `J3` instantiation in the relevant SKiDL sheet (likely `crsf_usb_3g.py` or a dedicated telem sheet) — keep the SKiDL block as a `# v2: re-enable when J3 placement is clean` marker.

**Firmware (hwdef.dat):**
- **NO CHANGE.** USART1 PA9/PA10 + SERIAL_ORDER stay declared so ArduPilot still publishes the peripheral. The MCU pads simply have no external connector wire — they remain available for v2 re-route.
- Defining `SERIAL1_PROTOCOL = -1` at runtime would soft-disable it; no firmware change needed in hwdef.

**Docs:**
- `docs/INTERFACE_CONTRACT.md` — add a note: v1 has no external telem connector; primary MAVLink is USB-CDC.
- `docs/OPEN_QUESTIONS.md` — log v2 plan: re-place J3 on a clean edge + route USART1.

## 4. Why this is safe to defer (not a regression)

| Concern | Resolution |
|---|---|
| "Does the drone Pi need J3?" | No. `~/novaros/docker-compose.yml` drone-control container opens USB-CDC `/dev/serial/by-id/usb-ArduPilot_*-if00` only (CLAUDE.md §3.1). No second serial telem is configured. |
| "Does Sai's flight test need an external radio modem?" | Per CLAUDE.md §6.3 Bring-up plan: tethered hover then free flight. ELRS RC link IS the radio (CRSF, 868/915 MHz, telem ratio 1:2). MAVLink ground-side telemetry is via USB-CDC over the cabled drone Pi — there is no separate ground modem in the Nova stack. |
| "Is USART1 still callable from ArduPilot code?" | Yes — `SERIAL1_*` parameters still apply to the peripheral; it just has no external pinout in v1. Any future SiK-style radio mod requires v2 rework anyway (board cutout for the radio enclosure). |
| "Does this affect the Pixhawk 6X functional drop-in claim?" | Marginally. 6X has TELEM1 connector. We tell Sai v1 is "USB-CDC functional drop-in" (per CLAUDE.md §1) — the secondary serial telem connector is a v2 hardware feature. |

## 5. Sai ratification

This deferral changes the **physical board feature set**, which per `feedback-master-drives-decisions.md` is a TRUE Sai-gate (scope change). Master is drafting this proactively; **execution waits for Sai's go**.

**Yes path:** master dispatches worker to (a) remove J3 from `.kicad_pcb`, (b) comment SKiDL telem block, (c) update BOM, (d) cluster-walk USART1 MCU pads to confirm "no external wire" rather than dangling, (e) note in `docs/INTERFACE_CONTRACT.md` and `docs/OPEN_QUESTIONS.md`.

**No path:** master keeps J3 placed + dispatches the multi-wall F↔B weave routing (cite `docs/CRSF_TELEM_SWD_ROUTING_ANALYSIS.md` §3 — "surgical" class). Adds 1-2 PRs to the freeze stack. Acceptable, just costlier.

**Master recommendation: defer to v2.** USB-CDC is the canonical Nova-stack telem path; J3 was always a "spare" pattern inherited from the 6X form factor, not a functional requirement.
