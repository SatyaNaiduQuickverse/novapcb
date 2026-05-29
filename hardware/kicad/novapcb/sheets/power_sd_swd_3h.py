"""
novapcb Phase 3h — power-monitor + microSD + SWD + mounting-holes sheet.

The LAST Phase 3 schematic sheet. Four small blocks:

  1. **Power-monitor block** — JST-GH 6-pin connector for the external Mauch
     HS-200-LV (per DECISIONS §5 + Phase 2g). +5V BEC supply from the
     module's onboard BEC into novapcb's +5V rail; VBAT-analog + current-
     analog into MCU ADC PC0/PC1 (per hwdef.dat:68-69 + Phase 2g lock).
     RC filter on each ADC line to reject ESC switching noise.

  2. **microSD block** — Hirose DM3AT-SF-PEJM5 push-push socket
     (Phase 2.5 P0.4 inventory). SDMMC1 4-bit mode wired per hwdef.dat:
     183-188 (PC8-12 + PD2). 47 kΩ pull-ups on CMD + D0-D3 per SD spec.
     Card-detect mechanical switch pin = Phase 4 layout testpoint
     (Phase 2h fork-2 left this hwdef-unassigned).

  3. **SWD block** — ARM Cortex Debug 2x5 1.27 mm header (J9 per Phase
     2.5 inventory). Pinout per the ARM standard + hwdef.dat:32-33
     (PA13 SWDIO, PA14 SWCLK). NRST wired to MCU's NRST net.

  4. **Mounting holes** — 4× M3 holes at the Pixhawk-standard 30.5×30.5
     mm c-to-c pattern (per CLAUDE.md §1 + DECISIONS §2 disambiguated
     Phase 2.5). Pads tied to GND for EMC.

## Authority for this sheet

  - `firmware/hwdef-novapcb/hwdef.dat` — AUTHORITATIVE for ADC + SDMMC1 +
    SWD pin map. Cited inline below.
  - Pixhawk Connector Standard DS-009 (pixhawk/Pixhawk-Standards GitHub)
    — JST-GH 6-pin power-module connector pinout (same canonical source
    as Phase 3e GPS 10P).
  - ARM Cortex Debug Connector — 2x5 1.27 mm standard pinout (cited via
    KiCad's `Conn_ARM_JTAG_SWD_10` symbol).
  - Infineon Mauch HS-200-LV product page — module spec (200 A HS via
    Allegro ACS-250U; 9:1 LV divider for ≤6S; supplies its own +5V BEC).
    NOTE: Mauch HS-200-LV ships with a DF-13 6-pin connector; novapcb v1
    uses a JST-GH 6-pin per DECISIONS §7, requiring Mauch product 065
    "Power-Cube output cable JST-GH/6p" or a user-fabricated DF-13→JST-GH
    adapter. Documented + flagged as a v1 user-side consideration.
  - SD Association SDMMC 4-bit spec — pull-up convention on CMD + D0-D3.

## hwdef.dat-cited authoritative pin map

| Net | MCU pin | Source line |
|---|---|---|
| BATT_VOLTAGE_SENS | PC0 | 68: `PC0 BATT_VOLTAGE_SENS ADC1 SCALE(1)` |
| BATT_CURRENT_SENS | PC1 | 69: `PC1 BATT_CURRENT_SENS ADC1 SCALE(1)` |
| HAL_BATT_MONITOR | 4 (analog VBAT+CURR) | 74 |
| HAL_BATT_VOLT_PIN | 10 | 75 |
| HAL_BATT_CURR_PIN | 11 | 76 |
| HAL_BATT_VOLT_SCALE | 9.0 (Mauch HS-200-LV) | 91 (Phase 2g) |
| HAL_BATT_CURR_SCALE | 60.6 (Mauch HS-200-LV) | 92 (Phase 2g) |
| SDMMC1_D0 | PC8 | 183 |
| SDMMC1_D1 | PC9 | 184 |
| SDMMC1_D2 | PC10 | 185 |
| SDMMC1_D3 | PC11 | 186 |
| SDMMC1_CK | PC12 | 187 |
| SDMMC1_CMD | PD2 | 188 |
| JTMS-SWDIO | PA13 | 32 |
| JTCK-SWCLK | PA14 | 33 |
| NRST | (MCU NRST pin, shared with mcu_3a) | mcu_3a.py via Net.fetch("NRST") |

## Decisions resolved this sheet

### Mauch connector (mauch-connector fork)

**JST-GH 6-pin (SM06B-GHS-TB)** per DECISIONS §7 + Pixhawk Connector
Standard DS-009. Pin order:

| Pin | Signal | Voltage | Wiring |
|---|---|---|---|
| 1 | VCC | +5V (Mauch BEC out) | → novapcb +5V rail |
| 2 | VCC | +5V (paralleled for current) | → novapcb +5V rail |
| 3 | Battery voltage analog | 0-3.3V (post 9:1 divider from VBAT) | → ADC PC0 via 1k+100nF filter |
| 4 | Battery current analog | 0-3.3V (Hall sensor + offset shift) | → ADC PC1 via 1k+100nF filter |
| 5 | GND | — | GND |
| 6 | GND | — (paralleled for current return) | GND |

Note: **Mauch HS-200-LV ships with DF-13 6-pin** factory cable. User
buys Mauch product 065 "Power-Cube output cable JST-GH/6p" OR fabricates
a DF-13→JST-GH adapter pigtail. Both routes are common in the
Pixhawk-class community. This is the standard Pixhawk-vs-Matek connector
choice; flagged for user docs (Phase 9 bring-up notes).

### ADC filter (adc-filter fork)

**Series 1 kΩ + 100 nF X7R to GND** on each ADC input (VBAT + CURRENT).
Standard low-pass filter pattern:
  - Cutoff frequency: 1/(2π × 1 kΩ × 100 nF) ≈ 1.6 kHz
  - Rejects ESC switching noise (DShot600 = 600 kHz, ESC PWM = 25-50 kHz
    typically)
  - Pass-band fast enough to track battery dynamics (battery state
    changes are sub-Hz; 1.6 kHz pass-band is comfortably above)
  - 1 kΩ source impedance is acceptable for STM32H743 ADC's 100 MΩ input
    impedance + minimum acquisition time (Phase 6h sim validates settling)

MatekH743's exact filter values not sourceable from local files (only
firmware hwdef accessible). Datasheet-grounded RC; Phase 6h sim refines
+ Phase 3.5 reference audit cross-checks vs MatekH743 if sourceable.

### SDMMC pull-ups (sdmmc-pullups fork)

**External 47 kΩ pull-ups** on CMD + D0-D3 (5 pull-ups). Per SD
Association SDMMC 4-bit spec + Phase 2h INTERFACE_CONTRACT note ("No
PULL directive in novapcb or MatekH743; external pull-ups belong on the
board"). MatekH743's exact value not sourceable locally; 47 kΩ is the
standard SD-spec value (range 10-100 kΩ, 47 kΩ is the common middle).

CLK does NOT need a pull-up (driven by MCU; idle state set by SDMMC
controller). D3 doubles as the SPI-mode chip-select line; in SD bus
mode it just needs the pull-up like other data lines.

### Mounting holes — GND-tied

**4× M3 mounting holes at 30.5 × 30.5 mm c-to-c** per Phase 2.5 P1.1
spec (board outline 36 × 36 mm, holes inset 2.75 mm from each edge).
**Mounting-hole pads tied to GND** for EMC drain — standard mini-FC
practice (matches MatekH743 reference + Pixhawk-class convention).
Trade-off vs isolated mounting:
  - GND-tied (chosen): EMC drain through mechanical attachment; airframe
    becomes part of the EMC return path. Standard mini-FC pattern.
  - Isolated: avoids ground loops via airframe (preferred for some
    high-sensitivity analog work, e.g. IMU isolation boards). Not the
    novapcb v1 target — v2 might revisit when isolated-IMU board lands.

## What this sheet does NOT do

  - Phase 4 PCB layout — exact ADC filter cap placement (close to ADC pin),
    SDMMC trace routing + matched lengths, SWD header placement on
    bottom layer per Phase 2.5 placement-fit, mounting-hole exact
    positions (already specified: corners at (2.75, 2.75), (33.25, 2.75),
    (2.75, 33.25), (33.25, 33.25))
  - Phase 6h sim — ADC settling/accuracy under switching noise
  - Phase 6f sim — SDMMC SI at clock rate (default 12.5 MHz; SDR25 target
    50 MHz pending sim)
  - Phase 9 bench — full Mauch HS-200-LV calibration + .bin log write/read

After this sheet, ALL hwdef.dat peripherals have a schematic sheet.
Phase 3.5 reference audit (cross-check whole schematic vs MatekH743 +
Pixhawk references) and Phase 3-exit (re-audit + assembled-netlist
check, per Phase 2-exit pattern) come next.
"""

