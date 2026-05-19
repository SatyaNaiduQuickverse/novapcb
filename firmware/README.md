# firmware/

ArduPilot board definition (`hwdef.dat`) and bring-up artefacts for novapcb.

## Layout

```
firmware/
├── README.md              (this file)
└── hwdef-novapcb/
    ├── BUILD_BASELINE.md  recorded sanity-build result
    ├── hwdef.dat          application hwdef (forked from MatekH743)
    └── hwdef-bl.dat       bootloader hwdef (forked from MatekH743)
```

## Why a symlink, not a copy

ArduPilot expects board hwdefs to live under `~/ardupilot/libraries/AP_HAL_ChibiOS/hwdef/<board>/`. We keep the source of truth in *this* repo and symlink it into a working ArduPilot checkout:

```
~/ardupilot/libraries/AP_HAL_ChibiOS/hwdef/novapcb-v1-> ~/novapcb/firmware/hwdef-novapcb
```

Run once per Pi after cloning both repos:

```bash
ln -s ~/novapcb/firmware/hwdef-novapcb \
      ~/ardupilot/libraries/AP_HAL_ChibiOS/hwdef/novapcb-v1
```

Build flow:

```bash
cd ~/ardupilot
. ~/.profile                              # arm-none-eabi gcc + venv on PATH
Tools/scripts/build_bootloaders.py novapcb-v1
./waf configure --board novapcb-v1
./waf copter
```

Artefacts land under `~/ardupilot/build/novapcb-v1/bin/`.

## Phase 1 scope (this fork)

Identity-only changes from `MatekH743`:

| Field | Value | Source |
|---|---|---|
| Board comment | `novapcb-v1 (forked from MatekH743)` | hwdef.dat:2, hwdef-bl.dat:2 |
| `APJ_BOARD_ID` | `5350` (clean gap in `Tools/AP_Bootloader/board_types.txt`) | hwdef.dat, hwdef-bl.dat |
| `USB_STRING_MANUFACTURER` | `"ArduPilot"` (satisfies udev `usb-ArduPilot_*` prefix — `docs/INTERFACE_CONTRACT.md §3.1`) | both |
| `USB_STRING_PRODUCT` | `"novapcb-v1"` | both |

Phase 1 is **deliberately** pin/sensor-identical to MatekH743. Pin map, IMU/baro/mag selection, DShot timer choices, connectorset — all Phase 2+ work and get their own branches.

## Upstreaming

The numeric `APJ_BOARD_ID 5350` works for local builds but ArduPilot CI rejects numeric IDs (see `libraries/AP_HAL/hwdef/scripts/hwdef.py:get_numeric_board_id`). If we ever upstream, register a symbolic name in `Tools/AP_Bootloader/board_types.txt` and switch the hwdefs to it.
