# T11 ESC TVS — v1 REACH FAILURE (full revert, 2026-05-30)

> Sai-directed SOTA push T11 (ESC outputs TVS on MOT1-MOT8 at J11).
> After 3 cascade attempts + master correction on Rule-17 half-state ban,
> the honest outcome is **v1 ships without ESC ESD/TVS clamp**. The board
> structurally can't fit 8 TVS stubs at J11's edge without major rework.

## 1. What was attempted

| Attempt | Approach | DRC severity-error | Outcome |
|---|---|---:|---|
| 1 | TVS B.Cu under J11, via at J11.pin + 0.6mm south | 28 → 58 (+30) | Vias landed INSIDE J11 1.70mm-tall SMD pad rectangles → 12 shorts. |
| 2 | Via offset calculated (J11.pin + 1.5mm south = pad south edge + clearance + via radius) | 28 → 78 (+50) | New vias collide with adjacent MOT routes on B.Cu; zone clearances against +3V3/GND/+5V_BEC zones (set at 0.5mm vs default 0.2mm). |
| 3 | Single shared +3V3 via at clear spot + B.Cu GND zone for clamp-bias | 28 → 76 (+48) | Long +3V3 B.Cu trace crosses 4 MOT* tracks; tracks_crossing + same-net pad shorts. |

## 2. Why structural

J11 (JST-GH SM10B-GHS-TB) is a 10-pin SMD connector with:
- 1.25mm pin pitch (0.60mm pad × 1.70mm tall, leaves 0.65mm pin-to-pin gap)
- 17×9.5mm courtyard bbox (includes mounting pegs at MP positions)
- North edge 0.25mm from board outline (Y=84.75 vs board Y=85)
- 8 MOT* signals already routed F.Cu + B.Cu (mix of layers per pin escape)
- +3V3 / GND / +5V_BEC zones in this area with 0.5mm clearance (larger than
  default 0.2mm) — historical decision for power-net signal isolation

Adding 8 through-vias + B.Cu fanout to 2 TVS ICs under J11 forces:
- Vias either inside J11 SMD pad rectangles (shorts) OR offset enough to
  collide with adjacent net routes
- B.Cu fanout traces cross each other on the limited B.Cu corridor
- Stitching vias for +3V3/GND clamp-bias trigger the wider zone clearances

Master suggested Attempts 4-6 (F.Cu south reposition, alternate TVS part,
4× 2-channel split). Engineering assessment of these:

| Suggested | Why infeasible / unlikely |
|---|---|
| 4 — F.Cu south of J11 | Only 0.25mm to board edge; physically impossible. |
| 4-alt — F.Cu north of J11 (Y=70-75 empty) | MOT1 routes via WEST edge (X=19.41) — 30mm away; MOT7/MOT8 unrouted (no path to tap). Only MOT2-6 reachable; partial protection = same half-state problem master rejected. |
| 5 — Different TVS pinout (PESD5V0X4, USBLC6-4SC6) | Pinout difference cosmetic; same 8-stub fanout geometry; same zone-clearance walls. |
| 6 — 4× 2-channel TVS | 4 ICs vs 2 (more board area + cost) but each IC still needs 2 stubs through the same congested area. Geometry not fundamentally simpler. |
| Freerouting Attempt 3 | Same DRC constraints; FR works within +3V3/GND zone clearances. 3 manual cascades suggest FR would plateau too. 1-2 hr setup with low success probability. |

## 3. Master correction on Rule-17 half-state

Master 2026-05-30 ratified the discipline: **placement-only with stubs
unrouted = half-state**. Ships TVS ICs assembled (BOM cost + PCB area +
assembly time) with **zero electrical benefit** because the protection
diodes have no signal path to clamp. Worse than not having them: confuses
debug, costs $ + assembly, no functional value.

Two acceptable outcomes:
1. Full route (DRC-clean, audit PASS)
2. Full revert (drop from BOM + SKiDL + placement)

This document records outcome (2).

## 4. What was reverted

- `hardware/kicad/novapcb/sheets/esc_3f.py` — D17/D18 SKiDL declarations
  + P3V3 net line removed (back to base)
- `hardware/kicad/novapcb/novapcb.net` — regenerated, no D17/D18 nodes
- `hardware/kicad/novapcb-stepwise/novapcb-stepwise.kicad_pcb` — D17/D18
  footprints removed; zones refilled
- `bom/novapcb-bom.csv` — row 55 (D17,D18) removed; back to 54 lines
- `scripts/audit_unconnected_per_net.py` — `INTENDED_DEFERRED_PADS` back
  to `{"C93.1"}`
- (Previous `docs/T11_TVS_DEFER.md` removed — that doc described the
  half-state that's now disallowed)

## 5. State after revert (clean)

- DRC severity-error: **28** (baseline, unchanged from pre-T11)
- `audit_unconnected_per_net.py`: PASS, **0 real-latent** unconnected
- `verify_bom.py`: 0 missing parts, 0 stale rows
- 8 unsourced TBDs (SAI-SOURCE Q5/L1/R45-48/J20/R61) unchanged

## 6. CONFIDENCE_MAP row 12 implication

Master 2026-05-30: "If Attempts 3-6 ALL wall structurally → that's a real
Rule-17 reach-failure: revert PR #142 entirely [...] document T11 as
'reach failure, v1 ships without ESC ESD' explicitly in CONFIDENCE_MAP
row 12 (would keep that row at MEDIUM not HIGH)".

Row 12 stays at MEDIUM (~80%) after T11/T12 (assuming T12 completes
full-routed). The T11 reach failure means MOT1-MOT8 lines remain
unclamped against ESD/back-EMF at the J11 cable interface.

**Operational mitigation**:
- Use shielded/twisted-pair ESC pigtails on the airframe
- Ferrites near J11 connector exit (user-side, post-fab)
- Avoid hot-plugging ESC leads with rotors spinning
- ESC internal clamping (most modern BLHeli ESCs have input clamps)

## 7. v2 path

v2 board respin can fix this by reserving space at Phase 4a:
- Either place J11 with ≥10mm south of its bbox for TVS row (board grows
  by 10mm in Y direction), OR
- Replace J11 with a J-shaped (90°) connector layout that puts MOT pins
  facing inward, allowing TVS placement east of pins, OR
- Allocate per-channel test pads + TVS pads in the layout BEFORE routing
  the MOT* signals (so the TVS taps are pre-allocated routing keep-outs)

## 8. Cross-references

- `feedback_dense_pocket_scan_geometry` — earlier project precedent on
  scanning courtyards + all track segments before placement decisions
- `feedback_root_cause_not_patch` — 2+ over-constraints at same pocket
  = re-place a passive (mostly applicable to v2 here)
- Master raise-the-bar dispatch 2026-05-30 + half-state correction
- `docs/CONFIDENCE_MAP.md` row 12 update
