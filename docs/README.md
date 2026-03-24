# ZenoYTDL

## Qué es

ZenoYTDL es una capa declarativa sobre `ytdl-sub` para definir perfiles de descarga de YouTube con YAML simples y generar automáticamente la configuración real que consume el motor.

El proyecto separa tres niveles:

1. **Intención funcional**: qué tipo de contenido quieres descargar.
2. **Compilación**: transformar esa intención en presets y suscripciones válidas para `ytdl-sub`.
3. **Ejecución inteligente**: decidir qué entradas merece la pena lanzar según el estado previo y lo que ya existe en disco.

Perfiles funcionales actuales:

- `Canales-youtube`
- `Podcast`
- `TV-Serie`
- `Music-Playlist`
- `Ambience-Video`
- `Ambience-Audio`

---

## Ruta real del proyecto

Ruta objetivo en Windows:

```text
E:\Docker_folders\streaming2\ytdl-sub\config\zenoytdl
```

---

## Estructura principal actual

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
├── config.generated.yaml
├── subscriptions.generated.yaml
├── beets.music-playlist.yaml
└── test-zenoytdl\
    ├── run_tests.py
    ├── GUIA-USO.md
    ├── listado-comandos-python.txt
    └── logs\
```

La parte de pruebas recomendada pasa a ser **solo Python**.

---

## Ficheros fuente que editas a mano

### `profiles-custom.yml`

Define perfiles y valores por defecto.

Campos usados por el código actual:

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
- `defaults.enable_throttle_protection` si se añade

### `subscription-custom.yml`

Define suscripciones concretas.

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

Ejemplo:

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

## Nueva forma de probar el proyecto

La forma recomendada de pruebas ya no usa PowerShell como orquestador de tests.

Ahora la batería se lanza con:

```powershell
python .\test-zenoytdl\run_tests.py --all-profiles --clean
```

O para un solo perfil:

```powershell
python .\test-zenoytdl\run_tests.py --profile "Music-Playlist" --clean
```

### Parámetros principales

- `--profile "<PERFIL>"`: prueba un perfil concreto
- `--all-profiles`: recorre todos los perfiles uno por uno
- `--dry-run`: genera config y runset, pero no descarga ni postprocesa
- `--clean`: limpia antes de empezar
- `--keep-logs`: no borra logs anteriores

### Qué hace la suite Python

1. Limpia entorno local y contenedores si se ha pedido.
2. Genera `config.generated.yaml` solo para el perfil en prueba.
3. Genera `subscriptions.runset.yaml` scoped al perfil actual.
4. Comprueba si el runset tiene entradas reales.
5. Si no es dry-run, ejecuta `ytdl-sub`.
6. Promueve `.recent-items-state.pending.json` a `.recent-items-state.json` cuando procede.
7. Lanza postproceso automático para:
   - `Music-Playlist` → `beets`
   - `Ambience-Video` → trim
   - `Ambience-Audio` → trim
8. Captura todo en **un único log por ejecución**.

---

## Requisitos operativos

### Host

- Python 3
- Docker funcionando
- `PyYAML` disponible

### Contenedores esperados

- `ytdl-sub`
- `beets-streaming2`

### Herramientas esperadas dentro de contenedores

En `ytdl-sub`:

- `ytdl-sub`
- `yt-dlp`
- `python`
- `ffmpeg`
- `ffprobe`

En `beets-streaming2`:

- `beet`

---

## Ejemplos rápidos

### Probar `Podcast` en dry-run

```powershell
python .\test-zenoytdl\run_tests.py --profile "Podcast" --clean --dry-run
```

### Probar `Music-Playlist` real con limpieza previa

```powershell
python .\test-zenoytdl\run_tests.py --profile "Music-Playlist" --clean
```

### Lanzar batería completa real

```powershell
python .\test-zenoytdl\run_tests.py --all-profiles --clean
```

---

## Logs

Cada ejecución genera un único log dentro de:

```text
E:\Docker_folders\streaming2\ytdl-sub\config\zenoytdl\test-zenoytdl\logs
```

Nombre esperado:

```text
zenoytdl-test-suite-YYYYMMDD-HHMMSS.log
```

Ese log incluye:

- limpieza
- generación
- preparación de runset
- ejecución de `ytdl-sub`
- postproceso
- captura resumida de logs de contenedores
- resumen final por perfil

---

## Documentación complementaria

- `DOSSIER-TECNICO.md`
- `EJEMPLOS.md`
- `test-zenoytdl\GUIA-USO.md`
- `test-zenoytdl\listado-comandos-python.txt`
