# +3V3_IMU rail gap-close — per-trace fix plan (NEXT SESSION)

> **Status:** plan-ready 2026-05-26 (master). Execution waiting on focused fresh-context worker pass — per Rule 17 (no loose threads) + Rule-surely-working-over-SOTA: dense IMU pocket needs careful per-trace work, not late-session iteration.
> **Priority:** flight-critical (IMU3 unpowered + IMU2 decaps floating as routed). MUST land before Phase 7a freeze trigger.
> **Sai-gate:** none — pure execute. Master pre-merges gate-clean.

---

## 1. The defect

Worker Rule-9 belt-and-suspenders pass at head 5390be4 (post PR #120) caught 5 unconnected pads on +3V3_IMU rail:

| Pad | Coords (mm) | Gap to nearest rail | What it powers |
|---|---|---|---|
| U9.5 | 78.50, 56.08 | 0.28 mm | LSM6DSV16X (IMU3) VDD |
| U9.8 | 76.83, 56.25 | 1.76 mm | LSM6DSV16X (IMU3) VDDIO |
| C91.1 | 67.3, 54.1 | 2.55 mm | BMI088 (IMU2) decap |
| C92.1 | 70.5, 57.0 | 0.85 mm | BMI088 (IMU2) decap |
| C93.1 | 67.8, 59.9 | 2.60 mm | BMI088 (IMU2) decap |

**As-routed flight capability:** IMU1 (ICM-42688 on SPI1) is fully powered + decoupled. v1 arms on IMU1 alone. IMU2/IMU3 redundancy is broken. NOT acceptable for v1 fab.

**Likely origin:** pre-existing from PR #105 Topology-a rail with near-miss gaps; was buried under ~213 total unconnected (dominated by intended-unrouted MOT7/8 + Telem/SWD defers).

---

## 2. Why the dense-pocket iteration risk

Worker tried 3 closure approaches in current session:
1. **Scoped Freerouting on +3V3_IMU**: 0/5 gaps closed (couldn't thread).
2. **Crude pure-add F.Cu stubs + vias**: closed all 5, but **27 new violations** — vias collided in the dense via field (`hole_clearance` ×8, shorts to `IMU2_GYR_CS` + GND, zone clearance, solder-mask bridges).
3. **Careful U9.5/8 → C94.1 F.Cu only (no vias)**: still 3 violations — U9 power pins 5/8 are **flanked by GND pins 6/7 at the SAME Y=56.08**, so any F.Cu trace grazes them.

Root cause of iteration: this is the same dense pocket flagged in worker's memory as "iteration-prone" (cost ~5 iters on HSE cap work). HSE crystal + 3 IMUs + 9 decaps + +3V3_IMU rail + GND stitch + IMU3_INT1 trace all converge in <15×10 mm.

**The fix is achievable but each gap needs B.Cu-under-GND-pins routing + precise via placement avoiding the dense pad/via field. Per-gap, this is ~1-2 careful DRC iterations with full obstacle modeling.**

---

## 3. Per-gap execution plan

### 3.1 U9.5 (78.50, 56.08) + U9.8 (76.83, 56.25) — IMU3 VDD + VDDIO

**Obstacle:** U9 pins 6/7 are GND, at the same Y as pad 5. Pure F.Cu trace from U9.5 grazes pin 6/7. ✗
**Target:** C94.1 (77.52, 54.50, F.Cu, N of U9) — this IS on the +3V3_IMU rail.

**Approach:**
1. **U9.5 → C94.1:** drop to B.Cu immediately at U9.5 pad via small via (LGA-14 doesn't have a pad-fanout requirement — direct via if pad allows; else 0.5mm stub south on F.Cu first). B.Cu trace south then west to a 2nd via at C94.1's south side. Verify via #1 clears U9.6 GND pad by ≥0.15mm hole_clearance (likely needs 0.4mm OD via or smaller).
2. **U9.8 → C94.1 or C95.1:** similar B.Cu-under approach. U9.8 is at X=76.83 — west of U9.5. Drop to B.Cu, trace west, return F.Cu at the rail trunk.

**Via constraints:**
- OD ≤0.45mm (matches DFM PR #109 baseline)
- Hole 0.25mm (per DFM)
- Annular ≥0.10mm
- Clearance to nearest pad ≥0.15mm

**Order matters:** route U9.8 first (longer route, more constrained); U9.5 second (0.28mm gap = literally a stub).

### 3.2 C91.1 (67.3, 54.1) → rail @ Y=56.58

**Obstacle:** U8.7 GND pin sits between C91.1 and the rail trace south. Gap is 2.4mm net.
**Approach:** B.Cu trace south from C91.1 (drop via at C91.1), under U8.7 GND pad, return F.Cu at the rail via. Single via per end. 

### 3.3 C92.1 (70.5, 57.0) → rail @ Y=56.58

**Obstacle:** rail is 0.42mm south. Needs via to drop to B.Cu (since F.Cu space is taken by C92.2 GND + U8.12). Single via under C92.1 land.
**Approach:** B.Cu trace 0.42mm south to rail location, return F.Cu via. Short route.

### 3.4 C93.1 (67.8, 59.9) → rail @ Y=59.94

**Obstacle:** rail passes ~under C93.1 at Y=59.94 already. Needs via to drop F.Cu pad to B.Cu rail.
**Approach:** single via at C93.1 land, drop to B.Cu, rail meets it (or 0.1mm B.Cu stub).

---

## 4. Execution sequence (recommended)

Order by reversibility risk + DRC blast radius (lowest risk first to build confidence):

1. **C93.1 (easiest)** — single via, rail already under it. Verify DRC clean before moving on.
2. **C92.1** — single via + 0.42mm B.Cu stub. DRC clean.
3. **C91.1** — B.Cu under U8.7 GND, 2 vias. DRC clean.
4. **U9.5 (0.28mm gap)** — small stub or single via. DRC clean.
5. **U9.8 (1.76mm gap, hardest)** — B.Cu under U9.6/7 GND, 2 vias. DRC clean.

After each gap, verify:
- +3V3_IMU per-net unconnected dropped by 1
- DRC total didn't gain a new violation
- No short to neighboring net (IMU2_GYR_CS, IMU3_INT1, GND fields)

If any single gap introduces >0 new violation → revert that gap, re-plan with a different approach (e.g. different via location, different layer). Don't carry forward partial work.

---

## 5. Verification gates (mandatory before merge)

- [ ] **+3V3_IMU per-net unconnected = 0** (was 5)
- [ ] **Overall DRC ≤ baseline 12 + 0 new** (baseline confirmed at PR #120)
- [ ] **Per-net cluster walk** on +3V3_IMU trace network — F.Cu over In3.Cu (+3V3 plane); B.Cu over In4.Cu GND plane
- [ ] **ArduPilot waf copter build verify** (same gate as #119, #120) — no firmware-side effect expected (this is pure layout) but required for freeze conformance
- [ ] **ERC clean** (no schematic side-effect; gap-close is layout-only)
- [ ] **Touch test:** USB diff pair (PR #75) untouched, SPI1/2/3 untouched, IMU2_GYR_CS / IMU3_INT1 / GND stitching untouched
- [ ] **DRU rules untouched** (per PR #106 audit baseline)

---

## 6. Why fresh context is the right call

Worker is currently deep into an extraordinarily long session (~30 PRs landed). Three closure attempts already absorbed iteration budget. The remaining work is per-trace careful surgery in a pocket flagged as iteration-prone in worker's own memory.

Per `feedback-no-loose-threads`: time flexes to the quality bar, not the reverse. Per `feedback-surely-working-over-sota`: confidence-in-function > chasing SOTA in the current pass.

A focused fresh-context worker pass:
- Brings a clean attention budget to dense pocket per-trace work
- Has this doc as the per-gap plan (no re-discovery cost)
- Can verify each gap before moving on (5-step sequence above)
- Lands one clean PR vs a partial/violation-laden one

Master pre-merges gate-clean per delegated authority (`feedback-pr-merge-delegated`). Sai-gate = none.

---

## 7. NOT a v2 defer

This is **next-up for fresh worker context**. It MUST land before:
- Phase 7a freeze trigger (Sai)
- Any future "flight-routable" or "all-IMUs-functional" claim
- BOM final verify (because IMU3 dead = BOM still includes U9 wasted spend)

If the dense pocket genuinely cannot accept the closure, the fallback is **drop U9 (LSM6DSV16X) from v1** (true v2 defer with BOM update + DECISIONS.md amendment) — but that's a real scope change that needs Sai ratification. Don't reach for that until 1+ fresh attempts fail.

---

## 8. Status flags to update after merge

- `STATUS.md`: restore "flight-routable" line correctly (all 3 IMUs powered + decoupled)
- `PHASE_7A_FREEZE_CHECKLIST.md`: flip the routing line back to ✅
- `docs/LSM6DSV16X_DECAP_CLOSURE.md`: append "+3V3_IMU rail confirmed connected to U9 in PR #N" — the bulk-via-shared-rail conclusion now stands on actual connectivity
- `docs/MASTER_PROCESS_RULES.md`: add **Rule 23 per-net unconnected audit** (master draft pending; would have caught this after PR #105)
- `scripts/audit_layout_compliance.py`: add audit gate failing on per-net unconnected > 0 for any power rail (+3V3, +3V3_IMU, +5V_BEC, GND)

---

**Plan author:** master 2026-05-26.
**Diagnostic data source:** worker's 3-attempt close + obstacle survey, same session.
**Execution dispatch:** next fresh worker context.
