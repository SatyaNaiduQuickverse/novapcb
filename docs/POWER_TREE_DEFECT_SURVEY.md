# Power-tree defect survey — per-net unconnected audit (Rule 23 catch)

> **The catch that prevented a dead-on-arrival fab.** A per-net breakdown of the
> 213-unconnected total (which everyone read as "mostly intended noise") reveals
> the board's **power tree is largely unrouted** — the board would not power up.
> Read-only survey at `origin/sch/option-b-buck` head 9f9df97. No `.kicad_pcb`
> change. Entry point for the power-tree routing effort (Phase-4d-redux).
>
> Reproduce: `python3 scripts/audit_unconnected_per_net.py`.

## 1. Headline

| | count |
|---|---|
| total DRC unconnected | 213 |
| plane-pour noise (GND/+3V3/+5V_BEC zones — pads connect via pour, NOT defects) | 139 |
| intended-deferred (MOT7/8, Telem, SWD per #56 triage) | 10 |
| **REAL LATENT unconnected** | **64 across 22 nets (18 power/critical)** |

The "flight-routable / all subsystems routed" status was wrong by a wide margin:
**signal + connector routing is largely done, but the POWER TREE (5V-in → eFuse →
buck → +3V3/+3V3_IMU → MCU core) is largely unrouted.** Verified definitively
(0 copper within 0.3 mm of pads; method sound — I2C2_SDA shows 9 trk, board has
854 trk; plane-pour correctly excluded).

## 2. Defects grouped by power domain (route order = criticality)

### D1 — Buck regulator U2 (TPS62177) — UNROUTED, blocks the entire +3V3 supply
| Net | trk/via | pads | connection needed |
|---|---|---|---|
| U2_FB | 0/0 | R47.2, R48.1, U2.5 | feedback divider → buck FB (sets Vout; buck won't regulate without it) |
| U2_SW | 0/0 | L1.1, U2.9 | buck switch node → inductor L1 (no output path without it) |

Likely root: **Option-B buck swap (PR #95/#96)** placed U2/R47/R48/L1 but the
buck-specific nets were never routed (the earlier #85 B-power routing predates the
LDO→buck change). **Without D1 there is no +3V3.**

### D2 — 5V input distribution — mostly UNROUTED
| Net | trk/via | unconn | pads (27) |
|---|---|---|---|
| +5V | 1/2 | 24 | C31/C32/C9/C83/C85, J1.A4/A9/B4/B9 (VBUS), J3.1/J5.1/J10.1/J20.1, U2.2/3/8 (buck in), U5.5, U6.3-8 (eFuse in), R5.2/R13.2/R61.1 |

The raw 5V from USB-C VBUS + connectors → eFuse U6 input → buck U2 input. Almost
none of it is routed. (Note: the protected **+5V_BEC** plane IS done — In2.Cu, 0
unconnected — but the raw +5V feeding INTO the eFuse is not.)

### D3 — eFuse protection (U6 TPS25940A) — UNROUTED
| Net | trk/via | pads | note |
|---|---|---|---|
| +5V_BEC_PROT | 0/0 | R9.1, D1.1, U6.9-13, C8.1, Q2.3, R7.1 | eFuse protected-output pre-Q2 path |
| EFUSE_FLT | 0/0 | U6.20, R13.1 | fault flag |
| EFUSE_PGOOD | 0/0 | U6.2, R5.1 | power-good |
| EFUSE_DVDT | 3/1 | U6.18, C7.1 | partial — 1 gap |

### D4 — MCU core power — UNROUTED (MCU will not run)
| Net | trk/via | pads | note |
|---|---|---|---|
| VCAP1 | 0/0 | U1.48, C17.1 | internal-LDO decap — MCU won't clock without it |
| VCAP2 | 0/0 | U1.73, C18.1 | internal-LDO decap |
| +3V3A (VDDA) | 0/0 | U1.21, FB1.2, C19.1, C20.1 | analog supply via FB1 ferrite from +3V3 |
| VREF_P | 0/0 | U1.20, R1.2, C21.1, C22.1 | ADC reference |
| VBAT | 0/0 | U1.6, C23.1, R2.2 | RTC/backup |
| BOOT0 | 0/0 | U1.94, R3.1 | boot mode |

Likely root: the MCU's **local power/decoupling stubs were never routed** (caps
placed adjacent to pins by C-placement, but the pin↔cap connections never drawn);
hidden in the unconnected total because no per-net audit was run.

### D5 — +3V3_IMU rail — 5 partial gaps (already has its own plan doc)
`docs/3V3_IMU_RAIL_GAP_FIX_PLAN.md` — U9.5/8 (IMU3 power) + C91/92/93 (IMU2 decaps).
trk/via 48/9 (mostly routed, 5 near-miss gaps). Dense-pocket; careful per-trace.

### D6 — USB-C CC + misc — UNROUTED / partial
| Net | trk/via | pads | note |
|---|---|---|---|
| USBC_CC1 | 0/0 | J1.A5, R31.1 | 5.1 kΩ CC pulldown — **required for USB host detection/enumeration** |
| USBC_CC2 | 0/0 | J1.B5, R32.1 | 5.1 kΩ CC pulldown |
| IMU3_INT1 | 0/0 | U9.4, U1.36 | IMU3 interrupt |
| HEATER_DRAIN | 0/0 | R61.2, Q5.3 | IMU heater FET drain |
| BATT_CURRENT_SENS | 8/2 | C62.1, R42.2, U1.16 | partial — 1 gap |
| BATT_VOLTAGE_SENS | 19/2 | R41.2, C61.1, U1.15 | partial — 1 gap |
| I2C2_SCL | 8/2 | R12.2, U1.46, U4.4 | partial — 1 gap |
| I2C2_SDA | 9/2 | R11.2, U1.47, U4.3 | partial — 1 gap |

## 3. Impact on prior validation (must re-gate after routing)

- **Sim 1 thermal (PR #94)** assumed the MCU dissipates ~235 mW — i.e. that it
  runs. With VCAP/VDDA unrouted the MCU won't clock; thermal result is moot until
  power lands. **Re-run after D4.**
- **Sim 5 PDN (PR #118)** modeled +3V3 reaching the MCU via the In3 plane; the
  local pad stubs are part of that path. **Re-confirm after D4.**
- "flight-routable" / "all subsystem routing complete" — retracted.

## 4. Methodology (Rule 23, for the freeze gate)

A net is a real defect only if it is **not a plane-pour net** (filled zone → pads
connect via the pour; the ratsnest line is an artifact) **and not an
intended-deferred net**. `scripts/audit_unconnected_per_net.py` encodes this
(plane-zone detection + intended-defer whitelist + power/critical flagging) and
should gate the freeze: **per-net unconnected = 0 on every power/critical net**.

## 5. Next

Power-tree routing effort (fresh context, by domain D1→D6, criticality order),
each a focused PR gated on `audit_unconnected_per_net.py` (the net's unconnected →
0) + `waf` build-verify. Board is **clean** (no partial committed) for the surgery.
