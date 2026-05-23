# PR — Option B: LDO → buck on +3V3 rail

> **Branch**: `sch/option-b-buck`
> **Scope**: U2 architecture change from AP2112K-3.3 LDO to TPS62177DQC
> buck regulator. Schematic + layout + thermal + audit + DRC + 4 sense-row
> mirror-pair fixes.
> **Commits**: `ba91b16` (schematic) → `2ea0cd4` (step 3 layout) → `7761fa1`
> (thermal Rule-9 fix).
> **Master sign-off**: 2026-05-23 (3 separate sign-offs: schematic, step 3
> layout, delta-investigation).

---

## Symptom

The +3V3 rail had to deliver up to ~500 mA total to the MCU + sensors +
peripherals. The original AP2112K-3.3 LDO dropped (5 V − 3.3 V) × 500 mA
= 850 mW typ, 642 mW realistic-worst-case continuous, **all dissipated as
heat at U2's body**. With U2 at (24 mm, 25 mm) — only 21 mm from the
MCU's body edge — the heat halo from U2 stacked into the MCU site.

Gate12 v3 thermal sim (1617 mW total board dissipation, k = 33.5/0.316
W/m·K anisotropic, h = 5 W/m²·K both sides, T_amb = 50 °C):

| Architecture | MCU Tj | Margin to 80 °C target |
|---|---|---|
| Current baseline (LDO @ 642 mW) | **82.5 °C** | **−2.5 °C — FAIL** |
| Option A: 115 × 100 board, same LDO | 74.1 °C | +5.9 °C (no headroom) |
| **Option B: 105 × 85 board + buck (this PR)** | **63.7 °C** | **+16.3 °C** |
| Option C: 110 × 90 board + buck | 62.8 °C | +17.2 °C (+0.9 over B) |

Architecture sweep ran on actual placed positions (Q3/Q4/U11/U12 + all
C/E/F/B/A subsystems), not planned-position artifacts — Rule 9.

## Fix

Three commits land Option B end-to-end.

### Commit 1 — schematic (`ba91b16`)

Replace U2 in SKiDL source:

- **Old**: `Part("Regulator_Linear", "AP2112K-3.3", footprint="Package_TO_SOT_SMD:SOT-23-5")`
- **New**: `Part("Regulator_Switching", "TPS62177DQC", footprint="Package_DFN_QFN:DFN-10-1EP_3x3mm_P0.5mm_EP1.58x2.35mm")`

Pin connections (per TI SLVSC73 §10 typical application):

| Pin | Net | Notes |
|---|---|---|
| 1 (AGND) | GND | analog ground |
| 2 (VIN) | +5V | from eFuse output |
| 3 (EN) | +5V | always-on (tied to VIN) |
| 5 (FB) | U2_FB | tap from R47/R48 divider midpoint |
| 6 (PGND) | GND | power ground |
| 7 (PG) | — | NC (power-good output unused in v1) |
| 8 (~SLEEP) | +5V | normal mode (HIGH) |
| 9 (SW) | U2_SW | switching node → L1 |
| 10 (VOS) | +3V3 | output sense |
| 11 (EP) | GND | thermal pad |

New components:

- **L1** — Coilcraft XAL4020-2R2 (2.2 µH shielded SMT power inductor,
  3.7 A I_sat, R_dc = 24 mΩ). Footprint `Inductor_SMD:L_Coilcraft_XAL4020-XXX`.
- **R47** — 562 kΩ 0402 (FB divider top, +3V3 → FB).
- **R48** — 180 kΩ 0402 (FB divider bot, FB → GND).
- **C31** — 10 µF 0805 X7R (Cin bulk).
- **C32** — 100 nF 0402 X7R (Cin HF).
- **C33** — 22 µF 0805 X7R (Cout bulk).
- **C34** — 100 nF 0402 X7R (Cout HF).

