# README — Sistema de perfiles y workflows para ytdl-sub

## 1. Qué es este proyecto

Este proyecto monta una capa de automatización por encima de `ytdl-sub` para poder definir perfiles funcionales de descarga a partir de YAML simples y generar automáticamente la configuración final que realmente consume el motor. El sistema ya da soporte validado a seis perfiles: `Canales-youtube`, `Podcast`, `TV-Serie`, `Music-Playlist`, `Ambience-Video` y `Ambience-Audio`. Además, el alcance funcional actual se considera cerrado y no quedan perfiles pendientes dentro de esta fase.  

El objetivo no es editar a mano YAML complejos de `ytdl-sub`, sino trabajar con dos ficheros fuente más legibles (`profiles-custom.yml` y `subscription-custom.yml`) y dejar que el generador construya los presets, las suscripciones y los auxiliares necesarios. fileciteturn1file0 fileciteturn1file1

---

## 2. Para qué sirve

Sirve para descargar distintos tipos de contenido de YouTube con semánticas distintas según el perfil:

- **Canales-youtube**: conserva sólo los N vídeos más recientes de un canal y los organiza como serie por fecha. fileciteturn1file0
- **Podcast**: descarga audio en MP3, con filtro de duración mínima y organización por suscripción lógica y por fuente. fileciteturn1file0
- **TV-Serie**: trata varios canales como una única serie lógica compatible con Jellyfin, con episodios por fecha y `tv_show_name` común. fileciteturn1file0 fileciteturn2file2
- **Music-Playlist**: descarga playlists musicales a MP3 y luego permite enriquecer metadatos con limpieza previa de nombres y beets. fileciteturn2file7 fileciteturn1file7
- **Ambience-Video**: descarga vídeos sueltos y luego los recorta postdescarga a una duración máxima. fileciteturn2file7 fileciteturn2file17
- **Ambience-Audio**: igual que ambience-video, pero extrayendo audio y recortándolo después. fileciteturn1file0 fileciteturn2file2

---

## 3. Arquitectura

## 3.1. Componentes principales

La arquitectura funcional actual se apoya en estos ficheros base:

- `profiles-custom.yml`
- `subscription-custom.yml`
- `generate-ytdl-config.py`
- `prepare-subscriptions-runset.py`
- `clean-music-filenames.ps1`
- `trim-ambience-video.py`
- `beets.music-playlist.yaml` (generado)

El sistema genera automáticamente:

- `config.generated.yaml`
- `subscriptions.generated.yaml`
- `subscriptions.runset.yaml`
- `.recent-items-state.json`
- `.recent-items-state.pending.json`
- `beets.music-playlist.yaml` cuando el conjunto incluye `music-playlist`. fileciteturn1file1 fileciteturn1file17 fileciteturn2file12

## 3.2. Flujo lógico de alto nivel

```text
profiles-custom.yml + subscription-custom.yml
                  │
                  ▼
      generate-ytdl-config.py
                  │
                  ├── config.generated.yaml
                  ├── subscriptions.generated.yaml
                  └── beets.music-playlist.yaml
                  │
                  ▼
    prepare-subscriptions-runset.py
                  │
                  ├── subscriptions.runset.yaml
                  └── .recent-items-state.pending.json
                  │
                  ▼
             ytdl-sub
                  │
                  ├── descargas /downloads/...
                  ├── logs /config/logs/...
                  └── archive files por suscripción
                  │
                  ├── clean-music-filenames.ps1 + beets
                  └── trim-ambience-video.py
                  │
                  ▼
          salida final validada
```

## 3.3. Idea de diseño

El proyecto abandonó el enfoque de montar YAML finales manualmente y se consolidó sobre un sistema de plantillas por tipo de perfil, con generación automática de nombres sanitizados, presets únicos, suscripciones válidas y mapeo entre el modelo funcional y el esquema real soportado por `ytdl-sub`. También quedó fijado que `max_duration` en perfiles ambience no actúa como filtro previo, sino como instrucción de recorte postdescarga. fileciteturn1file1 fileciteturn2file3

