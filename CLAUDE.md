# CLAUDE.md — Nova Flight Controller PCB

> **You are reading the canonical bootstrap document for this repo.**
> This file is automatically loaded by Claude Code on every session in this
> directory. Read it top-to-bottom on a cold start. It encodes everything a
> Claude joining this project needs to know — the system context, the
> contracts, the rules, the user profile, the known traps. If something
> looks ambiguous, the answer is here; if it's truly missing, ask before
> guessing.
>
> Status: bootstrapping (no schematics yet). Last revised: 2026-05-18.

---

## 0. TL;DR for a cold reader

**This repo (`novapcb`) is a from-scratch custom Flight Controller PCB for the Nova drone.** Greenfield. No schematics committed yet. Three things you should know before you do anything:

1. **The FC is a Holybro Pixhawk 6X replacement, not a new autopilot.** It must run an ArduPilot-compatible firmware and present as a stock ArduPilot autopilot to the rest of the Nova drone-side stack over USB-CDC MAVLink. Breaking that contract throws away ~6 months of integration work on the surrounding services. For v1 we replace the 6X **functionally** (same electrical + software interface); a true FMUv6X mechanical drop-in is deferred to v2 — see `docs/DECISIONS.md §2`.

2. **The user is hardware-curious, not a deep EE.** They will not review your technical details for correctness. You must self-validate (build, run, test, read your own diff) before declaring anything done. If you skipped a check, say so.

3. **The directory may look empty. That is on purpose — bootstrapping.** Do not "find files elsewhere and commit them here." If the task says PCB and the dir is empty, the task is to create the PCB project, not to import some other project.

**Read in this order:**
1. This file (rules + system context).
2. `docs/SYSTEM_CONTEXT.md` — the wider Nova stack the FC plugs into.
3. `docs/INTERFACE_CONTRACT.md` — pin-level constraints.
4. `docs/DECISIONS.md` — locked v1 scoping decisions + reasoning (was `OPEN_QUESTIONS.md` until 2026-05-18; `OPEN_QUESTIONS.md` now holds only future open questions).
5. `README.md` — short orientation (mostly redundant with this file).

---

## 1. Project identity

### What this repo IS

- A custom Flight Controller (FC) PCB design + firmware-config repo.
- Target: drop-in replacement for the off-the-shelf autopilot (currently a Holybro Pixhawk 6X) used in the Nova drone.
- Software contract: must speak ArduPilot MAVLink v2 over USB-CDC at 115200 baud and enumerate as `usb-ArduPilot_*` for udev pinning.
- Tooling intent: code-driven PCB workflow — KiCad sources in git, exports automated, BOM diffable in PRs.
- Form factor target (v1): Pixhawk-standard 30.5 × 30.5 mm with M3 mounting holes — **functional** drop-in (electrical + software identical to the 6X), single-PCB, requires a new mounting tray on the airframe. **FMUv6X mechanical drop-in is v2** (separate FMU + isolated-IMU boards, exact 6X mechanical match); deferred until v1 flies.

### What this repo IS NOT

- **Not** the drone-side Pi services. Those (CRSF→MAVLink translator, MAVROS telemetry pump, BLE GATT server) live in `~/drone_handoff/` on the build host. They are the *consumers* of the FC's MAVLink interface, not the FC itself.
- **Not** the Nova ROS2 stack (`~/novaros/`). That is the drone-Pi ROS2 + MAVROS + Hailo container stack. The FC must be compatible with it but is not part of it.
- **Not** the phone application (`~/novaapp_recovery/` and the NovaApp Kotlin/Compose project). The phone talks to the ground bridge Pi via AOA-USB, never directly to the FC.
- **Not** a from-scratch autopilot. Do not propose writing custom flight stabilization. Use ArduPilot (or, if firmware drifts, a minimal MAVLink shim) on a standard MCU.
- **Not** a place for ESC design. The 60 A FOC ESC is a separate, later project; it has its own repo when it exists.

### Status

- Last commit (as of 2026-05-18): `711c4d4` — added this CLAUDE.md on top of bootstrap `2bcdadc`.
- No schematics, no PCB layout, no firmware.
- All 9 v1 scoping decisions locked on 2026-05-18 — see `docs/DECISIONS.md`. MCU = STM32H743VIT6; form factor = Pixhawk-standard 30.5 × 30.5 mm M3.

---

## 2. The Nova drone system — full context

The FC does not exist in isolation. The surrounding system is fully built and flying with an off-the-shelf autopilot. Everything you do on the FC must remain compatible with this stack. Internalize the diagram below before designing anything.

