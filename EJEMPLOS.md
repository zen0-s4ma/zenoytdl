# ejemplos.md

# Colección de ejemplos de uso

Este documento reúne muchos ejemplos prácticos del proyecto para ayudarte a:
- modelar perfiles y suscripciones;
- generar YAML válidos;
- lanzar ejecuciones completas o parciales;
- entender el runset inteligente;
- probar overrides por fuente;
- validar resultados y depurar problemas.

> Nota importante sobre URLs  
> Algunos ejemplos usan URLs inventadas o plausibles para mostrar casuísticas. Al final del documento hay un inventario explícito de URLs ficticias.

---

# 1. Convenciones usadas en los ejemplos

## 1.1. Rutas habituales

Ruta de configuración:

```powershell
E:\Docker_folders\streaming2\ytdl-sub\config
```

Ruta host de descargas:

```powershell
E:\Docker_folders\ydtl-custom-downloads
```

Contenedores habituales:

- `ytdl-sub`
- `beets-streaming2`

## 1.2. Ficheros principales

- `profiles-custom.yml`
- `subscription-custom.yml`
- `generate-ytdl-config.py`
- `prepare-subscriptions-runset.py`
- `config.generated.yaml`
- `subscriptions.generated.yaml`
- `subscriptions.runset.yaml`
- `beets.music-playlist.yaml`
- `clean-music-filenames.ps1`
- `trim-ambience-video.py`

## 1.3. Patrón mínimo de ejecución

Casi todos los workflows parten de esta base:

```powershell
cd E:\Docker_folders\streaming2\ytdl-sub\config
python .\generate-ytdl-config.py
python .\prepare-subscriptions-runset.py
docker cp .\trim-ambience-video.py ytdl-sub:/tmp/trim-ambience-video.py
docker exec ytdl-sub sh -lc 'ytdl-sub --config /config/config.generated.yaml sub /config/subscriptions.runset.yaml'
```

---

# 2. Ejemplos básicos

## Ejemplo 01 — Regenerar YAML sin descargar nada

Objetivo: comprobar que el modelo declarativo compila correctamente.

### Qué tocas
Ningún fichero de salida multimedia.

### Cómo lanzarlo

```powershell
cd E:\Docker_folders\streaming2\ytdl-sub\config
python .\generate-ytdl-config.py
```

### Qué esperas
- `config.generated.yaml` actualizado
- `subscriptions.generated.yaml` actualizado
- `beets.music-playlist.yaml` solo si hay perfil `music-playlist`

---

## Ejemplo 02 — Preparar runset inteligente sin ejecutar descarga

Objetivo: ver qué suscripciones tocaría ejecutar y cuáles saltaría.

### Cómo lanzarlo

```powershell
cd E:\Docker_folders\streaming2\ytdl-sub\config
python .\generate-ytdl-config.py
python .\prepare-subscriptions-runset.py
Get-Content .\subscriptions.runset.yaml
```

### Qué esperas
- se genera `subscriptions.runset.yaml`;
- aparecen decisiones tipo `RUN` o `SKIP`;
- se actualiza `.recent-items-state.pending.json`.

---

## Ejemplo 03 — Lanzar todo el proyecto completo

Objetivo: workflow estándar end-to-end.

### Cómo lanzarlo

```powershell
cd E:\Docker_folders\streaming2\ytdl-sub\config
python .\generate-ytdl-config.py
python .\prepare-subscriptions-runset.py
docker cp .\trim-ambience-video.py ytdl-sub:/tmp/trim-ambience-video.py
docker exec ytdl-sub sh -lc 'ytdl-sub --config /config/config.generated.yaml sub /config/subscriptions.runset.yaml'
if (Test-Path '.\.recent-items-state.pending.json') {
  Move-Item '.\.recent-items-state.pending.json' '.\.recent-items-state.json' -Force
}
```

### Después
Para `music-playlist` añade:

```powershell
powershell.exe -ExecutionPolicy Bypass -File ".\clean-music-filenames.ps1" -TargetDir "E:\Docker_folders\ydtl-custom-downloads\Music-Playlist\music-playlist-prueba"
docker exec beets-streaming2 sh -lc 'beet -v -c /config/beets.music-playlist.yaml import -s -q /downloads/Music-Playlist/music-playlist-prueba'
```

---

## Ejemplo 04 — Generar solo un perfil

Objetivo: compilar únicamente presets y suscripciones de un `profile_type`.

### Cómo lanzarlo

```powershell
cd E:\Docker_folders\streaming2\ytdl-sub\config
python .\generate-ytdl-config.py --only-profile music-playlist
```

### Casos útiles
- aislar un perfil roto;
- acelerar iteraciones;
- comprobar el YAML de una sola familia funcional.

---

## Ejemplo 05 — Limpiar locks y working directory antes de empezar

Objetivo: ejecución más limpia en pruebas.

### Cómo lanzarlo

```powershell
docker exec ytdl-sub sh -lc 'pkill -f ytdl-sub 2>/dev/null || true'
docker exec ytdl-sub sh -lc 'find /tmp -maxdepth 1 -type f \( -name "ytdl-sub*.lock" -o -name "*.lock" \) -print -delete 2>/dev/null || true'
docker exec ytdl-sub sh -lc 'rm -rf /tmp/ytdl-sub-working-directory/* 2>/dev/null || true'
docker exec ytdl-sub sh -lc 'rm -f /tmp/trim-ambience-video.py /tmp/trim-ambience-media.py 2>/dev/null || true'
```

---

# 3. Ejemplos de configuración por perfil

## Ejemplo 06 — Canal de YouTube simple en MP4 720p

### `subscription-custom.yml`

```yaml
subscriptions:
  - profile_name: Canales-youtube
    custom_name: geopolitica-diaria
    sources:
      - url: https://www.youtube.com/@GeoPoliticaDiaria/videos
        max_items: 3
        quality: 720p
        format: mp4
```

### Cómo lanzarlo

```powershell
python .\generate-ytdl-config.py
python .\prepare-subscriptions-runset.py
docker exec ytdl-sub sh -lc 'ytdl-sub --config /config/config.generated.yaml sub /config/subscriptions.runset.yaml'
```

### Resultado esperado
- carpeta raíz en `/downloads/Canales-youtube/geopolitica-diaria`;
- estructura tipo serie/temporada;
- solo recientes, máximo 3;
- thumbnails embebidos si aplica.

---

## Ejemplo 07 — Canal de YouTube en MKV

```yaml
subscriptions:
  - profile_name: Canales-youtube
    custom_name: informes-largos
    sources:
      - url: https://www.youtube.com/@InformesLargos/videos
        max_items: 5
        quality: 1080p
        format: mkv
```

### Cómo lanzarlo

```powershell
python .\generate-ytdl-config.py
python .\prepare-subscriptions-runset.py
docker exec ytdl-sub sh -lc 'ytdl-sub --config /config/config.generated.yaml sub /config/subscriptions.runset.yaml'
```

---

## Ejemplo 08 — Podcast desde canal, convertido a MP3

```yaml
subscriptions:
  - profile_name: Podcast
    custom_name: entrevistas-tech
    sources:
      - url: https://www.youtube.com/@EntrevistasTech/videos
        max_items: 10
        min_duration: 8m
        quality: best
        format: mp3
```

