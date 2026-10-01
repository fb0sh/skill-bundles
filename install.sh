#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="$HOME/.agents/skills"

# Some skills are pinned as git submodules; make sure they are present first.
if command -v git >/dev/null 2>&1 && git -C "$SCRIPT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "Updating git submodules..."
    git -C "$SCRIPT_DIR" submodule update --init --recursive
else
    echo "Warning: git not available or not a git checkout; skipping submodule update" >&2
fi

mkdir -p "$TARGET_DIR"

for bundle_dir in "$SCRIPT_DIR"/*; do
    [[ -d "$bundle_dir" ]] || continue

    bundle_name="$(basename "$bundle_dir")"

    for skill_dir in "$bundle_dir"/*; do
        [[ -d "$skill_dir" ]] || continue

        skill_name="$(basename "$skill_dir")"
        manifest="$skill_dir/SKILL.md"

        # A valid skill must contain SKILL.md
        [[ -f "$manifest" ]] || continue

        skill_label="$bundle_name/$skill_name"
        link_path="$TARGET_DIR/$skill_name"

        if [[ -L "$link_path" ]]; then
            rm "$link_path"
        elif [[ -e "$link_path" ]]; then
            echo "Error: target already exists and is not a symlink: $link_path" >&2
            exit 1
        fi

        ln -s "$skill_dir" "$link_path"

        echo "Linked: $skill_label -> $link_path"
    done
done
