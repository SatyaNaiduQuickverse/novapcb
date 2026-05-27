# eFuse status flags (EFUSE_FLT / EFUSE_PGOOD) — v1 defer

> **Tracked deferral, not a defect.** EFUSE_FLT (U6.20) and EFUSE_PGOOD (U6.2)
> are left unrouted in v1. Whitelisted in `scripts/audit_unconnected_per_net.py`
> (`INTENDED_DEFERRED`) alongside MOT7/8, Telem (USART1), SWD. Decided
> 2026-05-27 (Phase 4d-redux D3 closure).

## Why it's safe to defer

The eFuse U6 (TPS25940A) protection is **autonomous in hardware**. Overcurrent,
overvoltage, reverse-current, and thermal events trigger the internal pass-FET
cutoff *regardless* of whether the MCU observes the status pins. The protected
rail (+5V_BEC) is safe with or without the flags wired.

EFUSE_FLT (active-low fault) and EFUSE_PGOOD (power-good) are **open-drain status
outputs** intended only to give the MCU *awareness* of an eFuse event — so
firmware could log it or raise a GCS alert. They are **not** part of any control
or safety loop.

Nova drone v1 has **no fault-handling pipeline** for eFuse state (no ArduPilot
parameter, no GCS alert path consumes these). Wiring them to MCU GPIO is a v2
firmware enhancement, not a v1 essential. The schematic nets are 2-pad each
(U6 flag pin + pull-up resistor R13/R5 to +5V) — there is no MCU-GPIO node on
the net to route to in any case.

## Geometry context (why they were hard, and why deferring is the right call)

R13/R5 (the flag pull-ups) sit ~17 mm from U6's flag pins (near the MCU edge,
X43–44, vs U6 at X26–27). Routing the open-drain flags across that span — through
the dense central band — would consume routing resource for a non-essential v1
feature. Per Rule-4 (match scope) and the autonomous-protection rationale above,
deferring is correct, not a compromise.

## v2 action

When the v2 firmware adds eFuse fault logging/alerts: route EFUSE_FLT → R13 and
EFUSE_PGOOD → R5 (and add the MCU-GPIO leg if monitoring is wanted), then remove
both from the `INTENDED_DEFERRED` whitelist so the audit re-flags any gap.
