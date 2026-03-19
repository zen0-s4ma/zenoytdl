param(
    [string]$ProfileName,
    [switch]$CleanLogs
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$TestRoot    = $PSScriptRoot
$LogsRoot    = Join-Path $TestRoot "logs"

function Write-Step([string]$Text) {
    Write-Host ""
    Write-Host "============================================================"
    Write-Host $Text
    Write-Host "============================================================"
}

function Write-Ok([string]$Text) {
    Write-Host "[OK] $Text"
}

function Write-Warn([string]$Text) {
    Write-Host "[WARN] $Text"
}

function Write-Info([string]$Text) {
    Write-Host "[INFO] $Text"
}

function Invoke-DockerScript {
    param(
        [Parameter(Mandatory = $true)][string]$Container,
        [Parameter(Mandatory = $true)][string]$ScriptContent,
        [Parameter(Mandatory = $true)][string]$RemoteName
    )

    $tempFile = Join-Path $env:TEMP $RemoteName
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($tempFile, $ScriptContent, $utf8NoBom)

    try {
        docker cp $tempFile "${Container}:/tmp/$RemoteName"
        if ($LASTEXITCODE -ne 0) {
            throw "docker cp falló al copiar $RemoteName a $Container"
        }

        docker exec $Container sh "/tmp/$RemoteName"
        if ($LASTEXITCODE -ne 0) {
            throw "docker exec falló en el contenedor '$Container' al ejecutar '/tmp/$RemoteName' con exit code $LASTEXITCODE"
        }
    }
    finally {
        Remove-Item $tempFile -Force -ErrorAction SilentlyContinue
    }
}

function Remove-DirectoryContents {
    param(
        [Parameter(Mandatory = $true)][string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }

    Get-ChildItem -LiteralPath $Path -Force -ErrorAction SilentlyContinue | ForEach-Object {
        Remove-Item -LiteralPath $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
    }
}

function Get-ProfileDownloadRoots {
    param(
        [string]$Profile
    )

    $map = [ordered]@{
        "canales-youtube" = @("/downloads/Canales-youtube")
        "podcast"         = @("/downloads/Podcast")
        "tv-serie"        = @("/downloads/TV-Serie")
        "music-playlist"  = @("/downloads/Music-Playlist")
        "ambience-video"  = @("/downloads/Ambience-Video")
        "ambience-audio"  = @("/downloads/Ambience-Audio")
    }

    if ([string]::IsNullOrWhiteSpace($Profile)) {
        return @(
            "/downloads/Canales-youtube",
            "/downloads/Podcast",
            "/downloads/TV-Serie",
            "/downloads/Music-Playlist",
            "/downloads/Ambience-Video",
            "/downloads/Ambience-Audio"
        )
    }

    $key = $Profile.Trim().ToLowerInvariant()
    if ($map.Contains($key)) {
        return $map[$key]
    }

    throw "Perfil no soportado para limpieza: $Profile"
}

function Normalize-ProfileName {
    param([string]$Value)

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return $null
    }

    $v = $Value.Trim().ToLowerInvariant()

    switch ($v) {
        "canales-youtube" { return "canales-youtube" }
        "podcast"         { return "podcast" }
        "tv-serie"        { return "tv-serie" }
        "music-playlist"  { return "music-playlist" }
        "ambience-video"  { return "ambience-video" }
        "ambience-audio"  { return "ambience-audio" }
        default {
            throw "ProfileName no soportado: $Value"
        }
    }
}

function Reset-StateFile {
    param(
        [Parameter(Mandatory = $true)][string]$Path
    )

    try {
        $emptyState = @{
            sources = @{}
        }

        $json = ($emptyState | ConvertTo-Json -Depth 10) + "`n"
        $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
        [System.IO.File]::WriteAllText($Path, $json, $utf8NoBom)
    }
    catch {
        throw "No se pudo recrear el state vacío en: $Path"
    }
}

$NormalizedProfile = Normalize-ProfileName -Value $ProfileName
$scopeLabel = if ($NormalizedProfile) { $ProfileName } else { "TODOS LOS PERFILES" }

Write-Host ""
Write-Host "Limpieza completa previa a pruebas"
Write-Host "Project root: $ProjectRoot"
Write-Host "Test root:    $TestRoot"
Write-Host "Logs root:    $LogsRoot"
Write-Host "Scope:        $scopeLabel"
Write-Host "CleanLogs:    $($CleanLogs.IsPresent)"

$DownloadRoots = Get-ProfileDownloadRoots -Profile $NormalizedProfile

Write-Step "1) Limpiar logs locales si se ha pedido"
if ($CleanLogs) {
    if (Test-Path -LiteralPath $LogsRoot) {
        Write-Host "Borrando contenido de logs local: $LogsRoot"
        Remove-DirectoryContents -Path $LogsRoot
    }
    else {
        New-Item -ItemType Directory -Path $LogsRoot -Force | Out-Null
    }
    Write-Ok "Carpeta de logs local limpiada"
}
else {
    Write-Ok "No se toca la carpeta de logs local: $LogsRoot"
}

Write-Step "2) Limpiar temporales y generados locales del proyecto"
$localGenerated = @(
    (Join-Path $ProjectRoot "subscriptions.runset.yaml"),
    (Join-Path $ProjectRoot "subscriptions.runset.filtered.yaml"),
    (Join-Path $ProjectRoot ".recent-items-state.pending.json"),
    (Join-Path $ProjectRoot ".recent-items-state.pending.filtered.json")
)

foreach ($file in $localGenerated) {
    if (Test-Path -LiteralPath $file) {
        Remove-Item -LiteralPath $file -Force -ErrorAction SilentlyContinue
    }
}
Write-Ok "Temporales y generados locales limpiados"

Write-Step "3) Limpiar state local del proyecto"
$stateFile = Join-Path $ProjectRoot ".recent-items-state.json"
if (Test-Path -LiteralPath $stateFile) {
    Write-Warn "No se pudo filtrar $stateFile; se recreará vacío"
}
Reset-StateFile -Path $stateFile
Write-Ok "State local limpiado"

Write-Step "4) Limpiar descargas reales, temporales y locks en ytdl-sub"
$quotedRootsYtdl = ($DownloadRoots | ForEach-Object { '"' + $_ + '"' }) -join " "

$ytdlScript = @"
#!/bin/sh
set -eu

for target in $quotedRootsYtdl
do
  if [ -d "`$target" ]; then
    echo "[INFO] Vaciando contenido de `$target"
    find "`$target" -mindepth 1 -delete
  fi
done

rm -rf /tmp/ytdl-sub-working-directory/* 2>/dev/null || true
rm -rf /config/.ytdl-sub-working-directory/* 2>/dev/null || true
rm -rf /config/.ytdl-sub-lock 2>/dev/null || true
rm -f /config/subscriptions.runset.yaml 2>/dev/null || true
rm -f /config/subscriptions.runset.filtered.yaml 2>/dev/null || true
rm -f /config/.recent-items-state.pending.json 2>/dev/null || true
rm -f /config/.recent-items-state.pending.filtered.json 2>/dev/null || true
"@

Invoke-DockerScript -Container "ytdl-sub" -ScriptContent $ytdlScript -RemoteName "clean-ytdl-sub.sh"
Write-Ok "Limpieza en ytdl-sub completada"

Write-Step "5) Limpiar entorno en beets-streaming2"
$quotedRootsBeets = ($DownloadRoots | ForEach-Object { '"' + $_ + '"' }) -join " "

$beetsScript = @"
#!/bin/sh
set -eu

for target in $quotedRootsBeets
do
  if [ -d "`$target" ]; then
    echo "[INFO] Vaciando contenido de `$target"
    find "`$target" -mindepth 1 -delete
  fi
done

rm -rf /tmp/ytdl-sub-working-directory/* 2>/dev/null || true
rm -rf /config/.ytdl-sub-working-directory/* 2>/dev/null || true
rm -rf /config/.ytdl-sub-lock 2>/dev/null || true
rm -f /config/logs/beets-import.log 2>/dev/null || true
rm -f /config/musiclibrary.db 2>/dev/null || true

if [ -f /config/library.db ]; then
  echo "[INFO] Conservando /config/library.db"
fi
"@

Invoke-DockerScript -Container "beets-streaming2" -ScriptContent $beetsScript -RemoteName "clean-beets.sh"
Write-Ok "Limpieza en beets-streaming2 completada"

Write-Step "6) Reiniciar contenedores"
docker restart ytdl-sub beets-streaming2
if ($LASTEXITCODE -ne 0) {
    throw "No se pudieron reiniciar los contenedores"
}
Write-Ok "Contenedores reiniciados correctamente"

Write-Step "7) Estado final rapido"

$quotedRootsState = ($DownloadRoots | ForEach-Object { '"' + $_ + '"' }) -join " "

$stateYtdl = @"
#!/bin/sh
set -eu
echo "[YTdl-sub /downloads seleccionados]"
for target in $quotedRootsState
do
  echo "--- `$target"
  if [ -d "`$target" ]; then
    find "`$target" -maxdepth 0 -print
    count=`$(find "`$target" -type f | wc -l | tr -d ' ')
    echo "[COUNT] `$target => `$count ficheros"
  else
    echo "[INFO] No existe `$target"
  fi
done
echo ""
echo "[YTdl-sub /config/logs]"
find /config/logs -maxdepth 0 -print 2>/dev/null || true
"@

Invoke-DockerScript -Container "ytdl-sub" -ScriptContent $stateYtdl -RemoteName "state-ytdl.sh"

$stateBeets = @"
#!/bin/sh
set -eu
echo "[beets /downloads seleccionados]"
for target in $quotedRootsState
do
  echo "--- `$target"
  if [ -d "`$target" ]; then
    find "`$target" -maxdepth 0 -print
    count=`$(find "`$target" -type f | wc -l | tr -d ' ')
    echo "[COUNT] `$target => `$count ficheros"
  else
    echo "[INFO] No existe `$target"
  fi
done
echo ""
echo "[beets /config/logs]"
find /config/logs -maxdepth 0 -print 2>/dev/null || true
"@

Invoke-DockerScript -Container "beets-streaming2" -ScriptContent $stateBeets -RemoteName "state-beets.sh"

Write-Host ""
Write-Ok "Entorno limpio."
Write-Host "Scope aplicado: $scopeLabel"
Write-Host "CleanLogs: $($CleanLogs.IsPresent)"
Write-Host ""
