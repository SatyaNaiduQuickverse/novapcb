# T3 partial (MOT3-6) routing — up-front survey (task #49)

> Branch `docs/t3-partial-survey` off `sch/option-b-buck`. **NO LAYOUT TOUCH.**
> Fresh survey on the CURRENT board (the prior `MOT_FANOUT_ACTUAL_OBSTACLE_SURVEY`
> predates the GPS #101 + BUZZER #102 routings, which added new corridor crossings).
> Scope: route MOT3-6 (6/8 motors); **MOT7-8 stay unrouted per Sai option D**
> (quad/hex pilot, no octo). hwdef defines all 8 (MOT7=PB8, MOT8=PB9) — the
> deferral is PCB-routing-only, no hwdef change.

## 1. Topology

| Net | MCU pin (S-edge) | J11 pad |
|---|---|---|
| MOT3 | U1.39 PE9 (45.5,42.7) | J11.3 (49.4,78.2) |
| MOT4 | U1.41 PE11 (46.5,42.7) | J11.4 (50.6,78.2) |
| MOT5 | U1.43 PE13 (47.5,42.7) | J11.5 (51.9,78.2) |
| MOT6 | U1.44 PE14 (48.0,42.7) | J11.6 (53.1,78.2) |

A 4-trace fanout from the MCU south edge (X45.5–48, Y42.7) ~35 mm south to J11
(X49.4–53.1, Y78.2). All 4 currently **unrouted** (0 tracks).

## 2. Corridor obstacle survey (Rule 18/19/20 — current board)

**F.Cu blockers** (E-W signal traces crossing the MOT3-6 path band):

| Net | Crossing Y | Note |
|---|---|---|
| **I2C1_SCL** | ~49.5 (X44.6–52.6) | **NEW** since prior survey (GPS PR #101) |
| **I2C1_SDA** | ~52.5 (X45.8–57.1) | **NEW** (GPS PR #101) |
| I2C2_SCL | 43.9 / 45.5 / 46.0 / 46.5 | R12 pull-up cluster (tied to R12) |
| I2C2_SDA | 48.3 (X43.3–52.5) | spans all 4 MOT cols |
| SPI1_SCK | 50.4 (X43.5–56.7) | spans all 4 |
| SPI1_MISO | 50.0 (X43.7–59.2) | spans all 4 |
| SPI1_MOSI | 44.4 / 45.1 / 45.8 | near MCU exit |
| IMU1_CS | 47.6 + 55.2 | diagonal |
| IMU3_CS | 51.6 + 61.6 | diagonal — **now reaches the band** (prior survey had it as a border-miss; re-verify confirms it clips X45.9–49.9 at Y51.6) |

**F.Cu footprints in path**: R12 (I2C2_SCL pull-up, ~45.5,46.5), C51 (+3V3 decap,
46.5,47.5), C17 (VCAP1 MCU decap, 48.5,45.0).

**B.Cu crossings** (fewer — relevant only if MOT3-6 route on B.Cu): IMU2_GYR_CS
(~45.8, X47.2–62.8), SPI3_MOSI (~46.7, X48.9–52.2), IMU2_ACC_INT1 (~52.8), I2C1_SDA
(short segs ~48–51).

**Net:** the F.Cu corridor is **~9 signal-net crossings + 3 footprints** —
denser than the prior survey (the +I2C1 crossings from GPS #101 are new). B.Cu
is materially lighter (~3–4 crossings).

## 3. Why the prior F.Cu "corridor redesign" stalled — and the reframe

The prior T3 attempts tried to clear the F.Cu corridor (move R12/C51 + re-route
the I2C2/SPI1 buses) — that over-scoped (17 nets at once → 148 DRC, reverted; then
iter-4 regressed to 49). With the corridor now **denser** (+I2C1), a full F.Cu
clear is even less attractive.

**Reframe — recommend B.Cu-primary for the MOT3-6 S-run:** MCU F.Cu exit → via →
**B.Cu south run** (sidesteps the ~9 F.Cu crossings) → via → J11 F.Cu pads. DShot
(≤600 kHz digital) on B.Cu (referenced to In4 GND) is fine — no SI concern, no
length-match. MOT3-6 then only contend with the ~3–4 B.Cu crossings (IMU2_GYR_CS,
SPI3_MOSI, IMU2_ACC_INT1), which are far more tractable than the F.Cu field.

## 4. Decisions for sign-off

1. **Approach**: B.Cu-primary S-run (recommend) vs the prior F.Cu corridor-clear.
   B.Cu sidesteps the dense F.Cu sensor-bus field. Sub-options once chosen:
   scoped Freerouting (4 MOT nets, bias B.Cu) or manual 4-trace B.Cu fanout.
2. **B.Cu crossing resolution**: the 3–4 B.Cu crossings (IMU2_GYR_CS Y45.8,
   SPI3_MOSI Y46.7, IMU2_ACC_INT1 Y52.8) — MOT3-6 weave between them, or
   layer-hop the shorter ones. Confirm acceptable.
3. **MCU-exit fanout**: PE9/11/13/14 exit the S-edge (Y42.7) — must clear the
   R12/C51/C17 footprints + SPI1_MOSI(Y44–46) immediately south before the via
   drop to B.Cu. May need the via-drop just south of the footprint band (~Y48).
4. **MOT7-8**: stay unrouted (Sai option D). Confirm.

## 5. Gates (planned)

- DRC ≤ baseline (+0 new, GUI-authoritative per the #30 kicad-cli note);
  unconnected −4 (MOT3-6 close).
- STACKUP / MIRROR / DECOUPLING audit PASS.
- Per-net cluster walk: MOT3-6 B.Cu over In4 GND (continuous).

---

**Awaiting master sign-off on the B.Cu-primary approach (vs F.Cu corridor-clear)
+ the via-drop point before execute.**
