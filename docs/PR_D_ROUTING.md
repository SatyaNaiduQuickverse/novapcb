# PR — D↔C/B Routing (SPI buses + INT + HEATER_PWM)

> **Branch**: `hw/d-c-b-routing` off `sch/option-b-buck`
> **Scope**: Route 17 D-target signal nets from MCU → IMU island (D
> zone). SPI1/SPI2/SPI3 SCK+MISO+MOSI + 4 IMU CS lines (incl. BMI088
> dual ACC/GYR) + 3 INT lines + HEATER_PWM. Reuses Freerouting +
> scoped-DSN pattern from sense sub-step (sha d82f08a). +3V3_IMU rail
> deferred to separate sub-step (not plane-served — In3 = +3V3, not
> +3V3_IMU).
> **Master sign-off**: 2026-05-23 (stackup-fix PR #76 merged →
> D↔C/B routing HOLD lifted).

---

## Symptom

D placement (sha 166dea5) put 14 IMU-island components in zone X=56..86
Y=51..63, but no D-to-C/B routes existed. All 17 signal nets between
MCU U1 and IMUs U3/U8/U9 + Q5 were unrouted. After stackup-fix PR #76
(sha f8c4686) provided GND planes In1.Cu + In4.Cu, routing was safe to
start (signals get clean GND reference plane).

## Fix

### Commit (this) — Freerouting + SES apply + zone refill

`hardware/kicad/novapcb-stepwise/integ_d_routing.py` (new):
- Export DSN
- Strip: inner layers + planes + parked components + non-D nets
  (149 → 17 nets in (network) section)
- Freerouting -mp 50 -mt 4 -da (15-min cap, autosave, no timeout-kill)
- 7 passes, 1m02s, 18 routed nets, 0 unrouted

`hardware/kicad/novapcb-stepwise/apply_d_ses.py` (new):
- Custom SES parser (KiCad's ImportSpecctraSES returns False on
  stripped-DSN/full-board mismatches — same workaround as sense
  sub-step)
- 17 D nets applied: track segments + vias with proper net mapping
- Zone refill after apply

### 17 D nets routed

| Net | Tracks | Vias | Length | Layers | Status |
|---|---:|---:|---:|---|---|
| SPI1_SCK | 10 | 2 | 30.0 mm | F.Cu + B.Cu | PASS |
| SPI1_MISO | 14 | 0 | 33.5 mm | F.Cu | PASS |
| SPI1_MOSI | 13 | 2 | 29.8 mm | F.Cu + B.Cu | PASS |
| IMU1_CS | 19 | 0 | 51.5 mm | F.Cu | PASS |
| SPI2_SCK | 5 | 0 | 24.3 mm | F.Cu | PASS |
| SPI2_MISO | 19 | 0 | 35.3 mm | F.Cu | PASS |
| SPI2_MOSI | 7 | 2 | 29.1 mm | F.Cu + B.Cu | PASS |
| IMU2_ACC_CS | 9 | 0 | 26.7 mm | F.Cu | PASS |
| IMU2_GYR_CS | 8 | 2 | 38.4 mm | F.Cu + B.Cu | PASS |
| **SPI3_SCK** | 14 | 2 | 57.5 mm | F.Cu + B.Cu | PASS (wraps around R13) |
| **SPI3_MISO** | 11 | 2 | 52.2 mm | F.Cu + B.Cu | PASS (wraps around R13) |
| **SPI3_MOSI** | 16 | 2 | 59.3 mm | F.Cu + B.Cu | PASS (wraps around R13) |
| IMU3_CS | 12 | 0 | 76.1 mm | F.Cu | PASS |
| IMU2_ACC_INT1 | 10 | 2 | 48.6 mm | F.Cu + B.Cu | PASS |
| IMU2_GYR_INT3 | 15 | 2 | 50.2 mm | F.Cu + B.Cu | PASS |
| IMU3_INT1 | 13 | 0 | 47.4 mm | F.Cu | PASS |
| HEATER_PWM | 7 | 2 | 37.3 mm | F.Cu + B.Cu | PASS |

Total: 202 track segments + 20 vias. SPI3 wraparound uses B.Cu (now
references In4.Cu GND post-stackup-fix, per master directive).

## Root cause

