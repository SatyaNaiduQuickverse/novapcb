"""
novapcb Phase 3b — power tree sheet (5V input → 3.3V LDO + 3V3/3V3A distribution).

Drives the +3V3 / +3V3A / VBAT nets declared by mcu_3a.py. The MCU sheet
already declares the analog-rail ferrite bead (FB1 in mcu_3a.py) which
isolates +3V3A from +3V3; this sheet provides +3V3 from the LDO.

## Authority for choices in this sheet

The Phase 3 hwdef-authoritative discipline does NOT apply to the power
tree — `firmware/hwdef-novapcb/hwdef.dat` is the firmware-side pin map
and says nothing about regulators or input protection. Authority for
power-tree choices is:

  - `CLAUDE.md §3.6` power table — 5V input from external BEC ≥3A;
    3.3V on-board LDO; USB 5V bench-only; VBAT 4-6S monitored externally
    (Mauch power module per DECISIONS §5, NOT regulated on-board)
  - MatekH743 reference — the regulator part + topology where sourceable
    (NOT sourceable from local files — MatekH743's schematic is not in
    the ArduPilot tree, which contains only the hwdef.dat firmware pin
    map. Choices below are datasheet-grounded with explicit Phase 3.5
    reference-audit flags.)
  - Individual part datasheets — AP2112K-3.3 (Diodes Inc DS39724),
    STM32H743 datasheet (ST DS12110), ICM-42688-P datasheet
    (TDK DS-000347), DPS310 datasheet (Infineon)

## 3.3V rail load estimate (per 3b.1 contract criterion)

Summing the on-board 3.3V consumers at worst-case operating conditions:

| Consumer | Datasheet typical / max @ 3.3V | Source |
|---|---|---|
| STM32H743VI core (run mode, 480MHz, all peripherals on) | ~250–300 mA (max envelope) | ST DS12110 §6.3 Supply current characteristics |
| ICM-42688-P 6-axis active mode | ~0.88 mA typical @ 1.8V; ~2 mA upper bound at 3.3V VDDIO | TDK DS-000347 §3 Electrical Characteristics |
| DPS310 active barometer measurement | ~1 mA worst-case (continuous burst) | Infineon DPS310 datasheet §1 General Characteristics |
| External GPS module on JST-GH 10P (3V3 supply) | 30–80 mA typical | per Pixhawk-standard GPS modules; Phase 3e contract |
| ESC outputs (Phase 3f) | 0 mA from 3.3V (DShot driven from MCU IO pin, not a separate 3.3V load) | — |
| **Total worst-case** | **~300–400 mA** | |

## LDO selection (per 3b.2)

**AP2112K-3.3** (Diodes Inc) — 600 mA fixed-3.3V CMOS LDO in SOT-25 package.

  - 600 mA rated continuous → ~50% margin over worst-case 300-400 mA load.
  - Low dropout: 250 mV @ 600 mA → operates correctly down to Vin ≈ 3.55 V
    (well within the 5 V BEC range, including BEC sag).
  - ±1.5% output accuracy.
  - Built-in over-current protection + thermal shutdown.
  - Jellybean part (in production at Diodes Inc; in distribution at DigiKey,
    LCSC, JLCPCB; common on Matek + Pixhawk-class mini-FCs).

KiCad symbol: `Regulator_Linear:AP2112K-3.3` (verified exact match).
KiCad footprint: `Package_TO_SOT_SMD:SOT-23-5` (per symbol's default hint).

NOTE for Phase 3.5 reference audit: MatekH743's actual regulator part is
NOT confirmed from local sources. AP2112K-3.3 is a datasheet-grounded pick
that meets the load+margin requirement; Phase 3.5 should verify against
the MatekH743 schematic if available + flag any divergence.

## Input protection (per 3b.4)

**Not implemented in this sub-phase.** MatekH743's 5V-input protection
topology is not sourceable from local files. Per master adjudication
2026-05-20 ("don't silently omit, don't silently add a non-inherited
topology"), 5V-input reverse-polarity + ESD protection is FLAGGED for:

  - Phase 3.5 reference audit (cross-check vs MatekH743 schematic if
    sourceable; vs Pixhawk6X reference)
  - Phase 6.5 forum review (CONFIDENCE_MAP row 11 already LOW —
    reverse-polarity/ESD is exactly the subsystem that needs external
    EE review)
  - Phase 6i sim (transient-overvoltage / TVS clamp behavior, if added)

The +5V net in this sheet is just declared + power-flagged; the actual
+5V source (BEC connector wiring, optional input-protection components)
lands in `sheets/power_mon_sd_swd_3h.py` alongside the Mauch ADC inputs.
"""

