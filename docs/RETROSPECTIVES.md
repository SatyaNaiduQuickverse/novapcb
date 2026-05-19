# Retrospectives — hourly self-review

Every hour boundary, supervisor (novaedge1) and worker(s) each write a short retrospective. Reviewed by the other side. Recurring patterns become PRs to `ENGINEERING_RIGOR.md` or `DESIGN_PHASES.md`.

## Cadence

- Triggered on the hour (12:00, 13:00, ...) local time on novaedge1.
- Trigger source: master's hourly `/loop` (or ScheduleWakeup) wake. Master writes its retrospective, then sends a retro trigger to each worker session via `/send/<worker>`.
- Each worker writes its retrospective in response.
- All retrospectives for one hour committed to a single file.

## Output convention

`retrospectives/YYYY-MM-DDTHH00.md` — template at `retrospectives/_TEMPLATE.md`.

## What a retrospective covers

Each side writes four short sections (~5 bullets each, hard cap):

1. **What I did this hour** — facts, not narration. Link PRs / files / commits. No filler.
2. **Rule adherence** — explicit checks against CLAUDE.md §7 rules + ENGINEERING_RIGOR.md commitments. Both passes and failures.
3. **Patterns / mistakes spotted** — recurring issues, near-misses, gaps between intent and execution.
4. **Process changes to consider** — proposed PRs if a pattern is worth fixing.

After both sides post, a **cross-review** section: each side reviews the other's retro in 2-3 lines. Pushback expected — flattery is a Rule 6 / Rigor #7 failure.

## What a retrospective is NOT

- Not a re-summary of work (commit messages do that).
- Not praise. "Good work" is filler.
- Not a re-statement of committed-doc content.
- Not a wall of text. ~50 lines max per side, ~20 lines for cross-review.

## Idle retrospectives

If a side did nothing meaningful in the hour, the retro is one line: "Idle — waiting on [thing]." Save the words.

## Acting on retrospectives

| Signal | Action |
|---|---|
| Pattern shows up in 3 consecutive retros | PR to the relevant doc (usually ENGINEERING_RIGOR.md or DESIGN_PHASES.md) |
| Single retro identifies a rule violation that shipped | Higher-priority PR — same hour — to fix the doc that was wrong |
| Cross-review identifies disagreement | Both sides escalate to user; do not silently converge |
| Three consecutive idle retros | Master pings user — system is stalled |

## What this is here to catch

- Slow drift from doc-defined process toward improvisation.
- Both sides quietly agreeing to skip a hard step.
- Repeated "almost violated rule X" near-misses.
- Time spent on things that don't advance a phase.

If the retro itself becomes ceremony (written rotely, never read, never acted on), that pattern shows up first as a meta-issue: "the retrospective is filler." That's the signal to delete this doc or simplify it.
