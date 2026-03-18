Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. "$PSScriptRoot\_shared.ps1"

param(
    [Parameter(Position = 0)]
    [bool]$DryRun = $false
)

$ctx = New-TestExecutionContext -TestName 'validate-downloads'
Start-TestLogging -Context $ctx

try {
    Write-TestSection -Context $ctx -Title 'Inicio validador global de descargas'
    Write-TestLine -Context $ctx -Message "DryRun: $DryRun"
    Write-TestLine -Context $ctx -Message 'Este validador no modifica nada; dry-run solo se registra a nivel informativo.'

    $projectRoot = Get-ProjectRoot
    Push-Location $projectRoot
    try {
        Write-TestSection -Context $ctx -Title 'Revisión de ficheros de control del proyecto'
        foreach ($file in @('profiles-custom.yml','subscription-custom.yml','config.generated.yaml','subscriptions.generated.yaml','subscriptions.runset.yaml','subscriptions.runset.filtered.yaml','.recent-items-state.json','.recent-items-state.pending.json','.recent-items-state.pending.filtered.json','beets.music-playlist.yaml')) {
            $path = Join-Path $projectRoot $file
            if (Test-Path $path) {
                Get-Item $path | Format-Table Name,Length,LastWriteTime -AutoSize | Out-String | Tee-Object -FilePath $ctx.MainLog -Append | Out-Null
            } else {
                Write-TestLine -Context $ctx -Message "No existe: $path" -Level 'WARN'
            }
        }
    }
    finally {
        Pop-Location
    }

    $defs = Get-ProfileDefinitions
    $allPaths = foreach ($profile in Get-AllProfileNames) {
        Get-ProfileOutputPaths -ProfileName $profile
    }

    foreach ($profile in Get-AllProfileNames) {
        Write-TestSection -Context $ctx -Title ("Inventario completo de rutas para perfil: $profile")
        $items = $allPaths | Where-Object { $_.ProfileName -eq $profile }
        foreach ($item in $items) {
            $script = @"
set -e
printf '[PATH]\n$item.OutputPath\n'
if [ -d '$($item.OutputPath)' ]; then
  echo '[TREE]'
  find '$($item.OutputPath)' -maxdepth 4 \( -type d -o -type f \) | sort
else
  echo '[NO-EXISTE]'
fi
"@
            Invoke-DockerShellScript -Context $ctx -Container 'ytdl-sub' -Script $script -Label ('tree-' + $item.SubscriptionRoot) -AllowFailure
        }
    }

    Write-TestSection -Context $ctx -Title 'Conteos amplios por ruta y extensiones relevantes'
    foreach ($profile in Get-AllProfileNames) {
        $def = $defs[$profile]
        foreach ($item in ($allPaths | Where-Object { $_.ProfileName -eq $profile })) {
            $findParts = ($def.Extensions | ForEach-Object { "-iname '*$_'" }) -join ' -o '
            $script = @"
set -e
if [ -d '$($item.OutputPath)' ]; then
  echo '[COUNT-FILES]'
  find '$($item.OutputPath)' -type f \( $findParts \) | wc -l
  echo '[FILES]'
  find '$($item.OutputPath)' -type f \( $findParts \) | sort
else
  echo 0
fi
"@
            Invoke-DockerShellScript -Context $ctx -Container 'ytdl-sub' -Script $script -Label ('count-' + $item.SubscriptionRoot) -AllowFailure
        }
    }

    Write-TestSection -Context $ctx -Title 'Validación de media con ffprobe donde aplica'
    $probeScript = @'
set -e
probe_dir() {
  dir="$1"
  if [ -d "$dir" ]; then
    find "$dir" -maxdepth 1 -type f \( -iname "*.mp4" -o -iname "*.mkv" -o -iname "*.webm" -o -iname "*.mov" -o -iname "*.m4v" -o -iname "*.avi" -o -iname "*.mp3" -o -iname "*.m4a" -o -iname "*.aac" -o -iname "*.opus" -o -iname "*.ogg" -o -iname "*.wav" -o -iname "*.flac" \) | sort | while read -r f; do
      echo "------------------------------------------------------------"
      echo "$f"
      ls -lh "$f"
      ffprobe -v error -show_entries format=duration,size -of default=noprint_wrappers=1 "$f" || true
      ffprobe -v error -show_entries stream=codec_type,codec_name,width,height,sample_rate,channels -of default=noprint_wrappers=1 "$f" || true
    done
  fi
}
'@
    $pathsBash = ($allPaths | ForEach-Object { "probe_dir '$($_.OutputPath)'" }) -join "`n"
    Invoke-DockerShellScript -Context $ctx -Container 'ytdl-sub' -Script ($probeScript + "`n" + $pathsBash + "`n") -Label 'ffprobe-all' -AllowFailure

    Write-TestSection -Context $ctx -Title 'Revisión de logs y estado para detectar skips, purgas, descargas y postprocesados'
    Collect-RelevantContainerLogs -Context $ctx

    Write-TestSection -Context $ctx -Title 'Fin del validador'
    Write-TestLine -Context $ctx -Message 'Validación completada.' -Level 'OK'
}
finally {
    Write-RelevantLogPaths -Context $ctx
    Stop-TestLogging
}
