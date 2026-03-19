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

    if (-not (Test-Path $Path)) {
        return $false
    }

    $raw = (Get-Content -Path $Path -Raw -Encoding UTF8).Trim()

    if ([string]::IsNullOrWhiteSpace($raw)) { return $false }
    if ($raw -eq '{}') { return $false }
    if ($raw -eq '---') { return $false }
    if ($raw -eq 'null') { return $false }

    return $true
}

function New-TestExecutionContext {
    param(
        [Parameter(Mandatory = $true)]
        [string]$TestName
    )

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
    $null = New-Item -ItemType Directory -Force -Path (Get-LogsRoot)
    Start-Transcript -Path $Context.TranscriptLog -Force | Out-Null
}

function Stop-TestLogging {
    try { Stop-Transcript | Out-Null } catch {}
}

function Write-TestLine {
    param(
        [Parameter(Mandatory = $true)]$Context,
        [Parameter(Mandatory = $true)][string]$Message,
        [ValidateSet('INFO','WARN','ERROR','OK','STEP')]
        [string]$Level = 'INFO'
    )

    $line = ('[{0}] [{1}] {2}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Level, $Message)
    Write-Host $line
    Add-Content -Path $Context.MainLog -Value $line -Encoding UTF8
}

function Write-TestSection {
    param(
        [Parameter(Mandatory = $true)]$Context,
        [Parameter(Mandatory = $true)][string]$Title
    )

    $sep = '=' * 76
    Write-TestLine -Context $Context -Message $sep -Level 'STEP'
    Write-TestLine -Context $Context -Message $Title -Level 'STEP'
    Write-TestLine -Context $Context -Message $sep -Level 'STEP'
}

function Invoke-LoggedExpression {
    param(
        [Parameter(Mandatory = $true)]$Context,
        [Parameter(Mandatory = $true)][string]$Expression,
        [string]$Label = 'command',
        [switch]$AllowFailure
    )

    Write-TestLine -Context $Context -Message ("Ejecutando [{0}]: {1}" -f $Label, $Expression)
    Add-Content -Path $Context.MainLog -Value ("`n### BEGIN {0}`n{1}`n" -f $Label, $Expression) -Encoding UTF8

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = 'powershell.exe'
    $psi.Arguments = "-NoProfile -ExecutionPolicy Bypass -Command $Expression"
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.CreateNoWindow = $true
    $psi.StandardOutputEncoding = [System.Text.UTF8Encoding]::new($false)
    $psi.StandardErrorEncoding = [System.Text.UTF8Encoding]::new($false)

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $psi

    $null = $process.Start()

    $stdout = $process.StandardOutput.ReadToEnd()
    $stderr = $process.StandardError.ReadToEnd()

    $process.WaitForExit()
    $exitCode = [int]$process.ExitCode
    $global:LASTEXITCODE = $exitCode

    if ($stdout) {
        $stdout | Tee-Object -FilePath $Context.MainLog -Append | Out-Host
    }
    if ($stderr) {
        $stderr | Tee-Object -FilePath $Context.MainLog -Append | Out-Host
    }

    Add-Content -Path $Context.MainLog -Value ("`n### END {0} (exit={1})`n" -f $Label, $exitCode) -Encoding UTF8

    if (($exitCode -ne 0) -and (-not $AllowFailure)) {
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
        try {
            & docker exec $Container rm -f $containerTmp *> $null
        }
        catch {}
        Remove-Item $localTmp -Force -ErrorAction SilentlyContinue
    }
}

function Get-ProfileDefinitions {
    return @{
        'Canales-youtube' = @{
            Slug = 'canales-youtube'
            OutputTemplate = '/downloads/Canales-youtube/{subscription_root}'
            Extensions = @('.mp4','.mkv','.webm','.mov','.m4v','.avi')
            NeedsBeets = $false
            NeedsTrim = $false
        }
        'Podcast' = @{
            Slug = 'podcast'
            OutputTemplate = '/downloads/Podcast/{subscription_root}/{source_target}'
            Extensions = @('.mp3','.m4a','.aac','.opus','.ogg','.wav','.flac')
            NeedsBeets = $false
            NeedsTrim = $false
        }
        'TV-Serie' = @{
            Slug = 'tv-serie'
            OutputTemplate = '/downloads/TV-Serie/{subscription_root}'
            Extensions = @('.mp4','.mkv','.webm','.mov','.m4v','.avi','.nfo')
            NeedsBeets = $false
            NeedsTrim = $false
        }
        'Music-Playlist' = @{
            Slug = 'music-playlist'
            OutputTemplate = '/downloads/Music-Playlist/{subscription_root}'
            Extensions = @('.mp3','.m4a','.aac','.opus','.ogg','.wav','.flac')
            NeedsBeets = $true
            NeedsTrim = $false
        }
        'Ambience-Video' = @{
            Slug = 'ambience-video'
            OutputTemplate = '/downloads/Ambience-Video/{subscription_root}'
            Extensions = @('.mp4','.mkv','.webm','.mov','.m4v','.avi')
            NeedsBeets = $false
            NeedsTrim = $true
        }
        'Ambience-Audio' = @{
            Slug = 'ambience-audio'
            OutputTemplate = '/downloads/Ambience-Audio/{subscription_root}'
            Extensions = @('.mp3','.m4a','.aac','.opus','.ogg','.wav','.flac')
            NeedsBeets = $false
            NeedsTrim = $true
        }
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

function Invoke-PythonInline {
    param(
        [Parameter(Mandatory = $true)]$Context,
        [Parameter(Mandatory = $true)][string]$Code,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [string]$Label = 'python-inline'
    )

    $tmpPy = Join-Path $env:TEMP ('zenotest-' + [guid]::NewGuid().ToString('N') + '.py')
    [System.IO.File]::WriteAllText($tmpPy, (($Code -replace "`r`n", "`n") -replace "`r", "`n"), [System.Text.UTF8Encoding]::new($false))
    try {
        $argsQuoted = $Arguments | ForEach-Object { '"' + ($_ -replace '"','\"') + '"' }
        $expr = 'python -u "{0}" {1}' -f $tmpPy, ($argsQuoted -join ' ')
        Invoke-LoggedExpression -Context $Context -Expression $expr -Label $Label
    }
    finally {
        Remove-Item $tmpPy -Force -ErrorAction SilentlyContinue
    }
}

function Filter-RunsetToProfiles {
    param(
        [Parameter(Mandatory = $true)]$Context,
        [Parameter(Mandatory = $true)][string[]]$Profiles
    )
    $projectRoot = Get-ProjectRoot
    $code = @'
import json, sys, yaml
from pathlib import Path

project_root = sys.argv[1]
profiles = set(sys.argv[2:])
runset_path = project_root + '/subscriptions.runset.yaml'
pending_path = project_root + '/.recent-items-state.pending.json'
out_runset_path = project_root + '/subscriptions.runset.filtered.yaml'
out_pending_path = project_root + '/.recent-items-state.pending.filtered.json'

runset = yaml.safe_load(open(runset_path, 'r', encoding='utf-8')) or {}
pending = json.load(open(pending_path, 'r', encoding='utf-8')) if Path(pending_path).exists() else {'sources':{}}

filtered_runset = {}
for key, value in (runset or {}).items():
    keep = False
    if isinstance(value, dict):
        profile_name = str(value.get('profile_name') or '').strip()
        if profile_name in profiles:
            keep = True
        elif profile_name == '' and key:
            for p in profiles:
                if key.startswith(p.lower().replace(' ', '-')):
                    keep = True
                    break
    if keep:
        filtered_runset[key] = value

filtered_pending = {'sources': {}}
for key, value in (pending.get('sources') or {}).items():
    if str(value.get('profile_name','')).strip() in profiles:
        filtered_pending['sources'][key] = value

with open(out_runset_path, 'w', encoding='utf-8', newline='\n') as fh:
    yaml.safe_dump(filtered_runset, fh, allow_unicode=True, sort_keys=False, default_flow_style=False, width=1000)
with open(out_pending_path, 'w', encoding='utf-8') as fh:
    json.dump(filtered_pending, fh, ensure_ascii=False, indent=2)

print(out_runset_path)
print(out_pending_path)
print(len(filtered_runset))
'@
    Invoke-PythonInline -Context $Context -Code $code -Arguments (@($projectRoot) + $Profiles) -Label 'filter-runset-profiles'
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
    param([Parameter(Mandatory = $true)]$Context)
    $projectRoot = Get-ProjectRoot
    Push-Location $projectRoot
    try {
        Write-TestSection -Context $Context -Title 'Generación de YAML y runset completo'
        Invoke-LoggedExpression -Context $Context -Expression 'python -u .\generate-ytdl-config.py' -Label 'generate-ytdl-config'
        Invoke-LoggedExpression -Context $Context -Expression 'python -u .\prepare-subscriptions-runset.py' -Label 'prepare-subscriptions-runset'
    }
    finally {
        Pop-Location
    }
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
    Invoke-LoggedExpression -Context $Context -Expression 'docker exec ytdl-sub sh -lc "ytdl-sub --config /config/zenoytdl/config.generated.yaml sub /config/zenoytdl/subscriptions.runset.filtered.yaml"' -Label 'ytdl-sub-sub'
}

function Promote-PendingState {
    param(
        [Parameter(Mandatory = $true)]$Context,
        [switch]$DryRun,
        [Parameter(Mandatory = $true)]
        [bool]$HasEntries
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
  tail -n 200 /config/logs/beets-import.log
else
  echo '[INFO] No existe /config/logs/beets-import.log'
fi
'@
    Invoke-DockerShellScript -Context $Context -Container 'beets-streaming2' -Script $beetsScript -Label 'collect-beets-logs' -AllowFailure
}

function Write-RelevantLogPaths {
    param([Parameter(Mandatory = $true)]$Context)
    $msg = @(
        "Logs principales:",
        "- Main log: $($Context.MainLog)",
        "- Transcript: $($Context.TranscriptLog)",
        "- Carpeta ejecución: $($Context.BaseDir)"
    ) -join [Environment]::NewLine
    $msg | Tee-Object -FilePath $Context.SummaryLog -Append | Write-Host
}