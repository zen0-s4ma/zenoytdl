# ZenoYTDL — README actualizado

## Qué es

ZenoYTDL es una capa declarativa sobre `ytdl-sub` para definir perfiles de descarga de YouTube con YAML simples y generar automáticamente la configuración real que consume el motor.

La idea del proyecto es separar tres niveles:

1. **Intención funcional**: qué tipo de contenido quieres descargar.
2. **Compilación**: transformar esa intención en presets y suscripciones válidas para `ytdl-sub`.
3. **Ejecución inteligente**: decidir qué entradas merece la pena lanzar según el estado previo y lo que ya existe en disco.

Actualmente el proyecto trabaja con seis perfiles funcionales:

- `Canales-youtube`
- `Podcast`
- `TV-Serie`
- `Music-Playlist`
- `Ambience-Video`
- `Ambience-Audio`

---

## Estructura real del proyecto

Ruta objetivo del proyecto en Windows:

```text
E:\Docker_folders\streaming2\ytdl-sub\config\zenoytdl
```

Estructura principal:

```text
zenoytdl\
├── README.md
├── DOSSIER-TECNICO.md
├── EJEMPLOS.md
├── README-mudanza-ruta.txt
├── profiles-custom.yml
├── subscription-custom.yml
├── generate-ytdl-config.py
├── prepare-subscriptions-runset.py
├── trim-ambience-video.py
├── clean-music-filenames.ps1
├── run-master-tests.ps1
├── test-e2e-perfiles-subscriptions.ps1
├── validate-test-e2e-perfiles-subscriptions.ps1
├── config.generated.yaml
├── subscriptions.generated.yaml
├── subscriptions.runset.yaml
├── subscriptions.runset.filtered.yaml
├── .recent-items-state.json
├── .recent-items-state.pending.json
├── .recent-items-state.pending.filtered.json
├── beets.music-playlist.yaml
└── test-zenoytdl\
    ├── GUIA-USO.md
    ├── _shared.ps1
    ├── _run-all-test.ps1
    ├── clean-windows-environment.ps1
    ├── run-profile-test.ps1
    ├── run-e2e.ps1
    ├── validate-downloads.ps1
    ├── test-beets-only.ps1
    ├── test-trim-only.ps1
    ├── listado-comandos-lanzar-ps1.txt
    └── logs\
```

---

## Ficheros fuente que editas a mano

### `profiles-custom.yml`
Define los perfiles y sus valores por defecto.

Campos que el código usa actualmente:

- `profile_name`
- `profile_type`
- `defaults.max_items`
- `defaults.quality`
- `defaults.format`
- `defaults.min_duration`
- `defaults.max_duration`
- `defaults.date_range`
- `defaults.embed_thumbnail`
- `defaults.audio_quality`
- `defaults.enable_throttle_protection` si lo añades

### `subscription-custom.yml`
Define las suscripciones concretas.

Cada suscripción tiene:

- `profile_name`
- `custom_name`
- `sources[]`

Y cada fuente puede llevar, entre otros:

- `url`
- `max_items`
- `quality`
- `format`
- `min_duration`
- `max_duration`
- `date_range`
- `embed_thumbnail`
- `audio_quality`

El generador fusiona defaults del perfil con overrides de cada fuente.

---

## Qué genera el sistema

### `generate-ytdl-config.py`
Genera:

- `config.generated.yaml`
- `subscriptions.generated.yaml`
- `beets.music-playlist.yaml` si existe al menos una suscripción `music-playlist`

También permite limitar la generación a un perfil:

```powershell
python .\generate-ytdl-config.py --only-profile music-playlist
```

### `prepare-subscriptions-runset.py`
Genera:

- `subscriptions.runset.yaml`
- `.recent-items-state.pending.json`

Su función es preparar un **runset inteligente** usando:

- lo que ya hay descargado en `/downloads/...`
- los IDs recientes detectados desde YouTube
- el estado guardado en `.recent-items-state.json`

