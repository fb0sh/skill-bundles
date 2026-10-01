$ErrorActionPreference = "Stop"

$baseDir   = Join-Path $PSScriptRoot "base"
$targetDir = Join-Path $HOME ".agents\skills"

[System.IO.Directory]::CreateDirectory($targetDir) | Out-Null

if (-not (Test-Path -LiteralPath $baseDir -PathType Container)) {
    throw "Bundle directory does not exist: $baseDir"
}

$bundleName = Split-Path $baseDir -Leaf

Get-ChildItem -LiteralPath $baseDir -Directory | ForEach-Object {
    $skillDir   = $_.FullName
    $skillName  = $_.Name
    $skillLabel = "$bundleName/$skillName"
    $manifest   = Join-Path $skillDir "SKILL.md"
    $linkPath   = Join-Path $targetDir $skillName

    if (-not (Test-Path -LiteralPath $manifest -PathType Leaf)) {
        Write-Warning "Skipped: $skillLabel (SKILL.md not found)"
        return
    }

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

    Write-Host "Linked: $skillLabel -> $linkPath"
}
