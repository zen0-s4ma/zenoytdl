Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. "$PSScriptRoot\_shared.ps1"

param(
    [Parameter(Position = 0)]
    [bool]$DryRun = $false
)

$ctx = New-TestExecutionContext -TestName 'test-trim-only'
Start-TestLogging -Context $ctx

try {
    Write-TestSection -Context $ctx -Title 'Inicio test aislado de trim'
    Write-TestLine -Context $ctx -Message "DryRun: $DryRun"

    $projectRoot = Get-ProjectRoot
    $containerTestDir = '/downloads/__test_trim_only'
    $containerInput = "$containerTestDir/input-trim-test.mp4"
    $trimSeconds = 5

    Write-TestSection -Context $ctx -Title 'Limpieza previa del entorno de prueba'
    $cleanupScript = @"
set -e
rm -rf '$containerTestDir'
mkdir -p '$containerTestDir'
rm -f /tmp/trim-ambience-video.py /tmp/trim-ambience-media.py 2>/dev/null || true
"@
    Invoke-DockerShellScript -Context $ctx -Container 'ytdl-sub' -Script $cleanupScript -Label 'trim-cleanup'

    Write-TestSection -Context $ctx -Title 'Generación de vídeo sintético rápido'
    $generateScript = @"
set -e
ffmpeg -y \
  -f lavfi -i testsrc=size=640x360:rate=25 \
  -f lavfi -i sine=frequency=1000:sample_rate=48000 \
  -t 12 \
  -c:v libx264 \
  -pix_fmt yuv420p \
  -c:a aac \
  -b:a 128k \
  '$containerInput'
echo '[INPUT-CREATED]'
ls -lh '$containerInput'
echo '[INPUT-PROBE]'
ffprobe -v error -show_entries format=duration,size -of default=noprint_wrappers=1 '$containerInput'
ffprobe -v error -show_entries stream=codec_type,codec_name,width,height,sample_rate,channels -of default=noprint_wrappers=1 '$containerInput'
"@
    Invoke-DockerShellScript -Context $ctx -Container 'ytdl-sub' -Script $generateScript -Label 'trim-generate-input'

    Write-TestSection -Context $ctx -Title 'Copiar script real de trim al contenedor'
    Copy-TrimScriptToContainer -Context $ctx

    if ($DryRun) {
        Write-TestSection -Context $ctx -Title 'Dry-run: no se ejecuta el recorte real'
        Write-TestLine -Context $ctx -Message 'Se ha generado el fichero de prueba y se ha validado el input, pero no se lanza el trim.' -Level 'OK'
    }
    else {
        Write-TestSection -Context $ctx -Title 'Ejecución real del trim'
        $trimScript = @"
set -e
python /tmp/trim-ambience-video.py --input '$containerInput' --max-duration 00:00:05 --replace --skip-output-probe
echo '[AFTER-TRIM]'
ls -lh '$containerInput'
echo '[AFTER-TRIM-PROBE]'
ffprobe -v error -show_entries format=duration,size -of default=noprint_wrappers=1 '$containerInput'
ffprobe -v error -show_entries stream=codec_type,codec_name,width,height,sample_rate,channels -of default=noprint_wrappers=1 '$containerInput'

dur=\$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 '$containerInput' | head -n 1)
python - << 'PY'
import sys
dur = float(sys.argv[1])
limit = 5.6
if dur <= limit:
    print(f"[OK] Duracion tras trim valida: {dur:.3f}s <= {limit}s")
    sys.exit(0)
print(f"[ERROR] Duracion tras trim no valida: {dur:.3f}s > {limit}s")
sys.exit(1)
PY "\$dur"
"@
        Invoke-DockerShellScript -Context $ctx -Container 'ytdl-sub' -Script $trimScript -Label 'trim-execution'
    }

    Write-TestSection -Context $ctx -Title 'Listado final del directorio de prueba'
    $finalScript = @"
set -e
echo '[FINAL-TREE]'
find '$containerTestDir' -maxdepth 2 \( -type d -o -type f \) | sort
"@
    Invoke-DockerShellScript -Context $ctx -Container 'ytdl-sub' -Script $finalScript -Label 'trim-final-tree' -AllowFailure

    Collect-RelevantContainerLogs -Context $ctx

    Write-TestSection -Context $ctx -Title 'Fin test aislado de trim'
    Write-TestLine -Context $ctx -Message 'Test de trim completado correctamente.' -Level 'OK'
}
finally {
    Write-RelevantLogPaths -Context $ctx
    Stop-TestLogging
}