### Cómo lanzarlo

```powershell
python .\generate-ytdl-config.py
python .\prepare-subscriptions-runset.py
docker exec ytdl-sub sh -lc 'ytdl-sub --config /config/config.generated.yaml sub /config/subscriptions.runset.yaml'
```

### Resultado esperado
- salida en `/downloads/Podcast/entrevistas-tech/entrevistastech`;
- audio extraído a mp3;
- `Only Recent` + `Filter Duration`.

---

## Ejemplo 09 — Podcast desde playlist

```yaml
subscriptions:
  - profile_name: Podcast
    custom_name: estrategia-semanal
    sources:
      - url: https://www.youtube.com/playlist?list=PLFAKEPODCAST001
        max_items: 20
        min_duration: 15m
        quality: best
        format: mp3
```

### Cómo lanzarlo

```powershell
python .\generate-ytdl-config.py
python .\prepare-subscriptions-runset.py
docker exec ytdl-sub sh -lc 'ytdl-sub --config /config/config.generated.yaml sub /config/subscriptions.runset.yaml'
```

---

## Ejemplo 10 — TV-Serie con dos fuentes

```yaml
subscriptions:
  - profile_name: TV-Serie
    custom_name: historia-del-mundo
    sources:
      - url: https://www.youtube.com/@CanalHistoriaTotal/videos
        max_items: 4
        min_duration: 10m
        quality: 1080p
        format: mp4
      - url: https://www.youtube.com/@HistoriaExpandida/videos
        max_items: 4
        min_duration: 10m
        quality: 720p
        format: mkv
```

### Cómo lanzarlo

```powershell
python .\generate-ytdl-config.py
python .\prepare-subscriptions-runset.py
docker exec ytdl-sub sh -lc 'ytdl-sub --config /config/config.generated.yaml sub /config/subscriptions.runset.yaml'
```

### Resultado esperado
Ambas fuentes convergen bajo la misma serie lógica.

---

## Ejemplo 11 — Music playlist ilimitada

```yaml
subscriptions:
  - profile_name: Music-Playlist
    custom_name: synthwave-nocturno
    sources:
      - url: https://www.youtube.com/playlist?list=PLFAKEMUSIC777
        max_items: 0
        quality: best
        format: mp3
```

### Cómo lanzarlo

```powershell
python .\generate-ytdl-config.py
python .\prepare-subscriptions-runset.py
docker exec ytdl-sub sh -lc 'ytdl-sub --config /config/config.generated.yaml sub /config/subscriptions.runset.yaml'
powershell.exe -ExecutionPolicy Bypass -File ".\clean-music-filenames.ps1" -TargetDir "E:\Docker_folders\ydtl-custom-downloads\Music-Playlist\synthwave-nocturno"
docker exec beets-streaming2 sh -lc 'beet -v -c /config/beets.music-playlist.yaml import -s -q /downloads/Music-Playlist/synthwave-nocturno'
```

---

## Ejemplo 12 — Ambience video desde un single video

```yaml
subscriptions:
  - profile_name: Ambience-Video
    custom_name: lluvia-neon
    sources:
      - url: https://www.youtube.com/watch?v=FAKEAMBIENCE001
        quality: 1080p
        format: mp4
        min_duration: ''
        max_duration: 3h3m3s
        audio_quality: best
```

### Cómo lanzarlo

```powershell
python .\generate-ytdl-config.py
python .\prepare-subscriptions-runset.py
docker cp .\trim-ambience-video.py ytdl-sub:/tmp/trim-ambience-video.py
docker exec ytdl-sub sh -lc 'ytdl-sub --config /config/config.generated.yaml sub /config/subscriptions.runset.yaml'
docker exec ytdl-sub sh -lc 'python /tmp/trim-ambience-video.py --input "/downloads/Ambience-Video/lluvia-neon/fakeambience001.mp4" --max-duration 3h3m3s --replace'
```

---

## Ejemplo 13 — Ambience audio desde single video

```yaml
subscriptions:
  - profile_name: Ambience-Audio
    custom_name: bosque-profundo
    sources:
      - url: https://youtu.be/FAKEFORESTAUD01
        quality: best
        format: mp3
        min_duration: ''
        max_duration: 3h3m3s
        audio_quality: best
```

### Cómo lanzarlo

```powershell
python .\generate-ytdl-config.py
python .\prepare-subscriptions-runset.py
docker cp .\trim-ambience-video.py ytdl-sub:/tmp/trim-ambience-video.py
docker exec ytdl-sub sh -lc 'ytdl-sub --config /config/config.generated.yaml sub /config/subscriptions.runset.yaml'
docker exec ytdl-sub sh -lc 'python /tmp/trim-ambience-video.py --input "/downloads/Ambience-Audio/bosque-profundo/fakeforestaud01.mp3" --max-duration 3h3m3s --replace'
```

---

# 4. Ejemplos de overrides y variaciones

## Ejemplo 14 — Misma suscripción con dos fuentes y calidades distintas

```yaml
subscriptions:
  - profile_name: Podcast
    custom_name: debates-geopoliticos
    sources:
      - url: https://www.youtube.com/@GeoDebatesUno/videos
        max_items: 6
        min_duration: 12m
        quality: best
        format: mp3
      - url: https://www.youtube.com/@GeoDebatesDos/videos
        max_items: 6
        min_duration: 25m
        quality: best
        format: mp3
```

### Cómo lanzarlo

```powershell
python .\generate-ytdl-config.py
python .\prepare-subscriptions-runset.py
docker exec ytdl-sub sh -lc 'ytdl-sub --config /config/config.generated.yaml sub /config/subscriptions.runset.yaml'
```

---

## Ejemplo 15 — Un TV-Serie con filtros más agresivos

```yaml
subscriptions:
  - profile_name: TV-Serie
    custom_name: documentales-breve
    sources:
      - url: https://www.youtube.com/@DocsBreves/videos
        max_items: 8
        min_duration: 3m
        max_duration: 22m
        quality: 720p
        format: mp4
```

### Cómo lanzarlo

```powershell
python .\generate-ytdl-config.py
python .\prepare-subscriptions-runset.py
docker exec ytdl-sub sh -lc 'ytdl-sub --config /config/config.generated.yaml sub /config/subscriptions.runset.yaml'
```

---

## Ejemplo 16 — Music playlist acotada a 25 items

```yaml
subscriptions:
  - profile_name: Music-Playlist
    custom_name: pop-esencial
    sources:
      - url: https://www.youtube.com/playlist?list=PLFAKEPOP001
        max_items: 25
        quality: best
        format: mp3
```

### Cómo lanzarlo

```powershell
python .\generate-ytdl-config.py
python .\prepare-subscriptions-runset.py
docker exec ytdl-sub sh -lc 'ytdl-sub --config /config/config.generated.yaml sub /config/subscriptions.runset.yaml'
powershell.exe -ExecutionPolicy Bypass -File ".\clean-music-filenames.ps1" -TargetDir "E:\Docker_folders\ydtl-custom-downloads\Music-Playlist\pop-esencial"
docker exec beets-streaming2 sh -lc 'beet -v -c /config/beets.music-playlist.yaml import -s -q /downloads/Music-Playlist/pop-esencial'
```

---

## Ejemplo 17 — Playlist musical incremental con runset inteligente