---

## 4. Cómo funciona internamente

## 4.1. Modelo fuente: perfiles + suscripciones

`profiles-custom.yml` define los perfiles y sus valores por defecto. En el estado actual hay seis perfiles, con defaults como `max_items`, `quality`, `format`, `min_duration`, `max_duration` y `date_range`. En ambience además se usan `embed_thumbnail: false` y `audio_quality`. fileciteturn1file19

Ejemplo real resumido de perfiles:

```yaml
profiles:
- profile_name: Canales-youtube
  profile_type: Canales-youtube
  defaults:
    max_items: 3
    quality: 720p
    format: mp4
    date_range: 100years

- profile_name: Music-Playlist
  profile_type: Music-Playlist
  defaults:
    max_items: 0
    quality: best
    format: mp3

- profile_name: Ambience-Video
  profile_type: ambience-video
  defaults:
    quality: 1080p
    format: mp4
    max_duration: 3h3m3s
    embed_thumbnail: false
```

`subscription-custom.yml` define las suscripciones concretas, asociando un `profile_name`, un `custom_name` y una lista de `sources`. Cada source puede sobrescribir parámetros del perfil. fileciteturn1file10

Ejemplo real resumido de suscripciones:

```yaml
subscriptions:
- profile_name: Podcast
  custom_name: entrevistas
  sources:
  - url: https://www.youtube.com/@geoestratego_oficial/videos
    max_items: 3
    min_duration: 5m
    quality: best
    format: mp3

- profile_name: TV-Serie
  custom_name: lolete
  sources:
  - url: https://www.youtube.com/@Kerios/videos
    max_items: 3
    min_duration: 5m
    quality: 1080p
    format: mp4
```

## 4.2. Generación de configuración real

`generate-ytdl-config.py`:

- carga ambos YAML fuente;
- normaliza perfiles y suscripciones;
- hace `deep_merge` entre defaults y overrides por source;
- detecta el tipo de descarga (`channel`, `playlist`, `single_video`);
- traduce parámetros funcionales a claves reales de `ytdl-sub`;
- genera `config.generated.yaml` y `subscriptions.generated.yaml`;
- genera también `beets.music-playlist.yaml` cuando hay perfil `music-playlist` en el conjunto. fileciteturn1file17 fileciteturn1file11

Además, el script acepta `--only-profile` para generar únicamente un `profile_type` concreto. fileciteturn1file8

### Traducciones importantes del generador

- Para perfiles no ambience, si `max_items > 0`, se emite `only_recent_max_files` y `only_recent_date_range`. fileciteturn2file14
- `min_duration` se traduce a `filter_duration_min_s`. fileciteturn2file14
- En `ambience-video` y `ambience-audio`, `max_duration` se traduce a `postprocess_trim_max_s`; en el resto, a `filter_duration_max_s`. fileciteturn2file9 fileciteturn2file14
- En `Canales-youtube` y `TV-Serie`, el generador añade `tv_show_name` con la raíz sanitizada de la suscripción. fileciteturn2file14

## 4.3. Runset inteligente

`prepare-subscriptions-runset.py` no vuelve a lanzar siempre todo. Genera un `subscriptions.runset.yaml` que sólo incluye las entradas que realmente toca ejecutar. Para ello:

- lee el estado anterior desde `.recent-items-state.json`;
- consulta IDs recientes o todos los IDs con `yt-dlp --dump-single-json --flat-playlist` dentro del contenedor `ytdl-sub`;
- compara el estado anterior con el actual;
- cuenta ficheros locales por perfil y ruta esperada;
- decide para cada source si hay que hacer `RUN` o `SKIP`. fileciteturn1file18 fileciteturn1file15 fileciteturn1file16

Los criterios principales son:

