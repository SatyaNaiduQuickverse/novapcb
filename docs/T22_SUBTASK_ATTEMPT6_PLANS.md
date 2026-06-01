# T22 sub-task Attempt-6 plans — master pre-think (2026-06-01)

> Per Sai 2026-06-01 "no deferring, finish all now" mandate. The 5 first-sweep
> reach failures (T3 LEDs, T11 ESC TVS, T12 microSD ESD, T14 buzzer, T16 SD CD)
> must actually land hardware in v1. Their REACH_FAILURE.md docs are now obsolete
> pending T22 completion.
>
> Worker uses these plans when cycling to T22 sub-tasks. Order: smallest-first
> for momentum + dependency-aware (T11/T12/T16 may benefit from T20 SDMMC1
> re-route opening corridors).

## T22.1 — T16 microSD card-detect (smallest target, do first)

**First-sweep failure mode:** all 18 free MCU pins yielded 47+mm trace to J2.10
because the corridor was populated.

**Attempt 6 strategy:**
- **6a:** Re-pin to a MCU corner pin physically closest to J2 at (95, 67).
  Survey nearest free pins on the East-Cu MCU edge. Even unusual pins
  acceptable since CD is just a GPIO input.
- **6b:** Route via B.Cu under the SDMMC1 group. Could share corridor T20
  opens (if T20 lands first).
- **6c:** Re-place J2 1-2mm to shorten the CD pin distance to MCU corridor.

**Sim re-validation needed:** none (CD is DC-level signal).
**Scope-creep risk:** low (1 GPIO + 1 trace, fab-tier classification if any).

## T22.2 — T3 PGOOD power-rail LEDs (small target, board-corner)

**First-sweep failure mode:** placement cascade.

**Attempt 6 strategy:**
- **6a:** Place 5 LEDs on B.Cu N-corner (X=10-30, Y=5-15) — open area per
  initial board survey. Reuse existing R41-R44 + 1 new R for eFuse PGOOD.
  Each LED needs ~3mm trace to its rail (planes are near).
- **6b:** Split LEDs across corners if N-corner doesn't have enough space.
- **6c:** Use smaller 0201 LEDs if 0402 don't fit (1.0 × 0.5 mm vs 1.6 × 0.8).

**Sim re-validation needed:** none.
**Scope-creep risk:** low (passive shunts to existing planes).

## T22.3 — T14 piezo buzzer (medium, needs corridor for 24mm trace)

**First-sweep failure mode:** 24mm F.Cu trace to J5.9 cascaded +18 DRC.

**Attempt 6 strategy:**
- **6a:** Wait for T20 SDMMC1 westward re-route → use freed NE corridor for
  buzzer trace too (BUZZER pin PD7 might run through similar lanes as USART1).
- **6b:** Route buzzer via B.Cu corridor (different from F.Cu T14 first
  attempt). Buzzer is low-current DC signal — no SI constraint.
- **6c:** Re-place buzzer near J5 (instead of at (8, 50)) — 5mm distance
  to J5.9 instead of 24mm.

**Sim re-validation needed:** none.
**Scope-creep risk:** low.

## T22.4 — T11 ESC TVS (hardest, J11 fanout constrained)

**First-sweep failure mode:** J11 1.25mm pitch + 17×9.5mm courtyard + 0.25mm
board edge S + 0.5mm power-zone clearance + 8-stub fanout = all attempts walled.

**Attempt 6 strategy:**
- **6a:** Re-place J11 north by 5mm to free S-edge area for TVS placement
  + fanout. Mech impact: ESC pigtails will exit 5mm further from board
  bottom edge — acceptable for typical drone frame.
- **6b:** Use 8× single-channel TVS (PESD3V3L4UG or similar SOT-323) instead
  of 2× quad-array. Smaller footprint, distributed placement, each TVS gets
  its own short stub.
- **6c:** Common-mode TVS array on the GROUND side (not the signal side) —
  protects via common-mode events without per-signal stubs.
- **6d:** Add a satellite ESD board concept — defer to v2 ONLY if 6a/6b/6c
  all wall. But per Sai mandate, push 6a/6b/6c harder before resort.

**Sim re-validation needed:** none (TVS additions don't change steady-state).
**Scope-creep risk:** medium (J11 re-place touches placement audits).

## T22.5 — T12 microSD ESD (depends on T20 SDMMC1 re-route)

**First-sweep failure mode:** J2 area B.Cu density + +3V3/GND zone clearance
+ SDMMC1 HANDS-OFF = walled.

**Attempt 6 strategy (sequenced AFTER T20):**
- **6a:** Use Sim 3 re-validated SDMMC1 westward routing — TVS now has cleaner
  J2-side B.Cu area to drop into.
- **6b:** Re-place J2 1-2mm if SDMMC1 re-route alone doesn't open enough.
- **6c:** Smaller TVS footprint (PESD3V3 SOT-323 series instead of TPD4S+
  larger quad). Per-line single TVS, distributed placement.
- **6d:** If still walls after 6a/6b/6c: this is the case where v1 might
  legitimately ship without (industry standard for internal SD). But push
  attempts 6a-6c HARD first per Sai mandate.

**Sim re-validation needed:** Sim 3 re-validation already in T20 contract
(this T22 sub-task piggybacks on that).
**Scope-creep risk:** medium (J2 re-place touches mech assumptions).

## Process discipline (all 5 sub-tasks)

- Per-net unconnected audit ABSOLUTE
- Scope-creep cap watch (currently 4/4) — no NEW scope-creep exceptions; new
  exceptions must be FAB-TIER (inherent package) classification
- Multi-session WIP commits OK
- Per-task PR with full DRC + sim + audit status
- NO v2-defer outcome
- If ALL attempts (6a through 6d/e/f) wall structurally on any sub-task,
  escalate to master for re-think — DO NOT silently accept reach failure

## Execution order

1. **T22.1 T16 SD card-detect** (smallest, no dependency) — first
2. **T22.2 T3 LEDs** (small, B.Cu corner, no dependency) — second
3. **T20 lands first** (SDMMC1 westward) — opens corridors
4. **T22.3 T14 buzzer** (uses opened corridor) — after T20
5. **T22.5 T12 microSD ESD** (uses SDMMC1 re-route) — after T20
6. **T22.4 T11 ESC TVS** (hardest, J11 re-place) — last
7. **Sim re-validation** (Sim 1 thermal + Sim 5 PDN if heat sources moved)
8. **Final freeze gate audit** per `docs/PHASE7A_FREEZE_PROCEDURE.md`
