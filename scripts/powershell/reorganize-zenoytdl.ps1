param(
    [string]$RootPath = (Get-Location).Path,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path $RootPath).Path

function Ensure-Dir([string]$Path) {
    if (-not (Test-Path $Path)) {
        if ($DryRun) { Write-Host "[DRYRUN] Crear carpeta: $Path" }
        else { New-Item -ItemType Directory -Path $Path -Force | Out-Null; Write-Host "[OK] Carpeta: $Path" }
    }
}

function Move-IfExists([string]$FromRelative, [string]$ToRelative) {
    $from = Join-Path $root $FromRelative
    $to = Join-Path $root $ToRelative
    if (-not (Test-Path $from)) {
        Write-Host "[SKIP] No existe: $from"
        return
    }
    Ensure-Dir (Split-Path -Parent $to)
    if ($DryRun) {
        Write-Host "[DRYRUN] Mover: $from -> $to"
    } else {
        if (Test-Path $to) { Remove-Item -LiteralPath $to -Force -Recurse }
        Move-Item -LiteralPath $from -Destination $to -Force
        Write-Host "[OK] Movido: $from -> $to"
    }
}

function Write-IfMissing([string]$RelativePath, [string]$Content) {
    $full = Join-Path $root $RelativePath
    Ensure-Dir (Split-Path -Parent $full)
    if (-not (Test-Path $full)) {
        if ($DryRun) { Write-Host "[DRYRUN] Crear fichero: $full" }
        else { Set-Content -LiteralPath $full -Value $Content -Encoding UTF8; Write-Host "[OK] Creado: $full" }
    }
}

@(
    'config/user',
    'config/runtime/prod/logs',
    'config/runtime/test/logs',
    'tools',
    'docs',
    'scripts/powershell',
    'scripts/legacy',
    '_old'
) | ForEach-Object { Ensure-Dir (Join-Path $root $_) }

# Launcher oficial y tools
Move-IfExists 'test-zenoytdl/run_tests.py' 'zenoytdl-run.py'
Move-IfExists 'generate-ytdl-config.py' 'tools/generate-ytdl-config.py'
Move-IfExists 'prepare-subscriptions-runset.py' 'tools/prepare-subscriptions-runset.py'
Move-IfExists 'trim-ambience-video.py' 'tools/trim-ambience-video.py'
Move-IfExists 'test-zenoytdl/check_music_metadata.py' 'tools/check_music_metadata.py'

# Config editable por usuario
Move-IfExists 'profiles-custom.yml' 'config/user/profiles-custom.yml'
Move-IfExists 'subscription-custom.yml' 'config/user/subscription-custom.yml'
Write-IfMissing 'config/user/README-config.md' @'
# Configuración editable por el usuario

- profiles-custom.yml
- subscription-custom.yml

Los ficheros generados no deben vivir aquí.
'@

# Runtime actual de producción
Move-IfExists 'config.generated.yaml' 'config/runtime/prod/config.generated.yaml'
Move-IfExists 'subscriptions.generated.yaml' 'config/runtime/prod/subscriptions.generated.yaml'
Move-IfExists 'subscriptions.runset.yaml' 'config/runtime/prod/subscriptions.runset.yaml'
Move-IfExists '.recent-items-state.json' 'config/runtime/prod/.recent-items-state.json'
Move-IfExists '.recent-items-state.pending.json' 'config/runtime/prod/.recent-items-state.pending.json'
Move-IfExists 'beets.music-playlist.yaml' 'config/runtime/prod/beets.music-playlist.yaml'

# Logs de test existentes
$testLogs = Join-Path $root 'test-zenoytdl/logs'
if (Test-Path $testLogs) {
    Get-ChildItem -LiteralPath $testLogs -File | ForEach-Object {
        Move-IfExists (Join-Path 'test-zenoytdl/logs' $_.Name) (Join-Path 'config/runtime/test/logs' $_.Name)
    }
}

# Documentación
Move-IfExists 'README.md' 'docs/README.md'
Move-IfExists 'DOSSIER-TECNICO.md' 'docs/DOSSIER-TECNICO.md'
Move-IfExists 'EJEMPLOS.md' 'docs/EJEMPLOS.md'
Move-IfExists 'README-mudanza-ruta.txt' 'docs/README-mudanza-ruta.txt'
Move-IfExists 'test-zenoytdl/GUIA-USO.md' 'docs/GUIA-USO.md'
Move-IfExists 'test-zenoytdl/listado-comandos-lanzar-ps1.txt' 'docs/listado-comandos-lanzar-ps1.txt'
Move-IfExists 'test-zenoytdl/listado-comandos-python.txt' 'docs/listado-comandos-python.txt'

# Scripts auxiliares no críticos para el flujo principal
Move-IfExists 'clean-music-filenames.ps1' 'scripts/powershell/clean-music-filenames.ps1'
Move-IfExists 'beets.sh' 'scripts/legacy/beets.sh'

Write-Host ''
Write-Host '[INFO] Reorganización base completada.'
Write-Host '[INFO] Este script no toca contenedores ni modifica volúmenes de descarga.'
Write-Host '[INFO] Para usar el modo test con aislamiento real, monta /downloads-test en los contenedores.'
