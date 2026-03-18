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

  $localTmp = Join-Path $env:TEMP ("oai-script-" + [guid]::NewGuid().ToString("N") + ".sh")
  $containerTmp = "/tmp/" + [System.IO.Path]::GetFileName($localTmp)

  try {
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    $normalized = $Script -replace "`r`n", "`n"
    [System.IO.File]::WriteAllText($localTmp, $normalized, $utf8NoBom)

    docker cp $localTmp "${Container}:${containerTmp}"
    if ($LASTEXITCODE -ne 0) {
      throw "Falló docker cp hacia '$Container'"
    }

    docker exec $Container sh $containerTmp
    if ($LASTEXITCODE -ne 0) {
      throw "Fallo la ejecucion del script shell en el contenedor '$Container' (exit code $LASTEXITCODE)."
    }
  }
  finally {
    try {
      docker exec $Container sh -c "rm -f '$containerTmp'" *> $null
    } catch {}
    if (Test-Path $localTmp) {
      Remove-Item $localTmp -Force -ErrorAction SilentlyContinue
    }
  }
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor DarkCyan
Write-Host "1) COMPROBACION DE YAML GENERADOS" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor DarkCyan

Get-Item .\config.generated.yaml, .\subscriptions.generated.yaml | Format-Table Name,Length,LastWriteTime -AutoSize
Write-Host ""
Write-Host "--- config.generated.yaml (cabecera) ---" -ForegroundColor Gray
Get-Content .\config.generated.yaml -TotalCount 120
Write-Host ""
Write-Host "--- subscriptions.generated.yaml (completo) ---" -ForegroundColor Gray
Get-Content .\subscriptions.generated.yaml

Write-Host ""
Write-Host "============================================================" -ForegroundColor DarkCyan
Write-Host "2) ARBOLES Y FICHEROS FINALES GENERADOS" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor DarkCyan

$treeScript = @'
set -e

echo
echo "[CANALES-YOUTUBE]"
find /downloads/Canales-youtube/ramon-alvarez-de-mon -maxdepth 3 \( -type d -o -type f \) | sort || true

echo
echo "[PODCAST]"
find /downloads/Podcast/entrevistas -maxdepth 3 \( -type d -o -type f \) | sort || true

echo
echo "[TV-SERIE]"
find /downloads/TV-Serie/lolete -maxdepth 3 \( -type d -o -type f \) | sort || true

echo
echo "[MUSIC-PLAYLIST]"
find /downloads/Music-Playlist/music-playlist-prueba -maxdepth 2 \( -type d -o -type f \) | sort || true

echo
echo "[AMBIENCE-VIDEO]"
find /downloads/Ambience-Video/ambience-video-prueba -maxdepth 2 \( -type d -o -type f \) | sort || true

echo
echo "[AMBIENCE-AUDIO]"
find /downloads/Ambience-Audio/ambience-audio-prueba -maxdepth 2 \( -type d -o -type f \) | sort || true
'@
Invoke-DockerShScript -Container "ytdl-sub" -Script $treeScript

Write-Host ""
Write-Host "============================================================" -ForegroundColor DarkCyan
Write-Host "3) RECUENTO DE FICHEROS CLAVE POR PERFIL" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor DarkCyan

$countScript = @'
set -e

echo "[COUNT] Canales-youtube videos:"
find /downloads/Canales-youtube/ramon-alvarez-de-mon -type f \( -iname "*.mp4" -o -iname "*.mkv" -o -iname "*.webm" \) | wc -l

echo "[COUNT] Podcast mp3:"
find /downloads/Podcast/entrevistas -type f -iname "*.mp3" | wc -l

echo "[COUNT] TV-Serie episodios video:"
find /downloads/TV-Serie/lolete -type f \( -iname "*.mp4" -o -iname "*.mkv" -o -iname "*.webm" \) | wc -l

echo "[COUNT] TV-Serie nfo:"
find /downloads/TV-Serie/lolete -type f -iname "*.nfo" | wc -l

