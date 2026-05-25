# R4 Routing Handoff — Final State (2026-05-22)

## Status: HOLD for Sai's interactive close-out decision

Per master 2026-05-22: numbers bouncing without clean convergence on
the residuals. Stopping headless effort. Plane-stitch pass completed
on clean FR3 baseline; signal residuals UNTOUCHED.

## Current state (commit `94a752f` pushed)

- **988 + ~190 vias** = ~1180 total tracks/vias (FR3 base + stitching)
- **30 unconnected items**:
  - 12 signal-net residuals (UNTOUCHED — per directive)
  - ~9 +3V3_IMU items (routing job, NOT stitch — see breakdown)
  - ~4-5 MCU power pins (cannot stitch in 0.5mm pitch)
  - ~4 signal-pad residuals appearing as unconnected (FR3 partial routes)
- **59 DRC violations** (stitch-via clashes with existing routes):
  - 11 tracks_crossing
  - 8 solder_mask_bridge (front)
  - 3+2+2+2+2+1 clearance (various ~0.04-0.20mm gaps)
  - 5 shorting_items (VCAP1↔GND, VBAT↔GND, GND↔ORING_B_GATE, 2 nameless)
  - 3 copper_edge_clearance (marginal 0.21-0.23mm)

## Recoverable bases

Two checkpoints depending on close-out approach:

```bash
# Option 1: clean FR3 baseline (no stitch tangles, 67 unconnected)
git checkout 14a2d46 -- hardware/kicad/novapcb-layout-v1.1/novapcb-layout-v1.1.kicad_pcb
# 988 tracks + 113 vias, 0 DRC, 67 unconnected

# Option 2: current state with stitches (30 unconnected, 59 DRC clashes)
git checkout 94a752f -- hardware/kicad/novapcb-layout-v1.1/novapcb-layout-v1.1.kicad_pcb
```

## Residual breakdown — current state

### Class 1: 12 signal-net residuals (HELD — untouched)

| Net | Endpoints | Traverse |
|---|---|---|
| IMU3_CS | U1.1 (33.33, 29.00) F.Cu ↔ U9.12 (41.50, 58.92) F.Cu | MCU W → island ~30mm |
| IMU3_INT1 | U1.41 (42.50, 42.67) F.Cu ↔ U9.4 (43.17, 57.25) F.Cu | MCU S → island ~15mm |
| MOT1 | J11.1 (10.00, 3.00) F.Cu ↔ U1.34 (39.00, 42.67) F.Cu | N edge → MCU S ~46mm |
| MOT2 | J12.1 (15.00, 3.00) F.Cu ↔ U1.35 (39.50, 42.67) F.Cu | N edge → MCU S ~45mm |
| SPI1_MISO | U3.9 (34.46, 58.25) F.Cu ↔ U1.30 (37.00, 42.67) F.Cu | Island → MCU S ~16mm |
| SPI1_MOSI | U3.12 (33.50, 56.80) F.Cu ↔ U1.31 (37.50, 42.67) F.Cu | Island → MCU S ~15mm |
| SPI1_SCK | U3.11 (34.46, 57.25) F.Cu ↔ U1.29 (36.50, 42.67) F.Cu | Island → MCU S ~15mm |
| SPI3_MISO | U1.90 (40.00, 27.32) F.Cu ↔ U9.1 (43.17, 58.75) F.Cu | MCU N → island ~32mm |
| SPI3_MOSI | U1.91 (39.50, 27.32) F.Cu ↔ U9.14 (42.50, 58.92) F.Cu | MCU N → island ~32mm |
| SPI3_SCK | U1.89 (40.50, 27.32) F.Cu ↔ U9.13 (42.00, 58.92) F.Cu | MCU N → island ~32mm |
| SWCLK | J9.4 (42.95, 61.27) B.Cu ↔ U1.76 (47.00, 27.32) F.Cu | SWD → MCU N ~35mm + via |
| SWDIO | J9.2 (42.95, 62.54) B.Cu ↔ U1.72 (48.67, 30.50) F.Cu | SWD → MCU E ~33mm + via |

### Class 2: +3V3_IMU routing (9 items — short TRACE job from FB2 output)

+3V3_IMU is a SEPARATE net (post-FB2 ferrite). Not a plane-stitch issue.
The FB2 (65, 52) output → U13 LDO → +3V3_IMU consumers (U9 IMU at
~42-43 X, ~57-59 Y) was never traced.

