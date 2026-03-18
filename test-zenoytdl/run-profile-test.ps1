Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. "$PSScriptRoot\_shared.ps1"

param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$ProfileName,

    [Parameter(Position = 1)]
    [bool]$ClearDownloads = $false,

    [Parameter(Position = 2)]
    [bool]$DryRun = $false
)

Assert-ValidProfileName -ProfileName $ProfileName
$ctx = New-TestExecutionContext -TestName 'run-profile-test'
Start-TestLogging -Context $ctx

try {
    Write-TestSection -Context $ctx -Title 'Inicio lanzador de perfil'
    Write-TestLine -Context $ctx -Message "Perfil: $ProfileName"
    Write-TestLine -Context $ctx -Message "ClearDownloads: $ClearDownloads"
    Write-TestLine -Context $ctx -Message "DryRun: $DryRun"
    Write-TestLine -Context $ctx -Message "Project root: $(Get-ProjectRoot)"

    if ($ClearDownloads) {
        Remove-ProfileDownloads -Context $ctx -Profiles @($ProfileName)
    } else {
        Write-TestLine -Context $ctx -Message 'No se borran descargas previas.' -Level 'INFO'
    }

    Reset-WorkingState -Context $ctx
    Invoke-GenerationPhase -Context $ctx
    Filter-RunsetToProfiles -Context $ctx -Profiles @($ProfileName)

    if ($ProfileName -in @('Ambience-Video','Ambience-Audio')) {
        Copy-TrimScriptToContainer -Context $ctx
    }

    Invoke-RunsetExecution -Context $ctx -DryRun:$DryRun
    Promote-PendingState -Context $ctx -DryRun:$DryRun

    if (-not $DryRun) {
        switch ($ProfileName) {
            'Music-Playlist' { Invoke-MusicPostprocess -Context $ctx }
            'Ambience-Video' { Invoke-AmbiencePostprocess -Context $ctx -ProfileName $ProfileName }
            'Ambience-Audio' { Invoke-AmbiencePostprocess -Context $ctx -ProfileName $ProfileName }
            default { Write-TestLine -Context $ctx -Message 'Este perfil no requiere postproceso específico.' -Level 'INFO' }
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
