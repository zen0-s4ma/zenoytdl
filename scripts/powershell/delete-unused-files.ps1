param(
    [string]$RootPath = (Get-Location).Path,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path $RootPath).Path
$targets = @(
    'run_tests.py.bkp',
    'bloque1-music-playlist-20260318-180044.log',
    'salida-terminal.txt',
    'comandos intereantes zenoytdl.txt',
    'run-master-tests.ps1',
    'test-e2e-perfiles-subscriptions.ps1',
    'validate-test-e2e-perfiles-subscriptions.ps1',
    'test-zenoytdl/clean-windows-environment.ps1',
    'test-zenoytdl/run-e2e.ps1',
    'test-zenoytdl/run-profile-test.ps1',
    'test-zenoytdl/test-beets-only.ps1',
    'test-zenoytdl/test-trim-only.ps1',
    'test-zenoytdl/validate-downloads.ps1',
    'test-zenoytdl/_run-all-test.ps1',
    'test-zenoytdl/_shared.ps1'
)

foreach ($relative in $targets) {
    $full = Join-Path $root $relative
    if (Test-Path $full) {
        if ($DryRun) {
            Write-Host "[DRYRUN] Eliminar: $full"
        } else {
            Remove-Item -LiteralPath $full -Force -Recurse
            Write-Host "[OK] Eliminado: $full"
        }
    } else {
        Write-Host "[SKIP] No existe: $full"
    }
}
