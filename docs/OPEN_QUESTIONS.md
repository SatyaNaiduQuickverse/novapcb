# Open questions

All v1 scoping decisions are in `DECISIONS.md`. Add new open questions here as they arise.

## v2-1. FMUv6X mechanical drop-in (deferred from `DECISIONS.md §2`)

v1 is a functional drop-in only (single-PCB, Pixhawk-standard 30.5 × 30.5 mm M3, requires a new mounting tray on the airframe). v2 is the mechanical drop-in against the Holybro Pixhawk 6X — FMUv6X form factor, two-board (FMU + isolated IMU on vibration mounts), exact 6X connector pin-out and footprint so the existing airframe accepts novapcb in place of the 6X without any mechanical change.

**What still has to be decided for v2 (not blocking v1):**

- Exact FMUv6X mechanical envelope (read from the Pixhawk Autopilot v6X Reference Standard, not from training-data memory — Rule 3).
- IMU isolation board: ICM-42688-P × 3 (or ICM-42688-P + BMI088 + ICM-20649 like the stock 6X) on a sub-board with rubber isolators? Or a flex-cable mounted daughterboard?
- Connector pin-out: the 6X uses a fixed set of JST-GH connectors on specified pins (UART/CAN/GPS/etc.); v2 must match the 6X carrier expectations.
- FMU/IMU interconnect: SPI bus + DMA stream choice between FMU and IMU board.
- Whether v2 shares any v1 PCB sources or starts as a fresh layout.

**Reference:** ArduPilot `libraries/AP_HAL_ChibiOS/hwdef/Pixhawk6X/hwdef.dat` is the source of truth for the 6X pin-out / peripheral mapping; v2 hwdef forks from there.

## phase2a-1. IMU DRDY pin (deferred from Phase 2a, `INTERFACE_CONTRACT.md §3.5`)

Phase 2a locked the primary IMU as ICM-42688-P on SPI1 (CS = `IMU1_CS` / PC15) in polled mode. ArduPilot supports interrupt-driven fast-sample mode if a DRDY (data-ready) input pin is wired and declared in `hwdef.dat`. DRDY allows tighter loop rates and lower jitter on the IMU thread; novapcb v1 ships without one.

**Why deferred, not picked now:**

- Pixhawk6X uses `PA10` for `SP2_DRDY2` (ArduPilot `libraries/AP_HAL_ChibiOS/hwdef/Pixhawk6X/hwdef.dat:129`). On our MatekH743-derived hwdef, `PA10` is already `USART1_RX` (telem2). Direct port impossible.
- Picking another H743 GPIO autonomously violates Rule 3 (no inventing technical specifics) — needs a grounded choice against (a) free pins on the H743 in our current pin map, (b) interrupt-line availability (DRDY needs EXTI), and (c) a future PCB routing constraint we don't have yet (Phase 4).
- MatekH743 in production runs ICM-42688-P polled successfully. So polled is a known-working fallback, not a hack.

**What needs to happen before this can resolve:**

- Decide whether v1 needs DRDY at all (depends on the target loop rate; ArduCopter default 1 kHz IMU thread is fine polled on H7).
- If yes, identify a free H743 GPIO that (a) is interrupt-capable, (b) doesn't conflict with Phase 2b–2h or 2-exit, (c) routes cleanly on the Phase 4 PCB layout.
- Re-do Phase 2a as 2a-rev2 with the DRDY pin in `hwdef.dat`.

**Options (placeholder, not chosen):**

- (a) Stay polled (current). Lowest risk; no rework if v1 ships fine.
- (b) Add DRDY on a yet-to-pick GPIO, plus `define HAL_DEFAULT_INS_FAST_SAMPLE 1` is already on — confirm fast-sample works with DRDY too.
- (c) Wait until Phase 4 PCB layout reveals which pins are physically convenient, then circle back.

**Recommendation:** (a) polled for v1; revisit only if we see IMU-thread jitter in bring-up (Phase 9).

## phase2exit-1. MAX7456 analog OSD chip — populate on novapcb v1 schematic?

