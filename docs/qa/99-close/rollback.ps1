$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..\..')).Path
$source = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot 'dashboard-original.html'))
$target = [IO.Path]::GetFullPath((Join-Path $root 'dashboard.html'))

if (-not $source.StartsWith($root + [IO.Path]::DirectorySeparatorChar) -or
    -not $target.StartsWith($root + [IO.Path]::DirectorySeparatorChar)) {
    throw 'rollback path escaped workspace'
}

Copy-Item -LiteralPath $source -Destination $target -Force
Write-Output "ROLLBACK_OK $target"