- si faltan ficheros locales respecto al top esperado, ejecuta;
- si el top reciente no ha cambiado, salta;
- si cambia el top, ejecuta y purga según semántica del perfil;
- en `single_video`, si ya existe el fichero y el estado no ha cambiado, salta;
- si no hay estado previo pero ya existe contenido local en ciertos casos, consolida estado sin relanzar. fileciteturn1file15

## 4.4. Postprocesos

### Music-Playlist

Después de descargar, el flujo puede ejecutar:

1. `clean-music-filenames.ps1`, que limpia títulos problemáticos eliminando etiquetas como `Official Video`, `Lyrics`, `Remastered`, etc., normalizando espacios y guiones.  
2. `beet import` con la configuración de `beets.music-playlist.yaml`, que escribe metadatos embebidos, usa `fromfilename`, `chroma`, `discogs`, `lastgenre`, `scrub`, `fetchart` y `embedart`, y guarda log en `/config/logs/beets-import.log`. fileciteturn1file7

### Ambience

`trim-ambience-video.py` aplica recorte rápido desde el inicio con `ffmpeg`, soporta audio y vídeo, valida duración con `ffprobe`, sustituye el original de forma segura con rollback y evita el problema de `Cross-device link` trabajando en el mismo filesystem del fichero destino. Se usa tanto para ambience-video como para ambience-audio. fileciteturn2file17 fileciteturn2file3

---

## 5. Estructura de ficheros

## 5.1. Ficheros de entrada

### `profiles-custom.yml`
Define los perfiles y sus defaults. fileciteturn1file19

### `subscription-custom.yml`
Define las suscripciones concretas por perfil. fileciteturn1file10

## 5.2. Ficheros generados

### `config.generated.yaml`
Contiene la configuración global y todos los presets reales de `ytdl-sub`, incluyendo `working_directory`, persistencia de logs en `/config/logs` y presets por source. fileciteturn2file8

### `subscriptions.generated.yaml`
Contiene las suscripciones finales, una por preset, con claves como `download_strategy`, `only_recent_max_files`, `filter_duration_min_s`, `tv_show_name` o `postprocess_trim_max_s`. fileciteturn2file2

### `subscriptions.runset.yaml`
Contiene sólo lo que toca ejecutar en una pasada concreta. Lo genera `prepare-subscriptions-runset.py`. fileciteturn1file16

### `.recent-items-state.json` y `.recent-items-state.pending.json`
Persisten el estado de los IDs seleccionados por source para decidir futuras ejecuciones. `pending` se promueve a estado definitivo al final del flujo si la ejecución ha ido bien. fileciteturn2file12

### `beets.music-playlist.yaml`
Config de beets específica para `music-playlist`. Se genera sólo cuando aplica. fileciteturn1file8 fileciteturn1file7

## 5.3. Scripts auxiliares

### `clean-music-filenames.ps1`
Limpia nombres de MP3 antes de pasar beets. 

### `trim-ambience-video.py`
Recorta audio o vídeo descargado desde el segundo 0 hasta la duración máxima pedida. 

### `beets.sh`
Script histórico de postproceso para beets; define `BEETSDIR`, `FPCALC` y ejecuta `beet -v import -q "$1"`. fileciteturn1file13

---

## 6. YAML de configuración: esqueleto y ejemplos

## 6.1. Esqueleto de `profiles-custom.yml`

```yaml
profiles:
- profile_name: Nombre-Visible
  profile_type: Nombre-Tecnico
  defaults:
    max_items: 3
    quality: best
    format: mp4
    min_duration: ''
    max_duration: ''
    date_range: 100years
```

## 6.2. Esqueleto de `subscription-custom.yml`

```yaml
subscriptions:
- profile_name: Nombre-Visible
  custom_name: nombre-logico
  sources:
  - url: https://www.youtube.com/...
    max_items: 3
    quality: best
    format: mp4
    min_duration: ''
    max_duration: ''
```

