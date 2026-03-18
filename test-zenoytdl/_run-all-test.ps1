Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. "$PSScriptRoot\_shared.ps1"

$ctx = New-TestExecutionContext -TestName '_run-all-test'
Start-TestLogging -Context $ctx

$reportPath = Join-Path $ctx.BaseDir '_run-all-test.report.log'
$jsonSummaryPath = Join-Path $ctx.BaseDir '_run-all-test.summary.json'
$csvSummaryPath = Join-Path $ctx.BaseDir '_run-all-test.summary.csv'

$script:ExecutionRows = [System.Collections.Generic.List[object]]::new()

function Write-ReportLine {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    $line = '[{0}] {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message
    Write-Host $line
    Add-Content -Path $reportPath -Value $line -Encoding UTF8
}

function Write-ReportSection {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Title
    )

    $sep = '=' * 96
    Write-ReportLine $sep
    Write-ReportLine $Title
    Write-ReportLine $sep
}

function Get-LogDirectorySnapshot {
    $logsRoot = Get-LogsRoot
    if (-not (Test-Path $logsRoot)) {
        return @()
    }

    return @(Get-ChildItem -Path $logsRoot -Directory -Recurse -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty FullName |
        Sort-Object -Unique)
}

function Get-NewLogDirectories {
    param(
        [string[]]$Before,
        [string[]]$After
    )

    $beforeSet = @{}
    foreach ($item in $Before) {
        $beforeSet[$item] = $true
    }

    $newItems = foreach ($item in $After) {
        if (-not $beforeSet.ContainsKey($item)) {
            $item
        }
    }

    return @($newItems | Sort-Object -Unique)
}

function Add-ExecutionRow {
    param(
        [Parameter(Mandatory = $true)]
        [pscustomobject]$Row
    )
    $script:ExecutionRows.Add($Row) | Out-Null
}

function Invoke-ChildTest {
    param(
        [Parameter(Mandatory = $true)]
        [string]$StepId,

        [Parameter(Mandatory = $true)]
        [string]$Category,

        [Parameter(Mandatory = $true)]
        [string]$DisplayName,

        [Parameter(Mandatory = $true)]
        [string]$Command
    )

    Write-ReportSection ("INICIO {0} | {1}" -f $StepId, $DisplayName)
    Write-ReportLine ("Categoría: {0}" -f $Category)
    Write-ReportLine ("Comando:   {0}" -f $Command)

    $beforeLogs = Get-LogDirectorySnapshot
    $start = Get-Date
    $status = 'OK'
    $exitCode = 0
    $errorText = $null

    try {
        Write-TestLine -Context $ctx -Message ("Lanzando hijo [{0}] {1}" -f $StepId, $DisplayName) -Level 'INFO'
        Invoke-LoggedExpression -Context $ctx -Expression $Command -Label ("child-" + $StepId)
        $exitCode = if ($null -ne $LASTEXITCODE) { [int]$LASTEXITCODE } else { 0 }
    }
    catch {
        $status = 'ERROR'
        $exitCode = if ($null -ne $LASTEXITCODE) { [int]$LASTEXITCODE } else { 1 }
        $errorText = $_.Exception.Message
        Write-TestLine -Context $ctx -Message ("Fallo en hijo [{0}] {1}: {2}" -f $StepId, $DisplayName, $errorText) -Level 'ERROR'
    }

    $end = Get-Date
    $afterLogs = Get-LogDirectorySnapshot
    $newLogDirs = Get-NewLogDirectories -Before $beforeLogs -After $afterLogs
    $duration = [math]::Round(($end - $start).TotalSeconds, 3)

    Write-ReportLine ("Resultado: {0}" -f $status)
    Write-ReportLine ("ExitCode:  {0}" -f $exitCode)
    Write-ReportLine ("Inicio:    {0}" -f $start.ToString('yyyy-MM-dd HH:mm:ss'))
    Write-ReportLine ("Fin:       {0}" -f $end.ToString('yyyy-MM-dd HH:mm:ss'))
    Write-ReportLine ("Duración:  {0} s" -f $duration)

    if ($newLogDirs.Count -gt 0) {
        Write-ReportLine 'Nuevas carpetas de logs detectadas:'
        foreach ($dir in $newLogDirs) {
            Write-ReportLine ("  - {0}" -f $dir)
        }
    }
    else {
        Write-ReportLine 'Nuevas carpetas de logs detectadas: ninguna'
    }

    if ($errorText) {
        Write-ReportLine ("Error resumido: {0}" -f $errorText)
    }

    Add-ExecutionRow ([pscustomobject]@{
        StepId         = $StepId
        Category       = $Category
        DisplayName    = $DisplayName
        Command        = $Command
        Status         = $status
        ExitCode       = $exitCode
        StartedAt      = $start.ToString('yyyy-MM-dd HH:mm:ss')
        FinishedAt     = $end.ToString('yyyy-MM-dd HH:mm:ss')
        DurationSec    = $duration
        NewLogDirs     = ($newLogDirs -join ' | ')
        ErrorSummary   = $errorText
    })

    return ($status -eq 'OK')
}

