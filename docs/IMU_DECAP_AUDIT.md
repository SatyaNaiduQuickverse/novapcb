# IMU decoupling-cap audit (task #51)

> Branch `docs/imu-decap-audit` off `sch/option-b-buck` (c79cd8f). **Doc /
> analysis only — NO LAYOUT TOUCH.** Audits the 9 IMU decoupling caps against
> per-part decoupling practice. Distances measured from the actual board.

## 0. Scope correction (flag for master)

The dispatch named all three IMUs as ICM-42688-P. The board shows **three
different parts** (intentional triple-redundant heterogeneous IMU set):

| Ref | Part | Package | Decaps |
|---|---|---|---|
| U3 | **ICM-42688-P** | LGA-14 2.5×3 mm | C41, C42 (100nF), C43 (2.2µF) |
| U8 | **BMI088** | LGA-16 | C91, C92 (100nF), C93 (1µF) |
| U9 | **LSM6DSV16X** | LGA-14 | C94, C95 (100nF), C96 (10nF) |

Decap specs therefore differ per part. Where a value/quantity needs the actual
datasheet to confirm (e.g. VDD vs VDDIO pin function, bulk-cap requirement),
this audit flags it rather than assuming ICM-42688-P numbers (Rule 3).

**General decoupling criteria used** (industry-standard for these LGA IMUs):
100 nF HF decap **≤2–3 mm** of the supply pin; bulk (1–10 µF) **≤5 mm**; GND
return pad → plane via short (≤~3 mm, sub-nH).

All 9 caps are on the **+3V3_IMU** rail (both power pins of each IMU tie to
+3V3_IMU — i.e. VDD and VDDIO share this rail on this board).

## 1. Per-IMU audit (measured from board)

### U3 — ICM-42688-P (@60.0,57.0); +3V3_IMU pins: 8 (61.46,57.75), 14 (59.50,55.80)

| Cap | Value | Net | Nearest +3V3 pin | Pin dist | 100nF≤3 / bulk≤5 | GND→via | Status |
|---|---|---|---|---|---|---|---|
| C41 | 100nF | +3V3_IMU | pin14 | 2.80 mm | ✅ (≤3) | 2.48 mm | OK (borderline) |
| C42 | 100nF | +3V3_IMU | pin14 | **3.21 mm** | ⚠️ >3 | 1.79 mm | minor nudge |
| C43 | 2.2µF (bulk) | +3V3_IMU | pin8 | 2.61 mm | ✅ (≤5) | 1.59 mm | optimal |

### U8 — BMI088 (@68.0,57.0); +3V3_IMU pins: 3 (66.80,57.50), 11 (69.20,56.50)

| Cap | Value | Net | Nearest +3V3 pin | Pin dist | 100nF≤3 / bulk≤5 | GND→via | Status |
|---|---|---|---|---|---|---|---|
| C91 | 100nF | +3V3_IMU | pin11 | **3.11 mm** | ⚠️ >3 | 2.95 mm | minor nudge |
| C92 | 100nF | +3V3_IMU | pin11 | 1.41 mm | ✅ | 1.11 mm | optimal |
| C93 | 1µF (bulk) | +3V3_IMU | pin3 | 2.62 mm | ✅ (≤5) | 2.51 mm | optimal |

### U9 — LSM6DSV16X (@78.0,57.0); +3V3_IMU pins: 5 (78.50,56.08), 8 (76.83,56.25)

| Cap | Value | Net | Nearest +3V3 pin | Pin dist | 100nF≤3 / bulk≤5 | GND→via | Status |
|---|---|---|---|---|---|---|---|
| C94 | 100nF | +3V3_IMU | pin5 | 1.86 mm | ✅ | 2.90 mm | optimal |
| C95 | 100nF | +3V3_IMU | pin5 | 2.22 mm | ✅ | 1.11 mm | optimal |
| C96 | **10nF** | +3V3_IMU | pin8 | **3.32 mm** | ⚠️ >3 + value | 2.90 mm | see §2.2 |

## 2. Findings

### 2.1 Distance compliance
- **6 / 9 optimal**: C43, C92, C93, C94, C95 clearly within spec; C41 at 2.80 mm
  borderline-OK.
- **3 / 9 marginally over** the 100 nF ≤3 mm guide: **C42 (3.21), C91 (3.11),
  C96 (3.32)** — small overshoots (~0.1–0.3 mm). HF decoupling impedance rises
  slightly; not a functional failure, candidate nudges.
- **GND returns**: all 9 cap GND pads have a GND plane via within **1.1–2.95 mm**
  (sub-nH). No GND-return concern. Good.

### 2.2 C96 is 10 nF, not a bulk cap (flag)
U9 (LSM6DSV16X) has 2×100 nF (C94, C95) + **1×10 nF (C96)** — no 1–10 µF bulk,
unlike U3 (2.2µF) and U8 (1µF). Either (a) intentional per LSM6DSV16X datasheet
(it may rely on the +3V3_IMU plane bulk + the 100 nF pair), or (b) a missing bulk
cap. **Confirm against the LSM6DSV16X datasheet** before any action.

### 2.3 Power-pin decap distribution (consistent pattern across all 3)
Each IMU has two +3V3_IMU pins; in every case the **two 100 nF caps cluster near
ONE pin** and the bulk/odd cap sits near the OTHER:
- U3: pin14 ← C41+C42 (100nF); pin8 ← C43 (bulk) only
- U8: pin11 ← C91+C92 (100nF); pin3 ← C93 (bulk) only
- U9: pin5 ← C94+C95 (100nF); pin8 ← C96 (10nF)

If the two power pins are **separate domains** (VDD vs VDDIO) that each want a
dedicated HF 100 nF, the "far" pin currently lacks one. **Mitigated** here
because both pins share the +3V3_IMU rail (the plane couples them), so this is a
lower-severity optimization, not a fault. **Confirm VDD/VDDIO pin functions per
each datasheet** to decide if redistribution is warranted.

## 3. Summary & recommendation

| Verdict | Count | Caps |
|---|---|---|
| Optimal | 6 | C41, C43, C92, C93, C94, C95 |
| Minor nudge (≤0.3 mm over) | 2 | C42, C91 |
| Needs datasheet confirm | 1 | C96 (value) + the VDD/VDDIO distribution question |
| Significant reposition | 0 | — |

**Overall: the IMU decoupling is in good shape** — all bulk caps within spec, all
GND returns short, 6/9 optimal, no significant repositions. The residual items
(C42/C91 ~0.1–0.3 mm over; C96 value; VDD/VDDIO distribution) are low-severity.

**Recommended follow-up (separate layout PR, fresh context):**
1. Nudge C42 and C91 ~0.3–0.5 mm toward their IMU power pins (if pocket allows).
2. Resolve C96: confirm LSM6DSV16X needs no bulk, or add/upsize per datasheet.
3. Confirm VDD/VDDIO pin functions on all 3 parts; redistribute a 100 nF to the
   "far" power pin only if the datasheets call for per-pin HF decoupling.

No layout changed in this PR (audit only).