Caso típico: `max_items: 0`, no quieres redescargar si no cambió la fuente completa.

```yaml
subscriptions:
  - profile_name: Music-Playlist
    custom_name: jazz-archivo
    sources:
      - url: https://www.youtube.com/playlist?list=PLFAKEJAZZ999
        max_items: 0
        quality: best
        format: mp3
```

### Cómo lanzarlo

```powershell
python .\generate-ytdl-config.py
python .\prepare-subscriptions-runset.py
Get-Content .\subscriptions.runset.yaml
docker exec ytdl-sub sh -lc 'ytdl-sub --config /config/config.generated.yaml sub /config/subscriptions.runset.yaml'
```

### Qué observar
Si la fuente completa no cambió y el estado previo coincide, el runset la dejará en `SKIP`.

---

## Ejemplo 18 — Canal con `max_items: 1` para modo “último episodio”

```yaml
subscriptions:
  - profile_name: Canales-youtube
    custom_name: ultimo-editorial
    sources:
      - url: https://www.youtube.com/@UltimoEditorial/videos
        max_items: 1
        quality: 1080p
        format: mp4
```

### Cómo lanzarlo

```powershell
python .\generate-ytdl-config.py
python .\prepare-subscriptions-runset.py
docker exec ytdl-sub sh -lc 'ytdl-sub --config /config/config.generated.yaml sub /config/subscriptions.runset.yaml'
```

---

## Ejemplo 19 — Ambience-video en MOV con recorte posterior

```yaml
subscriptions:
  - profile_name: Ambience-Video
    custom_name: cafe-noche
    sources:
      - url: https://www.youtube.com/watch?v=FAKEAMBIENCECAFE
        quality: 1080p
        format: mov
        min_duration: ''
        max_duration: 2h15m
        audio_quality: best
```

### Cómo lanzarlo

```powershell
python .\generate-ytdl-config.py
python .\prepare-subscriptions-runset.py
docker cp .\trim-ambience-video.py ytdl-sub:/tmp/trim-ambience-video.py
docker exec ytdl-sub sh -lc 'ytdl-sub --config /config/config.generated.yaml sub /config/subscriptions.runset.yaml'
docker exec ytdl-sub sh -lc 'python /tmp/trim-ambience-video.py --input "/downloads/Ambience-Video/cafe-noche/fakeambiencecafe.mov" --max-duration 2h15m --replace --faststart'
```

---

## Ejemplo 20 — Ambience-audio FLAC o WAV de referencia

```yaml
subscriptions:
  - profile_name: Ambience-Audio
    custom_name: mar-profundo
    sources:
      - url: https://youtu.be/FAKEMARPROFUNDO77
        quality: best
        format: wav
        min_duration: ''
        max_duration: 1h45m
        audio_quality: best
```

### Cómo lanzarlo

```powershell
python .\generate-ytdl-config.py
python .\prepare-subscriptions-runset.py
docker cp .\trim-ambience-video.py ytdl-sub:/tmp/trim-ambience-video.py
docker exec ytdl-sub sh -lc 'ytdl-sub --config /config/config.generated.yaml sub /config/subscriptions.runset.yaml'
docker exec ytdl-sub sh -lc 'python /tmp/trim-ambience-video.py --input "/downloads/Ambience-Audio/mar-profundo/fakemarprofundo77.wav" --max-duration 1h45m --replace'
```

---

# 5. Ejemplos de estructuras completas

## Ejemplo 21 — `profiles-custom.yml` mínimo y limpio

```yaml
profiles:
  - profile_name: Canales-youtube
    profile_type: Canales-youtube
    defaults:
      max_items: 3
      quality: 720p
      format: mp4
      min_duration: ''
      max_duration: ''
      date_range: 100years

  - profile_name: Podcast
    profile_type: Podcast
    defaults:
      max_items: 3
      quality: best
      format: mp3
      min_duration: 5m
      max_duration: ''
      date_range: 100years

  - profile_name: Music-Playlist
    profile_type: Music-Playlist
    defaults:
      max_items: 0
      quality: best
      format: mp3
      min_duration: ''
      max_duration: ''
      date_range: 100years
```

### Cómo lanzarlo

```powershell
python .\generate-ytdl-config.py
```

---

## Ejemplo 22 — `subscription-custom.yml` con las 6 familias

```yaml
subscriptions:
  - profile_name: Canales-youtube
    custom_name: analisis-mundo
    sources:
      - url: https://www.youtube.com/@AnalisisMundo/videos
        max_items: 3
        quality: 720p
        format: mp4

  - profile_name: Podcast
    custom_name: conversaciones-globales
    sources:
      - url: https://www.youtube.com/@ConversacionesGlobales/videos
        max_items: 5
        min_duration: 20m
        quality: best
        format: mp3

  - profile_name: TV-Serie
    custom_name: biblioteca-historia
    sources:
      - url: https://www.youtube.com/@BibliotecaHistoriaUno/videos
        max_items: 4
        min_duration: 8m
        quality: 1080p
        format: mp4
      - url: https://www.youtube.com/@BibliotecaHistoriaDos/videos
        max_items: 4
        min_duration: 8m
        quality: 720p
        format: mkv

  - profile_name: Music-Playlist
    custom_name: noche-electronica
    sources:
      - url: https://www.youtube.com/playlist?list=PLFAKENIGHT2026
        max_items: 0
        quality: best
        format: mp3

  - profile_name: Ambience-Video
    custom_name: ciudad-lluviosa
    sources:
      - url: https://www.youtube.com/watch?v=FAKECITYRAIN001
        quality: 1080p
        format: mp4
        min_duration: ''
        max_duration: 3h3m3s
        audio_quality: best

  - profile_name: Ambience-Audio
    custom_name: habitacion-viento
    sources:
      - url: https://www.youtube.com/watch?v=FAKEWINDROOM09
        quality: best
        format: mp3
        min_duration: ''
        max_duration: 3h3m3s
        audio_quality: best
```

### Cómo lanzarlo

```powershell
python .\generate-ytdl-config.py
python .\prepare-subscriptions-runset.py
docker cp .\trim-ambience-video.py ytdl-sub:/tmp/trim-ambience-video.py
docker exec ytdl-sub sh -lc 'ytdl-sub --config /config/config.generated.yaml sub /config/subscriptions.runset.yaml'
```

---

## Ejemplo 23 — Forzar solo la parte musical

### Recomendado cuando
Quieres iterar sobre `music-playlist`, limpieza de nombres y beets, sin tocar el resto.

### Cómo lanzarlo

```powershell
python .\generate-ytdl-config.py --only-profile music-playlist
python .\prepare-subscriptions-runset.py
docker exec ytdl-sub sh -lc 'ytdl-sub --config /config/config.generated.yaml sub /config/subscriptions.runset.yaml'
powershell.exe -ExecutionPolicy Bypass -File ".\clean-music-filenames.ps1" -TargetDir "E:\Docker_folders\ydtl-custom-downloads\Music-Playlist\noche-electronica"
docker exec beets-streaming2 sh -lc 'beet -v -c /config/beets.music-playlist.yaml import -s -q /downloads/Music-Playlist/noche-electronica'
```

---

## Ejemplo 24 — Forzar solo ambience

