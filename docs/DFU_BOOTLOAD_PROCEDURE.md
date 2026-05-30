# DFU first-flash procedure (novapcb v1)

> First-time firmware load uses **STM32 ROM bootloader DFU mode** over USB-CDC.
> Subsequent updates use the ArduPilot user bootloader (also USB DFU), or the
> running ArduPilot itself (MAVLink firmware upload via QGroundControl).
> SWD probes on the test-pads are the manufacturing fallback / advanced debug.

## When to use this

- **Out-of-fab board, blank flash:** STM32 ships with ROM DFU active when
  BOOT0=high; the user bootloader is not yet written. Use Stage 1.
- **ArduPilot bootloader present but ArduPilot firmware needs reflash:** use
  Stage 2 (no jumper needed).
- **Bootloader corrupted or wedged firmware:** force ROM DFU (Stage 1).

## Required tools

- USB-C cable, host PC (Linux preferred; Windows + Zadig works)
- `dfu-util` (apt: `sudo apt install dfu-util`)
- A small thin probe / paperclip / 0Ω 0402 / solder blob to short the BOOT0 jumper
- ArduPilot bootloader binary: `Tools/bootloaders/AP_Bootloader_novapcb-v1.bin`
- ArduPilot Copter firmware: `build/novapcb-v1/bin/arducopter.apj` (or `.bin`)

## Stage 1 — Blank flash → ROM DFU → write user bootloader

1. **Unplug** the board from USB.
2. **Short BOOT0 jumper** (J9 footprint repurposed; pads labeled `BOOT0_DFU`).
   - Default: jumper OPEN → BOOT0 pulled to GND → normal boot
   - DFU: jumper SHORTED → BOOT0 pulled to +3V3 → ROM DFU on next power-up
3. **Plug board into USB-C** (J1). LED status: D11 power LED on; D12 might
   blink briefly then settle (depends on ArduPilot status visibility at this
   stage).
4. **Verify DFU device appears** on host:
   ```
   $ lsusb | grep STM32
   Bus xxx Device yyy: ID 0483:df11 STMicroelectronics STM Device in DFU Mode
   ```
   - VID `0x0483` = STMicroelectronics
   - PID `0xDF11` = STM32 ROM DFU device descriptor
5. **Verify DFU interface** (use `dfu-util -l` to enumerate alt settings):
   ```
   $ dfu-util -l
   Found DFU: [0483:df11] ver=0200, devnum=yyy, cfg=1, intf=0, path="...", alt=0, name="@Internal Flash  /0x08000000/16*128Kg", serial="..."
                                                                              alt=1, name="@Option Bytes   /0x5200201C/01*128 e", serial="..."
   ```
6. **Write the ArduPilot user bootloader** to internal flash (alt=0,
   address 0x08000000):
   ```
   $ dfu-util -a 0 -s 0x08000000:leave -D Tools/bootloaders/AP_Bootloader_novapcb-v1.bin
   ```
   - `-a 0` = alt setting 0 (internal flash)
   - `-s 0x08000000:leave` = write at 0x08000000 + leave DFU mode + restart
   - `-D path` = download (host → device)
   Expected output: `Download done`, `File downloaded successfully`.
7. **Unplug + remove BOOT0 jumper short** (return jumper to GND-tied).
8. **Re-plug USB.** Now the user bootloader is in control:
   - Bootloader waits briefly (~5 s) for a firmware upload over USB-CDC
   - Then jumps to user firmware (Stage 2 needed first time to write
     ArduPilot itself)

## Stage 2 — User bootloader → write ArduPilot Copter firmware

1. Board is in user-bootloader USB-CDC mode (`dfu-util -l` will NOT show
   the 0483:df11 anymore; instead a CDC ACM device appears).
2. Find the CDC port:
   ```
   $ ls /dev/serial/by-id/ | grep -i ardupilot
   usb-ArduPilot_*Bootloader*-if00
   ```
3. **Upload ArduPilot Copter firmware** using `uploader.py` (lives in
   `Tools/scripts/uploader.py` in the ArduPilot tree):
   ```
   $ Tools/scripts/uploader.py --port /dev/serial/by-id/usb-ArduPilot_*Bootloader*-if00 \
       build/novapcb-v1/bin/arducopter.apj
   ```
   Expected output: `Programming` blocks, `Verify`, `done`, autoreboot.
4. **Board reboots into ArduPilot.** USB-CDC re-enumerates as:
   ```
   /dev/serial/by-id/usb-ArduPilot_*-if00
   ```
   This is the `*-if00` path the drone-side udev rules pin against.
5. Verify: MAVProxy or QGroundControl connects over USB-CDC at 115200
   baud, MAVLink v2, ArduPilot dialect. Heartbeat at 1 Hz with
   `type=MAV_TYPE_QUADROTOR`, `autopilot=MAV_AUTOPILOT_ARDUPILOTMEGA`.

## Subsequent firmware updates (no jumper needed)

Once the bootloader is in place, updates just need to enter user-bootloader
mode:

- **Power-cycle:** bootloader's USB window opens (~5 s) on every boot —
  upload during that window with `uploader.py`.
- **MAVLink reboot-to-bootloader:** `MAV_CMD_PREFLIGHT_REBOOT_SHUTDOWN`
  with param1=3 (reboot to bootloader). Most GCSes have a button for this.

## SWD test-pads (advanced debug)

If the user bootloader is corrupted or ArduPilot wedges hard enough that
DFU mode isn't reachable, use the SWD test-pads near U1 SW corner:

| Test pad | Net | Solder a probe wire to: |
|---|---|---|
| TP_SWDIO | PA13 | ST-LINK pin 2 (SWDIO/TMS) |
| TP_SWCLK | PA14 | ST-LINK pin 4 (SWCLK/TCK) |
| TP_NRST | NRST | ST-LINK pin 10 (SRST/RESET) — optional |
| TP_3V3 | +3V3 | ST-LINK pin 1 (VTref) — for level reference |
| TP_GND | GND | ST-LINK pin 3 / 5 (GND) |

Then standard `openocd` / `stlink` / `pyOCD` workflows apply. With SWD
present, you can use STM32CubeProgrammer or `dfu-util via SWD adapter` to
recover even from "no DFU possible" state.

## BOOT0 jumper detail

- Default position: OPEN → no electrical connection → external pull-down to
  GND on U1.94 → BOOT0=low → normal flash boot
- DFU position: SHORT (use solder blob, 0Ω 0402, or physical jumper across
  the 2 pads) → +3V3 connected to U1.94 → BOOT0=high → ROM DFU mode
- Silkscreen: `BOOT0_DFU` near the 2 pads with arrow/marking showing
  jumper-applied direction

## Notes for production

- For Sai's first board: do Stage 1 then Stage 2 once; subsequent firmware
  updates use MAVLink reboot-to-bootloader (no physical jumper).
- For batch production: have a fixture with a spring-loaded BOOT0 jumper
  short + USB cable + automated `dfu-util` script. Pull-and-go pattern.

## Cross-references

- `docs/SWD_TEST_PADS_V1.md` — design intent + placement targets (§A)
- `firmware/hwdef-novapcb/hwdef.dat` — PA13/PA14 declared as `JTMS-SWDIO`
  and `JTCK-SWCLK`; no firmware change required for test-pad usage
- `Tools/bootloaders/AP_Bootloader_novapcb-v1.bin` — the user bootloader
  binary (rebuild with `Tools/scripts/build_bootloaders.py --board novapcb-v1`)
- ArduPilot DFU bring-up reference: <https://ardupilot.org/dev/docs/loading-firmware-onto-chibios-only-boards.html>
