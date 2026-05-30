# SWD — v1 test-pads + USB DFU bootload decision

> **Status:** **MASTER-DECIDED 2026-05-28** (Sai delegated: "its your call you know rules"). Implement: defer J9 connector, add 5 labeled test-pads + BOOT0 jumper near MCU, first flash via STM32H7 ROM DFU mode (`dfu-util`).

> ~~Status: master draft 2026-05-26, awaiting Sai ratification.~~
> **Trigger:** task #56 empirically proved SWDIO/SWCLK cannot escape the MCU NE-saturated zone to J9 @ X=47 in v1 without surgical multi-wall F↔B weave + nudges. Master scope-pragmatism call: replace the J9 6-pin SWD connector with bare test-pads (or remove entirely) and use USB DFU bootload for initial flash. SWD as a debug-time pogo-pin/wire-tack tool only.

---

## 1. What this changes

| Item | v0/v1-with-J9 | v1 deferred to test-pads |
|---|---|---|
| J9 6-pin JST-GH SWD connector | placed on board, traces unroutable per #56 | **REMOVED** (or kept as DNP footprint) |
| SWDIO (PA13) routing | MCU east-edge → J9 W-edge: ~6mm with multi-wall F↔B weave | MCU pad → adjacent 1.5mm exposed test-pad (~2mm direct, no traversal) |
| SWCLK (PA14) routing | same as above | same as above |
| NRST (J9.10) | already routed in v1 (FR completed pre-#56) | re-route to a test-pad OR keep as-is if it lands cleanly without J9 |
| Initial firmware flash | SWD pogo or J9-cable into ST-LINK | **USB DFU mode** via BOOT0 jumper + dfu-util |
| Field debug | J9 cable | wire-tack onto test-pads (pogo-pin jig optional) |

## 2. Why this is safe — STM32H7 DFU bootloader

The STM32H743 has a factory-burned ROM bootloader (System Memory) that supports USB DFU mode on the OTG_FS port (PA11/PA12, our J6 USB-C). Entry: hold BOOT0 high + power cycle. Application: `dfu-util` from the drone Pi pushes the ArduPilot bootloader once, after which all firmware updates use ArduPilot's own USB-CDC bootloader.

**The one-time flash to bootstrap ArduPilot does NOT need SWD.**

After initial DFU flash:
- All ArduPilot updates: USB-CDC via Mission Planner / `--upload` waf target / `uploader.py`.
- Param tweaks / log download: MAVLink over USB-CDC.
- SD card log download: physical card or MAVLink FTP.

SWD becomes a *debug* tool — needed only for:
- Live single-step debugging (rare; ArduPilot is usually printf-debugged).
- Recovery from corrupted ArduPilot bootloader (very rare; DFU recovers anyway).
- ROM bootloader read-protection unlock (not a v1 concern).

For v1 bring-up (Sai's first 5 boards), the test-pad pattern is sufficient. Pogo-pin jig or wire-tack works for the rare debug session.

## 3. Concrete delta

**Board (.kicad_pcb):**
- Remove J9 footprint (6-pin JST-GH SWD connector).
- Add BOOT0 jumper pads near the MCU (2× 1.27mm pads, normally bridged to GND, jumpered to +3V3 for DFU entry).
- Add labeled test-pad pattern for SWD + reset signals:
  - TP_SWDIO — exposed 1.5mm circle near PA13 pad
  - TP_SWCLK — exposed 1.5mm circle near PA14 pad
  - TP_NRST — exposed 1.5mm circle near U1 NRST pin
  - TP_GND — exposed 1.5mm circle near a GND via
  - TP_+3V3 — exposed 1.5mm circle for power probe
- Silkscreen: label each pad clearly; this is a Sai-facing convenience.
- BOM: remove J9 row (1× JST-GH SM06B-GHS-TB).

**Schematic (SKiDL):**
- Comment out the `J9` instantiation.
- Add a `# v1: SWD via test-pads + USB DFU; J9 deferred to v2` marker.

**Firmware (hwdef.dat):**
- **NO CHANGE.** PA13/PA14 stay declared as SWD pins. The MCU pads simply terminate at test-pads rather than a connector.
- ArduPilot's DFU mode is built into the chip ROM — no firmware-side enable needed.

**Docs:**
- `docs/INTERFACE_CONTRACT.md` — add a section: v1 first-flash procedure (DFU via BOOT0 + `dfu-util`).
- `docs/PHASE7A_FREEZE_PROCEDURE.md` — update Phase 8 bring-up: replace "ArduPilot v4.6.3 flash via SWD (J9 header)" with "ArduPilot v4.6.3 flash via USB DFU".
- New: `docs/DFU_BOOTLOAD_PROCEDURE.md` (or fold into Phase 8) — exact `dfu-util` command, ArduPilot bootloader binary path, expected output.

## 4. Why this is safe to defer (not a regression)

| Concern | Resolution |
|---|---|
| "Will Sai actually be able to flash the board?" | Yes. `dfu-util` works from any Pi/Linux host. The drone Pi already has USB-host capability. ST publishes the DFU class descriptor for H7 ROM bootloader. Procedure is documented in ST AN2606. |
| "What if the ArduPilot bootloader gets corrupted on a bad flash?" | Re-enter DFU mode (BOOT0 high + power cycle) and re-flash. SWD is NOT needed for bootloader recovery — DFU IS the bootloader recovery path. |
| "What if a board fails mysteriously in the field?" | Bring it back to bench, wire-tack onto TP_SWDIO/SWCLK pads with a $5 SWD-flying-lead adapter. Recovery time: ~5 min vs ~30s with a J9 cable. Acceptable for v1 (Sai's 5-board first article). |
| "Does this affect the Pixhawk 6X functional drop-in claim?" | Marginally. 6X has J9 SWD connector. v1 ships with test-pads instead. Cosmetic / convenience difference; the *electrical* SWD interface still exists on PA13/PA14. |
| "What about JTAG / 5-wire debug?" | Not used; ArduPilot uses 2-wire SWD universally. Not a v1 or v2 concern. |
| "Does this delay anything?" | No — opposite. Removing J9 + adding test-pads unlocks the #56 routing blocker (SWDIO/SWCLK are the hardest 2 of the 6 escape nets). |

## 5. Sai ratification

Like the Telem defer, this changes the **physical board feature set** and the Phase 8 bring-up procedure. TRUE Sai-gate.

**Yes path:** master dispatches worker to (a) remove J9 from `.kicad_pcb`, (b) add 5 labeled test-pads near MCU PA13/PA14/NRST/GND/+3V3, (c) add BOOT0 jumper pads, (d) comment SKiDL J9 block, (e) update BOM, (f) write `docs/DFU_BOOTLOAD_PROCEDURE.md`, (g) update `PHASE7A_FREEZE_PROCEDURE.md` Phase 8.

**No path:** master keeps J9 placed + dispatches the multi-wall F↔B weave routing (hardest #56 class per `docs/CRSF_TELEM_SWD_ROUTING_ANALYSIS.md` §3). Burns ~1 PR per net (SWDIO + SWCLK = 2 PRs).

**Master recommendation: defer to test-pads + DFU.** STM32H7 DFU is rock-solid and standard ArduPilot bring-up uses it for non-J9 boards anyway. The J9 was a 6X form-factor heirloom; the actual electrical SWD interface still works via test-pads. Lower fab risk (fewer connectors to misalign), lower BOM, unblocks #56.

---

## §A. Implementation note — 2026-05-29

**Status:** Design intent documented; physical implementation **deferred to GUI follow-up PR**.

**Why:** Worker attempted J9 → test-pads + BOOT0 jumper surgery via Python `pcbnew` script (4 iterations). Each iteration produced 50–90 DRC fouls — TPs at the original J9 area (Y≈7) collided with the +5V plane on In4.Cu; TPs near U1 collided with U1's body courtyard + adjacent F.Cu pads; long BOOT0 routes crossed existing BATT_VOLTAGE_SENS + SDMMC1_CMD nets in the N-of-MCU area.

**Brutally-honest root cause:** Python `pcbnew` scripted placement of test-pad footprints + interactive routing is not the right tool for visual conflict resolution against an already-dense board. The KiCad GUI's interactive router (with shove + walk-around heuristics + visual confirmation) is the natural tool for this surgery.

**Split decision (master 2026-05-29):**
- **This PR (#129):** C96 value swap 10nF → 100nF (Path A ST conformance) + this implementation note. Board surgery NOT attempted.
- **Follow-up PR (task #68 GUI work):** worker on novatics64 opens `novapcb-stepwise.kicad_pcb` in KiCad 9.0.2 GUI, removes J9 footprint, places 5 labeled `TestPoint_Pad_D1.5mm` footprints near U1 SW-corner pin row, places `TestPoint_2Pads_Pitch2.54mm_Drill0.8mm` for BOOT0 jumper near U1.94, uses interactive router for short B.Cu traces (TP_SWDIO→U1.72, TP_SWCLK→U1.76, TP_NRST→U1.14, BOOT0 pad 2→U1.94), plane vias for TP_3V3 / TP_GND, DRC gate-clean.

**Designed placement targets (for the GUI PR):**

| Test pad | Net | Target XY | U1 pin |
|---|---|---|---|
| TP_SWDIO | SWDIO | ~(54, 30.5) B.Cu | U1.72 @(52.67, 30.50) |
| TP_SWCLK | SWCLK | ~(52, 26.0) B.Cu | U1.76 @(51.00, 27.32) |
| TP_NRST | NRST | ~(36, 36.5) B.Cu | U1.14 @(37.33, 35.50) |
| TP_3V3 | +3V3 | ~(55, 31.0) B.Cu | plane via |
| TP_GND | GND | ~(55, 33.0) B.Cu | plane via |
| BOOT0_DFU jumper | BOOT0 / GND | ~(41, 25.5) B.Cu | U1.94 @(42, 27.32) |

The GUI implementation may shift these XYs to clear local obstacles (U4 baro at (43, 47), +3V3 vias around (50.5, 44.95), MOT2 verticals, etc.) — visual placement is empowered to find the cleanest clear corners that meet the "near U1 SW corner" intent.

**v1 firmware impact:** NONE. `hwdef.dat` is unchanged. PA13/PA14 stay as SWD pins. DFU first-flash via USB-CDC + BOOT0-pull-high (via the jumper bridge or a temporary wire) — works whether or not the SWD test-pads are routed.

---

## §B. Implementation status update — 2026-05-29 (CLI-agent handoff to Sai GUI)

**Status:** SKiDL + BOM + docs delivered (this PR); physical board surgery
queued for Sai's pre-freeze KiCad GUI session.

**Why the handoff:**

CLI agent environment check (2026-05-29):
- `DISPLAY: NOT SET`, `WAYLAND_DISPLAY: NOT SET` — no X11 session
- KiCad 9.0.2 binaries installed (`/usr/bin/pcbnew`, `/usr/bin/kicad`) but
  require display for interactive editing
- Python `pcbnew` headless API works for bulk programmatic edits (delete-
  by-net-filter, plane stitching) but proved at 50–90 fouls per iteration
  for visual-placement-with-routing (see §A above)

Master (B)-scope decision: split tasks by tool. CLI delivers everything
text/logic/headless; GUI delivers visual placement + interactive routing
in Sai's pre-freeze KiCad session (which Sai opens anyway for final DRC +
freeze trigger).

**Delivered in this PR (CLI):**

- SKiDL `hardware/kicad/novapcb/sheets/power_sd_swd_3h.py`: J9 connector
  block commented out with v2 reference preserved; SWDIO/SWCLK still wired
  to PA13/PA14 via hwdef.dat
- BOM `bom/novapcb-bom.csv`: J9 row removed (54 → 53 line items after the
  PR #131 C96 closure; now 53 → 52)
- `docs/DFU_BOOTLOAD_PROCEDURE.md` (new): exact `dfu-util` + `uploader.py`
  + BOOT0 jumper procedure for first-flash + subsequent updates
- This `§B` update

**Pending in Sai's KiCad GUI session (board surgery):**

1. **Remove J9 footprint** (Edit → Delete on J9 in pcbnew)
2. **Place 5 labeled exposed-copper test-pads** near U1 SW corner per the
   placement table in §A
3. **Place BOOT0 jumper** (`TestPoint_2Pads_Pitch2.54mm_Drill0.8mm` or
   equivalent) near U1.94
4. **Route the test-pad nets** using interactive router (shove + walk-
   around — exactly what GUIs are built for):
   - TP_SWDIO → U1.72 SWDIO (~1.3 mm B.Cu)
   - TP_SWCLK → U1.76 SWCLK (~1.6 mm B.Cu)
   - TP_NRST → U1.14 NRST (~1.7 mm B.Cu)
   - TP_3V3 → +3V3 plane (single via)
   - TP_GND → GND plane (single via)
   - BOOT0 jumper pad 2 → U1.94 BOOT0 (~2 mm B.Cu)
5. **DRC + audit** in GUI (`Inspect → Design Rules Checker`); should pass
   ≤ baseline + 0 new
6. **Save + commit + push** (the `hw/swd-physical-gui-followup` or similar
   branch); master pre-merges

**Sai-bits queue (updated):**

| # | Task | Tool | Notes |
|---|---|---|---|
| 1 | GUI DRC final verify on freeze head | Sai KiCad GUI | Independent of SWD surgery; can run first |
| 2 | **SWD physical surgery** (this §B) | Sai KiCad GUI | Pair with #1 — same session |
| 3 | BOM LCSC sourcing at JLCPCB portal | Sai web | 8 SAI-SOURCE TBD: AO3400A Q5, XAL4020 L1, 120R R45, 0R R46, 562k R47, 180k R48, JST-GH SM04B J20, R61 placeholder |
| 4 | **Tick "Via-in-pad filled+capped" (IPC-4761 Type VII)** | Sai JLCPCB SMT form | 9 VIP pads — CRITICAL, board won't power without it; see `docs/DECISIONS.md §13.1b` |
| 5 | Phase 7a freeze trigger | Sai | Tag `v1-freeze`, lock fab sources |
| 6 | Phase 7b fab order submission | Sai | JLCPCB SMT both-sides + filled+capped vias + Extended parts confirm |
