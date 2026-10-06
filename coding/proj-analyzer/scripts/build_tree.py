#!/usr/bin/env python3
"""Build an annotated file-tree JSON for the report's File Explorer.

The tree is the report's map: it must show the architecture, not every artifact.
So it deliberately excludes build output, dependencies and caches, caps depth, and
marks the entries the analyst flagged as core or generated.

Annotations come from an optional JSON file mapping repo-relative path -> note:

  {
    "apps/api/src/bootstrap/routes.rs": {
      "role": "single place where all HTTP routes are registered",
      "module": "bootstrap",
      "core": true
    },
    "apps/api/src/entity": { "role": "generated SeaORM entities", "core": true }
  }

Any key that is a directory annotates that directory; a key that is a file
annotates that file. Missing annotations are fine — the report shows the tree
structure and marks un-annotated paths as unverified.

Usage
-----
  build_tree.py --root . --out .proj-analysis/tree.json \
      --annotations .proj-analysis/tree-notes.json
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import sys

DEFAULT_EXCLUDE = [
    ".git", "node_modules", "target", "dist", "build", "out", "coverage",
    ".next", ".nuxt", ".svelte-kit", ".venv", "venv", "__pycache__", ".mypy_cache",
    ".pytest_cache", ".ruff_cache", ".gradle", ".idea", ".vscode", ".cache",
    ".terraform", "vendor", "Pods", ".dart_tool", ".turbo", ".parcel-cache",
    # the analysis tooling itself must never appear as part of the project
    ".proj-analysis", ".agents", ".claude", ".codex",
]

DEFAULT_GENERATED = [
    "*.gen.ts", "*.gen.tsx", "*_pb2.py", "*.pb.go", "*_pb2_grpc.py",
    "*.g.dart", "*.freezed.dart", "*_generated.go", "routeTree.gen.ts",
]

DEFAULT_ASSET_EXT = (
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".svg", ".pdf",
    ".woff", ".woff2", ".ttf", ".eot", ".mp4", ".webm", ".zip", ".tar",
    ".gz", ".bz2", ".xz", ".7z", ".jar", ".so", ".dylib", ".dll", ".exe",
    ".bin", ".wasm", ".onnx", ".parquet", ".sqlite", ".db",
)


def count_lines(path: str) -> int | None:
    try:
        with open(path, "rb") as f:
            return sum(1 for _ in f)
    except OSError:
        return None


def build(abs_dir, rel_dir, depth, cfg):
    name = os.path.basename(abs_dir) if rel_dir else os.path.basename(os.path.abspath(cfg["root"]))
    node = {"name": name or "repo", "path": rel_dir or ".", "type": "dir"}
    note = cfg["notes"].get(rel_dir)
    if note:
        node.update({k: v for k, v in note.items() if k in ("role", "module", "core", "note")})
    children = []
    try:
        entries = sorted(os.listdir(abs_dir))
    except OSError:
        entries = []
    for e in entries:
        if e.startswith(".") and e in cfg["exclude"]:
            continue
        p = os.path.join(abs_dir, e)
        r = os.path.join(rel_dir, e) if rel_dir else e
        if os.path.isdir(p):
            if e in cfg["exclude"]:
                continue
            if depth >= cfg["max_depth"]:
                # keep a visible placeholder so the reader knows the tree was cut
                children.append({"name": e, "path": r, "type": "dir", "role": "（已按深度上限折叠）"})
                continue
            children.append(build(p, r, depth + 1, cfg))
            continue
        if any(fnmatch.fnmatch(e, pat) for pat in cfg["exclude_files"]):
            continue
        if e.lower().endswith(DEFAULT_ASSET_EXT):
            c = {"name": e, "path": r, "type": "asset"}
        else:
            c = {"name": e, "path": r, "type": "file"}
            lines = count_lines(p)
            if lines is not None:
                c["lines"] = lines
        if any(fnmatch.fnmatch(e, pat) for pat in cfg["generated"]):
            c["generated"] = True
            c["core"] = False
        note = cfg["notes"].get(r)
        if note:
            c.update({k: v for k, v in note.items() if k in ("role", "module", "core", "note")})
            if note.get("core"):
                c["core"] = True
        children.append(c)
    children.sort(key=lambda c: (c["type"] != "dir", c["name"].lower()))
    node["children"] = children[: cfg["max_children"]]
    return node


def collect_stats(node, acc):
    acc["dirs" if node["type"] == "dir" else "files"] += 1
    if node.get("core"):
        acc["core"] += 1
    for c in node.get("children", []):
        collect_stats(c, acc)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default=".proj-analysis/tree.json")
    ap.add_argument("--annotations", help="JSON file mapping repo-relative path -> note")
    ap.add_argument("--exclude", action="append", default=[],
                    help="extra directory name to skip (repeatable)")
    ap.add_argument("--exclude-file", action="append", default=[],
                    help="extra filename glob to skip (repeatable)")
    ap.add_argument("--generated", action="append", default=[],
                    help="extra generated-file glob (repeatable)")
    ap.add_argument("--max-depth", type=int, default=5)
    ap.add_argument("--max-children", type=int, default=400)
    args = ap.parse_args()

    notes = {}
    if args.annotations and os.path.exists(args.annotations):
        notes = json.load(open(args.annotations, encoding="utf-8"))
    cfg = {
        "root": args.root,
        "exclude": set(DEFAULT_EXCLUDE) | set(args.exclude),
        "exclude_files": [".DS_Store", "Thumbs.db"] + list(args.exclude_file),
        "generated": DEFAULT_GENERATED + list(args.generated),
        "notes": notes,
        "max_depth": args.max_depth,
        "max_children": args.max_children,
    }
    tree = build(args.root, "", 0, cfg)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(tree, f, ensure_ascii=False)

    acc = {"dirs": 0, "files": 0, "core": 0}
    collect_stats(tree, acc)
    unannotated_core_hint = acc["files"] - sum(
        1 for _ in _walk_paths(tree) if notes.get(_)
    )
    print(f"tree: {acc['dirs']} dirs, {acc['files']} files, {acc['core']} marked core "
          f"({len(notes)} annotations, {unannotated_core_hint} un-annotated entries)")
    if not notes:
        print("  NOTE: no annotations supplied — the File Explorer will show structure only. "
              "Annotating the 15-30 most important paths is what makes it a map instead of a listing.")
    return 0


def _walk_paths(node):
    if node["path"] != ".":
        yield node["path"]
    for c in node.get("children", []):
        yield from _walk_paths(c)


if __name__ == "__main__":
    sys.exit(main())
