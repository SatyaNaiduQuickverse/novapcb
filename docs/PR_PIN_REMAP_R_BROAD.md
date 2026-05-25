# PR — Pin remap R-broad (master+Sai 2026-05-24) — SKiDL + hwdef + board nets

> **Branch**: `sch/pin-remap-r-broad` off `sch/option-b-buck` head `ea6d62f`
> **Scope**: Pin reassignment ONLY (SKiDL + hwdef.dat + board pad-net
> updates) + Rule 18 + Rule 19 codification. **No MOT* routing in this
> PR** — deferred to follow-up sub-step per master 2026-05-24 sign-off.
> **Authorization**: Sai ratification required — schematic + firmware
> change per follow-master memory.
> **Carries**: `docs/MCU_PIN_MAP_AUDIT.md` (was PR #82 DRAFT — to be
> closed as audit doc carries forward into this PR).

---

## 1. Symptom

H↔C routing failed **TWICE** on the original MCU pin map:
- 2026-05-24 morning escalation: MOT3-6 west-edge PA0-PA3 + MOT7-8 east-edge
  PD12/PD13 physically blocked by component obstacles (Rule 18). 3
  manual routing iterations + Freerouting OOM + Freerouting NPE.
- 2026-05-24 afternoon: full MCU pin audit (#82 DRAFT) proposed coordinated
  remap — Sai ratified broadly, master signed sub-decisions.
- 2026-05-24 evening: with new pin map applied (this PR), 3 manual
  routing iterations STILL failed. **Different obstacle this time** —
  existing I2C2 SCL/SDA + SPI1 MISO/MOSI/SCK routes at Y=44..48
  constrict the south corridor that 6 new MOT3-6 + IMU3_INT1 needed
  to traverse. Reverted clean.

Pattern: pin remap is necessary but not sufficient. The "fanout-reach
audit" caught component-pad obstacles (Rule 18) but missed
existing-routed-net obstacles (now Rule 19).

## 2. Fix

**This PR lands pin remap CLEAN — routing deferred to next sub-step.**

### 2a. SKiDL changes (esc_3f.py + imu_3c.py)

```diff
- (3, "PA0",  True),    # was MOT3 TIM2_CH1 (W edge — cap-field blocked)
- (4, "PA1",  False),
- (5, "PA2",  True),
- (6, "PA3",  False),
- (7, "PD12", True),    # was MOT7 TIM4_CH1 (E edge — U7 BARO blocked)
- (8, "PD13", False),
+ (3, "PE9",  True),    # MOT3 TIM1_CH1 (S edge, advanced timer, BDSHOT)
+ (4, "PE11", False),   # MOT4 TIM1_CH2 (S edge — cascade IMU3_INT1)
+ (5, "PE13", True),    # MOT5 TIM1_CH3 (S edge)
+ (6, "PE14", False),   # MOT6 TIM1_CH4 (S edge)
+ (7, "PB8",  True),    # MOT7 TIM4_CH3 (N edge)
+ (8, "PB9",  False),   # MOT8 TIM4_CH4 (N edge)
```

```diff
- IMU3_INT1 += mcu["PE11"]     # was pad 41 S
+ IMU3_INT1 += mcu["PB2"]      # pad 36 S, GPIO INT (cascade PE11→MOT4)
```

### 2b. hwdef.dat sync (firmware/hwdef-novapcb/hwdef.dat)

- **MOT block (lines 168-181)**: pins updated to PE9/PE11/PE13/PE14/PB8/PB9
- **UART4 removed** (was on PB8/PB9, now MOT7/8; was "spare" with no SKiDL refs)
- **UART7 removed** (was on PE7-PE10; PE9/PE11 now MOT3/MOT4; was "spare" no SKiDL refs)
- **SERIAL_ORDER** updated: drop UART7 + UART4
- **10 SKiDL↔hwdef discrepancies fixed** per audit §0:
  - `PA15 HEATER_PWM OUTPUT GPIO(33) LOW` (was missing — power_3b.py:643)
  - `PB12 IMU2_ACC_CS CS` (imu_3c.py:274)
  - `PD4  IMU2_GYR_CS CS` (imu_3c.py:275)
  - `PE5  IMU2_ACC_INT1 INPUT GPIO(40)` (imu_3c.py:286)
  - `PE6  IMU2_GYR_INT3 INPUT GPIO(41)` (imu_3c.py:287)
  - `PE2  IMU3_CS CS` (imu_3c.py:280)
  - `PB2  IMU3_INT1 INPUT GPIO(42)` (NEW pin per remap)
  - `PC2_C BATT2_VOLTAGE_SENS ADC1 SCALE(1)` (power_sd_swd_3h.py:214)
  - `PC3_C BATT2_CURRENT_SENS ADC1 SCALE(1)` (power_sd_swd_3h.py:215)

### 2c. Board pad-net reassignment

`route_pin_remap.py` Python wrapper applies the netlist diff to the
board. 13 U1 pad-net changes:

| Pad | Old net | New net |
|---:|---|---|
| 22 | MOT3 | (empty) |
| 23 | MOT4 | (empty) |
| 24 | MOT5 | (empty) |
| 25 | MOT6 | (empty) |
| 36 | (empty) | IMU3_INT1 |
| 39 | (empty) | MOT3 |
| 41 | IMU3_INT1 | MOT4 |
| 43 | (empty) | MOT5 |
| 44 | (empty) | MOT6 |
| 59 | MOT7 | (empty) |
| 60 | MOT8 | (empty) |
| 95 | (empty) | MOT7 |
| 96 | (empty) | MOT8 |

**Old IMU3_INT1 F.Cu trace (13 segments terminating at pad 41=now-MOT4) removed** to prevent MOT4↔IMU3_INT1 short.

### 2d. Audit doc carried forward

`docs/MCU_PIN_MAP_AUDIT.md` (full 100-pad map per edge × PXn × subsystem
+ reach analysis + remap proposal) added to this PR. PR #82 DRAFT
to be closed since audit carries into this execution PR.

## 3. Root cause analysis (the lesson)

### Original H↔C failure (Rule 18 source)

Original analysis surveyed fanout corridor for tracks (found clean),
missed 8 caps + crystal + R2 at MCU west edge that physically blocked
MOT3-6 F.Cu fanout. **Component pads = physical obstacles same as
tracks.**

### Pin-remap routing failure (Rule 19 source — codified in this PR)

After audit + remap satisfied Rule 18 (no component-pad obstacles in
new corridor), routing STILL failed because:
- MOT3-6 from new S-edge pads (X=45.5..48) must sweep south
- 7 nets total need a narrow lane width
- I2C2 SCL/SDA at Y=44..48 (E-going to baro) + SPI1 MISO/MOSI/SCK at
  Y=44..52 (S-going to IMU) **already occupy the south corridor**
- Cross-section at Y=46 has only ~2mm clear lane, must fit 6-7 traces at 0.45mm each

Existing routed nets are physical obstacles to NEW routing in the
same way component pads are. Pin geometry alone isn't sufficient.

### Why this slipped past the audit

The audit's §2 "Per-subsystem fanout reach analysis" went through
the motions for each subsystem but ONLY validated:
- (a) MCU pin → connector geometric distance
- (b) Component-pad obstacles in corridor (Rule 18 catch)

It did NOT enumerate **existing routed nets in the corridor**. The
H↔C audit was specifically about the H subsystem — and H is the LAST
subsystem to route, so naturally most other nets are already routed
and crowd the corridor.

## 4. Prevention — Rule 19 (new this PR)

Codified in `docs/MASTER_PROCESS_RULES.md` (Rule 19):

> **Rule 19 — Fanout-reach audits also enumerate EXISTING ROUTED NETS.**
> A net that can geometrically reach its destination but must cross
> dense existing routing has the same problem as one blocked by
> component pads (Rule 18). Corridor must have ENOUGH SPACE for new
> nets to thread between existing ones.

Checklist additions to Rule 18:
- 5. Enumerate all routed nets currently in corridor (by net name + path)
- 6. Compute total trace lane count in narrowest cross-section vs
  available width × (track + clearance)
- 7. Flag any cross-section that cannot accommodate the planned new
  nets — escalate before commit

When constraint isn't met, options (in order):
- (a) Pick a different fanout corridor
- (b) Re-route existing constricting nets to vacate (touches their PRs)
- (c) Accept layer-split with documented DRU exceptions

**Rule 18 is also new this PR** (was discussed in master directives
earlier 2026-05-24 but never landed in the file). Both Rules added
together in this PR.

## 5. Spec deviations (Rule 4)

### Unconnected nets deferred to next sub-step:

| Net | Source pad (PXn) | Destination | Status |
|---|---|---|---|
| MOT1 | U1.34 (PB0) | J11.1 | UNROUTED — defer |
| MOT2 | U1.35 (PB1) | J11.2 | UNROUTED — defer |
| MOT3 | U1.39 (PE9) | J11.3 | UNROUTED — defer |
| MOT4 | U1.41 (PE11) | J11.4 | UNROUTED — defer |
| MOT5 | U1.43 (PE13) | J11.5 | UNROUTED — defer |
| MOT6 | U1.44 (PE14) | J11.6 | UNROUTED — defer |
| MOT7 | U1.95 (PB8) | J11.7 | UNROUTED — defer |
| MOT8 | U1.96 (PB9) | J11.8 | UNROUTED — defer |
| IMU3_INT1 | U1.36 (PB2) | U9 IMU3 INT pad | UNROUTED — defer |
| J11.10 GND stitching via | n/a | In1/In4 GND planes | UNROUTED — defer |

10 unconnected items deferred. Tracked in DRC report (unconnected 264
vs pre-pin-remap baseline 263 — +1 for IMU3_INT1 new pad).

### No board geometry deviations
- DRC: **21 errors** (baseline preserved post-old-IMU3_INT1-trace-removal)
- STACKUP-SPEC-MATCH: PASS unchanged
- MIRROR_PAIRS: 11/11 unchanged
- DECOUPLING fail count: 1 (U6, pre-existing #91)
- 7 zones filled, total 26832 mm² (unchanged)

## 6. Next sub-step (forward-looking — separate PR)

**Goal**: route the 10 deferred unconnected items.

**Options (Sai/master to pick at routing PR sign-off time)**:
- **(α) Corridor clear**: re-route I2C2 SCL/SDA + nearby SPI1 traces
  to vacate Y=44..48 band, then route MOT3-6 in clear space.
  Touches D-zone routing (PR #77/#78) — regression risk; must be
  managed via per-net cluster walks for the re-routed I2C2/SPI1 nets.
- **(β) Freerouting with 90-min timeout + accept partial result**:
  new pin geometry may converge better than original. OOM risk
  still present (Pi 5 16GB vs Freerouting 48GB pass-1 alloc).
- **(γ) Layer-split with documented DRU exceptions**: MOT3-6 via at
  pad → B.Cu south past existing F.Cu obstacles → via to F.Cu at
  J11. Adds ~12 vias + 2-3 DRU exceptions but doesn't touch
  existing routing.

Worker recommend: **(α) corridor clear** is cleanest long-term but
highest regression risk. **(γ) layer-split** is most surgical. Either
is feasible. Decision at routing PR sign-off.

## 7. Rule 9 verification (artifact-level)

| Claim | Verified by |
|---|---|
| SKiDL motor_map updated to 6 new pins | `grep '(3, "PE9"' hardware/kicad/novapcb/sheets/esc_3f.py` returns 1 match |
| IMU3_INT1 → PB2 in SKiDL | `grep 'IMU3_INT1     += mcu\["PB2"\]' imu_3c.py` returns 1 match |
| Netlist regen | novapcb.net mtime current; ERC 0 errors |
| All 8 MOT* nets bind to new U1 pads in netlist | `for n in 1..8: grep -A20 'name "MOT$n"' novapcb.net \| grep U1` → all 8 show new pad numbers (34/35/39/41/43/44/95/96) |
| IMU3_INT1 binds to U1 pad 36 | `grep -A6 'name "IMU3_INT1"' novapcb.net \| grep -B1 'pin "36"'` returns match |
| hwdef.dat MOT pins reassigned | `grep -E '^(PE9\|PE11\|PE13\|PE14\|PB8\|PB9)\s+TIM' hwdef.dat` returns 6 matches |
| UART4 + UART7 removed from hwdef.dat | `grep -cE '^(PB8\|PB9) UART4\|^(PE[7-9]\|PE10) UART7' hwdef.dat` returns 0 |
| Discrepancy nets added | `grep -cE '^(PA15 HEATER_PWM\|PB12 IMU2_ACC_CS\|PD4 IMU2_GYR_CS\|PE5 IMU2_ACC_INT1\|PE6 IMU2_GYR_INT3\|PE2 IMU3_CS\|PB2 IMU3_INT1\|PC2_C BATT2_VOLTAGE\|PC3_C BATT2_CURRENT)' hwdef.dat` returns 9 |
| Board pad-net updates applied | `pcbnew.LoadBoard().GetFootprints()['U1']` pad 39 net = "MOT3", pad 95 net = "MOT7", pad 36 net = "IMU3_INT1" — all confirmed |
| Old IMU3_INT1 F.Cu trace removed | `[t for t in brd.GetTracks() if t.GetNetname()=='IMU3_INT1']` returns 0 |
| DRC baseline preserved | `kicad-cli pcb drc` reports 21 errors (same as pre-remap baseline) |
| MIRROR_PAIRS 11/11 intact | `audit_layout_compliance.py` no MIRROR_PAIR warnings |
| Rule 18 + Rule 19 added to MASTER_PROCESS_RULES.md | `grep -n '^## Rule 18\|^## Rule 19' docs/MASTER_PROCESS_RULES.md` returns 2 lines |

## 8. Files changed

| File | Type | Purpose |
|---|---|---|
| `hardware/kicad/novapcb/sheets/esc_3f.py` | SKiDL | motor_map remap |
| `hardware/kicad/novapcb/sheets/imu_3c.py` | SKiDL | IMU3_INT1 PE11→PB2 |
| `hardware/kicad/novapcb/novapcb.net` | generated | regenerated netlist |
| `firmware/hwdef-novapcb/hwdef.dat` | firmware | pin block + UART removal + discrepancy fixes |
| `hardware/kicad/novapcb-stepwise/novapcb-stepwise.kicad_pcb` | board | U1 pad-net reassignment + old IMU3_INT1 trace removal + zone refill |
| `hardware/kicad/novapcb-stepwise/route_pin_remap.py` | wrapper | applies netlist diff to board + (future) routing template |
| `docs/MCU_PIN_MAP_AUDIT.md` | doc | full pin map + reach analysis (carried from PR #82 DRAFT) |
| `docs/MASTER_PROCESS_RULES.md` | doc | Rule 18 + Rule 19 added |
| `docs/PR_PIN_REMAP_R_BROAD.md` | doc | this PR doc |

## 9. Test plan

- [x] SKiDL motor_map: 6 new pin assignments verified
- [x] SKiDL imu_3c: IMU3_INT1 PE11→PB2
- [x] Netlist regen: ERC 0 errors
- [x] All 8 MOT* nets + IMU3_INT1 bind to new U1 pads (verified via pcbnew)
- [x] hwdef.dat: MOT block updated, UART4+UART7 removed, 9 discrepancy nets added, SERIAL_ORDER updated
- [x] Board: 13 U1 pads net-reassigned; old IMU3_INT1 trace removed
- [x] DRC: 21 errors (baseline preserved); unconnected 264 (=263 baseline + 1 for new IMU3_INT1 pad needing route)
- [x] MIRROR_PAIRS 11/11 unchanged; STACKUP-SPEC-MATCH PASS
- [x] Rule 18 + Rule 19 codified in MASTER_PROCESS_RULES.md
- [x] Audit doc carried forward (no PR #82 separate merge)
- [ ] **Next sub-step** (separate PR): route 10 deferred unconnected items per option α/β/γ
