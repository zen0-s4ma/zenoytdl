param(
    [Parameter(Position = 0)]
    [string]$DryRun = 'false'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. "$PSScriptRoot\_shared.ps1"

function ConvertTo-BooleanStrict {
    param(
        [Parameter(Mandatory = $true)]
        [AllowNull()]
        [object]$Value
    )

    if ($Value -is [bool]) { return [bool]$Value }
    if ($null -eq $Value) { throw "DryRun no puede ser null." }

    switch ($Value.ToString().Trim().ToLowerInvariant()) {
        'true'  { return $true }
        'false' { return $false }
        '1'     { return $true }
        '0'     { return $false }
        default { throw "Valor no válido para DryRun: $Value" }
    }
}

$DryRunBool = ConvertTo-BooleanStrict -Value $DryRun

$ctx = New-TestExecutionContext -TestName 'test-beets-only'
Start-TestLogging -Context $ctx

try {
    Write-TestSection -Context $ctx -Title 'Inicio test aislado de beets'
    Write-TestLine -Context $ctx -Message "DryRun: $DryRunBool"

    $containerDir = '/downloads/Music-Playlist/__test_beets_only'
    $rawMp3 = "$containerDir/Nothing Else Matters - Metallica.raw.mp3"
    $cleanMp3 = "$containerDir/Nothing Else Matters - Metallica.mp3"

    Write-TestSection -Context $ctx -Title 'Limpieza previa del entorno beets'
    $cleanupScript = @"
set -e
rm -rf '$containerDir'
mkdir -p '$containerDir'
rm -f /config/musiclibrary.db /config/logs/beets-import.log 2>/dev/null || true
"@
    Invoke-DockerShellScript -Context $ctx -Container 'beets-streaming2' -Script $cleanupScript -Label 'beets-cleanup'

    Write-TestSection -Context $ctx -Title 'Generación de MP3 de prueba con metadata embebida sucia'
    $generateScript = @"
set -e
ffmpeg -hide_banner -loglevel error -y \
  -f lavfi -i sine=frequency=440:sample_rate=44100 \
  -t 12 \
  -q:a 2 \
  -metadata title='BASURA TITLE' \
  -metadata artist='BASURA ARTIST' \
  -metadata album='BASURA ALBUM' \
  -metadata genre='BASURA GENRE' \
  -metadata comment='BASURA COMMENT' \
  '$rawMp3'

echo '[RAW-MP3]'
ls -lh '$rawMp3'
echo '[RAW-METADATA]'
ffprobe -v error -show_entries format_tags -of default=noprint_wrappers=1 '$rawMp3' || true
"@
    Invoke-DockerShellScript -Context $ctx -Container 'beets-streaming2' -Script $generateScript -Label 'beets-generate-raw'

    Write-TestSection -Context $ctx -Title 'Limpieza total de metadata embebida y renombrado final realista'
    $cleanScript = @"
set -e
ffmpeg -hide_banner -loglevel error -y -i '$rawMp3' -map 0:a -map_metadata -1 -c:a libmp3lame -q:a 2 '$cleanMp3'
rm -f '$rawMp3'

echo '[CLEAN-MP3]'
ls -lh '$cleanMp3'
echo '[CLEAN-METADATA]'
ffprobe -v error -show_entries format_tags -of default=noprint_wrappers=1 '$cleanMp3' || true
"@
    Invoke-DockerShellScript -Context $ctx -Container 'beets-streaming2' -Script $cleanScript -Label 'beets-clean-metadata'

    Write-TestSection -Context $ctx -Title 'Validación de que la metadata previa ha sido eliminada'
    $preCheckScript = @'
set -e
probe=$(ffprobe -v error -show_entries format_tags -of default=noprint_wrappers=1 '/downloads/Music-Playlist/__test_beets_only/Nothing Else Matters - Metallica.mp3' || true)
echo "$probe"
if echo "$probe" | grep -Eiq 'BASURA TITLE|BASURA ARTIST|BASURA ALBUM|BASURA GENRE|BASURA COMMENT'; then
  echo '[ERROR] Sigue existiendo metadata sucia embebida'
  exit 1
fi
echo '[OK] No queda metadata sucia embebida'
'@
    Invoke-DockerShellScript -Context $ctx -Container 'beets-streaming2' -Script $preCheckScript -Label 'beets-precheck-clean'

    if ($DryRunBool) {
        Write-TestSection -Context $ctx -Title 'Dry-run: no se ejecuta la fase real de beets'
        Write-TestLine -Context $ctx -Message 'Se ha generado el MP3, se ha limpiado la metadata embebida y se ha validado la limpieza, pero no se lanza beets real.' -Level 'OK'
    }
    else {
        Write-TestSection -Context $ctx -Title 'Import real, modificación y escritura con beets'
        $importScript = @'
set -e

TARGET='/downloads/Music-Playlist/__test_beets_only/Nothing Else Matters - Metallica.mp3'
CFG='/config/zenoytdl/beets.music-playlist.yaml'

# 1) Importar AS-IS para meterlo sí o sí en librería
beet -v -c "$CFG" import -A -s -q "$TARGET"

# 2) Verificar que existe en librería
echo '[BEET-LIST-BEFORE]'
beet -c "$CFG" list path:"$TARGET"

# 3) Modificar metadatos de la DB y escribir tags, sin interacción
beet -c "$CFG" modify -y -w path:"$TARGET" title="Nothing Else Matters" artist="Metallica" album="Metallica" year="1991"

# 4) Forzar escritura desde DB a fichero (y disparar scrub si aplica)
beet -c "$CFG" write -f path:"$TARGET"

echo '[BEETS-DB]'
ls -lh /config/musiclibrary.db 2>/dev/null || true
ls -lh /config/library.db 2>/dev/null || true

echo '[BEETS-LOG-TAIL]'
tail -n 200 /config/logs/beets-import.log 2>/dev/null || true

echo '[BEET-LIST-AFTER]'
beet -c "$CFG" list -f '$artist - $title - $album - $year' path:"$TARGET"

echo '[POST-BEETS-METADATA]'
ffprobe -v error -show_entries format_tags -of default=noprint_wrappers=1 "$TARGET" || true

probe=$(ffprobe -v error -show_entries format_tags -of default=noprint_wrappers=1 "$TARGET" || true)

if [ -z "$probe" ]; then
  echo '[ERROR] No hay metadata tras beets'
  exit 1
fi

if ! echo "$probe" | grep -Eiq 'TAG:title=Nothing Else Matters|title=Nothing Else Matters'; then
  echo '[ERROR] No se detecta title correcto tras beets'
  exit 1
fi

if ! echo "$probe" | grep -Eiq 'TAG:artist=Metallica|artist=Metallica'; then
  echo '[ERROR] No se detecta artist correcto tras beets'
  exit 1
fi

if ! echo "$probe" | grep -Eiq 'TAG:album=Metallica|album=Metallica'; then
  echo '[ERROR] No se detecta album correcto tras beets'
  exit 1
fi

if echo "$probe" | grep -Eiq 'BASURA TITLE|BASURA ARTIST|BASURA ALBUM|BASURA GENRE|BASURA COMMENT'; then
  echo '[ERROR] Persisten restos de metadata sucia tras beets'
  exit 1
fi

echo '[OK] Beets ha escrito metadata embebida válida en el MP3 de prueba'
'@
        Invoke-DockerShellScript -Context $ctx -Container 'beets-streaming2' -Script $importScript -Label 'beets-import-real'
    }

    Write-TestSection -Context $ctx -Title 'Inventario final de la carpeta de prueba'
    $finalScript = @"
set -e
echo '[FINAL-TREE]'
find '$containerDir' -maxdepth 2 \( -type d -o -type f \) | sort
"@
    Invoke-DockerShellScript -Context $ctx -Container 'beets-streaming2' -Script $finalScript -Label 'beets-final-tree' -AllowFailure

    Write-TestSection -Context $ctx -Title 'Captura final de logs relevantes'
    $beetsLogScript = @'
set -e
echo '[BEETS-LOG]'
if [ -f /config/logs/beets-import.log ]; then
  tail -n 250 /config/logs/beets-import.log
else
  echo '[WARN] No existe /config/logs/beets-import.log'
fi
echo
echo '[LIBRARIES]'
ls -lh /config/musiclibrary.db 2>/dev/null || true
ls -lh /config/library.db 2>/dev/null || true
'@
    Invoke-DockerShellScript -Context $ctx -Container 'beets-streaming2' -Script $beetsLogScript -Label 'beets-log-capture' -AllowFailure

    Write-TestSection -Context $ctx -Title 'Fin test aislado de beets'
    Write-TestLine -Context $ctx -Message 'Test de beets completado correctamente.' -Level 'OK'
}
finally {
    Write-RelevantLogPaths -Context $ctx
    Stop-TestLogging
}