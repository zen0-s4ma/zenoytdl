Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

Set-Location "E:\Docker_folders\streaming2\ytdl-sub\config\zenoytdl"

function Invoke-DockerShScript {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Container,

    [Parameter(Mandatory = $true)]
    [string]$Script
  )

  $tempName = "oai-script-" + [System.Guid]::NewGuid().ToString("N") + ".sh"
  $localTemp = Join-Path $env:TEMP $tempName
  $containerTemp = "/tmp/$tempName"

  try {
    $normalized = $Script -replace "`r`n", "`n"
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($localTemp, $normalized, $utf8NoBom)

    & docker cp $localTemp "${Container}:$containerTemp"
    if ($LASTEXITCODE -ne 0) {
      throw "Fallo docker cp hacia '$Container' ($containerTemp)."
    }

    & docker exec $Container sh $containerTemp
    if ($LASTEXITCODE -ne 0) {
      throw "Fallo la ejecucion del script shell en el contenedor '$Container' (exit code $LASTEXITCODE)."
    }
  }
  finally {
    & docker exec $Container sh -lc "rm -f '$containerTemp'" *> $null
    if (Test-Path $localTemp) {
      Remove-Item $localTemp -Force -ErrorAction SilentlyContinue
    }
  }
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor DarkCyan
Write-Host "1) PREPARAR CONTEXTO SIN BORRAR DESCARGAS EXISTENTES" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor DarkCyan

$prepScript = @'
set -e
echo "[INFO] No se borran directorios de salida ya descargados"
echo "[INFO] Se limpian procesos previos, locks, working_directory y auxiliares temporales"

pkill -f ytdl-sub 2>/dev/null || true
sleep 2