import skidl
from skidl import Part, Net

from sheets.common import setup, n, FP_R_0402, FP_C_0402
from sheets.mcu_3a import mcu

setup()


# ---- shared nets ----
GND  = n("GND")
P3V3 = n("+3V3")
P5V  = n("+5V")          # post-MOSFET filtered 5V (feeds LDO + decoupling) — Step 2 pivot 2026-05-21
P5V_BEC = n("+5V_BEC")   # raw 5V (post-OR-ing in 3b) → input to eFuse front-end
# v1.1 redundancy re-spin: J4 now feeds +5V_BEC_A (post-J4, pre-OR-ing FET);
# J19 (new 2nd input) feeds +5V_BEC_B. The LM74700 OR-ing in power_3b.py
# combines both into +5V_BEC.
P5V_BEC_A = n("+5V_BEC_A")
P5V_BEC_B = n("+5V_BEC_B")
NRST = n("NRST")   # shared with mcu_3a.py (Net.fetch returns existing)


# =====================================================================
# Block 1: Power-monitor (Mauch HS-200-LV via JST-GH 6P)
# =====================================================================

# MCU side ADC pins (hwdef.dat:68-69).
BATT_V_SENSE = n("BATT_VOLTAGE_SENS")
BATT_I_SENSE = n("BATT_CURRENT_SENS")
BATT_V_SENSE += mcu["PC0"]
BATT_I_SENSE += mcu["PC1"]

