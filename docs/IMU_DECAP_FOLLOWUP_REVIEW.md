# IMU decap follow-up — review (task #53)

> Follows the PR #104 audit (`docs/IMU_DECAP_AUDIT.md`). Reviews the 3 audit
> follow-up items (C42/C91 nudges, C96 bulk, VDD/VDDIO distribution).
> **Outcome: no layout change** — findings below. Doc-only PR.

## 1. C42 / C91 100nF distance — ACCEPT as-is (no move)

The audit flagged C42 (3.21mm to U3 ICM-42688-P) and C91 (3.11mm to U8 BMI088)
as ~0.1–0.2mm over the 100nF ≤3mm guideline. Measured from the board, the
**best-achievable clear distance** (full obstacle model: U3/U8 bodies + neighbor
decaps C41/C43/C92 + tracks) is:

| Cap | Current | Min clear achievable | Move required | +3V3_IMU rail re-route |
|---|---|---|---|---|
| C42 | 3.21mm | 2.79mm | ~3.5mm relocation (NW of U3) | yes — C42.1 has 2 rail tracks |
| C91 | 3.11mm | 2.94mm | ~0.16mm | (negligible) |

**Decision: no move.** The gain (0.2–0.4mm) is on the **shared +3V3_IMU rail**
(both IMU power pins tie to one rail) that already carries bulk decoupling
(C43 2.2µF, C93 1µF) plus the routed rail network. The SI impact of 3.2mm vs
2.8mm at the IMU's analog noise floor is below the measurement floor. Moving C42
requires re-routing its rail connection in the dense IMU pocket — **re-route +
DRC risk exceeds the zero practical electrical benefit.** The caps are at their
practical minimum given the dense, fixed IMU placement; 0.1–0.2mm over a
*guideline* is acceptable.

## 2. VDD/VDDIO distribution — MOOT (single-rail topology)

The audit observed the two 100nF caps cluster near one of each IMU's two
+3V3_IMU pins. This only matters when VDD and VDDIO are **separate domains**
each needing independent HF decoupling. On this board **both power pins of each
IMU tie to the single +3V3_IMU rail**, so a 100nF near *either* pin decouples
the shared rail. No redistribution warranted. Documented; no change.

## 3. C96 / LSM6DSV16X bulk cap — OPEN (Rule-3, Sai/datasheet input needed)

U9 (LSM6DSV16X) has 2×100nF (C94/C95) + **1×10nF (C96)** and **no 1–10µF bulk**,
unlike U3 (2.2µF) and U8 (1µF). Whether the LSM6DSV16X *requires* a local bulk
cap cannot be determined without the actual datasheet — and the repository
contains **no LSM6DSV16X decap spec**.

Per CLAUDE.md §3 / Rule 3, decap values must come from the datasheet, **not**
training-data pattern-matching (the drone-safety class of risk). This item is
therefore **held open**, not guessed.

Two resolution paths (Sai input):
- **(i)** Sai provides the LSM6DSV16X datasheet → master+worker run a decap-spec
  conformance check; add/size a bulk cap if the datasheet requires one (small
  SKiDL + layout follow-up).
- **(ii)** Sai confirms current design intent (e.g. bulk decoupling shared via
  the +3V3_IMU rail / plane is sufficient for the LSM6DSV16X) → accept as-is.

→ Tracked as **task #54 — LSM6DSV16X decap conformance check** (gated on Sai
providing the datasheet OR confirming intent).

## 4. Verification

Doc-only — **no layout, no SKiDL, no netlist change**. DRC unchanged at baseline
21 (error-severity); STACKUP / MIRROR / DECOUPLING audits unchanged. ERC N/A.

## 5. Outcome

- C42 / C91: **accept as-is** (practical minimum; negligible benefit to moving).
- VDD/VDDIO: **moot** (single +3V3_IMU rail).
- C96 / LSM6DSV16X bulk: **open → task #54** (Sai/datasheet).

IMU decoupling overall remains in good shape (per PR #104 audit: 6/9 optimal,
all GND returns short, all bulk caps present except the LSM6DSV16X question).
