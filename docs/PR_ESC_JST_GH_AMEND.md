# PR — ESC connector SKiDL amend → JST-GH 1x02 horizontal

> **Branch**: `sch/esc-jst-gh-amend` off `sch/option-b-buck` head `c35dee1`
> **Scope**: SCHEMATIC ONLY — `esc_3f.py` footprint amend + regen netlist.
> No layout / board file touch. PR-A in a 2-PR sequence (PR-B = H placement
> layout, branches on top of this once merged).
> **Authorization required**: **Sai ratification** — schematic/netlist
> changes are not under master's delegated merge authority per the
> [follow-master memory](../../.claude/projects/-home-novatics64-novapcb/memory/feedback_follow_master.md).

---

## Symptom

H placement up-front constraint analysis (sub-step #106, branch
`hw/h-placement` doc-only) surfaced a contradiction between the
schematic source and the locked connector decision:

- **SKiDL `esc_3f.py:151`** (current) uses a **placeholder footprint**
  `Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical` with
  body docstring claiming "Solder pads" as the resolved choice (§38-56).
- **`docs/DECISIONS.md §7`** (locked 2026-05-18) mandates **JST-GH
  (Pixhawk family)** for ALL FC connectors with explicit rationale:
  *"matches every harness on the existing airframe; bring-up must not
  also require re-crimping cables."*

Both can't be right. The Phase 3f docstring is from an earlier sub-phase
where the connector choice was open; DECISIONS.md §7 superseded it on
2026-05-18 (Sai-signed). The SKiDL was never re-aligned.

## Fix

Two minimal edits to `hardware/kicad/novapcb/sheets/esc_3f.py`:

### 1. Footprint reference (line 151 area)

```diff
 for idx in range(1, 9):
     pad = Part(
         "Connector_Generic", "Conn_01x02",
-        # Placeholder footprint — Phase 4 layout decides actual pad geometry.
-        # Using a generic header footprint for now; Phase 4 swaps to the
-        # production solder-pad land pattern.
-        footprint="Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
-        value=f"ESC{idx}_PAD",
+        footprint="Connector_JST:JST_GH_SM02B-GHS-TB_1x02-1MP_P1.25mm_Horizontal",
+        value=f"ESC{idx}",
     )
     pad.ref = f"J{10 + idx}"   # J11..J18
     mot_nets[idx] += pad[1]    # pin 1 = motor signal
     GND            += pad[2]   # pin 2 = GND return
```

### 2. Docstring §38-56 rewrite

Replaces the "Solder pads" rationale with:
- Cites `DECISIONS.md §7` mandate
- Calls out the horizontal-variant choice rationale (motor leads exit
  parallel to south board edge, matches other JST-GH conn on telem 3i /
  power 3h / GPS sheets)
- Pixhawk DS-009 reference (FMUv6 family uses JST-GH 1x02 per motor)
- Lists the canonical KiCad 9 footprint string

Net assignments + topology unchanged:
- 8 connectors (J11..J18) — one per motor
- 2 pads each (pin 1 = MOT_N signal, pin 2 = GND)
- 16 total pads → identical to placeholder count

## Root cause

Phase 3f wrote SKiDL in 2026-04..05 when the connector standard was
still **open** in `DECISIONS.md §7` (then-pending fork). The Phase 3f
author chose solder-pad provisionally with docstring rationale captured
in `esc_3f.py:38-56`.

On **2026-05-18**, Sai locked §7 to **JST-GH (Pixhawk family)** —
explicitly tighter than solder-pad: "must not require re-crimping
cables on the existing airframe." This supersedes the solder-pad
provisional.

`esc_3f.py` was never re-edited to match. Other sheets (telem_3i,
power_sd_swd_3h, gps, can) DID get the JST-GH treatment (verified by
grep — `JST_GH_SM06B-GHS-TB` × 1, `JST_GH_SM04B-GHS-TB` × N for those
sheets). Only `esc_3f.py` was missed.

The contradiction was hidden because:
- Schematic ERC doesn't validate footprint-vs-spec
- Audit script (`scripts/audit_layout_compliance.py`) checks placement
  / DRC / stackup / fanout — not connector-family alignment