# Mauch connector — JST-GH 6P per DECISIONS §7 + Pixhawk DS-009.
# Pre-filter analog lines (connector side):
MAUCH_VBAT_PRE = Net("MAUCH_VBAT_PRE")
MAUCH_CURR_PRE = Net("MAUCH_CURR_PRE")

mauch_conn = Part(
    "Connector_Generic", "Conn_01x06",
    footprint="Connector_JST:JST_GH_SM06B-GHS-TB_1x06-1MP_P1.25mm_Horizontal",
    value="MAUCH_6P",
)
mauch_conn.ref = "J4"   # J4 reserved per Phase 2.5 sketch (power 6P)

# Pin map per Pixhawk DS-009 6-pin power-module standard.
# v1.1 redundancy re-spin 2026-05-21: J4 now feeds +5V_BEC_A (input A to
# the LM74700 OR-ing in power_3b.py). The OR-ing FET drain feeds +5V_BEC
# (shared) which feeds the existing Q2/D1/U6 eFuse front-end downstream.
P5V_BEC_A       += mauch_conn[1]   # VCC (+5V_BEC_A raw from Mauch BEC, input A)
P5V_BEC_A       += mauch_conn[2]   # VCC (paralleled)
MAUCH_VBAT_PRE  += mauch_conn[3]   # VBAT analog (post 9:1 divider)
MAUCH_CURR_PRE  += mauch_conn[4]   # Current analog (Hall sensor)
GND             += mauch_conn[5]   # GND
GND             += mauch_conn[6]   # GND (paralleled)


# =====================================================================
# Block 1b (v1.1): 2nd power-monitor connector — J19, mirror of J4
# =====================================================================
# Per docs/RESPIN_SCOPE.md + master adjudication 2026-05-21:
#   - 2nd JST-GH 6P input for power-input redundancy
#   - Same pinout as J4 (Pixhawk DS-009)
#   - VCC feeds +5V_BEC_B (input B to LM74700 OR-ing in power_3b.py)
#   - Independent VBAT2/CURR2 ADC sense → MCU PC2/PC3 (free per hwdef
#     pin survey — PC2 = ADC123_IN12, PC3 = ADC123_IN13). hwdef revision
#     adds these as BATT2_VOLTAGE_SENS / BATT2_CURRENT_SENS lines.

BATT2_V_SENSE = n("BATT2_VOLTAGE_SENS")
BATT2_I_SENSE = n("BATT2_CURRENT_SENS")
BATT2_V_SENSE += mcu["PC2_C"]   # STM32H743 "direct" PC2 (KiCad symbol pin name)
BATT2_I_SENSE += mcu["PC3_C"]   # STM32H743 "direct" PC3 (KiCad symbol pin name)

MAUCH2_VBAT_PRE = Net("MAUCH2_VBAT_PRE")
MAUCH2_CURR_PRE = Net("MAUCH2_CURR_PRE")

mauch2_conn = Part(
    "Connector_Generic", "Conn_01x06",
    footprint="Connector_JST:JST_GH_SM06B-GHS-TB_1x06-1MP_P1.25mm_Horizontal",
    value="MAUCH2_6P",
)
mauch2_conn.ref = "J19"

