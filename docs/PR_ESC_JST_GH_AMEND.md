# PR — ESC connector SKiDL amend → 1× JST-GH 1x10 horizontal (Pixhawk 6X FMU PWM OUT)

> **Branch**: `sch/esc-jst-gh-amend` off `sch/option-b-buck` head `c35dee1`
> **Scope**: SCHEMATIC ONLY — `esc_3f.py` footprint + topology amend +
> regen netlist. No layout / board file touch. PR-A in a 2-PR sequence
> (PR-B = H placement layout, branches on top of this once merged).
> **Authorization required**: **Sai ratification** — schematic/netlist
> changes are not under master's delegated merge authority per the
> [follow-master memory](../../.claude/projects/-home-novatics64-novapcb/memory/feedback_follow_master.md).
>
> **Revision history on this PR**:
> - sha 7a6a959 — first amend (8× JST-GH 1x02). Sai pushback: Pixhawk
>   6X / Cube Orange+ / Jetson Baseboard all use 1× 10-pin per port;
>   8× 2-pin would force custom motor cables, violating §7's literal
>   harness-compat motivation.
> - **(this revision)** — second amend (1× JST-GH 1x10) per master
>   directive 2026-05-24 after Sai ratification of the direction.

---

## Symptom

H placement up-front constraint analysis (sub-step #106, branch
`hw/h-placement` doc-only) surfaced a contradiction between the
schematic source and the locked connector decision:

- **SKiDL `esc_3f.py:151`** (original) used a **placeholder footprint**
  `Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical` with
  body docstring claiming "Solder pads" as the resolved choice (Matek-
  style mini-racing-FC convention).
- **`docs/DECISIONS.md §7`** (locked 2026-05-18) mandates **JST-GH
  (Pixhawk family)** for ALL FC connectors with explicit rationale:
  *"matches every harness on the existing airframe; bring-up must not
  also require re-crimping cables."*

The first amendment (sha 7a6a959) corrected the family to JST-GH but
chose **8× 1x02** (one connector per motor). Sai flagged this as a
second §7 violation: no Pixhawk-family FC ships an 8× 2-pin layout —
the existing airframe harness terminates in a single 10-pin connector.

### Competitor research (justifies 1× 10-pin choice)

| FC board | Vendor | PWM OUT connector | Per port |
|---|---|---|---|
| Pixhawk 6X | Holybro | 2× **10-pin JST-GH** (FMU + IO) | 8 sig + 1 VDD_SERVO + 1 GND |
| Cube Orange+ | CubePilot | 2× **10-pin JST-GH** | same |
| Jetson Baseboard | NXP / ARK | 2× **10-pin JST-GH** | same |
| MatekH743 (referenced earlier) | Matek | **solder pads** per motor | racing-FC convention, NOT Pixhawk-family |

novapcb is FMU-only (no separate IO MCU), so only the FMU port is
implemented: **1× 10-pin JST-GH**. This matches the existing Pixhawk
6X harness end-to-end — drop-in compatible per §7.

The 8× 2-pin (first amend) and the original solder-pad (Phase 3f
placeholder) both came from racing-FC convention, not Pixhawk family.
Both violated §7's literal motivation. This revision restores alignment.

## Fix

Two edits to `hardware/kicad/novapcb/sheets/esc_3f.py`:

### 1. Connector instantiation (replaces 8-iteration loop)

```diff
-for idx in range(1, 9):
-    pad = Part(
-        "Connector_Generic", "Conn_01x02",
-        footprint="Connector_JST:JST_GH_SM02B-GHS-TB_1x02-1MP_P1.25mm_Horizontal",
-        value=f"ESC{idx}",
-    )
-    pad.ref = f"J{10 + idx}"   # J11..J18
-    mot_nets[idx] += pad[1]    # pin 1 = motor signal
-    GND            += pad[2]   # pin 2 = GND return
+esc_conn = Part(
+    "Connector_Generic", "Conn_01x10",
+    footprint="Connector_JST:JST_GH_SM10B-GHS-TB_1x10-1MP_P1.25mm_Horizontal",
+    value="ESC_OUT",
+)
+esc_conn.ref = "J11"
+
+for idx in range(1, 9):
+    mot_nets[idx] += esc_conn[idx]   # pin 1..8 = MOT1..MOT8 signal
+
+# pin 9 VDD_SERVO: NC — explicit no-bind per project SKiDL convention
+# (imu_3c.py:170). ERC will emit "unconnected pin" warning — EXPECTED.
+# If Sai ratifies (b) tie-to-GND: add `GND += esc_conn[9]` here.
+
+GND += esc_conn[10]   # pin 10 = GND return
```

### 2. Pin assignment (Pixhawk 6X DS-002 / DS-009 FMU PWM OUT)

