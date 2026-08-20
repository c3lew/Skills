$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "validate.py.original") -Destination (Join-Path $root "scripts\validate.py") -Force
python (Join-Path $root "scripts\validate.py") --self-check
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
