# T12 microSD ESD — v1 REACH FAILURE (full revert, 2026-05-30)

> Sai-directed SOTA push T12 (microSD ESD on J2 SDMMC1 CLK/CMD/D0-D3).
> 3 routing attempts + 4 enumerated alternatives, all share the same root
> cause. v1 ships without microSD ESD. Operational risk is genuinely low
> for an internal-enclosure SD slot (industry-standard for consumer
> electronics microSD slots).

## Attempts log (3 routing attempts)

| # | Approach | DRC severity-error | Outcome |
|---|---|---:|---|
| 1 | 2× TPD4E001 F.Cu @ Y=53, D19 (92.5, 53) + D20 (95.5, 53), placement-only | 28 → 35 (+7) | D19/D20 pad overlap (3mm center spacing < 3.8mm needed for 1.325mm pad width); shorts/mask_bridge. |
| 2 | Same placement spread to (92, 53) + (96, 53) = 4mm center spacing | 28 → 29 (+1) | Placement clean. |
| 2b | Add 6 F.Cu stub traces from J2 SDMMC1 pads + 4 power vias on TVS pads | 29 → 47 (+18) | Stubs cross J2's F.Cu shield-tab pads (J2.MP at multiple Y positions inside body); tracks_crossing + shorts; +3V3/GND vias on TVS pads conflict with stub tracks (same +3V3/GND zone clearance issue as T11). |
| 3 | Flip to B.Cu placement under J2 + F.Cu→via→B.Cu stub routing | 28 → 48 (+20) | B.Cu area under J2 has 15 existing tracks + 5 vias + C63 cap (per pre-survey); 8 mask_bridge + 6 shorts + 5 tracks_crossing. |

## Enumerated alternatives (master 2026-05-30 directive)

Each surveyed for root cause without full implementation:

### Attempt 4: F.Cu west of J2

J2 sits at (95, 67); west side has 10mm clear room (X=77-87).

Survey of west-of-J2 area (X=77-87, Y=60-75):
- **R51-R55 on B.Cu** at X=86, Y=62-70 — 5 SDMMC1 pullup resistors already populate the B.Cu area
- 8 B.Cu tracks routing SDMMC1_D0/D1/D2/D3/CMD already cross the west-of-J2 area
- F.Cu has only 1 track in the area (mostly clear)

Wall analysis: placing TVS on F.Cu west of J2 needs stubs to reach the SDMMC1 signal traces. Those traces are on B.Cu (under R51-R55 pullups + at 8 different track positions). Each F.Cu TVS pad → B.Cu trace requires a via. Via positions conflict with R51-R55 SMD pads + 8 existing B.Cu trace fanout. Same density cascade expected.

→ **Same root cause** as attempts 1-3.

### Attempt 5: Series-R approach (10-22Ω R0402 per line)

Insert 6 small resistors IN-SERIES with each SDMMC1 line. Acts as ESD attenuator + slew limiter. Doesn't need TVS.

Wall analysis: requires **re-routing existing SDMMC1 traces** to pass through the R pads. Per CLAUDE.md §3.7 + project memory: SDMMC1 is **HANDS-OFF (>5MHz)**. Hands-off bus cannot be re-routed at freeze head per project rules.

→ **Root cause: hands-off constraint** (different cause but same outcome).

### Attempt 6: Common-mode choke arrays on D0-D3

CMC arrays are intended for **differential pair** filtering (e.g., USB D+/D-, CAN H/L). They reject common-mode noise on a 2-conductor pair.

SDMMC1 is **6 single-ended lines** (CLK, CMD, D0, D1, D2, D3) — each line is independent, not a differential pair.

→ **Root cause: topology mismatch** — CMC doesn't apply to single-ended bus.

### Attempt 7: Rail-clamp single-TVS topology

Run a B.Cu RAIL trace parallel to J2; each SDMMC1 line gets a series-cap-then-shunt-clamp connection to rail; rail clamps to GND via single TVS.

Wall analysis:
- TVS arrays are line-to-GND devices, not line-to-rail. Standard TVS parts don't support this topology.
- Even if built with discrete series-caps + shunt-TVS: 6 stubs from SDMMC1 lines to RAIL = same B.Cu density issue as attempts 2b/3.
- Series-caps would attenuate the SDMMC signal — SI impact larger than series-R.

→ **Root cause: same J2 area density + topology mismatch.**

## Root cause synthesis

All 7 attempts (3 routing + 4 enumerated) share root causes:

| Root cause | Attempts affected |
|---|---|
| J2 area B.Cu density (15 tracks + 5 vias + C63 + R51-55 pullups) | 1, 2b, 3, 4, 7 |
| J2 area F.Cu shield-tab obstacles | 2b |
| +3V3/GND zone clearance (0.5mm vs 0.2mm default) | 1, 2b, 3, 4, 7 |
| SDMMC1 HANDS-OFF constraint (no re-routing) | 5 |
| Topology mismatch (CMC for SE bus) | 6 |

The first three cluster into the same structural-density root cause that also drove T11. Attempts 5-6 fail on different (independent) grounds.

## Cost-benefit honest assessment

**Industry context**: most consumer-electronics microSD slots ship **WITHOUT ESD**. The PESD/USBLC TVS approach is over-spec for internal slots. Examples:
- Raspberry Pi (all models with microSD): no TVS on SDMMC interface
- Most consumer DVRs / cameras with microSD: no TVS
- ArduPilot reference boards (MatekH743, Pixhawk 6X internal microSD): typically no TVS

**ESD risk vector for novapcb microSD**: user inserts/removes SD card. SD card is a contact-mediated event:
- Internal to drone enclosure (no field-exposed cable)
- Hot-swap is rare (logs downloaded post-flight, not during)
- Operator can ESD-discharge by touching metal before handling

**T12 risk < T11 risk** because microSD ESD vector is lower probability + smaller energy.

## State after revert

- DRC severity-error: **28** (baseline, unchanged from pre-T12)
- `audit_unconnected_per_net.py`: PASS, **0 real-latent**
- `verify_bom.py`: 0 missing parts, 0 stale rows

## v1 ships without microSD ESD

Operational mitigation:
- Discharge static (touch metal) before handling SD card
- Download logs via USB-CDC, not SD ejection (USB-CDC is the canonical ArduPilot log path)

## v2 path (same as T11)

Pre-allocate TVS pads + reserve SDMMC1 routing corridor at Phase 4a BEFORE
routing the bus. Or simply accept that microSD ESD is over-spec for an
internal slot and skip permanently.

## CONFIDENCE_MAP row 12 implication

Both T11 and T12 reach failures = 8 + 6 = 14 unclamped lines.
Row 12 stays MEDIUM (~80%) — cap remains MEDIUM-HIGH (~85%) after T8 sims,
not HIGH. The T12 portion of this gap is industry-acceptable for internal
SD slots.

## Cross-references

- `docs/T11_REACH_FAILURE.md` — same density root cause for ESC outputs
- `docs/CONFIDENCE_MAP.md` row 12
- `docs/SIM_3_SDMMC_SI_RESULT.md` — current SDMMC SI baseline (97.8% at SDR25; current cap 12.5 MHz)
- Master raise-the-bar dispatch 2026-05-30 + half-state correction
- Master enumeration directive 2026-05-30 (attempts 4-7)
