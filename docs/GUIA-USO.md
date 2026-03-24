# Guía de uso — suite Python `test-zenoytdl`

Esta carpeta contiene la nueva suite de pruebas del proyecto y pasa a ser la forma recomendada de validar cambios en perfiles, generación, runset, postprocesos y descargas.

---

## Ubicación esperada

```text
E:\Docker_folders\streaming2\ytdl-sub\config\zenoytdl\test-zenoytdl
```

Su carpeta padre debe ser la raíz real del proyecto:

```text
E:\Docker_folders\streaming2\ytdl-sub\config\zenoytdl
```

---

## Qué hay en esta carpeta

- `run_tests.py`: batería principal de pruebas en Python.
- `GUIA-USO.md`: guía operativa de la suite.
- `listado-comandos-python.txt`: chuleta de comandos.
- `logs\`: un único log por ejecución.

---

## Requisitos

### Host

- Python 3
- Docker funcionando
- `PyYAML`

### Contenedores

- `ytdl-sub`
- `beets-streaming2`

### Herramientas internas esperadas

En `ytdl-sub`:

- `ytdl-sub`
- `yt-dlp`
- `python`
- `ffmpeg`
- `ffprobe`

En `beets-streaming2`:

- `beet`

---

## Perfiles válidos

- `Canales-youtube`
- `Podcast`
- `TV-Serie`
- `Music-Playlist`
- `Ambience-Video`
- `Ambience-Audio`

---

## Comando principal

### Probar un perfil

```powershell
python .\test-zenoytdl\run_tests.py --profile "Music-Playlist" --clean
```

### Probar todos los perfiles

```powershell
python .\test-zenoytdl\run_tests.py --all-profiles --clean
```

---

## Parámetros

### `--profile "<PERFIL>"`

Prueba un perfil concreto.

Puede repetirse si quieres indicar varios perfiles concretos:

```powershell
python .\test-zenoytdl\run_tests.py --profile "Podcast" --profile "TV-Serie" --clean
```

### `--all-profiles`

Recorre todos los perfiles, uno por uno, en la misma ejecución.

### `--dry-run`

Genera config y runset, pero no lanza descargas reales ni postprocesos.

### `--clean`

Hace limpieza previa.

Comportamiento:

- si pruebas un perfil, limpia solo su alcance;
- si usas `--all-profiles`, hace limpieza general;
- además vacía `test-zenoytdl\logs` salvo que se use `--keep-logs`.

### `--keep-logs`

Conserva los logs anteriores aunque se use `--clean`.

---

## Qué hace internamente

Para cada perfil:

1. genera `config.generated.yaml` solo para ese perfil;
2. genera `subscriptions.runset.yaml` filtrado al perfil actual;
3. revisa si el runset tiene entradas reales;
4. si no es dry-run, ejecuta `ytdl-sub`;
5. promueve `.recent-items-state.pending.json` a `.recent-items-state.json`;
6. lanza postproceso si aplica;
7. captura logs relevantes de contenedores;
8. añade el resultado al resumen final.

---

## Postproceso automático

- `Music-Playlist` → importación con `beets`
- `Ambience-Video` → trim con `trim-ambience-video.py`
- `Ambience-Audio` → trim con `trim-ambience-video.py`
- resto → sin postproceso específico

---

## Ejemplos prácticos

### Dry-run de `Podcast`

```powershell
python .\test-zenoytdl\run_tests.py --profile "Podcast" --clean --dry-run
```

### Real de `Ambience-Video`

```powershell
python .\test-zenoytdl\run_tests.py --profile "Ambience-Video" --clean
```

### Regresión completa

```powershell
python .\test-zenoytdl\run_tests.py --all-profiles --clean
```

---

## Logs

Cada ejecución genera un único fichero:

```text
test-zenoytdl\logs\zenoytdl-test-suite-YYYYMMDD-HHMMSS.log
```

Ese log incluye:

- limpieza previa;
- comandos lanzados;
- stdout y stderr de subprocess;
- captura resumida de logs de contenedores;
- resumen final por perfil.

---

## Recomendación operativa

Para una batería seria después de tocar YAML, generadores o lógica de selección:

```powershell
python .\test-zenoytdl\run_tests.py --all-profiles --clean
```

Para iterar más rápido sobre un único perfil:

```powershell
python .\test-zenoytdl\run_tests.py --profile "Music-Playlist" --clean
```