| Pin | Net          | Role |
|---:|--------------|------|
| 1  | MOT1         | DShot ch 1 signal (3.3V logic) |
| 2  | MOT2         | DShot ch 2 |
| 3  | MOT3         | DShot ch 3 |
| 4  | MOT4         | DShot ch 4 |
| 5  | MOT5         | DShot ch 5 |
| 6  | MOT6         | DShot ch 6 |
| 7  | MOT7         | DShot ch 7 |
| 8  | MOT8         | DShot ch 8 |
| 9  | **VDD_SERVO** | **NC on novapcb** — see Sai decision below |
| 10 | GND          | Return |

### 3. Docstring §38-56 rewrite

Replaces "Solder pads" rationale with:
- DECISIONS.md §7 + literal Pixhawk-family motivation
- Competitor research table
- Pin-assignment table (matches code)
- Pin 9 VDD_SERVO NC convention note + cross-ref to Sai decision
- Footprint: `Connector_JST:JST_GH_SM10B-GHS-TB_1x10-1MP_P1.25mm_Horizontal`

### Net topology

- Before (original): 8 conn × 2 pads = 16 pads. 8 signal + 8 GND.
- This rev: 1 conn × 10 pads = 10 pads. 8 signal + 1 NC (pin 9) + 1 GND (pin 10).
- 6 fewer pads, 7 fewer connector refs (J12..J18 now free for future).
- All 8 MOT* net assignments preserved (now to J11.1..J11.8).
- GND on J11.10 (was J11.2 + J12.2 + ... + J18.2 across 8 connectors).

## Decisions for Sai

### D1 — Pin 9 VDD_SERVO handling

