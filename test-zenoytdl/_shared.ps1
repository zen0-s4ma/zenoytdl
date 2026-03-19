Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

function Get-TestRoot {
    return $PSScriptRoot
}

function Get-ProjectRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
}

function Get-LogsRoot {
    return Join-Path (Get-TestRoot) 'logs'
}

function Get-FilteredRunsetPath {
    return Join-Path (Get-ProjectRoot) 'subscriptions.runset.filtered.yaml'
}

function Get-FilteredPendingStatePath {
    return Join-Path (Get-ProjectRoot) '.recent-items-state.pending.filtered.json'
}

function Get-StateFilePath {
    return Join-Path (Get-ProjectRoot) '.recent-items-state.json'
}

function Test-FilteredRunsetHasEntries {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path $Path)) { return $false }

    $raw = (Get-Content -Path $Path -Raw -Encoding UTF8).Trim()
    if ([string]::IsNullOrWhiteSpace($raw)) { return $false }
    if ($raw -eq '{}') { return $false }
    if ($raw -eq '---') { return $false }
    if ($raw -eq 'null') { return $false }

    return $true
}

function New-TestExecutionContext {
    param([Parameter(Mandatory = $true)][string]$TestName)

    $timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $baseDir = Join-Path (Join-Path (Get-LogsRoot) $TestName) $timestamp
    $null = New-Item -ItemType Directory -Force -Path $baseDir

    [pscustomobject]@{
        TestName      = $TestName
        Timestamp     = $timestamp
        BaseDir       = $baseDir
        MainLog       = Join-Path $baseDir ($TestName + '.log')
        TranscriptLog = Join-Path $baseDir ($TestName + '.transcript.log')
        SummaryLog    = Join-Path $baseDir ($TestName + '.summary.log')
    }
}

function Start-TestLogging {
    param([Parameter(Mandatory = $true)]$Context)
    $null = New-Item -ItemType File -Force -Path $Context.MainLog
    Start-Transcript -Path $Context.TranscriptLog -Force | Out-Null
}

function Stop-TestLogging {
    try { Stop-Transcript | Out-Null } catch {}
}

function Write-TestLine {
    param(
        [Parameter(Mandatory = $true)]$Context,
        [Parameter(Mandatory = $true)][string]$Message,
        [ValidateSet('INFO','WARN','OK','STEP','ERROR')]
        [string]$Level = 'INFO'
    )
    $line = '[{0}] [{1}] {2}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Level, $Message
    $line | Tee-Object -FilePath $Context.MainLog -Append | Write-Host
}

function Write-TestSection {
    param(
        [Parameter(Mandatory = $true)]$Context,
        [Parameter(Mandatory = $true)][string]$Title
    )
    Write-TestLine -Context $Context -Message ('=' * 76) -Level 'STEP'
    Write-TestLine -Context $Context -Message $Title -Level 'STEP'
    Write-TestLine -Context $Context -Message ('=' * 76) -Level 'STEP'
}

function Invoke-LoggedExpression {
    param(
        [Parameter(Mandatory = $true)]$Context,
        [Parameter(Mandatory = $true)][string]$Expression,
        [Parameter(Mandatory = $true)][string]$Label,
        [switch]$AllowFailure
    )

    Write-TestLine -Context $Context -Message "Ejecutando [$Label]: $Expression" -Level 'INFO'

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = 'cmd.exe'
    $psi.Arguments = "/d /c $Expression"
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.StandardOutputEncoding = [System.Text.UTF8Encoding]::new($false)
    $psi.StandardErrorEncoding = [System.Text.UTF8Encoding]::new($false)

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $psi

    $null = $process.Start()

    $stdout = $process.StandardOutput.ReadToEnd()
    $stderr = $process.StandardError.ReadToEnd()

    $process.WaitForExit()
    $exitCode = $process.ExitCode

    $combined = @()
    if (-not [string]::IsNullOrWhiteSpace($stdout)) { $combined += $stdout.TrimEnd() }
    if (-not [string]::IsNullOrWhiteSpace($stderr)) { $combined += $stderr.TrimEnd() }

    if ($combined.Count -gt 0) {
        ($combined -join [Environment]::NewLine) |
            Tee-Object -FilePath $Context.MainLog -Append |
            Write-Host
    }

    if ($exitCode -ne 0 -and -not $AllowFailure) {
        Write-RelevantLogPaths -Context $Context
        throw "Fallo [$Label] con exit code $exitCode"
    }

    return $exitCode
}

