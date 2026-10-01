#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$SCRIPT_DIR/base"
TARGET_DIR="$HOME/.agents/skills"

mkdir -p "$TARGET_DIR"

if [[ ! -d "$BASE_DIR" ]]; then
    echo "Error: bundle directory does not exist: $BASE_DIR" >&2
    exit 1
fi

bundle_name="$(basename "$BASE_DIR")"

for skill_dir in "$BASE_DIR"/*; do
    [[ -d "$skill_dir" ]] || continue

    skill_name="$(basename "$skill_dir")"
    skill_label="$bundle_name/$skill_name"
    manifest="$skill_dir/SKILL.md"
    link_path="$TARGET_DIR/$skill_name"

    if [[ ! -f "$manifest" ]]; then
        echo "Skipped: $skill_label (SKILL.md not found)"
        continue
    fi

    if [[ -L "$link_path" ]]; then
        rm "$link_path"
    elif [[ -e "$link_path" ]]; then
        echo "Error: target already exists and is not a symlink: $link_path" >&2
        exit 1
    fi

    ln -s "$skill_dir" "$link_path"

    echo "Linked: $skill_label -> $link_path"
done