### 2.1 End-to-end chain (existing, working)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  PHONE (NovaApp, Kotlin/Compose Android, AOA-USB host role)                  │
│  – Stick inputs, mission upload, pre-flight RPC over BLE                     │
│  – Already applies pitch sign convention before transmit (DO NOT double-flip)│
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │ AOA-USB, 16 MiB framed:
                                │ [0xAA][CMD][LEN_u32_le][PAYLOAD][CRC8]
                                ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  GROUND BRIDGE Pi (novabridge, Python) — DONE                                │
│  ├─ ESP32 (USB-serial) → Ranger TX (CRSF, 420 kbaud) → ELRS RF              │
│  ├─ BLE central (bleak)                                                      │
│  └─ VRX stub (placeholder for analog/digital VRX integration)                │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │ ELRS RF: 150 Hz uplink, 1:2 telem ratio,
                                │ 100 mW TX, 868/915 MHz region-dependent
                                ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  DRONE-SIDE Pi 5 (16 GB) + Hailo-8 hat — runs ~/novaros/ docker stack        │
│                                                                              │
│  ├─ ELRS RX (RP4TD) on USB-CDC ────► /dev/serial/by-id/usb-ELRS_RP4TD…       │
│  │     420 kbaud CRSF, 8N1                                                   │
│  │                                                                           │
│  ├─ AUTOPILOT on USB-CDC      ────► /dev/serial/by-id/usb-ArduPilot_…        │
│  │     115200 baud, MAVLink v2, ArduPilot dialect                            │
│  │     ◄══════ THIS IS WHAT novapcb REPLACES ══════                          │
│  │     (Currently a Holybro Pixhawk 6X running ArduCopter v4.6.3)            │
│  │                                                                           │
│  ├─ Hailo-8 NPU (vision-detect container, on port 8081)                      │
│  ├─ Pi Camera (pi-cam container, rpicam-vid)                                 │
│  └─ BLE peripheral (bless, GATT) ◄── phone pre-flight RPC tunnel             │
│                                                                              │
│  Docker services (all running, all DONE):                                    │
│    1. drone-control    — ROS2 Humble + MAVROS, owns the MAVLink session     │
│    2. drone-bridge     — phone ↔ drone glue, exposes FastAPI on :8080       │
│    3. vision-detect    — Hailo object detection on :8081                    │
│    4. elrs-telemetry   — packs MAVROS state into 32 B ELRS downlink @ 3 Hz  │
│    5. web-control      — dev/debug web UI                                   │
│    6. pi-cam           — camera capture                                     │
│    7. novaros-mongodb  — state persistence on :27017                        │
│                                                                              │
│  Plus three Python services (per ~/drone_handoff/PROMPT.md, in build):       │
│    A. crsf_translator  — CRSF in → MAVLink MANUAL_CONTROL out via FastAPI   │
│    B. telemetry_pump   — MAVROS topics → ELRS 32 B digest                   │
│    C. ble_gatt_server  — phone RPC tunnel → local FastAPI on :8080          │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 What the FC replaces, exactly

The FC takes over **only the Autopilot box** in the diagram. Everything else stays as-is. From the host Pi's point of view, the FC must look indistinguishable from a stock ArduPilot autopilot:

