Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $repoRoot

try {
    $originalPath = $env:PATH
    $fixturesBin = Join-Path $repoRoot 'tests/fixtures/bin'
    $env:PATH = "$fixturesBin;$env:PATH"

    python -m src.api.cli --config tests/fixtures/clean/minimal.yaml
}
finally {
    if ($null -ne $originalPath) {
        $env:PATH = $originalPath
    }
    Pop-Location
}