```powershell
python .\generate-ytdl-config.py --only-profile ambience-video
python .\prepare-subscriptions-runset.py
docker cp .\trim-ambience-video.py ytdl-sub:/tmp/trim-ambience-video.py
docker exec ytdl-sub sh -lc 'ytdl-sub --config /config/config.generated.yaml sub /config/subscriptions.runset.yaml'
```

Y luego recorte:

```powershell
docker exec ytdl-sub sh -lc 'find /downloads/Ambience-Video -type f \( -iname "*.mp4" -o -iname "*.mkv" -o -iname "*.webm" -o -iname "*.mov" -o -iname "*.m4v" -o -iname "*.avi" \) -exec python /tmp/trim-ambience-video.py --input "{}" --max-duration 3h3m3s --replace \;'
```

---

# 6. Ejemplos de pruebas y validación

## Ejemplo 25 — Lanzar prueba e2e completa oficial

### Cómo lanzarlo

```powershell
powershell.exe -ExecutionPolicy Bypass -File ".\test-e2e-perfiles-subscriptions.ps1"
```

### Qué hace
- prepara contexto;
- regenera YAML;
- prepara runset;
- copia el trim script;
- ejecuta ytdl-sub real;
- mueve estado pendiente a estado estable;
- limpia nombres en music-playlist;
- ejecuta beets;
- recorta ambience video;
- recorta ambience audio.

---

## Ejemplo 26 — Validar una ejecución ya realizada

### Cómo lanzarlo

```powershell
powershell.exe -ExecutionPolicy Bypass -File ".\validate-test-e2e-perfiles-subscriptions.ps1"
```

### Qué mira
- YAML generado;
- árboles finales;
- conteos por perfil;
- duraciones reales;
- streams con ffprobe;
- residuos temporales;
- logs de ytdl-sub;
- logs de beets;
- basura en `/tmp`.

---

## Ejemplo 27 — Batería de dos bloques para music-playlist

### Bloque 1

```powershell
powershell.exe -ExecutionPolicy Bypass -File ".\bloque1-test.ps1"
```

### Bloque 2

```powershell
powershell.exe -ExecutionPolicy Bypass -File ".\bloque2-test.ps1"
```

### Cuándo usarlo
Cuando quieres comprobar:
- primera descarga real;
- segunda pasada sin redescarga redundante;
- archivo de descarga respetado;
- comportamiento de beets en pasadas sucesivas.

---

## Ejemplo 28 — Ver el número de MP3 finales

```powershell
docker exec ytdl-sub sh -lc 'echo "[COUNT MP3]"; if [ -d /downloads/Music-Playlist/music-playlist-prueba ]; then find /downloads/Music-Playlist/music-playlist-prueba -maxdepth 1 -type f -name "*.mp3" | wc -l; else echo 0; fi'
```

---

## Ejemplo 29 — Ver si se está reutilizando download archive

```powershell
docker exec ytdl-sub sh -lc 'latest=$(ls -1t /config/logs/*.music-playlist-prueba-*.log 2>/dev/null | head -n 1); if [ -n "$latest" ]; then grep -c "has already been recorded in the archive" "$latest" || true; else echo 0; fi'
```

---

## Ejemplo 30 — Validar duración final de ambience

```powershell
docker exec ytdl-sub sh -lc 'find /downloads/Ambience-Video/ambience-video-prueba -maxdepth 1 -type f \( -iname "*.mp4" -o -iname "*.mkv" -o -iname "*.webm" \) -exec sh -c '\''f="$1"; dur="$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$f")"; printf "%s -> %s s\n" "$f" "$dur"'\'' sh {} \;'
```

---

# 7. Ejemplos de depuración

## Ejemplo 31 — Ver logs persistidos

```powershell
docker exec ytdl-sub sh -lc 'ls -lah /config/logs'
```

---

## Ejemplo 32 — Sacar las últimas 200 líneas de logs de ytdl-sub

```powershell
docker exec ytdl-sub sh -lc 'find /config/logs -maxdepth 1 -type f | sort | tail -n 10 | while read -r f; do echo "------------------------------------------------------------"; echo "$f"; tail -n 200 "$f" || true; done'
```

---

## Ejemplo 33 — Ver log de beets en su contenedor

```powershell
docker exec beets-streaming2 sh -lc 'tail -n 200 /config/logs/beets-import.log 2>/dev/null || true'
```

---

## Ejemplo 34 — Revisar working_directory residual

```powershell
docker exec ytdl-sub sh -lc 'find /tmp/ytdl-sub-working-directory -mindepth 1 -maxdepth 3 -print 2>/dev/null || true'
```

---

## Ejemplo 35 — Revisar árboles de salida

```powershell
docker exec ytdl-sub sh -lc 'find /downloads/TV-Serie/lolete -maxdepth 3 \( -type d -o -type f \) | sort'
```

---

# 8. Ejemplos de casuísticas reales o típicas

## Ejemplo 36 — Canal grande con top reciente estable

Escenario:
- `max_items = 3`
- ya hay 3 ficheros locales;
- el top 3 de IDs no cambió;
- el runset debe dejarlo en `SKIP`.

### Cómo lanzarlo

```powershell
python .\prepare-subscriptions-runset.py
Get-Content .\subscriptions.runset.yaml
```

### Señal esperada
Mensajes tipo:

```text
[SKIP] canales-youtube-mi-canal-origen -> top 3 intacto; no toca descargar
```

---

## Ejemplo 37 — Canal grande con cambio en el top reciente

Escenario:
- `max_items = 3`;
- entra un vídeo nuevo y sale otro del top;
- el runset debe meterlo en `RUN`.

### Cómo lanzarlo

```powershell
python .\prepare-subscriptions-runset.py
Get-Content .\subscriptions.runset.yaml
docker exec ytdl-sub sh -lc 'ytdl-sub --config /config/config.generated.yaml sub /config/subscriptions.runset.yaml'
```

---

## Ejemplo 38 — Playlist completa con contenido local ya existente y sin estado previo

Escenario:
- `max_items = 0`;
- ya hay ficheros descargados;
- no existe `.recent-items-state.json`;
- el runset consolida estado sin reejecutar.

### Cómo lanzarlo

```powershell
Remove-Item .\.recent-items-state.json -Force -ErrorAction SilentlyContinue
python .\prepare-subscriptions-runset.py
```

---

## Ejemplo 39 — Single video ya presente

Escenario:
- ambience single video;
- el fichero ya existe;
- no quieres recargarlo.

### Cómo lanzarlo

```powershell
python .\prepare-subscriptions-runset.py
Get-Content .\subscriptions.runset.yaml
```

---

## Ejemplo 40 — Music-playlist con nombres sucios antes de beets

### Limpieza

```powershell
powershell.exe -ExecutionPolicy Bypass -File ".\clean-music-filenames.ps1" -TargetDir "E:\Docker_folders\ydtl-custom-downloads\Music-Playlist\music-playlist-prueba"
```

### Luego beets

```powershell
docker exec beets-streaming2 sh -lc 'beet -v -c /config/beets.music-playlist.yaml import -s -q /downloads/Music-Playlist/music-playlist-prueba'
```

---

## Ejemplo 41 — Recorte rápido sustituyendo el original

```powershell
docker exec ytdl-sub sh -lc 'python /tmp/trim-ambience-video.py --input "/downloads/Ambience-Video/ambience-video-prueba/algun-video.mp4" --max-duration 03:03:03 --replace'
```

