# PR — MOT1/MOT2 routing (task #55): close 6/8 motor count

> Branch `hw/mot12-routing` off `sch/option-b-buck` (32b33f6). Routes the two
> remaining motor nets (MOT1/MOT2) so the board reaches the **actual 6/8 motor
> count** Sai specified under option D (quad + hex flexibility). Includes a small
> cross-subsystem nudge of SPI1_MOSI to open the MCU fanout. **5-gate clean.**

## 1. Context

The DFM report (PR #109) found MOT1/MOT2 had 0 tracks — STATUS.md's "6/8" was
actually 4/8 (only MOT3-6 routed in T3-partial PR #107). This PR routes MOT1
(PB0/TIM3_CH3 → J11.1) and MOT2 (PB1/TIM3_CH4 → J11.2), bringing the routed
count to 6/8 (MOT7/MOT8 remain unrouted by design — option D, all 8 PWM defined
in hwdef). hwdef.dat is authoritative for the pins (PB0/PB1, TIM3).

## 2. The fanout blocker + the fix (SPI1_MOSI nudge)

The MCU south-edge MOT1/MOT2 pads (X43.0/43.5, 0.5mm pitch, south edge Y43.47)
were **boxed in**: SPI1_MOSI's horizontal ran at Y44.45, leaving only 0.88mm of
clear band — just under the ~0.9mm a 0.5mm escape via needs with 0.2mm clearance
both sides. Scoped Freerouting routed **0/2** (could not place a single wire).

**Fix (master-approved, option A):** nudge SPI1_MOSI's horizontal 0.4mm south.

| | Before | After |
|---|---|---|
| SPI1_MOSI horizontal Y | 44.45 | 44.85 |
| MOT fanout clear band | 0.88 mm | 1.28 mm |
| Gap to I2C2_SCL (Y45.5) | — | 0.65 mm (> 0.2 DRC) |

This is a **Rule 20 craft pattern** (move a non-critical obstacle out of the new
net's way). SPI1_MOSI is an 8 MHz medium-speed SPI signal — a 0.4mm shift is
electrically negligible (parasitic delta « SI tolerance). Three connecting
segments were adjusted (horizontal + 2 diagonal endpoints); SPI1_MOSI remains
one continuous, GND-referenced net (cluster-walk verified, not in unconnected
list). With the window open, Freerouting routed both nets.

## 3. Routes

| Net | Tracks | Vias | Length | Layers |
|---|---|---|---|---|
| MOT1 | 10 | 4 | 98.3 mm | F.Cu + B.Cu |
| MOT2 | 8 | 2 | 38.4 mm | F.Cu + B.Cu |

### MOT1 length — verified acceptable (not waved off, Rule 17)

MOT1 routed long (98 mm) because a clean local corridor is **barricaded**: the
I2C1_SCL "L" (vertical X41.15 Y40.82–55.54 + horizontal Y47.25 X41.15–44.27)
plus a +3V3 via (43.48,49.0) and I2C2_SCL vias (47.0/47.5) form a continuous
obstacle wall across X41–47.5 at Y44–52 — every candidate gap is ~0.08mm too
narrow on the 2 available signal layers (F.Cu/B.Cu; inner layers are all GND/
power planes). Freerouting's longer western detour is the DRC-clean route that
exists without moving merged cross-subsystem obstacles.

**Why the length is acceptable for v1:**
- **DShot600 timing:** ~0.6 ns one-way propagation (98 mm × 6 ps/mm) vs a
  1.67 µs DShot600 bit period — < 0.1%. Negligible. No length-matching applies
  to independent motor outputs.
- **No sensitive coupling:** a same-layer adjacency scan (≤0.6mm) found MOT1
  runs near only BUZZER (non-critical) and MOT2 (sibling motor) — **zero**
  IMU / SPI / I2C / analog / power / USB / GPS / CRSF nets within 0.6mm.
- Mostly B.Cu over the In4 GND plane (controlled, shielded return).

**v2 cleanup candidate:** a shorter MOT1 route is achievable if the I2C1_SCL /
+3V3-via wall is reworked — deferred to v2 (placement-aware), out of this PR's
scope (would be an invasive multi-net cross-subsystem move for zero v1 function
gain). Tracked, not silently accepted.

## 4. Verification (5-gate)

- **Gate 1 — DRC ≤ baseline+3:** 12 violations (= baseline; all `.kicad_dru`-
  covered via-in-pad/courtyard exceptions). **0 new** on MOT1/MOT2/SPI1_MOSI.
- **Gate 2 — STACKUP-SPEC-MATCH:** 6 Cu layers intact (no stackup change).
- **Gate 3 — MIRROR_PAIRS:** unchanged — footprint-position hash identical to
  HEAD (no component moved; routing + 1 trace nudge only).
- **Gate 4 — DECOUPLING:** unchanged (no cap moved; hash identical).
- **Gate 5 — per-net cluster walk:** MOT1 (10 trk/4 via, U1.34→J11.1), MOT2
  (8 trk/2 via, U1.35→J11.2) both connected; SPI1_MOSI continuous post-nudge.
- **Unconnected:** −2 — MOT1+MOT2 closed; only MOT7/MOT8 remain (by design).

## 5. Outcome

6/8 motors routed and DRC-clean — matches Sai's option-D intent (quad on any 4,
hex on 6). MOT7/MOT8 remain unrouted by design (v2). STATUS.md (corrected to 4/8
in 32b33f6) should update to 6/8 on merge.
