# PR — IMU Slot Deferred to v2

> **Branch**: `docs/imu-slot-v2-defer` off `sch/option-b-buck` head `ba7e28c`
> **Scope**: Doc-only PR. No layout touch. Defer IMU stress-relief slot
> from v1 to v2 after 2 layout-attempt failures.
> **Master sign-off**: 2026-05-24 (path E after (β) Y=45 attempt
> produced 27 net new DRC violations matching Y=33's 35).
> **Trigger**: Two-time-failure at any latitude = slot doesn't belong
> in v1; alignment with `DECISIONS.md §2` v1-functional-only / v2-mechanical scope split.

---

## Symptom

IMU stress-relief slot was tracked as sub-step #102 (deferred from D
placement). Master directed full constraint analysis + execution.
Two layout-attempt failures:

1. **Y=33 latitude attempt** (`hw/imu-slot-polygon` first try):
   - 35 net new DRC violations (DRC 10 → 45)
   - 22 copper_edge_clearance from PR #76 stitching vias at Y=32 sitting
     0.25mm from slot top Y=32.5
   - Pre-existing SPI3_SCK via at (58, 33) on slot edge
   - 4 invalid_outline from overlapping rectangle corners
   - Reverted clean.

2. **Y=45 latitude attempt** (master's (β) shift):
   - 27 net new DRC violations (DRC 10 → 37)
   - 11 tracks_crossing — 4 detour traces through bridge X=58..68
     collide with PR #77 SPI2_MOSI/SPI2_MISO/SPI2_SCK/IMU2_ACC_CS/
     IMU2_GYR_INT3 already routed densely in same region
   - 11 copper_edge_clearance from pre-existing +3V3 traces at X=52.6
     sitting 0.4mm from slot W edge X=53
   - Reverted clean.

Both failures escalated to master with options analysis. Master called
(E) defer to v2.

## Fix

Doc-only changes on this branch:

### 1. `docs/DECISIONS.md` — new §2.1

Added §2.1 "IMU stress-relief slot — DEFERRED to v2". Documents:
- Both layout-attempt failures with root cause for each
- Cosmetic-only alternative (F: S+E-only) rejection rationale (N-side is dominant flex-coupling, not S/E)
- Alignment with §2 v1-functional / v2-mechanical scope split
- Residual cost quantified (1-3 mdps/√Hz extra gyro noise under heavy vibration)
- ArduPilot harmonic-notch + dynamic-notch software mitigation
- v2 groundwork preserved at `docs/v2/D_SLOT_POLYGON_ANALYSIS.md`
- FUTURE-PROOFING NOTE: deferred mech constraints MUST be first-class at routing time for v2

### 2. `docs/v2/D_SLOT_POLYGON_ANALYSIS.md` — move + v2 banner

Full 494-line analysis (original + 2 amendments) preserved verbatim
under `docs/v2/` with v2-scope banner at top citing:
- DECISIONS.md §2.1 deferral
- Both layout-attempt failure modes
- "v2 plans slot as first-class constraint at routing time"

Not a duplicate — the doc was on `hw/imu-slot-polygon` branch only, never
merged to `sch/option-b-buck`. This PR moves it to its v2-permanent
home.

### 3. `scripts/audit_layout_compliance.py` — IMU-SLOT message update

`check_imu_slot()` info-only message updated:
- Before: "IMU-SLOT: no Edge.Cuts shape complex enough to verify"
- After: "IMU-SLOT: DEFERRED to v2 per DECISIONS.md §2.1 (see docs/v2/D_SLOT_POLYGON_ANALYSIS.md)"

Gate stays info-only (not removed) — primed for v2 reactivation. Logic
unchanged; only the message text updated to match the v1 deferral
state.

## Root cause

PR #77 (D↔C/B routing) ran Freerouting WITHOUT slot geometry as a
constraint. The autorouter took shortest paths through what would have
been the slot zone, filling the bridge column densely and placing
vias near future slot edges. Adding slot retroactively required:
- Surgery on already-merged PR #76/#77/#78 routes
- Cluster-walk regression risk on every touched net
- Bridge column saturation (24 nets requested vs 14 capacity)

The 2x failure pattern is the signal: slot is incompatible with the
post-route board state. Either it lives in v1 with mass surgery
(rejected — invalidates merged work, regression risk), or it moves to
v2 where it's planned upfront.

## Prevention

### FUTURE-PROOFING — first-class constraints, not retrofits

When a mechanical/geometric constraint is deferred during a placement
phase, the routing phase MUST either:
- (a) treat the deferred constraint as already-present (route around its
  future footprint), OR
- (b) explicitly accept the constraint will be DEFERRED to a later board
  revision and not added retroactively to this one.

This v1 attempt mistakenly took path (c): defer the constraint AND try
to add it later. That's the failure mode. v2 will follow (a) — slot
geometry is in the constraint set from day one of placement +
routing, with bridge column reserved at the placement stage.

Codify in `docs/MASTER_PROCESS_RULES.md` next revision: "deferred
constraints are either pre-reserved in current routing OR deferred to
next board rev — never retroactively retrofit."

## Spec deviations (Rule 4)

This PR is a scope-alignment doc — IMU slot was outside v1 scope per
DECISIONS.md §2 originally. The 2x attempts were the deviation; this
PR restores alignment.

**No board-state deviations** — `sch/option-b-buck` head `ba7e28c`
remains the merge target's current state. No layout touch, no DRC
runs needed.

## Rule 9 verification (artifact-level)

| Claim | Verified by |
|---|---|
| DECISIONS.md §2.1 added | `grep -n '2.1 IMU stress-relief'` returns 1 match |
| Slot analysis preserved at docs/v2/ | `ls docs/v2/D_SLOT_POLYGON_ANALYSIS.md` returns file 20.8KB |
| Analysis content unchanged from `hw/imu-slot-polygon:docs/D_SLOT_POLYGON_ANALYSIS.md` | content copied via `git show`, only v2-banner header added |
| Audit IMU-SLOT message updated | `python3 scripts/audit_layout_compliance.py …` shows "DEFERRED to v2 per DECISIONS.md §2.1" |
| No board changes | `git diff sch/option-b-buck -- hardware/kicad/novapcb-stepwise/novapcb-stepwise.kicad_pcb` = empty |
| No DRC change | board untouched; DRC remains baseline 10 |

## After this lands

Resume forward queue per master sequencing:
1. H placement (ESC outputs)
2. H↔C routing
3. G-remainder placement
4. G↔C routing
5. DRU cleanup PR #97 (pre-Phase-7a)
6. U6 DECOUPLING task #91 (pre-existing)
7. Full board sim suite
8. JLCPCB DFM check
9. Phase 7a freeze (Sai-only)

Slot was the last D-zone integration blocker. With deferral, path to
Phase 7a is unblocked.

## Test plan

- [x] DECISIONS.md §2.1 present with 2-attempt root cause + (F) rejection rationale
- [x] docs/v2/D_SLOT_POLYGON_ANALYSIS.md present with v2 banner
- [x] Audit IMU-SLOT info message updated
- [x] No board changes (board file unchanged)
- [x] No DRC delta (board untouched, baseline 10 preserved)
- [x] Branch `hw/imu-slot-polygon` work preserved in v2 path (not lost)