## 6.3. Ejemplo funcional: Canales-youtube

```yaml
- profile_name: Canales-youtube
  custom_name: ramon-alvarez-de-mon
  sources:
  - url: https://www.youtube.com/@RamonAlvarezdeMon/videos
    max_items: 3
    quality: 720p
    format: mp4
```

Esto termina traducido a un preset con `Jellyfin TV Show by Date`, `Max 720p`, `Only Recent` y `tv_show_directory: /downloads/Canales-youtube`, además de una suscripción con `download_strategy: channel`, `only_recent_max_files: 3` y `tv_show_name: ramon-alvarez-de-mon`. fileciteturn2file8 fileciteturn2file2

## 6.4. Ejemplo funcional: Podcast

```yaml
- profile_name: Podcast
  custom_name: entrevistas
  sources:
  - url: https://www.youtube.com/@geoestratego_oficial/videos
    max_items: 3
    min_duration: 5m
    quality: best
    format: mp3
```

Esto genera `Only Recent + Filter Duration + Max MP3 Quality`, `audio_extract.codec: mp3` y salida bajo `/downloads/Podcast/{subscription_root_sanitized}/{source_target_sanitized}`. fileciteturn2file8

## 6.5. Ejemplo funcional: TV-Serie

```yaml
- profile_name: TV-Serie
  custom_name: lolete
  sources:
  - url: https://www.youtube.com/@Kerios/videos
    max_items: 3
    min_duration: 5m
    quality: 1080p
    format: mp4
  - url: https://www.youtube.com/@nickdaboom/videos
    max_items: 3
    min_duration: 5m
    quality: 720p
    format: mkv
```

Se ha validado que varias fuentes alimenten una sola serie lógica y que cada una use formato distinto, conservando todo bajo la misma serie. fileciteturn1file0 fileciteturn2file3

## 6.6. Ejemplo funcional: Music-Playlist

```yaml
- profile_name: Music-Playlist
  custom_name: music-playlist-prueba
  sources:
  - url: https://www.youtube.com/playlist?list=PLcajSTgNCmdXgFdPc5aeNEVPrzGcr_kUt
    max_items: 0
    quality: best
    format: mp3
```

Con `max_items: 0` no aplica recorte al top reciente y se trata como descarga completa gestionada por estado y archive. fileciteturn1file15

## 6.7. Ejemplo funcional: Ambience-Video

```yaml
- profile_name: Ambience-Video
  custom_name: ambience-video-prueba
  sources:
  - url: https://www.youtube.com/watch?v=5_4KRUx2iKY
    quality: 1080p
    format: mp4
    max_duration: 3h3m3s
```

El generador no emite filtro de duración máxima normal, sino `postprocess_trim_max_s: 10983`. fileciteturn2file2

## 6.8. Ejemplo funcional: Ambience-Audio

```yaml
- profile_name: Ambience-Audio
  custom_name: ambience-audio-prueba
  sources:
  - url: https://www.youtube.com/watch?v=GR_vEjTZBso
    quality: best
    format: mp3
    max_duration: 3h3m3s
```

También se traduce a `single_video` + `postprocess_trim_max_s`. fileciteturn2file2

---

## 7. Walkthroughs de workflows

## 7.1. Workflow completo

1. Editar `profiles-custom.yml` y `subscription-custom.yml`. fileciteturn1file19 fileciteturn1file10
2. Ejecutar el generador:

```powershell
python .\generate-ytdl-config.py
```

3. Preparar el runset inteligente:

```powershell
python .\prepare-subscriptions-runset.py
```

4. Copiar el script de trim al contenedor:

```powershell
docker cp .\trim-ambience-video.py ytdl-sub:/tmp/trim-ambience-video.py
```

5. Ejecutar `ytdl-sub` sobre el runset real:

```powershell
docker exec ytdl-sub sh -lc 'ytdl-sub --config /config/zenoytdl/config.generated.yaml sub /config/zenoytdl/subscriptions.runset.yaml'
```

