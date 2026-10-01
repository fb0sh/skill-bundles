#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="$HOME/.agents/skills"

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
