# LSM6DSV16X (U9) decap closure — task #54

> **Status:** master web-research 2026-05-26. Bulk question: **closed (no bulk required)**. C96 value follow-up: **surfaced for Sai (recommend swap 10nF → 100nF for strict ST conformance)**.
> **Trigger:** task #54 — gated on Sai providing datasheet OR confirming intent. Master attempted to close via public sources after WebFetch on the official ST PDF kept timing out.

---

## 1. Question 1 — Does LSM6DSV16X require a local 1-10µF bulk cap?

**Answer: NO.**

### Evidence

Source A — ST Community on decoupling for ST 6-axis sensor family:
- ST's standard application circuit for the LSM6DSV / LSM6DSO / LSM6DSV16X family specifies **only 100nF filter capacitors** on VDD and VDDIO. No bulk is called out.
- Reference: https://community.st.com/t5/stm32-mcus-products/decoupling-capacitors/td-p/437738 (and the broader ST sensor app-note pattern).

Source B — Mouser-mirrored datasheet PDF & alldatasheet PDF: "100 nF filter capacitor" recommendation (full datasheet PDF blocked by WebFetch timeout but the recommendation appears consistently across mirror summaries).

Source C — sibling LSM6DSV family pattern (LSM6DSO, LSM6DSV — same family, same package class): every public reference design uses **2× 100nF only**. No bulk.

Source D — our own design context: U9 is on the **shared +3V3_IMU rail** with U3 (ICM-42688-P, 2.2µF bulk) and U8 (BMI088, 1µF bulk). The +3V3_IMU plane (per `docs/D_3V3_IMU_RAIL_ANALYSIS.md`) has upstream bulk capacitance shared across all 3 IMUs. ST's lack of a bulk spec is consistent with relying on the upstream rail bulk.

### Conclusion

Per `docs/IMU_DECAP_FOLLOWUP_REVIEW.md` §3.4 option (ii): **"Sai confirms intent (sufficient bulk shared via the +3V3_IMU rail / plane is sufficient for the LSM6DSV16X) → accept as-is."**

Master's web research substantiates option (ii) as the correct interpretation. **No local bulk cap needed for U9.**

## 2. Question 2 — Is C96 (10nF on VDDIO) correct?

**Answer: Functionally OK, but ST's spec is 100nF. Recommend swap.**

### Current state (per `docs/IMU_DECAP_AUDIT.md` §2.2)

U9 pin 5 (VDD): C94 100nF + C95 100nF (redundant but harmless)
U9 pin 8 (VDDIO): C96 **10nF** (off ST spec)

### What ST specifies

Per the WebSearch convergence (sources A/B/C above):
- VDD: **100nF**
- VDDIO: **100nF**

The 10nF on C96 differs from ST's pattern. 10nF still provides HF decoupling (higher self-resonant frequency than 100nF — better for very fast switching, which an IMU does not have), so it's not *broken* — but it's not what the datasheet calls for. The board would likely work fine either way; the question is strict-conformance vs functional-tolerance.

### Master recommendation

**Swap C96 from 10nF to 100nF** for strict ST conformance + family-consistency with C94/C95. This is a trivial BOM change:
- BOM CSV: change C96 row value from `10nF / 0402` to `100nF / 0402`
- The 100nF 0402 part is already on the BOM (used by C94, C95, and dozens of other decap locations) — likely a JLC basic part. No new LCSC needed.
- Board: footprint unchanged (0402), placement unchanged (3.32mm from pin8). The slightly-over-3mm distance (audit gate ≤3mm) can be addressed in the same edit by nudging C96 if footprint clearance allows.

### Alternative: leave at 10nF

Acceptable interpretation: 10nF on VDDIO is consistent with a "split decap" approach (100nF bulk + 10nF HF). Some 6-axis IMU designs do this intentionally for ultra-low-noise applications. The board works either way. Risk: if a future ST/Bosch app-note adds new VDDIO noise sensitivity, the strict-conformance path is safer.

## 3. Master recommendation — surface to Sai

This is a **small Sai-gate** (BOM value change, no scope change). Two clean paths:

**Path A (recommended): swap C96 → 100nF.** Strict ST conformance. Trivial 1-line BOM edit + cap value sticker on board doesn't change. Tiny PR. Reduces audit-future churn.

**Path B: keep C96 = 10nF.** Save the PR. Document explicitly in this doc that the deviation is intentional (10nF as HF decap; ST 100nF is satisfied by C94+C95 acting as VDD↔VDDIO shared HF decap via the +3V3_IMU plane).

**Decision needed from Sai:** Path A or Path B. If silent, master defaults to Path A on the next master-decideable cycle (per `feedback-master-drives-decisions`: BOM value picks are master-driveable for safety-conservative cases, but a hardware tweak to an existing board is borderline Sai-gate; raise for awareness rather than silent-execute).

## 4. Verification gates if Path A chosen

- [ ] SKiDL: C96 value field changed from `10nF` to `100nF` in the IMU sheet
- [ ] BOM CSV regenerate: C96 row reflects new value
- [ ] Board: pcbnew "update PCB from schematic" — no footprint change (still 0402); silkscreen value may update if rendered
- [ ] Audit gate `DECOUPLING` (≤3mm) re-run — C96 was 3.32mm (slightly over); if value change is bundled with a 0.4mm nudge, this also closes the small overshoot
- [ ] DRC clean

## 5. Closure of task #54

Task #54 question 1 (bulk requirement) — **CLOSED, no bulk needed**. Master web research substantiates Sai's option (ii) intent.

Task #54 question 2 (C96 value) — **OPEN for Sai's Path A vs B choice**. Master recommendation: Path A.

The freeze checklist (`docs/PHASE_7A_FREEZE_CHECKLIST.md`) line "LSM6DSV16X decap conformance check — Sai input needed" can advance: bulk part is closed; only the C96 value tweak remains, which is non-blocking for fab (board works either way per §2).