6. Si existe `.recent-items-state.pending.json`, promoverlo a estado definitivo:

```powershell
Move-Item '.\.recent-items-state.pending.json' '.\.recent-items-state.json' -Force
```

7. Lanzar postproceso music-playlist si aplica:

```powershell
powershell.exe -ExecutionPolicy Bypass -File ".\clean-music-filenames.ps1" -TargetDir "E:\Docker_folders\ydtl-custom-downloads\Music-Playlist\music-playlist-prueba"
docker exec beets-streaming2 sh -lc 'beet -v -c /config/zenoytdl/beets.music-playlist.yaml import -s -q /downloads/Music-Playlist/music-playlist-prueba'
```

8. Lanzar trim de ambience-video y ambience-audio. El test E2E oficial del proyecto ya encapsula estos pasos. fileciteturn2file12

## 7.2. Workflow de un solo perfil

El generador permite filtrar por perfil usando `--only-profile`.

Ejemplo con `music-playlist`:

```powershell
python .\generate-ytdl-config.py --only-profile music-playlist
python .\prepare-subscriptions-runset.py
```

Luego se ejecuta normalmente el runset:

```powershell
docker exec ytdl-sub sh -lc 'ytdl-sub --config /config/zenoytdl/config.generated.yaml sub /config/zenoytdl/subscriptions.runset.yaml'
```

Este modo es útil para iterar sobre un perfil sin regenerar los demás. fileciteturn1file8

## 7.3. Workflow music-playlist

1. Descargar con `ytdl-sub`.
2. Limpiar nombres con `clean-music-filenames.ps1`.
3. Ejecutar beets con el YAML generado.
4. Revisar `beets-import.log` para ver qué temas recibieron metadata y cuáles se saltaron. 

En validación real se confirmó que este flujo descarga bien, embebe thumbnails y permite enriquecer una parte relevante del conjunto sin romper los casos sin match. fileciteturn2file7 fileciteturn1file7

## 7.4. Workflow ambience

1. Descargar el media completo con `ytdl-sub`.
2. Recortar después con `trim-ambience-video.py --replace --skip-output-probe` o con validación final si prefieres mayor seguridad.
3. Verificar duración final y ausencia de residuos `.bak`, `.tmp`, `.part` y `.trimmed`. fileciteturn2file17

---

## 8. Guía de uso

## 8.1. Cómo se lanza completo

La forma estándar, tal como está reflejada en el E2E, es:

```powershell
Set-Location "E:\Docker_folders\streaming2\ytdl-sub\config\zenoytdl"
python .\generate-ytdl-config.py
python .\prepare-subscriptions-runset.py
docker cp .\trim-ambience-video.py ytdl-sub:/tmp/trim-ambience-video.py
docker exec ytdl-sub sh -lc 'ytdl-sub --config /config/zenoytdl/config.generated.yaml sub /config/zenoytdl/subscriptions.runset.yaml'
Move-Item '.\.recent-items-state.pending.json' '.\.recent-items-state.json' -Force
```

Después, ejecutar los postprocesos necesarios por perfil. fileciteturn2file12

## 8.2. Cómo se lanza con un solo perfil

```powershell
python .\generate-ytdl-config.py --only-profile podcast
python .\prepare-subscriptions-runset.py
docker exec ytdl-sub sh -lc 'ytdl-sub --config /config/zenoytdl/config.generated.yaml sub /config/zenoytdl/subscriptions.runset.yaml'
```

Cambia `podcast` por cualquier `profile_type` sanitizado soportado, por ejemplo:

- `canales-youtube`
- `podcast`
- `tv-serie`
- `music-playlist`
- `ambience-video`
- `ambience-audio` fileciteturn1file19 fileciteturn1file8

## 8.3. Modos de lanzamiento

### Modo 1: Generación solamente

