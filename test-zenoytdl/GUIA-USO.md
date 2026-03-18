# Guía de uso — test-zenoytdl

Esta carpeta sustituye a los tests antiguos con una estructura nueva, logs por ejecución y lanzadores reutilizables.

## Contenido

- `_shared.ps1`: funciones comunes, utilidades de logging, filtrado del runset y postprocesos.
- `run-profile-test.ps1`: ejecuta un único perfil.
- `run-e2e.ps1`: ejecuta todos los perfiles uno detrás de otro.
- `validate-downloads.ps1`: hace la validación global y genera un log amplio de inventario, conteos, ffprobe y logs de contenedores.
- `logs/`: aquí se crea automáticamente un subárbol por test y timestamp.

## Requisitos asumidos

- Esta carpeta debe quedar dentro del proyecto, como hermana de los ficheros reales (`profiles-custom.yml`, `subscription-custom.yml`, `generate-ytdl-config.py`, etc.).
- El proyecto debe seguir viviendo en la ruta que ya usas dentro del contenedor: `/config/zenoytdl`.
- Deben existir los contenedores `ytdl-sub` y `beets-streaming2`.
- Debe estar disponible `python` en Windows y en el contenedor `ytdl-sub`.

## Ubicación esperada

```text
E:\Docker_folders\streaming2\ytdl-sub\config\zenoytdl\
├── profiles-custom.yml
├── subscription-custom.yml
├── generate-ytdl-config.py
├── prepare-subscriptions-runset.py
├── trim-ambience-video.py
├── clean-music-filenames.ps1
├── ...
└── test-zenoytdl\
    ├── _shared.ps1
    ├── run-profile-test.ps1
    ├── run-e2e.ps1
    ├── validate-downloads.ps1
    ├── GUIA-USO.md
    └── logs\
```

## 1) Lanzar un único perfil

Sintaxis:

```powershell
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\run-profile-test.ps1 -ProfileName "<PERFIL>" -ClearDownloads:$false -DryRun:$false
```

Perfiles válidos:

- `Canales-youtube`
- `Podcast`
- `TV-Serie`
- `Music-Playlist`
- `Ambience-Video`
- `Ambience-Audio`

Ejemplos:

```powershell
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\run-profile-test.ps1 -ProfileName "Music-Playlist" -ClearDownloads:$true -DryRun:$false
```

```powershell
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\run-profile-test.ps1 -ProfileName "Ambience-Video" -ClearDownloads:$false -DryRun:$true
```

### Qué hace

- opcionalmente borra las descargas del perfil elegido;
- limpia locks y `working_directory`;
- regenera `config.generated.yaml` y `subscriptions.runset.yaml`;
- filtra el runset para dejar solo el perfil pedido;
- si no está en dry-run, ejecuta la descarga real;
- si aplica, ejecuta postproceso (`beets` o `trim`);
- captura logs relevantes del contenedor;
- informa al final de la ruta exacta de logs.

## 2) Lanzar el E2E completo

Sintaxis:

```powershell
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\run-e2e.ps1 -ClearDownloads:$false -DryRun:$false
```

Ejemplos:

```powershell
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\run-e2e.ps1 -ClearDownloads:$true -DryRun:$true
```

```powershell
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\run-e2e.ps1 -ClearDownloads:$false -DryRun:$false
```

### Qué hace

- llama a `run-profile-test.ps1` para cada perfil;
- conserva logs separados por hijo y otro log maestro del E2E;
- al final llama automáticamente a `validate-downloads.ps1`.

## 3) Lanzar solo el validador

Sintaxis:

```powershell
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\validate-downloads.ps1 -DryRun:$false
```

Ejemplo:

```powershell
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\validate-downloads.ps1 -DryRun:$true
```

### Qué valida

- existencia y fecha de los YAML y estados;
- árbol completo de rutas por perfil;
- conteo de ficheros por extensión relevante;
- inspección `ffprobe` de audio/vídeo;
- logs recientes de `ytdl-sub` y `beets`;
- working directory y restos temporales.

## Estructura de logs

Cada script crea:

```text
test-zenoytdl\logs\<nombre-test>\yyyyMMdd-HHmmss\
```

Dentro encontrarás normalmente:

- `<test>.log`: log principal de ejecución.
- `<test>.transcript.log`: transcript completo de PowerShell.
- `<test>.summary.log`: resumen con rutas clave.

## Nota importante sobre dry-run

En estos tests, `dry-run` significa:

- sí se regeneran YAML, estado pendiente y runset filtrado;
- sí se inspecciona y se deja log de lo que tocaría ejecutarse;
- no se lanza la descarga real de `ytdl-sub`;
- no se ejecutan postprocesos.

## Orden recomendado de prueba

1. `run-profile-test.ps1` con un perfil y `-DryRun:$true`
2. `run-profile-test.ps1` con ese perfil y `-DryRun:$false`
3. `validate-downloads.ps1`
4. `run-e2e.ps1`