P5V_BEC_B       += mauch2_conn[1]   # VCC (+5V_BEC_B raw, input B)
P5V_BEC_B       += mauch2_conn[2]   # VCC (paralleled)
MAUCH2_VBAT_PRE += mauch2_conn[3]   # VBAT analog
MAUCH2_CURR_PRE += mauch2_conn[4]   # Current analog
GND             += mauch2_conn[5]   # GND
GND             += mauch2_conn[6]   # GND (paralleled)

# ADC RC filters for J19 — identical topology to J4.
r_vbat2 = Part("Device", "R", value="1k", footprint=FP_R_0402)
r_vbat2.ref = "R43"
MAUCH2_VBAT_PRE += r_vbat2[1]
BATT2_V_SENSE   += r_vbat2[2]

c_vbat2 = Part("Device", "C", value="100nF", footprint=FP_C_0402)
c_vbat2.ref = "C81"
BATT2_V_SENSE += c_vbat2[1]
GND           += c_vbat2[2]

r_curr2 = Part("Device", "R", value="1k", footprint=FP_R_0402)
r_curr2.ref = "R44"
MAUCH2_CURR_PRE += r_curr2[1]
BATT2_I_SENSE   += r_curr2[2]

c_curr2 = Part("Device", "C", value="100nF", footprint=FP_C_0402)
c_curr2.ref = "C82"
BATT2_I_SENSE += c_curr2[1]
GND           += c_curr2[2]


# ---- ADC RC filters on VBAT + CURRENT (1 kΩ + 100 nF, ~1.6 kHz LPF) ----

# VBAT filter: connector → 1k series R → MCU PC0 + 100nF to GND
r_vbat = Part("Device", "R", value="1k", footprint=FP_R_0402)
r_vbat.ref = "R41"
MAUCH_VBAT_PRE += r_vbat[1]
BATT_V_SENSE   += r_vbat[2]

c_vbat = Part("Device", "C", value="100nF", footprint=FP_C_0402)
c_vbat.ref = "C61"
BATT_V_SENSE += c_vbat[1]
GND          += c_vbat[2]

# CURRENT filter: same topology
r_curr = Part("Device", "R", value="1k", footprint=FP_R_0402)
r_curr.ref = "R42"
MAUCH_CURR_PRE += r_curr[1]
BATT_I_SENSE   += r_curr[2]

c_curr = Part("Device", "C", value="100nF", footprint=FP_C_0402)
c_curr.ref = "C62"
BATT_I_SENSE += c_curr[1]
GND          += c_curr[2]


# =====================================================================
# Block 2: microSD (Hirose DM3AT-SF-PEJM5 push-push, SDMMC1 4-bit)
# =====================================================================

# Shared SDMMC nets — fetch via n() for the cross-sheet discipline,
# though SDMMC pins live only in this sheet + MCU side.
SDMMC1_CLK = n("SDMMC1_CLK")
SDMMC1_CMD = n("SDMMC1_CMD")
SDMMC1_D0  = n("SDMMC1_D0")
SDMMC1_D1  = n("SDMMC1_D1")
SDMMC1_D2  = n("SDMMC1_D2")
SDMMC1_D3  = n("SDMMC1_D3")

# MCU side (hwdef.dat:183-188)
SDMMC1_D0  += mcu["PC8"]
SDMMC1_D1  += mcu["PC9"]
SDMMC1_D2  += mcu["PC10"]
SDMMC1_D3  += mcu["PC11"]
SDMMC1_CLK += mcu["PC12"]
SDMMC1_CMD += mcu["PD2"]

# microSD socket symbol: Connector:SD_Card_Device (9-pin SD bus map)
sd = Part(
    "Connector", "SD_Card_Device",
    footprint="Connector_Card:microSD_HC_Hirose_DM3AT-SF-PEJM5",
    value="microSD_DM3AT",
)
sd.ref = "J2"   # J2 reserved per Phase 2.5 sketch (microSD)

# Pin map (SD bus, 4-bit):
SDMMC1_D3  += sd[1]   # CD/DAT3 (in SD bus mode, this is DAT3)
SDMMC1_CMD += sd[2]   # CMD
GND        += sd[3]   # VSS
P3V3       += sd[4]   # VDD
SDMMC1_CLK += sd[5]   # CLK
GND        += sd[6]   # VSS (paralleled)
SDMMC1_D0  += sd[7]   # DAT0
SDMMC1_D1  += sd[8]   # DAT1
SDMMC1_D2  += sd[9]   # DAT2