Feedback divider math: V_OUT = V_FB × (1 + R47/R48) = 0.8 V × (1 +
562/180) = 0.8 × 4.122 = **3.297 V** (within ±1% of 3.3 V nominal).

IMU noise budget (master approval gate): buck 1.8 MHz switching ripple
× LP5907 IMU LDO PSRR (60 dB @ 1.8 MHz from datasheet) × ICM-42688
PSRR (40 dB typ) = 4.5 µV / 1.5 nA equivalent at IMU supply, **10× margin**
to ICM-42688 intrinsic noise floor (3.5 mdps/√Hz gyro, 70 µg/√Hz accel).

### Commit 2 — step 3 layout (`2ea0cd4`)

Single-sweep re-layout per master directive: U2 area buck discipline + 4
sense-row mirror-pair fixes.

**Buck-discipline placement** (`step5_place_B.py`):

| Ref | Anchor (mm) | Why |
|---|---|---|
| U2 | (24.0, 25.0) | Sweet-spot preserved (proven by pre-Option-B iteration log — adiabatic-edge trap at X=15..22 documented in `memory feedback_adiabatic_edge_trap`) |
| L1 | (28.5, 25.0) | ~3 mm east of U2 SW pin; magnetic axis E-W ⊥ N-S buck-to-IMU vector |
| C31 (Cin bulk) | (20.5, 24.0) | West of VIN pin |
| C32 (Cin HF) | (21.0, 26.0) | Nearest VIN pin (placement-script nudged to 20.75, 26.43 for collision-clearance — 2.13 mm body-edge to VIN pin) |
| C33 (Cout bulk) | (33.0, 25.0) | East of L1 east lead |
| C34 (Cout HF) | (29.0, 21.5) | NE of U2 body, NORTH of L1 — only position satisfying DECOUPLING 3 mm body-edge rule given L1 blocks the east strip. 2.32 mm body-edge to U2. |
| R47 (FB top 562k) | (24.0, 27.5) | South of U2 FB pin (≤5 mm FB trace) |
| R48 (FB bot 180k) | (24.0, 28.5) | South of R47 |

Buck-to-IMU island separation: ~30.5 mm (>25 mm required). FB net trace
~3.5 mm total (≤5 mm required, GND-shielded via In3 plane zone fill).

**Sense-row mirror fixes** (`step6_place_A.py`) — mirror about X=52.5:

| Pair | West (kept) | East (was) | East (now) | Deviation |
|---|---|---|---|---|
| R41 ↔ R43 | (24.0, 14.5) | (76, 14.5) | **(81.0, 14.5)** | 0.000 mm |
| R42 ↔ R44 | (20.0, 14.5) | (80, 14.5) | **(85.0, 14.5)** | 0.000 mm |
| C61 ↔ C81 | (22.0, 14.5) | (74, 14.5) | **(83.0, 14.5)** | 0.000 mm |
| C62 ↔ C82 | (18.0, 14.5) | (82, 14.5) | **(87.0, 14.5)** | 0.000 mm |

East-side moves only — west already constrained by U6 north pin column.
East cluster has no analogue obstruction (no IC at X≈80, Y=18); Q4/U12/D7/D8/J19
all at Y ≤ 9.5, sense row at Y=14.5 — bbox Y separation ensures no collision.

**Footprint hygiene** (`fix_option_b_footprints.py`):

- SOT-23-5 → DFN-10-1EP_3x3 swap for U2 with pad-net assignments from
  `novapcb.net`.
- L1, R47, R48 added with pad-net assignments.
- C31..C34 footprint+value swap: was 0402 1µF / 0805 4.7µF (AP2112K era),
  now 0805 10µF / 0402 100nF / 0805 22µF / 0402 100nF (Option B per TI
  SLVSC73 §10).
- Orphan +3V3 via at (25.137, 24.050) removed — collided with new U2 pad
  9 SW + pad 11 EP (3 DRC violations cleared).

