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
