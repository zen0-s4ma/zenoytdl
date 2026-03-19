Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$masterLog = Join-Path (Get-Location) ("___master-{0}.log" -f $timestamp)

Start-Transcript -Path $masterLog -Force

try {
    Write-Host "Master log: $masterLog"
    Write-Host ""

    # ============================================================
    # PASO 0) LIMPIEZA PREVIA DEL ENTORNO
    # ============================================================
    powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\clean-windows-environment.ps1

    # ============================================================
    # PRUEBAS DE PERFILES — ORDEN PEDIDO
    # De cada perfil:
    #   1) sin clean + con dryrun
    #   2) sin clean + sin dryrun
    # Al final:
    #   - test-beets-only
    #   - test-trim-only
    # ============================================================

    # ------------------------------------------------------------
    # 1) Canales-youtube
    # ------------------------------------------------------------
    powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\run-profile-test.ps1 -ProfileName "Canales-youtube" -ClearDownloads:$false -DryRun:$true
    powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\run-profile-test.ps1 -ProfileName "Canales-youtube" -ClearDownloads:$false -DryRun:$false

    # ------------------------------------------------------------
    # 2) Podcast
    # ------------------------------------------------------------
    powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\run-profile-test.ps1 -ProfileName "Podcast" -ClearDownloads:$false -DryRun:$true
    powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\run-profile-test.ps1 -ProfileName "Podcast" -ClearDownloads:$false -DryRun:$false

    # ------------------------------------------------------------
    # 3) TV-Serie
    # ------------------------------------------------------------
    powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\run-profile-test.ps1 -ProfileName "TV-Serie" -ClearDownloads:$false -DryRun:$true
    powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\run-profile-test.ps1 -ProfileName "TV-Serie" -ClearDownloads:$false -DryRun:$false

    # ------------------------------------------------------------
    # 4) Music-Playlist
    # ------------------------------------------------------------
    powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\run-profile-test.ps1 -ProfileName "Music-Playlist" -ClearDownloads:$false -DryRun:$true
    powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\run-profile-test.ps1 -ProfileName "Music-Playlist" -ClearDownloads:$false -DryRun:$false

    # ------------------------------------------------------------
    # 5) Ambience-Video
    # ------------------------------------------------------------
    powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\run-profile-test.ps1 -ProfileName "Ambience-Video" -ClearDownloads:$false -DryRun:$true
    powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\run-profile-test.ps1 -ProfileName "Ambience-Video" -ClearDownloads:$false -DryRun:$false

    # ------------------------------------------------------------
    # 6) Ambience-Audio
    # ------------------------------------------------------------
    powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\run-profile-test.ps1 -ProfileName "Ambience-Audio" -ClearDownloads:$false -DryRun:$true
    powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\run-profile-test.ps1 -ProfileName "Ambience-Audio" -ClearDownloads:$false -DryRun:$false

    # ------------------------------------------------------------
    # 7) test-beets-only
    # ------------------------------------------------------------
    powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\test-beets-only.ps1 -DryRun:$false

    # ------------------------------------------------------------
    # 8) test-trim-only
    # ------------------------------------------------------------
    powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\test-trim-only.ps1 -DryRun:$false
}
finally {
    Stop-Transcript
    Write-Host ""
    Write-Host "Log maestro generado en:"
    Write-Host $masterLog
}