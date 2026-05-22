# novapcb-stepwise — incremental-integration board (v1.1+)

The single `.kicad_pcb` that grows subsystem by subsystem per
`docs/PLACEMENT_ROUTING_GATES.md` §0 and the integration order in
`docs/SUBSYSTEM_CONTRACTS.md` §4.

## Status

- **Step 1 (C — MCU_CORE):** placed + gates 1/3/4/12 GREEN.
- **Step 2 (E — BARO_I2C):** placed (U4, U7, C51, C52, C71, C72, R11, R12).
- Steps 3-10: future PRs (one per subsystem / integration step).

## How to regenerate

```bash
# Step 1 — place C only
python3 step1_place_C.py
# Step 2 — add E (BARO_I2C) on top of the Step-1 board
python3 step2_place_E.py

# Run the gates (each returns 0 = green, 1 = fail)
python3 gate1_bbox_overlap.py    # bbox-overlap + self-test
python3 gate3_uniqueness.py      # netlist ↔ pcb match
python3 gate4_artifact_trust.py  # grep-the-artifact audit
python3 gate12_thermal_U1.py     # per-subsystem thermal (U1 T_j)

# Gate 2 — 3D render (visual eyeball for master audit)
kicad-cli pcb render --side top    --output render_top.png novapcb-stepwise.kicad_pcb
kicad-cli pcb render --side bottom --output render_bot.png novapcb-stepwise.kicad_pcb
```

## Files

| File | Purpose |
|---|---|
| `novapcb-stepwise.kicad_pcb` | the growing board (committed) |
| `fp-lib-table`               | absolute-path footprint libs (KiCad 9 KIPRJMOD workaround) |
| `step1_place_C.py`           | Step-1 placer: U1, Y1, FB1, 16 caps, 3 resistors |
| `step2_place_E.py`           | Step-2 placer: U4 (DPS310), U7 (BMP388), C51/52/71/72, R11/12 |
| `gate1_bbox_overlap.py`      | Gate 1 verifier (with deliberate-bad self-test) |
| `gate3_uniqueness.py`        | Gate 3: every netlist refdes in .kicad_pcb exactly once |
| `gate4_artifact_trust.py`    | Gate 4: parse the actual .kicad_pcb, don't trust placer's "OK" |
| `gate12_thermal_U1.py`       | Gate 12: U1 worst-case T_j (analytical + Elmer FE attempt) |
| `render_top.png` / `render_bot.png` | Gate 2: 3D renders (visual audit) |

## Step 1 — C (MCU_CORE) placement summary

Per `docs/SUBSYSTEM_CONTRACTS.md §C`:

- **U1** STM32H743VIT6 LQFP-100 at **(45, 35)** mm — geometric center of board.
- **Y1** 8 MHz HSE crystal at W edge, vertically between U1 pins 12 (PH0)
  and 13 (PH1). Rotated 90° so the 3.2 mm dim is in Y.
- **C24, C25** xtal load caps (18 pF) flanking Y1, further W.
- **C11..C15** per-VDD-pin 100 nF decap (5 caps, one per VDD pin: 11 W, 27 S,
  50 S, 75 E, 100 N).
- **C17** (VCAP1, 2.2 µF) S band near pin 48.
- **C18** (VCAP2, 2.2 µF) E band near pin 73.
- **C19, C20, FB1** VDDA chain (100 nF + 1 µF + ferrite) W band near pin 21.
- **C21, C22, R1** VREF+ chain (100 nF + 1 µF + 0R tie) W band near pin 20.
- **C23, R2** VBAT (100 nF + 0R tie to +3V3) W band near pin 6.
- **C26** NRST decap (100 nF) W band near pin 14.
- **R3** BOOT0 pulldown (10k) N band near pin 94.
- **C16** bulk decoupling (4.7 µF 0805) N band, +X-offset from R3.

All 22 C-subsystem footprints + U1 + 4 corner mounting holes are on-board.
The remaining 103 footprints (subsystems A, B, D, E, F, G, H) are PARKED at
X ≥ 110 mm — they will be positioned by future Step-N PRs.

## Sub-phase 1.0 — workflow workaround

KiCad 9's `pcbnew.FootprintLoad` returns `None` for `kinet2pcb`, so we
**clone-and-strip** the v1.1 source `.kicad_pcb` (which has all 125
SKiDL-generated footprints already loaded) via an S-expression rewrite
that drops tracks/vias/zones/Edge.Cuts shapes/original mounting holes.
`pcbnew` then handles repositioning. See `step1_place_C.py:sexp_strip()`.

## Gate-7 note

LQFP-100 (`Package_QFP:LQFP-100_14x14mm_P0.5mm`) is a gull-wing
package — **no exposed thermal pad** — so Gate 7 thermal-vias-under-U1
is N/A. The MCU dissipates ≤500 mW through its 100 leads to the planes
(planes added in the cross-subsystem routing PR).

## Gate-12 note

Two-track T_j evidence per `docs/PLACEMENT_ROUTING_GATES.md` §Gate 13:

- **Analytical (with planes, JESD51-7):** T_j worst = 47.5 °C at P=0.5W,
  T_amb=25°C, Theta_ja=45°C/W (ST DS12110 §6.1). Margin to 105°C
  spec = **57.5 °C**. The cross-subsystem +3V3 + GND planes (added in
  the cross-subsystem routing PR) deliver this regime.
- **Elmer 3D FE (bare FR4, no planes):** T_j ≈ 103 °C. **Marginal**
  (1.8°C from spec) but expected — bare FR4 has no copper spreader,
  so this is a worst-case lower bound for the placement before planes
  land. As soon as the +3V3 / GND planes are present, T_j drops toward
  the analytical 47.5°C.

**3D body-source convention lesson (caught 2026-05-22):** Elmer's
`HeatSolver` expects `Heat Source` in **W/kg** (per unit MASS), not
W/m³. Solver internally multiplies by `Density`. Setting raw W/m³
over-sources by the density factor (~1850× for FR4). Validated against
1D thin-slab analytical to **1.00× match** — see
`sims/validation/VALIDATION_RESULTS.md` §3.

Convergence note: medium→fine mesh delta is 5.63% (just above the <5%
bar). The next iteration of `gate12_thermal_U1.py` should push to a
finer mesh or document why 5.6% is acceptable for a "bare-FR4
upper bound that won't be the ship-state anyway."
