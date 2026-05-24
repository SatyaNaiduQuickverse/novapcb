# Full Board Sim Suite — Plan (task #10)

> **Status**: DRAFT for master sign-off (autonomous mode 2026-05-24).
> NO sim execution yet — plan only.
> **Branch**: `docs/sim-suite-plan` off sch/option-b-buck head 780b5c3.
> **Trigger**: per master 2026-05-24 directive after 7-PR autonomous burst
> + H↔C halt. Final-state board sims pre-Phase-7a-freeze.

---

## Scope

5 sim categories per master directive. Each gets its own up-front
sub-section + execution PR.

## 1. Final thermal (gate12 v3) — confirm MCU Tj ≤ 80°C

**Reuse**: `hardware/kicad/novapcb-stepwise/gate12_thermal.py` v3 (sha
7761fa1 — fixed board outline 0.105 × 0.085m, added D zone IMU heat
sources). Last clean run before H↔C iteration burst: MCU 63.72°C
matching arch sweep within 0.02°C.

**Inputs**:
- Current `novapcb-stepwise.kicad_pcb` (post-CAN/microSD/GPS/CRSF-TELEM-SWD merge)
- Hot-case ambient T_amb=50°C
- Component heat sources: MCU 0.5W, U2 buck 0.05W, U6 eFuse 0.15W,
  U11/U12 ORFETs 0.05W each, IMU heater 0.0W (hot case)

**Gates**:
- MCU Tj ≤ 80°C (ArduPilot operating safety margin)
- Power conservation assertion (mesh-convergence per v3 self-check)
- No new hot spots > 75°C anywhere

**Output**: thermal map + body-temp table + delta vs pre-H-placement baseline.

## 2. USB Z_diff re-validate

**Reuse**: openEMS coupled-pair setup validated at PR #75. Last result:
Z_diff bracket [87.4, 105.75]Ω (Kirschning-Jansen analytical reference).

**Inputs**:
- USB diff pair F.Cu segment widths W=0.20mm, spacing S=0.13mm
- 4-layer stackup In1.Cu GND reference at 0.205mm

**Gates**:
- Z_diff in [87.4, 105.75]Ω bracket
- Z_diff variance ≤±5% across segments

**Likely no change** since USB geometry (J1, U5, MCU PA11/PA12) unchanged
post-H↔C iteration. Just final stamp.

## 3. SDMMC1 SI sanity check

**Per microSD PR #85 plan**: D0-D3 length-matched ±0.5mm, CLK ±2mm of
data avg, CMD ±5mm.

**Sim approach**: simple length-extraction from board + compute skew
per channel. No need for full FEM if length matching tolerance met.

**Status**: J2 placed at (95, 67) per PR #85, but SDMMC1 NOT YET routed
(routing is a separate sub-step from placement). So this sim is
**deferred until SDMMC routing PR lands**.

**Action**: defer to post-SDMMC-routing.

## 4. CAN bus diff impedance sanity

**Per CAN PR #84**: CANH/CANL pair routed with consistent spacing.
Master noted "doesn't need controlled impedance at v1's bus-stub-length
scale (<50mm); ~50-80Ω diff OK for short stubs."

**Sim approach**: simple openEMS or analytical Z_diff calc with
JLC06161H-7628 stackup parameters.

**Inputs**:
- CANH/CANL F.Cu trace widths + spacing (TBD from board — likely
  W=0.25mm default, S=0.20mm default)
- In1.Cu GND reference

**Gates**:
- Z_diff in 50-80Ω bracket (CAN spec is 120Ω terminated, but transmission
  line impedance is decoupled from termination at <50mm stubs)
- Z_common ≤ 60Ω (low common-mode for ESD/EMC margin)

**Status**: CAN U14+J20 placed but NOT YET routed (Step 8 PR placement only).
**Defer until CAN routing PR lands.**

## 5. Power-network sim (PDN impedance at MCU VDD)

**Reuse**: openEMS PDN setup if available; otherwise SPICE behavioral.

**Inputs**:
- MCU VDD pins (5 pins: 11/27/50/75/100) on +3V3 net
- C decap inventory near each VDD pin (per gate Rule)
- In3.Cu +3V3 plane impedance
- B subsystem U2 buck output impedance (10MHz BW)

**Gates**:
- PDN |Z| ≤ 100mΩ at 10MHz (typical MCU SI target)
- No PDN resonance peak > 200mΩ in 1MHz-100MHz range

**Status**: B/C placement + +3V3 plane all merged. PDN sim runnable on
current board.

## Decisions for sign-off

1. **Sim 1 (Thermal)**: run NOW — board ready ✓
2. **Sim 2 (USB Z_diff)**: run NOW — geometry unchanged ✓
3. **Sim 3 (SDMMC SI)**: DEFER until SDMMC routing PR lands
4. **Sim 4 (CAN Z_diff)**: DEFER until CAN routing PR lands
5. **Sim 5 (PDN)**: run NOW — board ready ✓

**Recommend**: execute sims 1+2+5 in this PR; queue 3+4 as follow-up
post-routing.

## Gates per sim PR

Each sim PR:
- Sim setup script committed
- Input parameters documented
- Output: numerical result + threshold check (PASS/FAIL)
- Comparison to baseline (if applicable)
- Brief PR doc with method + result

## Sequence

1. Master sign-off on this plan
2. Execute Sim 1 (thermal) — gate12_thermal.py v3 on current board → PR
3. Execute Sim 2 (USB Z_diff) — openEMS coupled-pair → PR
4. Execute Sim 5 (PDN) — openEMS or analytical → PR
5. Defer Sim 3 + 4 until corresponding routing PRs land

---

**Awaiting master sign-off (or autonomous-execute approval per current burst mode).**
