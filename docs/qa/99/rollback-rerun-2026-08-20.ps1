$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..\..')).Path
$target = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot 'rerun-2026-08-20'))

if (-not $target.StartsWith($root + [IO.Path]::DirectorySeparatorChar)) {
    throw "rollback target escaped workspace: $target"
}

if (Test-Path -LiteralPath $target) {
    Remove-Item -LiteralPath $target -Recurse -Force
}

Write-Output "ROLLBACK_OK $target"