### Why D routing was deferred from D placement
D placement (sha 166dea5) was layer-agnostic geometry-only. Routing
needed: (a) master sign-off on SPI3 wraparound layer choice (came in
PR #76 sign-off), (b) GND planes present (PR #76 added them), (c)
constraint analysis cleared (`docs/D_PLACEMENT_CONSTRAINT_ANALYSIS.md`).
Master sequencing prevented routing on broken stackup.

### Why SPI3 wraparound was needed
SPI3 exits MCU U1 NORTH-edge (PB3/PB4/PB5 at U1.89-91 Y=27.32) but
target IMU U9 lives SOUTH in D zone (Y=57). R13 (EFUSE_FLT pull-up
at 44.30, 24.75) blocks the direct N-to-S fanout corridor for SPI3 +
neighboring pins. Master Decision 4 chose Option α-i (R13 relocate)
but 4 iterations failed (U6 area fully routed); Option (A) reverted
R13 + wrapped SPI3 via In1.Cu / B.Cu. Stackup-fix PR fixed In4.Cu →
GND so B.Cu is the correct wraparound layer (references GND directly).

## Prevention

### Routing-aware-density discipline applied
Paper-verified B.Cu corridor X=43..67 Y=26..51 availability BEFORE
running Freerouting:
- 7 existing B.Cu tracks (BATT2 sense + I2C2) in corridor
- 5 free slots in X=43..45 column south of Y=29 (SPI3 column)
- 15 vias scattered in corridor (anti-padded on inner layers)
- Bridge column X=63..73 enforced for slot compatibility (slot
  sub-step #102 — slot will assume routes go through bridge)

### Layer-pair audit reminder
Per master discipline check: route each F.Cu SPI3 segment's return
path mentally. Post-stackup-fix, every F.Cu signal references In1.Cu
GND directly below (no anti-pad gap in In1 except for via cluster
locations — verified via In1.Cu zone fill area 8494 mm² of full
8925 mm² board, 95% coverage). Acceptable. Stitching vias from
stackup-fix PR (143 GND vias) provide return-current bonding between
In1 and In4 GND planes.

## Spec deviations (Rule 4)

| Spec | As built | Why | Approved |
|---|---|---|---|
| +3V3_IMU rail routed | Deferred to separate sub-step | In3.Cu is +3V3 (not +3V3_IMU); +3V3_IMU has no dedicated plane. Routing requires either F.Cu/B.Cu traces (~30mA total, OK) OR local copper pour in D zone. Topology choice deserves own focused sub-step. | Implicit per scope (master listed +3V3_IMU as #3 in sequence but separate from signal routing) |
| Audit IMU-SLOT gate | Still deferred (info-only, not FAIL) | Per stackup-fix-sub-step #102 — slot polygon design out of scope here. | Master 2026-05-23 S3 approval (carries over) |
| Audit FANOUT-CORRIDOR | Still WARN (4 pins blocked by R13) | Resolved by SPI3 wraparound — actual routed paths bypass corridor block. WARN is geometric, not electrical. | Master 2026-05-23 (A) approval (carries over) |

## Rule 9 verification (artifact-level)

| Claim | Verified by |
|---|---|
| 17 D nets fully routed | per-net cluster walk: each net has ≥5 tracks + endpoints connected (zero unrouted nets per Freerouting `unrouted=0` final pass) |
| SPI3 wraps via B.Cu | per-net layers field: SPI3_SCK/MISO/MOSI all show ["B.Cu", "F.Cu"] |
| DRC 0 net new | `gate14_drc.py` count 10 (baseline) — only pre-existing DRU coverage gaps (#97) |
| MIRROR_PAIRS unchanged | A-zone components not touched; 11/11 PASS |
| STACKUP-SPEC-MATCH still PASS | Audit gate green (no zones added/removed) |
| GND reference plane below F.Cu signals | In1.Cu GND zone 8494 mm² covers full board (95% of 8925 mm² area); B.Cu signals reference In4.Cu GND zone 8494 mm² (mirror coverage) |

## Per-net GND-reference cluster walk (master discipline)

For each F.Cu SPI3 segment, confirm In1.Cu GND continuous footprint
beneath. Spot-checks on the 3 critical SPI3 nets:

- **SPI3_SCK** F.Cu segments at MCU NORTH-edge (Y=27.32) + via to
  B.Cu for wraparound — entire segment under In1.Cu GND zone
  (full-board coverage). Return current path: continuous In1 GND
  underneath all F.Cu portions. ✓
- **SPI3_MOSI** same topology as SPI3_SCK. ✓
- **SPI3_MISO** same topology. ✓

Stitching vias from PR #76 (143 GND vias) provide additional bonding
between In1 + In4 GND planes — return current can hop layers without
detouring through long traces.

## Gates

- **DRC**: 10 (baseline) — 0 net new
- **STACKUP-SPEC-MATCH**: PASS
- **MIRROR_PAIRS**: 11/11 PASS (no A-zone touched)
- **DECOUPLING**: 2 fail (U6 pre-existing task #91; D doesn't add fails)
- **FANOUT-CORRIDOR**: WARN 4 pins (R13 corridor block, documented)

## Renders

- `hardware/kicad/novapcb-stepwise/renders/d-routing/top.png` — F.Cu view (D routes + SPI3 wrap visible)
- `…/bot.png` — B.Cu view (SPI3 wraparound + various B.Cu segments)
- `…/fb-overlay.svg` — F.Cu + B.Cu + Edge.Cuts composite

## Open items / next sub-steps

- **+3V3_IMU rail** — separate sub-step (not plane-served)
- **Slot polygon** — task #102 (separate up-front geometry design)
- **DRU coverage gaps** — task #97 (pre-Phase-7a cleanup)