try {
    Write-TestSection -Context $ctx -Title 'Inicio del lanzador maestro de todos los tests'
    Write-ReportSection 'RUN ALL TESTS - REPORTE MAESTRO'
    Write-ReportLine ("Carpeta de ejecución maestra: {0}" -f $ctx.BaseDir)
    Write-ReportLine ("Main log maestro:            {0}" -f $ctx.MainLog)
    Write-ReportLine ("Transcript maestro:          {0}" -f $ctx.TranscriptLog)
    Write-ReportLine ("Report log maestro:          {0}" -f $reportPath)
    Write-ReportLine ("Logs root global:            {0}" -f (Get-LogsRoot))
    Write-ReportLine ("Project root:                {0}" -f (Get-ProjectRoot))
    Write-ReportLine ("PowerShell version:          {0}" -f $PSVersionTable.PSVersion.ToString())
    Write-ReportLine ("Equipo:                      {0}" -f $env:COMPUTERNAME)
    Write-ReportLine ("Usuario:                     {0}" -f $env:USERNAME)

    $profiles = @(
        'Canales-youtube',
        'Podcast',
        'TV-Serie',
        'Music-Playlist',
        'Ambience-Video',
        'Ambience-Audio'
    )

    $steps = [System.Collections.Generic.List[object]]::new()

    # ------------------------------------------------------------
    # FASE 1 - TESTS AISLADOS EN DRY-RUN
    # ------------------------------------------------------------
    $steps.Add([pscustomobject]@{
        StepId      = '001'
        Category    = 'isolated-dryrun'
        DisplayName = 'test-trim-only | DryRun'
        Command     = "powershell -ExecutionPolicy Bypass -File `"$PSScriptRoot\test-trim-only.ps1`" -DryRun:`$true"
    }) | Out-Null

    $steps.Add([pscustomobject]@{
        StepId      = '002'
        Category    = 'isolated-dryrun'
        DisplayName = 'test-beets-only | DryRun'
        Command     = "powershell -ExecutionPolicy Bypass -File `"$PSScriptRoot\test-beets-only.ps1`" -DryRun:`$true"
    }) | Out-Null

    # ------------------------------------------------------------
    # FASE 2 - PROFILE TESTS EN DRY-RUN SIN BORRADO
    # ------------------------------------------------------------
    $stepIndex = 3
    foreach ($profile in $profiles) {
        $steps.Add([pscustomobject]@{
            StepId      = ('{0:D3}' -f $stepIndex)
            Category    = 'profile-dryrun-no-clear'
            DisplayName = "run-profile-test | $profile | ClearDownloads=false | DryRun=true"
            Command     = "powershell -ExecutionPolicy Bypass -File `"$PSScriptRoot\run-profile-test.ps1`" -ProfileName `"$profile`" -ClearDownloads:`$false -DryRun:`$true"
        }) | Out-Null
        $stepIndex++
    }

    # ------------------------------------------------------------
    # FASE 3 - PROFILE TESTS EN DRY-RUN CON BORRADO
    # ------------------------------------------------------------
    foreach ($profile in $profiles) {
        $steps.Add([pscustomobject]@{
            StepId      = ('{0:D3}' -f $stepIndex)
            Category    = 'profile-dryrun-clear'
            DisplayName = "run-profile-test | $profile | ClearDownloads=true | DryRun=true"
            Command     = "powershell -ExecutionPolicy Bypass -File `"$PSScriptRoot\run-profile-test.ps1`" -ProfileName `"$profile`" -ClearDownloads:`$true -DryRun:`$true"
        }) | Out-Null
        $stepIndex++
    }

    # ------------------------------------------------------------
    # FASE 4 - VALIDADOR Y E2E EN DRY-RUN
    # ------------------------------------------------------------
    $steps.Add([pscustomobject]@{
        StepId      = ('{0:D3}' -f $stepIndex)
        Category    = 'validator-dryrun'
        DisplayName = 'validate-downloads | DryRun'
        Command     = "powershell -ExecutionPolicy Bypass -File `"$PSScriptRoot\validate-downloads.ps1`" -DryRun:`$true"
    }) | Out-Null
    $stepIndex++

    $steps.Add([pscustomobject]@{
        StepId      = ('{0:D3}' -f $stepIndex)
        Category    = 'e2e-dryrun-no-clear'
        DisplayName = 'run-e2e | ClearDownloads=false | DryRun=true'
        Command     = "powershell -ExecutionPolicy Bypass -File `"$PSScriptRoot\run-e2e.ps1`" -ClearDownloads:`$false -DryRun:`$true"
    }) | Out-Null
    $stepIndex++

    $steps.Add([pscustomobject]@{
        StepId      = ('{0:D3}' -f $stepIndex)
        Category    = 'e2e-dryrun-clear'
        DisplayName = 'run-e2e | ClearDownloads=true | DryRun=true'
        Command     = "powershell -ExecutionPolicy Bypass -File `"$PSScriptRoot\run-e2e.ps1`" -ClearDownloads:`$true -DryRun:`$true"
    }) | Out-Null
    $stepIndex++

    # ------------------------------------------------------------
    # FASE 5 - TESTS AISLADOS REALES
    # ------------------------------------------------------------
    $steps.Add([pscustomobject]@{
        StepId      = ('{0:D3}' -f $stepIndex)
        Category    = 'isolated-real'
        DisplayName = 'test-trim-only | DryRun=false'
        Command     = "powershell -ExecutionPolicy Bypass -File `"$PSScriptRoot\test-trim-only.ps1`" -DryRun:`$false"
    }) | Out-Null
    $stepIndex++

    $steps.Add([pscustomobject]@{
        StepId      = ('{0:D3}' -f $stepIndex)
        Category    = 'isolated-real'
        DisplayName = 'test-beets-only | DryRun=false'
        Command     = "powershell -ExecutionPolicy Bypass -File `"$PSScriptRoot\test-beets-only.ps1`" -DryRun:`$false"
    }) | Out-Null
    $stepIndex++

    # ------------------------------------------------------------
    # FASE 6 - PROFILE TESTS REALES SIN BORRADO
    # ------------------------------------------------------------
    foreach ($profile in $profiles) {
        $steps.Add([pscustomobject]@{
            StepId      = ('{0:D3}' -f $stepIndex)
            Category    = 'profile-real-no-clear'
            DisplayName = "run-profile-test | $profile | ClearDownloads=false | DryRun=false"
            Command     = "powershell -ExecutionPolicy Bypass -File `"$PSScriptRoot\run-profile-test.ps1`" -ProfileName `"$profile`" -ClearDownloads:`$false -DryRun:`$false"
        }) | Out-Null
        $stepIndex++
    }

    # Validador tras perfiles reales sin borrado
    $steps.Add([pscustomobject]@{
        StepId      = ('{0:D3}' -f $stepIndex)
        Category    = 'validator-real-mid'
        DisplayName = 'validate-downloads | DryRun=false | tras perfiles reales sin borrado'
        Command     = "powershell -ExecutionPolicy Bypass -File `"$PSScriptRoot\validate-downloads.ps1`" -DryRun:`$false"
    }) | Out-Null
    $stepIndex++

    # ------------------------------------------------------------
    # FASE 7 - PROFILE TESTS REALES CON BORRADO
    # ------------------------------------------------------------
    foreach ($profile in $profiles) {
        $steps.Add([pscustomobject]@{
            StepId      = ('{0:D3}' -f $stepIndex)
            Category    = 'profile-real-clear'
            DisplayName = "run-profile-test | $profile | ClearDownloads=true | DryRun=false"
            Command     = "powershell -ExecutionPolicy Bypass -File `"$PSScriptRoot\run-profile-test.ps1`" -ProfileName `"$profile`" -ClearDownloads:`$true -DryRun:`$false"
        }) | Out-Null
        $stepIndex++
    }

    # Validador tras perfiles reales con borrado
    $steps.Add([pscustomobject]@{
        StepId      = ('{0:D3}' -f $stepIndex)
        Category    = 'validator-real-mid'
        DisplayName = 'validate-downloads | DryRun=false | tras perfiles reales con borrado'
        Command     = "powershell -ExecutionPolicy Bypass -File `"$PSScriptRoot\validate-downloads.ps1`" -DryRun:`$false"
    }) | Out-Null
    $stepIndex++

    # ------------------------------------------------------------
    # FASE 8 - E2E REAL
    # ------------------------------------------------------------
    $steps.Add([pscustomobject]@{
        StepId      = ('{0:D3}' -f $stepIndex)
        Category    = 'e2e-real-no-clear'
        DisplayName = 'run-e2e | ClearDownloads=false | DryRun=false'
        Command     = "powershell -ExecutionPolicy Bypass -File `"$PSScriptRoot\run-e2e.ps1`" -ClearDownloads:`$false -DryRun:`$false"
    }) | Out-Null
    $stepIndex++

    $steps.Add([pscustomobject]@{
        StepId      = ('{0:D3}' -f $stepIndex)
        Category    = 'validator-real-post-e2e'
        DisplayName = 'validate-downloads | DryRun=false | tras e2e real sin borrado'
        Command     = "powershell -ExecutionPolicy Bypass -File `"$PSScriptRoot\validate-downloads.ps1`" -DryRun:`$false"
    }) | Out-Null
    $stepIndex++

    $steps.Add([pscustomobject]@{
        StepId      = ('{0:D3}' -f $stepIndex)
        Category    = 'e2e-real-clear'
        DisplayName = 'run-e2e | ClearDownloads=true | DryRun=false'
        Command     = "powershell -ExecutionPolicy Bypass -File `"$PSScriptRoot\run-e2e.ps1`" -ClearDownloads:`$true -DryRun:`$false"
    }) | Out-Null
    $stepIndex++

    $steps.Add([pscustomobject]@{
        StepId      = ('{0:D3}' -f $stepIndex)
        Category    = 'validator-real-final'
        DisplayName = 'validate-downloads | DryRun=false | validación final'
        Command     = "powershell -ExecutionPolicy Bypass -File `"$PSScriptRoot\validate-downloads.ps1`" -DryRun:`$false"
    }) | Out-Null
    $stepIndex++

    # ------------------------------------------------------------
    # EJECUCIÓN
    # ------------------------------------------------------------
    Write-ReportSection 'PLAN DE EJECUCIÓN'
    Write-ReportLine ("Total de pasos planificados: {0}" -f $steps.Count)
    foreach ($step in $steps) {
        Write-ReportLine ("{0} | {1} | {2}" -f $step.StepId, $step.Category, $step.DisplayName)
    }

    $globalStart = Get-Date
    $okCount = 0
    $errorCount = 0

    foreach ($step in $steps) {
        $ok = Invoke-ChildTest -StepId $step.StepId -Category $step.Category -DisplayName $step.DisplayName -Command $step.Command
        if ($ok) {
            $okCount++
        }
        else {
            $errorCount++
        }
    }

    $globalEnd = Get-Date
    $globalDuration = [math]::Round(($globalEnd - $globalStart).TotalSeconds, 3)

    # ------------------------------------------------------------
    # RESUMEN FINAL
    # ------------------------------------------------------------
    Write-ReportSection 'RESUMEN FINAL GLOBAL'
    Write-ReportLine ("Inicio global:   {0}" -f $globalStart.ToString('yyyy-MM-dd HH:mm:ss'))
    Write-ReportLine ("Fin global:      {0}" -f $globalEnd.ToString('yyyy-MM-dd HH:mm:ss'))
    Write-ReportLine ("Duración global: {0} s" -f $globalDuration)
    Write-ReportLine ("Pasos totales:   {0}" -f $steps.Count)
    Write-ReportLine ("Correctos:       {0}" -f $okCount)
    Write-ReportLine ("Con error:       {0}" -f $errorCount)

    $failed = $script:ExecutionRows | Where-Object { $_.Status -ne 'OK' }
    if ($failed.Count -gt 0) {
        Write-ReportLine 'Pasos con error:'
        foreach ($row in $failed) {
            Write-ReportLine ("  - {0} | {1} | Exit={2}" -f $row.StepId, $row.DisplayName, $row.ExitCode)
        }
    }
    else {
        Write-ReportLine 'Todos los pasos terminaron correctamente.'
    }

    Write-ReportSection 'RUTAS IMPORTANTES PARA ANALISIS EXTERNO'
    Write-ReportLine ("Carpeta maestra de esta ejecución: {0}" -f $ctx.BaseDir)
    Write-ReportLine ("Reporte maestro:                  {0}" -f $reportPath)
    Write-ReportLine ("Main log maestro:                 {0}" -f $ctx.MainLog)
    Write-ReportLine ("Transcript maestro:               {0}" -f $ctx.TranscriptLog)
    Write-ReportLine ("CSV resumen:                      {0}" -f $csvSummaryPath)
    Write-ReportLine ("JSON resumen:                     {0}" -f $jsonSummaryPath)
    Write-ReportLine ("Logs root global:                 {0}" -f (Get-LogsRoot))
    Write-ReportLine 'Para enviar a otra IA: comprime la carpeta logs completa y adjunta además este report log.'

    # Exportes estructurados
    $script:ExecutionRows |
        Export-Csv -Path $csvSummaryPath -NoTypeInformation -Encoding UTF8

    $script:ExecutionRows |
        ConvertTo-Json -Depth 6 |
        Set-Content -Path $jsonSummaryPath -Encoding UTF8

    Write-TestLine -Context $ctx -Message 'Lanzador maestro completado.' -Level 'OK'
}
finally {
    Write-RelevantLogPaths -Context $ctx
    Write-Host ""
    Write-Host "Reporte maestro:"
    Write-Host $reportPath
    Write-Host ""
    Write-Host "Resumen CSV:"
    Write-Host $csvSummaryPath
    Write-Host ""
    Write-Host "Resumen JSON:"
    Write-Host $jsonSummaryPath
    Stop-TestLogging
}