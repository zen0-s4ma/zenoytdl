$LogFile = Join-Path (Get-Location) ("bloque2-music-playlist-" + (Get-Date -Format "yyyyMMdd-HHmmss") + ".log")

powershell.exe -ExecutionPolicy Bypass -File ".\test-e2e-perfiles-subscriptions.ps1" 2>&1 | Tee-Object -FilePath $LogFile -Append

docker exec ytdl-sub sh -lc 'echo "[COUNT MP3 FINAL]"; if [ -d /downloads/Music-Playlist/music-playlist-prueba ]; then find /downloads/Music-Playlist/music-playlist-prueba -maxdepth 1 -type f -name "*.mp3" | wc -l; else echo 0; fi' 2>&1 | Tee-Object -FilePath $LogFile -Append
docker exec ytdl-sub sh -lc 'echo "[CONTEO already been recorded]"; latest=$(ls -1t /config/logs/*.music-playlist-prueba-*.log 2>/dev/null | head -n 1); if [ -n "$latest" ]; then grep -c "has already been recorded in the archive" "$latest" || true; else echo 0; fi' 2>&1 | Tee-Object -FilePath $LogFile -Append
docker exec beets-streaming2 sh -lc 'echo "[ULTIMAS 80 LINEAS BEETS]"; tail -n 80 /config/logs/beets-import.log 2>/dev/null || true' 2>&1 | Tee-Object -FilePath $LogFile -Append

Write-Output $LogFile | Tee-Object -FilePath $LogFile -Append