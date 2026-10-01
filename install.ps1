$ErrorActionPreference = "Stop"

$scriptDir = $PSScriptRoot
$targetDir = Join-Path $HOME ".agents\skills"

# Some skills are pinned as git submodules; make sure they are present first.
if (Get-Command git -ErrorAction SilentlyContinue) {
    git -C $scriptDir rev-parse --is-inside-work-tree 2>$null | Out-Null

    if ($LASTEXITCODE -eq 0) {
        Write-Host "Updating git submodules..."
        git -C $scriptDir submodule sync --recursive
        git -C $scriptDir submodule update --init --recursive

        if ($LASTEXITCODE -ne 0) {
            throw "git submodule update failed with exit code $LASTEXITCODE"
        }
    }
    else {
        Write-Warning "Not a git checkout; skipping submodule update"
    }
}
else {
    Write-Warning "git not found; skipping submodule update"
}

# Recursively create ~/.agents/skills
[System.IO.Directory]::CreateDirectory($targetDir) | Out-Null

Get-ChildItem -LiteralPath $scriptDir -Directory | ForEach-Object {
    $bundleDir  = $_.FullName
    $bundleName = $_.Name

    Get-ChildItem -LiteralPath $bundleDir -Directory | ForEach-Object {
        $skillDir  = $_.FullName
        $skillName = $_.Name
        $manifest  = Join-Path $skillDir "SKILL.md"

        # Only treat directories containing SKILL.md as skills
        if (-not (Test-Path -LiteralPath $manifest -PathType Leaf)) {
            return
        }

        $skillLabel = "$bundleName/$skillName"
        $linkPath   = Join-Path $targetDir $skillName

        $existing = Get-Item `
            -LiteralPath $linkPath `
            -Force `
            -ErrorAction SilentlyContinue

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

        Write-Host "Linked: $skillLabel -> $linkPath"
    }
}
