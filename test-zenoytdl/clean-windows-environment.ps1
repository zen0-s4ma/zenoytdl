param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Step {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Title
    )

    Write-Host ""
    Write-Host "============================================================"
    Write-Host $Title
    Write-Host "============================================================"
}

function Write-Utf8NoBomLfFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [string]$Content
    )

    $normalized = $Content -replace "`r`n", "`n"
    $normalized = $normalized -replace "`r", "`n"

    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    $writer = New-Object System.IO.StreamWriter($Path, $false, $utf8NoBom)
    try {
        $writer.NewLine = "`n"
        $writer.Write($normalized)
    }
    finally {
        $writer.Dispose()
    }
}

function Invoke-DockerScriptFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Container,

        [Parameter(Mandatory = $true)]
        [string]$Script,

        [Parameter(Mandatory = $true)]
        [string]$RemoteName
    )

    $tempDir = Join-Path $env:TEMP "test-zenoytdl-clean"
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

    $localScriptPath = Join-Path $tempDir $RemoteName
    $remoteScriptPath = "/tmp/$RemoteName"

    try {
        Write-Utf8NoBomLfFile -Path $localScriptPath -Content $Script

        & docker cp $localScriptPath "${Container}:$remoteScriptPath"
        if ($LASTEXITCODE -ne 0) {
            throw "docker cp falló para '$Container' -> '$remoteScriptPath' con exit code $LASTEXITCODE"
        }

        & docker exec $Container sh $remoteScriptPath
        if ($LASTEXITCODE -ne 0) {
            throw "docker exec falló en el contenedor '$Container' al ejecutar '$remoteScriptPath' con exit code $LASTEXITCODE"
        }

        & docker exec $Container rm -f $remoteScriptPath | Out-Null
    }
    finally {
        Remove-Item $localScriptPath -Force -ErrorAction SilentlyContinue
    }
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
$testRoot = $scriptDir
$logsRoot = Join-Path $testRoot 'logs'

Write-Host ""
Write-Host "Limpieza completa previa a _run-all-test.ps1"
Write-Host "Project root: $projectRoot"
Write-Host "Test root:    $testRoot"
Write-Host "Logs root:    $logsRoot"
Write-Host "Modo logs:    NO TOCAR"

Write-Step '1) Preservar logs de tests locales'
Write-Host "[OK] No se toca la carpeta de logs local: $logsRoot"

Write-Step '2) Limpiar posibles temporales locales del proyecto'
$localPathsToClean = @(
    (Join-Path $projectRoot 'tmp'),
    (Join-Path $projectRoot 'temp'),
    (Join-Path $projectRoot '.tmp'),
    (Join-Path $projectRoot '.temp'),
    (Join-Path $projectRoot 'runsets'),
    (Join-Path $projectRoot 'generated\runsets'),
    (Join-Path $projectRoot 'generated\tmp'),
    (Join-Path $projectRoot 'generated\temp')
)

foreach ($path in $localPathsToClean) {
    if (Test-Path $path) {
        Write-Host "Borrando $path"
        Remove-Item $path -Recurse -Force -ErrorAction SilentlyContinue
    }
}
Write-Host "[OK] Limpieza local completada"

Write-Step '3) Limpiar descargas y temporales dentro de ytdl-sub'
$ytdlCleanup = @'
set -e
rm -rf /downloads/Canales-youtube/__test_* 2>/dev/null || true
rm -rf /downloads/Podcast/__test_* 2>/dev/null || true
rm -rf /downloads/TV-Serie/__test_* 2>/dev/null || true
rm -rf /downloads/Music-Playlist/__test_* 2>/dev/null || true
rm -rf /downloads/Ambience-Video/__test_* 2>/dev/null || true
rm -rf /downloads/Ambience-Audio/__test_* 2>/dev/null || true
rm -rf /downloads/__test_trim_only 2>/dev/null || true