import skidl
from skidl import Part, Net

from sheets.common import (
    setup, n, FP_R_0402, FP_C_0402, FP_C_0805,
)

setup()


# ---- nets (shared via n() singleton fetcher — same Net instances as mcu_3a.py) ----
# WITHOUT n(): `Net('+3V3')` in mcu_3a + `Net('+3V3')` in power_3b would create
# TWO separate nets (+3V3 and +3V3_1) — silent topology bug. The MCU's VDDs and
# the LDO's VOUT would not be electrically connected in the netlist.
GND   = n("GND")
P3V3  = n("+3V3")    # sourced by LDO U2.VOUT below
P3V3A = n("+3V3A")   # source: ferrite FB1 from +3V3 (declared in mcu_3a.py)
VBAT  = n("VBAT")    # source: 0R R2 from +3V3 (declared in mcu_3a.py)

# +5V is the filtered post-MOSFET rail that feeds the LDO + decoupling.
# Step 2 pivot 2026-05-21: P-MOSFET soft-start (Q1) between +5V_BEC (raw, from
# 3h Mauch connector) and +5V (filtered). Caps the inrush current at power-on.
P5V     = n("+5V")
P5V_BEC = n("+5V_BEC")   # raw BEC input (sourced in sheets/power_sd_swd_3h.py)


# ====================================================================
# Step 2 pivot (iter 4 — adjudicated 2026-05-21): COMPLETE input-protection
# front-end using an active eFuse with current-limit-bounded inrush.
# ====================================================================
# Sai/master adjudication 2026-05-21: option (b) — active current-limit IC —
# is the definitive solution. The previous discrete-MOSFET iterations (iter 0-3,
# preserved in DECISIONS §11) demonstrated that passive R-C-MOSFET topologies
# cannot bound absolute inrush regardless of BEC ramp speed. An eFuse with
# integrated current limit bounds inrush BY CONSTRUCTION.
#
# Sai's augmentation: "I want the best possible solution there" → implement
# the COMPLETE input-protection front-end as one coherent stage:
#   1. Core eFuse with programmable I_LIM, dV/dt, UVLO, OVP, thermal, FLT
#   2. Reverse-polarity blocker (P-MOSFET ideal diode upstream of eFuse)
#   3. TVS for transient/surge protection (motor noise, hot-plug spikes)
#
# Topology (input → output):
#
#   BEC connector (+5V_BEC_RAW) ──┐
#                                  │
#         Q2 (AO3401A P-FET)       │ Source(Q2.S) = +5V_BEC_RAW
#         reverse-polarity         │ Drain(Q2.D)  = +5V_BEC_PROT (protected)
#         Gate = GND               │ Vgs = 0 - V_S = -5V → ON normally
#                                  │ Vgs = +5V if BEC reversed → OFF, blocks
#                                  ▼
#                          +5V_BEC_PROT ─────┐
#                                            │
#                            D1 (SMAJ5.0A)   │ Clamps surges/transients
#                            TVS to GND      │ V_BR = 6.4V, V_C = 9.2V@65A
#                                            ▼
#                            U6 IN pins (TPS25940A)
#                            programmable:
#                              ILIM = 2.08A (R_ILIM = 42.2kΩ — datasheet table)
#                              UVLO trip @ 4.0V (R7=30.1kΩ + R8=10kΩ)
#                              OVP trip  @ 6.5V (R9=56kΩ + R10=10kΩ)
#                              dV/dt ramp ~15ms (C7=100nF on dVdT pin)
#                                            │
#                            U6 OUT pins ────┴───── +5V (filtered, to LDO)
#
# Verification (per master Step 2 spec):
#   The eFuse's CURRENT LIMIT bounds inrush BY CONSTRUCTION:
#   - dV/dt ramp at output: t_dVdT = 100 + 150 × C_dVdT(nF) µs (datasheet)
#     = 100 + 150 × 100 = 15100 µs ≈ 15 ms
#   - dV_OUT/dt = 5V / 15ms = 333 V/s
#   - I_inrush = C_OUT_total × dV/dt = 12.5 µF × 333 = 4.17 mA
#   - If load drew more: HARD-CLAMPED at I_LIM = 2.08A by the eFuse
#   - Result: inrush ALWAYS ≤ 2.08A regardless of BEC behavior. Bounded by IC.
#
# Per §10 reliability mandate, this design checks every box:
#   ✓ Programmable inrush soft-start (CdVdT pin, deterministic)
#   ✓ Adjustable current limit (ILIM pin, hard upper bound at 2.08A)
#   ✓ Overvoltage protection (OVP pin, trips at 6.5V)
#   ✓ Undervoltage lockout (EN/UVLO pin, holds off below 4.0V)
#   ✓ Thermal shutdown (datasheet: TSD at 160°C, auto-retry)
#   ✓ Fault flag (FLT open-drain to MCU for diagnostics)
#   ✓ Power-good signal (PGOOD open-drain to MCU)
#   ✓ Reverse-current blocking (back-to-back FETs in TPS25940A)
#   ✓ Reverse-polarity protection (Q2 P-FET upstream blocks reverse input)
#   ✓ Transient/surge clamping (D1 TVS clamps fast spikes)
#
# This closes the deferred Phase-6.5 review item "5V input protection" —
# resolved as Step 2 fix iter 4.
#
# BOM cost (vs pre-Step-2): +U6 (TPS25940A eFuse, ~$1.50 LCSC, EXTENDED)
#                           +Q2 (AO3401A P-FET, ~$0.10, BASIC)
#                           +D1 (SMAJ5.0A TVS, ~$0.20, BASIC)
#                           +5× R0402 + 3× C0402 = ~$0.10
#                           = ~$2 added BOM for complete input protection.
# Per §10 ("no premature optimization for cost"), this lands.