Con ello evita relanzar trabajo innecesario y decide qué fuentes deben entrar en la siguiente ejecución.

---

## Comportamiento por perfil

### 1. `Canales-youtube`
- Usa preset base `Jellyfin TV Show by Date`.
- Puede añadir `Max 720p` o `Max 1080p`.
- Si `max_items > 0`, activa `Only Recent`.
- Sale en:
  - `/downloads/Canales-youtube/{subscription_root}`
- Marca `tv_show_name = subscription_root`.

### 2. `Podcast`
- Fuerza extracción de audio MP3.
- Usa `Filter Duration` y `Max MP3 Quality`.
- Si `max_items > 0`, añade `Only Recent`.
- Sale en:
  - `/downloads/Podcast/{subscription_root}/{source_target}`

### 3. `TV-Serie`
- Usa `Jellyfin TV Show by Date`.
- Añade filtro de duración.
- Permite `720p`, `1080p` o `best`.
- Sale en:
  - `/downloads/TV-Serie/{subscription_root}`
- Marca `tv_show_name = subscription_root`.

### 4. `Music-Playlist`
- Extrae audio MP3.
- Usa `Max MP3 Quality`.
- Si `max_items > 0`, añade `Only Recent`.
- Sale en:
  - `/downloads/Music-Playlist/{subscription_root}`
- Mantiene archivo de descarga.
- Tiene postproceso con `beets`.

### 5. `Ambience-Video`
- Descarga vídeo en el contenedor `ytdl-sub`.
- Sale en:
  - `/downloads/Ambience-Video/{subscription_root}`
- No aplica `Only Recent`.
- El límite máximo de duración se guarda para **trim posterior**, no como filtro de descarga.

### 6. `Ambience-Audio`
- Extrae audio MP3.
- Sale en:
  - `/downloads/Ambience-Audio/{subscription_root}`
- Igual que ambience-video, el `max_duration` se usa como recorte posterior.

---

## Flujo recomendado de trabajo

### Flujo manual completo

Desde:

```powershell
cd E:\Docker_folders\streaming2\ytdl-sub\config\zenoytdl
```

1. Generar configuración:

```powershell
python .\generate-ytdl-config.py
```

2. Preparar runset inteligente:

```powershell
python .\prepare-subscriptions-runset.py
```

3. Copiar script de trim al contenedor:

```powershell
docker cp .\trim-ambience-video.py ytdl-sub:/tmp/trim-ambience-video.py
```

4. Ejecutar `ytdl-sub` con el runset:

```powershell
docker exec ytdl-sub ytdl-sub --config /config/zenoytdl/config.generated.yaml sub /config/zenoytdl/subscriptions.runset.yaml
```

5. Si hay música, lanzar `beets`:

```powershell
docker exec beets-streaming2 sh -lc 'find /downloads/Music-Playlist -mindepth 1 -maxdepth 1 -type d | while read -r d; do beet -v -c /config/zenoytdl/beets.music-playlist.yaml import -s -q "$d" || true; done'
```

6. Si hay ambience, recortar:

```powershell
docker exec ytdl-sub sh -lc 'find /downloads/Ambience-Video -type f \( -iname "*.mp4" -o -iname "*.mkv" -o -iname "*.webm" -o -iname "*.mov" -o -iname "*.m4v" -o -iname "*.avi" \) | while IFS= read -r f; do python /tmp/trim-ambience-video.py --input "$f" --max-duration 03:03:03 --replace --skip-output-probe; done'
```

---

## Flujo recomendado de tests

