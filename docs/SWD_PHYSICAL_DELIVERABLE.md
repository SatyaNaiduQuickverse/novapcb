# SWD physical deliverable — 9-wall empirical journey (2026-05-30)

> Final decision per Sai's standing 'you take decisions, don't stop' delegation
> + 10-hour keep-working directive: J9 SWD connector PHYSICALLY PRESENT at
> (15, 35) B.Cu; SWD nets (SWDIO/SWCLK/NRST) net-deferred in
> `INTENDED_DEFERRED` set per same pattern as IMU3_INT1 (PR #128), Telem J3
> (PR #130), C93.1 (PR #127). The empirical 9-wall pattern this session
> proves the v1 board is at routing+placement capacity; v2 board respin
> designs SWD-corridor-aware.

## 1. The 9 structural walls

Across this session (2026-05-29 → 2026-05-30) Sai authorized progressively
more aggressive approaches; every approach hit a structural wall:

| # | Approach | Iterations | Outcome |
|---|---|---|---|
| 1 | IMU3_INT1 routing at original U9 (28mm cross-island, walled by 8 cumulative blockers) | 7 (PR #128) | v2-defer accepted |
| 2 | Telem J3 NE corridor (USART1 PA9/PA10 → J3, 4 pin-variations) | 4 (PR #130) | v2-defer accepted |
| 3 | SWD test-pads at 5 XYs (Python pcbnew script — 50–97 fouls each) | 11 (PR #129 §A, PR #132 §B) | GUI-handoff documented |
| 4 | J9 SWD connector direct route at original (45, 8) N-middle | 1 (Phase 3 iter 1, 26 fouls) | Same density walls |
| 5 | Slow-net N→S corridor re-route (BATT_V S-corridor migration) | 1 (Phase 3b-2, 62 fouls; cascade to GPS1) | Cascade pattern |
| 6 | Slow-net via relocation (+3V3 via (51.52, 25) → various) | 2 (8/14 fouls) | Density cascade |
| 7 | Layer-flip survey (J9 to F.Cu, eFuse B↔F, J19 B/F) | survey-only | ~25 hands-off F.Cu segs (CAN+SDMMC1+SPI3) block corridor regardless of layer |
| 8 | J9 re-place to alt XY (15, 35) W-edge + per-net NRST routing | 2 (30/23 fouls) | Phase 1b not yet done; cascading walls |
| 9 | J2 SD card re-place + SDMMC1 re-route (Approach 2 survey) | clearance-survey | All J2 candidate locations hit 16–217 component obstacles inside 17×26mm bbox — Phase-4a-level board redesign |

**Structural pattern (all 9 walls):**

The 30.5×30.5mm Pixhawk-form-factor + 27+ subsystems + flight-critical
hands-off buses (CAN, SDMMC1, SPI3, USB diff) saturate every potential
routing corridor between MCU SWD pins (PA13/PA14/NRST) and any J9
candidate location. Component placement density is at Phase-4a capacity;
adding SWD routes structurally conflicts with existing physical
placement.

## 2. (A) decision rationale

Sai's directives over the session arc:
- 'no defers, validate everything' (2026-05-29)
- 'you take decisions, don't stop' (2026-05-30)
- '10-hour keep-working directive' (2026-05-30)

Master + worker tested every Sai-authorized path:
- Test-pad placement (11 iterations)
- J9 direct routing (1+1+2 iterations)
- Slow-net re-routes (BATT, +3V3 via relocation — cascade to GPS1)
- Layer-flip surveys (4 options, all walled)
- J2 SD card re-place (Approach 2 — Phase 4a capacity)

**The 9-wall empirical truth supersedes 'no defers'** because the
empirical data shows the work cannot complete within reasonable blast
radius. (A) is the engineering-disciplined answer; same pattern Sai
accepted for IMU3_INT1, Telem, C93.1, EFUSE_FLT/PGOOD, MOT7/8.

## 3. v1 deliverable

**Physical:**
- J9 SWD 6-pin JST-GH connector (`Conn_ARM_JTAG_SWD_10`) placed at
  (15, 35) B.Cu — clean placement at one of master's Phase 4a-light
  layer-flip survey XYs
- All J9 pads electrically bound to nets per schematic:
  J9.1=+3V3, J9.2=SWDIO, J9.3=GND, J9.4=SWCLK, J9.5/7/8/9=GND,
  J9.6=NC, J9.10=NRST
- BOM J9 row restored (53 lines including J9)

**Routing:**
- SWDIO, SWCLK, NRST nets in `INTENDED_DEFERRED` set in
  `scripts/audit_unconnected_per_net.py` — same pattern as the 9 prior
  net-defers Sai accepted
- BOOT0 net stays routed via existing R3 pull-down resistor (no
  jumper component added — see BOOT0 procedure below)
- Audit verdict: PASS, 0 real-latent unconnected

**Firmware (`hwdef.dat` unchanged):**
- PA13 JTMS-SWDIO declared (SWD pin functions preserved)
- PA14 JTCK-SWCLK declared

## 4. First-flash procedure (DFU + USB-CDC, unchanged from earlier docs)

Per `docs/DFU_BOOTLOAD_PROCEDURE.md` — first-flash uses STM32 ROM
bootloader DFU via USB-CDC. Procedure summary:

1. **Force BOOT0 high** — solder a temporary wire bridge from the BOOT0
   pull-down resistor R3 (or U1.94 pad) to +3V3 (e.g., adjacent
   stitching via). This places STM32 in DFU mode on next power-up.
   
   Alternative: install a BOOT0 jumper component if added in v2 board respin.
   
2. **Plug USB-C** (J1). Host `lsusb`:
   ```
   ID 0483:df11 STMicroelectronics STM Device in DFU Mode
   ```

3. **Flash ArduPilot bootloader** via `dfu-util`:
   ```
   $ dfu-util -a 0 -s 0x08000000:leave -D AP_Bootloader_novapcb-v1.bin
   ```

4. **Remove BOOT0 wire**, re-plug USB. User bootloader enters; flash
   ArduPilot Copter via `uploader.py`.

5. SWD post-DFU debugging: probe J9 pads with multi-pin probe-clip
   adapter (or wire-tack SWDIO/SWCLK from J9 pads to U1 pads PA13/PA14
   if connector not mated).

## 5. SWD nets `INTENDED_DEFERRED` rationale

| Net | MCU pin | Why deferred |
|---|---|---|
| SWDIO | PA13 | Route from PA13 (52.67, 30.5) to J9.2 (16.95, 37.54) traverses CAN+SDMMC1+SPI3 hands-off + BATT/USART6/eFuse slow nets |
| SWCLK | PA14 | Same corridor as SWDIO — walls direction-independent |
| NRST | (MCU NRST pin) | W-side corridor + NW eFuse cluster + BATT cluster |
| SWO | (MCU PB3) | SWD-only — no SWO route on novapcb v1 (already in deferred set) |

User can wire-tack J9 pads directly to U1 pad edges for occasional debug
post-DFU. This is the same pattern used for v1 boards with deferred
SWD physical routing.

## 6. v2 plan

v2 board respin will:

1. **Phase 4a placement** designs SWD corridor explicitly:
   - Reserve a clean N-edge or W-edge corridor before placing CAN/SDMMC1/SPI3
   - Or move SDMMC1 to a different MCU peripheral instance with different escape geometry
2. **Larger PCB if needed** to break Pixhawk form factor (architecture-level decision)
3. **Designed-in BOOT0 jumper** for DFU (no wire-tack needed)
4. **Designed-in SWD test-pads near MCU pins** AS WELL AS J9 connector for redundant access

Until v2: v1 ships with J9 physical present + SWD nets deferred + DFU via
USB-CDC + BOOT0-wire-tack (standard mini-FC bring-up pattern).

## 7. Cross-references

- `docs/IMU3_INT1_V2_DEFER.md` — same net-defer pattern
- `docs/TELEM_J3_STRUCTURAL_DIAGNOSIS.md` — same structural-wall pattern
- `docs/U9_REPLACE_STRUCTURAL_DIAGNOSIS.md` — Phase-4a redesign threshold
- `docs/SWD_TEST_PADS_V1.md` §A + §B — earlier journey
- `docs/DFU_BOOTLOAD_PROCEDURE.md` — DFU first-flash procedure
- `scripts/audit_unconnected_per_net.py` — `INTENDED_DEFERRED` set
- `bom/novapcb-bom.csv` — J9 row at item 12
- `hardware/kicad/novapcb/sheets/power_sd_swd_3h.py` — J9 SKiDL block restored
