Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Invoke-InNewTerminal {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ScriptPath,

        [string[]]$Arguments = @()
    )

    $resolvedScript = (Resolve-Path $ScriptPath).Path
    $workingDir = (Get-Location).Path
    $parentPid = $PID

    $argText = if ($Arguments.Count -gt 0) {
        ($Arguments | ForEach-Object {
            if ($_ -match '\s') { '"{0}"' -f $_ } else { $_ }
        }) -join ' '
    }
    else {
        ''
    }

    $safeName = [IO.Path]::GetFileNameWithoutExtension($resolvedScript)
    $guid = [guid]::NewGuid().ToString('N')
    $signalFile = Join-Path $env:TEMP ("zeno-finished-{0}-{1}.signal" -f $safeName, $guid)
    $wrapperFile = Join-Path $env:TEMP ("zeno-wrapper-{0}-{1}.ps1" -f $safeName, $guid)

    $windowTitle = "RUNNING :: $(Split-Path $resolvedScript -Leaf) $argText"

    $wrapperContent = @"
`$Host.UI.RawUI.WindowTitle = '$windowTitle'
Set-Location '$workingDir'

`$exitCode = 1

try {
    & '$resolvedScript' $argText
    if (`$null -ne `$LASTEXITCODE) {
        `$exitCode = `$LASTEXITCODE
    }
    else {
        `$exitCode = 0
    }
}
catch {
    `$exitCode = 1
    Write-Host ''
    Write-Host 'ERROR durante la ejecución:' -ForegroundColor Red
    Write-Host (`$_.Exception.Message) -ForegroundColor Red
    Write-Host ''
    Write-Host 'DETALLE COMPLETO:' -ForegroundColor Yellow
    Write-Host `$_
}
finally {
    try {
        'EXITCODE=' + `$exitCode | Set-Content -Path '$signalFile' -Encoding UTF8 -Force
    }
    catch {
        Write-Host 'No se pudo escribir el signal file.' -ForegroundColor Red
        Write-Host `$_
    }
}

Write-Host ''
Write-Host '============================================================'
if (`$exitCode -eq 0) {
    Write-Host 'Proceso terminado correctamente.' -ForegroundColor Green
}
else {
    Write-Host ('Proceso terminado con código: {0}' -f `$exitCode) -ForegroundColor Red
}
Write-Host 'Esta ventana queda en pausa.'
Write-Host 'Pulsa ENTER para cerrarla.'
Write-Host '============================================================'
Read-Host | Out-Null
exit `$exitCode
"@

    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($wrapperFile, $wrapperContent, $utf8NoBom)

    $proc = Start-Process powershell.exe `
        -ArgumentList @(
            '-NoLogo',
            '-NoExit',
            '-ExecutionPolicy', 'Bypass',
            '-File', $wrapperFile
        ) `
        -WorkingDirectory $workingDir `
        -PassThru

    Start-Sleep -Milliseconds 500

    try {
        Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class Win32Focus {
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);
}
"@ -ErrorAction SilentlyContinue | Out-Null

        $parentProcess = Get-Process -Id $parentPid -ErrorAction Stop
        if ($parentProcess.MainWindowHandle -ne 0) {
            [Win32Focus]::SetForegroundWindow($parentProcess.MainWindowHandle) | Out-Null
        }
    }
    catch {
        # Si no se puede devolver el foco, no rompemos la ejecución.
    }

    while (-not (Test-Path $signalFile)) {
        Start-Sleep -Milliseconds 300

        if ($proc.HasExited) {
            Remove-Item -Path $wrapperFile -Force -ErrorAction SilentlyContinue
            throw "La ventana de '$resolvedScript' se cerró antes de generar la señal de fin."
        }
    }

    $signalContent = Get-Content -Path $signalFile -ErrorAction Stop
    Remove-Item -Path $signalFile -Force -ErrorAction SilentlyContinue
    Remove-Item -Path $wrapperFile -Force -ErrorAction SilentlyContinue

    $exitCode = 1
    if ($signalContent -match '^EXITCODE=(\d+)$') {
        $exitCode = [int]$Matches[1]
    }

    if ($exitCode -ne 0) {
        throw "La ejecución de '$resolvedScript' terminó con código $exitCode."
    }
}

function Write-Section {
    param(
        [string]$Title
    )

    Write-Host ''
    Write-Host ('=' * 80) -ForegroundColor DarkGray
    Write-Host $Title -ForegroundColor Cyan
    Write-Host ('=' * 80) -ForegroundColor DarkGray
}