---

## Ejemplo 42 — Recorte con `--faststart`

```powershell
docker exec ytdl-sub sh -lc 'python /tmp/trim-ambience-video.py --input "/downloads/Ambience-Video/ambience-video-prueba/algun-video.mp4" --max-duration 03:03:03 --replace --faststart'
```

---

## Ejemplo 43 — Recorte con `--skip-output-probe`

```powershell
docker exec ytdl-sub sh -lc 'python /tmp/trim-ambience-video.py --input "/downloads/Ambience-Video/ambience-video-prueba/algun-video.mp4" --max-duration 03:03:03 --replace --skip-output-probe'
```

---

## Ejemplo 44 — Contar vídeos por tipo

```powershell
docker exec ytdl-sub sh -lc 'find /downloads/Canales-youtube/analisis-mundo -type f \( -iname "*.mp4" -o -iname "*.mkv" -o -iname "*.webm" \) | wc -l'
```

---

## Ejemplo 45 — Inspección rápida de códecs

```powershell
docker exec ytdl-sub sh -lc 'ffprobe -v error -select_streams a:0 -show_entries stream=codec_name,sample_rate,channels -of default=noprint_wrappers=1 "/downloads/Music-Playlist/music-playlist-prueba/cancion.mp3"'
```

---

# 9. Ejemplos medianos de configuración completa

## Ejemplo 46 — Setup “biblioteca ligera”

```yaml
subscriptions:
  - profile_name: Canales-youtube
    custom_name: noticias-cortas
    sources:
      - url: https://www.youtube.com/@NoticiasCortas/videos
        max_items: 2
        quality: 720p
        format: mp4

  - profile_name: Podcast
    custom_name: analisis-sonoro
    sources:
      - url: https://www.youtube.com/@AnalisisSonoro/videos
        max_items: 5
        min_duration: 12m
        quality: best
        format: mp3

  - profile_name: Ambience-Audio
    custom_name: noche-suave
    sources:
      - url: https://www.youtube.com/watch?v=FAKENOCHESUAVE88
        quality: best
        format: mp3
        min_duration: ''
        max_duration: 2h
        audio_quality: best
```

### Cómo lanzarlo

```powershell
python .\generate-ytdl-config.py
python .\prepare-subscriptions-runset.py
docker cp .\trim-ambience-video.py ytdl-sub:/tmp/trim-ambience-video.py
docker exec ytdl-sub sh -lc 'ytdl-sub --config /config/config.generated.yaml sub /config/subscriptions.runset.yaml'
```

---

## Ejemplo 47 — Setup “archivo audiovisual”

```yaml
subscriptions:
  - profile_name: TV-Serie
    custom_name: imperios
    sources:
      - url: https://www.youtube.com/@ImperiosArchivo/videos
        max_items: 12
        min_duration: 7m
        quality: 1080p
        format: mp4
      - url: https://www.youtube.com/@CronicasDeImperios/videos
        max_items: 12
        min_duration: 7m
        quality: 1080p
        format: mkv

  - profile_name: Canales-youtube
    custom_name: editoriales
    sources:
      - url: https://www.youtube.com/@EditorialesLargas/videos
        max_items: 6
        quality: 1080p
        format: mp4
```

### Cómo lanzarlo

```powershell
python .\generate-ytdl-config.py
python .\prepare-subscriptions-runset.py
docker exec ytdl-sub sh -lc 'ytdl-sub --config /config/config.generated.yaml sub /config/subscriptions.runset.yaml'
```

---

## Ejemplo 48 — Setup “audio-first”

```yaml
subscriptions:
  - profile_name: Podcast
    custom_name: macro-geopolitica
    sources:
      - url: https://www.youtube.com/@MacroGeoUno/videos
        max_items: 8
        min_duration: 18m
        quality: best
        format: mp3
      - url: https://www.youtube.com/playlist?list=PLFAKEMACROGEO22
        max_items: 8
        min_duration: 18m
        quality: best
        format: mp3

  - profile_name: Music-Playlist
    custom_name: clasicos-remaster
    sources:
      - url: https://www.youtube.com/playlist?list=PLFAKECLASSICS2026
        max_items: 0
        quality: best
        format: mp3

  - profile_name: Ambience-Audio
    custom_name: lectura-profunda
    sources:
      - url: https://youtu.be/FAKELECTURA777
        quality: best
        format: mp3
        min_duration: ''
        max_duration: 4h
        audio_quality: best
```

### Cómo lanzarlo

```powershell
python .\generate-ytdl-config.py
python .\prepare-subscriptions-runset.py
docker cp .\trim-ambience-video.py ytdl-sub:/tmp/trim-ambience-video.py
docker exec ytdl-sub sh -lc 'ytdl-sub --config /config/config.generated.yaml sub /config/subscriptions.runset.yaml'
powershell.exe -ExecutionPolicy Bypass -File ".\clean-music-filenames.ps1" -TargetDir "E:\Docker_folders\ydtl-custom-downloads\Music-Playlist\clasicos-remaster"
docker exec beets-streaming2 sh -lc 'beet -v -c /config/beets.music-playlist.yaml import -s -q /downloads/Music-Playlist/clasicos-remaster'
```

---

# 10. Ejemplos avanzados

## Ejemplo 49 — Preparar un runset y no ejecutar nada si sale vacío

```powershell
python .\generate-ytdl-config.py
python .\prepare-subscriptions-runset.py
$runsetPath = Join-Path (Get-Location) "subscriptions.runset.yaml"
$runsetInfo = Get-Item $runsetPath
if ($runsetInfo.Length -le 5) {
  Write-Host "[INFO] subscriptions.runset.yaml esta vacio: no toca descargar nada."
} else {
  docker exec ytdl-sub sh -lc 'ytdl-sub --config /config/config.generated.yaml sub /config/subscriptions.runset.yaml'
}
```

---

## Ejemplo 50 — Full workflow con consolidación de estado

```powershell
python .\generate-ytdl-config.py
python .\prepare-subscriptions-runset.py
docker cp .\trim-ambience-video.py ytdl-sub:/tmp/trim-ambience-video.py
docker exec ytdl-sub sh -lc 'ytdl-sub --config /config/config.generated.yaml sub /config/subscriptions.runset.yaml'
if (Test-Path '.\.recent-items-state.pending.json') {
  Move-Item '.\.recent-items-state.pending.json' '.\.recent-items-state.json' -Force
}
powershell.exe -ExecutionPolicy Bypass -File ".\clean-music-filenames.ps1" -TargetDir "E:\Docker_folders\ydtl-custom-downloads\Music-Playlist\clasicos-remaster"
docker exec beets-streaming2 sh -lc 'beet -v -c /config/beets.music-playlist.yaml import -s -q /downloads/Music-Playlist/clasicos-remaster'
docker exec ytdl-sub sh -lc 'find /downloads/Ambience-Video -type f \( -iname "*.mp4" -o -iname "*.mkv" -o -iname "*.webm" -o -iname "*.mov" -o -iname "*.m4v" -o -iname "*.avi" \) -exec python /tmp/trim-ambience-video.py --input "{}" --max-duration 03:03:03 --replace \;'
docker exec ytdl-sub sh -lc 'find /downloads/Ambience-Audio -type f \( -iname "*.mp3" -o -iname "*.m4a" -o -iname "*.aac" -o -iname "*.opus" -o -iname "*.ogg" -o -iname "*.wav" -o -iname "*.flac" \) -exec python /tmp/trim-ambience-video.py --input "{}" --max-duration 03:03:03 --replace \;'
```

