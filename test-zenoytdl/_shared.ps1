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

    try {
        Invoke-Expression $Expression 2>&1 | Tee-Object -FilePath $Context.MainLog -Append
        $exitCode = if ($null -ne $LASTEXITCODE) { $LASTEXITCODE } else { 0 }
    }
    catch {
        if (-not $AllowFailure) { throw }
        $_ | Out-String | Tee-Object -FilePath $Context.MainLog -Append | Out-Null
        $exitCode = if ($null -ne $LASTEXITCODE) { $LASTEXITCODE } else { 1 }
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
    [System.IO.File]::WriteAllText($localTmp, ($Script -replace "`r`n", "`n"), $utf8NoBom)

    try {
        Invoke-LoggedExpression -Context $Context -Expression ("docker cp `"{0}`" {1}:{2}" -f $localTmp, $Container, $containerTmp) -Label ($Label + '-cp')
        Invoke-LoggedExpression -Context $Context -Expression ("docker exec {0} sh {1}" -f $Container, $containerTmp) -Label ($Label + '-exec') -AllowFailure:$AllowFailure
    }
    finally {
        try { Invoke-Expression ("docker exec {0} sh -lc \"rm -f '{1}'\"" -f $Container, $containerTmp) *> $null } catch {}
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
    [System.IO.File]::WriteAllText($tmpPy, ($Code -replace "`r`n", "`n"), [System.Text.UTF8Encoding]::new($false))
    try {
        $argsQuoted = $Arguments | ForEach-Object { '"' + ($_ -replace '"','\"') + '"' }
        $expr = 'python "{0}" {1}' -f $tmpPy, ($argsQuoted -join ' ')
        Invoke-LoggedExpression -Context $Context -Expression $expr -Label $Label
    }
    finally {
        Remove-Item $tmpPy -Force -ErrorAction SilentlyContinue
    }
}

function Get-SubscriptionOverview {
    $projectRoot = Get-ProjectRoot
    $py = @'
import sys, yaml, re, unicodedata
from urllib.parse import parse_qs, urlparse

def slugify(value: str) -> str:
    raw = str(value).strip().lower()
    raw = unicodedata.normalize("NFKD", raw)
    raw = raw.encode("ascii", "ignore").decode("ascii")
    raw = raw.replace("_", "-")
    raw = re.sub(r"[^a-z0-9\-]+", "-", raw)
    raw = re.sub(r"-{2,}", "-", raw)
    raw = raw.strip("-")
    return raw or "item"

def extract_source_target_from_url(url: str) -> str:
    url = url.strip()
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    if 'v' in qs and qs['v']:
        return slugify(qs['v'][0])
    if 'list' in qs and qs['list']:
        return slugify(qs['list'][0])
    m = re.search(r"youtube\.com/@([^/?#]+)", url, re.IGNORECASE)
    if m:
        return slugify(m.group(1))
    parts = [p for p in parsed.path.split('/') if p]
    if parts:
        return slugify(parts[-1])
    return 'source'

subs = yaml.safe_load(open(sys.argv[1], 'r', encoding='utf-8')) or {}
for item in subs.get('subscriptions', []):
    profile = str(item.get('profile_name','')).strip()
    custom_name = str(item.get('custom_name','')).strip()
    root = slugify(custom_name)
    for source in item.get('sources') or []:
        url = str(source.get('url','')).strip()
        target = extract_source_target_from_url(url)
        print(f"{profile}\t{custom_name}\t{root}\t{target}\t{url}")
'@
    $tmp = Join-Path $env:TEMP ('zeno-subs-' + [guid]::NewGuid().ToString('N') + '.py')
    [System.IO.File]::WriteAllText($tmp, $py, [System.Text.UTF8Encoding]::new($false))
    try {
        $lines = & python $tmp (Join-Path $projectRoot 'subscription-custom.yml')
        if ($LASTEXITCODE -ne 0) { throw 'No se pudo leer subscription-custom.yml' }
        $items = foreach ($line in $lines) {
            if ([string]::IsNullOrWhiteSpace($line)) { continue }
            $parts = $line -split "`t", 5
            [pscustomobject]@{
                ProfileName      = $parts[0]
                CustomName       = $parts[1]
                SubscriptionRoot = $parts[2]
                SourceTarget     = $parts[3]
                Url              = $parts[4]
            }
        }
        return ,$items
    }
    finally {
        Remove-Item $tmp -Force -ErrorAction SilentlyContinue
    }
}

function Get-ProfileOutputPaths {
    param([Parameter(Mandatory = $true)][string]$ProfileName)
    Assert-ValidProfileName -ProfileName $ProfileName
    $defs = Get-ProfileDefinitions
    $def = $defs[$ProfileName]
    $items = Get-SubscriptionOverview | Where-Object { $_.ProfileName -eq $ProfileName }
    $paths = foreach ($item in $items) {
        $path = $def.OutputTemplate.Replace('{subscription_root}', $item.SubscriptionRoot).Replace('{source_target}', $item.SourceTarget)
        [pscustomobject]@{
            ProfileName      = $ProfileName
            CustomName       = $item.CustomName
            SubscriptionRoot = $item.SubscriptionRoot
            SourceTarget     = $item.SourceTarget
            OutputPath       = $path
            Url              = $item.Url
        }
    }
    return ,$paths
}

function Remove-ProfileDownloads {
    param(
        [Parameter(Mandatory = $true)]$Context,
        [Parameter(Mandatory = $true)][string[]]$Profiles
    )

    foreach ($profile in $Profiles) {
        Write-TestSection -Context $Context -Title ("Borrado previo de descargas para perfil: $profile")
        $paths = Get-ProfileOutputPaths -ProfileName $profile
        foreach ($entry in $paths) {
            Invoke-LoggedExpression -Context $Context -Expression ("docker exec ytdl-sub sh -lc \"rm -rf '{0}'\"" -f $entry.OutputPath) -Label ("rm-download-" + $entry.SubscriptionRoot)
        }
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
    param([Parameter(Mandatory = $true)]$Context)
    $projectRoot = Get-ProjectRoot
    Push-Location $projectRoot
    try {
        Write-TestSection -Context $Context -Title 'Generación de YAML y runset completo'
        Invoke-LoggedExpression -Context $Context -Expression 'python .\generate-ytdl-config.py' -Label 'generate-ytdl-config'
        Invoke-LoggedExpression -Context $Context -Expression 'python .\prepare-subscriptions-runset.py' -Label 'prepare-subscriptions-runset'
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
    $code = @'
import json, sys, yaml
project_root = sys.argv[1]
profiles = set(sys.argv[2:])
runset_path = project_root + '/subscriptions.runset.yaml'
pending_path = project_root + '/.recent-items-state.pending.json'
out_runset_path = project_root + '/subscriptions.runset.filtered.yaml'
out_pending_path = project_root + '/.recent-items-state.pending.filtered.json'
sub_path = project_root + '/subscription-custom.yml'

subs = yaml.safe_load(open(sub_path, 'r', encoding='utf-8')) or {}
runset = yaml.safe_load(open(runset_path, 'r', encoding='utf-8')) or {}
pending = json.load(open(pending_path, 'r', encoding='utf-8')) if __import__('pathlib').Path(pending_path).exists() else {'sources':{}}

allowed_roots = set()
for item in subs.get('subscriptions', []):
    if str(item.get('profile_name','')).strip() in profiles:
        custom = str(item.get('custom_name','')).strip().lower()
        import re, unicodedata
        raw = unicodedata.normalize('NFKD', custom).encode('ascii', 'ignore').decode('ascii')
        raw = raw.replace('_','-')
        raw = re.sub(r'[^a-z0-9\-]+', '-', raw)
        raw = re.sub(r'-{2,}', '-', raw).strip('-') or 'item'
        allowed_roots.add(raw)

filtered_runset = {}
for key, value in (runset or {}).items():
    keep = False
    root = ''
    if isinstance(value, dict) and value:
        first_val = next(iter(value.values()))
        if isinstance(first_val, dict):
            root = str(first_val.get('subscription_root_sanitized') or '')
    if root in allowed_roots:
        keep = True
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
    Invoke-PythonInline -Context $Context -Code $code -Arguments @($projectRoot) + $Profiles -Label 'filter-runset-profiles'
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
    $projectRoot = Get-ProjectRoot
    $filteredRunset = Join-Path $projectRoot 'subscriptions.runset.filtered.yaml'
    if (-not (Test-Path $filteredRunset)) { throw 'No existe subscriptions.runset.filtered.yaml' }

    Write-TestSection -Context $Context -Title 'Inspección del runset filtrado'
    Get-Content $filteredRunset | Tee-Object -FilePath $Context.MainLog -Append | Out-Null

    if ((Get-Item $filteredRunset).Length -le 5) {
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
        [switch]$DryRun
    )
    $projectRoot = Get-ProjectRoot
    if ($DryRun) {
        Write-TestLine -Context $Context -Message 'Dry-run activo: no se promueve .recent-items-state.pending.filtered.json a estado definitivo.' -Level 'INFO'
        return
    }
    $pendingFiltered = Join-Path $projectRoot '.recent-items-state.pending.filtered.json'
    $stateFile = Join-Path $projectRoot '.recent-items-state.json'
    if (Test-Path $pendingFiltered) {
        Copy-Item $pendingFiltered $stateFile -Force
        Write-TestLine -Context $Context -Message "Estado promovido a definitivo: $stateFile" -Level 'OK'
    }
}

function Invoke-MusicPostprocess {
    param([Parameter(Mandatory = $true)]$Context)
    $projectRoot = Get-ProjectRoot
    Write-TestSection -Context $Context -Title 'Postproceso music-playlist: limpieza + beets'
    $paths = Get-ProfileOutputPaths -ProfileName 'Music-Playlist'
    foreach ($entry in $paths) {
        $windowsDir = "E:\Docker_folders\ydtl-custom-downloads\Music-Playlist\{0}" -f $entry.SubscriptionRoot
        if (Test-Path (Join-Path $projectRoot 'clean-music-filenames.ps1')) {
            Invoke-LoggedExpression -Context $Context -Expression ("powershell -ExecutionPolicy Bypass -File `"{0}`" -TargetDir `"{1}`"" -f (Join-Path $projectRoot 'clean-music-filenames.ps1'), $windowsDir) -Label ('clean-music-' + $entry.SubscriptionRoot)
        }
        $script = @"
set -e
if [ -d '$($entry.OutputPath)' ]; then
  beet -v -c /config/zenoytdl/beets.music-playlist.yaml import -s -q '$($entry.OutputPath)'
else
  echo '[WARN] No existe $($entry.OutputPath)'
fi
"@
        Invoke-DockerShellScript -Context $Context -Container 'beets-streaming2' -Script $script -Label ('beets-' + $entry.SubscriptionRoot)
    }
}

function Invoke-AmbiencePostprocess {
    param(
        [Parameter(Mandatory = $true)]$Context,
        [Parameter(Mandatory = $true)][string]$ProfileName
    )
    $paths = Get-ProfileOutputPaths -ProfileName $ProfileName
    $title = if ($ProfileName -eq 'Ambience-Video') { 'Postproceso ambience-video: trim' } else { 'Postproceso ambience-audio: trim' }
    Write-TestSection -Context $Context -Title $title

    foreach ($entry in $paths) {
        $findExpr = if ($ProfileName -eq 'Ambience-Video') {
            "\\( -iname '*.mp4' -o -iname '*.mkv' -o -iname '*.webm' -o -iname '*.mov' -o -iname '*.m4v' -o -iname '*.avi' \\)"
        } else {
            "\\( -iname '*.mp3' -o -iname '*.m4a' -o -iname '*.aac' -o -iname '*.opus' -o -iname '*.ogg' -o -iname '*.wav' -o -iname '*.flac' \\)"
        }
        $script = @"
set -e
if [ -d '$($entry.OutputPath)' ]; then
  find '$($entry.OutputPath)' -maxdepth 1 -type f $findExpr -exec sh -c '
    f="$1"
    echo "[TRIM] $f"
    python /tmp/trim-ambience-video.py --input "$f" --max-duration 03:03:03 --replace --skip-output-probe
  ' sh {} \;
else
  echo '[WARN] No existe $($entry.OutputPath)'
fi
"@
        Invoke-DockerShellScript -Context $Context -Container 'ytdl-sub' -Script $script -Label ('trim-' + $entry.SubscriptionRoot)
    }
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
