# novapcb-v1 — Phase 1 sanity-build baseline

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
