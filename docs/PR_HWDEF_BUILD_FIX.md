# PR C — hwdef build-readiness fix + SDMMC clock lift (firmware now builds)

> Branch `fw/sdc-max-clock-50mhz`. What started as a 1-line SDMMC clock lift
> surfaced — via the **first actual ArduPilot build ever run for this board** —
> that the v1.1 `hwdef.dat` did **not build at all**. This PR fixes the four
> build blockers + lands the SDMMC lift. **`waf copter` now succeeds for
> novapcb-v1.**

## 1. Build-verify result (the deliverable)

```
Setup for MCU STM32H743xx
Writing hwdef setup in build/novapcb-v1/hwdef.h
'copter' finished successfully (6m13s)
Target          Text(B)   Data(B)  BSS(B)   Total Flash   Free Flash
bin/arducopter  1515324   4528     133152   1519852       184076
```
- `arducopter.bin` produced for **novapcb-v1** (not SITL), 184 KB flash free.
- `define STM32_SDC_MAX_CLOCK 50000000` confirmed in the generated `hwdef.h`.

## 2. The four blockers fixed (in build-discovery order)

| # | Error | Root cause | Fix |
|---|---|---|---|
| 1 | `Pin PB12 redefined` | `PB12 MAX7456_CS` (OSD) vs real `PB12 IMU2_ACC_CS` (BMI088 accel) | remove MAX7456_CS — no OSD chip on board |
| 2 | `Pin PD4 redefined` | `PD4 EXT_CS1` vs real `PD4 IMU2_GYR_CS` (BMI088 gyro) | remove EXT_CS1 |
| 3 | `Pin PE2 redefined` | `PE2 EXT_CS2` vs real `PE2 IMU3_CS` (LSM6DSV16X) | remove EXT_CS2 |
| 4 | `Bad pin line: PC2_C ... ADC1` | `_C` is an H743 SYSCFG analog-switch token ArduPilot's parser doesn't know (zero `PC[0-9]_C` hits in the whole AP tree); PC2/PC2_C are the **same ball** | `PC2_C`→`PC2`, `PC3_C`→`PC3` |

Also removed the now-dangling dead config: `SPIDEV osd` (MAX7456_CS), `SPIDEV
pixartflow` (EXT_CS1, no optical-flow sensor), `OSD_ENABLED`,
`HAL_OSD_TYPE_DEFAULT`.

**All fixes verified against the artifact:** no MAX7456 / PixArt-flow footprint
or net exists on the board; the real CS nets (IMU2_ACC_CS U8.14↔U1.51,
IMU2_GYR_CS U8.5↔U1.85, IMU3_CS U9.12↔U1.1) ARE routed. PC2/PC3 = ADC1
ch12/13 — identical to what Pixhawk6X uses for battery sense (failsafe-safe;
master public-source research: STM32H743 datasheet + AP source grep).

## 3. SDMMC clock lift (the original task)

`define STM32_SDC_MAX_CLOCK 50000000` — lifts the microSD from the ArduPilot H7
global 12.5 MHz default to the SDR25 50 MHz target. Justified by **Sim 3**
(`SIM_3_SDMMC_SI_RESULT.md`): routed SDMMC1 skew is 0.86 % of the 50 MHz bit
period (97.8 % of the SD HS setup+hold window remains). Faster `.bin` logging.

## 4. Prevention

The v1.1 `hwdef.dat` was seeded from the MatekH743 template; the MAX7456 OSD +
EXT_CS + pixartflow blocks were **dead inheritance for hardware that doesn't
exist on novapcb**, and `PC2_C/PC3_C` used an H743 token ArduPilot can't parse.
**None of this was caught by ERC or DRC** — those check the schematic/PCB, not
the firmware. It was caught only by *actually running the ArduPilot build*, which
no prior session had done.

**Lesson (for the Phase 7a checklist, master adding):** `waf configure --board
novapcb-v1 && waf copter` succeeding is an **explicit Phase 7a freeze gate** —
the firmware must build for the board before it can be flashed (Phase 8). ERC +
DRC + build-verify are three independent gates, not two.

## 5. Verification
- `waf copter` for novapcb-v1: **success**, 0 errors/warnings (`-Werror` on).
- Diff scope: `hwdef.dat` only (12 +/ 11 −). No board/SKiDL/net change.
- ADC fix is functionally identical to Pixhawk6X battery sense (Rule-3-safe,
  public-source-verified, no board re-pin).
