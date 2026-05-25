# PR — +3V3_IMU Rail Routing

> **Branch**: `hw/3v3-imu-rail` off `sch/option-b-buck` head `e43ec76`
> **Scope**: Route the +3V3_IMU rail from U13 LP5907 LDO output to all 6
> IMU power pins + 9 decap caps via F.Cu/B.Cu trace network per master
> Topology (a) decision. Single net (17 endpoints) Freerouting run.
> **Master sign-off**: 2026-05-23 (3 decisions: topology a, 0.25mm width,
> bridge X=63±5mm; pre-flight bridge census passed at 6/14).

---

## Symptom

`+3V3_IMU` rail had 17 on-board pads but ZERO routes. D-routing PR #77
(merged at e43ec76) intentionally deferred +3V3_IMU because In3.Cu is
+3V3 (not +3V3_IMU) — no dedicated plane. Topology choice (trace network
vs plane-pour vs split-zone) deserved its own focused sub-step.

Without +3V3_IMU routes, the 3 IMUs (U3/U8/U9) had power-net pads
floating electrically. Audit `check_decoupling` couldn't verify cap-to-IMU
proximity (gate requires routed connectivity).

## Fix

### Commit (this) — Freerouting + SES apply

`hardware/kicad/novapcb-stepwise/integ_3v3_imu.py` (new):
- DSN export + strip (149 nets → 1 net `+3V3_IMU`)
- Freerouting 8 passes in 70s, 0 unrouted
- SES 10,713 bytes

`hardware/kicad/novapcb-stepwise/apply_3v3_imu_ses.py` (new):
- Custom SES parser (sense-sub-step pattern)
- 48 track segments + 9 vias applied
- Zone refill after

**Routing result**:
- 48 tracks + 9 vias
- 104.0 mm total trace length
- F.Cu + B.Cu (Freerouting distributed branches between layers)
- Connects: U13.5 (source) + C78.1 (LDO bulk) + 6 IMU power pins
  (U3.14, U3.8, U8.3, U8.11, U9.5, U9.8) + 9 decap caps
  (C41-43.1, C91-93.1, C94-96.1)

## Root cause

### Why +3V3_IMU was deferred from D-routing
D-routing scope was signal nets only (SPI/INT/HEATER). Power-net
routing has different topology considerations (PDN impedance, return-
current geometry) so warranted its own analysis + master sign-off.
Per `docs/D_3V3_IMU_RAIL_ANALYSIS.md` (sha ae8d859), three topologies
were quantitatively compared and (a) F.Cu trace network was chosen.

### Why trace network over plane pour
At 30mA total IMU current (6 fanouts × ~5mA each), trace inductance
contribution is negligible. The LP5907 LDO does the noise filtering
(PSRR 60-80 dB across audio + buck switching frequencies). IMU noise
budget (verified in Option B doc) has 580× gyro / 7400× accel margin —
trace topology has plenty of headroom. Plane pour would cost
significant rework to existing F.Cu/B.Cu D-zone routes from PR #77.

## Prevention

### Up-front topology analysis pattern (master 2026-05-23)
Per the D-placement + sense + D-routing pattern, all routing sub-steps
now use an up-front constraint analysis doc with quantified rationale
before any code commits. `D_3V3_IMU_RAIL_ANALYSIS.md` is the template
for power-rail topology decisions:
1. Net inventory (source + loads + bypass caps)
2. Topology candidates with cost/benefit per option
3. Quantified rationale for recommendation
4. Decap distance check
5. Routing plan with bridge-column compatibility for slot #102
6. Constraints from prior PRs (DRC baseline, audit gates)
7. Decisions for master sign-off

### Pre-flight bridge column census (master discipline)
Master added a census step before commit: count F.Cu + B.Cu nets
crossing the future-slot column X=63±5mm Y=27..35. Threshold:
- ≤13 → silent proceed
- 14-15 → flag for sub-branch split
- >15 → escalate

**Pre-+3V3_IMU**: 5 nets (USB_DM/DP F.Cu + HEATER_PWM/IMU2_GYR_INT3/SPI3_SCK B.Cu)
**Post-+3V3_IMU**: 6 nets (added +3V3_IMU on both F.Cu + B.Cu but counts once per master's net-count rule)

6/14 — well under threshold. Silent proceed.

## Spec deviations (Rule 4)

**None** — implementation matches master's confirmed topology (a) + 0.25mm
width + bridge column. No deviations taken.

## Rule 9 verification (artifact-level)

| Claim | Verified by |
|---|---|
| +3V3_IMU fully routed | per-net cluster walk: 48 tracks, 9 vias, len=104.0mm — Freerouting `unrouted=0` final pass |
| Trunk uses bridge column X=63±5mm | Bridge column census post-route shows +3V3_IMU present on F.Cu AND B.Cu at X=58..68 Y=27..35 |
| DRC 0 net new | `gate14_drc.py` 10 (baseline) — only pre-existing DRU coverage gaps |
| STACKUP-SPEC-MATCH PASS | Audit gate INFO line green |
| MIRROR_PAIRS unchanged | No A-zone touched; 11/11 PASS |
| Decap-to-IMU proximity verified | All 9 caps within 0.05-0.5mm body-edge to IMU bodies (analysis §4); routing closes the net loop so audit `check_decoupling` will recognize them on next gate run |
| Bridge column ≤13 threshold | 6/14 nets crossing — silent proceed |
| LDO source preserved | U13.5 (58.70, 26.95) + C78.1 (62.52, 27.00) are net endpoints (verified in SES) |

## Per-trace GND-reference cluster walk

Sample 3 segments to verify In1.Cu GND continuity beneath F.Cu +3V3_IMU
+ In4.Cu GND beneath B.Cu +3V3_IMU:

- **U13.5 → trunk south on F.Cu near X=62 Y=30** — In1.Cu GND zone covers
  full board (8494 mm², 95% area). Segment over solid GND fill. ✓
- **Trunk bridge crossing X=63 Y=42** — In1.Cu GND zone with anti-pads
  for any vias in this column. +3V3_IMU trunk centerline has continuous
  GND reference beneath. ✓
- **Branch into U8 area F.Cu around X=68 Y=55** — In1.Cu GND zone
  continues; D-zone area has full GND coverage. ✓

B.Cu +3V3_IMU segments reference In4.Cu GND (also 8494 mm² full-board
coverage). Stitching vias (143 from stackup-fix PR) bond In1+In4 GND
planes for cross-layer return current.

## Gates

- **DRC**: 10 (baseline) — 0 net new
- **STACKUP-SPEC-MATCH**: PASS (no zones added/removed)
- **MIRROR_PAIRS**: 11/11 PASS (A-zone untouched)
- **DECOUPLING**: 2 fail (only pre-existing U6 task #91 — D-zone IMU
  decap caps already within 3mm; net connectivity now closed)
- **FANOUT-CORRIDOR**: WARN 4 pins (R13 deviation, documented)

## Renders

- `hardware/kicad/novapcb-stepwise/renders/3v3-imu/top.png` — F.Cu view
  (+3V3_IMU trunk + branches visible in D-zone + bridge corridor)
- `…/bot.png` — B.Cu view (some +3V3_IMU branches on bottom)

## Open items / next sub-steps

- **Stress-relief slot polygon** — sub-step #102 (deferred from D placement)
- **DRU coverage gaps** — task #97 (pre-Phase-7a cleanup)
- **U6 DECOUPLING** — task #91 (pre-existing, not D-related)
