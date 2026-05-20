# Phase 4d2 — 17-net routing completion — RESULTS

> **Outcome**: **0 of 17 nets routed cleanly.** Naive L-shape Manhattan router crashed into the dense 96%-Freerouted board on every net. Board reverted to pre-4d2 state.
>
> **Verdict**: Phase 4d failure mode (Phase 4d 3-iter tripwire on whole-board scripted routing) reproduces at the net-by-net level when the router has no obstacle awareness. **Rule-13 stop per master's "one honest attempt per net" directive.** Hand back to `ROUTING_HANDOFF.md` GUI flow.

---

## What I tried

Per ROUTING_HANDOFF.md, 17 nets with documented pad endpoints. `run_route_17nets.py`:
- API-measured every pad position (no estimates, per KICAD9_NOTES discipline).
- For each net, added simple L-shape tracks pad-to-pad (or pad-via-pad for F.Cu↔B.Cu crossings).
- Set `IsLocked()=True` on every new track.
- Used per-net-class widths (USB_DP 0.25mm, DShot 0.20mm, SDMMC 0.15mm, etc.).

Per the routing-approach pre-recommendation in `tasks/phase-4d2-routing-completion.yaml`: "One honest attempt; lock on success; named-net residual if any."

## Actual result

| Net | Items added | DRC violations from my routing | Status |
|---|---|---|---|
| HSE_OUT | 4 | 23 | FAIL — crosses +3V3 plane + existing tracks |
| USART1_RX | 2 | 10 | FAIL — crosses existing tracks |
| MOT1 | 2 | 28 | FAIL |
| MOT2 | 2 | 24 | FAIL |
| MOT3 | 2 | 11 | FAIL — long N-to-S route shorts to +3V3 plane |
| USB_DP | 2 | 34 | FAIL — naive geometry, crosses many existing tracks |
| I2C2_SDA | 5 | 22 | FAIL — crosses +3V3 + adjacent I²C |
| I2C2_SCL | 5 | 11 | FAIL |
| SWDIO | 3 | 8 | FAIL |
| SWCLK | 3 | 16 | FAIL |
| NRST | 5 | 20 | FAIL |
| SDMMC1_CLK | 3 | 26 | FAIL — B.Cu segment hits J2 keepout |
| SDMMC1_CMD | 5 | 30 | FAIL — same B.Cu keepout |
| SDMMC1_D0 | 5 | 37 | FAIL |
| SDMMC1_D1 | 5 | 44 | FAIL |
| SDMMC1_D2 | 5 | 32 | FAIL |
| SDMMC1_D3 | 5 | 41 | FAIL |

**Total DRC violations introduced by 4d2: 345 (vs 0 on the pre-4d2 board).**

Violation type breakdown (touching my routes):
- `tracks_crossing` — 141 (my L-shapes crossed existing F.Cu / B.Cu tracks)
- `shorting_items` — 140 (my L-shapes shorted to copper planes — primarily +3V3 / GND)
- `clearance` — 46 (my L-shapes ran too close to existing tracks/pads)
- `items_not_allowed` (keepout) — 5 (SDMMC B.Cu segments crossed the J2 microSD body keepout area)
- `hole_clearance` — 1

## Why it failed

Same root cause as Phase 4d (the 3-iter 53→81→6 tripwire master flagged): **a scripted Manhattan router with no obstacle awareness cannot solve dense-board completion**. The 96%-Freerouted board has tracks + vias + planes occupying nearly every direct path between MCU pins and the 17 ratline endpoints. My L-shapes pick the shortest geometric route — which on this density is guaranteed to cross obstacles.

Per-net analysis confirms this isn't a sub-set-of-nets problem (which would have indicated a fixable hot-spot) — it's the underlying approach. **All 17 nets failed for the same fundamental reason: no obstacle avoidance.**

## What I did NOT do (per master's directive)

- **Did not zigzag on any single net.** Per-net rev-count tripwire respected.
- **Did not iterate the whole-board approach.** Phase 4d already proved this fails (3 iter → 6 violations residual + master halted).
- **Did not implement a fancier router** (e.g., obstacle-graph A*, manual zone-avoidance, layer-switch heuristics). That would be net-new infrastructure beyond the "one honest attempt" framing.
- **Did not silently modify the design.** The board is reverted to pre-4d2 state (771 tracks + 153 vias, 0 DRC errors — same as PR #48 main).

## Recommendation

**Hand back to `ROUTING_HANDOFF.md` GUI flow.** It was the original Phase 4d adjudication. KiCad 9 GUI's interactive router has:
- Obstacle-aware push-and-shove routing
- Diff-pair length tuning for USB_DP (the 90Ω class width 0.25mm / gap 0.10mm geometry is already set in `.kicad_pro`)
- Layer-aware crossings (vias auto-placed)
- DRC live feedback

The 17 nets per ROUTING_HANDOFF.md remain the correct authority: per-net endpoint list + class assignments + geometry hints already documented.

## Reverted state

```
post-revert: 771 tracks + 153 vias (Freerouting baseline)
kicad-cli pcb drc: Found 0 violations
```

Confirmed via `git checkout hardware/kicad/novapcb-layout/novapcb-layout.kicad_pcb` + DRC verification.

## Artifacts kept (committed in this PR)

- `tasks/phase-4d2-routing-completion.yaml` — task contract with falsifiable pre-prediction + actual-outcome captured.
- `hardware/kicad/novapcb-layout/run_route_17nets.py` — the attempt script. **Useful as a documented dead-end** so a future Claude doesn't re-attempt the naive Manhattan approach. The script header notes "ZERO obstacle awareness — this approach proven INFEASIBLE on the 96%-routed board, see phase-4d2-results.md".
- This results doc.

The .kicad_pcb is NOT modified (reverted to main).

## Updated falsifiable-prediction discipline note

Prediction was 11-14 of 17 clear; actual was 0 of 17. **Prediction was wrong in the same direction as Phase 4d** — both times I underestimated how thoroughly the dense routing space blocks naive line-of-sight L-shape routes. Lesson encoded for next router attempt: **no naive-router prediction should be ≥4-of-N on a >80%-routed board without obstacle-aware pathfinding implemented first**.
