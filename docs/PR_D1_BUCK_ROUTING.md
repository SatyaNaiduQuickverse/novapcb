# PR — D1 buck routing: U2_FB + U2_SW (Phase 4d-redux D1, unblocks +3V3)

> Branch `hw/d1-buck-routing` off `sch/option-b-buck`. First step of the
> power-tree routing effort opened by the Rule-23 per-net audit
> (`docs/POWER_TREE_DEFECT_SURVEY.md`). Routes the two buck-specific nets that
> were placed but never connected — **without these there is no +3V3, and the
> board does not power up.**

## 1. Why (root cause)

The Rule-23 per-net unconnected audit found the TPS62177 buck regulator U2 had
its two defining nets **completely unrouted** (0 track / 0 via each):

| Net | pads | function |
|---|---|---|
| U2_FB | U2.5, R47.2, R48.1 | feedback divider tap → buck FB pin (sets Vout; buck won't regulate without it) |
| U2_SW | U2.9, L1.1 | switch node → inductor L1 (no output path without it) |

**Root cause:** the Option-B buck swap (PR #95 SKiDL / #96 layout) replaced the
original +3V3 LDO with the TPS62177 buck and placed U2/R47/R48/L1, but the
buck-specific nets (FB divider + SW→L1) were never routed — the earlier #85
B-power routing predates the LDO→buck change, so nothing drew these. Hidden in
the 213-unconnected top-level DRC number until the per-net audit broke it down.

## 2. Changes (board-only — `novapcb-stepwise.kicad_pcb`, +48 lines)

**U2_FB** (4 segments, 0.20 mm, F.Cu) — the dense corner (U2.11 GND thermal pad
boxes U2.5 to the east; R47.1 +3V3 sits between U2.5 and R48.1; a +3V3 via at
(22.50, 28.35) blocks the SW approach to R48.1). Computed-clear topology:
- `U2.5 (22.562,26.000) → (22.562,26.600)` — south, staying west of U2.11
- `→ (24.510,26.600)` — east, 0.425 mm south of U2.11's south edge
- `→ R47.2 (24.510,27.500)` — drop into R47.2 **from the north** (avoids
  crossing R47.1 +3V3, which shares R47.2's row to the west)
- `R47.2 → R48.1 (23.490,28.500)` — diagonal across the FB tap; rounded rrect
  corners on R47.1/R48.2 keep it ≥0.2 mm clear

**U2_SW** (2 segments, 0.30 mm, F.Cu) — U2.9 is sandwiched between U2.10 (+3V3,
0.5 mm N) and U2.8 (+5V, 0.5 mm S) on 0.5 mm pitch; a wide trace can't clear
both. Routed to exit east *level with U2.9* before turning to the inductor:
- `U2.9 (25.438,24.500) → (26.200,24.500)` — east at Y24.5 (0.225 mm clear of
  both U2.10 and U2.8, past their east edge)
- `→ L1.1 (27.815,25.000)` — diagonal into the large inductor pad

A first attempt routing U2.5→R48.1 directly grazed R47.1 (+3V3) at 0.35 mm, and
a wide SW trace grazed U2.10 (+3V3) at 0.15 mm — both fixed by the geometry
above (verified against exact pad sizes: U2 pads 0.825×0.250 rrect, R47/R48
0.540×0.640 rrect, L1.1 0.980×3.400).

## 3. Verification (master's 6-gate set)

- **Per-net audit** (`scripts/audit_unconnected_per_net.py`): U2_FB and U2_SW
  **both drop out of real-latent** (each 0 unconnected). Real-latent total
  64 → 61 (the −3 are D1's items; remaining 61 are D2–D6, dispatched next).
- **DRC**: **12 = baseline**, 0 non-baseline / 0 net-new (all 12 are the
  `.kicad_dru`-covered courtyard/drill/via exceptions). GUI-authoritative.
- **`waf copter` build-verify**: **PASS** — `arducopter.bin` for novapcb-v1,
  184116 B free flash. (hwdef.dat byte-identical to base — board-only change
  cannot affect firmware; build input unchanged, re-link confirms.)
- **Untouched subsystems**: per-net track-count diff vs base shows **only**
  U2_FB (0→4) and U2_SW (0→2) changed; every other net (USB, SPI1/2/3, CAN,
  microSD/SDMMC1, MOT1–6, CRSF, +5V_BEC plane, GND/+3V3 planes) byte-identical.
- **Schematic/ERC**: no SKiDL/netlist change on this branch (`git diff` =
  `.kicad_pcb` only); the FB/SW nets already exist in the schematic from the
  Option-B swap, so schematic ERC state is unchanged from baseline.

## 4. Scope

Closes **Phase 4d-redux D1**. Unblocks the +3V3 supply path. Next (master
sequences): D2 (+5V input distribution), D3 (eFuse), D4 (MCU core
VCAP/VDDA/VREF/VBAT/BOOT0), D6 (USB-C CC + misc), D5 (+3V3_IMU dense pocket).
Sim 1 thermal + Sim 5 PDN re-gate after D4 closes the MCU core (per the survey
doc §3 — both assumed power that wasn't routed).