function Format-ArgumentsText {
    param(
        [string[]]$Arguments
    )

    if ($null -eq $Arguments -or $Arguments.Count -eq 0) {
        return '(sin argumentos)'
    }

    return ($Arguments -join ' ')
}

$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$masterLog = Join-Path (Get-Location) ("___master-{0}.log" -f $timestamp)

Start-Transcript -Path $masterLog -Force

try {
    Write-Host "Master log: $masterLog" -ForegroundColor Yellow
    Write-Host ''

    $tasks = @(
        [pscustomobject]@{
            Name       = 'Limpieza previa del entorno'
            ScriptPath = '.\test-zenoytdl\clean-windows-environment.ps1'
            Arguments  = @('-CleanLogs')
        }
        [pscustomobject]@{
            Name       = 'Test aislado beets'
            ScriptPath = '.\test-zenoytdl\test-beets-only.ps1'
            Arguments  = @('-DryRun:$false')
        }
        [pscustomobject]@{
            Name       = 'Test aislado trim'
            ScriptPath = '.\test-zenoytdl\test-trim-only.ps1'
            Arguments  = @('-DryRun:$false')
        }
        [pscustomobject]@{
            Name       = 'Canales-youtube pasada 1'
            ScriptPath = '.\test-zenoytdl\run-profile-test.ps1'
            Arguments  = @('-ProfileName', 'Canales-youtube', '-ClearDownloads:$false', '-DryRun:$false')
        }
        [pscustomobject]@{
            Name       = 'Podcast pasada 1'
            ScriptPath = '.\test-zenoytdl\run-profile-test.ps1'
            Arguments  = @('-ProfileName', 'Podcast', '-ClearDownloads:$false', '-DryRun:$false')
        }
        [pscustomobject]@{
            Name       = 'TV-Serie pasada 1'
            ScriptPath = '.\test-zenoytdl\run-profile-test.ps1'
            Arguments  = @('-ProfileName', 'TV-Serie', '-ClearDownloads:$false', '-DryRun:$false')
        }
        [pscustomobject]@{
            Name       = 'Music-Playlist pasada 1'
            ScriptPath = '.\test-zenoytdl\run-profile-test.ps1'
            Arguments  = @('-ProfileName', 'Music-Playlist', '-ClearDownloads:$false', '-DryRun:$false')
        }
        [pscustomobject]@{
            Name       = 'Ambience-Video pasada 1'
            ScriptPath = '.\test-zenoytdl\run-profile-test.ps1'
            Arguments  = @('-ProfileName', 'Ambience-Video', '-ClearDownloads:$false', '-DryRun:$false')
        }
        [pscustomobject]@{
            Name       = 'Ambience-Audio pasada 1'
            ScriptPath = '.\test-zenoytdl\run-profile-test.ps1'
            Arguments  = @('-ProfileName', 'Ambience-Audio', '-ClearDownloads:$false', '-DryRun:$false')
        }
        [pscustomobject]@{
            Name       = 'Canales-youtube pasada 2'
            ScriptPath = '.\test-zenoytdl\run-profile-test.ps1'
            Arguments  = @('-ProfileName', 'Canales-youtube', '-ClearDownloads:$false', '-DryRun:$false')
        }
        [pscustomobject]@{
            Name       = 'Podcast pasada 2'
            ScriptPath = '.\test-zenoytdl\run-profile-test.ps1'
            Arguments  = @('-ProfileName', 'Podcast', '-ClearDownloads:$false', '-DryRun:$false')
        }
        [pscustomobject]@{
            Name       = 'TV-Serie pasada 2'
            ScriptPath = '.\test-zenoytdl\run-profile-test.ps1'
            Arguments  = @('-ProfileName', 'TV-Serie', '-ClearDownloads:$false', '-DryRun:$false')
        }
        [pscustomobject]@{
            Name       = 'Music-Playlist pasada 2'
            ScriptPath = '.\test-zenoytdl\run-profile-test.ps1'
            Arguments  = @('-ProfileName', 'Music-Playlist', '-ClearDownloads:$false', '-DryRun:$false')
        }
        [pscustomobject]@{
            Name       = 'Ambience-Video pasada 2'
            ScriptPath = '.\test-zenoytdl\run-profile-test.ps1'
            Arguments  = @('-ProfileName', 'Ambience-Video', '-ClearDownloads:$false', '-DryRun:$false')
        }
        [pscustomobject]@{
            Name       = 'Ambience-Audio pasada 2'
            ScriptPath = '.\test-zenoytdl\run-profile-test.ps1'
            Arguments  = @('-ProfileName', 'Ambience-Audio', '-ClearDownloads:$false', '-DryRun:$false')
        }
    )

    $totalTasks = $tasks.Count
    $completed = 0
    $okCount = 0
    $failedCount = 0
    $startedAt = Get-Date

    Write-Section "INICIO RUN MASTER TESTS"
    Write-Host ("Total de pasos planificados: {0}" -f $totalTasks) -ForegroundColor Yellow
    Write-Host "Orden previsto:" -ForegroundColor Yellow
    for ($i = 0; $i -lt $tasks.Count; $i++) {
        Write-Host ("  [{0}/{1}] {2}" -f ($i + 1), $totalTasks, $tasks[$i].Name) -ForegroundColor DarkGray
    }

    foreach ($task in $tasks) {
        $currentIndex = $completed + 1
        $remainingAfterThis = $totalTasks - $currentIndex

        Write-Section ("LANZANDO [{0}/{1}] {2}" -f $currentIndex, $totalTasks, $task.Name)
        Write-Host ("Script     : {0}" -f $task.ScriptPath) -ForegroundColor Gray
        Write-Host ("Argumentos : {0}" -f (Format-ArgumentsText -Arguments $task.Arguments)) -ForegroundColor Gray
        Write-Host ("Completados: {0}" -f $completed) -ForegroundColor Gray
        Write-Host ("Pendientes : {0}" -f ($totalTasks - $completed)) -ForegroundColor Gray

        $taskStartedAt = Get-Date

        try {
            Invoke-InNewTerminal -ScriptPath $task.ScriptPath -Arguments $task.Arguments

            $completed++
            $okCount++

            $taskDuration = (Get-Date) - $taskStartedAt
            $elapsed = (Get-Date) - $startedAt

            Write-Host ''
            Write-Host ("[OK] [{0}/{1}] {2}" -f $completed, $totalTasks, $task.Name) -ForegroundColor Green
            Write-Host ("Duración paso : {0:hh\:mm\:ss}" -f $taskDuration) -ForegroundColor Green
            Write-Host ("Acumulado OK  : {0}" -f $okCount) -ForegroundColor Green
            Write-Host ("Fallos        : {0}" -f $failedCount) -ForegroundColor Green
            Write-Host ("Quedan        : {0}" -f ($totalTasks - $completed)) -ForegroundColor Yellow
            Write-Host ("Tiempo total  : {0:hh\:mm\:ss}" -f $elapsed) -ForegroundColor Yellow
        }
        catch {
            $completed++
            $failedCount++

            $taskDuration = (Get-Date) - $taskStartedAt
            $elapsed = (Get-Date) - $startedAt

            Write-Host ''
            Write-Host ("[ERROR] [{0}/{1}] {2}" -f $completed, $totalTasks, $task.Name) -ForegroundColor Red
            Write-Host ("Duración paso : {0:hh\:mm\:ss}" -f $taskDuration) -ForegroundColor Red
            Write-Host ("Acumulado OK  : {0}" -f $okCount) -ForegroundColor Yellow
            Write-Host ("Fallos        : {0}" -f $failedCount) -ForegroundColor Red
            Write-Host ("Quedaban      : {0}" -f $remainingAfterThis) -ForegroundColor Yellow
            Write-Host ("Tiempo total  : {0:hh\:mm\:ss}" -f $elapsed) -ForegroundColor Yellow
            Write-Host ''
            Write-Host 'Pendiente desde este punto:' -ForegroundColor Yellow

            for ($j = $currentIndex; $j -lt $tasks.Count; $j++) {
                Write-Host ("  - {0}" -f $tasks[$j].Name) -ForegroundColor DarkYellow
            }

            throw
        }
    }

    $totalElapsed = (Get-Date) - $startedAt

    Write-Section "RESUMEN FINAL"
    Write-Host ("Pasos totales : {0}" -f $totalTasks) -ForegroundColor Yellow
    Write-Host ("Correctos     : {0}" -f $okCount) -ForegroundColor Green
    Write-Host ("Fallidos      : {0}" -f $failedCount) -ForegroundColor Red
    Write-Host ("Tiempo total  : {0:hh\:mm\:ss}" -f $totalElapsed) -ForegroundColor Cyan
    Write-Host "Estado final  : OK" -ForegroundColor Green
}
finally {
    Stop-Transcript
    Write-Host ""
    Write-Host "Log maestro generado en:" -ForegroundColor Yellow
    Write-Host $masterLog -ForegroundColor Yellow
}