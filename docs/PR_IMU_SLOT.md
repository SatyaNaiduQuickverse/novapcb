# PR — IMU stress-relief slot (S-edge), task #50

> Branch `hw/imu-slot` off `sch/option-b-buck`. Adds an Edge.Cuts stress-relief
> slot along the **south** edge of the IMU island to mechanically decouple it
> from board flex on the dominant (N-S prop-thrust) axis. Survey:
> `docs/IMU_SLOT_SURVEY.md`. Sai un-deferred from v2.

## 1. What changed

**S-edge slot** at Y66: two Edge.Cuts segments **X42–44 + X47–83** (37 mm total
flex break) with one **bridge at X44–47** carrying BUZZER + I2C1_SDA across.
N neck (the 27-net MCU connectivity belt) stays fully intact. Zones re-filled
(slot cutout in all 6 copper layers).

## 2. Geometry journey (open-N insight + cascade to S-only)

- **Open-N insight** (the fix the prior 2 attempts missed): the IMU island's N
  edge carries 27 crossings / 23 nets (all SPI/I2C/INT/CS/+3V3_IMU enter from
  the MCU, N/W of the island). The prior attempts cut a **N-span** → severed the
  connectivity belt → 25–35 DRC. The slot must **open north**, cutting the
  low-crossing W/E/S sides.
- **Cascade (master pre-approved A→B→C): both W and E sides blocked by parallel
  routing → S-only.**
  - **E-cut blocked**: SDMMC1_D0 weaves across X85 four times (the microSD route
    runs *along* the E-cut full height) → ~7 bridges = ineffective slot.
  - **W-cut blocked**: the IMU3_CS diagonal (29.4,41.7→50.8,61.6) sweeps through
    the W-slot zone, and I2C1_SCL runs vertically at X41.15 — both within the
    0.5 mm edge clearance of the W-cut. (Caught by DRC `copper_edge_clearance`
    after the trial cut; reverted cleanly.)
  - **S-cut clean**: IMU3_CS maxes at Y61.6 and I2C1_SCL stays at X≤41.2 —
    neither reaches the S-slot (Y66, X42–83). The S middle (X47–84) is clear.

Result: **S-only** — a 37 mm flex break on the **dominant N-S prop-thrust axis**
(per master: airframe flex is dominantly N-S, not E-W). W/E omitted (routing-
blocked, would need rerouting merged IMU/microSD work for marginal cross-axis gain).

## 3. Methodology lesson (for the survey-then-cut pattern)

The per-side **crossing count** in the survey (traces crossing the slot *line*
perpendicularly) said all 3 sides feasible — but it **missed traces running
parallel/diagonal through the slot zone** (E: SDMMC1 weave; W: IMU3_CS diagonal +
I2C1_SCL vertical). The fab-grade check is **copper-within-edge-clearance of the
slot rectangle**, not just line-crossings. (Same class as the dense-pocket
scan-geometry lesson — model the full 2-D trace geometry, not 1-D crossings.)

## 4. Verification (5-gate)

| Gate | Result |
|---|---|
| DRC | **21 = baseline, 0 new** (incl. 0 `copper_edge_clearance` — the S-slot clears all nearby copper) |
| STACKUP-SPEC-MATCH | **PASS** (4 plane pairs unchanged) |
| MIRROR / DECOUPLING / audit | **PASS** — all clean (no component moves) |
| Unconnected | **0 delta** (222 = baseline) — the bridge carries BUZZER + I2C1_SDA continuously (verified) |
| Cluster walk / mech-isolation | S-slot breaks the island S edge X42–83; island connects via N neck + W + E; bridge X44–47 preserves the 2 crossing nets |

## 5. ArduPilot impact + scope note

- Reduces board-flex strain transfer to the IMU mounting plane on the N-S axis →
  improved gyro noise floor under prop-thrust flex (the point of the slot).
- **1-side (S) vs the originally-scoped 2-side (W+S)**: W blocked by IMU3_CS +
  I2C1_SCL. Full W/E isolation would require rerouting those off the W edge +
  SDMMC1 off the E edge (touches merged PRs #100/#101/#105) — deferrable as a
  follow-up if Sai wants cross-axis isolation; the dominant N-S axis is covered.
- Honors Sai's "absolutely use the IMU slot" — the slot is in v1.
