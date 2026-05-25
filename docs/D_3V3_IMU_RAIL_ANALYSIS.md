# +3V3_IMU Rail Routing — Up-Front Constraint Analysis

> **Status**: DRAFT for master review. NO routing committed until master
> approves this topology choice (per D-placement pattern + Rule 8).
> Branch: `hw/3v3-imu-rail` off `sch/option-b-buck` head `e43ec76`.
> Written 2026-05-23.

---

## 1. Net inventory (verified)

`+3V3_IMU` net has 17 on-board pads:

| Ref | Pad | Position (mm) | Role |
|---|---|---|---|
| **U13** | 5 (OUT) | (58.70, 26.95) | LP5907 LDO output — SOURCE |
| **C78** | 1 | (62.52, 27.00) | LDO output bulk cap (already adjacent to U13) |
| C41 | 1 | (57.02, 54.50) | U3 VDD 100nF decap |
| C42 | 1 | (56.52, 57.00) | U3 VDDIO 100nF decap |
| C43 | 1 | (59.52, 59.50) | U3 bulk 2.2µF |
| U3 | 14 (VDD) | (59.50, 55.80) | IMU1 ICM-42688-P VDD |
| U3 | 8 (VDDIO) | (61.46, 57.75) | IMU1 ICM-42688-P VDDIO |
| C91 | 1 | (67.27, 54.07) | U8 VDD 100nF |
| C92 | 1 | (70.52, 57.00) | U8 VDDIO 100nF |
| C93 | 1 | (67.77, 59.93) | U8 bulk 1µF |
| U8 | 3 (VDD) | (66.80, 57.50) | IMU2 BMI088 VDD |
| U8 | 11 (VDDIO) | (69.20, 56.50) | IMU2 BMI088 VDDIO |
| C94 | 1 | (77.52, 54.50) | U9 VDD 100nF |
| C95 | 1 | (80.52, 57.00) | U9 VDDIO 100nF |
| C96 | 1 | (77.52, 59.50) | U9 bulk 1µF |
| U9 | 5 (VDDIO) | (78.50, 56.08) | IMU3 LSM6DSV16X VDDIO |
| U9 | 8 (VDD) | (76.83, 56.25) | IMU3 LSM6DSV16X VDD |

**Source**: U13.5 (LDO output) at (58.70, 26.95)
**Loads**: 6 IMU power pins + 9 decap caps spread across D zone X=56..86 Y=51..63
**Source-to-farthest-load**: U13.5 (58.70, 26.95) → U9.5 (78.50, 56.08) ≈ sqrt(19.8² + 29.1²) ≈ 35 mm

## 2. Topology decision

Three candidates per master 2026-05-23:

### (a) F.Cu/B.Cu trace network — **RECOMMENDED**

- Trace width 0.25mm (single trace at 5mA carries <5°C rise; plenty of margin at total 30mA)
- Source (U13.5+C78.1 cluster at Y=27) → trunk south through bridge column X=63±5mm
  to Y=53 → branches east+west to each IMU + its 3 decap caps