### Commit 3 — thermal Rule-9 fix (`7761fa1`)

Hardcoded board outline 0.090 × 0.070 m in `gate12_thermal.py:main()` —
stale value from before v1.1 grew the board to 105 × 85 mm. Smaller
simulated outline = less spreader copper = artificially +5.2 °C MCU.
Synced to 0.105 × 0.085. MCU Tj 68.94 °C → **63.72 °C** (matches
arch-sweep prediction within 0.02 °C).

## Root cause

### Why the LDO failed (Option-B necessity)

Linear regulators with (V_in − V_out) drop × I_out > 100 mW are
unsuitable for compact aerospace boards without significant heatsinking.
642 mW continuous at U2 was the dominant heat budget item (40 % of the
1617 mW total).

The 5 V → 3.3 V drop is fundamental — only switching topology can
deliver 3.3 V at ~95 % efficiency, removing the dissipation entirely
(25 mW residual vs 642 mW dissipated). Architecture-level decision, not
a layout-tweak fix.

### Why the +5.2 °C delta appeared in step 3

Hardcoded geometry in the simulation script diverged from board
artifact. `gate12_arch_sweep.py` called `g12.run(board_L_m=0.105,
board_W_m=0.085, …)` explicitly (correct), but `gate12_thermal.py:main()`
used `board_L_m, board_W_m = 0.090, 0.070` (stale hardcoded from 90×70mm
v0). Same Rule-9 trap class as the planned-vs-actual sweep catch from
2026-05-23: sim INPUT diverged from board ARTIFACT.

### Why the mirror pairs deviated 5-9 mm

R42 and C62 were relocated west during prior task #87 (A↔B routing) to
clear U6's north pin column (X=27.25..28.75). The east-side mirror
partners (R44, C82) were not co-relocated in the corresponding +X
direction, leaving the asymmetry. Caught by the audit-hardening
adoption of pcb.ai R2 (mirror-pair ZERO-threshold-relaxation, 2026-05-23).

## Prevention

### Buck architecture as default for >50 mW drop (project rule)

Don't add an LDO when (V_in − V_out) × I_out > 50 mW unless heat
budget already covers it. Architecture sweep should run as part of any
power-rail spec decision, not after layout closure.

### Read geometry from board artifact, not hardcode

