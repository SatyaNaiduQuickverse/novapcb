# R4 Routing Handoff — Clean Base for Push-and-Shove Close-out (2026-05-22)

## Status

Per master 2026-05-22: numbers bouncing without clean convergence
(DRC 33 → 73 → 86 → 169; unconnected 143 → 57 → 53). Stopping
headless effort here. Sai to direct path forward, likely interactive
push-and-shove routing.

PCB reverted to **commit `14a2d46`** — the cleanest checkpoint:
Freerouting 3-signal stackup 88.8% routed, no whack-a-mole cleanup
residuals.

## Recoverable base

```bash
git checkout 14a2d46 -- hardware/kicad/novapcb-layout-v1.1/novapcb-layout-v1.1.kicad_pcb
```

Verified state at this commit:
- **988 tracks + 113 vias** (FR3 -mp 30 v2.2.3 SES imported)
- **67 unconnected items** (= 55 plane-stitch + 12 signal-net residuals)
- 3 marginal copper_edge_clearance (0.21–0.23mm vs 0.30mm) — minor
- 0 shorts, 0 mask_bridge, 0 invalid_outline
- Stackup: 3-signal (L1/L4/L6 sig; L2/L5 GND; L3 +3V3 plane)

## Residual breakdown

Total: 67 unconnected items, of which:

### Plane-stitch needed (55 items) — need stitch vias to inner planes

| Net | Items | Notes |
|---|---|---|
| +3V3 | 46 | Bulk of remaining work — many pads still need stitch vias to L3 +3V3 plane (~30+ failed/missed by earlier stitch script). MCU power pins 11/27/50/75/100 + various decap pads + IMU LDO. |
| +3V3_IMU | 4 | C78/C94/C95 + U9 pin 5/8 — IMU LDO output rail, separate net from main +3V3. |
| GND | 5 | U9 pins 6/7 + J9 pins 3/5/9 + C94.2 — small set, U9 IMU + SWD ground stitch issue. |

### Signal-net residuals (12 items) — actual unrouted net legs

| Net | Endpoints | Direction |
|---|---|---|
| IMU3_CS | U1.1 (33.33, 29.00) F.Cu → U9.12 (41.50, 58.92) F.Cu | MCU W → island ~30mm diag |
| IMU3_INT1 | U1.41 (42.50, 42.67) F.Cu → U9.4 (43.17, 57.25) F.Cu | MCU S → island ~15mm |
| MOT1 | J11.1 (10.00, 3.00) F.Cu → U1.34 (39.00, 42.67) F.Cu | N-edge ESC → MCU S ~46mm |
| MOT2 | J12.1 (15.00, 3.00) F.Cu → U1.35 (39.50, 42.67) F.Cu | N-edge ESC → MCU S ~45mm |
| SPI1_MISO | U3.9 (34.46, 58.25) F.Cu → U1.30 (37.00, 42.67) F.Cu | Island → MCU S ~16mm |
| SPI1_MOSI | U3.12 (33.50, 56.80) F.Cu → U1.31 (37.50, 42.67) F.Cu | Island → MCU S ~15mm |
| SPI1_SCK | U3.11 (34.46, 57.25) F.Cu → U1.29 (36.50, 42.67) F.Cu | Island → MCU S ~15mm |
| SPI3_MISO | U1.90 (40.00, 27.32) F.Cu → U9.1 (43.17, 58.75) F.Cu | MCU N → island ~32mm |
| SPI3_MOSI | U1.91 (39.50, 27.32) F.Cu → U9.14 (42.50, 58.92) F.Cu | MCU N → island ~32mm |
| SPI3_SCK | U1.89 (40.50, 27.32) F.Cu → U9.13 (42.00, 58.92) F.Cu | MCU N → island ~32mm |
| SWCLK | J9.4 (42.95, 61.27) B.Cu → U1.76 (47.00, 27.32) F.Cu | SWD → MCU N ~35mm + via |
| SWDIO | J9.2 (42.95, 62.54) B.Cu → U1.72 (48.67, 30.50) F.Cu | SWD → MCU E ~33mm + via |

## What the 12 signal residuals need

All 12 require routing through the dense MCU-south region where they
intersect existing 988-track routing. They are exactly what FR3
plateau'd on. Interactive push-and-shove routing (KiCad GUI router or
A* with proper plane-keepout modeling) is the natural close-out.

Notable clusters:
- **SPI3 (3 nets)** all from MCU N pins to U9 island — diagonal
  ~32mm traverses through congested center. THIS is the bottleneck.
- **SPI1 (3 nets)** from U3 island to MCU S — shorter ~15mm but
  area is dense.
- **MOT1/2** long N-edge to MCU S — pin-mux locked.
- **SWCLK/SWDIO** SWD (B.Cu) to MCU — long traverse.

## What the 55 plane-stitch items need

Mostly +3V3 pads on F.Cu/B.Cu requiring vias to L3 +3V3 plane.
Earlier `run_stitch_plane_nets.py` placed 170 stitches successfully
but failed on 21 in dense pad regions. Those + the rest of the
+3V3 pads listed in HANDOFF_residuals.json need:
- Spiral-search via placement (current radius 4mm; may need 6-8mm)
- Or trace-to-decap-with-via for MCU power pins (master step A approach)
- DRC-clean

## Files / artifacts

- `novapcb-layout-v1.1.kicad_pcb` — at FR3 88.8% baseline (commit 14a2d46)
- `novapcb-layout-v1.1.ses` — FR3 Specctra SES (76 KB)
- `HANDOFF_residuals.json` — machine-readable residual list with
  endpoint coords + layers
- `render_handoff_top.png` + `render_handoff_bot.png` — current top + bottom
  visuals at the FR3 baseline

## Tools available (built during this effort)

- `run_pristine_2layer.py` — Freerouting 2-signal wrapper
- `run_3layer.py` — Freerouting 3-signal wrapper (this checkpoint's run)
- `run_4layer.py` — Freerouting 4-signal wrapper (tested, WORSE result)
- `astar_router.py` — 2-layer A* (depreciated, plane-keepout gap)
- `astar_3layer.py` — 3-layer A* (depreciated, same gap)
- `astar_via_cleanup.py` — A* + path-level layer-excursion collapse
  (this is the post-processor that got 500→33 DRC but introduced
  endpoint gaps)
- `fix_endpoints.py` — Endpoint-gap fixer (closes A* cell-grid vs
  pad-center mismatches; +9 closures in last run)
- `fix_mcu_power.py` — MCU power pin → decap connection trace adder
- `nudge_shorts.py` — Via-nudge for AVC shorts (broken: doesn't
  reconnect routes properly when via moves)
- `run_stitch_plane_nets.py` — Plane stitch via placer (170/191
  success rate, fails dense regions)
- `place_smalls_fresh.py` / `greedy_placer.py` — re-placement (used
  for v13 placement)
- `cleanup_placement.py` — slot polygon + outer outline management
- All `batch_B*.json` / `batch_*.json` — net groupings used during
  iteration

Standing by for Sai's path decision.