Útil para revisar YAML antes de ejecutar nada.

```powershell
python .\generate-ytdl-config.py
Get-Content .\config.generated.yaml -TotalCount 120
Get-Content .\subscriptions.generated.yaml
```

### Modo 2: Generación + runset inteligente

Útil para decidir qué toca ejecutar y qué se puede saltar.

```powershell
python .\generate-ytdl-config.py
python .\prepare-subscriptions-runset.py
Get-Content .\subscriptions.runset.yaml
```

### Modo 3: Ejecución real completa

```powershell
docker exec ytdl-sub sh -lc 'ytdl-sub --config /config/zenoytdl/config.generated.yaml sub /config/zenoytdl/subscriptions.runset.yaml'
```

### Modo 4: Sólo limpieza y metadata musical

```powershell
powershell.exe -ExecutionPolicy Bypass -File ".\clean-music-filenames.ps1" -TargetDir "E:\Docker_folders\ydtl-custom-downloads\Music-Playlist\music-playlist-prueba"
docker exec beets-streaming2 sh -lc 'beet -v -c /config/zenoytdl/beets.music-playlist.yaml import -s -q /downloads/Music-Playlist/music-playlist-prueba'
```

### Modo 5: Sólo trim de ambience

Ejemplo manual sobre un fichero:

```powershell
python .\trim-ambience-video.py --input "E:\ruta\al\fichero.mp4" --max-duration 03:03:03 --replace --skip-output-probe
```

Las opciones soportadas por el script incluyen `--replace`, `--faststart` y `--skip-output-probe`. fileciteturn2file17

---

## 9. Rutas y salida esperada

La ruta host validada de descargas es:

```text
E:\Docker_folders\ydtl-custom-downloads
```

Rutas validadas por perfil:

```text
E:\Docker_folders\ydtl-custom-downloads\Canales-youtube\ramon-alvarez-de-mon
E:\Docker_folders\ydtl-custom-downloads\Podcast\entrevistas\geoestratego-oficial
E:\Docker_folders\ydtl-custom-downloads\Podcast\entrevistas\pl01fnqnul7ykui7id1lwxkz8ho3j8l8of
E:\Docker_folders\ydtl-custom-downloads\TV-Serie\lolete
E:\Docker_folders\ydtl-custom-downloads\Music-Playlist\music-playlist-prueba
E:\Docker_folders\ydtl-custom-downloads\Ambience-Video\ambience-video-prueba
E:\Docker_folders\ydtl-custom-downloads\Ambience-Audio\ambience-audio-prueba
```

fileciteturn2file4

---

## 10. Tests

## 10.1. Filosofía de test

El proyecto incluye un flujo de test E2E real, más dos bloques de prueba prácticos para `music-playlist` y un script de validación posterior. El objetivo no es test unitario puro, sino verificar que el pipeline completo genera YAML válido, descarga, postprocesa y deja salida consistente en disco. Esto encaja con el documento de estado, donde todos los perfiles actuales figuran como validados en real. fileciteturn1file0

## 10.2. Test principal: `test-e2e-perfiles-subscriptions.ps1`

Este script:

1. prepara el contexto sin borrar descargas existentes;
2. mata procesos viejos y limpia locks y `working_directory` temporal;
3. regenera `config.generated.yaml` y `subscriptions.generated.yaml`;
4. regenera `subscriptions.runset.yaml`;
5. copia `trim-ambience-video.py` al contenedor;
6. ejecuta `ytdl-sub` sobre el runset real;
7. promueve `.recent-items-state.pending.json` a `.recent-items-state.json`;
8. ejecuta limpieza + beets para `music-playlist`;
9. ejecuta el recorte para `ambience-video` y `ambience-audio`. 

Es el script de referencia para una pasada completa. Sus pasos se ven explícitamente en el propio `.ps1`. 

## 10.3. Validación posterior: `validate-test-e2e-perfiles-subscriptions.ps1`

