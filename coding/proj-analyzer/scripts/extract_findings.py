#!/usr/bin/env python3
"""Recover a findings directory from a previously rendered report.

A rendered report embeds its entire findings payload in
`<script id="report-data" type="application/json">`. That makes the scratch
findings directory disposable: if you need to re-render, restyle, or diff against
an older report, recover the inputs from the report itself instead of redoing the
analysis.

Usage
-----
  extract_findings.py --report PROJECT-ANALYSIS.html --out .proj-analysis
  extract_findings.py --report PROJECT-ANALYSIS.html --out /tmp/old --print-only
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

SCRIPT_RE = re.compile(
    r'<script id="report-data" type="application/json">(.*?)</script>', re.S)

# top-level DATA keys that are derived at render time and must not be written back
DERIVED = {"unconfirmed", "stats", "fileNotes"}

# how a DATA key is split back into findings files
SPLIT = {
    "overview": ("overview.json", None),
    "architecture": ("architecture.json", None),
    "modules": ("modules.json", None),
    "flows": ("flows.json", "flows"),
    "database": ("database.json", None),
    "config": ("config.json", None),
    "auth": ("auth.json", None),
    "frontend": ("frontend.json", None),
    "jobs": ("jobs.json", None),
    "deps": ("deps.json", None),
    "deploy": ("deploy.json", None),
    "entry": ("entry.json", None),
    "risks": ("risks.json", None),
}


def load_report(path: str) -> dict:
    html = open(path, encoding="utf-8").read()
    m = SCRIPT_RE.search(html)
    if not m:
        raise SystemExit(f"error: no report payload found in {path} "
                         "(is it a report produced by render_report.py?)")
    # the renderer escapes `</` inside the JSON so it cannot close the script tag
    return json.loads(m.group(1).replace("<\\/", "</"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", required=True)
    ap.add_argument("--out", default=".proj-analysis")
    ap.add_argument("--print-only", action="store_true",
                    help="report what would be written without writing it")
    args = ap.parse_args()

    D = load_report(args.report)
    written = []

    def write(name, obj):
        written.append((name, obj))
        if args.print_only:
            return
        os.makedirs(args.out, exist_ok=True)
        with open(os.path.join(args.out, name), "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=1)

    for key, (fname, wrap) in SPLIT.items():
        if key not in D:
            continue
        obj = D[key]
        if key == "flows":
            # flows.json documents {summary, flows:[...]}; the data may be either
            if isinstance(obj, list):
                obj = {"flows": obj}
        if key == "database" and isinstance(obj, dict):
            obj = {k: v for k, v in obj.items() if k != "erDiagram"}
        if key == "architecture" and isinstance(obj, dict):
            obj = {k: v for k, v in obj.items() if k != "moduleGraph"}
        write(fname, obj)

    # meta / tree / notes live in their own files
    meta = dict(D.get("meta") or {})
    ov = D.get("overview") or {}
    # project identity belongs in meta.json; keep the Overview payload too so both
    # layouts the renderer accepts round-trip cleanly
    for k in ("name", "tagline"):
        if ov.get(k) and k not in meta:
            meta[k] = ov[k]
    write("meta.json", meta)
    if D.get("tree"):
        write("tree.json", D["tree"])
    if D.get("fileNotes"):
        write("tree-notes.json", D["fileNotes"])
    if D.get("unconfirmed"):
        write("unconfirmed.json", D["unconfirmed"])

    # routes: keep the documented bare-array shape
    if D.get("endpoints"):
        write("endpoints.json", D["endpoints"])

    print(f"{'would recover' if args.print_only else 'recovered'} "
          f"{len(written)} findings file(s) from {args.report}")
    for name, obj in written:
        n = len(obj) if hasattr(obj, "__len__") else "-"
        print(f"  {name:22} {type(obj).__name__:6} {n}")
    if not args.print_only:
        print(f"\nre-render with:  render_report.py --findings {args.out} --out report.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