- Same USB-CDC enumeration (`usb-ArduPilot_*` so udev by-id symlinks resolve unchanged).
- Same baud rate (115200).
- Same MAVLink dialect (ArduPilot, v2).
- Same parameter set (or close enough that MAVROS doesn't choke).
- Same arm/disarm semantics, same mode IDs, same failsafe codes.

If any of those drift, the surrounding services break silently.

### 2.3 What the FC must NOT touch

- BLE / GATT — host-side concern. The phone's pre-flight RPC tunnel is the Pi's job, not the FC's.
- Vision / Hailo NPU — host-side concern. The FC never sees video.
- VTX source switching — handled in software by the drone-bridge service over HTTP (`/vtx/source`).
- Mission upload, parameter persistence, fence config — host-side FastAPI on `:8080`.
- ELRS telemetry packing — host-side `elrs-telemetry` container.
- Phone-side anything.

---

## 3. Interface contract (HARD constraints — do not break)

Numbers in this section come from `~/drone_handoff/PROMPT.md` and the `~/novaros/docker-compose.yml`. Treat them as load-bearing for software that was written months ago and is already in production-shaped state. If you're about to deviate from anything here, raise it in `docs/OPEN_QUESTIONS.md` first and get explicit go-ahead.

### 3.1 Primary host link — USB-CDC MAVLink

| Property | Value | Why it's load-bearing |
|---|---|---|
| Transport | USB 2.0 full-speed, CDC-ACM | drone-control container opens `/dev/ttyACM*` |
| Baud (logical) | 115200, 8N1 | Hardcoded in drone-control config |
| Protocol | MAVLink v2, ArduPilot dialect | MAVROS dialect; non-Ardu dialects break MAVROS message IDs |
| USB descriptor | Must enumerate as `usb-ArduPilot_*` | udev by-id pinning across boot order |
| Heartbeat | 1 Hz, type=MAV_TYPE_QUADROTOR, autopilot=MAV_AUTOPILOT_ARDUPILOTMEGA | MAVROS detects connection on heartbeat presence |

### 3.2 RC input — CRSF over UART

The RC link arrives at the drone Pi as a stream of CRSF frames from an ELRS RP4TD receiver. Currently bridged through an ESP32-C6 on USB. If the FC has a spare 5 V-tolerant UART, v1 plan is to absorb CRSF directly onto the FC and retire the ESP32 bridge.

| Property | Value |
|---|---|
| Baud | 420 000, 8N1 |
| Frame rate | ~150 Hz |
| Telemetry ratio | 1:2 (one downlink slot per two uplink slots) |
| Channel encoding | u11 packed (172 = −1.0, 992 = centre, 1811 = +1.0) |
| Channel-to-axis | `axis_pm1(ch) = (ch - 992) / 819.5`, clamped to ±1 |
| Channel-to-throttle | `throttle_01(ch) = max(0, min(1, (ch - 172) / 1639))` |

**Channel map (set by NovaApp, already in drone convention):**

| Ch | Purpose | Range / behavior |
|---:|---|---|
| 1 | Roll | −1 (left) … +1 (right) |
| 2 | Pitch | −1 (nose down) … +1 (nose up) — *phone already applied sign; do not re-flip* |
| 3 | Throttle | 0 (idle) … 1 (full) |
| 4 | Yaw | −1 (CCW) … +1 (CW) |
| 5 | Arm | <1500 disarm, ≥1500 arm |
| 6 | Force-disarm | ≥1500 forces disarm regardless of CH5 |
| 7 | Flight mode | 6-position today (1000/1200/1400/1600/1800/2000); 12-pos redesign pending |
| 8 | Mode overflow / layered ops | reserved today; redesign in flight |
| 9 | Precision-landing trigger | ≥1500 triggers `/land/precision` on FastAPI |
| 10–12 | Box coordinates (vision lock) | reserved for box geometry |
| 13–16 | Not transmitted in 12ch Mixed mode on this RP4TD |

### 3.3 Failsafe semantics — do not synthesize neutral sticks

If you stop seeing CRSF frames for >300 ms, you **must stop sending MANUAL_CONTROL** and let ArduPilot's onboard RC failsafe (`FS_THR_*`, `FS_GCS_ENABLE`) fire. Do not emit "neutral stick" frames as a substitute — that defeats the failsafe entirely. The next valid frame resumes the loop. This was caught in v0 review; do not reintroduce.

### 3.4 ESC outputs

| Property | Value |
|---|---|
| Channel count | 8 (DShot300/600, PWM fallback) — `docs/DECISIONS.md` #3 |
| Protocol | DShot300 / DShot600 preferred; PWM fallback |
| Connector | TBD — JST-SH 1.0 or solder pads (#7) |
| Logic level | 3.3 V (most modern ESCs accept) |

### 3.5 Sensors required for ArduCopter parity

| Sensor | Recommended part | Notes |
|---|---|---|
| IMU (primary) | ICM-42688-P | What current ArduPilot boards favor |
| IMU (secondary) | ICM-42688-P or BMI088 | Redundancy improves arming reliability |
| Barometer | DPS310 or BMP388 | DPS310 preferred for noise floor |
| Magnetometer | IST8310 or RM3100 (external, via I²C) | Internal mag is too noisy on most FCs |
| GPS | UART, plus I²C for external compass | Standard Pixhawk GPS module assumed |
| Optional | Optical flow / rangefinder | I²C or UART; not v1 critical |

### 3.6 Power

| Rail | Spec |
|---|---|
| VBAT monitoring | 4S–6S LiPo (16 V – 26 V nominal) |
| 5 V in | from external BEC, ≥ 3 A |
| 3.3 V | on-board LDO for sensors / MCU |
| USB 5 V | bench bring-up only; do not power motors |

### 3.7 Pi-side ports (informational only)

The FC never opens TCP sockets. Listed so firmware bring-up scripts can sanity-check the surrounding stack on the Pi:

- `127.0.0.1:8080` — drone-control FastAPI (calibration / mission / params / fence / safety)
- `127.0.0.1:8081` — vision-detect (Hailo)
- `127.0.0.1:27017` — MongoDB

---

## 4. Known traps — do not reintroduce these bugs

These were caught in prior reviews of the surrounding software. They are documented here because firmware decisions on the FC can resurrect them.

### 4.1 Pitch sign double-flip

The phone applies `pitch = -right.y` before transmit. CRSF channel 2 arrives at the FC already in drone convention. **Do not negate again.**

```
pitch = axis_pm1(channels[1])       # YES — already in drone convention
pitch = -axis_pm1(channels[1])      # NO — double-flips; nose-up stick → nose-down → crash
```

This bug was caught in v0 software review. Do not re-introduce in firmware, helper docs, or example code in this repo.

### 4.2 Blocking HTTP on the CRSF hot path

`requests.post(...)` on the CRSF parser thread stalls the parser and drops frames. Use `httpx.AsyncClient` inside asyncio, or `await asyncio.to_thread(requests.post, ...)`. This is a software-side trap, but if any FC bring-up code touches a host-side endpoint, the same rule applies.

### 4.3 Hardcoded `/dev/ttyUSB0` or `/dev/ttyACM0`

USB enumeration order is not guaranteed at boot. Always use udev by-id paths (and globs):

```
/dev/serial/by-id/usb-ArduPilot_*-if00
/dev/serial/by-id/usb-Express_LRS_RP4TD_*-if00
```

This is also why the FC's USB descriptor must include the `ArduPilot_*` prefix — the surrounding scripts depend on it.

### 4.4 Neutral sticks on link loss

Already covered in §3.3. Repeated here because it is the most dangerous bug a future FC-side helper could re-introduce.

### 4.5 INSTALLED_TOOLS.md says MAVROS is not installed — it is

The `~/novaros/INSTALLED_TOOLS.md` document is from an earlier phase and claims ROS2/MAVROS are not installed. They are. The running docker stack is the source of truth. Don't propose installing them again.

### 4.6 CH7 6-position vs 12-position

Today the live system uses 6-position CH7 decoding (`DRONE_CH7_MODES = STABILIZE,ALT_HOLD,LOITER,POSHOLD,RTL,LAND` in `~/novaros/docker-compose.yml`). A 12-position redesign exists in `~/drone_side_redesign_prompt.md` but is not yet shipped. FC firmware can be agnostic to which is live; PCB design is unaffected.

---

## 5. Repo layout

```
novapcb/
├── CLAUDE.md                       (this file — bootstrap for Claude sessions)
├── README.md                       (short human orientation)
├── .gitignore
├── docs/
│   ├── SYSTEM_CONTEXT.md           where the FC sits in the wider Nova stack
│   ├── INTERFACE_CONTRACT.md       pin/protocol constraints (mirrors §3 here)
│   ├── DECISIONS.md               locked v1 scoping decisions (2026-05-18)
│   └── OPEN_QUESTIONS.md           stub for future open questions
├── hardware/
│   ├── kicad/                      KiCad 8 schematic + PCB sources
│   └── exports/                    gerbers, drill, pick-and-place — generated, gitignored
├── firmware/                       ArduPilot hwdef.dat + board bring-up code
├── bom/                            parts list, sourcing notes, alt-parts table
└── mechanical/                     mounting hole patterns, stack-up, frame-fit refs
```

**Rules for what goes where:**

- `hardware/kicad/` — schematic and PCB *sources only*. Never commit generated outputs here.
- `hardware/exports/` — generated. Reproducible via script. Gitignored except for `.gitkeep`. Tagged releases may include a snapshot.
- `docs/` — Markdown only. Diagrams as Mermaid or ASCII (no binary blobs unless absolutely necessary).
- `firmware/` — the ArduPilot `hwdef.dat` for our board, plus any minimal C bring-up (e.g., LED-blink test before flashing ArduPilot itself).
- `bom/` — CSV preferred, one row per line item, including footprint, alt-parts, sourcing URL, last-checked price/date.

---

## 6. Development workflow

### 6.1 Code-driven PCB philosophy

PCB work on this project is reviewable the same way firmware is. That means:

- KiCad sources committed in plain-text S-expression form (KiCad 8 default).
- Schematic and layout changes go through PRs.
- BOM is CSV and diffable.
- Export pipeline is scripted (a `make exports` or `scripts/export.sh` target) — never click-export from KiCad.
- Footprints and symbols: prefer in-repo libraries over global KiCad libs (so the design is reproducible on any clone). Commit a `hardware/kicad/lib/` directory when needed.

### 6.2 Docs first, schematic second, layout third

Don't open KiCad until the doc layer is right. Specifically:

1. If something isn't in `docs/INTERFACE_CONTRACT.md`, decide it and write it there *first*.
2. If a decision is open, leave it in `docs/OPEN_QUESTIONS.md` with options + a recommendation.
3. Only then sketch in KiCad.

Reason: schematic decisions are 10× more expensive to undo than doc decisions. Lock the constraints first.

### 6.3 Bring-up plan (when there's hardware to test)

Phased, do not skip a phase:

1. **Bare-metal LED blink** — verifies MCU is alive, clock tree is right, programmer connects.
2. **Sensor I²C/SPI roll-call** — every sensor responds to its ID register.
3. **USB-CDC enumeration** — host sees `usb-ArduPilot_*` (with our descriptor — even before ArduPilot itself runs, the bootloader's CDC suffices).
4. **ArduPilot port** — flash ArduCopter built with our hwdef, run on bench (props off!), MAVROS connects.
5. **A/B against the Holybro Pixhawk 6X** — **functional** swap (not mechanical in v1): unplug 6X from the drone Pi's USB, plug in novapcb on a bench tray, ensure all drone-side services come up unchanged, both APMs report identical (within tolerance) param values.
6. **Tethered hover** — first flight is tethered, props on, low throttle, RTL armed.
7. **Free flight** — after telemetry digests look clean for ≥10 min tethered.

### 6.4 PR conventions

- Branch per change (`hw/imu-section`, `doc/connector-pinout`, `fw/hwdef-h743`).
- Commit messages: imperative mood, why-not-what, ≤72 char subject.
- Co-author trailer when Claude wrote the change.
- Never amend a pushed commit. Make a new one.

### 6.5 Git / GitHub conventions for this repo

- Remote: `https://github.com/SatyaNaiduQuickverse/novapcb`. Currently public for cross-Pi setup; was initially private. Don't flip visibility without user confirmation (Rule 7).
- Default branch: `main`.
- Auth on the build host: `gh` CLI, HTTPS, token stored in keychain by gh.
- Force-push to `main` is forbidden.
- Pushing requires user confirmation in chat each time — see Rule 7.

---

## 7. Development rules (read every session)

These are the behaviors that have worked on this project so far. Violating them is what causes lost time and frustrated users. Re-read them at the start of every session.

### Rule 1 — Read before acting

Before committing, restructuring, or picking a target directory, survey the related repos. If the target directory is empty, that means **bootstrap a new project here**, not "go find files somewhere else and commit those." On 2026-05-05 a previous Claude jumped at `~/drone_handoff` because it had files; that was wrong — `drone_handoff` is drone-side *software*, not the PCB. The user corrected the course; this rule exists so the same mistake isn't made twice.

When the scope is genuinely ambiguous, ask. The cost of one clarifying question is far less than the cost of bootstrapping the wrong project.

### Rule 2 — Document the contract before writing code

For any feature that crosses a system boundary (USB, UART, BLE, HTTP, IPC, ROS topic, I²C, SPI), first write or update a short doc: what's the wire format, what are the timeouts, what's the failure mode, who initiates. Code comes after the doc, not before. This applies to firmware too: write a hwdef.dat *after* the interface contract is locked, not before.

### Rule 3 — Never invent technical specifics from training data

Baud rates, pin maps, GATT UUIDs, packet layouts, API endpoints, sensor register addresses — pull these from the actual project files (`docs/INTERFACE_CONTRACT.md`, `~/drone_handoff/PROMPT.md`, source code in related repos, datasheets). If you can't find a number, say "I don't have this — where should I look?" Do not pattern-match a plausible number from training data; in this domain that is how drones crash.

### Rule 4 — Match scope to the request

A bug fix doesn't need a refactor. A one-shot script doesn't need a CLI framework. A README doesn't need a wiki. No "while I'm here" cleanups, no premature abstractions, no feature flags for hypothetical futures.

The user says "do X" — do X, not X-plus-a-restructuring. If you see something nearby that needs fixing, note it (in `docs/OPEN_QUESTIONS.md` or a follow-up PR), don't silently expand scope.

### Rule 5 — For UI / build / hardware changes, actually run it

Type-checking and tests verify *correctness*, not *feature correctness*. For this repo specifically:

- KiCad changes: open the project, run DRC, run ERC, look at the 3D view. Don't claim "should layout fine" — check.
- Firmware bring-up: flash to hardware if hardware exists. If not, say "no hardware to verify on; this is a paper change."
- Doc changes: if a doc references a file, verify the file exists at the path you wrote.

If you can't run the check, say so explicitly — do not claim success you didn't verify.

### Rule 6 — Self-validate. The user does not review technical details.

The user is hardware-curious but is not going to catch your wrong pin assignment or your inverted enable line. Before declaring a task done:

1. Build / DRC / ERC / tests / lint — whichever apply.
2. Read your own diff line-by-line.
3. Cross-check against `docs/INTERFACE_CONTRACT.md` for anything that touches a wire-level constraint.
4. State explicitly in your final message what you checked.

If you skipped a step, say which and why. The user prefers an honest "I didn't run DRC because KiCad isn't installed yet" over a confident "looks good."

### Rule 7 — Verify and confirm before destructive or shared-state actions

Authorization for one push is not authorization for the next. Before any of:

- `git push`, `git push --force`, `git reset --hard`
- `gh repo delete`, `gh repo edit --visibility`
- `rm -rf`, `git clean -fdx`
- Modifying CI, GitHub Actions, branch protection
- Sending anything to a phone, drone, or remote service
- Deleting branches (local or remote)

…state the action, name the blast radius, and confirm. The user told us "carefully" on 2026-05-05 before the first push — assume that posture holds for every push thereafter.

### Rule 8 — Open questions go in OPEN_QUESTIONS.md

When you hit a decision the user hasn't made (MCU pick, library choice, connector standard), don't pick silently and don't block the whole task. Add it to `docs/OPEN_QUESTIONS.md` with:

- Options (≥2)
- Your recommendation
- Trade-offs / reasoning
- Date raised

Then continue with parts of the task that don't depend on the unresolved question.

### Rule 9 — Don't re-introduce known bugs

See §4. The pitch-sign double-flip is the canonical example. Whenever you touch a sign convention, a serial parser, or a failsafe path, re-read §4 before writing the change.

### Rule 10 — Comments are for non-obvious WHY, not WHAT

Don't write `// read CRSF channel` above `read_crsf_channel()`. Do write a one-line note when there's a hidden constraint (a race, a vendor quirk, a regulatory limit, a past bug). The pitch-sign comment in `crsf_translator.py` is the right kind of comment — it stops a future contributor from "fixing" something that isn't broken.

### Rule 11 — Memory hygiene

If the user corrects you ("no, not that"), save the rule and the *why*. If the user confirms a non-obvious call ("yeah, that bundled PR was right"), save that too. Quiet confirmations matter as much as corrections — they prevent drift.

Don't save:
- Ephemeral task state (use the task list).
- Things derivable from the code (file layouts, function signatures).
- Things derivable from git (who changed what).
- Anything already in this CLAUDE.md.

Memory lives at `~/.claude/projects/<path-hash>/memory/` and is per-machine. If the project state is durable enough to matter on a clone, promote it from memory into a committed doc.

### Rule 12 — Communicate tightly

- End-of-turn: one or two sentences. What changed, what's next. Nothing else.
- Working: one sentence when you find something, change direction, or hit a blocker. Silent is not better than brief.
- Don't narrate your internal deliberation. State results.
- When you reference a file, use `path:line` so the user can click through.

### Rule 13 — Stop and ask when the task is ambiguous

If "go ahead" could mean three things, pick the most likely and **state which one** before acting — give the user one round to redirect cheaply. Don't ask three clarifying questions in a row; one well-chosen statement of intent ("I'll lock the open questions and write ARCHITECTURE.md, ~5 min") is better than a multiple-choice prompt.

### Rule 14 — Never bypass safety / quality checks

No `git commit --no-verify`. No `--skip-tests`. No `// noinspection` without a reason comment next to it. No `// @ts-ignore` without an explanation. If a hook fails, diagnose; don't bypass.

### Rule 15 — Don't write code the user didn't ask for

This is a special case of Rule 4 but worth its own line because Claude has a tendency to do it. If the user asks "what do you think about X," that is a discussion, not a permission to implement X. Discuss in 2–3 sentences with a recommendation. Implement only after the user agrees.

### Rule 16 — Be careful with the auto-memory in shared contexts

The auto-memory may contain personal notes (preferences, profile). When generating a CLAUDE.md or any committed doc, do not blindly paste personal memory content. Personal preferences belong in memory; project rules belong in committed docs. This file is the line between the two.

---

## 8. User profile — how to work with this user

Encoded from interactions and from auto-memory notes. Keep these in mind when shaping responses and proposals.

### 8.1 Background

- Hardware-curious, building code-driven PCB workflows. Not a deep EE.
- Software-fluent. Familiar with Docker, ROS2, Kotlin/Compose, FastAPI, Python asyncio.
- Working across multiple Pis simultaneously (build host, drone Pi, ground bridge Pi, sometimes a separate Pi for the phone app). Sometimes uses different Claude accounts on different Pis — context does not transfer automatically; that's why this file exists.

### 8.2 Working style

- **Terse.** Will say "do it" or "go ahead" when the next step is obvious. Don't ask for re-confirmation of things already authorized.
- **Action-oriented.** Long lists of clarifying questions burn patience. Prefer "I'll do X (~5 min), say stop if wrong" over a multiple-choice prompt.
- **Trusts Claude to make technical calls.** And does *not* review them. Therefore: self-validate (Rule 6).
- **Will correct course when wrong.** When that happens, save the correction to memory (Rule 11) and update relevant docs.
- **Appreciates being told what's about to happen.** Before destructive actions, the user wants the action + blast radius stated up front (Rule 7).

### 8.3 Active projects (in addition to novapcb)

The user juggles several related projects. Knowing the boundary helps you stay in scope:

- **novapcb** — this repo. FC PCB.
- **FOC ESC, 60 A** — separate later project, currently scoping. Not in this repo.
- **NovaApp** — Kotlin/Compose Android phone app. Lives on a different Pi.
- **Nova drone software** — `~/drone_handoff/` (build host) and the running docker stack in `~/novaros/`. Already shipped end-to-end.
- **Ground bridge** — `novabridge`, done.

If a request feels like it belongs to one of the other projects, name that and ask.

### 8.4 What "done" means to the user

A task is done when:

1. The change works (verified).
2. The diff is small enough to read.
3. The docs are updated.
4. The commit is on the right branch.
5. You have stated, in one sentence, what you verified.

A task is **not** done when the build passes but you didn't open the app / flash the firmware / run DRC.

---

## 9. Memory and cross-machine state

This section is meta — it covers how Claude's own state moves between machines. The user runs Claude on multiple Pis, sometimes with different accounts. The state model is:

| Thing | Location | Cross-machine? |
|---|---|---|
| Repo files | `~/novapcb/` | Yes, via `git clone` |
| `CLAUDE.md` (this file) | `~/novapcb/CLAUDE.md` | Yes, via `git clone` — auto-loaded each session |
| Auto-memory | `~/.claude/projects/<path-hash>/memory/` | **No** — per-machine, outside the repo |
| Conversation transcripts | `~/.claude/projects/<path-hash>/*.jsonl` | **No** — local, account-scoped |
| MCP server configs | `~/.claude/` | **No** — per-machine |
| GitHub auth | `~/.config/gh/` | **No** — per-machine |
| Local Claude permissions | `~/novapcb/.claude/settings.local.json` | **Gitignored** — per-machine |

### 9.1 Implication

When a fresh Claude (different account, different Pi) clones this repo, it starts cold with:
- All of `CLAUDE.md` (this file)
- All of `docs/`
- Git history

It does **not** start with memory or transcripts. So anything load-bearing must live in this file or in `docs/`, not in auto-memory. This file is the single source of project truth for cross-machine work.

### 9.2 If you need to physically move memory (rare)

```bash
# Path hash is derived from the absolute project path:
#   /home/novaedge1/novapcb  →  -home-novaedge1-novapcb
# Destination path must match exactly, or rename the hash dir to fit.

rsync -av ~/.claude/projects/-home-novaedge1-novapcb/ \
          user@otherpi:~/.claude/projects/-home-novaedge1-novapcb/
```

But the cleaner pattern is: **promote anything that matters into this file**. Memory is for ephemeral or personal notes; CLAUDE.md is for what should travel.

---

## 10. Build host environment

Documented so a new Claude on a fresh clone knows what tools to expect (or install).

### 10.1 Hardware

- Raspberry Pi 5, 16 GB RAM
- Hailo-8 NPU hat
- Fresh SD card (Bookworm 64-bit, kernel 6.12.x)

### 10.2 Software stack (on the build host as of 2026-05-18)

| Tool | Version | Use |
|---|---|---|
| Git | 2.x (`/usr/bin/git`) | source control |
| `gh` | 2.46.0 | GitHub CLI; HTTPS auth, token in keychain |
| Docker | running (drone-side stack) | not used directly for PCB work, but containers are running |
| HailoRT | 4.23.0 firmware | for the NPU; not relevant to PCB |
| KiCad | not installed yet (TBD) | will be installed when schematic work starts |

### 10.3 Where related projects live on the build host

These are *not* part of this repo but are referenced by docs. If you're on a different Pi and these paths don't exist, that's fine — the relevant excerpts are embedded in this file.

```
~/novapcb            this repo
~/drone_handoff      drone-side software brief + smoke test (PROMPT.md, drone_smoke.py)
~/novaros            ROS2 + MAVROS + docker stack on the drone Pi
~/novaapp_recovery   phone app handoff materials
~/drone_side_redesign_prompt.md       CH7 12-pos / CH8 layered ops redesign brief
~/drone_side_stage_abc_prompt.md      end-to-end coordinated validation brief
```

---

## 11. Locked decisions (2026-05-18)

Authoritative copy is `docs/DECISIONS.md`. Summarized here so a cold Claude doesn't have to context-switch. All 9 v1 scoping decisions signed off 2026-05-18.

1. **MCU** — STM32H743VIT6.
2. **Form factor** — v1: Pixhawk-standard 30.5 × 30.5 mm M3 single-PCB (functional drop-in; airframe gets a new tray). v2: FMUv6X mechanical drop-in (deferred — see `docs/OPEN_QUESTIONS.md`).
3. **ESC channels** — 8 (DShot300/600 preferred, PWM fallback).
4. **ELRS RX integration** — external RX module + on-board CRSF UART; no on-board RF in v1.
5. **Voltage / current monitoring** — external Mauch power module via FC ADC input.
6. **microSD logging** — yes; standard slot for ArduPilot `.bin` logs.
7. **Connector standard** — JST-GH (Pixhawk family).
8. **PCB stack-up** — 4-layer for v1; 6-layer reserved for v2 if on-board RF lands.
9. **USB VID/PID** — ArduPilot allocation (request via forum when needed); meanwhile `USB_VENDOR_STRING` starts with `ArduPilot` for udev by-id resolution.

For new questions that arise from here on, use `docs/OPEN_QUESTIONS.md` per Rule 8.

---

## 12. Glossary

Domain-specific terms used throughout the docs.

- **ArduPilot** — open-source autopilot firmware. ArduCopter is the multirotor variant.
- **AOA** — Android Open Accessory; USB host-role protocol the phone uses to talk to the ground bridge Pi.
- **BEC** — Battery Eliminator Circuit; 5 V regulator off the main battery, usually inside an ESC.
- **BLE GATT** — Bluetooth Low Energy Generic Attribute Profile; the protocol the drone Pi uses to expose pre-flight RPC to the phone.
- **CRSF** — Crossfire/ELRS serial protocol; 420 kbaud half-duplex RC + telemetry.
- **Holybro Pixhawk 6X** — FMUv6X-family autopilot, STM32H743-based, two-board (FMU + isolated IMU); what novapcb replaces. ArduPilot hwdef: `Pixhawk6X`.
- **CubeOrange+** — Cube-family autopilot, STM32H757-based; not the active reference, mentioned historically.
- **DRC / ERC** — Design Rule Check / Electrical Rule Check in KiCad.
- **DShot** — digital ESC protocol (300/600/1200 kbit/s); preferred over PWM.
- **ELRS** — ExpressLRS; long-range RC link, 868/915 MHz, sub-GHz.
- **FastAPI** — the Python web framework running on `:8080` on the drone Pi; owns calibration / mission / params endpoints.
- **FC** — Flight Controller. The board this repo designs.
- **FOC** — Field-Oriented Control; ESC type for the separate 60 A ESC project.
- **hwdef.dat** — ArduPilot board definition file; pin map, peripheral assignment, board ID.
- **MANUAL_CONTROL** — MAVLink message for direct stick inputs.
- **MAVLink** — the autopilot wire protocol. v2 dialect = ArduPilot.
- **MAVROS** — ROS node that bridges MAVLink ↔ ROS topics.
- **NovaApp** — the phone-side Android client (Kotlin/Compose).
- **NPU** — Neural Processing Unit; the Hailo-8 hat on the drone Pi runs vision inference.
- **Pixhawk** — open hardware autopilot family; we mimic its form factor and software interface.
- **RP4TD** — an ELRS receiver variant; what the drone-side Pi sees as the RC source.
- **udev by-id** — Linux kernel feature for stable `/dev/serial/by-id/...` names independent of plug order.
- **VRX / VTX** — Video Receiver / Video Transmitter; analog or digital video downlink hardware.

---

## 13. When in doubt

- Re-read §0 (TL;DR), §3 (Interface Contract), §4 (Known Traps), and §7 (Rules).
- If the answer isn't here, check `docs/`.
- If it isn't in `docs/`, ask the user with one specific statement of intent. Don't guess.
- If you guessed and it was wrong, fix it, save the correction to memory, and consider whether this file needs updating.

This file is meant to grow. When you learn something that should be on this list, add it. Keep sections numbered; don't reorder.

— End of CLAUDE.md —