echo "[COUNT] Music-Playlist mp3:"
find /downloads/Music-Playlist/music-playlist-prueba -type f -iname "*.mp3" | wc -l

echo "[COUNT] Ambience-Video media:"
find /downloads/Ambience-Video/ambience-video-prueba -maxdepth 1 -type f \( -iname "*.mp4" -o -iname "*.mkv" -o -iname "*.webm" \) | wc -l

echo "[COUNT] Ambience-Audio mp3:"
find /downloads/Ambience-Audio/ambience-audio-prueba -maxdepth 1 -type f -iname "*.mp3" | wc -l
'@
Invoke-DockerShScript -Container "ytdl-sub" -Script $countScript

Write-Host ""
Write-Host "============================================================" -ForegroundColor DarkCyan
Write-Host "4) VALIDACION DETALLADA DE AMBIENCE-VIDEO Y AMBIENCE-AUDIO" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor DarkCyan

$probeScript = @'
set -e

echo
echo "[AMBIENCE-VIDEO] Duracion, tamano y streams"
find /downloads/Ambience-Video/ambience-video-prueba -maxdepth 1 -type f \
  \( -iname "*.mp4" -o -iname "*.mkv" -o -iname "*.webm" -o -iname "*.mov" -o -iname "*.m4v" -o -iname "*.avi" \) \
  -exec sh -c '
    f="$1"
    echo "------------------------------------------------------------"
    echo "$f"
    ls -lh "$f"
    ffprobe -v error -show_entries format=duration,size -of default=noprint_wrappers=1 "$f"
    echo "[VIDEO STREAM]"
    ffprobe -v error -select_streams v:0 -show_entries stream=codec_name,width,height -of default=noprint_wrappers=1 "$f"
    echo "[AUDIO STREAM]"
    ffprobe -v error -select_streams a:0 -show_entries stream=codec_name,sample_rate,channels -of default=noprint_wrappers=1 "$f"
  ' sh {} \;

echo
echo "[AMBIENCE-AUDIO] Duracion, tamano y stream"
find /downloads/Ambience-Audio/ambience-audio-prueba -maxdepth 1 -type f \
  \( -iname "*.mp3" -o -iname "*.m4a" -o -iname "*.aac" -o -iname "*.opus" -o -iname "*.ogg" -o -iname "*.wav" -o -iname "*.flac" \) \
  -exec sh -c '
    f="$1"
    echo "------------------------------------------------------------"
    echo "$f"
    ls -lh "$f"
    ffprobe -v error -show_entries format=duration,size -of default=noprint_wrappers=1 "$f"
    echo "[AUDIO STREAM]"
    ffprobe -v error -select_streams a:0 -show_entries stream=codec_name,sample_rate,channels -of default=noprint_wrappers=1 "$f"
  ' sh {} \;
'@
Invoke-DockerShScript -Container "ytdl-sub" -Script $probeScript

Write-Host ""
Write-Host "============================================================" -ForegroundColor DarkCyan
Write-Host "5) COMPROBAR QUE EL RECORTE FINAL QUEDO EN 10983s Y SIN RESIDUOS" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor DarkCyan

$trimCheckScript = @'
set -e

echo "[CHECK] Duraciones ambience-video"
find /downloads/Ambience-Video/ambience-video-prueba -maxdepth 1 -type f \
  \( -iname "*.mp4" -o -iname "*.mkv" -o -iname "*.webm" -o -iname "*.mov" -o -iname "*.m4v" -o -iname "*.avi" \) \
  -exec sh -c '
    f="$1"
    dur="$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$f")"
    printf "%s -> %s s\n" "$f" "$dur"
  ' sh {} \;