---

## Ejemplo 51 — Ciclo de desarrollo de un único perfil

1. editar `profiles-custom.yml`;
2. editar `subscription-custom.yml`;
3. generar solo el perfil;
4. revisar YAML;
5. ejecutar;
6. validar conteos y logs.

### Cómo lanzarlo

```powershell
python .\generate-ytdl-config.py --only-profile podcast
Get-Content .\config.generated.yaml -TotalCount 200
Get-Content .\subscriptions.generated.yaml
python .\prepare-subscriptions-runset.py
docker exec ytdl-sub sh -lc 'ytdl-sub --config /config/config.generated.yaml sub /config/subscriptions.runset.yaml'
docker exec ytdl-sub sh -lc 'ls -lah /config/logs'
```

---

## Ejemplo 52 — Canal con nombre custom largo y slug complejo

```yaml
subscriptions:
  - profile_name: Canales-youtube
    custom_name: analisis-macro-y-geopolitica-edicion-especial-2026
    sources:
      - url: https://www.youtube.com/@AnalisisMacroGeoEdicionEspecial/videos
        max_items: 3
        quality: 1080p
        format: mp4
```

### Cómo lanzarlo

```powershell
python .\generate-ytdl-config.py
python .\prepare-subscriptions-runset.py
Get-Content .\subscriptions.generated.yaml
docker exec ytdl-sub sh -lc 'ytdl-sub --config /config/config.generated.yaml sub /config/subscriptions.runset.yaml'
```

---

## Ejemplo 53 — Mezcla de canal, playlist y single video

```yaml
subscriptions:
  - profile_name: Podcast
    custom_name: inteligencia-operativa
    sources:
      - url: https://www.youtube.com/@InteligenciaOperativa/videos
        max_items: 5
        min_duration: 10m
        quality: best
        format: mp3
      - url: https://www.youtube.com/playlist?list=PLFAKEINTEL2026
        max_items: 5
        min_duration: 10m
        quality: best
        format: mp3

  - profile_name: Ambience-Video
    custom_name: bunker-nocturno
    sources:
      - url: https://www.youtube.com/watch?v=FAKEBUNKER001
        quality: 1080p
        format: mp4
        min_duration: ''
        max_duration: 2h30m
        audio_quality: best
```

### Cómo lanzarlo

```powershell
python .\generate-ytdl-config.py
python .\prepare-subscriptions-runset.py
docker cp .\trim-ambience-video.py ytdl-sub:/tmp/trim-ambience-video.py
docker exec ytdl-sub sh -lc 'ytdl-sub --config /config/config.generated.yaml sub /config/subscriptions.runset.yaml'
```

---

## Ejemplo 54 — Validación detallada post-ejecución de audio

```powershell
docker exec ytdl-sub sh -lc 'find /downloads/Ambience-Audio/lectura-profunda -maxdepth 1 -type f \( -iname "*.mp3" -o -iname "*.flac" -o -iname "*.wav" \) -exec sh -c '\''f="$1"; echo "------------------------------------------------------------"; echo "$f"; ls -lh "$f"; ffprobe -v error -show_entries format=duration,size -of default=noprint_wrappers=1 "$f"; ffprobe -v error -select_streams a:0 -show_entries stream=codec_name,sample_rate,channels -of default=noprint_wrappers=1 "$f"'\'' sh {} \;'
```

---

## Ejemplo 55 — Revisar contenido final de una serie Jellyfin

```powershell
docker exec ytdl-sub sh -lc 'find /downloads/TV-Serie/historia-del-mundo -maxdepth 3 \( -type d -o -type f \) | sort'
```

---

# 11. Ejemplos gigantes

## Ejemplo 56 — Configuración “multi-biblioteca” grande

```yaml
subscriptions:
  - profile_name: Canales-youtube
    custom_name: geoestrategia-actual
    sources:
      - url: https://www.youtube.com/@GeoestrategiaActual/videos
        max_items: 4
        quality: 1080p
        format: mp4

  - profile_name: Canales-youtube
    custom_name: editoriales-rapidas
    sources:
      - url: https://www.youtube.com/@EditorialesRapidas/videos
        max_items: 2
        quality: 720p
        format: mp4

  - profile_name: Podcast
    custom_name: debates-largos
    sources:
      - url: https://www.youtube.com/@DebatesLargos/videos
        max_items: 8
        min_duration: 30m
        quality: best
        format: mp3
      - url: https://www.youtube.com/playlist?list=PLFAKEDEBATES2026
        max_items: 8
        min_duration: 30m
        quality: best
        format: mp3

  - profile_name: TV-Serie
    custom_name: cronicas-del-siglo
    sources:
      - url: https://www.youtube.com/@CronicasDelSigloUno/videos
        max_items: 6
        min_duration: 7m
        quality: 1080p
        format: mp4
      - url: https://www.youtube.com/@CronicasDelSigloDos/videos
        max_items: 6
        min_duration: 7m
        quality: 720p
        format: mkv

  - profile_name: Music-Playlist
    custom_name: ambient-electronica
    sources:
      - url: https://www.youtube.com/playlist?list=PLFAKEAMBIENTELEC01
        max_items: 0
        quality: best
        format: mp3

  - profile_name: Music-Playlist
    custom_name: clasicos-orquestales
    sources:
      - url: https://www.youtube.com/playlist?list=PLFAKEORQUESTA909
        max_items: 60
        quality: best
        format: mp3

  - profile_name: Ambience-Video
    custom_name: ciudad-futurista
    sources:
      - url: https://www.youtube.com/watch?v=FAKEFUTURECITY01
        quality: 1080p
        format: mp4
        min_duration: ''
        max_duration: 3h3m3s
        audio_quality: best
      - url: https://www.youtube.com/watch?v=FAKEFUTURECITY02
        quality: 720p
        format: mp4
        min_duration: ''
        max_duration: 2h45m
        audio_quality: best

  - profile_name: Ambience-Audio
    custom_name: estudio-profundo
    sources:
      - url: https://www.youtube.com/watch?v=FAKESTUDIOAUDIO01
        quality: best
        format: mp3
        min_duration: ''
        max_duration: 3h3m3s
        audio_quality: best
      - url: https://youtu.be/FAKESTUDIOAUDIO02
        quality: best
        format: flac
        min_duration: ''
        max_duration: 2h
        audio_quality: best
```

### Cómo lanzarlo

