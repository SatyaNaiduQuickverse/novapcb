"""
novapcb Phase 3a — MCU sheet (STM32H743VITx + clock + reset + decoupling).

This module declares the MCU + its mandatory support circuitry.
Peripheral pin connections (SPI/I2C/UART/USB/ADC) are wired by
later-sheet modules (3b-3h); they `from sheets.mcu_3a import mcu` and
connect their nets to mcu['PIN_NAME'] or mcu[pin_number].

Datasheet references (no internet on novarobotics64 — facts cited from
the KiCad-symbol-encoded pin map + the published ST guidance summarized
in PHASE3_P0_REPORT.md):

  - STM32H743VI datasheet (ST DS12110), latest rev — pin map, electrical
    characteristics, decoupling guidance.
  - ST AN5354 / RM0433 — H7 hardware development: power scheme,
    decoupling network, crystal load caps, NRST + BOOT0 wiring.

Authoritative novapcb facts (grep'd from hwdef.dat):

  - hwdef.dat:5   MCU STM32H7xx STM32H743xx
  - hwdef.dat:8   APJ_BOARD_ID 5350
  - hwdef.dat:16  OSCILLATOR_HZ 8000000  (HSE crystal frequency)
  - hwdef.dat:18  FLASH_SIZE_KB 2048

H743 core power scheme: LDO (PWR_CR3_LDOEN). Inherited from MatekH743 —
neither MatekH743/hwdef.dat nor MatekH743-bdshot/hwdef.dat defines
SMPS_PWR or SMPS_EXT, so they fall through to the LDO default in
hwdef/common/stm32h7_mcuconf.h:93. LDO mode requires the 2.2 uF X7R
caps on VCAP1 + VCAP2 (per H743 datasheet §6.1.6 Power supplies).
"""

import skidl
from skidl import Part, Net

from sheets.common import (
    setup, FP_R_0402, FP_C_0402, FP_C_0805, FP_FB_0402, FP_XTAL_3225,
)

setup()


# ---- shared power nets (referenced by all sheets) ----
GND   = Net("GND")
P3V3  = Net("+3V3")    # main digital supply rail
P3V3A = Net("+3V3A")   # analog supply rail, post-ferrite from +3V3
VBAT  = Net("VBAT")    # backup-domain supply (tied to +3V3 via 0R for v1, no battery)


# ---- MCU part ----
# Symbol: MCU_ST_STM32H7:STM32H743VITx (LQFP-100, 14x14, 0.5mm pitch).
# Footprint: Package_QFP:LQFP-100_14x14mm_P0.5mm (matches Phase 2.5 P0.4 inventory).
mcu = Part(
    "MCU_ST_STM32H7", "STM32H743VITx",
    footprint="Package_QFP:LQFP-100_14x14mm_P0.5mm",
    value="STM32H743VITx",
)
mcu.ref = "U1"

# Power-pin connections (cited from KiCad-symbol pin map; grep'd 2026-05-20):
#   VDD pins: 11, 27, 50, 75, 100              (5 digital supply pins)
#   VSS pins: 10, 26, 49, 74, 99               (5 digital ground pins)
#   VDDA: 21, VSSA: 19, VREF+: 20              (analog island)
#   VCAP: 48, 73                               (LDO core capacitor pins)
#   VBAT: 6                                    (backup domain supply)
#   NRST: 14, BOOT0: 94                        (reset + boot select)
#   HSE: PH0 (12) = OSC_IN, PH1 (13) = OSC_OUT  (8 MHz HSE crystal)
mcu_vdd_pins = [11, 27, 50, 75, 100]
mcu_vss_pins = [10, 26, 49, 74, 99]
for p in mcu_vdd_pins:
    P3V3 += mcu[p]
for p in mcu_vss_pins:
    GND += mcu[p]
P3V3A += mcu["VDDA"]
GND   += mcu["VSSA"]
VBAT  += mcu["VBAT"]

# VCAP nets (one cap each to GND; LDO core caps per H743 datasheet §6.1.6).
VCAP1 = Net("VCAP1"); VCAP1 += mcu[48]
VCAP2 = Net("VCAP2"); VCAP2 += mcu[73]

# VREF+ rail (analog reference). Tied to +3V3A via 100nF + 1uF filter;
# some designs jumper VREF+ directly to VDDA for simplicity. We expose
# VREF as its own net + decouple it; 3.5 reference-design audit can revise.
VREF = Net("VREF_P"); VREF += mcu["VREF+"]


# ---- decoupling network: one 100nF per VDD pin ----
# Per H743 datasheet table "Decoupling capacitors" + AN5354 §3.3.
# 100nF X7R 0402 placed within 5 mm of each VDD pin at Phase 4 layout.
for i, vdd_pin in enumerate(mcu_vdd_pins, start=1):
    c = Part("Device", "C", value="100nF",
             footprint=FP_C_0402)
    c.ref = f"C{10 + i}"   # C11..C15 by index
    P3V3 += c[1]
    GND  += c[2]

# Bulk decoupling for digital VDD plane.
c_bulk = Part("Device", "C", value="4.7uF",
              footprint=FP_C_0805)
c_bulk.ref = "C16"
P3V3 += c_bulk[1]
GND  += c_bulk[2]