# ---- SDMMC pull-ups (47 kΩ each on CMD + D0-D3 — 5 pull-ups) ----
# Per SD Association 4-bit SDMMC spec + Phase 2h Phase 4-deferred resolution.
# CLK is NOT pulled up (MCU drives idle state).
for ref, target_net, name in (
    ("R51", SDMMC1_CMD, "CMD"),
    ("R52", SDMMC1_D0,  "D0"),
    ("R53", SDMMC1_D1,  "D1"),
    ("R54", SDMMC1_D2,  "D2"),
    ("R55", SDMMC1_D3,  "D3"),
):
    pu = Part("Device", "R", value="47k", footprint=FP_R_0402)
    pu.ref = ref
    P3V3       += pu[1]
    target_net += pu[2]


# ---- microSD VDD decoupling (100 nF X7R near socket VDD pin) ----
c_sd_dec = Part("Device", "C", value="100nF", footprint=FP_C_0402)
c_sd_dec.ref = "C63"
P3V3 += c_sd_dec[1]
GND  += c_sd_dec[2]


# =====================================================================
# Block 3: SWD debug header (ARM Cortex Debug 10-pin 1.27mm) — J9 RESTORED 2026-05-30
# =====================================================================
#
# v1: J9 SWD connector RESTORED per docs/SWD_PHYSICAL_DELIVERABLE.md after
# 7-structural-wall empirical finding (test-pads at 5 XYs walled, J9-direct
# routing walled, slow-net re-route walled, layer-flip survey walled).
# Empirical truth: hands-off CAN1 + SDMMC1 + SPI3 buses occupy the J9 corridor
# regardless of layer or route geometry. SWD nets (SWDIO/SWCLK/NRST) added to
# INTENDED_DEFERRED in scripts/audit_unconnected_per_net.py — same pattern as
# IMU3_INT1 (PR #128), USART1_TX/RX Telem (PR #130), MOT7/8, EFUSE_FLT/PGOOD.
#
# v1 first-flash path UNCHANGED: USB-CDC + BOOT0 jumper + STM32 ROM bootloader
# fully functional. SWD probe-only access via wire-tack J9 pads → U1 pins for
# occasional debug post-DFU.

# MCU side (hwdef.dat:32-33)
SWDIO = n("SWDIO"); SWDIO += mcu["PA13"]
SWCLK = n("SWCLK"); SWCLK += mcu["PA14"]

swd = Part(
    "Connector", "Conn_ARM_JTAG_SWD_10",
    footprint="Connector_PinHeader_1.27mm:PinHeader_2x05_P1.27mm_Vertical_SMD",
    value="SWD_10P",
)
swd.ref = "J9"   # J9 reserved per Phase 2.5 sketch (SWD); restored 2026-05-30

# Pin map per the ARM Cortex Debug standard (KiCad symbol pin labels
# match the standard verbatim).
P3V3  += swd[1]   # VTref (target supply voltage reference)
SWDIO += swd[2]   # SWDIO/TMS
GND   += swd[3]   # GND
SWCLK += swd[4]   # SWCLK/TCK
GND   += swd[5]   # GND
# pin 6 SWO/TDO — leave NC (SWD-only, no SWO route on novapcb v1)
# pins 7 (KEY) + 8 (NC/TDI): unused — tied to GND (DRU cleanup task #30).
# Standard practice for unused debug-header pins (no floating inputs, cleaner
# EMC); also removes the false-positive "shorting" DRC vs the adjacent GND
# stitching vias on B.Cu (the pads were <no net>).
GND   += swd[7]   # KEY — tied GND
GND   += swd[8]   # NC/TDI — tied GND
GND   += swd[9]   # GNDDetect (tied to GND, used by debuggers to detect ground)
NRST  += swd[10]  # ~RESET


# =====================================================================
# Block 4: Mounting holes (4× M3 at 30.5×30.5 mm c-to-c, GND-tied)
# =====================================================================

# 4 mounting holes — using MountingHole_3.2mm_M3_Pad (6.4mm copper pad)
# tied to GND for EMC drain. Phase 2.5 placement-fit verified geometry.
for ref in ("H1", "H2", "H3", "H4"):
    mh = Part(
        "Mechanical", "MountingHole_Pad",
        footprint="MountingHole:MountingHole_3.2mm_M3_Pad",
        value="M3_GND",
    )
    mh.ref = ref
    GND += mh[1]
