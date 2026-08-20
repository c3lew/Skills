param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path,
    [string]$ClaudeSkillsRoot = (Join-Path $HOME ".claude\skills"),
    [string]$AgentSkillsRoot = (Join-Path $HOME ".agents\skills")
)

$ErrorActionPreference = "Stop"
$dashboardBackup = Join-Path $PSScriptRoot "dashboard.original.html"
$nextBackup = Join-Path $PSScriptRoot "next.previous.SKILL.md"
$dashboardTarget = Join-Path $RepoRoot "dashboard.html"
$nextTargets = @(
    (Join-Path $ClaudeSkillsRoot "next\SKILL.md"),
    (Join-Path $AgentSkillsRoot "next\SKILL.md")
)

Copy-Item -LiteralPath $dashboardBackup -Destination $dashboardTarget -Force
foreach ($target in $nextTargets) {
    New-Item -ItemType Directory -Path (Split-Path $target) -Force | Out-Null
    Copy-Item -LiteralPath $nextBackup -Destination $target -Force
}

Write-Output "OK restored dashboard and the pre-#42 next skill"