function Invoke-DockerShellScript {
    param(
        [Parameter(Mandatory = $true)]$Context,
        [Parameter(Mandatory = $true)][string]$Container,
        [Parameter(Mandatory = $true)][string]$Script,
        [string]$Label = 'docker-shell',
        [switch]$AllowFailure
    )

    $tmpName = 'zenotest-' + [guid]::NewGuid().ToString('N') + '.sh'
    $localTmp = Join-Path $env:TEMP $tmpName
    $containerTmp = '/tmp/' + $tmpName
    $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllText($localTmp, (($Script -replace "`r`n", "`n") -replace "`r", "`n"), $utf8NoBom)

    try {
        Invoke-LoggedExpression -Context $Context -Expression ("docker cp `"{0}`" {1}:{2}" -f $localTmp, $Container, $containerTmp) -Label ($Label + '-cp')
        Invoke-LoggedExpression -Context $Context -Expression ("docker exec {0} sh {1}" -f $Container, $containerTmp) -Label ($Label + '-exec') -AllowFailure:$AllowFailure
    }
    finally {
        try { & docker exec $Container rm -f $containerTmp *> $null } catch {}
        Remove-Item $localTmp -Force -ErrorAction SilentlyContinue
    }
}

function Get-ProfileDefinitions {
    return @{
        'Canales-youtube' = @{ Slug = 'canales-youtube' }
        'Podcast'         = @{ Slug = 'podcast' }
        'TV-Serie'        = @{ Slug = 'tv-serie' }
        'Music-Playlist'  = @{ Slug = 'music-playlist' }
        'Ambience-Video'  = @{ Slug = 'ambience-video' }
        'Ambience-Audio'  = @{ Slug = 'ambience-audio' }
    }
}

function Get-AllProfileNames {
    return @('Canales-youtube','Podcast','TV-Serie','Music-Playlist','Ambience-Video','Ambience-Audio')
}

function Assert-ValidProfileName {
    param([Parameter(Mandatory = $true)][string]$ProfileName)
    if ($ProfileName -notin (Get-AllProfileNames)) {
        throw "Perfil no válido: $ProfileName. Válidos: $((Get-AllProfileNames) -join ', ')"
    }
}

function Reset-WorkingState {
    param([Parameter(Mandatory = $true)]$Context)
    Write-TestSection -Context $Context -Title 'Limpieza de locks, working directory y restos temporales'
    $script = @'
set -e
pkill -f ytdl-sub 2>/dev/null || true
sleep 1
find /tmp -maxdepth 1 -type f \( -name "ytdl-sub*.lock" -o -name "*.lock" \) -print -delete 2>/dev/null || true
rm -rf /tmp/ytdl-sub-working-directory/* 2>/dev/null || true
rm -f /tmp/trim-ambience-video.py /tmp/trim-ambience-media.py 2>/dev/null || true
'@
    Invoke-DockerShellScript -Context $Context -Container 'ytdl-sub' -Script $script -Label 'reset-workdir'
}

function Invoke-GenerationPhase {
    param(
        [Parameter(Mandatory = $true)]$Context,
        [string[]]$Profiles = @()
    )

    $projectRoot = Get-ProjectRoot
    Push-Location $projectRoot
    try {
        Write-TestSection -Context $Context -Title 'Generación de YAML y runset'
        Invoke-LoggedExpression -Context $Context -Expression 'python -u .\generate-ytdl-config.py' -Label 'generate-ytdl-config'

        if ($Profiles.Count -gt 0) {
            $profileArgs = ($Profiles | ForEach-Object { '--profile-name "{0}"' -f $_ }) -join ' '
            Invoke-LoggedExpression -Context $Context -Expression ("python -u .\prepare-subscriptions-runset.py {0}" -f $profileArgs) -Label 'prepare-subscriptions-runset'
        }
        else {
            Invoke-LoggedExpression -Context $Context -Expression 'python -u .\prepare-subscriptions-runset.py' -Label 'prepare-subscriptions-runset'
        }
    }
    finally {
        Pop-Location
    }
}

function Filter-RunsetToProfiles {
    param(
        [Parameter(Mandatory = $true)]$Context,
        [Parameter(Mandatory = $true)][string[]]$Profiles
    )

    $projectRoot = Get-ProjectRoot
    $runsetPath = Join-Path $projectRoot 'subscriptions.runset.yaml'
    $pendingPath = Join-Path $projectRoot '.recent-items-state.pending.json'
    $filteredRunsetPath = Get-FilteredRunsetPath
    $filteredPendingPath = Get-FilteredPendingStatePath

    if (-not (Test-Path $runsetPath)) {
        throw "No existe el runset base: $runsetPath"
    }

    if (-not (Test-Path $pendingPath)) {
        throw "No existe el estado pendiente base: $pendingPath"
    }

    Copy-Item -Path $runsetPath -Destination $filteredRunsetPath -Force
    Copy-Item -Path $pendingPath -Destination $filteredPendingPath -Force

    $count = 0
    if (Test-FilteredRunsetHasEntries -Path $filteredRunsetPath) {
        $raw = Get-Content -Path $filteredRunsetPath -Raw -Encoding UTF8
        $matches = [regex]::Matches($raw, '^[^\s:#][^:]*:', [System.Text.RegularExpressions.RegexOptions]::Multiline)
        $count = $matches.Count
    }

    Write-TestLine -Context $Context -Message "Runset filtrado preparado desde el runset ya scoped por prepare-subscriptions-runset.py" -Level 'INFO'
    Write-TestLine -Context $Context -Message "Perfiles solicitados: $($Profiles -join ', ')" -Level 'INFO'
    Write-TestLine -Context $Context -Message "Runset filtrado: $filteredRunsetPath" -Level 'INFO'
    Write-TestLine -Context $Context -Message "Estado pendiente filtrado: $filteredPendingPath" -Level 'INFO'
    Write-TestLine -Context $Context -Message "Entradas detectadas en runset filtrado: $count" -Level 'INFO'
}

function Copy-TrimScriptToContainer {
    param([Parameter(Mandatory = $true)]$Context)
    $projectRoot = Get-ProjectRoot
    Invoke-LoggedExpression -Context $Context -Expression ("docker cp `"{0}`" ytdl-sub:/tmp/trim-ambience-video.py" -f (Join-Path $projectRoot 'trim-ambience-video.py')) -Label 'copy-trim-script'
}

function Invoke-RunsetExecution {
    param(
        [Parameter(Mandatory = $true)]$Context,
        [switch]$DryRun
    )

    $filteredRunset = Get-FilteredRunsetPath
    if (-not (Test-Path $filteredRunset)) { throw 'No existe subscriptions.runset.filtered.yaml' }

    Write-TestSection -Context $Context -Title 'Inspección del runset filtrado'
    Get-Content $filteredRunset | Tee-Object -FilePath $Context.MainLog -Append | Out-Null

    if (-not (Test-FilteredRunsetHasEntries -Path $filteredRunset)) {
        Write-TestLine -Context $Context -Message 'El runset filtrado está vacío; no hay nada que ejecutar.' -Level 'WARN'
        return
    }

    if ($DryRun) {
        Write-TestSection -Context $Context -Title 'Dry-run: se omite la descarga real y todo postproceso'
        Write-TestLine -Context $Context -Message 'Se han generado YAML, runset y estado pendiente, pero no se lanza ytdl-sub real.' -Level 'OK'
        return
    }

    Write-TestSection -Context $Context -Title 'Ejecución real de ytdl-sub sobre el runset filtrado'
    Invoke-LoggedExpression -Context $Context -Expression 'docker exec ytdl-sub ytdl-sub --config /config/zenoytdl/config.generated.yaml sub /config/zenoytdl/subscriptions.runset.filtered.yaml' -Label 'ytdl-sub-sub'
}

function Promote-PendingState {
    param(
        [Parameter(Mandatory = $true)]$Context,
        [switch]$DryRun,
        [Parameter(Mandatory = $true)][bool]$HasEntries
    )

    if ($DryRun) {
        Write-TestLine -Context $Context -Message 'Dry-run activo: no se promueve .recent-items-state.pending.filtered.json a estado definitivo.' -Level 'INFO'
        return
    }

    if (-not $HasEntries) {
        Write-TestLine -Context $Context -Message 'No se promueve estado porque el runset filtrado está vacío.' -Level 'WARN'
        return
    }

    $pendingFiltered = Get-FilteredPendingStatePath
    $stateFile = Get-StateFilePath
    if (Test-Path $pendingFiltered) {
        Copy-Item $pendingFiltered $stateFile -Force
        Write-TestLine -Context $Context -Message "Estado promovido a definitivo: $stateFile" -Level 'OK'
    }
    else {
        Write-TestLine -Context $Context -Message "No existe estado pendiente filtrado: $pendingFiltered" -Level 'WARN'
    }
}

function Invoke-MusicPostprocess {
    param([Parameter(Mandatory = $true)]$Context)
    Write-TestSection -Context $Context -Title 'Postproceso music-playlist: limpieza + beets'
    $script = @'
set -e
if [ -d /downloads/Music-Playlist ]; then
  find /downloads/Music-Playlist -mindepth 1 -maxdepth 1 -type d | while read -r d; do
    echo "[BEETS] $d"
    beet -v -c /config/zenoytdl/beets.music-playlist.yaml import -s -q "$d" || true
  done
else
  echo '[WARN] No existe /downloads/Music-Playlist'
fi
'@
    Invoke-DockerShellScript -Context $Context -Container 'beets-streaming2' -Script $script -Label 'beets-music'
}

function Invoke-AmbiencePostprocess {
    param(
        [Parameter(Mandatory = $true)]$Context,
        [Parameter(Mandatory = $true)][string]$ProfileName
    )

    $title = if ($ProfileName -eq 'Ambience-Video') { 'Postproceso ambience-video: trim' } else { 'Postproceso ambience-audio: trim' }
    Write-TestSection -Context $Context -Title $title

    if ($ProfileName -eq 'Ambience-Video') {
        $baseDir = '/downloads/Ambience-Video'
        $findExpr = "\( -iname '*.mp4' -o -iname '*.mkv' -o -iname '*.webm' -o -iname '*.mov' -o -iname '*.m4v' -o -iname '*.avi' \)"
    }
    else {
        $baseDir = '/downloads/Ambience-Audio'
        $findExpr = "\( -iname '*.mp3' -o -iname '*.m4a' -o -iname '*.aac' -o -iname '*.opus' -o -iname '*.ogg' -o -iname '*.wav' -o -iname '*.flac' \)"
    }

    $script = @'
set -e
if [ -d "{0}" ]; then
  find "{0}" -type f {1} | while IFS= read -r f; do
    echo "[TRIM] $f"
    python /tmp/trim-ambience-video.py --input "$f" --max-duration 03:03:03 --replace --skip-output-probe
  done
else
  echo '[WARN] No existe {0}'
fi
'@ -f $baseDir, $findExpr

    Invoke-DockerShellScript -Context $Context -Container 'ytdl-sub' -Script $script -Label ('trim-' + $ProfileName.ToLowerInvariant())
}

function Collect-RelevantContainerLogs {
    param([Parameter(Mandatory = $true)]$Context)

    Write-TestSection -Context $Context -Title 'Captura de logs relevantes de contenedores'
    $script = @'
set -e
printf "[LOGS /config/logs]\n"
ls -lah /config/logs 2>/dev/null || true
printf "\n[ULTIMOS LOGS YTDL-SUB]\n"
find /config/logs -maxdepth 1 -type f | sort | tail -n 20 | while read -r f; do
  echo "------------------------------------------------------------"
  echo "$f"
  tail -n 120 "$f" || true
done
printf "\n[WORKING DIRECTORY]\n"
find /tmp/ytdl-sub-working-directory -mindepth 1 -maxdepth 3 -print 2>/dev/null || true
'@
    Invoke-DockerShellScript -Context $Context -Container 'ytdl-sub' -Script $script -Label 'collect-ytdl-logs' -AllowFailure

    $beetsScript = @'
set -e
printf "[BEETS LOG]\n"
if [ -f /config/logs/beets-import.log ]; then
  tail -n 200 /config/logs/beets-import.log || true
else
  echo "[INFO] No existe /config/logs/beets-import.log"
fi
'@
    Invoke-DockerShellScript -Context $Context -Container 'beets-streaming2' -Script $beetsScript -Label 'collect-beets-logs' -AllowFailure
}

function Write-RelevantLogPaths {
    param([Parameter(Mandatory = $true)]$Context)
    Write-Host "Logs principales:"
    Write-Host "- Main log: $($Context.MainLog)"
    Write-Host "- Transcript: $($Context.TranscriptLog)"
    Write-Host "- Carpeta ejecución: $($Context.BaseDir)"
}