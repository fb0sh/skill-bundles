#!/usr/bin/env python3
"""Assemble PROJECT-ANALYSIS.html from a findings directory.

The report is data-driven: this script reads whatever findings files exist,
derives the diagrams that can be derived mechanically (ER graph from
`erLayout`/`erCore`), injects everything as one JSON blob into the bundled
HTML shell, and writes a single self-contained file with no network access.

Sections with no data are dropped from the navigation, so a project without a
database or without a frontend simply does not show those pages.

Usage
-----
  render_report.py --findings .proj-analysis \
      --out PROJECT-ANALYSIS.html --name FloatCTF --brand "FloatCTF · 项目分析"

Findings files are looked up by name inside --findings:
  meta.json architecture.json modules.json endpoints.json flows.json
  database.json config.json auth.json frontend.json jobs.json deps.json
  deploy.json entry.json risks.json tree.json tree-notes.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.normpath(os.path.join(HERE, "..", "assets"))

# ordered: earlier entries win when several findings files report the same gap
UNCONFIRMED_SOURCES = ["meta", "architecture", "modules", "database", "config",
                       "auth", "frontend", "jobs", "deps", "deploy", "risks"]


def load_dir(path: str) -> dict:
    out = {}
    if not os.path.isdir(path):
        return out
    for fn in sorted(os.listdir(path)):
        if not fn.endswith(".json"):
            continue
        key = fn[:-5]
        try:
            out[key] = json.load(open(os.path.join(path, fn), encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            print(f"  ! skipping {fn}: {e}", file=sys.stderr)
    return out


# ── derived diagram: ER graph ───────────────────────────────────────────
def er_svg(db: dict) -> str:
    layout = db.get("erLayout") or []
    core = db.get("erCore") or []
    known = {t for g in layout for t in (g.get("tables") or [])}
    if not layout or not known:
        return ""
    BW, BH, VG, PAD, LBL, GAP = 176, 26, 7, 14, 20, 16
    groups = []
    for g in sorted(layout, key=lambda x: x.get("order", 99)):
        ts = [t for t in (g.get("tables") or []) if t in known]
        if not ts:
            continue
        groups.append({"name": g.get("group", "?"), "tables": ts,
                       "w": BW + PAD * 2, "h": LBL + len(ts) * (BH + VG) + PAD * 2})
    if not groups:
        return ""
    ncol = 3 if len(groups) > 4 else (2 if len(groups) > 2 else 1)
    cols, heights = [[] for _ in range(ncol)], [0] * ncol
    for g in sorted(groups, key=lambda x: -x["h"]):
        i = heights.index(min(heights))
        cols[i].append(g)
        heights[i] += g["h"] + GAP
    colw = max(g["w"] for g in groups) + GAP
    pos = {}
    for ci, col in enumerate(cols):
        y = 12
        for g in col:
            g["x"], g["y"] = 12 + ci * colw, y
            for ti, t in enumerate(g["tables"]):
                pos[t] = (g["x"] + PAD, g["y"] + LBL + PAD + ti * (BH + VG))
            y += g["h"] + GAP
    W = int(12 + colw * ncol)
    H = int(max((g["y"] + g["h"] for g in groups), default=200) + 20)
    palette = ["#2456d6", "#1a7f4b", "#9a6100", "#6b3fa0", "#0b6b8f", "#b3261e", "#4a5568", "#a0217a"]
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
           'font-family="ui-monospace,Menlo,Consolas,monospace">',
           '<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
           'orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#8b939f"/></marker></defs>']
    for r in core:
        f, t = r.get("from"), r.get("to")
        if f not in pos or t not in pos:
            continue
        x1, y1 = pos[f][0] + BW / 2, pos[f][1] + BH / 2
        x2, y2 = pos[t][0] + BW / 2, pos[t][1] + BH / 2
        mx = (x1 + x2) / 2
        # zlib.crc32, not hash(): Python randomises str hashing per process, which
        # would give the same findings a different diagram colour on every render
        col = palette[zlib.crc32(f.encode("utf-8")) % len(palette)]
        out.append(f'<path d="M{x1:.0f},{y1:.0f} C{mx:.0f},{y1:.0f} {mx:.0f},{y2:.0f} {x2:.0f},{y2:.0f}" '
                   f'fill="none" stroke="{col}" stroke-width="1" opacity="0.42" marker-end="url(#ar)">'
                   f'<title>{f} → {t} ({r.get("card","")}) via {r.get("via","")}</title></path>')
    for gi, g in enumerate(groups):
        col = palette[gi % len(palette)]
        out.append(f'<rect x="{g["x"]}" y="{g["y"]}" width="{g["w"]}" height="{g["h"]}" rx="6" fill="none" '
                   f'stroke="{col}" stroke-dasharray="3 3" opacity="0.55"/>')
        out.append(f'<text x="{g["x"]+PAD}" y="{g["y"]+14}" font-size="10" fill="{col}" '
                   f'letter-spacing="0.5">{g["name"].upper()}</text>')
        for t in g["tables"]:
            bx, by = pos[t]
            out.append(f'<rect x="{bx}" y="{by}" width="{BW}" height="{BH}" rx="4" fill="var(--bg-elev)" '
                       f'stroke="{col}" stroke-width="1.1"/>')
            out.append(f'<text x="{bx+8}" y="{by+17}" font-size="11" fill="var(--fg)">{t}</text>')
    out.append("</svg>")
    return "".join(out)


# ── normalisation ───────────────────────────────────────────────────────
def normalise(f: dict) -> dict:
    """Accept the documented schema plus common shorthand from ad-hoc findings."""
    cfg = f.get("config") or {}
    if "items" not in cfg and "configs" in cfg:
        cfg["items"] = cfg.pop("configs")
    if "loader" not in cfg and "loader" not in cfg:
        cfg["loader"] = {}
    cfg.setdefault("items", [])
    f["config"] = cfg

    risks = f.get("risks") or {}
    for r in risks.get("risks", []) or []:
        if "phenomenon" not in r and "现象" in r:
            r["phenomenon"] = r.pop("现象")
    f["risks"] = risks

    mods = f.get("modules") or {}
    if "modules" not in mods and "list" in mods:
        mods["modules"] = mods.pop("list")
    mods.setdefault("modules", [])
    f["modules"] = mods

    ar = f.get("architecture") or {}
    if "modules" not in ar and mods.get("modules"):
        ar["modules"] = mods["modules"]
    f["architecture"] = ar

    db = f.get("database") or {}
    if db:
        db["erDiagram"] = er_svg(db)
    f["database"] = db

    return f


def collect_unconfirmed(f: dict) -> list:
    out = []
    for key in UNCONFIRMED_SOURCES:
        obj = f.get(key)
        if isinstance(obj, dict):
            for n in obj.get("notes") or []:
                out.append(f"<b>[{key}]</b> {n}")
    return out


# ── secret scan ─────────────────────────────────────────────────────────
SECRET_PATTERNS = [
    (re.compile(r"(?i)\b(password|passwd|pwd|secret|token|api[_-]?key|private[_-]?key)\b\s*[:=]\s*[\"']([^\"'\s]{8,})[\"']"),
     "quoted credential-looking assignment"),
    (re.compile(r"(?i)\b(postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|amqp|https?)://[^/\s\"'<>]{0,64}:[^@/\s\"'<>]{3,}@"),
     "connection string with inline credentials"),
    (re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), "AWS access key id"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"), "GitHub token"),
    (re.compile(r"\bsk-[A-Za-z0-9]{32,}\b"), "OpenAI-style key"),
    (re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----"), "private key block"),
]
# Text that looks like a credential but is a documented placeholder. Keep the
# redaction convention (USER:PASS / ***) in this list, or the scan cries wolf and
# people stop reading it.
SAFE_HINTS = ("example", "placeholder", "changeme", "change-me", "your-", "<", "xxx",
              "todo", "redacted", "dummy", "fake", "secret(***)", "***",
              "user:pass", "username:password", "user:***", ":***@", "user:pw",
              "${", "{{", "%s", "$(")


def scan_secrets(text: str) -> list:
    hits = []
    for pat, label in SECRET_PATTERNS:
        for m in pat.finditer(text):
            frag = m.group(0)
            if any(h in frag.lower() for h in SAFE_HINTS):
                continue
            hits.append((label, frag[:90]))
    return hits


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--findings", default=".proj-analysis", help="directory holding the findings JSON files")
    ap.add_argument("--out", default="PROJECT-ANALYSIS.html")
    ap.add_argument("--name", default="Project")
    ap.add_argument("--brand", default=None, help="top-left label, defaults to '<name> · 项目分析'")
    ap.add_argument("--lang", default="zh-CN")
    ap.add_argument("--title", default=None)
    ap.add_argument("--strict-secrets", action="store_true", help="exit non-zero if a credential-looking value is found")
    args = ap.parse_args()

    raw = load_dir(args.findings)
    if not raw:
        print(f"error: no findings JSON found in {args.findings}", file=sys.stderr)
        return 2

    f = normalise(raw)

    # The documented schema puts the project identity AND the Overview content in
    # meta.json; a separate overview.json is also accepted. Support both so a
    # hand-written findings directory never silently loses the Overview page.
    meta = f.get("meta") or {}
    ov = f.get("overview") or {}
    if not ov:
        ov = {k: meta[k] for k in ("oneLiner", "type", "shape", "repoState", "stack",
                                   "archPoints", "stats", "keyEntries", "surface", "caveats")
              if meta.get(k)}
    meta.setdefault("name", ov.get("name") or args.name)
    if not meta.get("tagline") and ov.get("tagline"):
        meta["tagline"] = ov["tagline"]
    f["meta"] = meta
    f["overview"] = ov

    tree = f.get("tree")
    if tree:
        acc = {"dirs": 0, "files": 0}

        def walk(n):
            if n.get("type") == "dir":
                acc["dirs"] += 1
            elif n.get("type") != "asset":
                acc["files"] += 1
            for c in n.get("children", []):
                walk(c)

        walk(tree)
        f.setdefault("stats", {})["treeCount"] = f"{acc['files']} files / {acc['dirs']} dirs"
    else:
        f.setdefault("stats", {})

    # file annotations: tree notes are also exposed to the detail panel
    f["fileNotes"] = f.get("tree-notes") or {}
    for m in (f.get("modules") or {}).get("modules", []) or []:
        for kf in m.get("keyFiles") or []:
            if not kf.get("path"):
                continue
            note = f["fileNotes"].setdefault(kf["path"], {})
            note.setdefault("module", m.get("name", ""))
            note.setdefault("role", kf.get("role", ""))
            note.setdefault("usedBy", m.get("downstream") or [])

    # A curated unconfirmed.json (bare array) wins over aggregation, so an analyst
    # can hand-pick the list; otherwise gather every findings file's `notes`.
    curated = f.get("unconfirmed")
    if isinstance(curated, list) and curated:
        f["unconfirmed"] = curated
    elif isinstance(curated, dict) and curated.get("items"):
        f["unconfirmed"] = curated["items"]
    else:
        f["unconfirmed"] = collect_unconfirmed(f)

    data_json = json.dumps(f, ensure_ascii=False).replace("</", "<\\/")
    head = open(os.path.join(ASSETS, "tpl_head.html"), encoding="utf-8").read()
    body = open(os.path.join(ASSETS, "tpl_body.html"), encoding="utf-8").read()
    html = (head
            .replace("__LANG__", args.lang)
            .replace("__TITLE__", args.title or f"{meta['name']} · 项目分析报告")
            .replace("__BRAND__", args.brand or f"{meta['name']} · 项目分析")
            .replace("__SEARCH_PLACEHOLDER__", "搜索文件 / 模块 / API / 配置 / 模型 / 符号…")
            + "\n" + body.replace("__DATA_JSON__", data_json))

    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(html)

    # ── self-checks ──
    sections = {
        "overview": bool(f.get("meta")),
        "architecture": bool(f.get("architecture")),
        "files": bool(f.get("tree")),
        "modules": bool((f.get("modules") or {}).get("modules")),
        "api": bool(f.get("endpoints")),
        "flows": bool((f.get("flows") or {}).get("flows")),
        "database": bool((f.get("database") or {}).get("tables")),
        "config": bool((f.get("config") or {}).get("items")),
        "auth": bool(f.get("auth")),
        "frontend": bool((f.get("frontend") or {}).get("pages")),
        "jobs": bool((f.get("jobs") or {}).get("tasks")),
        "deps": bool((f.get("deps") or {}).get("groups")),
        "deploy": bool(f.get("deploy")),
        "entry": bool((f.get("entry") or {}).get("order")),
        "risks": bool((f.get("risks") or {}).get("risks")),
    }
    present = [k for k, v in sections.items() if v]
    missing = [k for k, v in sections.items() if not v]

    print(f"wrote {args.out} ({len(html):,} bytes)")
    print(f"  sections present: {', '.join(present)}")
    if missing:
        print(f"  sections omitted (no findings): {', '.join(missing)}")
    print(f"  endpoints={len(f.get('endpoints') or [])} "
          f"tables={len((f.get('database') or {}).get('tables') or [])} "
          f"modules={len((f.get('modules') or {}).get('modules') or [])} "
          f"risks={len((f.get('risks') or {}).get('risks') or [])} "
          f"unconfirmed={len(f['unconfirmed'])}")

    # embedded JSON must round-trip, or the page renders nothing at all
    m = re.search(r'<script id="report-data" type="application/json">(.*?)</script>', html, re.S)
    try:
        json.loads(m.group(1))
    except Exception as e:  # noqa: BLE001
        print(f"  ! FATAL: embedded JSON does not parse: {e}", file=sys.stderr)
        return 1
    if "__DATA_JSON__" in html:
        print("  ! FATAL: template placeholder was not replaced", file=sys.stderr)
        return 1
    externals = re.findall(r'<(?:script|link)[^>]*(?:src|href)="(?!#)([^"]+)"', html)
    if externals:
        print(f"  ! WARNING: external resources found (report must work offline): {externals}")

    hits = scan_secrets(html)
    if hits:
        print(f"  ! SECRET SCAN: {len(hits)} credential-looking value(s) in the output:")
        for label, frag in hits[:15]:
            print(f"      [{label}] {frag}")
        print("      Redact these in the findings JSON and re-render.")
        if args.strict_secrets:
            return 1
    else:
        print("  secret scan: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
