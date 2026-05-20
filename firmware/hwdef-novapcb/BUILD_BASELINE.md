# novapcb-v1 — build progression

Recorded ArduCopter build results per sub-phase. Each section is self-contained: hwdef state, build wall-clock, flash budget, sha256. New sub-phases append a section; older sections stay as the historical record so we can spot drift.

| Phase | Total flash used | Free flash | `arducopter.bin` sha256 |
|---|---:|---:|---|
| Phase 1 (identity fork) | 1,545,872 | 158,060 | `7f3cfc25…95bc1297` |
| Phase 2a (IMU → ICM-42688-P only) | 1,534,644 | 169,284 | `b34eb835…b685c6fa` |
| Phase 2b (baro → DPS310 only) | 1,534,572 | 169,356 | `12a4d50d…d7444aa8` |
| Phase 2c (mag → IST8310+RM3100, drop broad-probe) | 1,519,948 | 183,980 | `86fec69e…f788ac70` |
| Phase 2d (GPS port verify, zero hwdef change) | 1,519,948 | 183,980 | `86fec69e…f788ac70` (bit-identical) |
| Phase 2e (8 ESC channels with **4 BIDIR**, MatekH743-bdshot inherit) | 1,521,688 | 182,244 | `8c3adbfa…2df234d93f` |
| Phase 2f (CRSF UART lock + defaults.parm at 420 kbaud) | 1,523,100 | 180,828 | `0ec597c1…d9a58b3c` |
| Phase 2g (VBAT+CURRENT ADC lock; Mauch HS-200-LV researched SCALEs) | 1,523,104 | 180,828 | `9ddb37d4…c06b1db7` |

Phase 2a delta from Phase 1: text −11,228 B, BSS −1,860 B → total flash used **−11,224 B**, free flash **+11,224 B**. Drop comes from un-linking the three legacy IMU drivers (`mpu6000`, `icm20602`, `icm42605`) we removed.

Phase 2b delta from Phase 2a: text **−72 B**, BSS 0 → total flash used **−72 B**, free flash **+72 B**. Tiny because MS5611 + BMP280 baro drivers share probe-loop infrastructure with the DPS310 driver we kept.

Phase 2c delta from Phase 2b: text **−14,624 B**, BSS 0 → total flash used **−14,624 B**, free flash **+14,624 B**. Big drop from removing `AP_COMPASS_PROBING_ENABLED` — unlinks all the compass drivers we no longer probe (BMM150, BMM350, LIS2MDL, IIS2MDC, AK8963, AK09916, QMC5883L/P, MMC3416, MMC5xx3, HMC5843, plus probe infrastructure). Only IST8310 + RM3100 driver code remains linked.

Phase 2e delta from Phase 2d (amended for bdshot): text **+1,820 B**, data −80 B, BSS **+1,212 B** → total flash used **+1,740 B**, free flash **−1,736 B**. Net positive because bdshot's BIDIR machinery (TIM3/TIM2 DMA receive path for ESC telemetry) adds ~2.4 KB on top of the ~672 B saved from dropping PWM 9-13. Trade-off: 4 BIDIR-DShot channels (motor RPM telemetry on PB0/PA0/PA2/PD12) cost ~2.4 KB vs the base-MatekH743 inheritance alternative. Free-flash headroom still ~10.7% of image_maxsize.