```powershell
python .\generate-ytdl-config.py
python .\prepare-subscriptions-runset.py
docker cp .\trim-ambience-video.py ytdl-sub:/tmp/trim-ambience-video.py
docker exec ytdl-sub sh -lc 'ytdl-sub --config /config/config.generated.yaml sub /config/subscriptions.runset.yaml'
if (Test-Path '.\.recent-items-state.pending.json') {
  Move-Item '.\.recent-items-state.pending.json' '.\.recent-items-state.json' -Force
}
powershell.exe -ExecutionPolicy Bypass -File ".\clean-music-filenames.ps1" -TargetDir "E:\Docker_folders\ydtl-custom-downloads\Music-Playlist\ambient-electronica"
powershell.exe -ExecutionPolicy Bypass -File ".\clean-music-filenames.ps1" -TargetDir "E:\Docker_folders\ydtl-custom-downloads\Music-Playlist\clasicos-orquestales"
docker exec beets-streaming2 sh -lc 'beet -v -c /config/beets.music-playlist.yaml import -s -q /downloads/Music-Playlist/ambient-electronica'
docker exec beets-streaming2 sh -lc 'beet -v -c /config/beets.music-playlist.yaml import -s -q /downloads/Music-Playlist/clasicos-orquestales'
docker exec ytdl-sub sh -lc 'find /downloads/Ambience-Video/ciudad-futurista -maxdepth 1 -type f \( -iname "*.mp4" -o -iname "*.mkv" -o -iname "*.webm" -o -iname "*.mov" -o -iname "*.m4v" -o -iname "*.avi" \) -exec python /tmp/trim-ambience-video.py --input "{}" --max-duration 03:03:03 --replace \;'
docker exec ytdl-sub sh -lc 'find /downloads/Ambience-Audio/estudio-profundo -maxdepth 1 -type f \( -iname "*.mp3" -o -iname "*.m4a" -o -iname "*.aac" -o -iname "*.opus" -o -iname "*.ogg" -o -iname "*.wav" -o -iname "*.flac" \) -exec python /tmp/trim-ambience-video.py --input "{}" --max-duration 03:03:03 --replace \;'
powershell.exe -ExecutionPolicy Bypass -File ".\validate-test-e2e-perfiles-subscriptions.ps1"
```

---

## Ejemplo 57 — Ejemplo master gigante

Este ejemplo intenta cubrir prácticamente todas las casuísticas del proyecto: múltiples perfiles, múltiples fuentes por suscripción, mezcla de canal/playlist/single video, ejecución inteligente, limpieza musical, etiquetado con beets, recorte ambience y validación final.

### `profiles-custom.yml`

```yaml
profiles:
  - profile_name: Canales-youtube
    profile_type: Canales-youtube
    defaults:
      max_items: 3
      quality: 720p
      format: mp4
      min_duration: ''
      max_duration: ''
      date_range: 100years

  - profile_name: Podcast
    profile_type: Podcast
    defaults:
      max_items: 5
      quality: best
      format: mp3
      min_duration: 8m
      max_duration: ''
      date_range: 100years

  - profile_name: TV-Serie
    profile_type: TV-Serie
    defaults:
      max_items: 4
      quality: 1080p
      format: mp4
      min_duration: 5m
      max_duration: ''
      date_range: 100years

  - profile_name: Music-Playlist
    profile_type: Music-Playlist
    defaults:
      max_items: 0
      quality: best
      format: mp3
      min_duration: ''
      max_duration: ''
      date_range: 100years

  - profile_name: Ambience-Video
    profile_type: ambience-video
    defaults:
      quality: 1080p
      format: mp4
      min_duration: ''
      max_duration: 3h3m3s
      date_range: 100years
      embed_thumbnail: false
      audio_quality: best

  - profile_name: Ambience-Audio
    profile_type: ambience-audio
    defaults:
      quality: best
      format: mp3
      min_duration: ''
      max_duration: 3h3m3s
      date_range: 100years
      embed_thumbnail: false
      audio_quality: best
```

### `subscription-custom.yml`

```yaml
subscriptions:
  - profile_name: Canales-youtube
    custom_name: geoestrategia-central
    sources:
      - url: https://www.youtube.com/@GeoCentralUno/videos
        max_items: 3
        quality: 1080p
        format: mp4
      - url: https://www.youtube.com/@GeoCentralDos/videos
        max_items: 2
        quality: 720p
        format: mkv

  - profile_name: Podcast
    custom_name: mundo-en-audio
    sources:
      - url: https://www.youtube.com/@MundoEnAudio/videos
        max_items: 12
        min_duration: 20m
        quality: best
        format: mp3
      - url: https://www.youtube.com/playlist?list=PLFAKEMUNDOAUDIO88
        max_items: 12
        min_duration: 20m
        quality: best
        format: mp3

  - profile_name: TV-Serie
    custom_name: atlas-historico
    sources:
      - url: https://www.youtube.com/@AtlasHistoricoUno/videos
        max_items: 10
        min_duration: 6m
        quality: 1080p
        format: mp4
      - url: https://www.youtube.com/@AtlasHistoricoDos/videos
        max_items: 10
        min_duration: 6m
        quality: 720p
        format: mkv
      - url: https://www.youtube.com/@AtlasHistoricoTres/videos
        max_items: 10
        min_duration: 6m
        quality: 720p
        format: webm

  - profile_name: Music-Playlist
    custom_name: archivo-electronico
    sources:
      - url: https://www.youtube.com/playlist?list=PLFAKEARCHIVEELECTRO01
        max_items: 0
        quality: best
        format: mp3

  - profile_name: Music-Playlist
    custom_name: canciones-cinematograficas
    sources:
      - url: https://www.youtube.com/playlist?list=PLFAKECINEMUSIC808
        max_items: 40
        quality: best
        format: mp3

  - profile_name: Ambience-Video
    custom_name: lluvia-megaciudad
    sources:
      - url: https://www.youtube.com/watch?v=FAKEMEGACITY01
        quality: 1080p
        format: mp4
        min_duration: ''
        max_duration: 3h3m3s
        audio_quality: best
      - url: https://www.youtube.com/watch?v=FAKEMEGACITY02
        quality: 1080p
        format: mov
        min_duration: ''
        max_duration: 2h20m
        audio_quality: best

  - profile_name: Ambience-Audio
    custom_name: estudio-total
    sources:
      - url: https://www.youtube.com/watch?v=FAKESTUDIOTOTAL01
        quality: best
        format: mp3
        min_duration: ''
        max_duration: 3h3m3s
        audio_quality: best
      - url: https://youtu.be/FAKESTUDIOTOTAL02
        quality: best
        format: flac
        min_duration: ''
        max_duration: 90m
        audio_quality: best
      - url: https://youtu.be/FAKESTUDIOTOTAL03
        quality: best
        format: wav
        min_duration: ''
        max_duration: 2h15m
        audio_quality: best
```

### Cómo lanzarlo

#### Paso 1 — regeneración

```powershell
cd E:\Docker_folders\streaming2\ytdl-sub\config
python .\generate-ytdl-config.py
```

#### Paso 2 — runset inteligente

```powershell
python .\prepare-subscriptions-runset.py
Get-Content .\subscriptions.runset.yaml
```

#### Paso 3 — copia del trim helper

```powershell
docker cp .\trim-ambience-video.py ytdl-sub:/tmp/trim-ambience-video.py
```

#### Paso 4 — descarga real

```powershell
docker exec ytdl-sub sh -lc 'ytdl-sub --config /config/config.generated.yaml sub /config/subscriptions.runset.yaml'
```

#### Paso 5 — consolidar estado

```powershell
if (Test-Path '.\.recent-items-state.pending.json') {
  Move-Item '.\.recent-items-state.pending.json' '.\.recent-items-state.json' -Force
}
```

#### Paso 6 — limpieza previa musical

