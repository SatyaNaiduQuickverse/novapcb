# novapcb-v1 — build progression

Recorded ArduCopter build results per sub-phase. Each section is self-contained: hwdef state, build wall-clock, flash budget, sha256. New sub-phases append a section; older sections stay as the historical record so we can spot drift.

| Phase | Total flash used | Free flash | `arducopter.bin` sha256 |
|---|---:|---:|---|
| Phase 1 (identity fork) | 1,545,872 | 158,060 | `7f3cfc25…95bc1297` |
| Phase 2a (IMU → ICM-42688-P only) | 1,534,644 | 169,284 | `b34eb835…b685c6fa` |
| Phase 2b (baro → DPS310 only) | 1,534,572 | 169,356 | `12a4d50d…d7444aa8` |
| Phase 2c (mag → IST8310+RM3100, drop broad-probe) | 1,519,948 | 183,980 | `86fec69e…f788ac70` |

Phase 2a delta from Phase 1: text −11,228 B, BSS −1,860 B → total flash used **−11,224 B**, free flash **+11,224 B**. Drop comes from un-linking the three legacy IMU drivers (`mpu6000`, `icm20602`, `icm42605`) we removed.

Phase 2b delta from Phase 2a: text **−72 B**, BSS 0 → total flash used **−72 B**, free flash **+72 B**. Tiny because MS5611 + BMP280 baro drivers share probe-loop infrastructure with the DPS310 driver we kept.

Phase 2c delta from Phase 2b: text **−14,624 B**, BSS 0 → total flash used **−14,624 B**, free flash **+14,624 B**. Big drop from removing `AP_COMPASS_PROBING_ENABLED` — unlinks all the compass drivers we no longer probe (BMM150, BMM350, LIS2MDL, IIS2MDC, AK8963, AK09916, QMC5883L/P, MMC3416, MMC5xx3, HMC5843, plus probe infrastructure). Only IST8310 + RM3100 driver code remains linked. Free-flash headroom now ~10.8% of image_maxsize.

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