# ---- VCAP1 + VCAP2 caps (LDO mode, mandatory) ----
# 2.2 uF X7R 0402 each, per H743 datasheet §6.1.6 Power supplies (LDO).
for i, vcap_net in enumerate([VCAP1, VCAP2], start=1):
    c = Part("Device", "C", value="2.2uF",
             footprint=FP_C_0402)
    c.ref = f"C{17 + i - 1}"   # C17, C18
    vcap_net += c[1]
    GND     += c[2]


# ---- VDDA / VREF analog filtering ----
# Ferrite bead from +3V3 to +3V3A. Standard pattern per AN5354 §3.4.
fb_vdda = Part("Device", "FerriteBead", value="600R@100MHz",
               footprint=FP_FB_0402)
fb_vdda.ref = "FB1"
P3V3   += fb_vdda[1]
P3V3A  += fb_vdda[2]

# +3V3A decoupling: 100nF + 1uF in parallel, close to VDDA pin.
c_vdda_100n = Part("Device", "C", value="100nF",
                   footprint=FP_C_0402)
c_vdda_100n.ref = "C19"
P3V3A += c_vdda_100n[1]
GND   += c_vdda_100n[2]

c_vdda_1u = Part("Device", "C", value="1uF",
                 footprint=FP_C_0402)
c_vdda_1u.ref = "C20"
P3V3A += c_vdda_1u[1]
GND   += c_vdda_1u[2]

# VREF+ decoupling: 100nF + 1uF in parallel, per H743 datasheet ADC section.
c_vref_100n = Part("Device", "C", value="100nF",
                   footprint=FP_C_0402)
c_vref_100n.ref = "C21"
VREF += c_vref_100n[1]
GND  += c_vref_100n[2]

c_vref_1u = Part("Device", "C", value="1uF",
                 footprint=FP_C_0402)
c_vref_1u.ref = "C22"
VREF += c_vref_1u[1]
GND  += c_vref_1u[2]

# VREF+ tie: connect VREF rail to +3V3A through a 0R link (DNP-able).
# Phase 3.5 reference audit may swap this for a discrete reference IC if
# ADC accuracy demands it; default for novapcb v1 is to share +3V3A.
r_vref_tie = Part("Device", "R", value="0R",
                  footprint=FP_R_0402)
r_vref_tie.ref = "R1"
P3V3A += r_vref_tie[1]
VREF  += r_vref_tie[2]


# ---- VBAT handling (no backup battery on novapcb v1) ----
# Tie VBAT to +3V3 via 0R link (DNP-able if a real battery lands at v2).
# 100nF decoupling on VBAT as per datasheet recommendation.
r_vbat_tie = Part("Device", "R", value="0R",
                  footprint=FP_R_0402)
r_vbat_tie.ref = "R2"
P3V3 += r_vbat_tie[1]
VBAT += r_vbat_tie[2]

c_vbat = Part("Device", "C", value="100nF",
              footprint=FP_C_0402)
c_vbat.ref = "C23"
VBAT += c_vbat[1]
GND  += c_vbat[2]


# ---- HSE crystal (8 MHz per hwdef.dat:16 OSCILLATOR_HZ) ----
# 4-pin SMD crystal (Crystal_SMD_3225-4Pin_3.2x2.5mm). Load caps sized
# for typical 12 pF crystal load capacitance: C_load = 2*(CL - C_stray),
# C_stray ~3 pF -> C_load ~18 pF. Use C0G 0402 for low temperature drift.
xtal = Part("Device", "Crystal_GND24", value="8MHz",
            footprint=FP_XTAL_3225)
xtal.ref = "Y1"

HSE_IN  = Net("HSE_IN"); HSE_IN  += mcu["PH0"]
HSE_OUT = Net("HSE_OUT"); HSE_OUT += mcu["PH1"]
HSE_IN  += xtal[1]
HSE_OUT += xtal[3]
GND     += xtal[2]   # case-ground pins on 4-pin crystal
GND     += xtal[4]

c_xtal1 = Part("Device", "C", value="18pF",
               footprint=FP_C_0402)
c_xtal1.ref = "C24"
HSE_IN += c_xtal1[1]
GND    += c_xtal1[2]

c_xtal2 = Part("Device", "C", value="18pF",
               footprint=FP_C_0402)
c_xtal2.ref = "C25"
HSE_OUT += c_xtal2[1]
GND     += c_xtal2[2]


# ---- NRST reset circuit ----
# 100nF decoupling cap to GND; STM32 has internal pull-up so no external
# pull-up needed. No reset button on novapcb v1 (SWD reset suffices).
NRST = Net("NRST"); NRST += mcu["NRST"]
c_nrst = Part("Device", "C", value="100nF",
              footprint=FP_C_0402)
c_nrst.ref = "C26"
NRST += c_nrst[1]
GND  += c_nrst[2]


# ---- BOOT0 — boot from main flash by default ----
# 10k pull-down to GND. A test point or jumper to +3V3 can be added at
# Phase 4 for DFU bootloader access; not in v1 schematic.
BOOT0 = Net("BOOT0"); BOOT0 += mcu["BOOT0"]
r_boot = Part("Device", "R", value="10k",
              footprint=FP_R_0402)
r_boot.ref = "R3"
BOOT0 += r_boot[1]
GND   += r_boot[2]


# Power-driving for the +3V3 / +3V3A / GND rails is provided by the Phase 3b
# power-tree sheet (LDO output drives +3V3). In 3a alone, ERC will warn
# "Input Power pin not driven by any Output Power pins" for these rails;
# expected at this sub-phase. PWR_FLAGs intentionally omitted here — they
# belong in 3b where the real source lives, not as virtual placeholders.
