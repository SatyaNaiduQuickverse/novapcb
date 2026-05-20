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

# +5V is new in 3b — the BEC input rail. Source: 3h power-monitor sheet
# (BEC connector lands there alongside the Mauch ADC inputs).
P5V   = n("+5V")


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
#    adding a PWR_FLAG produces "Pin conflict: POWER-OUT <==> POWER-OUT"
#    (the two-power-source error).
#  - +5V: PWR_FLAG needed — the real source (BEC connector) is in 3h, so 3b's
#    ERC view doesn't see a driver yet.
#  - +3V3A: PWR_FLAG needed — sourced via ferrite FB1 from +3V3; passives
#    don't propagate the POWER-OUT attribute through ERC's net analysis.
#  - VBAT: PWR_FLAG needed — sourced via 0R R2 from +3V3; same reason.
# (The empty-footprint handler in sheets/common.py silently accepts PWR_FLAG.)
for ref, target_net in (("#FLG_5V", P5V),
                        ("#FLG_3V3A", P3V3A),
                        ("#FLG_VBAT", VBAT)):
    flag = Part("power", "PWR_FLAG")
    flag.ref = ref
    target_net += flag[1]