| Option | Wiring | Behavior | Trade-off |
|---|---|---|---|
| **(a) NC** (recommend, this PR's default) | unbound in SKiDL | floating on FC side; harness rail sourced elsewhere or unused | matches Pixhawk-family "FC doesn't power servos" pattern (DShot-only setup); avoids unintended GND short if external harness ever powers this pin |
| (b) tied-to-GND | `GND += esc_conn[9]` | defined potential on FC side | safer if harness wiring is ambiguous; matches some non-Pixhawk vendors; but if harness ever injects 5V on pin 9 (e.g., for analog servos on a different airframe), this would short the BEC to GND |

**Recommend (a)**. Pixhawk 6X itself leaves the FMU PWM OUT VDD_SERVO
unconnected on the FMU side (sourced from a separate PM02 servo BEC
into the IO port on dual-MCU designs). novapcb is single-MCU + DShot-
only, so option (b) "tie-to-GND" adds risk without benefit.

If Sai picks (b), one line of SKiDL changes (uncomment the documented
alternative). Net regen + ERC re-run is trivial.

## Root cause

Phase 3f wrote SKiDL in 2026-04..05 when the connector standard was
still **open** in `DECISIONS.md §7`. The Phase 3f author defaulted to
**Matek-style solder pads** (racing-FC convention they were familiar
with), captured the rationale in `esc_3f.py:38-56`.

On **2026-05-18**, Sai locked §7 to **JST-GH (Pixhawk family)** —
literal motivation: "matches every harness on the existing airframe."
Two layers of placeholder needed correcting:

1. **Family**: solder-pad (Matek racing-FC) → JST-GH (Pixhawk family).
   First amend (sha 7a6a959).
2. **Topology**: 8 per-motor vs 1 multi-pin. Every Pixhawk-family FC
   (6X, Cube, Jetson Baseboard) ships 1× 10-pin per port. 8× 2-pin
   would force Sai to crimp custom cables to mate with the airframe
   harness, violating §7's literal motivation. Second amend (this rev).

Both placeholders inherited from a different FC market segment
(racing) than the locked decision target (Pixhawk family). The audit
didn't catch this because it doesn't currently cross-check connector
footprint family against DECISIONS.md.

## Prevention

### Audit gate (follow-up — NOT in this PR)

Add a `check_connector_family_alignment()` info-only gate to
`scripts/audit_layout_compliance.py` that parses
`hardware/kicad/novapcb/novapcb.net` for every `J*` reference and
flags any footprint NOT in `Connector_JST:JST_GH_*` (with allowlist
for known exceptions like USB-C, SWD ribbon, microSD card socket).

For the next level of rigor (catch topology mismatches like 8× vs 1×),
the gate could also flag whenever the SAME logical port (e.g., all
motor outputs) is split across multiple connector refs without an
explicit DECISIONS.md ratification.

Owner: master (defer until DRU cleanup PR #97). Out of scope for PR-A.

### Phase 3 amend hygiene

When `DECISIONS.md` lands a value that supersedes a prior Phase 3
placeholder, the corresponding SKiDL sheet MUST be re-edited within
the same calendar day. Going forward: any `DECISIONS.md` ratification
PR should grep `hardware/kicad/novapcb/sheets/*.py` for placeholder
patterns it potentially supersedes and bundle the SKiDL amend.

This sheet was missed in May because §7's ratification PR only touched
docs, not SKiDL. The other sheets (telem 3i, power 3h, GPS, CAN) had
already been written with JST-GH (their authors happened to use the
Pixhawk-family default). Only `esc_3f.py` had the Matek-derived
placeholder.

## Spec deviations (Rule 4)

NONE. This PR restores alignment to a locked spec.

## Rule 9 verification (artifact-level)

| Claim | Verified by |
|---|---|
| Single 10-pin connector instantiated | `grep -c 'ref "J11"' novapcb.net` = 13 (1 comp + 10 pin nodes + 2 misc) |
| J12..J18 absent | `grep -cE 'ref "J1[2-8]"' novapcb.net` = **0** |
| J11 footprint = JST_GH_SM10B | `grep -A4 'ref "J11"' novapcb.net` shows `Connector_JST:JST_GH_SM10B-GHS-TB_1x10-1MP_P1.25mm_Horizontal` |
| MOT1..MOT8 each have J11 node | for n in 1..8: `grep -A20 'name "MOT$n"' novapcb.net \| grep 'ref "J11"'` = 1 match each ✓ |
| GND has J11 pin 10 | `grep -A1 'name "GND"' novapcb.net` shows J11/pin 10 ✓ |
| Pin 9 unbound (NC) | no node entry for J11 pin 9 in any net (greppable via `grep -B1 -A2 'pin "9"' novapcb.net \| grep -B1 'J11'` returns empty) |
| ERC clean | `python3 generate.py` → "ERC INFO: 0 errors found while running ERC" |
| No board file touch | `git diff sch/option-b-buck -- hardware/kicad/novapcb-stepwise/novapcb-stepwise.kicad_pcb` empty |
| Audit baseline unchanged | 2 pre-existing FAILs (U6 DECOUPLING #91 + R13 fanout slot-deferral) — not caused by this PR |

### Netlist diff noise note

SKiDL regenerates random `tstamps` UUIDs + `SKiDL Tag` values on every
run. The full `git diff novapcb.net` is mostly UUID churn. **For
substantive review**:

```bash
# 1× 10-pin J11 verification
grep -B1 -A4 'ref "J11"' hardware/kicad/novapcb/novapcb.net | head -10

# J12..J18 should be GONE (was 8 connectors, now 1)
grep -cE 'ref "J1[2-8]"' hardware/kicad/novapcb/novapcb.net

# 8 MOT* nets each bound to J11 pin 1..8
for n in 1 2 3 4 5 6 7 8; do
  echo "MOT$n:"; grep -A20 "name \"MOT$n\"" hardware/kicad/novapcb/novapcb.net | grep -A2 'ref "J11"' | head -3
done
```

## After this lands

PR-B (`hw/h-placement`, branched on top of this) starts:
- Single 10-pin JST-GH placement (~17mm × ~7mm body, much simpler than 8 destinations)
- Center on board midline OR offset — fresh up-front analysis required
- MCU fanout: 8 MOT* from MCU TIM pins consolidated to a single connector
- South-edge placement (motor harness exits south) still correct
- D-zone EMI keep-out + length budgeting reuse the §6-§7 analysis from
  the original H placement doc

Geometry is **fundamentally different** from the 8× 2-pin plan, so the
existing `docs/H_PLACEMENT_CONSTRAINT_ANALYSIS.md` (sha 87fc1e0 on
`hw/h-placement`) needs a fresh rewrite before PR-B layout. Master
will sign off on the new analysis before layout execution per the
established up-front-analysis pattern.

## Test plan

- [x] `hardware/kicad/novapcb/sheets/esc_3f.py` footprint string =
  `Connector_JST:JST_GH_SM10B-GHS-TB_1x10-1MP_P1.25mm_Horizontal`
- [x] `python3 generate.py` runs clean: 0 ERC errors
- [x] `novapcb.net` regenerated with single J11 connector
- [x] J12..J18 absent
- [x] All 8 MOT1..MOT8 nets bound to J11 pin 1..8 respectively
- [x] GND bound to J11 pin 10
- [x] Pin 9 VDD_SERVO unbound (NC per default; Sai decision D1)
- [x] Docstring §38-56 reflects 1× 10-pin Pixhawk 6X convention + competitor research
- [x] No board file touched (placement happens in PR-B)
- [x] DECISIONS.md §7 (lock unchanged)
- [ ] **Sai D1 decision**: pin 9 NC (default) vs tied-to-GND
