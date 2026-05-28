# PR — D5 +3V3_IMU rail: 4 of 5 gaps closed + VIP extension (real-latent 5→2)

> Branch `hw/imu3-int1-route` (misleading name — no IMU3_INT1 work; will rename
> at squash). Closes 4 of 5 D5 +3V3_IMU rail gaps per
> `docs/3V3_IMU_RAIL_GAP_FIX_PLAN.md`. C93.1 remains as the last D5 gap (escalated:
> hands-off walled, ~3 attempts all collide SPI2/SPI3/IMU3_CS/IMU2). IMU3_INT1
> independent (Sai-gated y/z).

## 1. What landed

| order | gap | method | result |
|---|---|---|---|
| 1 | **C92.1** | std 0.5mm via on C92.1 pad + 0.84mm B.Cu stub → rail @(71.24,56.58) | **routed clean** (24af29a) |
| 2 | **U9.5** (IMU3 VDD) | **VIP** on U9.5 pad + 0.30mm B.Cu stub → rail point | **routed** (ddb0c49) |
| 3 | **U9.8** (IMU3 VDDIO) | **VIP** on U9.8 pad + 1.76mm B.Cu stub → rail | **routed** (ddb0c49) |
| 4 | **C91.1** | std via @C91.1 (slight N within pad) + 2.57mm B.Cu hop → rail | **routed** (a71b047) |
| 5 | C93.1 | (defer — see §3) | not in this PR |

DRC non-baseline electrical = **0**. Real-latent: **5 → 2** (only C93.1 + IMU3_INT1).

## 2. VIP-extension (master-approved during session)

U9.5 + U9.8 are LSM6DSV16X LGA-14 0.5 mm-pitch power escapes — same fine-pitch
wall pattern as U1.48 VCAP1: a normal 0.5 mm via fouls the adjacent GND/INT pads
(U9.6 GND + U9.4 IMU3_INT1) by hole_clearance. The clean fix is **VIP** (small
0.30/0.15 via on the pad) — the established U1.48 pattern, per
[`feedback-dense-pocket-escape-patterns`](memory). DRU rule `vip-mcu-baro-*`
extended to also match `+3V3_IMU` (per the same NetName-scope pattern used for
U4.3/U4.4). Same JLC Type-VII filled+capped process — **no incremental fab cost**.

**VIP set grows 7 → 9 pads.** Sanity sweep confirmed all 9 are documented; no
other fine-pitch pad needs VIP.
- `docs/DECISIONS.md §13.1b` updated (count + scope).
- `bom/SOURCING_NOTES.md §5 #8` updated (all 5 fab-VIP pads listed).

## 3. C93.1 — escalated to master for (m / n / p) decision

C93.1 hand-route was attempted via **3 distinct paths**, all blocked by hands-off
buses in the IMU island:

| path | blocker |
|---|---|
| Direct B.Cu C93→U8.3 rail | crosses SPI3_MOSI B horizontal (Y58.88, hands-off IMU3 bus) |
| Up-and-around X70.5 vertical | crosses SPI2_MISO F (Y58.50 X69.2–70.94) + GND via@(71,61) |
| W-side X68.8 vertical | inside U8 BMI088 body + close to C93.2 GND |
| E-side X72.5 vertical | crosses IMU3_CS F (hands-off) + still grazes GND via |

Every F.Cu lane through Y57–61 X67–72 crosses hands-off (SPI2/SPI3/IMU2/IMU3_CS);
every B.Cu lane crosses SPI3_MOSI. Master will decide:
**(m)** coordinated nudge of one hands-off seg (high risk),
**(n)** v2-defer C93.1 as the 4th-of-5-redundant +3V3_IMU decap (rail still has
4 decaps + U8.11 + U9.5/U9.8 connected; losing C93.1 reduces decap redundancy
but does NOT break IMU3 power),
**(p)** fresh-focus careful F+B thread with layer hops.

## 4. Verification

- **Per-net audit:** C92.1, U9.5, U9.8, C91.1 all 0 unconnected. Remaining
  real-latent = C93.1 (1) + IMU3_INT1 (1) — both out of this PR's scope.
- **DRC:** non-baseline electrical **= 0**. Baseline = DRU-documented exceptions
  (the now-9 VIP pads + 3 documented courtyards).
- **Board-only:** `hwdef.dat` byte-identical → `waf copter` unaffected.
- **No hands-off collateral:** SPI1/SPI3 (IMU buses), SDMMC1, USB diff, CAN diff
  untouched. VIPs respect master's hard constraints.

## 5. Scope

Closes 4/5 of **Phase-4d-redux D5**. Next: C93.1 (master decision m/n/p) + IMU3_INT1
(Sai gate y/z). Then freeze-ready.
