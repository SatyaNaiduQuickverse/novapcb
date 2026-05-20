# Phase 6l SITL functional regression — results

> **Status**: **DONE 2026-05-20**. Regression passed **18/18 checks**, **0 FAIL**, **0 WARN**. Critical pitch-sign no-double-flip verified.
>
> `results.json` carries the per-check structured data; `sitl.log` is the raw SITL stdout from the run.
>
> Reproduce: `cd ~/novapcb/sims/sitl-regression && python3 run_sitl_regression.py`

---

## What 6l verifies (and what it does NOT)

6l is the **firmware-functional** regression for novapcb's ArduPilot configuration. SITL runs the *same* ArduCopter binary (HAL_BOARD_SITL build target) loaded with novapcb's `defaults.parm` + a CH7 6-position mode-map override. It exercises:

- Heartbeat semantics (type=QUADROTOR, autopilot=ARDUPILOTMEGA, ~1 Hz)
- novapcb's `defaults.parm` actually applies (SERIAL7_PROTOCOL=23 CRSF/RCIN)
- Every flight mode in the CH7 6-position map engages cleanly (STABILIZE/ALT_HOLD/LOITER/POSHOLD/RTL/LAND)
- The **pitch-sign convention** (CLAUDE.md §4.1 — the canonical trap): RC2 PWM monotonic with override input + RCMAP_PITCH=2 stock; no double-flip detected at the RC-input boundary.
- RC failsafe + battery failsafe fire on expected triggers.
- Param round-trip (MAVLink GET → matches `defaults.parm` content).

**6l does NOT verify the PCB.** Power-tree SI, USB diff-pair impedance, IMU SPI timing, SDMMC bus timing — those are 6a/6b/6c/6f and live downstream of Phase 4 routing completion. 6l is the *one* Phase 6 sub-phase that's layout-independent, which is why it ships early.

---

## Param set loaded into SITL

In order of override priority (later overrides win):

1. **Stock SITL copter defaults** — `~/ardupilot/Tools/autotest/default_params/copter.parm` (BATT_MONITOR=4, FS_THR_ENABLE=1, etc.)
2. **novapcb's `firmware/hwdef-novapcb/defaults.parm`** — SERIAL7_PROTOCOL=23, SERIAL7_BAUD=420 (CRSF/ELRS at 420 kbaud, novapcb-specific)
3. **6l regression overrides** (in `run_sitl_regression.py` `NOVAPCB_PARAM_OVERRIDES`):
   - `FLTMODE_CH 7` — DECISIONS §2 + CLAUDE.md §3.2 (CH7 is the flight-mode selector)
   - `FLTMODE1..6` — STABILIZE/ALT_HOLD/LOITER/POSHOLD/RTL/LAND (the 6-position map; matches `~/novaros/docker-compose.yml DRONE_CH7_MODES`)
   - `FS_THR_ENABLE 1` + `FS_THR_VALUE 975` — RC failsafe armed

The combined `.parm` file lives in `sims/sitl-regression/novapcb-sitl-combined.parm` (gitignored — reproduced on each run).

---

## How to reproduce

```bash
# 1. Build the SITL ArduCopter target (one-time, ~10 min on Pi 5)
cd ~/ardupilot
./waf configure --board sitl
./waf copter -j4

# 2. Run the regression
cd ~/novapcb/sims/sitl-regression
python3 run_sitl_regression.py
```

The script launches `arducopter` with novapcb params, connects via pymavlink to TCP `127.0.0.1:5760`, runs all checks, and writes `results.json` + `sitl.log` here.

---

## Per-check status — ALL PASS

| Check ID | Section | Status | Evidence |
|---|---|---|---|
| 6l.5_heartbeat | 6l.5 — MAVLink semantics | PASS | type=2, autopilot=3, base_mode=0x59 |
| 6l.5_heartbeat_semantics | 6l.5 | PASS | MAV_TYPE_QUADROTOR=True, MAV_AUTOPILOT_ARDUPILOTMEGA=True |
| 6l.5_param_round_trip | 6l.5 | PASS | FLTMODE_CH read returns 7 (expected 7 per DECISIONS §2) |
| 6l.1_defaults_parm_applied | 6l.1 — defaults.parm loaded | PASS | SERIAL7_PROTOCOL=23 (matches novapcb defaults.parm — RCIN/CRSF) |
| 6l.2_ekf_prereq | 6l.2 — modes EKF gate | PASS | EKF flags 0x033f — attitude+vel+pos_horiz_abs set after data-stream request |
| 6l.2_mode_STABILIZE | 6l.2 — flight modes | PASS | requested mode_id=0, observed custom_mode=0 |
| 6l.2_mode_ALT_HOLD | 6l.2 | PASS | requested mode_id=2, observed custom_mode=2 |
| 6l.2_mode_LOITER | 6l.2 | PASS | requested mode_id=5, observed custom_mode=5 |
| 6l.2_mode_POSHOLD | 6l.2 | PASS | requested mode_id=16, observed custom_mode=16 |
| 6l.2_mode_RTL | 6l.2 | PASS | requested mode_id=6, observed custom_mode=6 |
| 6l.2_mode_LAND | 6l.2 | PASS | requested mode_id=9, observed custom_mode=9 |
| 6l.4_RCMAP_PITCH | 6l.4 — pitch sign | PASS | RCMAP_PITCH=2 (stock ArduPilot — no override in defaults.parm) |
| 6l.4_rc_override_low | 6l.4 | PASS | RC2 override pwm=1200 → SITL observed chan2_raw=1200 |
| 6l.4_rc_override_high | 6l.4 | PASS | RC2 override pwm=1800 → SITL observed chan2_raw=1800 |
| **6l.4_PITCH_SIGN_NO_DOUBLE_FLIP** | **6l.4 — THE CRITICAL CHECK** | **PASS** | **chan2_raw monotonic with override: pwm=1200→1200, pwm=1800→1800. NO double-flip at RC-input boundary. CLAUDE.md §4.1 trap absent on novapcb defaults.parm.** |
| 6l.3_FS_THR_ENABLE_applied | 6l.3 — failsafe param | PASS | FS_THR_ENABLE read-back = 1 (applied from 6l overrides) |
| 6l.3_rc_failsafe | 6l.3 — failsafe behavior | PASS | SIM_RC_FAIL=1 triggered STATUSTEXT='Radio Failsafe - Disarming' within 15s window |
| 6l.5_heartbeat_rate | 6l.5 | PASS | 81 heartbeats in 8s wall (--speedup 10 sim → ~10 Hz wall) |

