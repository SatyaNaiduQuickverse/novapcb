# Phase 7a — Fab-Ready Freeze Procedure

> **Purpose**: lock the validated v1 design state as the "surely-works"
> baseline (per DECISIONS §12 — Sai's freeze-at-fab-ready directive)
> via an immutable git tag `v1.0-fab-ready-frozen`, BEFORE the actual
> fab order (Phase 7b — Sai sign-off only) and before any shrink work
> (Phase 7.5).
>
> **Status**: procedure document; freeze NOT yet executed.

---

## 1. What "fab-ready" means (the freeze gate)

A commit can carry the `v1.0-fab-ready-frozen` tag only after ALL these
are true. The checklist is the gate.

### 1.1 Routing

- [ ] 0 DRC errors
- [ ] 0 unconnected items
- [ ] 0 signal misroutes on inner plane layers (`sims/enumerate_inner_layer_signals.py` → `misroute_count == 0`)
- [ ] Inner planes (In1-In4) ≥ 90% main-outline fill, single-outline each (no fragmentation voids; `sims/emc-6k/results_step6.json` → `6k.1` PASS)
- [ ] USB diff pair on F.Cu+B.Cu microstrip referenced to In1.Cu/In4.Cu GND, W=0.30/S=0.10, length-matched within USB 2.0 ±150 ps skew tolerance
- [ ] All plane-net pads stitched (every SMD plane-net pad on outer layer has a same-net via dropping to its inner plane)

### 1.2 Schematic

- [ ] DRC `--schematic-parity` → 0 errors (board matches netlist exactly)
- [ ] BOM ↔ netlist parity: every footprint reference appears in `bom/novapcb-bom.csv` and vice versa

### 1.3 Step 6 sims dispositioned

- [ ] 6a Power tree (eFuse front-end): PASS (`sims/power-6a/results_step6.json`)
- [ ] 6b USB diff-pair SI: PASS (analytical H-J + via-transition model; Phase 9 bench is final verdict; `sims/block_a_results_final.json`)
- [ ] 6c IMU SPI SI: PASS or design change (series term R if needed)
- [ ] 6f SDMMC SI: PASS (lumped regime, slow SDMMC)
- [ ] 6g DShot SI: PASS (electrically tiny)
- [ ] 6i ESD/input protection: PASS for +5V_BEC (eFuse+Q2+TVS); remaining JST-GH gaps documented as Phase 6.5 forum-review queue items, NOT Phase 7 blockers (`sims/esd-6i/results_step6.json`)
- [ ] 6j Thermal: PASS (Step 4 result valid post-route; convection-limited regime; `sims/thermal-6j/results_step6.json`)
- [ ] 6k EMC: PASS (post-route plane integrity 90-94%; harmonic-band intersections unchanged from pre-route, 4 critical-band hits on Phase 6.5 review; `sims/emc-6k/results_step6.json`)
- [ ] 6l ArduPilot SITL functional: PASS (unchanged by pivot; PR #52)
- [ ] Block B OpenEMS Z0 — UNAVAILABLE-DIVERGED disposition recorded honestly (analytical+bench is the floor; `sims/usb-diffpair-6b/openems_z0_attempt.json`)

### 1.4 DFM (manufacturability)

- [ ] DFM against JLCPCB 6-layer (JLC06161H-7628) standard rules — 0 violations
- [ ] Project rules (min track 0.10mm / clearance 0.10mm / hole 0.30mm / via 0.40mm) meet/exceed JLC standard tier
- [ ] Gerber export strict pass (no `--allow-incomplete`); all 13 gerbers + drill + POS + STEP + IPC-2581 produce cleanly

### 1.5 Documentation

- [ ] DECISIONS.md current (all locked decisions reflected)
- [ ] CONTROLLED_IMPEDANCE.md current
- [ ] DESIGN_PHASES.md reflects Phase 7a entry
- [ ] OPEN_QUESTIONS.md has no Phase 7-blocking items (anything outstanding documented as Phase 6.5 forum review queue or v1.x scope)

---

## 2. Freeze execution

Once §1 checklist is GREEN, the freeze is an immutable git tag.

**Pre-conditions:**
- All Step-6-related PRs merged to `main`
- `main` is at the fab-ready commit
- `gh pr list` shows no open Phase-7-blocking PRs

**Procedure** (master may execute; Phase 7b ORDER is Sai-only):

```bash
cd ~/novapcb
git checkout main && git pull --ff-only

# Verify the freeze gate one last time
python3 sims/enumerate_inner_layer_signals.py | grep "TOTAL"
# Expect: TOTAL signal misroutes on plane layers: 0 nets, 0 mm total
kicad-cli pcb drc --severity-error --exit-code-violations \
                  --units mm hardware/kicad/novapcb-layout-v2/novapcb-layout-v2.kicad_pcb
# Expect: 0 violations
python3 hardware/kicad/novapcb-layout-v2/run_gerber_export.py
# Expect: pipeline completes WITHOUT --allow-incomplete

# Create the tag
TAG="v1.0-fab-ready-frozen"
git tag -a "$TAG" -m "Phase 7a freeze: v1.0 fab-ready baseline.

This commit is the validated, generously-margined 80×60 6-layer
JLC06161H-7628 design. The Step 6 sim regime is fully dispositioned.
Per DECISIONS §12 (Sai 2026-05-21), this tag preserves the
surely-works baseline. Phase 7.5 shrink-optimization may proceed
from this point; the tag itself is immutable.

Phase 7b (actual fab order) is Sai sign-off — master and worker
cannot place an order."
git push origin "$TAG"
```

**Acceptance**: tag visible at `https://github.com/SatyaNaiduQuickverse/novapcb/releases/tag/v1.0-fab-ready-frozen`.

---

## 3. What freezing does (and doesn't)

### 3.1 Does

- Locks the v1 design state as a git-immutable reference.
- Provides the rollback target if Phase 7.5 shrink work degrades margins.
- Provides the precise commit for Sai's fab-order sign-off.

### 3.2 Does NOT

- Place a fab order. Phase 7b is a separate hard-stop gate (Sai-only).
- Block further work. Phase 7.5 shrink-optimization PRs may begin
  immediately after the freeze, branched off the tagged commit.
- Prevent v1.x amendments. The frozen tag is one specific commit; v1.1
  / v1.2 development can branch off `main` post-tag.

---

## 4. Phase 7.5 — shrink optimization (post-freeze)

Per DECISIONS §12: after the freeze, incremental sim-driven shrinking
proceeds from the safe baseline. Each shrink step gets its own PR with:

- New dimensions
- Re-sim results vs the frozen baseline (thermal especially; SI; DRC)
- Which margin is closest to its limit
- Pass/fail vs the frozen baseline's margins

Phase 7.5 stops at the first margin-or-DRC violation. The frozen
baseline ships if no improvement is found.

---

## 5. Phase 7b — fab order (Sai-only)

Phase 7b is bounded by Sai's explicit sign-off. The actual order can
target either:

- The Phase 7a frozen baseline (`v1.0-fab-ready-frozen` tag)
- The Phase 7.5 post-shrink optimum (if Phase 7.5 produced one that
  passes all sims at the new dimensions)

Master and worker cannot place an order. The hand-off is a chat
message to Sai with:

- The candidate commit / tag
- Step-6-sim dispositions table (this checklist filled in)
- Estimated fab cost (~$50-100 JLCPCB 5-board run + stencil)
- Lead time estimate
- Sai's go/no-go reply triggers the actual order action.

---

## 6. Open items at time of writing

(Things explicitly held outside the freeze gate per master 2026-05-21.)

- **Plane-stitch GUI cleanup** (`PLANE_STITCH_GUI_HANDOFF.md`) — Sai's
  15-min interactive task. Blocks §1.1 last checkbox.
- **Block A SI sims final run** — gated on the GUI cleanup; scaffold
  ready at `sims/run_block_a_analytical.py`. Blocks §1.3 6b/6c/6f/6g.
- **Final strict-DRC gerber export** — gated on the above two.
- **Phase 6.5 forum review** for the documented gaps (3 JST-GH ESD
  connectors, 4 critical-band EMC hits). NOT Phase 7 blockers per
  master adjudication 2026-05-21.

When those 3 items resolve, the §1 checklist is fully green and the
freeze can execute.