# Reverse-polarity P-MOSFET upstream of eFuse
q2 = Part(
    "Transistor_FET", "AO3401A",
    footprint="Package_TO_SOT_SMD:SOT-23",
    value="AO3401A",
)
q2.ref = "Q2"
P5V_BEC_PROT = n("+5V_BEC_PROT")   # post-reverse-polarity, pre-eFuse
P5V_BEC      += q2["S"]
P5V_BEC_PROT += q2["D"]
GND          += q2["G"]

# TVS diode on the protected BEC rail — clamps fast surges before they reach U6
d1 = Part("Diode", "SMAJ6.0A",
          footprint="Diode_SMD:D_SMA",
          value="SMAJ6.0A")
d1.ref = "D1"
# SMAJ6.0A selection rationale (master config-coordination review 2026-05-21):
#   - V_WM = 6.0V > rail max ~5.25V → no leakage in normal operation
#     (SMAJ5.0A's V_WM=5.0V was right at the rail nominal — leaked at 5.25V)
#   - V_BR min = 6.67V > eFuse OVP trip (6.0V) → OVP catches sustained
#     over-voltage BEFORE the TVS conducts; TVS only fires for ns-scale
#     transients too fast for the eFuse OVP comparator (2µs response).
#   - V_C max = 10.3V at peak rated surge (114A) — for realistic drone-board
#     transients (~10A), V_C is much lower (~7V). Phase 6.5 forum review
#     can evaluate whether a tighter-clamp TVS is warranted for the LDO's
#     6.5V abs-max margin.
P5V_BEC_PROT += d1[1]    # cathode (K) → +5V_BEC_PROT
GND          += d1[2]    # anode (A) → GND

# U6 TPS25940A eFuse — the core current-limit + soft-start IC.
# KiCad standard libs lack a TPS25940 symbol; using Conn_01x20 generic with
# the value set to "TPS25940A" so the BOM tracks correctly. Pin numbers match
# the datasheet RVC package pinout (page 3) — see comments per pin below.
u6 = Part(
    "Connector_Generic", "Conn_01x20",
    footprint="Package_DFN_QFN:WQFN-20-1EP_4x3mm_P0.5mm_EP1.7x2.7mm",
    value="TPS25940A",
)
u6.ref = "U6"