La batería nueva vive en `test-zenoytdl\` y es la más mantenible ahora mismo.

### Scripts principales nuevos

- `test-zenoytdl\run-profile-test.ps1`
- `test-zenoytdl\run-e2e.ps1`
- `test-zenoytdl\validate-downloads.ps1`
- `test-zenoytdl\test-beets-only.ps1`
- `test-zenoytdl\test-trim-only.ps1`
- `test-zenoytdl\clean-windows-environment.ps1`
- `test-zenoytdl\_run-all-test.ps1`

### Script legacy que sigue existiendo

- `test-e2e-perfiles-subscriptions.ps1`
- `validate-test-e2e-perfiles-subscriptions.ps1`

Estos scripts antiguos siguen siendo útiles como referencia o compatibilidad, pero la suite nueva de `test-zenoytdl` es la recomendada para trabajar y validar cambios.

---

## Estado y runset inteligente

### Ficheros de estado

- `.recent-items-state.json`: estado consolidado actual
- `.recent-items-state.pending.json`: estado pendiente generado por el preparador
- `.recent-items-state.pending.filtered.json`: estado pendiente del runset filtrado en los tests nuevos

### Idea de funcionamiento

El preparador intenta responder a esta pregunta:

> ¿Qué fuentes tienen novedades reales o necesitan completarse según el número de elementos esperado y lo que ya hay en disco?

Para eso combina:

- conteo real de ficheros por perfil en `/downloads/...`
- IDs recuperados desde YouTube
- estado consolidado de la ejecución anterior

Tras una ejecución exitosa de la suite nueva, `run-profile-test.ps1` puede promocionar el estado filtrado a `.recent-items-state.json`.

---

## Requisitos operativos

### En Windows

- PowerShell
- Python accesible como `python`
- Docker Desktop funcionando

### Contenedores esperados

- `ytdl-sub`
- `beets-streaming2`

### Dentro del contenedor `ytdl-sub`

- `ytdl-sub`
- `python`
- `ffmpeg` / `ffprobe`

### Dentro del contenedor `beets-streaming2`

- `beet`
- acceso a `/config/zenoytdl/beets.music-playlist.yaml`

---

## Comandos rápidos útiles

### Probar un perfil

```powershell
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\run-profile-test.ps1 -ProfileName "Music-Playlist" -ClearDownloads:$false -DryRun:$false
```

### Probar todo el E2E

```powershell
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\run-e2e.ps1 -ClearDownloads:$false -DryRun:$false
```

### Validar inventario completo

```powershell
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\validate-downloads.ps1 -DryRun:$false
```

### Limpiar entorno de pruebas

```powershell
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\clean-windows-environment.ps1 -CleanLogs
```

### Lanzar la batería maestra

```powershell
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\_run-all-test.ps1
```

O, si quieres la secuencia legacy en ventanas nuevas:

```powershell
powershell -ExecutionPolicy Bypass -File .\run-master-tests.ps1
```

---

## Dónde colocar estos Markdown

Todos los `.md` y el `README-mudanza-ruta.txt` de este paquete deben copiarse manteniendo esta estructura:

```text
E:\Docker_folders\streaming2\ytdl-sub\config\zenoytdl\README.md
E:\Docker_folders\streaming2\ytdl-sub\config\zenoytdl\DOSSIER-TECNICO.md
E:\Docker_folders\streaming2\ytdl-sub\config\zenoytdl\EJEMPLOS.md
E:\Docker_folders\streaming2\ytdl-sub\config\zenoytdl\README-mudanza-ruta.txt
E:\Docker_folders\streaming2\ytdl-sub\config\zenoytdl\test-zenoytdl\GUIA-USO.md
```

---

## Observaciones importantes

- La documentación antigua tenía restos de citas de chat incrustadas; ya no deben usarse.
- La suite de pruebas nueva trabaja con `subscriptions.runset.filtered.yaml` y `.recent-items-state.pending.filtered.json`.
- `Music-Playlist` tiene `max_items: 0` en el ejemplo actual, por lo que se comporta como descarga no limitada por recencia.
- `Ambience-Video` y `Ambience-Audio` no filtran por duración máxima durante la descarga: recortan después.
- Los Python del proyecto usan `BASE_DIR = Path(__file__).resolve().parent`, por lo que la carpeta `zenoytdl` es la unidad real de despliegue.
