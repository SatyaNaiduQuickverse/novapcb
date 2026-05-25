# Placement strategy — pivot Step 3 P0

> **Purpose**: lock the physics-guided placement strategy on paper BEFORE any
> KiCad placement work. Per CLAUDE.md §6.2 (plan first, expensive layout work
> second). This is the input master adjudicates so the Step 3 P1+ placement
> execution has a clear strategy + a master-approved layer count to work
> against.
>
> **Status**: pivot Step 3 P0 planning deliverable, 2026-05-21. Companion to
> `docs/THERMAL_BUDGET.md` (per-component dissipation) — heat sources drive
> the zoning decisions in this document.
>
> **Sai's reliability mandate** (verbatim 2026-05-20): "it working 100% is
> the priority", "strong resilient stuff that won't fail". Sai's dimension
> freedom (later 2026-05-20): board size is OUTPUT of good placement, not
> a fixed input — the rectangle expands as needed for generous spacing.

---

## 1. The five failure modes the placement must fix

Phase 6 P0 surfaced four failure-mode signals on the dense 36×36 4-layer
baseline; Step 2 fixed one of them (#1 inrush). The remaining four are the
constraints that drive every placement decision below.

| # | Failure mode | Phase 6 source | Density-driven? | Mitigation strategy |
|---|---|---|---|---|
| 1 | ~~Inrush 3.39 A at power-on~~ | 6a.3 | partially | **FIXED** by Step 2 eFuse front-end (PR #55) |
| 2 | PDN anti-resonance 133 mΩ at 100 kHz | 6a (PDN sweep) | YES — mixed power plane | Layer-count uplift to 6 → separate 3V3 + 5V planes (§3 below) |
| 3 | AP2112K LDO Tj = 88°C at 40°C ambient | 6j.2 | YES — thermal-pour constrained | Architecture evaluated (linear LDO retained — THERMAL_BUDGET §2.5) + zoning + LDO copper pour ≥ 100 mm² on inner power plane (§2.1 + THERMAL_BUDGET §2.3) |
| 4 | 4 USB-self-band harmonics > −40 dB | 6k | partially — coupling-distance | Zone separation: SDMMC + DShot aggressors at one end, USB+IMU at the other (§2 + §4) |
| 5 | 5 unprotected external lines (no TVS on telem/GPS/CRSF/ESC) | 6i | NO — circuit-level not placement | Out of v1 scope per `docs/CONFIDENCE_MAP.md` row 11; v2 candidate |

All four open failure modes have a placement-level lever (zoning, layer
count, copper pour). The placement strategy below addresses them in order.

---

## 2. Subsystem zoning — end-to-end physical separation

The board is divided into four zones along the long axis, with EMI/thermal
aggressors at one end and victims at the other. Adapted from the standard
Pixhawk family zoning convention (power on one short edge, IMU at the
opposite short edge).

### 2.1 Zone map

```
       Long axis →
       ┌──────────────────────────────────────────────────────────────────┐
       │                                                                  │
       │  Zone 1     │  Zone 2 (centre)         │  Zone 3                 │
       │  POWER      │  MCU + USB + SDMMC       │  SENSORS / ANALOG       │
       │  (HEAT +    │  (DIGITAL HUB +          │  (VICTIM — IMU + baro + │
       │   inrush    │   USB-self-band          │   ADC; FAR from heat +  │
       │   stage)    │   aggressors)            │   EMI sources)          │
       │             │                          │                          │
       │  Mauch J4   │  STM32H743 U1            │  ICM-42688-P U3 (TOP)   │
       │  Q2 P-FET   │  Y1 8 MHz xtal           │  DPS310 U4 (BOTTOM)     │
       │  D1 TVS     │  Decoupling halo         │  ADC RC LPFs            │
       │  U6 eFuse   │  USB-C J1                │  IMU vibration-iso pad  │
       │  +5V bulks  │  USBLC6 U5               │                          │
       │  AP2112K U2 │  microSD J2              │                          │
       │  +3V3 bulks │  SWD J9                  │                          │
       │             │                          │                          │
       └──────────────────────────────────────────────────────────────────┘
                              ↑
                Zone 4 (along the long edges)
                CONNECTORS — J3 telem, J5 GPS+mag, J10 CRSF,
                J11-J18 ESC pads. Edge placement → harness exit.
```

### 2.2 Per-zone reasoning

**Zone 1 — POWER (heat + inrush stage)**

Anchored at one short edge of the board, ~15 × 25 mm working area.

| Component | Position | Why |
|---|---|---|
| J4 Mauch power connector | Edge of Zone 1, harness exits the short edge | All input power enters here; no Zone-2/3 crossing |
| Q2 AO3401A reverse-polarity P-FET | First in series (closest to J4) | Blocks reverse polarity before any downstream silicon sees it |
| D1 SMAJ6.0A TVS | Across +5V_BEC_PROT to GND, ≤ 5 mm from Q2.D | TVS must clamp before the energy reaches U6; short-trace = low inductance = effective clamp |
| U6 TPS25940A eFuse | Centre of Zone 1, with thermal pour | Programmable inrush + OC + OVP + UVLO. Low dissipation (18 mW typ), but needs IN/OUT bypass caps close + IN/OUT pin pairs vias into 5V plane |
| C7 (dVdT 100 nF), C8 (IN 100 nF), C9 (OUT 1 µF) | ≤ 2 mm from respective U6 pins | Datasheet placement guidance — keep bypass close to pins |
| R4 (ILIM 42.2 kΩ), R5/R13 (FLT/PGOOD pull-ups), R7+R8 (UVLO divider), R9+R10 (OVP divider) | Adjacent to U6 | Configuration network — short connections to dedicated pins |
| C31 (1 µF +5V bypass), C32 (4.7 µF +5V bulk) | Between U6 OUT and U2 LDO IN | LDO input filtering |
| **U2 AP2112K-3.3 LDO + thermal pour ≥ 100 mm²** | **Centre of Zone 1, fanout to inner +5V power plane via 4×4 thermal-via array** | **THE thermal hotspot** — see THERMAL_BUDGET §2 |
| C17 (2.2 µF LDO output), C33 (1 µF +3V3 bypass), C34 (4.7 µF +3V3 bulk) | ≤ 5 mm from U2 OUT | LDO output filtering + decoupling |

Zone 1 is the heat + transient + high-current zone. Every other zone is
downstream of Zone 1's +3V3 output. Maximum physical separation from
Zone 3 (sensors).

**Zone 2 — MCU + USB + SDMMC (digital hub + USB-self-band aggressors)**

Centre of the board, ~25 × 25 mm working area.

| Component | Position | Why |
|---|---|---|
| U1 STM32H743VIT6 (LQFP-100) | Centre of Zone 2 | All buses + GPIO fan out; central placement minimizes worst-case trace length to peripherals |
| Y1 8 MHz crystal + C24/C25 18 pF load caps | ≤ 5 mm from PH0/PH1 (OSC_IN/OSC_OUT) | Crystal traces must be short + guard-ringed |
| 16× 100 nF decoupling caps (C11-C15, C19, C21, C23, C26, C41-C42, C51-C52, C61-C63) | One per VDD pin, ≤ 2 mm from respective pin | Standard MCU decoupling halo |
| C16 (4.7 µF MCU bulk), FB1 (ferrite bead VDDA), C18 (2.2 µF VDDA), C43 (2.2 µF VREF+) | Adjacent to U1 analog supply pins | Analog supply isolation |
| J1 USB-C connector | Edge of Zone 2 (long edge) | USB harness exit; short trace from J1.D+/D− through U5 to MCU PA11/PA12 |
| U5 USBLC6 ESD | Between J1 and U1, ≤ 8 mm from J1 | ESD protection must be the first thing the strike hits |
| J2 microSD (Hirose DM3AT) | Edge of Zone 2 opposite J1 | SDMMC1 to U1 PC8-PC12 + PD2; SDMMC is the highest-aggressor frequency on the board (12.5 MHz clock + 25 MHz fastest data) |
| R3 (NRST pullup), R11+R12 (I²C2 pullups) | Adjacent to U1 | Standard support |
| J9 SWD header (2×5 1.27 mm) | Edge of Zone 2 (preferably the long edge opposite J1) | SWD harness exit during bring-up |

Zone 2 is the digital hub. SDMMC is the primary 6k EMC aggressor; its
clock + USB clock + DShot harmonics all intersect in the 12 MHz USB FS
band (6k.1 finding). Co-locating SDMMC and USB inside Zone 2 is **counterintuitive**
but correct: it keeps the aggressor + victim physically close enough that
careful routing (short USB diff pair, guarded SDMMC clock, ground stitching)
contains the coupling within Zone 2. Spreading them to Zones 1 + 3 would
lengthen the aggressor traces + increase the EMI radius.

**Zone 3 — SENSORS / ANALOG (victims)**

Anchored at the short edge opposite Zone 1, ~15 × 25 mm working area.

| Component | Position | Why |
|---|---|---|
| U3 ICM-42688-P IMU | Centre of Zone 3, **TOP layer (F.Cu)**, with vibration-iso pad zone | Primary IMU; placement on TOP minimizes vibration coupling from board flex; far from heat (Zone 1) — IMU drift is temperature-sensitive |
| U4 DPS310 baro | Centre of Zone 3, **BOTTOM layer (B.Cu)** | Pressure sensor; bottom-layer placement keeps it shielded from board-top air currents (cleaner P readings) |
| C12 + C20 (IMU decoupling), C13 + C22 (baro decoupling) | ≤ 2 mm from respective sensor VDD pins | Standard sensor decoupling |
| ADC input network for VBAT/current (R-divider + C LPFs) | Zone 3 edge, near Mauch's analog signals coming from Zone 1 via SHORT bypass route through inner-layer signal | ADC reads must be clean; LPF response (6h shows -3dB at 1.59 kHz) means edge placement is fine |

Zone 3 design priorities:
1. **Maximum distance from Zone 1 heat sources**: temperature-dependent IMU bias drift (typical ICM-42688-P: ~0.05 °/s per °C). End-to-end separation keeps Zone 3 ambient close to enclosure ambient, not LDO-heated.
2. **No high-current traces through Zone 3**: SPI to IMU + I²C to baro are µA-class signals; routing must not run alongside ESC PWM (Zone 4 long-edge ESC pads) or SDMMC (Zone 2).
3. **IMU vibration-iso pad**: ~6×6 mm copper-free zone under U3 on every layer + slotted board edges (optional) to mechanically decouple the IMU from frame vibration. Final iso-pad geometry tuned in Phase 6 deep-pass.

**Zone 4 — CONNECTORS (along the long edges)**

Distributed along the two long edges:

| Connector | Edge placement | Why |
|---|---|---|
| J3 Telem UART (JST-GH 6P) | Long edge, near Zone 2 (MCU UART pins) | Short fan-out from U1 USART pins |
| J5 GPS+Mag (JST-GH 10P) | Long edge, near Zone 2 / Zone 3 boundary | Both UART (GPS) + I²C1 (external mag) go to U1 |
| J10 CRSF solder pads | Long edge, near Zone 2 (CRSF UART pins) | RC link to U1 USART |
| J11-J18 ESC1-8 solder pads | Long edge OPPOSITE the JST connectors, ≥ 10 mm from USB+IMU traces | 8 high-current PWM lines; ESC pads + harness exit on dedicated edge |

The dual-long-edge connector convention puts JST connectors on one long
edge (telem/GPS/CRSF — signal-level harnesses) and ESC pads on the opposite
long edge (high-current motor wires) — physical separation between
signal-level harnesses and motor-current paths.

---

## 3. Layer count recommendation — 6-layer

**Recommendation**: **6-layer**. Master adjudicates DECISIONS §8.

### 3.1 The engineering case

Four independent forces converge on 6-layer for v1:

**Force 1 — PDN integrity (the dispositive engineering reason)**

Phase 6a found PDN anti-resonance of 133 mΩ at 100 kHz on the +5V rail.
Root cause: on the 4-layer stackup, +3V3 and +5V share a single inner
power plane (Layer 3), which creates a shared-return path and a
high-impedance peak between the LDO's regulation bandwidth and the MCU's
high-frequency decoupling caps.

The 6-layer stackup provides **two independent inner power planes** (L3 =
+3V3, L4 = +5V) with their own dedicated GND references (L2 + L5). This
gives:

- Each rail has a sub-100 mΩ-at-1-MHz impedance across the full board
  (predicted; verifiable in Phase 6a re-sim with the new stackup).
- No shared-return current paths between digital MCU load and analog ADC
  bias network — cleaner ADC measurements.
- Sub-100 mΩ PDN means the bulk caps (C16, C32, C34) can actually
  deliver their rated transient-step current; on 4-layer the trace+plane
  impedance saturates that.

**Force 2 — thermal-pour effectiveness for the LDO**

Per THERMAL_BUDGET §2.3, the AP2112K LDO at 4-layer with copper pour has
θ_JA ≈ 80 °C/W → T_j = 98 °C at 50°C ambient → 13°C OVER SPEC.

6-layer adds an additional inner copper plane (4 oz, 140 µm) that the LDO's
thermal-pad vias can reach. Effectively doubles the heat-spreading inner
copper, lowering θ_JA to ≈ 50 °C/W. At that θ_JA the LDO sits at T_j ≈
79.8 °C at 50°C ambient → PASS with 5°C margin.

4-layer cannot meet the 50°C-ambient spec at the current LDO load. 6-layer
can. This is the dispositive thermal reason.

> **Architecture choice note**: the LDO topology itself was evaluated as an
> explicit architecture decision rather than inherited from Step 2 (master
> PR #57 review directive). See THERMAL_BUDGET §2.5 for the full
> evaluation of linear LDO vs buck switcher vs switcher+LDO hybrid. The
> recommendation is **retain the linear LDO** — the Mauch BEC is already
> our upstream switcher, putting an on-board switcher within 20-40 mm of
> the IMU would degrade sensor SNR more than it would save thermal margin,
> and the 6-layer + pour solution brings the LDO comfortably under spec
> anyway. Force 2 here is therefore *supportive* of the 6-layer call, not
> the dispositive reason (Force 1 PDN is). The 6-layer call stands
> independently.

**Force 3 — EMC reference-plane integrity for the USB / SDMMC / DShot
intersections**

Phase 6k found 4 harmonics > −40 dB in the USB FS self-band (12 MHz):
SDMMC clock at 12.5 MHz, USB FS NRZI at 12 MHz, DShot600 harmonics at
11.4 + 12.6 MHz. All in Zone 2 — close-proximity aggressors and victims.

The 6-layer stackup gives the USB diff pair routed on a top-layer signal
trace a **continuous L2 GND plane** directly underneath (no power-plane
splits to cross). On 4-layer with a mixed L3 power plane, the USB pair
routes over a plane that has +3V3 / +5V splits → split-induced ground-return
discontinuities → coupling spike at the discontinuity frequency.

6-layer gives both USB and SDMMC clean reference planes (L2 = GND mirror
for L1 top, L5 = GND mirror for L6 bottom). Predicted EMI reduction: the
4 critical harmonics drop ~6-10 dB on 6-layer vs 4-layer (rough estimate
from textbook reference-plane integrity literature, e.g. Hartal §3.6) —
still chamber-test items but with less margin pressure.

**Force 4 — Sai's reliability mandate + dimension freedom + cost reality**

Sai 2026-05-20: "it working 100% is the priority", "strong resilient
stuff that won't fail". The 4-layer was chosen as a cost optimization
for the 36×36 dense layout; the new rectangle has no cost-driven density
constraint. JLCPCB 6-layer at qty 5: ~$5-7/board (vs ~$2-3 for 4-layer)
→ delta ~$15-20 for a 5-board prototype run. Negligible against the
reliability priority.

Production reality check: the Holybro Pixhawk 6X (the autopilot novapcb
replaces functionally) is a 12-layer board. MatekH743 (our schematic
reference) is 4-layer because it's a cost-engineered hobby FC. The
6-layer choice for novapcb v1 puts it in the "serious autopilot" tier
without going to the 6X's full 12-layer expense.

### 3.2 What 4-layer would force us to give up

To stay on 4-layer + still meet the 50°C-ambient LDO thermal target,
we would need ONE of:
- Switch to a buck regulator (Knob 4 in THERMAL_BUDGET §2.3) — out of
  Step 3 scope; requires a Step 2 redesign + EMC re-analysis.
- Add a series Schottky diode upstream of the LDO to drop V_in (~0.4 V) —
  costs another part, adds another voltage drop, and the V_F drop just
  moves the heat to the Schottky (which is also SOT-23 thermal class).
- Add an external metal heat-spreader / heatsink attached to the LDO —
  not v1, mechanical complexity.

Each of these is a real engineering compromise that **6-layer obviates**.

### 3.3 What 6-layer costs

- ~$15-20 extra on a 5-board prototype run at JLCPCB.
- Slightly thicker board (1.6 mm same as 4-layer; the inner layers add
  ~0.5 mm to the stackup but JLCPCB normalizes to 1.6 mm).
- ~1 extra day of fab lead time at JLCPCB (5 days → 6 days).

None of these are blocking. The decision is unambiguous.

### 3.4 Falsifiable predictions if 6-layer chosen

- PDN impedance on +5V rail at 100 kHz: drops from 133 mΩ (4-layer) to
  ≤ 50 mΩ (6-layer dedicated +5V plane). Verifiable: Phase 6a PDN re-run
  with new stackup.
- LDO Tj at 50°C ambient with 100 mm² thermal pour over L4 +5V plane:
  drops from 98 °C (4-layer) to ≤ 80 °C (6-layer). Verifiable:
  Phase 6j re-run with Elmer-FEM on actual placement geometry.
- USB self-band EMI worst case: drops ~6-10 dB on the 4 critical
  harmonics. Verifiable in Phase 9.5 chamber.

If any of these falsifies on the actual layout, we escalate honestly.

### 3.5 Recommended stackup

JLCPCB **JLC06161H** 6-layer / 1.6 mm — outer 1 oz, inner 0.5 oz (the
real JLC standard; **earlier draft incorrectly said "4 oz inner" which
is NOT a JLC standard offering** — heavy copper is 2-layer only).

Layer assignment + dielectric details: see THERMAL_BUDGET §3.2 (real
JLC table) and CONTROLLED_IMPEDANCE.md (impedance-control prepreg
variant `JLC06161H-7628` for USB diff-pair Z ~ 90 Ω).

| Layer | Net | Reason |
|---|---|---|
| L1 (top, 1 oz) | Components + signal | F.Cu user layer |
| L2 (inner, 0.5 oz) | GND plane | Reference for L1 high-speed signals |
| L3 (inner, 0.5 oz) | +3V3 plane | Dedicated low-impedance MCU + sensor rail |
| L4 (inner, 0.5 oz) | +5V plane | Dedicated rail; LDO thermal-pad fan-out target |
| L5 (inner, 0.5 oz) | GND plane | Reference for L6 high-speed signals |
| L6 (bot, 1 oz) | Signal (sensors + low-speed) | B.Cu user layer; baro U4 lives here |

**Thermal-spreading note**: the corrected stackup (0.5 oz inner vs the
erroneous "4 oz" assumption) does NOT reduce thermal margin. Step 4
FEA re-run with the real anisotropic conductivities (k_xy = 33.5
W/m·K from the 0.131 mm total Cu, k_z = 0.316 W/m·K through-plane)
confirms LDO Tj = 69.8 °C, MCU Tj = 74.2 °C at 80×60 mm / h=5 /
50 °C — both PASS the 80 °C target. The design is convection-limited
(not heat-spreading-limited), so inner Cu weight doesn't change the
conclusion — see THERMAL_BUDGET §2 + Step 4 STEP4_REPORT for the
verification.

---

## 4. Board sizing — target envelope

Per Sai's directive, the board size is an OUTPUT of placement, not a
fixed input. The strategy below gives a **target envelope** so the
placement task knows the working area. Final dimensions emerge from the
place→sim→adjust iteration.

### 4.1 Target envelope

| Dimension | Target | Why |
|---|---|---|
| Length (long axis) | **50-55 mm** | Zone 1 (15-20 mm) + Zone 2 (25 mm) + Zone 3 (15 mm) + margins (~5 mm) |
| Width (short axis) | **35-40 mm** | MCU 14 mm + decoupling halo + connector long-edge real estate + margins |
| Area | **1750-2200 mm²** | ~35-70% more area than 36 × 36 baseline (1296 mm²) |
| Aspect ratio | **1.3:1 to 1.6:1** | Roomy rectangle; not extreme |

### 4.2 What sets the minimum length

The ESC connector strip is the long-axis constraint:

- 8 ESC pads × 3 mm pitch (~4 mm pitch with margin) = 24-32 mm
- USB-C + microSD on opposite long edge: each ~10 mm width
- These don't overlap, so each edge can carry its connector set independently

Long axis ≥ 50 mm gives Zone 1 + 2 + 3 enough room with ~3 mm gaps
between zones for ground-stitching vias.

### 4.3 What sets the minimum width

- STM32H743 LQFP-100 body: 14 × 14 mm. Decoupling halo + crystal +
  fan-out vias: ~22 × 22 mm working area in Zone 2.
- JST-GH connectors on long edge: each ~8-12 mm tall (perpendicular to
  long axis).
- Margins to mounting holes: ~3 mm edge inset.

Short axis ≥ 35 mm gives 22 mm Zone-2 MCU + ~10 mm connector real
estate + 3 mm margins.

### 4.4 Why the envelope is a range, not a single number

Final dimensions depend on:
- Phase 6j re-run with actual placement: if LDO pour needs > 100 mm²
  to hit the 80°C target, Zone 1 widens.
- IMU vibration-iso pad geometry from Phase 6 deep-pass: if the pad
  needs > 6×6 mm exclusion, Zone 3 widens.
- Routing channel widths from Phase 6b USB/DShot SI analysis: if any
  high-speed pair needs > 200 µm of separation from aggressors, zones
  push apart.

Step 3 P1+ iteration converges on the final number. Master can challenge
this envelope; it's a planning input not a commitment.

---

## 5. Mounting holes

### 5.1 Pattern — DECIDED 2026-05-23, RE-SCALED for 105×85 same day

**4× M3 corner-inset mounting holes** on the **105 × 85 mm v1.1 final board**,
**3.25 mm edge inset** (3.0 mm originally; bumped to 3.25 mm after discovery
that 5.5 mm GND-pad lands would violate the 0.5 mm edge-clearance rule at
3.0 mm inset — see `DECISIONS.md §2` for the geometry walk-through).

Positions (mm, pcbnew Y-down): (3.25, 3.25), (101.75, 3.25), (3.25, 81.75),
(101.75, 81.75).

**Centre-to-centre:**
- Long axis (X): 105 − 2×3.25 = **98.5 mm**
- Short axis (Y): 85 − 2×3.25 = **78.5 mm**

The Pixhawk-standard 30.5×30.5 M3 pattern is formally dropped for v1.1
(see `DECISIONS.md §2`). Per Sai 2026-05-23: no airframe size constraint,
105×85 final, new tray required (v1 is functional drop-in, not mechanical).

> ⚠ The 105 × 85 outline itself is under review — the thermal LOCK that
> sized this board was invalidated 2026-05-23. See
> `docs/THERMAL_ARCHITECTURE_DECISION.md` for sweep + Sai-pending architecture
> pick. The mounting pattern above is valid for the 105 × 85 case (Option A
> stays at 115×100 — different pattern needed if Sai picks A).

### 5.2 Hole specification

- M3 clearance (3.2 mm hole diameter; through-plated)
- GND-pad land around hole (5 mm pad diameter) — connects hole metal to
  chassis GND for ESD safety
- No copper exclusion zone in the inner power planes around the hole
  (the GND-pad land handles the chassis-to-GND tie)

### 5.3 Contingency — +2 mid-long-edge holes (sim-gated; placement reserves keep-out NOW)

**Sim-gated 4-vs-6** (master 2026-05-23): if Phase 6 vibration modeling (Task #10) shows the 98.5×78.5 mm hole spacing leaves excessive board flex amplitude at the IMU location, add 2 more M3 holes at the midpoints of the long edges (total 6 holes).

**Placement MUST reserve keep-out at the mid-edge positions NOW** so a sim-driven add doesn't trigger a re-place of B/A/D/H:

- Mid-long-edge keep-out positions: (3.25, 42.5) west mid and (101.75, 42.5) east mid
- Keep-out diameter: 8 mm (M3 + GND-pad land + tolerance)
- Subsystems B, A, D, H placement scripts MUST exclude these two circular regions

This makes the sim-driven 4→6 transition FREE (no re-place needed if Phase 6 says we need the extra two holes).

---

## 6. Place→sim→adjust methodology

Step 3 P1+ executes the placement work. The strategy below defines the
iteration loop the placement task follows.

### 6.1 Round 1 — initial placement per zoning (this PR's strategy)

1. Lock the board outline to a placement-target envelope (e.g. 52 × 38 mm).
2. Place mounting holes at the corners with ≥ 3 mm inset.
3. Place zone anchors:
   - Zone 1: J4 Mauch at one short edge; Q2 → D1 → U6 → U2 in linear
     power-flow order; bulks adjacent.
   - Zone 2: U1 LQFP-100 centred; Y1 ≤ 5 mm from OSC pins; USB-C J1 +
     USBLC6 U5 on one long edge near U1; microSD J2 on adjacent edge.
   - Zone 3: ICM-42688-P U3 centred on the opposite short edge (TOP);
     DPS310 U4 on bottom-layer counterpart; ADC LPFs in Zone 3 corner
     toward Mauch's analog signals.
   - Zone 4: JST-GH connectors along one long edge; ESC pads J11-J18
     along the opposite long edge.
4. Run KiCad DRC + first-pass airwire visualization (KiCad pcbnew Python API).
5. **Output**: `hardware/kicad/novapcb-layout-v2/` initial placement.

### 6.2 Round 2 — thermal sim + LDO copper pour tuning

1. Export Round-1 placement geometry → Elmer-FEM thermal input file.
2. Run Elmer-FEM with the THERMAL_BUDGET §4 boundary conditions (50°C
   ambient, h = 5 W/m²·K still-air convection).
3. Read U2 LDO T_j from the result. Pass criterion: **T_j ≤ 80°C at 50°C
   ambient**.
4. If FAIL:
   - Enlarge LDO thermal pour (target 100-150 mm² of L4 +5V plane around
     U2's thermal-pad via array).
   - If pour reaches Zone 2 boundary, push U2 toward Zone-1 edge to free
     pour area.
5. Re-export, re-run Elmer-FEM. Iterate until PASS.
6. **Output**: locked LDO placement + pour geometry.

### 6.3 Round 3 — SI / EMI spot-check

1. Export USB diff pair routing channel + SDMMC clock routing channel +
   nearest-DShot-pair routing channels.
2. Run OpenEMS spot-check on the worst-case USB pair geometry (now with
   the Z0-extraction fix from Phase 0.6 PR #56). Pass criterion:
   **Z_diff = 90 Ω ± 10 %** flat across 1.5-3 GHz band.
3. If USB pair shows splitting/coupling from SDMMC or DShot proximity,
   add ground-stitching vias or push the aggressor traces.
4. **Output**: locked SI-critical trace geometries.

### 6.4 Round-N escalation criteria

If Round 2 cannot bring T_j ≤ 80°C even with 150 mm² pour + maximum
practical inner-copper area: **ESCALATE TO SAI**. The buck-converter
question (THERMAL_BUDGET §2.3 Knob 4) becomes a real conversation, not
a deferred v2 item. Step 3 cannot fix a thermal headroom problem by
moving components alone if the underlying device dissipation exceeds
the package's heat-dissipation capacity at the chosen ambient.

If Round 3 USB / SDMMC SI cannot meet Z_diff or coupling targets even
with maximum routing-channel spacing: re-evaluate Zone 2 internal
layout (move SDMMC J2 to opposite edge from USB-C J1) before
escalating.

### 6.5 Acceptable round count

Convergence in ≤ 3 rounds is the target. > 3 rounds suggests the
strategy is wrong, not the geometry — go back to the strategy review
with master, not into round 4.

---

## 7. Out-of-scope (and why)

- **Final pin-level fanout / via pattern**: emerges from Round 1
  placement, not pre-committed in strategy.
- **Routing topology** (where each trace goes): Step 5 (route once) per
  the pivot plan, not Step 3.
- **Stiffener / mechanical mount details**: airframe-tray design, owned
  by Sai downstream.
- **Final BOM rev**: schematic + BOM are locked (Step 2 merge). Step 3
  consumes them; doesn't change them.
- **Phase 6.5 forum review prep**: schematic-rendering deferred to
  Phase 6.5 prep window per OPEN_QUESTIONS phase3-render-1; PCB strategy
  doesn't depend on it.

---

## 8. Falsifiable headline predictions (for master review)

If master adjudicates 6-layer + this strategy as the v1 build:

- **Layer count** (DECISIONS §8): 6-layer.
- **Predicted LDO T_j at 50°C ambient + 100 mm² L4 pour**: ≤ 80 °C
  (vs 98 °C on 4-layer). Verifiable in Step 3 P1+ Elmer-FEM.
- **Predicted +5V PDN impedance at 100 kHz on the new stackup**:
  ≤ 50 mΩ (vs 133 mΩ on 4-layer). Verifiable in Phase 6a re-sim.
- **Predicted USB-self-band harmonic EMI reduction**: 6-10 dB on the
  4 critical harmonics (USB FS 12 MHz, SDMMC 12.5 MHz, DShot 11.4/12.6
  MHz). Verifiable in Phase 9.5 chamber.
- **Predicted final board envelope**: 50-55 mm × 35-40 mm (1750-2200
  mm²; aspect ratio 1.3-1.6). Verifiable in Step 3 P1+ placement output.
- **Predicted mounting-hole pattern**: 4 × M3, corners, ≥ 3 mm edge inset.
  Verifiable in Step 3 P1+ placement output.

If any of these falsify in execution, we escalate honestly — the
strategy was wrong; pretending otherwise wastes layout cycles.

---

## 9. References

- `docs/CLAUDE.md` §6.2 (plan before expensive layout work)
- `docs/DECISIONS.md` §2 (form factor pivot), §8 (layer-count open),
  §10 (reliability mandate), §11 (Step 2 eFuse front-end)
- `docs/OPEN_QUESTIONS.md` pivot-2026-05-20 (Sai dimension freedom +
  layer-count open)
- `docs/SIMULATION_PLAN.md` §6a (PDN), §6j (thermal), §6k (EMC)
- `docs/THERMAL_BUDGET.md` (this PR's companion thermal-input prep)
- `sims/PHASE6_P0_RESULTS.md` (failure-mode evidence base)
- `tasks/phase-pivot-step3-p0.yaml` (this PR's task contract)
- Master 2026-05-21 directive (Step 3 planning PR scope)

---

**Status**: Step 3 P0 planning deliverable. Master adjudicates layer
count (DECISIONS §8) → dispatches Step 3 P1 placement-execution task.
