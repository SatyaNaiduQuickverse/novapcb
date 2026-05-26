# IMU stress-relief slot — fresh up-front survey (task #50)

> Branch `docs/imu-slot-survey` off `sch/option-b-buck`. **NO LAYOUT TOUCH.**
> Sai un-deferred the slot from v2 → v1. Fresh survey on the CURRENT board (NOT
> the 2026-05-23/24 assumptions). Prior analysis: `docs/v2/D_SLOT_POLYGON_ANALYSIS.md`
> (deferred after 2 retrofit failures: 25-35 new DRC each).

## 1. Purpose

U-kerf Edge.Cuts slot to mechanically isolate the IMU island from board flex /
vibration (mount-bolt torque, frame/motor vibration, ESC shock). Pixhawk 6X uses
a separate isolated IMU PCB; v1 emulates with slot + bridge(s). The bridge gives
controlled mechanical coupling + carries the signal paths.

## 2. IMU island (current board)

ICs + decaps extent: **X44.0–83.4, Y50.2–63.8** (U3 ICM-42688-P @60, U8 BMI088
@68, U9 LSM6DSV16X @78, + decaps C41-43/C91-96). 39 mm wide — the 3 IMUs are
spread, so this is a large island.

## 3. KEY FINDING — perimeter crossing density (why the geometry must change)

Trace-crossings on each candidate slot line (±2 mm margin around the island):

| Slot line | Crossings | Nets | Verdict |
|---|---|---|---|
| **N-cut (Y≈48)** | **27** | **23** | ❌ INFEASIBLE — all IMU connectivity enters here (SPI1/2/3, I2C1/2, +3V3_IMU, HEATER_PWM, IMU2 CS/INT…) — the MCU is N/W of the island |
| W-cut (X≈42) | 3 | IMU3_CS, SPI1_MISO/SCK | ✅ low |
| E-cut (X≈85) | 5 | SDMMC1_D0/CLK/D1 | ✅ low |
| S-cut (Y≈66) | 4 | BUZZER, I2C1_SDA, SDMMC1_D1/D2 | ✅ low |

**This explains the prior failures**: both attempts cut a **N-span** (Y33/Y45)
— i.e. across the 27-net connectivity belt → 25-35 new DRC. The connectivity
fundamentally enters from the **north** (MCU side).

**Reframe: the U-slot must OPEN NORTH** — keep the dense N edge as the
connectivity neck (island "hangs" from the N), and slot the low-crossing
**W + E + S** sides. The prior "U-opens-west/south" geometry was backwards.

## 4. Decision matrix

| Option | Geometry | Nets to handle | Isolation | Risk on current (dense) board |
|---|---|---|---|---|
| **A — full U-open-N** | W + E + S slots, N open as neck | 12 (W3+E5+S4) → bridges/detours | 3-side flex break (good) | MED — 12 nets need bridge-gaps or re-route; +T3 MOT B.Cu now runs near W |
| **B — partial + bridges** | W + S slots only (skip E or shorten), bridge-gaps at each crossing | ~7 | 2-side break (moderate) | LOW-MED — fewer cuts, bridges carry crossings |
| **C — mini-slot** | short slots S of the *primary* IMU (U3) only | ~2-4 | partial (U3-focused) | LOW — minimal cuts |

Notes: even the low-crossing sides each carry a few nets — a slot can't sever
them, so each crossing needs either a **bridge gap** (leave board material +
copper there) or a **re-route** to the N neck. The board is **denser than the
failed attempts** (CAN/microSD/GPS/HSE/T3 all landed since), so any cut competes
with more routing + stitching vias near the slot lines.

## 5. Recommendation

**Option A (full U-open-N) is the right isolation target**, but its feasibility
hinges on handling the 12 W/E/S crossings without DRC regression on the dense
board. Recommended execution sequence (for sign-off):
1. Place the W/E/S slot Edge.Cuts segments with **bridge gaps** exactly where the
   12 nets cross (no re-routing needed — the bridges carry them). Verify each
   bridge is wide enough (≥~2 mm) for its crossing nets + clearance.
2. Confirm no stitching via / plane-pour sits on a slot-cut line (the PR #76
   conflict class) — relocate any that do (Rule 20).
3. Keep the N neck fully intact (the 27-net belt).

If §5.1 shows the bridge gaps can't be placed without cutting routing (dense
board), fall back to **Option B/C** (fewer slots) — partial isolation is still
better than none, and avoids a destructive retrofit.

## 6. Gates (planned, for the execution PR)

- DRC ≤ baseline (no nets cut; bridges carry all crossings); Edge.Cuts valid
  (closed board outline + slots).
- STACKUP / MIRROR / DECOUPLING audit PASS.
- Per-net check: every net crossing a slot line runs through a bridge (not cut).
- (v2 note) full mechanical isolation still wants the separate-IMU-board target.

---

**Awaiting master sign-off on the geometry (A full-U-open-N vs B/C) before any
layout touch. Key correction vs prior: the slot opens NORTH, not south.**