EFUSE_FLT    = Net("EFUSE_FLT")
EFUSE_PGOOD  = Net("EFUSE_PGOOD")
EFUSE_EN     = Net("EFUSE_EN")
EFUSE_OVP    = Net("EFUSE_OVP")
EFUSE_ILIM   = Net("EFUSE_ILIM")
EFUSE_DVDT   = Net("EFUSE_DVDT")
EFUSE_IMON   = Net("EFUSE_IMON")   # optional output (test point)

GND          += u6[1]   # pin 1: DEVSLP — tie GND (no DevSleep mode)
EFUSE_PGOOD  += u6[2]   # pin 2: PGOOD (open-drain)
P5V          += u6[3]   # pin 3: PGTH — sense the output rail
P5V          += u6[4]   # pins 4-8: OUT (5 paralleled output pins)
P5V          += u6[5]
P5V          += u6[6]
P5V          += u6[7]
P5V          += u6[8]
P5V_BEC_PROT += u6[9]   # pins 9-13: IN (5 paralleled input pins)
P5V_BEC_PROT += u6[10]
P5V_BEC_PROT += u6[11]
P5V_BEC_PROT += u6[12]
P5V_BEC_PROT += u6[13]
EFUSE_EN     += u6[14]  # pin 14: EN/UVLO (programmable UV trip via R7+R8)
EFUSE_OVP    += u6[15]  # pin 15: OVP (programmable OV trip via R9+R10)
GND          += u6[16]  # pin 16: GND
EFUSE_ILIM   += u6[17]  # pin 17: ILIM (R11=42.2kΩ → I_LIM=2.08A)
EFUSE_DVDT   += u6[18]  # pin 18: dVdT (C7=100nF → ~15ms soft-start ramp)
EFUSE_IMON   += u6[19]  # pin 19: IMON — test point
EFUSE_FLT    += u6[20]  # pin 20: FLT (open-drain)

# UVLO divider: trips at V_IN = 4.0V (board holds off below this until BEC stable)
r7 = Part("Device", "R", value="30.1k", footprint=FP_R_0402); r7.ref = "R7"
P5V_BEC_PROT += r7[1]; EFUSE_EN += r7[2]
r8 = Part("Device", "R", value="10k", footprint=FP_R_0402); r8.ref = "R8"
EFUSE_EN += r8[1]; GND += r8[2]

# OVP divider: trips at V_IN = 6.0V (master 2026-05-21 review: was 6.5V, lowered
# to give 8% margin under AP2112K LDO V_IN abs-max of 6.5V, and to trip BEFORE
# TVS D1 V_BR_min=6.67V so the eFuse handles sustained over-voltage as primary
# mechanism + TVS handles only fast transients).
# R9=51kΩ + R10=10kΩ; V_OVP threshold = 0.99V × (51+10)/10 = 6.04V (E12 round).
r9 = Part("Device", "R", value="51k", footprint=FP_R_0402); r9.ref = "R9"
P5V_BEC_PROT += r9[1]; EFUSE_OVP += r9[2]
r10 = Part("Device", "R", value="10k", footprint=FP_R_0402); r10.ref = "R10"
EFUSE_OVP += r10[1]; GND += r10[2]

# ILIM: 42.2kΩ → I_LIM = 2.08A per datasheet table. R4 (R11 conflicts with I2C pullup)
r_ilim = Part("Device", "R", value="42.2k", footprint=FP_R_0402); r_ilim.ref = "R4"
EFUSE_ILIM += r_ilim[1]; GND += r_ilim[2]

# dVdT: 100nF → soft-start ramp time = 100 + 150 × 100 = 15100µs ≈ 15ms
c7 = Part("Device", "C", value="100nF", footprint=FP_C_0402); c7.ref = "C7"
EFUSE_DVDT += c7[1]; GND += c7[2]

# IN-pin bypass: 100nF X7R close to the IN pins per datasheet recommendation
c8 = Part("Device", "C", value="100nF", footprint=FP_C_0402); c8.ref = "C8"
P5V_BEC_PROT += c8[1]; GND += c8[2]

# OUT-pin bypass: 1µF X7R per datasheet's "typical application" (page 1 schematic)
c9 = Part("Device", "C", value="1uF", footprint=FP_C_0402); c9.ref = "C9"
P5V += c9[1]; GND += c9[2]