- ~12 connection segments (MST topology on 17 nodes)
- Total trace length ~80-100mm including all branches
- Layer: F.Cu primary (D zone F.Cu is sparsely used after D-routing PR
  #77 — most of D F.Cu has only decap-to-IMU short stubs); B.Cu reserved
  for SPI signals already routed

### (b) Local copper pour in D zone (B.Cu or F.Cu)

- Define +3V3_IMU zone covering D zone X=56..86 Y=51..63
- Single via from U13 area + cluster pads tap directly
- **Cons**:
  - F.Cu pour competes with 12 IMU3_CS/SPI3_SCK/MISO/MOSI track segments
    already routed F.Cu in D zone (PR #77 added these)
  - B.Cu pour fights with SPI3 wraparound + IMU3_INT1 routes already on B.Cu
  - Either way: significant rework to existing D routes
- Marginal PDN improvement over (a) at 30mA total current

### (c) Inner-layer split-zone

- Carve +3V3_IMU sub-zone out of In3.Cu +3V3 plane
- **Cons**:
  - Requires update to `EXPECTED_PLANES` in audit (and re-codification of
    stackup-spec-match for partial-layer zones)
  - Invalidates existing +3V3 plane PSRR calculation (split changes
    impedance for OTHER consumers — U4 DPS310, U7 LPS22HB, all MCU
    decoupling on +3V3)
  - Significant stackup rework — would need its own PR

## 3. Recommendation: Topology (a) F.Cu trace network

**Quantified rationale**:

| Factor | Number | Verdict |
|---|---|---|
| Total current | ~30 mA (6 IMU power pins × ~5 mA each) | Trivial for trace |
| Trace width sufficient at 30mA | 0.10 mm (allows 0.5A) | 2.5× margin even at 0.25mm |
| LDO PSRR @ 1kHz (LP5907) | 80 dB | Source-side noise rejection already excellent |
| LDO PSRR @ buck switching 1.8MHz | 60 dB | Verified IMU noise budget Option B doc |
| IMU intrinsic noise floor (gyro) | 3.5 mdps/√Hz | Margin 580× per Option B sweep |
| IMU intrinsic noise floor (accel) | 70 µg/√Hz | Margin 7400× per Option B sweep |
| Source-to-farthest-load trace length | ≤35mm | Impedance contribution at 30mA DC ≈ 0 |

The LDO does the noise filtering job — the rail just needs to deliver
clean DC. Plane topology offers marginal noise improvement at significant
rework cost. (a) wins by Occam's razor + cost/benefit.

## 4. Decap distance check (existing audit gate)

For each IMU VDD/VDDIO pin, nearest decap cap on +3V3_IMU:

| Pin | XY | Nearest cap | Cap XY | Body-edge dist (mm) | ≤3mm gate |
|---|---|---|---|---|---|
| U3.14 (VDD) | (59.50, 55.80) | C41 | (57.02, 54.50) | 0.25 (C41.south to U3.north) | ✓ |
| U3.8 (VDDIO) | (61.46, 57.75) | C42 | (56.52, 57.00) | 0.05 (C42.east to U3.west) | ✓ |
| (U3 bulk) | — | C43 | (59.52, 59.50) | 0.25 (C43.north to U3.south) | ✓ |
| U8.3 (VDD) | (66.80, 57.50) | C91 | (67.27, 54.07) | ~0.5 | ✓ |
| U8.11 (VDDIO) | (69.20, 56.50) | C92 | (70.52, 57.00) | ~0.5 | ✓ |
| (U8 bulk) | — | C93 | (67.77, 59.93) | ~0.5 | ✓ |
| U9.8 (VDD) | (76.83, 56.25) | C94 | (77.52, 54.50) | ~0.5 | ✓ |
| U9.5 (VDDIO) | (78.50, 56.08) | C95 | (80.52, 57.00) | ~0.5 | ✓ |
| (U9 bulk) | — | C96 | (77.52, 59.50) | ~0.5 | ✓ |

All 9 decap caps within 0.05-0.5mm body-edge to their respective IMU
bodies. `check_decoupling` audit gate will PASS for all D-zone IMUs
once +3V3_IMU is routed (the cap pad must be connected to the IC pin's
VDD net for the gate to verify proximity — currently they are connected
in the netlist, but the gate checks routed pad-to-pad which requires
F.Cu trace closing the loop).

## 5. Routing plan

**Phase A** — source-to-D-zone trunk:
- U13.5 (58.70, 26.95) → F.Cu south to (62.0, 30) — short hop east
- Trunk south on F.Cu at X=62-65 column (bridge corridor X=63±5)
  through to D zone north edge Y=51
- Length ~24mm

**Phase B** — D-zone branch network:
- At Y=53 (south of bridge), split into 3 IMU sub-branches:
  - U3 branch: west to X=59, then taps to C41+C42+C43+U3.14+U3.8
  - U8 branch: stays around X=68, taps to C91+C92+C93+U8.3+U8.11
  - U9 branch: east to X=78, taps to C94+C95+C96+U9.8+U9.5

Each branch traces ~6-10mm total. Sum of all branches ~50mm.

**Total**: ~80-100mm of F.Cu trace at 0.25mm width.

## 6. Implementation approach

Freerouting with surgical DSN scope to single net `+3V3_IMU` (1 net,
17 pad endpoints). Should complete in <30s. Reuse `integ_d_routing.py`
+ `apply_d_ses.py` pattern.

Alternative: manual routing script with hand-picked MST topology if
Freerouting produces awkward paths.

## 7. Constraints (master 2026-05-23)

- DRC ≤ baseline 10 (0 net new)
- `stackup-spec-match` audit gate PASS (no inner-layer changes)
- MIRROR_PAIRS 11/11 PASS (A-zone untouched)
- Per-trace GND-reference cluster walk (F.Cu over In1.Cu GND, B.Cu
  over In4.Cu GND)
- Each IMU decap ≤3mm body-edge to its VDD pin (verified §4)

## 8. Decisions for master

1. **Topology**: confirm (a) F.Cu trace network (my recommendation)
   OR redirect to (b)/(c)?
2. **Trace width**: confirm 0.25mm (my default; could go thinner 0.15mm
   for routing flexibility if needed). 0.25mm = ~5A current rating
   at 1oz Cu, vastly overspec for 30mA but standard signal width.
3. **Bridge column**: confirm trunk south through bridge X=63±5mm
   (per slot sub-step #102 future compatibility)?

---

**Awaiting master sign-off on §8 decisions before implementation.**