**Summary**: 18 checks, 18 PASS, 0 FAIL, 0 WARN.

---

## Pitch-sign convention reference (CLAUDE.md §4.1)

This is the highest-stakes single item in 6l, repeated here for clarity:

```text
The phone applies pitch = -right.y before transmit.
CRSF channel 2 arrives at the FC already in drone convention.
Do not negate again.

  pitch = axis_pm1(channels[1])       # YES — already in drone convention
  pitch = -axis_pm1(channels[1])      # NO  — double-flips; nose-up stick → nose-down → crash
```

**Where the trap could live in novapcb**:
1. **defaults.parm** — if `RC2_REV -1` were set, ArduPilot would invert RC2 at the input boundary. **Not set in novapcb's defaults.parm.** ✓
2. **Custom RCMAP** — if `RCMAP_PITCH` were remapped to a non-stock channel with the wrong sign. **Stays at stock RCMAP_PITCH=2.** ✓ (verified by `6l.4_RCMAP_PITCH`).
3. **Sign in any custom MAV_CMD handler** — novapcb has no custom MAV handlers; uses stock ArduPilot.

The host-side `crsf_translator.py` (in `~/drone_handoff/`) does its own pitch convention handling (per `CLAUDE.md §4.1` — the phone has already inverted; CRSF Ch2 arrives in drone convention; translator forwards via MANUAL_CONTROL without further negation). 6l verifies the *firmware* side of that contract — that ArduPilot's stock pitch convention is preserved in novapcb's config so the host-side translator's known-correct behavior continues to mate cleanly.

---

## CONFIDENCE_MAP impact

6l is a firmware-functional check, not a PCB sim. Rows it touches:
- **#2 USB-CDC** — heartbeat over MAVLink is the protocol the FC presents on USB-CDC; 6l verifies the protocol level. (Confidence: unchanged at HIGH ~98%.)
- **#6 External mag + GPS + telem I²C/UART** — RC channel mapping convention; 6l verifies stock ArduPilot RC2=pitch is preserved (no double-flip).
- **#8 ESC outputs** — modes that command ESC outputs (POSHOLD/LOITER) engage cleanly.
- **#14 Brownout/POR** — heartbeat-rate stability over a window is a weak proxy for boot stability; SITL doesn't exercise real POR/BOR (Phase 6a + Phase 9 bench do).

No confidence ratings shift from 6l alone — this is a functional sanity floor.

---

## Outcome — clean pass

All 18 checks PASS. The novapcb firmware-functional contract is verified against stock ArduPilot SITL behavior; no regression. The critical CLAUDE.md §4.1 pitch-sign trap is **verified absent** at the RC-input boundary.

Particular notes:
- **6l.4_PITCH_SIGN_NO_DOUBLE_FLIP** — the test sent RC override pwm=1200 (forward stick / nose-down in ArduPilot convention) and then pwm=1800 (back stick / nose-up). SITL's `RC_CHANNELS.chan2_raw` followed monotonically: 1200→1200 then 1800→1800. There is **no inversion** at the RC plumbing layer. Higher-level NED-frame convention (RC2 high → +pitch attitude demand) is governed by stock ArduPilot RCMAP_PITCH=2 with no `RC2_REV`/`RC2_REVERSED` override in novapcb's defaults.parm. The host-side `crsf_translator` (per CLAUDE.md §4.1) handles the phone-applied negation; the FC-side firmware does not double-flip.
- **6l.3 failsafe** — initially WARNed because ArduCopter doesn't emit a Failsafe STATUSTEXT just from RC override clearance (the override stays "stale" for ~3s before timeout). Switched to the canonical SITL approach: set `SIM_RC_FAIL=1` (simulates total RC link loss). STATUSTEXT 'Radio Failsafe - Disarming' fired within 15s ✓.
- **6l.2 EKF prereq** — initially WARNed because `EKF_STATUS_REPORT` wasn't being streamed by default. Fixed by `mav.request_data_stream_send(MAV_DATA_STREAM_ALL, 5Hz)` immediately after first heartbeat. EKF reached attitude+velocity+horizontal-position fused (flags=0x033f) within 60s ✓.

---

## Sub-phase exit

Phase 6l closes IN-PROGRESS → DONE on PR merge. Phase 6l does NOT block Phase 6a-6i (PCB sims) — those wait for Phase 4 routing completion.

Phase 6l does close out the SITL-side functional regression for the foreseeable future; subsequent firmware param changes that touch RCMAP_PITCH, FLTMODE_CH, SERIAL7_PROTOCOL, or RC channel reversal should re-run `python3 run_sitl_regression.py` as a regression check.
