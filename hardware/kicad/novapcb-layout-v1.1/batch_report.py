#!/usr/bin/env python3
"""Generate a master-readable batch summary from the *_log.json."""
import json, sys, os
from pathlib import Path

HERE = Path(__file__).parent.resolve()


def make_report(batch_no):
    log_p = HERE / f"batch_{batch_no}_log.json"
    spec_p = HERE / f"batch_{batch_no}.json"
    if not log_p.exists():
        print(f"!! no log at {log_p}"); return
    log = json.load(open(log_p))
    spec = json.load(open(spec_p))

    base = log["baseline"]
    final = log.get("final", {})
    results = log["results"]

    n_total = len(results)
    n_ok = sum(1 for r in results if r.get("ok"))
    n_stuck = n_total - n_ok

    md = []
    md.append(f"# Batch {batch_no} report")
    md.append("")
    md.append(f"- Baseline: err={base['err']}, unc={base.get('unc','?')}")
    md.append(f"- Final:    err={final.get('err','?')}, unc={final.get('unc','?')}")
    delta = final.get("err", base["err"]) - base["err"]
    md.append(f"- Delta:    {delta:+d} errors")
    md.append(f"- Placed:   {n_ok}/{n_total}  stuck: {n_stuck}")
    md.append("")
    md.append("## Per-item")
    md.append("")
    for r in results:
        kind = r.get("kind")
        if kind == "stitch":
            tag = f"{r['ref']}.{r['pad']} ({r['net']})"
            status = "OK" if r["ok"] else "STUCK"
            md.append(f"- STITCH {tag}: {status} ({r['strategy']})")
        elif kind == "net":
            tag = r["net"]
            status = "OK" if r["ok"] else "STUCK"
            md.append(f"- NET {tag}: {status}")
            for leg in r.get("legs", []):
                md.append(f"  - {leg['leg']}: {leg['strat']} (err={leg.get('err','?')})")
    md.append("")

    out = HERE / f"batch_{batch_no}_report.md"
    out.write_text("\n".join(md))
    print(f"[report] {out}")
    print()
    print("\n".join(md))


if __name__ == "__main__":
    make_report(sys.argv[1])