Este script comprueba:

- que los YAML generados existen y son coherentes;
- árbol final de directorios y ficheros;
- recuento de vídeos, MP3 y NFO por perfil;
- duración, tamaño y streams de ambience-video y ambience-audio;
- que las duraciones finales queden en torno a 10983 s;
- que no queden residuos temporales;
- codec/sample rate/channels de MP3 de podcast y music-playlist;
- logs relevantes en `/config/logs`;
- estado del `working_directory` y basura temporal en `/tmp`. 

## 10.4. Bloques rápidos de prueba para `music-playlist`

### `bloque1-test.ps1`

Hace una prueba de arranque “limpia” del perfil musical:

- borra la carpeta de salida `music-playlist-prueba`;
- limpia working dir temporal de ese source;
- borra logs previos del source;
- resetea `musiclibrary.db` y `beets-import.log` en `beets-streaming2`;
- ejecuta `test-e2e-perfiles-subscriptions.ps1`;
- cuenta MP3 resultantes;
- localiza el último log de music-playlist;
- vuelca todo a un log local llamado `bloque1-music-playlist-YYYYMMDD-HHMMSS.log`.

### `bloque2-test.ps1`

Hace una segunda pasada sin limpieza inicial, pensada para validar idempotencia y comportamiento incremental:

- relanza `test-e2e-perfiles-subscriptions.ps1`;
- vuelve a contar MP3 finales;
- cuenta apariciones de `has already been recorded in the archive` en el último log del source;
- muestra las últimas 80 líneas del log de beets;
- guarda todo en `bloque2-music-playlist-YYYYMMDD-HHMMSS.log`.

Este segundo bloque es muy útil para confirmar que no hay redescargas innecesarias cuando el archive y el estado ya están consolidados. 

## 10.5. Dónde guardan logs

### Logs del propio sistema

- `config.generated.yaml` configura `persist_logs.keep_successful_logs: true` y `persist_logs.logs_directory: /config/logs`. fileciteturn2file8
- `beets.music-playlist.yaml` guarda su log en `/config/logs/beets-import.log`. fileciteturn1file7

### Logs locales PowerShell de bloques

- `bloque1-test.ps1` genera `bloque1-music-playlist-<timestamp>.log` en el directorio actual.
- `bloque2-test.ps1` genera `bloque2-music-playlist-<timestamp>.log` en el directorio actual.

## 10.6. Qué valida cada test, en resumen

- **test-e2e-perfiles-subscriptions.ps1**: ejecución completa real.
- **validate-test-e2e-perfiles-subscriptions.ps1**: inspección y validación detallada de resultados.
- **bloque1-test.ps1**: prueba limpia específica de `music-playlist`.
- **bloque2-test.ps1**: segunda pasada para validar no redescarga, archive y estabilidad.

---

## 11. Limitaciones y notas operativas

- Los warnings ocasionales de `yt-dlp` relacionados con `deno` o `n challenge solving failed` se consideran una limitación del entorno y no un bloqueo funcional, porque en las pruebas reales no impidieron obtener el resultado correcto. fileciteturn1file3
- En `music-playlist`, no todos los temas van a conseguir metadata enriquecida. Eso ya se asumió como limitación conocida y no invalida el perfil. fileciteturn2file7
- El script de trim debe trabajar en el mismo filesystem del fichero objetivo para evitar errores de `Cross-device link`. fileciteturn2file3

---

## 12. Estado del proyecto

A día de hoy, el conjunto actual de perfiles queda cerrado para esta fase del proyecto. Los perfiles validados en real son:

1. `Canales-youtube`
2. `Podcast`
3. `TV-Serie`
4. `music-playlist`
5. `ambience-video`
6. `ambience-audio` 

Y los perfiles contemplados en algún momento como `Enlace-suelto`, `music-discos` y `shorts` quedaron descartados por redundancia funcional respecto a los ya existentes. fileciteturn1file4
