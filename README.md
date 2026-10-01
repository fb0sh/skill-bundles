# skill-bundle

集中管理并安装个人 Agent Skills。

`skill-bundle` 将多个 Skill 统一存放在仓库的 `base/` 目录中，通过符号链接将它们暴露到：

```text
~/.agents/skills/
```

这样可以统一使用 Git 管理所有 Skill，同时保持 `~/.agents/skills/` 符合 Agent Skills 的目录结构。

## 目录结构

```text
skill-bundle/
├── base/
│   ├── skill1/
│   │   └── SKILL.md
│   ├── skill2/
│   │   └── SKILL.md
│   └── skill3/
│       └── SKILL.md
├── install.ps1
├── install.sh
└── README.md
```

每个 Skill 必须直接位于 `base/` 下，并包含 `SKILL.md`：

```text
base/<skill-name>/SKILL.md
```

执行安装脚本后：

```text
~/.agents/skills/
├── skill1 -> <skill-bundle>/base/skill1
├── skill2 -> <skill-bundle>/base/skill2
└── skill3 -> <skill-bundle>/base/skill3
```

Skill 的实际文件仍然保存在本仓库中。

## 安装

### Windows

使用 PowerShell：

```powershell
.\install.ps1
```

脚本会自动递归创建：

```text
~/.agents/skills/
```

然后扫描：

```text
base/*
```

所有包含 `SKILL.md` 的目录都会链接到 `~/.agents/skills/`。

Windows 默认推荐使用 Junction，适合本地目录链接，并且通常具有更好的权限兼容性。

`install.ps1`：

```powershell
$ErrorActionPreference = "Stop"

$baseDir   = Join-Path $PSScriptRoot "base"
$targetDir = Join-Path $HOME ".agents\skills"

# Create ~/.agents/skills recursively
[System.IO.Directory]::CreateDirectory($targetDir) | Out-Null

if (-not (Test-Path -LiteralPath $baseDir -PathType Container)) {
    throw "Bundle directory does not exist: $baseDir"
}

Get-ChildItem -LiteralPath $baseDir -Directory | ForEach-Object {
    $skillDir = $_.FullName
    $manifest = Join-Path $skillDir "SKILL.md"

    if (-not (Test-Path -LiteralPath $manifest -PathType Leaf)) {
        Write-Warning "Skipped $($_.Name): SKILL.md not found"
        return
    }

    $linkPath = Join-Path $targetDir $_.Name
    $existing = Get-Item -LiteralPath $linkPath -Force -ErrorAction SilentlyContinue

    if ($existing) {
        if ($existing.LinkType -in @("SymbolicLink", "Junction")) {
            Remove-Item -LiteralPath $linkPath -Force
        }
        else {
            throw "Target already exists and is not a link: $linkPath"
        }
    }

    New-Item `
        -ItemType Junction `
        -Path $linkPath `
        -Target $skillDir | Out-Null

    Write-Host "Linked: $($_.Name) -> $skillDir"
}
```

### Linux / macOS

执行：

```bash
chmod +x install.sh
./install.sh
```

脚本会自动创建：

```text
~/.agents/skills/
```

并为 `base/` 中所有有效 Skill 创建符号链接。

`install.sh`：

```bash
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

for skill_dir in "$BASE_DIR"/*; do
    [[ -d "$skill_dir" ]] || continue

    skill_name="$(basename "$skill_dir")"
    manifest="$skill_dir/SKILL.md"
    link_path="$TARGET_DIR/$skill_name"

    if [[ ! -f "$manifest" ]]; then
        echo "Skipped $skill_name: SKILL.md not found"
        continue
    fi

    if [[ -L "$link_path" ]]; then
        rm "$link_path"
    elif [[ -e "$link_path" ]]; then
        echo "Error: target already exists and is not a symlink: $link_path" >&2
        exit 1
    fi

    ln -s "$skill_dir" "$link_path"

    echo "Linked: $skill_name -> $skill_dir"
done
```

## 添加 Skill

直接在 `base/` 中添加新的 Skill：

```text
base/
└── my-skill/
    └── SKILL.md
```

然后重新执行安装脚本：

```bash
./install.sh
```

或者 Windows：

```powershell
.\install.ps1
```

新的 Skill 会自动链接到：

```text
~/.agents/skills/my-skill
```

## 更新 Skill

Skill 文件直接保存在仓库：

```text
base/<skill-name>/
```

因此可以正常使用 Git：

```bash
git pull
```

符号链接无需重新创建，更新后的 Skill 会立即反映到 `~/.agents/skills/`。

只有新增或删除 Skill 时需要重新运行安装脚本。

## 设计原则

仓库负责 Skill 的版本管理：

```text
skill-bundle/base/
```

Agent 使用标准位置发现 Skill：

```text
~/.agents/skills/
```

两者通过目录链接连接：

```text
skill-bundle/base/<skill>
            │
            └──────────────> ~/.agents/skills/<skill>
```

这样可以避免复制 Skill 文件，同时允许整个 Skill 集合通过一个 Git 仓库统一维护。