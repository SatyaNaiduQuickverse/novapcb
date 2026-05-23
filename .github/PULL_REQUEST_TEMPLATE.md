<!--
Every PR uses this template. See:
  - docs/ENGINEERING_RIGOR.md §7 (4-section + augmented sections)
  - docs/MASTER_PROCESS_RULES.md (Rule 4 spec deviations, Rule 9 artifact verification)

Delete this comment block + any sections not applicable, but state explicitly
when you delete a section WHY it doesn't apply (e.g. "no spec deviations —
implementation matches contract exactly").
-->

## Symptom

<!-- What was observed. The DRC error / sim fail / unexpected number / user
report. State what you saw, not your interpretation. -->

## Fix

<!-- One to three bullets describing what changed. The diff in prose. -->

## Root cause

<!-- WHY it broke — the underlying issue, not where the symptom surfaced.
Cross-ref docs/ENGINEERING_RIGOR.md §12 (root-cause discipline). If this is
a stopgap rather than a root fix, label it explicitly and log the root to
docs/OPEN_QUESTIONS.md. -->

## Prevention

<!-- How to avoid the next instance. New gate / audit-script check / doc
clarification / committed memory. If no preventive measure is possible, say
so explicitly with the reasoning. -->

## Spec deviations (Rule 4)

<!-- Every divergence from the approved spec (subsystem contract / DECISIONS /
INTERFACE_CONTRACT). For each: WHAT the spec said, WHAT was built, WHY they
differ, WHO approved (master sign-off if outside normal scope).

Examples: component position differs from approved placement, DRU rule
adopted, fab-process bump required, net deferred to a later sub-step.

If no deviations, write "None — implementation matches contract exactly". -->

## Rule 9 verification (artifact-level)

<!-- For any "DRC GREEN" or "zone filled" or "net routed" claim — prove the
ARTIFACT, not the tool exit code. Examples:
  - Cluster walk on pads+tracks+vias confirms <N> nets fully connected
  - `pcbnew.Zone.GetFilledArea()` > 0 for each declared zone
  - Gerber visual inspection of region X (link to PNG export)
  - Thermal sim run on actual board (not planned positions)
  - openEMS sim convergence + S11/S21 numbers
If not applicable (e.g. doc-only PR), write "N/A — doc-only change". -->

## Audit run

<!-- Paste output of:
  python3 scripts/audit_layout_compliance.py hardware/kicad/novapcb-stepwise/novapcb-stepwise.kicad_pcb
PR cannot be merged with NEW warnings vs main. -->

## Master sign-off

<!-- If outside normal scope (Phase 4 layout / Phase 5 BOM / Phase 6 sims /
Phase 7 fab), supermaster's typed PR comment is the merge gate. Reference
the comment / commit sha. -->
