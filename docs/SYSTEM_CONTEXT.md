# System context — where the FC fits

The Nova drone is end-to-end-built and flying with an off-the-shelf autopilot. This document fixes what surrounds the FC so the custom board doesn't break anything that already works.

## The chain (existing, working)

```
phone (NovaApp, Kotlin/Compose, AOA-USB)
   │
   ▼
ground bridge Pi (novabridge)
   ├─ ESP32  →  Ranger TX  →  ELRS RF (150 Hz, 1:2 telem, 100 mW)
   └─ BLE central
   │
   ▼  RF
drone-side Pi 5 (running ~/novaros docker stack)
   ├─ ELRS RX (RP4TD) on USB-CDC, 420 kbaud CRSF
   ├─ Pixhawk / CubeOrange+ on USB-CDC, 115200 MAVLink   ← THIS IS WHAT novapcb REPLACES
   ├─ Hailo-8 NPU (vision-detect container)
   ├─ Pi camera (pi-cam container)
   └─ BLE peripheral (GATT to phone)

Drone-side services (Python, systemd / docker):
   1. crsf_translator     — CRSF in → MAVLink MANUAL_CONTROL out
   2. telemetry_pump      — MAVROS topics → 32-byte ELRS digest
   3. ble_gatt_server     — phone RPC tunnel → local FastAPI on :8080
   4. drone-control       — ROS2 Humble + MAVROS, owns the MAVLink session
   5. drone-bridge        — phone↔drone glue
   6. vision-detect       — Hailo object detection
   7. elrs-telemetry      — downlink digest
   8. web-control         — dev/debug web UI
```

## What the FC replaces

The FC takes over **only the Pixhawk role**. Everything else stays as-is. From the Pi's point of view the FC must look like a stock ArduPilot autopilot on `/dev/serial/by-id/usb-ArduPilot_*-if00`.

## What the FC must NOT change

- USB-CDC MAVLink at 115200, ArduPilot dialect. The drone-control container is wired to this and breaks if the dialect or transport changes.
- Pixhawk-style mode/arm semantics (CH5 arm, CH6 force-disarm, CH7 mode select). Phone-side already encodes channels in drone convention; FC-side firmware must not double-flip pitch.
- Failsafe behavior: on RC link loss the FC must run its own RC failsafe (`FS_THR_*`) — the drone-Pi services deliberately stop sending sticks during link loss and rely on this.

## Things that change later (don't design around them yet)

- 12-position CH7 redesign (`~/drone_side_redesign_prompt.md`) — pending field validation. Current live system is 6-position. FC firmware can target either; PCB doesn't care.
- BLE encryption — v2 work, not on the FC.
- VTX source switching — handled in software via `/vtx/source` HTTP, not an FC concern.
