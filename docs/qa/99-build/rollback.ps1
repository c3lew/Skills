$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "dashboard-original.html") -Destination (Join-Path $root "dashboard.html") -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "README-original.md") -Destination (Join-Path $root "scripts\qa\README.md") -Force
Write-Output "OK #99 workspace rollback"
