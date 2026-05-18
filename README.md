# novapcb — Nova Flight Controller (FC) PCB

Custom flight controller board for the Nova drone platform. **Status: scoping / greenfield.** No schematics committed yet.

## What this is

A from-scratch FC PCB that drops into the existing Nova drone-Pi software stack. It must remain wire-compatible with the autopilot the system currently uses (a CubeOrange+/Pixhawk over USB-CDC MAVLink), because the rest of the stack — ELRS RC link, MAVROS, BLE pre-flight, Hailo vision, phone app — all assumes that contract and is already integrated end-to-end.

This is not an attempt to write a new autopilot. The plan is to run an ArduPilot-compatible firmware (or MAVLink-shim equivalent) on a custom board sized and connectorized to fit the Nova frame, with sensors and IO chosen for our specific airframe.

## What this is NOT

- Not the drone-side Pi services. Those live in `~/drone_handoff` (CRSF translator, MAVROS telemetry pump, BLE GATT server) — see `docs/SYSTEM_CONTEXT.md`.
- Not the ground bridge or phone app. Those are `~/novaros` and `~/novaapp_recovery`.
- Not a from-scratch flight stack. The board must speak ArduPilot/MAVLink.

## Repo layout

```
hardware/
  kicad/        # schematic + PCB sources (KiCad 8)
  exports/      # gerbers, drill, pick-and-place — generated, not handwritten
docs/
  SYSTEM_CONTEXT.md       # where the FC sits in the Nova stack
  INTERFACE_CONTRACT.md   # exact pin / protocol contract with the rest of the system
  OPEN_QUESTIONS.md       # decisions not yet made (MCU, form factor, channel count, …)
firmware/      # ArduPilot board definition + any board-bringup code
bom/           # parts list, sourcing notes
mechanical/    # mounting holes, stack-up, frame-fit references
```

## Where to start reading

1. `docs/SYSTEM_CONTEXT.md` — what the FC has to live with
2. `docs/INTERFACE_CONTRACT.md` — the hard pin-level constraints
3. `docs/OPEN_QUESTIONS.md` — what's undecided; pick one and propose an answer

## Workflow

PCB work on this project is code-driven where it can be: sources in KiCad, exports automated, BOM diffable. The intent is to keep schematic/layout reviewable in PRs the same way firmware changes are. See `CLAUDE.md` §6 for the full workflow.

## Hardware host

Design and build environment is a Raspberry Pi 5 (16 GB) with a Hailo-8 hat — the same Pi that runs the drone-side stack in dockerized form. KiCad runs natively on the Pi.