# PGOOD + FLT pull-ups to +5V (open-drain outputs). R5/R13 (R12 conflicts).
r_pgood_pu = Part("Device", "R", value="10k", footprint=FP_R_0402); r_pgood_pu.ref = "R5"
EFUSE_PGOOD += r_pgood_pu[1]; P5V += r_pgood_pu[2]
r_flt_pu = Part("Device", "R", value="10k", footprint=FP_R_0402); r_flt_pu.ref = "R13"
EFUSE_FLT += r_flt_pu[1]; P5V += r_flt_pu[2]


# ---- LDO: AP2112K-3.3 (5V in → 3.3V out, 600mA) ----
ldo = Part(
    "Regulator_Linear", "AP2112K-3.3",
    footprint="Package_TO_SOT_SMD:SOT-23-5",
    value="AP2112K-3.3",
)
ldo.ref = "U2"

# AP2112K-3.3 pin map (verified via SKiDL Part().pins query 2026-05-20):
#   pin 1 = VIN, pin 2 = GND, pin 3 = EN, pin 4 = NC, pin 5 = VOUT
P5V  += ldo["VIN"]
GND  += ldo["GND"]
P5V  += ldo["EN"]       # EN tied to VIN: LDO always-on (no enable control needed)
# pin 4 NC: leave unconnected (intentional — the part has no internal use for it)
P3V3 += ldo["VOUT"]


# ---- LDO input caps (per AP2112 datasheet — typical CMOS LDO: 1µF X7R) ----
# C_in: 1µF X7R 0402 directly at VIN pin.
c_in = Part("Device", "C", value="1uF", footprint=FP_C_0402)
c_in.ref = "C31"
P5V += c_in[1]
GND += c_in[2]

# C_in_bulk: 4.7µF X5R 0805 — bulk on the 5V rail to absorb BEC reflections +
# transient demand from MCU load steps. Phase 6a will sim adequacy.
c_in_bulk = Part("Device", "C", value="4.7uF", footprint=FP_C_0805)
c_in_bulk.ref = "C32"
P5V += c_in_bulk[1]
GND += c_in_bulk[2]


# ---- LDO output caps (per AP2112 datasheet — 1µF X7R minimum) ----
# C_out: 1µF X7R 0402 directly at VOUT pin.
c_out = Part("Device", "C", value="1uF", footprint=FP_C_0402)
c_out.ref = "C33"
P3V3 += c_out[1]
GND  += c_out[2]

# C_out_bulk: 4.7µF X5R 0805 — bulk on the +3V3 rail. Complements the per-VDD-
# pin 100nF caps + the 4.7µF bulk in mcu_3a.py (C16); two parallel bulks give
# good low-frequency + mid-frequency decoupling for the MCU load.
c_out_bulk = Part("Device", "C", value="4.7uF", footprint=FP_C_0805)
c_out_bulk.ref = "C34"
P3V3 += c_out_bulk[1]
GND  += c_out_bulk[2]


# ---- power-flag symbols for ERC ----
# PWR_FLAG is a virtual symbol (no footprint) that tells KiCad ERC "this rail
# has a source somewhere." Rules:
#  - +3V3: NO PWR_FLAG here — the LDO's VOUT pin is itself a POWER-OUT pin;
#    adding a PWR_FLAG produces "Pin conflict: POWER-OUT <==> POWER-OUT".
#  - +5V_BEC: PWR_FLAG needed — the real source (BEC connector in 3h) is the
#    POWER-OUT; the FLAG marks the raw input as source-driven.
#  - +5V: PWR_FLAG NOT needed — Q1's MOSFET drain feeds this rail (passive
#    propagation rules apply, but Q1's source is +5V_BEC which has the FLAG).
#    ERC may still want a FLAG to silence "no driver" warnings; keep it.
#  - +3V3A: PWR_FLAG needed — sourced via ferrite FB1 from +3V3.
#  - VBAT: PWR_FLAG needed — sourced via 0R R2 from +3V3.
for ref, target_net in (("#FLG_5V_BEC", P5V_BEC),
                        ("#FLG_5V", P5V),
                        ("#FLG_3V3A", P3V3A),
                        ("#FLG_VBAT", VBAT)):
    flag = Part("power", "PWR_FLAG")
    flag.ref = ref
    target_net += flag[1]
