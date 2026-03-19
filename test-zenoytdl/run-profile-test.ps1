param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$ProfileName,

    [Parameter(Position = 1)]
    [string]$ClearDownloads = 'false',

    [Parameter(Position = 2)]
    [string]$DryRun = 'false'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. "$PSScriptRoot\_shared.ps1"

function ConvertTo-BooleanStrict {
    param(
        [Parameter(Mandatory = $true)]
        [AllowNull()]
        [object]$Value,

        [Parameter(Mandatory = $true)]
        [string]$ParameterName
    )

    if ($Value -is [bool]) { return [bool]$Value }
    if ($null -eq $Value) { throw "El parámetro '$ParameterName' no puede ser null." }

    $text = $Value.ToString().Trim().ToLowerInvariant()
    switch ($text) {
        'true'  { return $true }
        'false' { return $false }
        '1'     { return $true }
        '0'     { return $false }
        'yes'   { return $true }
        'no'    { return $false }
        'y'     { return $true }
        'n'     { return $false }
        default { throw "Valor no válido para '$ParameterName': '$Value'. Usa true/false, 1/0, yes/no." }
    }
}

$ClearDownloadsBool = ConvertTo-BooleanStrict -Value $ClearDownloads -ParameterName 'ClearDownloads'
$DryRunBool = ConvertTo-BooleanStrict -Value $DryRun -ParameterName 'DryRun'

Assert-ValidProfileName -ProfileName $ProfileName
$ctx = New-TestExecutionContext -TestName 'run-profile-test'
Start-TestLogging -Context $ctx

try {
    Write-TestSection -Context $ctx -Title 'Inicio lanzador de perfil'
    Write-TestLine -Context $ctx -Message "Perfil: $ProfileName"
    Write-TestLine -Context $ctx -Message "ClearDownloads: $ClearDownloadsBool"
    Write-TestLine -Context $ctx -Message "DryRun: $DryRunBool"
    Write-TestLine -Context $ctx -Message "Project root: $(Get-ProjectRoot)"

    if ($ClearDownloadsBool) {
        Write-TestSection -Context $ctx -Title 'Limpieza previa solicitada'
        Write-TestLine -Context $ctx -Message "Se ejecutará clean-windows-environment.ps1 solo para el perfil: $ProfileName" -Level 'INFO'

        $cleanScript = Join-Path $PSScriptRoot 'clean-windows-environment.ps1'
        if (-not (Test-Path $cleanScript)) {
            throw "No existe el script de limpieza requerido: $cleanScript"
        }

        Invoke-LoggedExpression `
            -Context $ctx `
            -Expression ("powershell -ExecutionPolicy Bypass -File `"{0}`" -ProfileName `"{1}`"" -f $cleanScript, $ProfileName) `
            -Label 'clean-windows-environment'
    }
    else {
        Write-TestLine -Context $ctx -Message 'No se ejecuta limpieza previa.' -Level 'INFO'
    }

    Reset-WorkingState -Context $ctx
    Invoke-GenerationPhase -Context $ctx -Profiles @($ProfileName)
    Filter-RunsetToProfiles -Context $ctx -Profiles @($ProfileName)

    $filteredRunsetPath = Get-FilteredRunsetPath
    $hasFilteredRunsetEntries = Test-FilteredRunsetHasEntries -Path $filteredRunsetPath

    if ($ProfileName -in @('Ambience-Video', 'Ambience-Audio')) {
        Copy-TrimScriptToContainer -Context $ctx
    }

    Invoke-RunsetExecution -Context $ctx -DryRun:$DryRunBool
    Promote-PendingState -Context $ctx -DryRun:$DryRunBool -HasEntries:$hasFilteredRunsetEntries

    if (-not $DryRunBool) {
        if (-not $hasFilteredRunsetEntries) {
            Write-TestLine -Context $ctx -Message 'No hay entradas reales en el runset filtrado; se omite cualquier postproceso.' -Level 'WARN'
        }
        else {
            switch ($ProfileName) {
                'Music-Playlist' { Invoke-MusicPostprocess -Context $ctx }
                'Ambience-Video' { Invoke-AmbiencePostprocess -Context $ctx -ProfileName $ProfileName }
                'Ambience-Audio' { Invoke-AmbiencePostprocess -Context $ctx -ProfileName $ProfileName }
                default { Write-TestLine -Context $ctx -Message 'Este perfil no requiere postproceso específico.' -Level 'INFO' }
            }
        }
    }

    Collect-RelevantContainerLogs -Context $ctx
    Write-TestSection -Context $ctx -Title 'Fin lanzador de perfil'
    Write-TestLine -Context $ctx -Message 'Ejecución completada correctamente.' -Level 'OK'
}
finally {
    Write-RelevantLogPaths -Context $ctx
    Stop-TestLogging
}