rm -f /tmp/trim-ambience-video.py 2>/dev/null || true
rm -f /tmp/trim-ambience-media.py 2>/dev/null || true
rm -rf /tmp/zenoytdl* /tmp/test-zenoytdl* 2>/dev/null || true

find /downloads -type f \( -name '*.part' -o -name '*.ytdl' -o -name '*.tmp' -o -name '*.temp' \) -delete 2>/dev/null || true

mkdir -p /downloads
echo '[OK] Limpieza en ytdl-sub completada'
'@
Invoke-DockerScriptFile -Container 'ytdl-sub' -Script $ytdlCleanup -RemoteName 'clean-ytdl-sub.sh'

Write-Step '4) Limpiar entorno de beets'
$beetsCleanup = @'
set -e
rm -rf /downloads/Music-Playlist/__test_beets_only 2>/dev/null || true
rm -f /config/musiclibrary.db 2>/dev/null || true
rm -f /config/library.db 2>/dev/null || true
rm -f /config/logs/beets-import.log 2>/dev/null || true
rm -rf /tmp/zenoytdl* /tmp/test-zenoytdl* 2>/dev/null || true

find /downloads -type f \( -name '*.part' -o -name '*.ytdl' -o -name '*.tmp' -o -name '*.temp' \) -delete 2>/dev/null || true

mkdir -p /config/logs
echo '[OK] Limpieza en beets-streaming2 completada'
'@
Invoke-DockerScriptFile -Container 'beets-streaming2' -Script $beetsCleanup -RemoteName 'clean-beets.sh'

Write-Step '5) Limpiar logs internos historicos de contenedores'
$internalLogsCleanupYtdl = @'
set -e
find /config/logs -maxdepth 1 -type f \( -name '*.log' -o -name '*.success.log' -o -name '*.error.log' \) -delete 2>/dev/null || true
echo '[OK] Logs internos limpiados en ytdl-sub'
'@
Invoke-DockerScriptFile -Container 'ytdl-sub' -Script $internalLogsCleanupYtdl -RemoteName 'clean-ytdl-logs.sh'

$internalLogsCleanupBeets = @'
set -e
find /config/logs -maxdepth 1 -type f \( -name '*.log' -o -name '*.success.log' -o -name '*.error.log' \) -delete 2>/dev/null || true
echo '[OK] Logs internos limpiados en beets-streaming2'
'@
Invoke-DockerScriptFile -Container 'beets-streaming2' -Script $internalLogsCleanupBeets -RemoteName 'clean-beets-logs.sh'

Write-Step '6) Reiniciar contenedores'
& docker restart ytdl-sub
if ($LASTEXITCODE -ne 0) {
    throw "docker restart ytdl-sub fallo con exit code $LASTEXITCODE"
}

& docker restart beets-streaming2
if ($LASTEXITCODE -ne 0) {
    throw "docker restart beets-streaming2 fallo con exit code $LASTEXITCODE"
}

Write-Host "[OK] Contenedores reiniciados correctamente"

Write-Step '7) Estado final rapido'
$ytdlState = @'
set -e
echo '[YTdl-sub /downloads]'
find /downloads -maxdepth 2 | sort
echo
echo '[YTdl-sub /config/logs]'
find /config/logs -maxdepth 1 | sort
'@
Invoke-DockerScriptFile -Container 'ytdl-sub' -Script $ytdlState -RemoteName 'state-ytdl.sh'

$beetsState = @'
set -e
echo '[beets /downloads]'
find /downloads -maxdepth 2 | sort
echo
echo '[beets /config]'
find /config -maxdepth 2 | sort
'@
Invoke-DockerScriptFile -Container 'beets-streaming2' -Script $beetsState -RemoteName 'state-beets.sh'

Write-Host ""
Write-Host "Entorno limpio."
Write-Host "La carpeta de logs local NO ha sido tocada."
Write-Host "Ya puedes lanzar:"
Write-Host "powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\_run-all-test.ps1"