Raised 2026-05-20 (Phase 2-exit cruft inventory). Inherited from MatekH743 reference.

**RECOMMENDATION: omit.** MAX7456 is analog-FPV-FC hardware; novapcb is a Pixhawk-class autopilot replacement (`CLAUDE.md §0` / `§1`) and Pixhawk-class boards have no onboard analog OSD. Nova drone video is fully digital (Pi Camera / Hailo, `§2.1`); no analog video path exists. When Phase 3 schematic confirms "no MAX7456", a follow-up PR strips the 5 hwdef lines (PB12 CS, SPIDEV osd, OSD_ENABLED, HAL_OSD_TYPE_DEFAULT, ROMFS_WILDCARD fonts) — frees ~10-30 KB flash.

Keeping the hwdef lines until then costs ~10-30 KB flash + zero runtime risk.

**Resolution path:** Phase 3 schematic init explicitly states whether novapcb has a MAX7456 chip populated. If "no" (master near-certain recommendation), a follow-up firmware PR strips the 5 lines listed above. If "yes" (would need an explicit reason against the recommendation), hwdef stays as-is and the chip drives the SPI2 OSD line.

## phase3-render-1. Phase 3 drawn-schematic rendering

Raised 2026-05-20 (Phase 3a Rule-13 stop — escalation #1 on `tasks/phase-3a-mcu.yaml`).

**Problem.** SKiDL `generate_schematic()` auto-router does not scale past trivial circuits. On the 3a MCU sheet (STM32H743VITx LQFP-100 + 27 components / ~30 nets, with 95 unconnected peripheral pins on the MCU), it hangs in the router retry loop for 11+ minutes with no output produced. SKiDL `generate_netlist()` works instantly and cleanly (22 KB netlist, 0 errors). The Phase 3 Part 0 smoke test was only 2 components — it validated that the API EXISTS but did NOT validate that it SCALES. Both worker and master under-validated. (Captured as shared P0 miss for the next retro: investigation-phase smoke tests must be realistically scaled to the actual workload, not toy-sized.)

**Why it matters.** A human-readable schematic is needed for **Phase 6.5 forum review** — EEs expect a schematic. Phases 3.5 / 4 / 5 / 6 do NOT need it; they consume the netlist directly (which works). So the drawn-schematic problem is bounded: it blocks Phase 6.5, nothing earlier.

**Resolution path.** Dedicated investigation + resolution scheduled IN the Phase 3.5–6 window (BEFORE Phase 6.5 prep), evaluating:

- **(a)** SKiDL router flags / timeout / hierarchical-subcircuit options — does SKiDL's auto-router have a "place-only, don't route" mode? Does breaking into hierarchical subcircuits help?
- **(b)** kicad-skip programmatic placement — but note: kicad-skip itself is an auto-place/route problem, the same hard thing `generate_schematic()` fails at; front-loading it is premature until (a) and (c) are evaluated.
- **(c)** One-time manual KiCad-GUI layout pass from the netlist — open the netlist in eeschema GUI, hand-tidy the placement, render PDF via kicad-cli. Bounded human effort; produces highest-quality schematic for forum review.
- **(d)** Per-small-sheet generation — the MCU sheet hangs, but small peripheral sheets (a few components each) may route fine. Generate per-sheet PDFs + concatenate.

**Decision criteria:** whichever option (a)/(b)/(c)/(d) produces a forum-quality schematic with bounded effort, ranked by (i) reproducibility, (ii) developer effort, (iii) reviewer quality. (c) is the safest fallback (any-time-of-day a GUI Claude or supermaster can do it); (a)/(d) are the most attractive if they work.

**Not blocking.** Phase 3.5 (reference-design audit) and Phase 4 (PCB layout) both consume the SKiDL-generated netlist, which works. Phase 5 (BOM) consumes the netlist + parts metadata. Phase 6 (sims) takes the netlist + footprint placements. The drawn-schematic gap blocks Phase 6.5 specifically.

**Owner / when:** dedicated task scheduled within the Phase 3.5–6 window. Not blocking Phase 3 sub-phase advance (netlist-only mode is the agreed Phase 3 deliverable; see `tasks/phase-3a-mcu.yaml` escalation_log entry #1).

## phase4a-1. ICM-42688-P land pattern — **RESOLVED 2026-05-21** (custom footprint integrated)

Raised 2026-05-20 (Phase 4a — master adjudication of the `icm42688p-footprint` decision fork). **Resolved 2026-05-21 via a custom in-repo footprint at `hardware/kicad/novapcb-layout-v2/lib/novapcb.pretty/ICM-42688-P_LGA-14_2.5x3mm_P0.5mm.kicad_mod`.** See "Resolution 2026-05-21" section at the bottom of this entry for the new footprint, the cross-verification sources, and the integration.

**Status:** Phase 4a-4d **accept** the KiCad-generic `Package_LGA:LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y` footprint. Body, pitch, and pad-count/arrangement are TDK-spec-matched per Phase 2.5 P0.4. Pad sizes are IPC-7351 nominal. Placement (4b) and routing topology (4c/4d) depend on pad LOCATIONS which the generic gets right — so Phase 4 does NOT stall on this.

**Must-resolve before Phase 6m (manufacturability / DFM check):** verify pad dimensions against the TDK ds-000347 recommended land pattern. The ICM-42688-P is the **primary IMU** — the most flight-critical sensor on the board. A leadless-IC land pattern with wrong pad dimensions = poor or failed solder joints on a part that can't be hand-inspected. IPC-7351-generic is production-grade and probably fine, but "probably fine" is not the bar for the primary IMU on a board going to fab.

**Same re-verification applies to all leadless-IC footprints (LGA/QFN — IMU + DPS310) before fab; leaded packages (LQFP-100 + SOT-23) are lower-risk and Phase 2.5 P0.4 already cited KiCad-standard exact matches for those.**

**Resolution path (worker action — attempt near-term, ideally before Phase 4e so IMU SPI critical-net hand-routing uses final pads):**

- **(a) SnapEDA / UltraLibrarian vendor-verified footprint** — known sources for ICM-42688-P, free download. If verifiable + KiCad-9-compatible, swap the footprint in a small follow-up PR.
- **(b) Targeted single-page fetch of the datasheet's land-pattern figure** — narrower than the full 60-page PDF that timed out in Phase 4a WebFetch.
- **(c) An open-source FC project's datasheet-derived ICM-42688-P KiCad footprint** — well-traveled chip used on many FCs; somebody's likely committed a quality footprint.
- **(d) SUPERMASTER session with PDF tooling** — extract dimensions directly from ds-000347; SUPERMASTER REVIEW flag if none of (a)/(b)/(c) work headlessly.

**This is HARD carry-forward, not a soft "confirm at 6.5."** A leadless IMU footprint must not reach fab on a generic stand-in. Track it through Phase 4 sub-phases until resolved.

### Focused-attempt status 2026-05-21 (per master PR #58 review directive)

Research agent spent ~30 min reading every public TDK source for the LGA-14 land pattern:

- **ICM-42688-P datasheet DS-000347 v1.5 + v1.6**: read end-to-end. NO package outline drawing, NO land-pattern figure. Section 18 (References) explicitly defers PCB Design Guidelines to controlled-distribution document **AN-IVS-0002A-00**.
- **ICM-42605 datasheet DS-000292** (same LGA-14 package family): same — no package outline, no land pattern.
- **TDK AN-000262 "PCB Design Guidelines"**: provides only the parametric template (`A = LGA pin length, B = LGA pin width, C/D = mask opening = land + 0.1 mm`). States "recommended pad size is provided within the IMU device datasheets" — but for ICM-42688-P that section does not exist in the public datasheet.
- **TDK CDN** (`invensense.tdk.com/wp-content/uploads/...`): blocks both WebFetch and direct curl, so AN-IVS-0002A-00 not retrievable headlessly.

**Conclusion**: TDK does NOT publish the LGA-14 land pattern in the public ICM-42688-P datasheet. Headless paths (a)/(b)/(c) above are not viable for an authoritative source — the canonical land pattern lives in AN-IVS-0002A-00 (controlled distribution) only.

### Sai escalation (path (d), now the only authoritative path)

Two safe non-headless paths exist; Sai action needed:

1. **Request AN-IVS-0002A-00 from TDK directly**: free, requires email/account registration on TDK Developer portal (https://invensense.tdk.com/developers/). The document contains the canonical LGA-14 package mechanical drawing + recommended PCB land pattern.
2. **Vendor-library import + source citation**: download the ICM-42688-P KiCad footprint from one of:
   - Ultra Librarian: https://app.ultralibrarian.com/details/0a4080d3-d392-11ed-b159-0a34d6323d74/TDK-InvenSense/ICM-42688-P
   - SnapEDA: https://www.snapeda.com/parts/ICM-42688-P/TDK/view-part/
   Both vendor libs cite the source datasheet/app-note; record the source URL in the footprint's `descr` field for traceability.

Recommend Sai pursues path 1 (authoritative + reusable for the secondary IMU + other TDK parts on future boards). Path 2 is the fallback if Sai doesn't want to register on TDK Developer portal.

### Resolution 2026-05-21 (custom footprint, master-directed parallel task)

Per master 2026-05-21 directive ("find a reliable open-source result"): investigated ARK Electronics open-source hardware repos, finalized via a custom in-repo footprint built from cross-verified geometry.

**ARK Electronics findings (production-evidence source)**

- `github.com/ARK-Electronics/ARKV6X_Flight_Controller` (MIT-licensed, NDAA-compliant, Blue-UAS-listed, US-manufactured) uses dual ICM-42688-P in LGA-14 — production-flown evidence of the part choice.
- BUT: ARK publishes STEP + PDF schematic + BOM only. NO editable KiCad/Altium sources. (Same for ARK-Pi6X, ARK_Flow, ARK_RTK_GPS, ARK_FPV — confirmed by inspection of repo contents.)
- → ARK is a production-evidence reference, NOT a direct footprint source.

**Community KiCad footprints found via GitHub code search** (all referenced for geometric cross-verification only, not redistributed)

| Source repo | License | Pad geometry | Pad-edge gap |
|---|---|---|---|
| Gripsou/effective-coffee-spoon (`mcu_verbose.pretty/LGA-14__PQFN50P300X250X97-14N`) | CC-BY-SA-4.0 | 0.59 × 0.35 mm | 0.15 mm — fails 0.2 mm DRC |
| Aerokitties/Kitties-Hardware (`user_lib.pretty/LGA-14_2.5x3x0.91mm`) | unlicensed | 0.975 × 0.25 mm | 0.25 mm — passes 0.2 mm DRC |
| tetra-aero/ICM-42688-P_breakout | GPL-3.0 | (not extracted; GPL viral) | n/a |

All three confirm the same TDK pin layout (4 pads on each long side, 3 pads on each short side, pin 1 at NW corner, 0.5 mm pitch on a 3.0 × 2.5 × 0.91 mm body). The geometric facts (pin count, pitch, body) are not copyrightable; the specific .kicad_mod file structures of CC-BY-SA / GPL / unlicensed files are.

**Resolution: custom footprint at `hardware/kicad/novapcb-layout-v2/lib/novapcb.pretty/ICM-42688-P_LGA-14_2.5x3mm_P0.5mm.kicad_mod`**

Built from package-mechanical facts (TDK DS-000347 §11.1 public datasheet) + IPC-7351B Density-N pad sizing methodology. The pad sizes follow Aerokitties' demonstrably-DRC-passing 0.975 × 0.25 mm pattern (which is IPC-7351B-conventional for 0.5 mm-pitch LGA + matches the TDK package mechanical drawing). Cross-verified pin layout against all three community footprints. ARK ARKV6X cited as production-evidence that the part is real and flown.

Pad-edge gap in pitch direction = 0.5 - 0.25 = **0.25 mm** (clears the 0.2 mm netclass clearance with 25% margin).

`generate_board.py` updated to swap U3's KiCad-stock footprint with this custom one (similar to existing U6/J10/J11-18 swaps).

**Reliability standard (Sai's words via master)**: "the footprint must be cross-checkable against the authoritative package geometry, not trusted blindly." Cross-checks performed:

| Cross-check | Source | Result |
|---|---|---|
| Body dimensions 3.0 × 2.5 × 0.91 mm | TDK DS-000347 §11.1 (public) | matched |
| Pin count 14 | TDK pinout Fig 5 + all 3 community footprints | matched |
| Pin pitch 0.5 mm | TDK + all 3 community footprints | matched |
| Pin layout (4-3-4-3 with pin 1 at NW corner) | TDK + all 3 community footprints | matched |
| Pad size for DRC clearance | Aerokitties precedent + IPC-7351B Density-N | 0.975 × 0.25 mm; 0.25 mm edge gap clears 0.2 mm |
| Production evidence of part choice | ARK Electronics ARKV6X (MIT, open-source FC, flown) | confirmed |

**DRC outcome on Step 3 P1-rev placement**: 0 violations (all 14 prior U3-internal clearance failures cleared by the new footprint).

**What still requires confirmation** (informational, not blocking): pad-size exact match to AN-IVS-0002A-00 (TDK's controlled-distribution land-pattern doc). If/when Sai obtains that doc and the recommended sizes differ from our 0.975 × 0.25 mm, a follow-up PR replaces the pad sizes — but pin layout + pitch + body are correct.

**Status:** RESOLVED for v1 fab. Sai retrieval of AN-IVS-0002A-00 remains a nice-to-have for confirmation but is not blocking; the cross-verified custom footprint is fab-quality (passes DRC; pin layout authoritative from TDK datasheet; pad sizes IPC-7351B-conventional and consistent with the Aerokitties production-derived pattern).

---

## phase0.6-2. OpenEMS microstrip Z0-extraction — Phase 6b deep-dive required

**Raised 2026-05-21** (Phase 0.6 PR #56 follow-up; convergence re-run after the one-line ref_impedance fix).

Phase 0.6 validated OpenEMS as a SOLVER (rectangular-cavity TE₁₀₁ notch test: 0.03% error vs analytical resonance frequency). The microstrip Z0-extraction script v2 was thought to need only a one-line API fix (omit `ref_impedance=50` in `CalcPort()`, read `port.Z_ref` directly per `openEMS/ports.py:376`). PR #56 applied that fix and launched a background convergence re-run.

### Re-run interim results (n=5 + n=10 of 5/10/15 sweep)

  | Mesh density (cells across W) | Z0_avg (Ω) | Std (Ω) | vs analytical 69 Ω |
  |---|---|---|---|
  | n = 5 | **194,448** | 20,146 | wrong by 2818× |
  | n = 10 | **132,496** | 29,227 | wrong by 1920× |

n=15 still running at last check (~12% in). Even if it improves to ~60kΩ, the result is still 1000× wrong. Reading `port.Z_ref` directly did NOT fix the extraction — it produces a different wrong value than the v1 ratio-of-uf-tot/if-tot, but both are wildly off.

### Phase 6b deep-dive scope (worker action: NONE further on this script)

Per master 2026-05-21: "if the energy keeps oscillating (non-monotonic decay) and the result still scatters, that's the honest Phase 6b deep-dive outcome — flag it, don't re-iterate." Worker has stopped at the tripwire.

100s-of-kΩ result is a GROSS bug class — likely best fixed by starting fresh from a known-good OpenEMS impedance-extraction tutorial and adapting it, NOT by debugging the current script line-by-line. Candidate references for the Phase 6b deep-dive (NOT for headless implementation now — these are research starting points for whoever picks up the deep-dive):

- The OpenEMS Python tutorial `MSL_NotchFilter.py` — extracts a notch from an MSL filter, but uses Z0 as a known input not output; not directly applicable.
- The OpenEMS bend / coupler tutorials that *do* extract Z0 from S-parameter fits over a long line of known length.
- The OpenEMS C++ source for MSLPort (`Common/processports/processvoltage.cpp` etc.) to understand exactly how Et/Ht integration paths are constructed and what could go wrong on our mesh geometry.

### What this does NOT block

- **OpenEMS the solver stays validated** (notch 0.03% error). Future Phase 6b/4 routing of differential pairs (USB D+/D−) can still use OpenEMS for full S-parameter sims that don't rely on the broken Z0-extraction script.
- **Step 4 (sim-validate) on the current placement** proceeds — Step 4's thermal sim is Elmer-FEM (independent of OpenEMS), and the EM sims it does run are for plane-coupling / harmonic intersection, not microstrip Z0 extraction.
- **Step 5 (route once) controlled-impedance traces** can use analytical Hammerstad-Jensen (Pozar §3.8, IPC-2141 thickness-corrected) as the impedance floor, with bench measurement at Phase 9 as the delivery-time verification. OpenEMS Z0 extraction is the *cross-check* that's deferred.

### Status

- **Phase 0.6 PR #56**: closed. Solver validated, the one-line "diagnosis" fix applied, the re-run honestly demonstrates a deeper bug.
- **Z0-extraction script**: broken; awaits Phase 6b deep-dive. Don't grind further.
- **Critical path**: NOT blocking Step 3 (placement) or Step 4 (sim-validate) or Step 5 (routing). Becomes a real conversation if + when Step 5's controlled-impedance traces need OpenEMS verification beyond analytical Hammerstad-Jensen.

---

## pivot-2026-05-20. Re-layout dimensions — form factor, size, layer count, mounting

**Raised 2026-05-20** (Sai-directed pivot, mid-Phase-4-routing).
**Sai dimension-freedom update 2026-05-20 (later)**: Sai released the standard-dimension constraint — the board is a free RECTANGLE; size + aspect-ratio are an OUTPUT of deliberate placement, not a fixed input. See `DECISIONS.md §2 + §10`.

The dense 36×36 / 4-layer board is being set aside in favor of a deliberate, sim-driven, physics-guided placement on a roomier board. The previous form-factor decisions (`DECISIONS.md §2` 36×36 mm; `DECISIONS.md §8` 4-layer; Pixhawk-standard 30.5×30.5 M3 mounting) are **superseded** — see DECISIONS.md §2 §8 §10 §11 for the post-pivot direction.

### Sai-resolved 2026-05-20 (the dimension-freedom update)
1. **Board outline shape** — RECTANGLE. Aspect ratio is an OUTPUT of placement (Step 3), not pre-decided.
2. **Board size** — sized to the placement. No fixed dim constraint. ✓
3. **Layer count** — **OPEN**. 4 vs 6 to be decided in Step 3 based on whether 6-layer measurably reduces EMI/SI failure modes per the §10 reliability mandate.
4. **Mounting pattern** — driven by the resulting board outline + the airframe envelope; new tray is acceptable per §2.
5. **Airframe envelope** — **OPEN** (Sai will provide; not blocking Step 2 inrush mitigation or thermal-sim input prep).

### What's locked
- Schematic (Phase 3, in `hardware/kicad/novapcb/`) — unchanged
- BOM (Phase 5) — unchanged
- Firmware / hwdef — unchanged
- Footprints (Phase 4a custom + KiCad standard) — unchanged
- USB-CDC + CRSF + MAVLink interface contracts — unchanged

### What's open until Sai answers
- `hardware/kicad/novapcb-layout-v2/` (new project) — placement + planes + routing
- DECISIONS.md §2 §8 — revised
- Mounting tray (downstream airframe work)

### Why this matters
The Phase 6 P0 sim results surfaced real density-driven concerns: PDN anti-resonance at 100 kHz, AP2112K LDO Tj=88°C, inrush 3.39A, EMC harmonic intersections in GPS L1. A roomier layout + 6-layer option directly mitigates each of those.

---

## Mounting-hole-pattern-90x70. Supersede `DECISIONS §2` 30.5×30.5 c-to-c with corner-inset M3 for the 90×70 board

**Raised 2026-05-22** (master directive during SUBSYSTEM_CONTRACTS review).

**Question for Sai to ratify.** `DECISIONS §2` locks the v1 mounting pattern at Pixhawk-standard 30.5×30.5 mm c-to-c M3 (4 holes). That number was sized for the original 36×36 mm form factor. With the **2026-05-20 pivot to a 90×70 mm rectangular board** (also `DECISIONS §2`, post-supersession note), a centered 30.5×30.5 pattern leaves ~30 mm of unsupported overhang per side — mechanically poor for a board carrying connector strain and a stack of through-hole motor cables.

**Master's call 2026-05-22:** use 4 corner-inset M3 holes at ~5 mm inset, positions **(5, 5), (85, 5), (5, 65), (85, 65)** on the 90×70 board. The airframe gets a new tray anyway (v1 is a functional drop-in, not mechanical); corner holes maximize support and align with how every premium FC in this footprint class (Kakute H7, mRo Control Zero) actually mounts.

**What Sai needs to confirm:**
- That the 4-corner pattern is acceptable for the airframe tray design.
- That the 5 mm corner inset is correct (vs. tighter 3 mm or looser 8 mm). 5 mm gives M3 + 1 mm keep-out + some board edge margin and matches reference FC layouts.

**Effect on `DECISIONS.md`:** if Sai ratifies, `DECISIONS §2` gets a new entry that supersedes the 30.5×30.5 c-to-c c-locked-2026-05-18 entry for v1.1+. The 36×36 form factor itself is already superseded by the 90×70 rectangle pivot in the same §2; this is the follow-on mounting decision.

Reference: `docs/SUBSYSTEM_CONTRACTS.md §0.5` (where the 4 corner holes are quoted as the global constraint driving zone assignment).

---

# Closed decisions (recorded here for traceability)

## CLOSED phase3exit-can. CAN: novapcb v1 deliberately ships no CAN connector / transceiver

**Decided 2026-05-20** (Phase 3-exit A2 escalation; master adjudication).

**SUPERSEDED 2026-05-22** by commit `13d26a8` ("hw: can_3j.py — 1× CAN port on FDCAN1 (R1.4)") in the v1.1 re-spin. The SKiDL netlist `hardware/kicad/novapcb/sheets/can_3j.py` now instantiates the full CAN front-end: **U14** (TJA1051TK/3 transceiver), **U15** (PESD2CAN ESD diode array), **J20** (CAN connector), **R45** (120 Ω terminator), **R46** (terminator jumper), **C83/C84** (U14 decoupling). v1.1 ships **1× CAN port** on FDCAN1 (PD0/PD1 + GPIO_CAN1_SILENT on PD3). The original entry below is preserved verbatim for traceability of the earlier decision; the current ship-state is per the R1.4 SKiDL netlist (immutable for v1.1).

— original entry —

novapcb v1 deliberately ships **no CAN connector / transceiver**. The Nova drone uses zero CAN peripherals (GPS via UART, power via analog Mauch, ESCs via DShot, mag via I²C). Adding CAN would require an external CAN transceiver IC + 120 Ω termination + connector + board area — an unvalidated sub-circuit for a feature the target drone doesn't use. Per Rule 4 (match scope) + don't-design-for-hypothetical-futures discipline.

The `hwdef.dat` CAN1 definition (`hwdef.dat:147-149`: PD0/PD1 CAN1 + PD3 GPIO_CAN1_SILENT) is **RETAINED as harmless firmware capability** — if a future v1.x or v2 adopts a CAN peripheral (DroneCAN gimbal, smart battery, ESC telemetry-via-CAN), the firmware side is already in place and adding the transceiver + connector then is a contained change.

This decision resolves the Phase 2-exit Part B Item 6 pointer ("Phase 3 decides whether CAN connector is populated") cleanly. Phase 3 (now, at 3-exit) decides: **don't populate**.

**Why this is a CLOSED entry not an OPEN one:** it's a deliberate v1 feature-scope decision, not an unresolved question. It belongs here for traceability + so a future Claude sees the reasoning, but it's not awaiting any action.