```powershell
powershell.exe -ExecutionPolicy Bypass -File ".\clean-music-filenames.ps1" -TargetDir "E:\Docker_folders\ydtl-custom-downloads\Music-Playlist\archivo-electronico"
powershell.exe -ExecutionPolicy Bypass -File ".\clean-music-filenames.ps1" -TargetDir "E:\Docker_folders\ydtl-custom-downloads\Music-Playlist\canciones-cinematograficas"
```

#### Paso 7 — etiquetado con beets

```powershell
docker exec beets-streaming2 sh -lc 'beet -v -c /config/beets.music-playlist.yaml import -s -q /downloads/Music-Playlist/archivo-electronico'
docker exec beets-streaming2 sh -lc 'beet -v -c /config/beets.music-playlist.yaml import -s -q /downloads/Music-Playlist/canciones-cinematograficas'
```

#### Paso 8 — recorte de ambience video

```powershell
docker exec ytdl-sub sh -lc 'find /downloads/Ambience-Video/lluvia-megaciudad -maxdepth 1 -type f \( -iname "*.mp4" -o -iname "*.mkv" -o -iname "*.webm" -o -iname "*.mov" -o -iname "*.m4v" -o -iname "*.avi" \) -exec python /tmp/trim-ambience-video.py --input "{}" --max-duration 03:03:03 --replace \;'
```

#### Paso 9 — recorte de ambience audio

```powershell
docker exec ytdl-sub sh -lc 'find /downloads/Ambience-Audio/estudio-total -maxdepth 1 -type f \( -iname "*.mp3" -o -iname "*.m4a" -o -iname "*.aac" -o -iname "*.opus" -o -iname "*.ogg" -o -iname "*.wav" -o -iname "*.flac" \) -exec python /tmp/trim-ambience-video.py --input "{}" --max-duration 03:03:03 --replace \;'
```

#### Paso 10 — validación final

```powershell
powershell.exe -ExecutionPolicy Bypass -File ".\validate-test-e2e-perfiles-subscriptions.ps1"
```

### Qué valida este ejemplo master
- generación de múltiples presets;
- slugificación de nombres;
- separación entre `preset_name` y `subscription_name`;
- uso combinado de canal, playlist y single video;
- diferencias entre filtros de duración y recorte posterior;
- skip inteligente por estado previo;
- descarga controlada por top reciente;
- music-playlist con enriquecimiento posterior;
- recorte reemplazando original;
- inspección final con logs, conteos, ffprobe y residuos.

---

# 12. Inventario de URLs ficticias usadas en este documento

Estas URLs son de ejemplo y no tienen por qué existir:

- `https://www.youtube.com/@GeoPoliticaDiaria/videos`
- `https://www.youtube.com/@InformesLargos/videos`
- `https://www.youtube.com/@EntrevistasTech/videos`
- `https://www.youtube.com/playlist?list=PLFAKEPODCAST001`
- `https://www.youtube.com/@CanalHistoriaTotal/videos`
- `https://www.youtube.com/@HistoriaExpandida/videos`
- `https://www.youtube.com/playlist?list=PLFAKEMUSIC777`
- `https://www.youtube.com/watch?v=FAKEAMBIENCE001`
- `https://youtu.be/FAKEFORESTAUD01`
- `https://www.youtube.com/@GeoDebatesUno/videos`
- `https://www.youtube.com/@GeoDebatesDos/videos`
- `https://www.youtube.com/@DocsBreves/videos`
- `https://www.youtube.com/playlist?list=PLFAKEPOP001`
- `https://www.youtube.com/playlist?list=PLFAKEJAZZ999`
- `https://www.youtube.com/@UltimoEditorial/videos`
- `https://www.youtube.com/watch?v=FAKEAMBIENCECAFE`
- `https://youtu.be/FAKEMARPROFUNDO77`
- `https://www.youtube.com/@AnalisisMundo/videos`
- `https://www.youtube.com/@ConversacionesGlobales/videos`
- `https://www.youtube.com/@BibliotecaHistoriaUno/videos`
- `https://www.youtube.com/@BibliotecaHistoriaDos/videos`
- `https://www.youtube.com/playlist?list=PLFAKENIGHT2026`
- `https://www.youtube.com/watch?v=FAKECITYRAIN001`
- `https://www.youtube.com/watch?v=FAKEWINDROOM09`
- `https://www.youtube.com/@NoticiasCortas/videos`
- `https://www.youtube.com/@AnalisisSonoro/videos`
- `https://www.youtube.com/watch?v=FAKENOCHESUAVE88`
- `https://www.youtube.com/@ImperiosArchivo/videos`
- `https://www.youtube.com/@CronicasDeImperios/videos`
- `https://www.youtube.com/@EditorialesLargas/videos`
- `https://www.youtube.com/@MacroGeoUno/videos`
- `https://www.youtube.com/playlist?list=PLFAKEMACROGEO22`
- `https://www.youtube.com/playlist?list=PLFAKECLASSICS2026`
- `https://youtu.be/FAKELECTURA777`
- `https://www.youtube.com/@AnalisisMacroGeoEdicionEspecial/videos`
- `https://www.youtube.com/@InteligenciaOperativa/videos`
- `https://www.youtube.com/playlist?list=PLFAKEINTEL2026`
- `https://www.youtube.com/watch?v=FAKEBUNKER001`
- `https://www.youtube.com/@GeoestrategiaActual/videos`
- `https://www.youtube.com/@EditorialesRapidas/videos`
- `https://www.youtube.com/@DebatesLargos/videos`
- `https://www.youtube.com/playlist?list=PLFAKEDEBATES2026`
- `https://www.youtube.com/@CronicasDelSigloUno/videos`
- `https://www.youtube.com/@CronicasDelSigloDos/videos`
- `https://www.youtube.com/playlist?list=PLFAKEAMBIENTELEC01`
- `https://www.youtube.com/playlist?list=PLFAKEORQUESTA909`
- `https://www.youtube.com/watch?v=FAKEFUTURECITY01`
- `https://www.youtube.com/watch?v=FAKEFUTURECITY02`
- `https://www.youtube.com/watch?v=FAKESTUDIOAUDIO01`
- `https://youtu.be/FAKESTUDIOAUDIO02`
- `https://www.youtube.com/@GeoCentralUno/videos`
- `https://www.youtube.com/@GeoCentralDos/videos`
- `https://www.youtube.com/@MundoEnAudio/videos`
- `https://www.youtube.com/playlist?list=PLFAKEMUNDOAUDIO88`
- `https://www.youtube.com/@AtlasHistoricoUno/videos`
- `https://www.youtube.com/@AtlasHistoricoDos/videos`
- `https://www.youtube.com/@AtlasHistoricoTres/videos`
- `https://www.youtube.com/playlist?list=PLFAKEARCHIVEELECTRO01`
- `https://www.youtube.com/playlist?list=PLFAKECINEMUSIC808`
- `https://www.youtube.com/watch?v=FAKEMEGACITY01`
- `https://www.youtube.com/watch?v=FAKEMEGACITY02`
- `https://www.youtube.com/watch?v=FAKESTUDIOTOTAL01`
- `https://youtu.be/FAKESTUDIOTOTAL02`
- `https://youtu.be/FAKESTUDIOTOTAL03`

