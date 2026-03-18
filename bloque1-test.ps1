$LogFile = Join-Path (Get-Location) ("bloque1-music-playlist-" + (Get-Date -Format "yyyyMMdd-HHmmss") + ".log")

docker exec ytdl-sub sh -lc 'rm -rf /downloads/Music-Playlist/music-playlist-prueba' 2>&1 | Tee-Object -FilePath $LogFile -Append
docker exec ytdl-sub sh -lc 'rm -rf /tmp/ytdl-sub-working-directory/music-playlist-prueba-plcajstgncmdxgfdpc5aenevprzgcr-kut' 2>&1 | Tee-Object -FilePath $LogFile -Append
docker exec ytdl-sub sh -lc 'find /config/logs -maxdepth 1 -type f -name "*.music-playlist-prueba-plcajstgncmdxgfdpc5aenevprzgcr-kut.*.log" -delete' 2>&1 | Tee-Object -FilePath $LogFile -Append
docker exec beets-streaming2 sh -lc 'rm -f /config/musiclibrary.db /config/logs/beets-import.log' 2>&1 | Tee-Object -FilePath $LogFile -Append

powershell.exe -ExecutionPolicy Bypass -File ".\test-e2e-perfiles-subscriptions.ps1" 2>&1 | Tee-Object -FilePath $LogFile -Append

docker exec ytdl-sub sh -lc 'echo "[COUNT MP3]"; if [ -d /downloads/Music-Playlist/music-playlist-prueba ]; then find /downloads/Music-Playlist/music-playlist-prueba -maxdepth 1 -type f -name "*.mp3" | wc -l; else echo 0; fi' 2>&1 | Tee-Object -FilePath $LogFile -Append
docker exec ytdl-sub sh -lc 'echo "[ULTIMO LOG MUSIC]"; ls -1t /config/logs/*.music-playlist-prueba-*.log 2>/dev/null | head -n 1 || true' 2>&1 | Tee-Object -FilePath $LogFile -Append

Write-Output $LogFile | Tee-Object -FilePath $LogFile -Append