find /tmp -maxdepth 1 -type f \( -name "ytdl-sub*.lock" -o -name "*.lock" \) -print -delete 2>/dev/null || true
rm -rf /tmp/ytdl-sub-working-directory/* 2>/dev/null || true
rm -f /tmp/trim-ambience-video.py /tmp/trim-ambience-media.py 2>/dev/null || true

echo
echo "[STATE] Directorios actuales"
for d in \
  /downloads/Canales-youtube/ramon-alvarez-de-mon \
  /downloads/Podcast/entrevistas \
  /downloads/TV-Serie/lolete \
  /downloads/Music-Playlist/music-playlist-prueba \
  /downloads/Ambience-Video/ambience-video-prueba \
  /downloads/Ambience-Audio/ambience-audio-prueba
do
  if [ -e "$d" ]; then
    echo "[EXISTE] $d"
  else
    echo "[NO-EXISTE] $d"
  fi
done
'@
Invoke-DockerShScript -Container "ytdl-sub" -Script $prepScript

Write-Host ""
Write-Host "============================================================" -ForegroundColor DarkCyan
Write-Host "2) REGENERAR YAML DESDE CUSTOM" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor DarkCyan

& python .\generate-ytdl-config.py
if ($LASTEXITCODE -ne 0) {
  throw "Fallo generate-ytdl-config.py"
}

& python .\prepare-subscriptions-runset.py
if ($LASTEXITCODE -ne 0) {
  throw "Fallo prepare-subscriptions-runset.py"
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor DarkCyan
Write-Host "3) COPIAR SCRIPT DE TRIM AL CONTENEDOR" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor DarkCyan

& docker cp .\trim-ambience-video.py ytdl-sub:/tmp/trim-ambience-video.py
if ($LASTEXITCODE -ne 0) {
  throw "Fallo docker cp de trim-ambience-video.py"
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor DarkCyan
Write-Host "4) EJECUCION REAL COMPLETA YTDL-SUB" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor DarkCyan

$runsetPath = Join-Path (Get-Location) "subscriptions.runset.yaml"
if (-not (Test-Path $runsetPath)) {
  throw "No existe subscriptions.runset.yaml"
}

$runsetInfo = Get-Item $runsetPath
if ($runsetInfo.Length -le 5) {
  Write-Host "[INFO] subscriptions.runset.yaml esta vacio: no toca descargar nada en esta ejecucion." -ForegroundColor Yellow
} else {
  & docker exec ytdl-sub sh -lc 'ytdl-sub --config /config/zenoytdl/config.generated.yaml sub /config/zenoytdl/subscriptions.runset.yaml'
  if ($LASTEXITCODE -ne 0) {
    throw "Fallo la ejecucion real de ytdl-sub"
  }
}

if (Test-Path '.\.recent-items-state.pending.json') {
  Move-Item '.\.recent-items-state.pending.json' '.\.recent-items-state.json' -Force
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor DarkCyan
Write-Host "5) POSTPROCESO MUSIC-PLAYLIST (LIMPIEZA + BEETS)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor DarkCyan

if (Test-Path ".\clean-music-filenames.ps1") {
  & powershell.exe -ExecutionPolicy Bypass -File ".\clean-music-filenames.ps1" -TargetDir "E:\Docker_folders\ydtl-custom-downloads\Music-Playlist\music-playlist-prueba"
  if ($LASTEXITCODE -ne 0) {
    throw "Fallo clean-music-filenames.ps1"
  }
} else {
  Write-Host "[WARN] No existe .\clean-music-filenames.ps1; se omite limpieza previa de nombres." -ForegroundColor Yellow
}

$beetsScript = @'
set -e
if [ -d /downloads/Music-Playlist/music-playlist-prueba ]; then
  beet -v -c /config/zenoytdl/beets.music-playlist.yaml import -s -q /downloads/Music-Playlist/music-playlist-prueba
else
  echo "[WARN] No existe /downloads/Music-Playlist/music-playlist-prueba"
fi
'@
Invoke-DockerShScript -Container "beets-streaming2" -Script $beetsScript

Write-Host ""
Write-Host "============================================================" -ForegroundColor DarkCyan
Write-Host "6) POSTPROCESO AMBIENCE-VIDEO" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor DarkCyan

$trimVideoScript = @'
set -e
if [ -d /downloads/Ambience-Video/ambience-video-prueba ]; then
  find /downloads/Ambience-Video/ambience-video-prueba -maxdepth 1 -type f \
    \( -iname "*.mp4" -o -iname "*.mkv" -o -iname "*.webm" -o -iname "*.mov" -o -iname "*.m4v" -o -iname "*.avi" \) \
    -exec sh -c '
      f="$1"
      echo "[TRIM-VIDEO] $f"
      python /tmp/trim-ambience-video.py --input "$f" --max-duration 03:03:03 --replace --skip-output-probe
    ' sh {} \;
else
  echo "[WARN] No existe /downloads/Ambience-Video/ambience-video-prueba"
fi
'@
Invoke-DockerShScript -Container "ytdl-sub" -Script $trimVideoScript

Write-Host ""
Write-Host "============================================================" -ForegroundColor DarkCyan
Write-Host "7) POSTPROCESO AMBIENCE-AUDIO" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor DarkCyan

$trimAudioScript = @'
set -e
if [ -d /downloads/Ambience-Audio/ambience-audio-prueba ]; then
  find /downloads/Ambience-Audio/ambience-audio-prueba -maxdepth 1 -type f \
    \( -iname "*.mp3" -o -iname "*.m4a" -o -iname "*.aac" -o -iname "*.opus" -o -iname "*.ogg" -o -iname "*.wav" -o -iname "*.flac" \) \
    -exec sh -c '
      f="$1"
      echo "[TRIM-AUDIO] $f"
      python /tmp/trim-ambience-video.py --input "$f" --max-duration 03:03:03 --replace --skip-output-probe
    ' sh {} \;
else
  echo "[WARN] No existe /downloads/Ambience-Audio/ambience-audio-prueba"
fi
'@
Invoke-DockerShScript -Container "ytdl-sub" -Script $trimAudioScript

Write-Host ""
Write-Host "============================================================" -ForegroundColor DarkCyan
Write-Host "8) ESTADO FINAL DE SALIDA REAL" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor DarkCyan

$treeScript = @'
set -e
echo
echo "[TREE] /downloads/Canales-youtube/ramon-alvarez-de-mon"
find /downloads/Canales-youtube/ramon-alvarez-de-mon -maxdepth 3 \( -type d -o -type f \) | sort || true

echo
echo "[TREE] /downloads/Podcast/entrevistas"
find /downloads/Podcast/entrevistas -maxdepth 3 \( -type d -o -type f \) | sort || true

echo
echo "[TREE] /downloads/TV-Serie/lolete"
find /downloads/TV-Serie/lolete -maxdepth 3 \( -type d -o -type f \) | sort || true

echo
echo "[TREE] /downloads/Music-Playlist/music-playlist-prueba"
find /downloads/Music-Playlist/music-playlist-prueba -maxdepth 2 \( -type d -o -type f \) | sort || true

echo
echo "[TREE] /downloads/Ambience-Video/ambience-video-prueba"
find /downloads/Ambience-Video/ambience-video-prueba -maxdepth 2 \( -type d -o -type f \) | sort || true

echo
echo "[TREE] /downloads/Ambience-Audio/ambience-audio-prueba"
find /downloads/Ambience-Audio/ambience-audio-prueba -maxdepth 2 \( -type d -o -type f \) | sort || true
'@
Invoke-DockerShScript -Container "ytdl-sub" -Script $treeScript
