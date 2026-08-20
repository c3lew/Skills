$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "dashboard.original.html") -Destination (Join-Path $root "dashboard.html") -Force
if ((git -C $root hash-object dashboard.html) -ne (git -C $root rev-parse HEAD:dashboard.html)) { throw "dashboard rollback hash mismatch" }
