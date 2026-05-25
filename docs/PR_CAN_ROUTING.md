# PR — CAN bus routing (task #45)

> Branch: `hw/can-routing-v2`. Routes the FDCAN1 subsystem (transceiver U14,
> ESD U15, split termination R45/R46, connector J20) on the `novapcb-stepwise`
> board. 5 of 6 CAN nets routed; the 6th (software silent-mode GPIO) resolved
> by hard-tie to GND for v1.

## 1. What changed

**Placement (passives repositioned to unblock routing — Rule 20):**
- **FB2** (+3V3 → +3V3_IMU_PRE filter ferrite) moved (49.25,25.7) → (52.0,25.0).
  It sat directly north of CAN1_RX (PD0, FDCAN1-peripheral-locked) and blocked
  the only N-edge exit. +3V3 leg = plane-via tap; +3V3_IMU_PRE leg re-routed to
  rejoin the existing X=56.02 vertical to U13.
- **R45/R46** (split termination) flipped 180° — TERM_MID now on the INNER
  pads (short clean link), CANH/CANL on the outer. Root-cause fix for the
  TERM_MID-link-crosses-the-pads tangle.
- **U15** (PESD2CAN ESD) repositioned (96,27) → (95,17) into the U14↔J20 corridor.

**Schematic (SKiDL `can_3j.py` + `hwdef.dat`):**
- `GPIO_CAN1_SILENT` net **removed**. TJA1051 pin 8 (S) **hard-tied to GND =
  NORMAL MODE** for v1. `hwdef.dat` PD15 line removed → PD15 reverts to free GPIO.
- (Intermediate step, now reverted: SILENT was remapped PD3→PD15 to dodge the
  N-edge block before we determined PD15→U14.8 is unroutable — see §4.)
- Netlist regenerated; ERC = 0 errors.

**Routing (5 CAN nets):**
- **CANH / CANL / CAN_TERM_MID** — routed by **Freerouting** (scoped to the CAN
  nets, F.Cu+B.Cu only), all clean F.Cu. This is the part that resisted ~6
  manual topologies; the canvas-aware router solved the dense NE-corner bus in 13s.
- **CAN1_TX / CAN1_RX** — routed **manually** (Freerouting would not place the
  B.Cu hops these need). Y=19 / Y=16 lanes with B.Cu hops over the
  BATT2_CURRENT_SENS F.Cu wall (Y=21.2); RX enters U14.4 from the SE via a B.Cu
  diagonal under the bus.

## 2. Why (key decisions)

- **Freerouting for the bus**: 5-net scope (not the full-board scope that OOM'd
  earlier). Two enabling fixes to the scoped-DSN export: (a) keep only the CAN
  nets in `(network)` so it doesn't try to route the board's other unrouted
  nets; (b) strip the inner-layer shapes from the via padstack so a valid F-B
  via exists in the 2-layer DSN.
- **SILENT → GND (v1)**: ArduPilot DroneCAN does not use CAN silent/listen-only
  mode in flight; S=LOW (normal mode) is the industry-default hard-tie for CAN
  nodes. Removing the one unroutable net keeps the bus fully functional.
  Software silent-control deferred to v2 (analogous to the MOT7/8 v2 deferral).

## 3. Verification (5-gate)

| Gate | Result |
|---|---|
| DRC | **18 errors = baseline** (no new errors; ≤ baseline+3) |
| Unconnected | 264 → **255** (−9: CANH 3 + CANL 3 + TERM 1 + RX 1 + TX 1; SILENT resolved) |
| 0 CAN "Missing connection" | **PASS** — all 5 nets fully routed (verified per-net pad set) |
| STACKUP-SPEC-MATCH | **PASS** (4 plane pairs match DECISIONS §8) |
| MIRROR_PAIRS / DECOUPLING | **PASS** (layout-compliance audit clean) |
| Per-net cluster walk | **PASS** — every signal-carrying segment (lanes + B.Cu
  diagonals) overlies its GND plane (F.Cu→In1.Cu, B.Cu→In4.Cu); the only sampling
  voids are the physically-required antipads around the nets' OWN through-vias
  (immaterial for ≤1 Mbps CAN). |
| ERC (netlist) | **PASS** — 0 errors; `GPIO_CAN1_SILENT` net gone, U14.8 on GND |
| +3V3_IMU rail re-verify (FB2 move) | **PASS** — In1 GND continuous under new
  leg, In3 +3V3 plane taps the new FB2.1 via, U13 feed intact |

## 4. Prevention / lessons

**Rule 18 hit THREE more times** (refinement added to MASTER_PROCESS_RULES.md):
"component pads" means every pad-class/through-class obstacle, enumerated by
footprint reference —
- **ferrite bead** (FB2 looked like "a +3V3 via" in a track-only survey);
- **GND-stitch via grid** (a "clear lane" by track count plowed a 4-via row at Y=20);
- **connector-shield PTH** (J1 USB-C shield pads at Y=34.32 block ALL layers);
- **1.6 mm-long LQFP-100 pads** (no via fits in a 0.86 mm pad-to-track window).

**Rule 20 formalized** — *move the passive before moving the trace*: FB2, R45/R46,
U15, R11/R12 each unblocked a problem that resisted trace-level fixes.

**SILENT unroutability — root cause documented**: PD15→U14.8 is impossible
because the MCU-east region is saturated on BOTH layers at Y≈30-31 — the USB
diff pair (F.Cu) and SPI3_SCK + IMU2_GYR_INT3 (B.Cu, fanning to the IMU island)
overlap there, leaving no crossing point on either layer for any free E-edge
pin. Not an autorouter limitation; a true 2-layer-saturation wall → v1 GND-tie.

**v2 reference**: stuff an R-NC pulldown on U14.8→GND with an optional MCU
pull-high stuffing option to restore software silent-mode control.

**Routing-tool note**: pcbnew SWIG iterators (`GetFootprints()`) are invalidated
by a preceding `brd.Remove()` in the same process — resolve net objects BEFORE
removing tracks, and run multi-stage board edits as separate subprocess phases.