Phase 2g delta from Phase 2f: text **+4 B**, data 0, BSS **−4 B** → total flash used **+4 B**, free flash effectively unchanged at 180,828. Tiny because the only edits are two compile-time SCALE-default constants (`HAL_BATT_VOLT_SCALE 11.0 → 9.0`, `HAL_BATT_CURR_SCALE 40.0 → 60.6`) which feed `AP_BATT_VOLTDIVIDER_DEFAULT` / `AP_BATT_CURR_AMP_PERVOLT_DEFAULT` — the +4 B is one extra constant-pool entry because 60.6 (vs Matek's 40.0) needs different float representation. No new code paths or symbols added.

---

## Phase 1 — identity fork (2026-05-18)

Recorded result of the first end-to-end ArduCopter build against this hwdef. Phase 1 is identity-only over MatekH743; if a future build's flash usage drifts noticeably from this baseline before pin/sensor changes land, something unexpected happened.

## Build identity

| Field | Value |
|---|---|
| Date | 2026-05-18 |
| ArduPilot commit | `4379c5b82df2b333ba956887a8c7861c03775326` (`4379c5b82d AP_Logger: remove unused should_log_rcin2`) |
| ArduPilot describe | `ArduPilot-4.6.0-beta1-6764-g4379c5b82d` |
| Toolchain | `gcc-arm-none-eabi-10-2020-q4-major` (at `/opt/gcc-arm-none-eabi-10-2020-q4-major/bin/`) |
| Build host | Raspberry Pi 5, 16 GB RAM, Bookworm 64-bit, kernel 6.12.x |
| Builder | `./waf configure --board novapcb-v1 && ./waf copter` (preceded by `Tools/scripts/build_bootloaders.py novapcb-v1`) |

## hwdef identity fields

| Field | Value |
|---|---|
| `APJ_BOARD_ID` | `5350` |
| `USB_STRING_MANUFACTURER` | `"ArduPilot"` |
| `USB_STRING_PRODUCT` | `"novapcb-v1"` |
| Forked from | `~/ardupilot/libraries/AP_HAL_ChibiOS/hwdef/MatekH743/` |

## Build wall-clock

| Step | Time |
|---|---|
| `./waf configure --board novapcb-v1` | 1.116 s |
| `Tools/scripts/build_bootloaders.py novapcb-v1` | 40.658 s (cold ccache) |
| `./waf copter` | **2 min 23.636 s** (warm ccache from prior MatekH743 build) |
| `./waf copter` (real / user / sys) | 2m24.067s / 6m49.289s / 0m45.802s |
| Compiler warnings | **0** (Werror build) |

## Flash budget (`bin/arducopter`)

| Section | Bytes |
|---|---:|
| Text | 1,541,264 |
| Data | 4,608 |
| BSS | 138,060 |
| Total flash used | **1,545,872** |
| Free flash | **158,060** (~9.3% headroom) |
| External flash used | Not Applicable |

Matches the MatekH743 baseline (same numbers — Phase 1 changes are identity strings only, which don't affect text/data/bss).

## Artefacts (under `~/ardupilot/build/novapcb-v1/bin/`)

| File | Purpose | Size |
|---|---|---:|
| `arducopter` | ELF, debug-info, unstripped — for `gdb`/`arm-none-eabi-objdump` | 2,968,968 B |
| `arducopter.bin` | flashable raw binary | 1,545,876 B |
| `arducopter.apj` | ArduPilot Package JSON (uploaded by GCS) — `board_id: 5350` ✓ | 1,386,754 B |
| `arducopter.abin` | signed binary (no signature today, structure only) | 1,545,971 B |
| `arducopter_with_bl.hex` | ihex including bootloader (for SWD/JLink flash) | 4,612,044 B |
| `AP_Bootloader.bin` | standalone bootloader | 39,740 B |

## Checksums

```
sha256  7f3cfc2546cda80587f510773e80ba7835411892c89776aceb760dfc95bc1297  arducopter.bin
md5     b3d3c2244a26688124a46a812717ccb5                                  arducopter.bin   (from waf "apj_gen" line)
```

## Verification

- `board_id` in `arducopter.apj` = `5350` ✓ (matches `APJ_BOARD_ID 5350` in `hwdef.dat`)
- `git_identity` in `arducopter.apj` = `4379c5b8` ✓ (matches ardupilot HEAD)
- Exit code from `./waf copter` = `0`
- Build output contains one benign informational line at step 1255: `No APP_DESCRIPTOR found` — refers to secure-firmware metadata not set in an unsigned build.

## Reproducibility

```bash
ln -s ~/novapcb/firmware/hwdef-novapcb \
      ~/ardupilot/libraries/AP_HAL_ChibiOS/hwdef/novapcb-v1
cd ~/ardupilot && git checkout 4379c5b82df2b333ba956887a8c7861c03775326
. ~/.profile
Tools/scripts/build_bootloaders.py novapcb-v1
./waf configure --board novapcb-v1
./waf copter
sha256sum build/novapcb-v1/bin/arducopter.bin   # expect 7f3cfc2546cda80587…
```

## What this baseline is NOT

- It is not a flight-validated firmware. The hwdef still has MatekH743 pin/sensor assignments; flashing this onto a novapcb PCB (when one exists) would not work correctly.
- The 9.3% free-flash headroom is identical to MatekH743 and will be eaten by any pin-map / driver additions in Phase 2+. Plan to selectively disable optional ArduPilot features (DroneCAN, ESC telem, scripting) if we approach the limit.

---

## Phase 2a — IMU primary lock to ICM-42688-P (2026-05-18)

Phase 2a narrows the IMU stack from MatekH743's four-chip multi-revision support to novapcb-v1's single locked primary: ICM-42688-P on SPI1, polled mode. SPI4 / `IMU2_CS` / `IMU3_CS` removed (secondary IMU is a parked decision per `CLAUDE.md §3.5`). Legacy SPIDEV entries for `mpu6000`, `icm20602`, `icm42605` dropped. DRDY pin deferred (see `docs/OPEN_QUESTIONS.md` "IMU DRDY pin"); Pixhawk6X's `PA10` choice conflicts with our `USART1_RX`, and picking another pin needs grounding we don't have yet (Rule 3).

### hwdef identity (unchanged from Phase 1)

| Field | Value |
|---|---|
| `APJ_BOARD_ID` | `5350` |
| `USB_STRING_MANUFACTURER` | `"ArduPilot"` |
| `USB_STRING_PRODUCT` | `"novapcb-v1"` |

### Build identity

| Field | Value |
|---|---|
| Date | 2026-05-18 |
| ArduPilot commit | `4379c5b82df2b333ba956887a8c7861c03775326` (unchanged from Phase 1) |
| Toolchain | `gcc-arm-none-eabi-10-2020-q4-major` (unchanged) |
| Builder | `./waf configure --board novapcb-v1 && ./waf copter` |

### Build wall-clock

| Step | Time |
|---|---|
| `./waf configure --board novapcb-v1` | 3.885 s |
| `./waf copter` | **9 min 11.9 s** (warm ccache invalidated for any TU dependent on the regenerated `hwdef.h`) |
| Real / user / sys | 9m12.869s / 23m07.867s / 1m56.843s |
| Compiler warnings | **0** (Werror build) |

### Flash budget (`bin/arducopter`)

| Section | Bytes | Δ vs Phase 1 |
|---|---:|---:|
| Text | 1,530,036 | −11,228 |
| Data | 4,608 | 0 |
| BSS | 136,200 | −1,860 |
| **Total flash used** | **1,534,644** | **−11,224** |
| **Free flash** | **169,284** | **+11,224** |
| External flash used | Not Applicable | — |

Headroom moved from ~9.3% (Phase 1) to ~9.9% (Phase 2a). Recovered space goes to future Phase 2 sub-phases that *add* drivers (e.g. ICM-42688-P FFT support, additional sensor probes).

### Artefacts (under `~/ardupilot/build/novapcb-v1/bin/`)

| File | Size (B) |
|---|---:|
| `arducopter` (ELF, debug-info) | 2,957,648 |
| `arducopter.bin` (flashable raw) | 1,534,652 |
| `arducopter.apj` | 1,375,536 (approx — verified via `image_size: 1534652`) |
| `arducopter.abin` | 1,534,747 |
| `arducopter_with_bl.hex` | 4,578,820 |

### Checksums

```
sha256  b34eb8350f5304fc2769e5284537f4813313810fc938e72e60c190dcb685c6fa  arducopter.bin
```

### Verification

- `board_id` in `arducopter.apj` = `5350` ✓ (preserved through Phase 2a hwdef changes)
- `image_size: 1534652`, `image_maxsize: 1703936` ✓ (well within H743 partition)
- Exit code from `./waf copter` = `0`
- `No APP_DESCRIPTOR found` benign informational line at step 1255 (unchanged from Phase 1).

### What this Phase 2a build is NOT

- Still not flight-validated. The IMU is now correctly *declared* as ICM-42688-P, but the chip is not physically on a board yet.
- Polled mode means we may need to revisit if Phase 9 (bring-up) shows IMU-thread jitter. Tracked as `docs/OPEN_QUESTIONS.md` "IMU DRDY pin".
- Rotation (`ROTATION_YAW_180`) inherited from MatekH743 unchanged. The correct rotation depends on the chip's physical orientation on the novapcb PCB, which is a Phase 4 (layout) decision.

---

## Phase 2b — Barometer lock to DPS310 (2026-05-20)

Phase 2b drops MatekH743's multi-revision baro support (MS5611 + DPS310 + BMP280 probed at I²C2 addresses 0x76/0x77) and locks novapcb-v1 to a single primary: **DPS310 on I²C2 at 0x76**. Address 0x76 because MatekH743's DPS310 board ties SDO to GND; novapcb v1 follows. Bus is I²C2 (index 0 in I2C_ORDER).

**Reference-design grounding:** MatekH743 uses DPS310 on this same bus + address (hwdef.dat:214). Pixhawk6X does NOT use DPS310 — it uses BMP388/BMP581/ICP201XX (hwdef.dat:284-294 baros for various 6X variants). The "MatekH743 + Pixhawk6X consensus on DPS310" framing in the task contract dispatch was a master-side Rule-3 slip caught + corrected mid-PR; criterion #6 in `tasks/phase-2b-baro.yaml` updated to reflect the actual reference-design state. DPS310 is selected per `CLAUDE.md §3.5` (preferred over BMP388 per noise floor) — a single-reference decision, not a multi-reference consensus.

### hwdef identity (unchanged from Phase 2a)

| Field | Value |
|---|---|
| `APJ_BOARD_ID` | `5350` |
| `USB_STRING_MANUFACTURER` | `"ArduPilot"` |
| `USB_STRING_PRODUCT` | `"novapcb-v1"` |

### Build identity

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| ArduPilot commit | `4379c5b82df2b333ba956887a8c7861c03775326` (unchanged) |
| Toolchain | `gcc-arm-none-eabi-10-2020-q4-major` (unchanged) |
| Builder | `./waf configure --board novapcb-v1 && ./waf copter` |

### Build wall-clock

| Step | Time |
|---|---|
| `./waf configure --board novapcb-v1` | 2.047 s |
| `./waf copter` | **3 min 42.6 s** (hwdef.h regenerated for the new BARO directive list → ccache invalidated for TUs that include it; same pattern as Phase 2a's regen) |
| Real / user / sys | 3m43.253s / 7m36.808s / 1m11.720s |
| Compiler warnings | **0** (Werror build) |

### Flash budget (`bin/arducopter`)

| Section | Bytes | Δ vs Phase 2a |
|---|---:|---:|
| Text | 1,529,964 | −72 |
| Data | 4,608 | 0 |
| BSS | 136,200 | 0 |
| **Total flash used** | **1,534,572** | **−72** |
| **Free flash** | **169,356** | **+72** |
| External flash used | Not Applicable | — |

Tiny delta because MS5611 and BMP280 drivers share probe-loop infrastructure with the DPS310 driver that stays. Master's contract note ("may be a near-no-op flash-delta-wise") proven correct.

### Checksums

```
sha256  12a4d50d0fc3d4cb548c6b17c05eefa8678bade162e625569a280b1dd7444aa8  arducopter.bin
```

### Verification

- `board_id` in `arducopter.apj` = `5350` ✓ (preserved through Phase 2b hwdef changes).
- `image_size: 1534580`, `image_maxsize: 1703936` ✓ (well within H743 partition).
- Exit code from `./waf copter` = `0`.
- Single `BARO DPS310 I2C:0:0x76` line in hwdef.dat; `BARO MS5611` and `BARO BMP280` lines removed. Grep-confirmed.
- `No APP_DESCRIPTOR found` informational line at step 1255 (unchanged from prior phases).

### What this Phase 2b build is NOT

- Not flight-validated. The baro is now correctly *declared* as DPS310 on I²C2 at 0x76, but the chip is not physically on a board yet.
- I²C pull-up sizing not analyzed; deferred to Phase 6d (`SIMULATION_PLAN.md §6d` — pull-up sizing for 400 kHz, rise time vs total bus cap).
- DPS310 INT pin (data-ready interrupt, equivalent to IMU DRDY) not wired or referenced. DPS310 driver in ArduPilot polls by default; ArduPilot does not currently require an INT line for the baro. If Phase 9 bring-up shows baro-thread jitter, this becomes an open question similar to `phase2a-1 IMU DRDY pin`.
- Rotation N/A for baro.

---

## Phase 2c — External compass lock to IST8310 + RM3100 (2026-05-20)

Phase 2c replaces MatekH743's broad-probe compass approach (`define AP_COMPASS_PROBING_ENABLED 1` — probes for every compass chip ArduPilot knows about) with two explicit `COMPASS` driver lines for novapcb-v1's only supported chips: **IST8310 at 0x0E** (primary) + **RM3100 at 0x20** (alternative). Both on `I²C:ALL_EXTERNAL`, both `ROTATION_NONE`, both flagged `true` (external). `HAL_COMPASS_AUTO_ROT_DEFAULT 2` retained for runtime auto-detect.

**Reference-design grounding:** 3-reference convergence on the explicit-COMPASS-no-broad-probing pattern — `CUAV-Nora/hwdef.dat:253-254` (IST8310 + RM3100), `CUAV-X7/hwdef.dat:261-266` (same), `CarbonixF405/hwdef.dat:131` (IST8310 only). MatekH743 uses the broad-probe alternative — both are valid SOTA patterns; novapcb v1 picks explicit-lock to match `CLAUDE.md §3.5`'s "IST8310 or RM3100" two-chip lock and to save flash for unfielded compass drivers.

Per `HAL_I2C_INTERNAL_MASK 0` (inherited from MatekH743, retained), both novapcb I²C buses are external — so `ALL_EXTERNAL` probes both. Specific I²C bus → GPS-connector pin assignment is a Phase 4 layout decision; the hwdef stays bus-agnostic for now.

### hwdef identity (unchanged from Phase 2b)

| Field | Value |
|---|---|
| `APJ_BOARD_ID` | `5350` |
| `USB_STRING_MANUFACTURER` | `"ArduPilot"` |
| `USB_STRING_PRODUCT` | `"novapcb-v1"` |

### Build wall-clock

| Step | Time |
|---|---|
| `./waf configure --board novapcb-v1` | 2.056 s |
| `./waf copter` | **3 min 37.7 s** (hwdef.h regen invalidated ccache for compass-using TUs; same pattern as 2a/2b regens) |
| Real / user / sys | 3m38.531s / 7m32.063s / 1m11.851s |
| Compiler warnings | **0** (Werror build) |

### Flash budget (`bin/arducopter`)

| Section | Bytes | Δ vs Phase 2b |
|---|---:|---:|
| Text | 1,515,340 | **−14,624** |
| Data | 4,608 | 0 |
| BSS | 136,200 | 0 |
| **Total flash used** | **1,519,948** | **−14,624** |
| **Free flash** | **183,980** | **+14,624** |
| External flash used | Not Applicable | — |

**Big delta — 14.6 KB recovered.** Dropping `AP_COMPASS_PROBING_ENABLED` unlinks every compass driver ArduPilot would otherwise probe for (BMM150, BMM350, LIS2MDL, IIS2MDC, AK8963, AK09916, QMC5883L, QMC5883P, MMC3416, MMC5xx3, HMC5843, plus their probing infrastructure). Only IST8310 + RM3100 driver code remains linked. Free-flash headroom now ~10.8% of image_maxsize, up from ~9.9% at Phase 2b. Useful margin for Phase 2d-2h additions.

### Checksums

```
sha256  86fec69e894e08fe4555477c2752b566bc2f0dde00c83de39f5f77fff788ac70  arducopter.bin
```

### Verification

- `board_id` in `arducopter.apj` = `5350` ✓ (preserved through Phase 2c hwdef changes).
- `image_size: 1519956`, `image_maxsize: 1703936` ✓ (well within H743 partition; headroom ~12%).
- Exit code from `./waf copter` = `0`.
- Grep-confirmed: `COMPASS IST8310 I2C:ALL_EXTERNAL:0x0E true ROTATION_NONE` + `COMPASS RM3100 I2C:ALL_EXTERNAL:0x20 true ROTATION_NONE` both present; `AP_COMPASS_PROBING_ENABLED` absent.
- `No APP_DESCRIPTOR found` informational line at step 1255 (unchanged across phases).

### What this Phase 2c build is NOT

- Not flight-validated. Compass driver lines are declared correctly; the chip is not physically on a board yet — IST8310 / RM3100 lives on the external GPS+MAG module connected via the GPS connector's I²C lines.
- Specific I²C bus → GPS-connector pin mapping is **deferred to Phase 4 layout**. Currently `ALL_EXTERNAL` probes both I²C1 and I²C2; once the GPS connector is wired to a specific bus, the COMPASS lines can be narrowed to `I2C:1:0x0E` (or whichever bus is the GPS bus).
- DPS310 + IST8310 + RM3100 sharing I²C2 (where DPS310 lives) would be allowed by ALL_EXTERNAL — fine in practice (different addresses, no collision) but worth noting if Phase 4 puts the GPS connector on I²C1 and we want to narrow.
- Rotation: `ROTATION_NONE` is the default-if-auto-fails. `HAL_COMPASS_AUTO_ROT_DEFAULT 2` lets ArduPilot auto-detect rotation during compass calibration — actual rotation depends on the user's GPS module orientation.
- I²C pull-up sizing not analyzed (deferred to Phase 6d).

---

## Phase 2d — GPS port verify + lock (no hwdef.dat change) (2026-05-20)

Verification-only sub-phase per master's contract. MatekH743's inherited GPS-port config is "surely-working" by definition (MatekH743 ships and flies as-is); Phase 2d verifies it's correct as-is for novapcb v1 and locks the documentation. **Zero hwdef.dat change.**

### What was verified (Rule 3 / Rigor §10 grep-then-state)

| Item | Verified state | Source |
|---|---|---|
| GPS1 UART | USART2 on PD5 (TX) / PD6 (RX), index 3 in SERIAL_ORDER → SERIAL3 | MatekH743 hwdef.dat:108-110 |
| GPS2 UART | USART3 on PD8 (TX) / PD9 (RX), index 4 in SERIAL_ORDER → SERIAL4 | MatekH743 hwdef.dat:112-114 |
| SERIAL_ORDER | `OTG1 UART7 USART1 USART2 USART3 UART8 UART4 USART6 OTG2` | MatekH743 hwdef.dat:102 |
| I²C buses exposed | I2C1 (PB6 SCL / PB7 SDA) + I2C2 (PB10 SCL / PB11 SDA) | MatekH743 hwdef.dat:60-69 |
| I²C_ORDER | `I2C2 I2C1` → I2C2 = bus index 0, I2C1 = bus index 1 | MatekH743 hwdef.dat:61 |
| `HAL_I2C_INTERNAL_MASK 0` | 0 = no internal buses; both are external | MatekH743 hwdef.dat:199 |
| ALL_EXTERNAL consistency with Phase 2c COMPASS | ✓ both I²C buses are in ALL_EXTERNAL; COMPASS IST8310/RM3100 ALL_EXTERNAL lines from 2c will probe whichever bus is wired to the GPS connector | derived |
| Phase 4 layout decision deferred | which I²C bus is physically wired to the GPS connector (vs to the on-board DPS310's I²C2) | layout-time |

### Why no hwdef.dat edit

- GPS1/GPS2 UART pin assignments are H743 alt-func choices that MatekH743 vendor has already validated. No reason to change without a specific bug.
- SERIAL_ORDER places GPS1 at SERIAL3, which is ArduPilot's default GPS slot (`SERIAL3_PROTOCOL=5` by default at runtime). No edit needed.
- I²C bus pinout doesn't need novapcb-specific changes — both buses are exposed, `HAL_I2C_INTERNAL_MASK 0` makes both external, ALL_EXTERNAL probes both.
- Per master's "surely-working > SOTA when tied" calibration: default is to keep MatekH743's config. No reason found to deviate.

### Build identity (unchanged from Phase 2c)

| Field | Value |
|---|---|
| `APJ_BOARD_ID` | `5350` |
| `USB_STRING_MANUFACTURER` | `"ArduPilot"` |
| `USB_STRING_PRODUCT` | `"novapcb-v1"` |

### Build wall-clock

| Step | Time |
|---|---|
| `./waf configure --board novapcb-v1` | 1.984 s |
| `./waf copter` | **7.868 s** (full ccache; no source change → identical compile inputs → bit-identical output) |
| Real / user / sys | 8.692s / 7.354s / 0.808s |
| Compiler warnings | **0** (Werror build) |

### Flash budget (`bin/arducopter`)

| Section | Bytes | Δ vs Phase 2c |
|---|---:|---:|
| Text | 1,515,340 | 0 |
| Data | 4,608 | 0 |
| BSS | 136,200 | 0 |
| **Total flash used** | **1,519,948** | **0** |
| **Free flash** | **183,980** | **0** |
| External flash used | Not Applicable | — |

**Bit-identical to Phase 2c**, as expected for a zero-source-change verification. The build proves the hwdef + ardupilot HEAD combination still produces the recorded sha256.

### Checksums

```
sha256  86fec69e894e08fe4555477c2752b566bc2f0dde00c83de39f5f77fff788ac70  arducopter.bin
        (bit-identical to Phase 2c snapshot)
```

### Verification

- `board_id` in `arducopter.apj` = `5350` ✓.
- `image_size: 1519956`, `image_maxsize: 1703936` ✓.
- `sha256` matches Phase 2c exactly — no firmware change in this sub-phase.
- All three Rule-3 grep checks completed against MatekH743 hwdef.dat with cited line numbers.

### What this Phase 2d build is NOT

- Not flight-validated. GPS UART pins are declared correctly; novapcb has no physical board yet.
- Specific I²C bus → GPS connector pin mapping is Phase 4 layout (which I²C bus is on the GPS connector vs which is dedicated to on-board DPS310).
- `SERIAL3_PROTOCOL` / `SERIAL4_PROTOCOL` runtime defaults assumed to be ArduPilot's defaults (`5` = GPS for SERIAL3, `5` for SERIAL4 = GPS2). Not verified against an `apj_tool.py --show-params` dump.
- u-blox baud + protocol negotiation works at runtime via ArduPilot driver; not a hwdef concern.
- I²C pull-up sizing not yet analyzed (Phase 6d).

---

## Phase 2e — ESC outputs lock to 8 channels with 4-BIDIR (MatekH743-bdshot inheritance) (amended 2026-05-20)

Phase 2e initially landed (2026-05-20 in this same dev session) inheriting **base MatekH743**'s PWM block — 8 motor channels on TIM8/TIM5/TIM4, zero BIDIR. Worker flagged in the initial PR that MatekH743-**bdshot** variant provides 4 BIDIR-DShot channels via different timer reassignments (TIM3/TIM2 in place of TIM8/TIM5 on the same PB0/PB1/PA0/PA1 pins), with bdshot's two trade-offs (RC-via-UART required, GPIO-buzzer only) being FREE for novapcb v1 (CRSF on UART per `DECISIONS §4` + no buzzer requirement). Master accepted the recommendation and amended the PR before merge per the "push limits when the proven path is free" calibration.

This section reflects the AMENDED state: byte-identical inheritance of MatekH743-bdshot's PWM block lines 23-30, plus the conflict-resolution edits the bdshot variant makes to base MatekH743 (resolve TIM3 conflict on PC7 RC input; resolve TIM2 conflict on PA15 buzzer; add NODMA to UART4/UART8 to free DMA streams for motor timers; extend DMA_NOSHARE with motor timers).

### Locked pin / timer / channel / BIDIR table

| PWM # | Pin | Timer | Channel | GPIO# | DShot300/600 | BIDIR |
|---:|---|---|---|---:|:---:|:---:|
| 1 | PB0  | TIM3 | CH3  | 50 | ✓ | ✓ |
| 2 | PB1  | TIM3 | CH4  | 51 | ✓ | — |
| 3 | PA0  | TIM2 | CH1  | 52 | ✓ | ✓ |
| 4 | PA1  | TIM2 | CH2  | 53 | ✓ | — |
| 5 | PA2  | TIM5 | CH3  | 54 | ✓ | ✓ |
| 6 | PA3  | TIM5 | CH4  | 55 | ✓ | — |
| 7 | PD12 | TIM4 | CH1  | 56 | ✓ | ✓ |
| 8 | PD13 | TIM4 | CH2  | 57 | ✓ | — |

All 8 lines byte-identical to MatekH743-bdshot hwdef.dat:23-30. **4/8 BIDIR** — one per timer per the H743 "one BIDIR per timer" hardware constraint.

### Conflict resolution (bdshot-style, applied beyond the 6 PWM lines)

The bdshot timer reassignments collide with two base-MatekH743 pin definitions; bdshot resolves these via `undef` + re-add. We applied the same resolutions (since we have a full inline copy of MatekH743 rather than an `include` + `undef`):

| Conflict | Base MatekH743 | Resolution (bdshot pattern) |
|---|---|---|
| TIM3 used by PC7 RCININT (RC input via timer) | `PC7 TIM3_CH2 TIM3 RCININT PULLDOWN LOW` + `PC7 USART6_RX USART6 NODMA ALT(1)` | Drop both; `PC7 USART6_RX USART6` (primary, not ALT). cite bdshot hwdef.dat:19-20 |
| TIM2 used by PA15 ALARM (buzzer PWM) | `PA15 TIM2_CH1 TIM2 GPIO(32) ALARM` | `PA15 BUZZER OUTPUT GPIO(32) LOW` + `define HAL_BUZZER_PIN 32` (GPIO single-tone). cite bdshot hwdef.dat:39-40 |
| DMA streams contended by motor timers | `DMA_NOSHARE SPI1*` | `DMA_NOSHARE SPI1* TIM3* TIM2* TIM5* TIM4*` (motor timers get dedicated streams). cite bdshot hwdef.dat:45 |
| UART4/UART8 DMA candidates conflict with motor DMA | `PB9 UART4_TX UART4` (no NODMA) etc. | `PB9 UART4_TX UART4 NODMA`, `PB8 UART4_RX UART4 NODMA`, `PE0 UART8_RX UART8 NODMA`, `PE1 UART8_TX UART8 NODMA`. cite bdshot hwdef.dat:11-17 |

For novapcb v1 the bdshot trade-offs are free:
- USART6 was unused for RC anyway (we use CRSF on a separate UART per `DECISIONS §4`; Phase 2f locks the specific UART)
- novapcb v1 has no documented buzzer requirement — PA15 GPIO buzzer is a future option, not used
- UART4/UART8 NODMA loss is acceptable; both are auxiliary UARTs not used at high baud

### Dropped channels (unchanged from initial 2e)

| PWM # | Pin | Timer/Ch | Reason |
|---:|---|---|---|
| 9 | PD14 | TIM4_CH3 | DECISIONS §3 8-channel cap |
| 10 | PD15 | TIM4_CH4 | DECISIONS §3 |
| 11 | PE5 | TIM15_CH1 | DECISIONS §3 |
| 12 | PE6 | TIM15_CH2 | DECISIONS §3 |
| 13 | PA8 | TIM1_CH1 | WS2812 LED — no v1 requirement |

### Build identity (unchanged)

| Field | Value |
|---|---|
| `APJ_BOARD_ID` | `5350` |
| `USB_STRING_MANUFACTURER` | `"ArduPilot"` |
| `USB_STRING_PRODUCT` | `"novapcb-v1"` |

### Build wall-clock

| Step | Time |
|---|---|
| `./waf configure --board novapcb-v1` | 2.170 s |
| `./waf copter` | **10 min 20.7 s** (large hwdef.h regen — PWM timer reassignment + USART6 reassignment + buzzer reassignment + DMA_NOSHARE change all invalidated significant ccache) |
| Real / user / sys | 10m21.598s / 23m02.472s / 2m5.400s |
| Compiler warnings | **0** (Werror build) |

### Flash budget (`bin/arducopter`)

| Section | Bytes | Δ vs Phase 2d |
|---|---:|---:|
| Text | 1,517,160 | +1,820 |
| Data | 4,528 | −80 |
| BSS | 136,668 | +1,212 |
| **Total flash used** | **1,521,688** | **+1,740** |
| **Free flash** | **182,244** | **−1,736** |
| External flash used | Not Applicable | — |

The +1,740 B net cost over Phase 2d comes from: (a) bdshot BIDIR machinery for the 4 BIDIR channels (~+2,400 B vs base inheritance), partially offset by (b) the −672 B saved from dropping 5 PWM channels relative to MatekH743's 13-channel block. Headroom remains comfortable at ~10.7% of `image_maxsize`.

### Checksums

```
sha256  8c3adbfa5ab30e36e341b61405b5024e4ef6947ef2d73d640a19db2df234d93f  arducopter.bin
```

### Verification

- `board_id` in `arducopter.apj` = `5350` ✓.
- `image_size: 1521692`, `image_maxsize: 1703936` ✓.
- Grep-confirmed: PWM 1-8 lines + DMA_NOSHARE all match bdshot variant byte-identically.
- PC7 TIM3_CH2 RCININT line removed (was the timer-conflict source); PC7 is now USART6_RX.
- PA15 TIM2_CH1 ALARM line removed; PA15 is now GPIO BUZZER with `define HAL_BUZZER_PIN 32`.
- UART4 (PB9/PB8) and UART8 (PE0/PE1) all have NODMA flag added.
- DMA_NOSHARE expanded to include TIM3* TIM2* TIM5* TIM4*.

### What this Phase 2e build is NOT

- Not flight-validated. Pin/timer assignments are correct + production-validated against MatekH743-bdshot; no physical board to test ESC drive yet.
- Real-silicon DShot600 + BIDIR timing margin not measured; deferred to Phase 6g sim (IBIS analysis).
- DMA stream allocation table not explicitly tabulated against H743 RM DMA request mux — implicit via ArduPilot DMAMUX allocator + the bdshot-pattern DMA_NOSHARE rule. Build passes = no allocation conflict reported by waf.
- USART6 (PC7/PC6) defined as a UART but novapcb v1 doesn't currently use it. Phase 2f locks the CRSF UART (different UART); USART6 pins stay defined to match bdshot pattern but become "spare UART" for novapcb.
- PA15 BUZZER pin defined but no buzzer hardware required for v1. Pin can be repurposed in Phase 2-exit if not used.
- `HAL_BUZZER_PIN 32` is defined; no buzzer driver code change beyond ArduPilot's default GPIO-toggle pattern.
---

## Phase 2f — CRSF UART lock (novapcb defaults.parm, SERIAL7 + 420 kbaud) (2026-05-20)

Phase 2f locks the CRSF UART configuration for the external ELRS RX per `DECISIONS.md §4`. **No hwdef.dat change** — USART6 RX/TX on PC7/PC6 was already inherited from MatekH743-bdshot via the Phase 2e amendment. The new artefact is `firmware/hwdef-novapcb/defaults.parm` — first parameter-defaults file for novapcb-v1, gets baked into the binary's ROMFS at build time and applied on first boot.

### `defaults.parm` content (2 lines)

```
SERIAL7_PROTOCOL 23     # RCIN — inherited from MatekH743-bdshot/defaults.parm
SERIAL7_BAUD 420        # CRSF 420 kbaud — novapcb-specific deviation from bdshot's 115
```

### Design decision: option (B) per master adjudication 2026-05-20

| Option | Picked? | Reason |
|---|:---:|---|
| (A) Strict bdshot inheritance — `SERIAL7_BAUD 115` | — | BAUD 115 = 115 200, fits SBUS/DSM/PPM at TTL levels. Does NOT match CRSF's 420 kbaud. Fails our committed CRSF target per DECISIONS §4. |
| (B) novapcb-specific defaults.parm — `SERIAL7_BAUD 420` | **✓** | DECISIONS §4 locks novapcb v1 to CRSF/ELRS. 1-number deviation from bdshot, deliberate + cited. "Surely-working AND decision-aligned" beats "surely-working strict inheritance." |
| (C) No defaults.parm | — | Loses out-of-box capability. User must GCS-configure SERIAL7_PROTOCOL + BAUD before first flight. Brittle UX. |

### Scope-expansion authorization

Master authorized adding `firmware/hwdef-novapcb/defaults.parm` to the contract's `outputs.files_created` 2026-05-20 after worker's Rule-13 stop flagged it. The contract was updated in the same PR (small edit). Per `ENGINEERING_RIGOR.md §8`, scope expansion goes through contract update first.

### Verification (Rule 3, grep-then-state)

| Item | State | Source |
|---|---|---|
| MatekH743-bdshot defaults.parm | 2 lines — `SERIAL7_PROTOCOL 23` + `SERIAL7_BAUD 115` | `~/ardupilot/libraries/AP_HAL_ChibiOS/hwdef/MatekH743-bdshot/defaults.parm` |
| Base MatekH743 defaults.parm | does not exist | `~/ardupilot/libraries/AP_HAL_ChibiOS/hwdef/MatekH743/` directory listing |
| USART6 → SERIAL slot mapping | USART6 at index 7 in SERIAL_ORDER → SERIAL7 | novapcb-v1 `hwdef.dat` SERIAL_ORDER line |
| USART6 pins | PC7 (RX) / PC6 (TX) inherited from bdshot | novapcb-v1 `hwdef.dat` lines (post Phase 2e amendment) ← bdshot:19-20 |
| Inversion / half-duplex flags | none in either MatekH743 variant | grep `RXINV|TXINV|HALF_DUPLEX` over both hwdefs |
| FT-rated pin verification | deferred — PC7 is bdshot-inherited (production-validated) | trust path: ArduPilot upstream + bdshot-shipping-on-hardware |

### Build wall-clock

| Step | Time |
|---|---|
| `./waf configure --board novapcb-v1` | 1.717 s |
| `./waf copter` | **3 min 6.7 s** (defaults.parm ROMFS embed regen; small hwdef.h delta from configure tool's awareness of the new file) |
| Real / user / sys | 3m7.425s / 7m18.808s / 1m9.305s |
| Compiler warnings | **0** (Werror build) |

### Flash budget (`bin/arducopter`)

| Section | Bytes | Δ vs Phase 2e |
|---|---:|---:|
| Text | 1,518,572 | +1,412 |
| Data | 4,528 | 0 |
| BSS | 136,680 | +12 |
| **Total flash used** | **1,523,100** | **+1,412** |
| **Free flash** | **180,828** | **−1,416** |
| External flash used | Not Applicable | — |

The +1,412 B comes from the defaults.parm content + the ROMFS embed handler. The .parm text itself is ~150 bytes; the rest is the ArduPilot ROMFS handler + apply-on-boot logic. Free flash now ~10.6% of `image_maxsize` — still comfortable for Phase 2g/2h additions.

### Checksums

```
sha256  0ec597c10f89965a9a2dd8145010dd1536b53f1ff1d534b9a41f3818d9a58b3c  arducopter.bin
```

### Verification (post-build)

- `board_id` in `arducopter.apj` = `5350` ✓ (preserved).
- `image_size: 1523108`, `image_maxsize: 1703936` ✓.
- Exit code from `./waf copter` = `0`.
- defaults.parm created at `firmware/hwdef-novapcb/defaults.parm` (2 content lines + 4 comment lines).
- hwdef.dat unchanged in this sub-phase — USART6 pins inherited from Phase 2e amendment.

### What this Phase 2f build is NOT

- Not flight-validated. CRSF UART is correctly declared + baud set to 420; no physical board + ELRS RX to test against.
- FT-rated pin verification deferred — STM32H743V datasheet Table 9 not directly grep'd (PDF not on this Pi). Trust path is bdshot's production-validated PC7 usage.
- ArduPilot defaults.parm honoring behavior: assumed-working based on bdshot's defaults.parm being shipped + working in production. Not bench-verified against a built binary's actual first-boot parameter store.
- CRSF protocol-level handshake (open-drain UART, polarity autodetection) is ArduPilot driver responsibility at protocol layer. Phase 6e sim can verify edge-rate / eye opening.
- DECISIONS §4 also references "external RX module + on-board CRSF UART" — the "on-board" part means a JST connector for the ELRS RX module's CRSF lines. Specific connector pinout (which of PC7/PC6 + which power rails + which ground) is a Phase 4 layout decision.

---

## Phase 2g — VBAT + CURRENT ADC lock for external Mauch HS-200-LV (2026-05-20)

Phase 2g locks the FC-side ADC pin assignments for novapcb's external Mauch power module per `DECISIONS.md §5` (Mauch 200A pinned) + CLAUDE.md §3.6 (4-6S LiPo → LV variant, max 28V). The ADC pin lines + `HAL_BATT_*_PIN` defines inherit cleanly from MatekH743 (production-validated). The `HAL_BATT_VOLT_SCALE` / `HAL_BATT_CURR_SCALE` defines DIVERGE from Matek-inherited values: replaced with researched Mauch HS-200-LV typicals.

### Locked ADC pin allocation (inherited from MatekH743 hwdef.dat:68-77)

| Property | Pin | ADC | Channel | Define |
|---|---|---|---:|---|
| BATT1 voltage sense | PC0 | ADC1 | 10 | `HAL_BATT_VOLT_PIN 10` |
| BATT1 current sense | PC1 | ADC1 | 11 | `HAL_BATT_CURR_PIN 11` |
| BATT2 voltage sense (scaffolding) | PA4 | ADC1 | 18 | `HAL_BATT2_VOLT_PIN 18` |
| BATT2 current sense (scaffolding) | PA7 | ADC1 | 7 | `HAL_BATT2_CURR_PIN 7` |

All four ADC inputs declared with `SCALE(1)` (1× attenuation; the per-channel ArduPilot ADC scaler). ADC1 DMA uses DMA2 streams, no conflict with Phase 2e's `DMA_NOSHARE SPI1* TIM3* TIM2* TIM5* TIM4*` (DMA1 or other DMA2 streams).

### BATT_MONITOR + SCALE defaults

| Define | Value | Source |
|---|---|---|
| `HAL_BATT_MONITOR_DEFAULT` | `4` (Analog Voltage + Current) | inherited Matek — correct for Mauch analog VBAT + Hall current |
| `HAL_BATT_VOLT_SCALE` | **`9.0`** (DIVERGED from Matek `11.0`) | researched Mauch HS-200-LV 9:1 1% resistor divider; sets `BATT_VOLT_MULT` default |
| `HAL_BATT_CURR_SCALE` | **`60.6`** (DIVERGED from Matek `40.0`) | researched Mauch HS-200 typical (200A unidirectional over 0-3.3V analog full-scale, ACS-250U hall sensor with offset shifting → 200/3.3 ≈ 60.6 A/V); sets `BATT_AMP_PERVLT` default |
| `HAL_BATT2_VOLT_SCALE` | `11.0` | inherited Matek; `#ifdef`-guarded, `BATT_MONITOR2` defaults to `0` (never read), harmless. Full BATT2 removal queued for Phase 2-exit. |

### Master adjudication chain (Phase 2g 2026-05-20)

| Option | Picked? | Reason |
|---|:---:|---|
| (A) Strict Matek inheritance — SCALE 11.0 / 40.0 / 11.0 | — | Wrong-hardware calibration. The 40.0 current scale is Matek's ONBOARD hall sensor; Mauch HS-200's ACS-250U is a completely different sensor (~50% scale error, not 8%). Ships definitely-wrong calibration for known target hardware. |
| (B) Drop the 3 SCALE defines | — | **Build FAILS.** ArduPilot `#error`-enforces SCALE-with-PIN at `AP_BattMonitor_Analog.cpp:17-18 + 32-33`: `#if defined(HAL_BATT_CURR_PIN) #ifndef HAL_BATT_CURR_SCALE #error …` Same for VOLT. BATT2 SCALEs use `#ifdef` (optional), but BATT1 enforces both. |
| (C3) Sentinel 0 / scream-loud broken values | — | Failsafes IMPOSSIBLE to trigger correctly with `BATT_CURR_SCALE 0` (current always reads 0 → consumed-mAh failsafe never fires). User who forgets to calibrate flies with ZERO low-battery protection. Strictly more dangerous than 0-3% calibration error. |
| (C4) Override at defaults.parm with `BATT_AMP_PER_VOLT 0` | — | Same fatal flaw as C3 (defaults.parm wins over hwdef at first boot → same uncalibrated-flight-no-failsafe risk). |
| **(C5) Researched Mauch HS-200-LV typicals** | **✓** | Compiles + correct-to-ballpark for the actual target hardware. Failsafes work approximately even if user never calibrates; precise after standard per-unit calibration card entry. Implements DECISIONS §5 + CLAUDE.md §3.6 surely-working calibration. |

### Mauch HS-200-LV research sources (cited per Rule 3 grep-then-state)

| Source | Value extracted |
|---|---|
| `mauch-electronic.com/products/076-hs-200-hv` (HV variant product page) | "200A — Current measurement sensor board, based on Allegro Hall Sensor ACS-250U"; "voltage reading of the LiPo is optimized for up to 14S LiPo packs" (HV); "the offset shifting allows the current measurement to use the full analog input range of the flight controller from 0.0V (0A) until 3.3V" (HV+LV share sensor) |
| `craftandtheoryllc.com/store/mauch-075-hs-200-lv/` (LV variant listing) | "up to 6S (max 28V) for LV version" — confirms LV is the right variant for Nova's 4-6S spec |
| `ardupilot.org/copter/docs/common-mauch-power-modules.html` | "1% resistor divider in factor 9:1 (LV) and 18:1 (HV)" → BATT_VOLT_MULT = 9.0 nominal for LV; "Each sensor board comes with a final test result, which indicates the calibration values for voltage and current measurement" → per-unit precision via Mauch's calibration card |

Per-unit precision: Mauch ships a final-test calibration card with each sensor (typical ±1-3% deviation from nominal). User enters their unit's card values for precision; failsafes work approximately with the shipped typicals pre-calibration.

### HV variant note

If a future Nova frame switches to HS-200-HV (>6S, up to 14S), update `HAL_BATT_VOLT_SCALE 9.0 → 18.0` (HV uses 18:1 divider). Current calibration (`60.6`) is unchanged — HV and LV share the same ACS-250U hall sensor.

### Build wall-clock

| Step | Time |
|---|---|
| `./waf configure --board=novapcb-v1` | 1.780 s |
| `./waf copter` | **3 min 27.152 s** (clean rebuild after Phase 2g hwdef edit invalidated ROMFS + AP_BattMonitor compilation chain) |
| Compiler warnings | **0** (Werror build) |

### Flash budget (`bin/arducopter`)

| Section | Bytes | Δ vs Phase 2f |
|---|---:|---:|
| Text | 1,518,576 | +4 |
| Data | 4,528 | 0 |
| BSS | 136,676 | −4 |
| **Total flash used** | **1,523,104** | **+4** |
| **Free flash** | **180,828** | unchanged (4 B variance absorbed) |
| External flash used | Not Applicable | — |

The +4 B comes from the float constant change `40.0 → 60.6` requiring an extra constant-pool entry (the BSS −4 B is allocator-level rearrangement, not a removal). No new code paths, symbols, or libraries linked. Free flash now ~10.6% of `image_maxsize` (`1,703,936`) — still comfortable for Phase 2h additions.

### Checksums

```
sha256  9ddb37d420c166ab7b425cf6aa0fd7cdaf234dc250ecd31adf2a9419c06b1db7  arducopter.bin
```

### Verification (post-build)

- `board_id` in `arducopter.apj` = `5350` ✓ (preserved).
- `image_size: 1523108`, `image_maxsize: 1703936` ✓.
- Exit code from `./waf copter` = `0`, `Enabling -Werror : yes` confirmed.
- hwdef.dat BATT block: ADC pin lines + `HAL_BATT_*_PIN` defines + `HAL_BATT_MONITOR_DEFAULT 4` inherited from MatekH743; `HAL_BATT_VOLT_SCALE` + `HAL_BATT_CURR_SCALE` diverged to Mauch HS-200-LV typicals + multi-line lock comment explaining the option-C5 chain.
- defaults.parm unchanged — Phase 2g intentionally does not preset `BATT_VOLT_MULT` / `BATT_AMP_PER_VOLT` at parameter layer; the hwdef SCALE defines suffice (and the per-unit calibration card workflow expects the user to set these via GCS after physical install, not via defaults.parm).

### What this Phase 2g build is NOT

- Not flight-validated. The Mauch HS-200-LV typical values are correct-to-ballpark from datasheet research; precision comes from the per-unit calibration card. No physical Mauch + arming sequence to verify on this Pi.
- Not pinout-locked at the connector level — which JST pin carries the Mauch VBAT analog vs Mauch CURR analog vs sensor GND vs sensor 5 V is a Phase 4 layout decision. The hwdef just says "VBAT analog feeds PC0, CURR analog feeds PC1."
- BATT2 scaffolding (PA4/PA7 + BATT2 defines) retained as harmless inherited cruft (BATT_MONITOR2 = 0 default → never read; `#ifdef`-guarded SCALE = zero runtime cost). Removal queued for Phase 2-exit candidate list (joins HAL_BUZZER_PIN from Phase 2e + PC7 RCININT historical-comment cruft).
- HV variant tracking — if airframe upgrades to >6S, hwdef needs the `9.0 → 18.0` flip noted above. Not future-proofed via a multi-config define; Phase 1 commitment to a single canonical hwdef per variant family.
- ADC settling time + filter cap design — Phase 4 layout / Phase 6h sim concerns; hwdef only declares which channel is which.
