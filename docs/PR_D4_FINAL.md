# PR — D4-final MCU-core close + D6 misc partials (Phase-4d-redux)

> Branch `hw/d6-usbc-misc` (off `hw/d4-mcu-core`@d364851). Closes the **MCU
> core power** domain fully (D4) and the **D6 misc partials** except IMU3_INT1.
> Real-latent **16 → 6** this PR-chain (the remaining 6 = D5 +3V3_IMU[5] +
> IMU3_INT1[1], both queued next). The via-in-pad insight unlocked the whole
> dense W/SW MCU pocket.

## 1. What landed

| Domain | Net(s) | result |
|---|---|---|
| **D4** | **VCAP1** (U1.48 ↔ C17) | **routed** — via-in-pad on U1.48, B.Cu E-of-SPI3 to C17 (rot 180°) |
| **D4** | **+3V3A** (→U1.21), **VREF_P** (→U1.20) | **routed** — C19-vertical re-spread opened the corridor |
| **D6** | **I2C2_SCL / I2C2_SDA** (→U4.3/U4.4 baro) | **routed** — via-in-pad into bottom-mount DPS310 pads |
| **D6** | **BATT_CURRENT_SENS / BATT_VOLTAGE_SENS** | **routed** — Mauch divider→filter hops |
| **D6** | **USBC_CC1 / USBC_CC2** | **routed** — B.Cu under the diff pair (GND-plane isolated) |
| **D6** | **HEATER_DRAIN** (R61↔Q5) | **routed** — layer-switch thread through the IMU island |
| **D6** | **IMU3_INT1** (U1.36↔U9.4) | **DEFERRED to FR** — see §3 |

## 2. The via-in-pad unlock (Sai-approved + master-extended)

The MCU W/SW analog-decap cluster was walled by hands-off buses so densely that
3 pins could not escape with conventional vias:

- **U1.48 VCAP1** (STM32H743 0.5mm-pitch core-LDO pin) — I2C2_SDA (F) 0.4mm S of
  the pad row + the IMU3 SPI3/IMU2 bus (B) to the W. No normal escape via fits.
  **VIP** drops straight to B.Cu, routed E-of-SPI3 to C17 — zero IMU3 crossing.
- **U4.3/U4.4 I2C2** (DPS310 baro HLGA-10, bottom-mount, 0.65mm pitch, I2C1-boxed)
  — two 0.5mm vias need 0.7mm spacing, won't fit at 0.65 pitch. **VIP** into each
  B.Cu pad.

Via-near-pad verified infeasible for all 3 (Rule-9). A **pre-PR sanity sweep** of
every fine-pitch IC (U1/U3/U7/U8/U9 + baro) confirmed the VIP set is **complete at
7 pads** (4 existing ORING/+5V_BEC + 3 new) — no other latent VIP-needed pad.
Fab: same JLC Type-VII filled+capped process, **no incremental cost**
(`docs/DECISIONS.md §13.1b`, DRU rules `vip-mcu-baro-*`).

`+3V3A/VREF`: the stacked GND pads (C19.2/C21.2) walled both nets through a 0.48mm
gap (no trace/via fits at 0.2mm clearance). Root fix = **rotate C19 vertical** so
its GND pad leaves the corridor — both nets then route clean F.Cu. C19-vertical
overlaps C20's courtyard by 0.79mm, but actual edge clearances are JLC-fine
(opp-net pads 0.36/0.68mm; only GND↔GND touch, same-net) → DRU relax
`c19-c20-courtyard-relax` (master path c, `docs/DRU_CLEANUP.md §4`).

## 3. IMU3_INT1 — deferred to FreeRouting (next task)

U1.36 → U9.4 is a ~35mm haul whose only clear layer (B.Cu) crosses **24 obstacles**
including the hands-off SPI1/SPI2/SPI3/SDMMC1/IMU2-fast buses — every crossing
needs a layer change. This is FreeRouting territory (per the scoped-FR workflow),
not a hand-route. Tracked as the immediate D6 follow-up; **not** an INTENDED_DEFERRED
v2 item. It does not block D4 (a different domain).

## 4. Verification (master's gate set)

- **Per-net audit:** every net this PR routes — VCAP1, +3V3A, VREF_P, I2C2_SCL/SDA,
  BATT_*_SENS, USBC_CC1/2, HEATER_DRAIN — **0 unconnected**. Remaining real-latent
  (6) = +3V3_IMU[5, D5] + IMU3_INT1[1] — both out of this PR's scope, queued.
- **DRC:** non-baseline electrical = **0**. Baseline categories
  (courtyard/drill/via_diameter/annular) = DRU-documented exceptions only
  (3 VIP families + 3 courtyards). GUI DRC (authoritative, applies `.kicad_dru`)
  expected clean.
- **Board-only:** `firmware/hwdef.dat` byte-identical → `waf copter` unaffected.
- **No hands-off collateral:** SPI1/SPI3 (IMU buses), SDMMC1, USB diff, CAN diff
  untouched; VCAP1/I2C2 VIP routes stay E-of / clear-of the IMU3 bus.

## 5. Scope

Closes **Phase-4d-redux D4** (MCU core power) + most of **D6**. Next: IMU3_INT1
(FR), then **D5** (+3V3_IMU dense pocket). After D5 + IMU3_INT1: Sim 1 thermal +
Sim 5 PDN re-runs → freeze-ready.
