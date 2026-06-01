# Disk space audit on novaedge1 (master Pi) — 2026-06-01

> Sai had asked "check space on this pi first then decide" earlier in the
> session. Audit follow-through. **Critical: only 1.9 GB free of 29 GB.**

## State at audit time

| Mount | Size | Used | Avail | Use% |
|---|---|---|---|---|
| `/` (mmcblk0p2) | 29 GB | 26 GB | 1.9 GB | **94%** |

## Largest consumers under `/home/novaedge1`

| Path | Size | Notes |
|---|---|---|
| `/home/novaedge1/.arduino15` | **6.9 GB** | Arduino IDE installation + packages + staging. Likely unused for novapcb (novapcb uses ArduPilot waf build on novatics64). **Largest candidate for cleanup.** |
| `/home/novaedge1/.arduino15/packages` | 5.3 GB | Arduino package cache |
| `/home/novaedge1/novapcb` | 1.6 GB | Project itself — DO NOT touch |
| `/home/novaedge1/.arduino15/staging` | 1.5 GB | Arduino staging area |
| `/home/novaedge1/novapcb/hardware` | 1.3 GB | KiCad files inside repo |
| `/home/novaedge1/.local` | 916 MB | Python user packages |
| `/home/novaedge1/.claude` | 136 MB | Claude state — DO NOT touch |
| Other | < 200 MB | Misc |

## Why this matters

Worker on novatics64 is running ArduPilot waf builds + ngspice + skrf for
the T20/T21/T22 + sim re-validation campaign. Heavy disk pressure on
novaedge1 isn't directly blocking — but if Sai wants ngspice runs locally
(option discussed earlier), there's no room.

## Recommendation

**Cleanable with Sai approval:**
- `.arduino15` (6.9 GB) — only if Arduino IDE isn't actively used. Frees
  to 8.8 GB available (30% headroom).
- `.local` (916 MB) — `pip cache purge` would recover ~200-400 MB.

**Don't touch:**
- `novapcb/` — active repo
- `.claude/` — session state
- System dirs

**Net potential:** ~7.5 GB recoverable. Final state: ~9.4 GB free, ~67% used.

## Action

This is a **Sai-decision** (deleting user tools needs explicit OK). Master
flagging the gap; not executing without authorization.

If Sai authorizes: `rm -rf ~/.arduino15` (6.9 GB) + `pip cache purge`.

## Why not master-process learnings doc instead

Sai 2026-06-01 reminder: "make sure you dont drift from the mandate".
Mandate = finish v1, both don't stop. Disk audit supports the campaign
(prevents fail mode where worker sim runs can't write output). A retro
"master-process learnings" doc is project polish, not v1-finishing —
dropped from this burst per the don't-drift call.
