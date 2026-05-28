# +3V3_IMU decap deferrals (v2) — C93.1 (2026-05-28)

> Tracked deferral, not a defect. C93.1 (one of three BMI088/U8 decap caps on
> the +3V3_IMU rail) left unrouted in v1 — added to `INTENDED_DEFERRED_PADS`
> whitelist in `scripts/audit_unconnected_per_net.py` so the gate-clean audit
> ignores it. Master-approved 2026-05-28 (option n).

## Why deferring is safe

The +3V3_IMU rail powers three IMUs (U3 ICM-42688 IMU1, U8 BMI088 IMU2,
U9 LSM6DSV16X IMU3) + the baro DPS310 (U4). All three IMUs and the baro
**retain power and decoupling** without C93.1.

**U8 BMI088 decoupling (the IC C93 was for):**

| cap | location | status | role |
|---|---|---|---|
| C91 | (67.27, 54.07) | **routed** (this PR, a71b047) | BMI088 supply decap #1 |
| C92 | (70.52, 57.00) | **routed** (this PR, 24af29a) | BMI088 supply decap #2 |
| C93 | (67.77, 59.93) | **DEFERRED v2** | BMI088 supply decap #3 |

Bosch BMI088 datasheet typical application: 2 decaps (100nF on VDD + 100nF
on VDDIO). We have C91 + C92 + the U8.11 +3V3_IMU pad directly on the rail.
Losing C93 keeps U8 within Bosch's recommended decoupling envelope.

## Why the gap is hard to close

3 hand-route paths attempted (same session); every one collided hands-off
buses in the dense IMU island:

| path | blocker |
|---|---|
| Direct B.Cu C93→U8.3 rail | SPI3_MOSI B.Cu @Y58.88 (IMU3 SPI, hands-off) |
| Up-and-around F.Cu X70.5 | SPI2_MISO F (Y58.50 X69.2–70.94, OSD/SPI2 hands-off) + GND via@(71,61) |
| Up-and-around F.Cu X68.8 | inside U8 BMI088 body (LGA-14 pads X69.20 col) |
| Up-and-around F.Cu X72.5 | IMU3_CS F (IMU3 SPI bus, hands-off) + SPI2_MISO + GND via |

Closing C93.1 in v1 would require a coordinated re-route of a hands-off bus
segment (SPI2_MISO or IMU3_CS) — the same risk profile master dismissed for
IMU3_INT1's option (y). Per `feedback-root-cause-not-patch` + the Rule-17
fatigue/quality threshold, v2-defer is the disciplined call.

## PDN impact assessment

`sim_pdn.py` (Sim 5) initial run with all 12×100nF connected → mid-band peak
**79.4 mΩ**. **Re-ran with 11×100nF** (C93 absent, via in-memory CAPS patch):
mid-band peak **82.9 mΩ** ≤ 100 mΩ gate → **PASS**. Delta = +3.5 mΩ (+4.4%),
**margin retained = 17.1 mΩ**. C93 defer's PDN impact is bounded + comfortably
within the 100 mΩ gate. No residual flag needed.

## v2 action

When v2 board respin happens (currently planned: post-v1-flight feedback):

1. **Re-place a hands-off-adjacent passive** (a U8 SPI2/IMU2 trace passive)
   to open a C93 escape lane — same pattern as the D4 cluster spread, OR
2. **Re-place C93** to a less-walled position on the +3V3_IMU rail (e.g.,
   shift NE near the open Y61+ band), OR
3. Accept the defer (BMI088 spec keeps holding with 2 decaps; only flag if
   v1 flight EMC measurements show a +3V3_IMU rail noise spike traceable to
   missing C93 decoupling).

Then remove C93.1 from the `INTENDED_DEFERRED_PADS` whitelist + re-run the
audit + verify gate-clean.

## v1 BOM note

C93 remains placed (BOM unchanged) — only its rail connection is unrouted.
Component populated but acts as an isolated pad. This is consistent with
the MOT7/8 + Telem + SWD pattern (component populated, net unrouted).
