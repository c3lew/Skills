$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "dashboard-original.html") -Destination (Join-Path $root "dashboard.html") -Force
Write-Output "restored dashboard.html"
