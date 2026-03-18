Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. "$PSScriptRoot\_shared.ps1"

param(
    [Parameter(Position = 0)]
    [bool]$ClearDownloads = $false,

    [Parameter(Position = 1)]
    [bool]$DryRun = $false
)

$ctx = New-TestExecutionContext -TestName 'run-e2e'
Start-TestLogging -Context $ctx

try {
    Write-TestSection -Context $ctx -Title 'Inicio lanzador E2E de todos los perfiles'
    Write-TestLine -Context $ctx -Message "ClearDownloads: $ClearDownloads"
    Write-TestLine -Context $ctx -Message "DryRun: $DryRun"

    foreach ($profile in (Get-AllProfileNames)) {
        Write-TestSection -Context $ctx -Title ("Lanzando perfil: $profile")
        $cmd = "powershell -ExecutionPolicy Bypass -File `"$PSScriptRoot\run-profile-test.ps1`" -ProfileName `"$profile`" -ClearDownloads:`$$ClearDownloads -DryRun:`$$DryRun"
        # Construcción segura de bool para PowerShell hijo
        $cmd = "powershell -ExecutionPolicy Bypass -File `"$PSScriptRoot\run-profile-test.ps1`" -ProfileName `"$profile`" -ClearDownloads:`$" + $ClearDownloads.ToString().ToLower() + " -DryRun:`$" + $DryRun.ToString().ToLower()
        Invoke-LoggedExpression -Context $ctx -Expression $cmd -Label ('child-' + $profile)
    }

    Write-TestSection -Context $ctx -Title 'Validación global al finalizar E2E'
    $validateCmd = "powershell -ExecutionPolicy Bypass -File `"$PSScriptRoot\validate-downloads.ps1`" -DryRun:`$" + $DryRun.ToString().ToLower()
    Invoke-LoggedExpression -Context $ctx -Expression $validateCmd -Label 'validate-downloads'

    Write-TestLine -Context $ctx -Message 'E2E completado correctamente.' -Level 'OK'
}
finally {
    Write-RelevantLogPaths -Context $ctx
    Stop-TestLogging
}