- Board file J11..J18 use a custom `ESC_solder_pad` footprint (PARKED at
  X>100) that diverged from BOTH the SKiDL placeholder AND the
  DECISIONS spec, masking the schematic discrepancy

H placement audit forced the cross-check (master found the
contradiction while reviewing the constraint analysis).

## Prevention

### Audit gate (suggested follow-up — NOT in this PR)

Add a `check_connector_family_alignment()` info-only gate to
`scripts/audit_layout_compliance.py` that parses
`hardware/kicad/novapcb/novapcb.net` for every `J*` reference and
flags any footprint NOT in `Connector_JST:JST_GH_*` (with allowlist
for known exceptions like USB-C, SWD ribbon, microSD).

Owner: master (defer until DRU cleanup PR #97). Out of scope for PR-A.

### Phase 3 amend hygiene

When `DECISIONS.md` lands a value that supersedes a prior Phase 3
placeholder, the corresponding SKiDL sheet MUST be re-edited within the
same calendar day. Going forward: any `DECISIONS.md` ratification PR
should grep `hardware/kicad/novapcb/sheets/*.py` for placeholder
patterns it potentially supersedes and bundle the SKiDL amend.

## Spec deviations (Rule 4)

NONE. This PR restores alignment to a locked spec.

## Rule 9 verification (artifact-level)

| Claim | Verified by |
|---|---|
| SKiDL footprint changed to JST-GH-1x02 horizontal | `grep "JST_GH_SM02B-GHS-TB" hardware/kicad/novapcb/sheets/esc_3f.py` → 1 match |
| Netlist regenerated | `novapcb.net` mtime updated; date "05/24/2026 12:23 AM" |
| Netlist J11..J18 all use JST-GH footprint | `grep -E 'JST_GH_SM02B' novapcb.net` → 16 matches (8× component decl + 8× field) |
| J11..J18 net assignments preserved (MOT1..MOT8 → pin 1, GND → pin 2) | side-by-side `grep 'ref "J1[1-8]"\|MOT[1-8]'` old vs new identical |
| Line count parity | `wc -l novapcb.net` old=new=5720 (no nets added/removed) |
| ERC clean | `python3 generate.py` → "INFO: 0 errors found while generating netlist" |
| No board file touch | `git diff sch/option-b-buck -- hardware/kicad/novapcb-stepwise/novapcb-stepwise.kicad_pcb` empty |
| Audit baseline unchanged | 2 pre-existing FAILs (U6 DECOUPLING task #91, R13 fanout slot-deferral consequence) — not caused by this PR |

### Netlist diff noise note

SKiDL regenerates random `tstamps` UUIDs + `SKiDL Tag` values for every
component on every run. The full `git diff novapcb.net` is ~5000 lines
of UUID churn unrelated to the substantive change. **For review,
inspect**:

```bash
grep -B1 -A4 'ref "J1[1-8]"' hardware/kicad/novapcb/novapcb.net
# All 8 should show JST_GH_SM02B-GHS-TB footprint + value ESCN (was ESCN_PAD)
```

## After this lands

PR-B (`hw/h-placement`, branched on top of this) starts:
- Layout placement of 8× JST-GH-1x02 horizontal connectors
- Per master D2-D5 (sub-step #107): south band Y=65..85, uniform
  11.86mm pitch, X=10..93, right-edge compressed for H4 mount keep-out
- KiCad update-from-netlist auto-replaces parked `ESC_solder_pad`
  footprints with new JST-GH footprints at parked X>100 — then
  step7_place_H.py moves them into final position

## Test plan

- [x] `hardware/kicad/novapcb/sheets/esc_3f.py` footprint string =
  `Connector_JST:JST_GH_SM02B-GHS-TB_1x02-1MP_P1.25mm_Horizontal`
- [x] `python3 generate.py` runs clean: 0 ERC errors
- [x] `novapcb.net` regenerated with new footprint × 8 connectors
- [x] Net topology preserved (MOT1..MOT8 → pin 1; GND → pin 2 on all 8)
- [x] Docstring §38-56 reflects JST-GH decision (DECISIONS.md §7 citation)
- [x] No board file touched (placement happens in PR-B)
- [x] DECISIONS.md §7 (lock unchanged)