echo
echo "[CHECK] Duraciones ambience-audio"
find /downloads/Ambience-Audio/ambience-audio-prueba -maxdepth 1 -type f \
  \( -iname "*.mp3" -o -iname "*.m4a" -o -iname "*.aac" -o -iname "*.opus" -o -iname "*.ogg" -o -iname "*.wav" -o -iname "*.flac" \) \
  -exec sh -c '
    f="$1"
    dur="$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$f")"
    printf "%s -> %s s\n" "$f" "$dur"
  ' sh {} \;

echo
echo "[CHECK] Restos temporales/residuales"
find /downloads/Ambience-Video/ambience-video-prueba /downloads/Ambience-Audio/ambience-audio-prueba \
  -type f \( -name "*.bak" -o -name "*.tmp" -o -name "*.part" -o -name "*.trimmed" \) -print || true
'@
Invoke-DockerShScript -Container "ytdl-sub" -Script $trimCheckScript

Write-Host ""
Write-Host "============================================================" -ForegroundColor DarkCyan
Write-Host "6) VALIDACION MP3 DONDE APLICA" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor DarkCyan

$mp3CheckScript = @'
set -e

echo "[PODCAST MP3]"
find /downloads/Podcast/entrevistas -type f -iname "*.mp3" \
  -exec sh -c '
    f="$1"
    echo "------------------------------------------------------------"
    echo "$f"
    ffprobe -v error -select_streams a:0 -show_entries stream=codec_name,sample_rate,channels -of default=noprint_wrappers=1 "$f"
  ' sh {} \;

echo
echo "[MUSIC-PLAYLIST MP3]"
find /downloads/Music-Playlist/music-playlist-prueba -type f -iname "*.mp3" \
  -exec sh -c '
    f="$1"
    echo "------------------------------------------------------------"
    echo "$f"
    ffprobe -v error -select_streams a:0 -show_entries stream=codec_name,sample_rate,channels -of default=noprint_wrappers=1 "$f"
  ' sh {} \;
'@
Invoke-DockerShScript -Container "ytdl-sub" -Script $mp3CheckScript

Write-Host ""
Write-Host "============================================================" -ForegroundColor DarkCyan
Write-Host "7) REVISION DE LOGS RELEVANTES" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor DarkCyan

$logsScript = @'
set -e

echo
echo "[LISTADO LOGS]"
ls -lah /config/logs || true

echo
echo "[ULTIMOS 200 - ytdl-sub logs]"
find /config/logs -maxdepth 1 -type f | sort | tail -n 10 | while read -r f; do
  echo "------------------------------------------------------------"
  echo "$f"
  tail -n 200 "$f" || true
done

echo
echo "[BEETS LOG EN ytdl-sub]"
if [ -f /config/logs/beets-import.log ]; then
  tail -n 200 /config/logs/beets-import.log
else
  echo "[INFO] No existe /config/logs/beets-import.log en ytdl-sub"
fi
'@
Invoke-DockerShScript -Container "ytdl-sub" -Script $logsScript

Write-Host ""
Write-Host "============================================================" -ForegroundColor DarkCyan
Write-Host "7B) REVISION DE LOG BEETS EN SU CONTENEDOR" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor DarkCyan

$beetsLogsScript = @'
set -e

echo "[BEETS LOG EN beets-streaming2]"
if [ -f /config/logs/beets-import.log ]; then
  tail -n 200 /config/logs/beets-import.log
else
  echo "[INFO] No existe /config/logs/beets-import.log en beets-streaming2"
fi
'@
Invoke-DockerShScript -Container "beets-streaming2" -Script $beetsLogsScript

Write-Host ""
Write-Host "============================================================" -ForegroundColor DarkCyan
Write-Host "8) COMPROBACION DE WORKDIR Y BASURA TEMPORAL" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor DarkCyan

$tmpScript = @'
set -e

echo "[TMP y working_directory]"
ls -lah /tmp || true

echo
echo "[RESTOS EN working_directory]"
find /tmp/ytdl-sub-working-directory -mindepth 1 -maxdepth 3 -print 2>/dev/null || true
'@
Invoke-DockerShScript -Container "ytdl-sub" -Script $tmpScript