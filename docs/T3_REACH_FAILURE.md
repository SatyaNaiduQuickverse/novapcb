# T3 PGOOD power-rail LEDs — v1 REACH FAILURE (2026-05-30)

> Sai-directed SOTA T3 (5× LED + 5× series-R for +5V/+3V3/+3V3_IMU/+5V_BEC/EFUSE_PGOOD indicator LEDs). Placement at Y=10 strip cascades +17 DRC. Per cap-watch (scope-creep 4/4): FULL REVERT.

## Attempt

Located 31mm-wide clear-of-footprints strip at Y=10, X=37-67 (between U11/U12 ORFETs). Placed 5 LEDs + 5 series-R (10 × 0402 components) at (40-62, 10) F.Cu.

## Cascade

DRC delta: 29 → 46 (+17): 7 courtyards_overlap + 6 mask_bridge + 5 clearance + 3 shorts.

The `has_copper_near` footprint+via scan missed:
- ORFET U11/U12 courtyards (extended courtyards include silk + assembly margin)
- B.Cu zone copper fills under Y=10 area
- +5V_BEC In2.Cu plane via clearances

10 components in a single dense N-strip overwhelmed the available clearance.

## Per cap-watch

Master 2026-05-30: "T14/T16/T17 that adds another scope-creep exception BREACHES the cap." T3 attempt added 5 clearance violations alone = cap-breach. FULL REVERT.

## Operational mitigation

v1 ships without indicator LEDs:
- Power-rail debug via TP3 (+3V3) and TP5 (GND) probe pads (T13 plane-net probes work)
- Or scope-probe U2.OUT (+5V), U13.OUT (+3V3_IMU), U6.PGOOD pins directly

Visible status: USB-CDC console output via `mavproxy.py --master /dev/serial/by-id/usb-ArduPilot_*` covers all status info LEDs would provide.

## v2 path

Pre-allocate LED + R row at Phase 4a in a dedicated N-edge strip BEFORE ORFETs/eFuse fill the area. ~20×3mm reservation needed.

## State after revert

- DRC severity-error: **29** (unchanged from pre-T3)
- audit_unconnected_per_net: PASS, **0 real-latent**
- Scope-creep: **4/4** (no T3 additions)