| Pad | Position | What it needs |
|---|---|---|
| C78.1 | (42.52, 55.58) F.Cu | Trace from FB2 output |
| C94.1 | (39.51, 55.57) F.Cu | Trace from FB2 output |
| C95.1 | (42.52, 54.33) F.Cu | Trace from FB2 output |
| U9.5 | (42.50, 57.08) F.Cu | Trace from FB2 output |
| U9.8 | (40.83, 57.25) F.Cu | Trace from FB2 output |
| (+ 4 more pad-pair items between these) |

### Class 3: MCU power pins (~4-5 items — cannot stitch, dense 0.5mm pitch)

| Pad | Net | Position | Why failed |
|---|---|---|---|
| U1.11 | +3V3 | (33.33, 34.00) F.Cu | Adjacent pins too close for via at pad+offset |
| U1.50 | +3V3 | (47.00, 42.67) F.Cu | Same |
| U1.74 | GND | (48.67, 29.50) F.Cu | Same |
| U1.75 | +3V3 | (48.67, 29.00) F.Cu | Same |

These MAY route through their decoupling caps — need manual placement.

### Class 4: Signal pads appearing unconnected (partial FR3 routes)

These pads on U1 don't have a complete route to their destination:
- U1.86 = GPS1_TX (FR3 routed partially)
- U1.88 = BUZZER (FR3 routed partially)
- A few others

## 59 DRC characterization

| Category | Count | Notes |
|---|---|---|
| tracks_crossing | 11 | Stitch-vias placed on existing routes — net pairs |
| solder_mask_bridge (front) | 8 | Stitch-via apertures merging with adjacent pads |
| clearance violations (~0.04-0.20mm) | 13 | Stitch-via too close to other-net tracks |
| shorting_items | 5 | VCAP1↔GND (U1.48 area), VBAT↔GND (W block), GND↔ORING_B_GATE (Q4 area), 2 nameless (U1 pin 97 area) |
| copper_edge_clearance | 3 | 2 marginal (0.21-0.23mm), 1 specific (J9 SWD pad spillover) |
| starved_thermal | 0 | (cleared) |
| invalid_outline | 0 | ✓ |

## What close-out work needs

### Mechanical (small-scope, post-Sai):
1. **+3V3_IMU traces** (~10mm of routes): FB2.2 → C94 → U9.8/5 → C78 → C95
   path on F.Cu. Single-layer, short. ~5min in KiCad GUI.
2. **Clean 59 DRC** stitch clashes: each stitch via that landed on an
   existing track — slide it 0.5-1mm to clear. ~5-10 nudges.
3. **MCU power pins** (U1.11/50/74/75): connect each via short trace to
   nearest already-stitched +3V3/GND cap. Manual placement; ~3-5min.

### Strategic (the real work):
**12 signal-net residuals** through MCU south. The 3-signal stackup has
the bandwidth (FR3 88.8% proved it); the remaining 12 are concentrated
diagonal MCU↔island traverses. Push-and-shove interactive routing in
KiCad GUI is the natural close-out.

## Files / artifacts

- `novapcb-layout-v1.1.kicad_pcb` — current state at commit `94a752f`
- `novapcb-layout-v1.1.ses` — FR3 SES (76 KB)
- `HANDOFF_residuals.json` — machine-readable residual list (refreshed)
- `render_handoff_top.png` + `render_handoff_bot.png` — current visuals

## Tool inventory (built during this effort)

| Script | What it does | Status |
|---|---|---|
| `run_pristine_2layer.py` | Freerouting 2-signal wrapper | Works |
| `run_3layer.py` | Freerouting 3-signal wrapper | **Used for FR3 88.8%** |
| `run_4layer.py` | Freerouting 4-signal wrapper | Tested, WORSE result |
| `astar_router.py` | 2-layer A* | Deprecated (plane gap) |
| `astar_3layer.py` | 3-layer A* | Routes topologically; plane gap |
| `astar_via_cleanup.py` | A* + path-level layer-excursion collapse | 500→33 DRC but endpoint gaps |
| `fix_endpoints.py` | Cell-grid vs pad-center gap closer | Limited effect |
| `fix_mcu_power.py` | MCU pin → decap trace | Added 8-15 traces |
| `nudge_shorts.py` | Via-nudge for AVC shorts | **BROKEN** (revert logic missing) |
| `run_stitch_plane_nets.py` | Plane stitch via placer | 170-176 success, 15-21 dense fail |
| `replace_v2.py` | Big-block re-placement | Used for v13 placement |
| `cleanup_placement.py` | Slot polygon + outer outline | Used for v13 |
| `greedy_placer.py` | Per-block fresh small-part placement | Used for v13 |

## Standing by

PCB at commit `94a752f`. Sai's decision pending on:
- 12 signal residuals close-out path (KiCad GUI push-and-shove?)
- Mechanical cleanup (+3V3_IMU traces, 5 MCU pins, 59 DRC nudges)
