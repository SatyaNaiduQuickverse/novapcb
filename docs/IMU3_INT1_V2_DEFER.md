# IMU3_INT1 v2-defer (2026-05-29)

> Net-deferred to v2 per `audit_unconnected_per_net.py` `INTENDED_DEFERRED` whitelist.
> Structural finding after 5/5 walled route attempts at 3 placement candidates.
> Master + Sai (delegated) sign-off 2026-05-29.

## What is deferred

`IMU3_INT1` — the LSM6DSV16X (U9) INT1 sample-ready interrupt → MCU PB2 (EXTI2).
The net is wired in the schematic but **physically unrouted on the v1 PCB**.
Component populated; pin acts as a no-connect on the assembled board.

## Why it is safe in v1

ArduPilot's IMU driver supports **polled-mode** sampling for any backend:
configure `INS_USE3 = 1` + `INS_FAST_SAMPLE_3 = 1`, the driver polls the
LSM6DSV16X over SPI3 at ~1 kHz instead of waiting on INT1. Functionally
equivalent for an autopilot-tier IMU; loses only the ability to capture
chip ODR rates above the polling rate (LSM6DSV16X ODR up to 6.7 kHz).

**Triple-IMU redundancy preserved:**

| IMU | Chip | Mode | INT wired? |
|---|---|---|---|
| IMU1 (primary) | ICM-42688-P (U3) | INT-driven | ✓ |
| IMU2 (secondary) | BMI088 (U8) | INT-driven (ACC_INT1 + GYR_INT3) | ✓ |
| IMU3 (tertiary) | LSM6DSV16X (U9) | **polled @ ~1 kHz** | ✗ (v2) |

Loss is "third-IMU INT rate" — well within ArduPilot triple-IMU voting
tolerance. The two INT-driven IMUs (IMU1+IMU2) handle high-rate sampling;
IMU3 polled adds redundancy + sanity-check against the other two.

## Why deferring is the disciplined call (5/5 structural data points)

`docs/U9_REPLACE_STRUCTURAL_DIAGNOSIS.md` captures the full audit. Summary:

| # | Approach | Placement | Result |
|---|---|---|---|
| 1 | Manual route at original U9 (78, 57) | original | 8 cumulative walls (SPI3/SPI2/MCU pocket density + +3V3_IMU rail loop) |
| 2 | Full-DSN Freerouting | original | 9 h CPU, no SES (search-space wedged) |
| 3 | Manual SPI3 at C2 (55.5, 44.0) | C2 re-place | 79 fouls after 2 iterations |
| 4 | Manual SPI3 at C1 (58, 45.5) | C1 re-place | 97 fouls (N-wrap geometry) |
| 5 | Scoped FR at C1 (5 nets + rail tail) | C1 re-place | 30-min cap, no SES (search-space still wedged) |

The board's late-Phase-4d-redux density (8+ existing nets transiting any
MCU→U9 path on both layers) walls any re-route within reasonable blast
radius. Continuing the grind would require either:
- 2-3 days of per-foul cluster surgery on existing-net coordinates, or
- a Phase-4a-level placement redesign (out of scope for v1).

## v2 plan

v2 board respin (post-v1 flight) re-architects the IMU island around the
**IMU-at-center principle** (Sai 2026-05-28):

1. **Triple-IMU CG correlation** — place all three IMUs within ≤10 mm of
   board geometric center, designed in from Phase 4a (not bolted on at
   Phase 4d). U9 moves to under-MCU B.Cu by design, with the routing
   channels for SPI3/IMU3_CS/IMU3_INT1 reserved up front.
2. **IMU3_INT1 INT-driven** — wired through reserved short-via stack to
   MCU PB2 (or re-pin to an even shorter route).
3. **Polled-mode fallback retained** for redundancy.

## Firmware reference

ArduPilot `AP_InertialSensor_LSM6DSV16X.cpp` polled-mode usage:
- `INS_USE3 = 1`
- `INS_FAST_SAMPLE_3 = 1`
- `_polled_sampling = true` (set in driver init when INT pin not configured)
- No `hwdef.dat` EXTI directive needed; pin can be left as `INPUT` or
  removed from `hwdef.dat` entirely.

## Audit impact

`scripts/audit_unconnected_per_net.py` `INTENDED_DEFERRED` set extended to
include `IMU3_INT1`. Audit verdict returns to PASS. Same pattern as
`C93.1` pad-defer (PR #127) and the existing `MOT7`/`MOT8`/`USART1_*`/
`SW*`/`EFUSE_FLT`/`EFUSE_PGOOD` net-defers.

## Cross-references

- `docs/U9_REPLACE_STRUCTURAL_DIAGNOSIS.md` — full 5/5-attempt audit
- `docs/D5_3V3_IMU_DEFERRED_DECAPS.md` — C93.1 pad-defer pattern (same
  whitelist mechanism, pad-level instead of net-level)
- `scripts/audit_unconnected_per_net.py` — INTENDED_DEFERRED set
- ArduPilot polled-mode IMU: `libraries/AP_InertialSensor/`