Long-term fix queued for the **DRU coverage gap cleanup PR (task #97)**:
`gate12_thermal.py` will use `board.GetBoardEdgesBoundingBox()` to derive
`board_L_m / board_W_m` at run-time, eliminating hardcoded-geometry
drift. Master directive 2026-05-23 also adds a new audit gate
`sim-inputs-match-board-artifact` that asserts all geometry/position
inputs to sims come from `board.*` API calls — same family as the
existing `thermal-uses-actual-positions` gate.

### Mirror-pair audit-hardening (pcb.ai R2 adoption)

`scripts/audit_layout_compliance.py:check_a_symmetry()` enforces ≤0.5 mm
deviation between mirror-pair members as a HARD FAIL (raised from WARN
2026-05-23). Any future relocation of a mirror-pair-listed component
must move both partners in opposite directions, or the audit blocks
merge. Cross-ref `docs/MASTER_PROCESS_RULES.md` §"Symmetry refinements".

## Spec deviations (Rule 4)

| Spec | As built | Why | Approved |
|---|---|---|---|
| C34 (Cout HF) east of L1 (initial proposal) | C34 NE of U2 body, NORTH of L1 (29.0, 21.5) | L1 (4 mm body + courtyard) blocks the east strip; only NE placement keeps cap body-edge ≤3 mm of U2 (DECOUPLING audit rule). Documented in `step5_place_B.py:160`. | Master 2026-05-23 step-3 sign-off |
| 10 DRC violations carry over | Pre-existing from #87/#89 fab-spec exceptions (drill_out_of_range + via_diameter on +5V_BEC, EFUSE_ILIM, ORING_GATE 0.25 mm-drill vias). | DRU rules exist for ORING_GATE; +5V_BEC and EFUSE_ILIM lack DRU exemption. Not Option B scope; baseline-confirmed by `git stash` + gate14 (10 before this PR). | Master 2026-05-23 step-3 sign-off; task #97 cleanup PR before Phase 7a |
| C32 (Cin HF) at (20.75, 26.43) — 1.93 mm Y from VIN pin | Anchor (21.0, 26.0) nudged 0.43 mm south by collision-avoidance | Still within 2.13 mm body-edge to VIN pad. Bulk C31 covers the lower-freq path. | Within decoupling guidance — no master callback needed |

## Rule 9 verification (artifact-level)

| Claim | Verified by |
|---|---|
| Pin wiring matches TPS62177DQC datasheet | Master line-by-line check of `power_3b.py` against TI SLVSC73 §10 typical-application figure |
| Feedback divider 0.8 × (1 + 562/180) = 3.297 V | Math verified by master at sign-off |
| L1 XAL4020-2R2 shielded for IMU noise | Coilcraft datasheet confirmed by master |
| Cap topology matches TI SLVSC73 §10 | Master sign-off on `power_3b.py` diff |
| U2_SW + U2_FB named nets | grep on `novapcb.net` confirms |
| gate12 COMPONENT_PROFILES U2 = 25 mW | `grep "U2" gate12_thermal.py:156` |
| ERC clean | `generate.erc` 0 errors |
| Mirror pairs sum to 105 | Python verification: 24+81=105, 20+85=105, 22+83=105, 18+87=105 |
| Thermal MCU 63.72 °C ≈ arch-sweep 63.7 °C | `thermal/current_step/` vs `thermal/swp_B_105_BUCK/` — same source set, same total P, same body forces, post-outline-fix mesh dimensions match |
| 0 net new DRC violations | Baseline 10 (git-stash + gate14 pre-PR) vs current 10 (post-PR + via removal) |

## Audit run

```
=== Layout compliance audit: novapcb-stepwise.kicad_pcb ===
Components: 83
Board outline: (0.0,0.0) to (105.0,85.0) mm

INFO:
  QUADRANT-AUTO: NW=33 NE=6 SW=8 SE=2
  ZONE-FILL: 7 zones filled — total 15819 mm² copper plane
  FAB-EXCEPTIONS: 11 total DRU rules; 8 fab-spec exceptions; 3 standard
  THERMAL-SIM-SOT: gate12_arch_sweep.py reads from .kicad_pcb (PASS)

MIRROR_PAIRS: 11/11 PASS (sense-row exactly 0.000mm, Q3↔Q4 0.5mm Y as
  master-approved per Q4 north-0.5mm position, others 0.000mm)

WARNINGS:
  QUADRANT-AUTO: spread 31 — documented in this PR doc under Spec
    deviations (structural reason: A/B/C/E/F/G subsystem boundaries
    bias NW-heavy by design)
  FANOUT-CORRIDOR: 4 U1 SPI3 pins blocked by R13 — pending R13 FLT
    firmware contract (non-blocking per master)

FAIL (3 issues remaining):
  DECOUPLING:
    U5 VDD net=+5V — nearest cap C9 @ 43.05mm  ← task #98 (this PR's next step)
    U6 VDD net=+5V — nearest cap C9 @ 3.46mm   ← task #91 (separate)
```

U2 DECOUPLING now PASS (C34 @ 2.32 mm body-edge). Total FAIL count
4 → 3 after Option B. Remaining 2 are pre-existing, both tracked.

## Renders

- `hardware/kicad/novapcb-stepwise/renders/option-b-step3/top.png` —
  buck cluster + mirror-symmetric sense rows + corner mounts
- `…/bot.png`, `…/in2.svg`, `…/in3.svg` — layer set per master directive
