# Entorno de ejecución en contenedor (Linux)

> Este documento define el **runtime objetivo de Hito 1** según `hitos-and-test.md`.
> No implica cierre de hitos posteriores (incluido Hito 22).

## Runtime objetivo soportado
- Plataforma soportada: **Linux containerizado**.
- Patrón de ejecución: **un proceso principal** (sin supervisor adicional en esta fase).
- Usuario recomendado: **no root** con permisos de escritura sobre rutas persistentes en `/data`.

## Layout oficial de rutas

### Configuración (bind mount, solo lectura recomendada)
- `/config/general.yaml`
- `/config/profiles.yaml`
- `/config/subscriptions.yaml`
- `/config/integrations.yaml`
- `/config/cache.yaml`
- `/config/queues.yaml`
- `/config/logging.yaml`

### Persistencia (volúmenes)
Rutas persistentes oficiales del runtime:
- `/data/library`
- `/data/tmp`
- `/data/logs`
- `/data/state.sqlite`
- `/data/cache.sqlite`
- `/data/compiled-ytdl-sub`

## Política de persistencia y reinicios
- Deben **sobrevivir a reinicios/recreaciones** del contenedor:
  - base de datos de estado (`/data/state.sqlite`),
  - caché (`/data/cache.sqlite`),
  - artefactos compilados (`/data/compiled-ytdl-sub`),
  - biblioteca descargada (`/data/library`),
  - logs persistidos en disco (`/data/logs`) si se habilitan.
- `/data/tmp` se considera persistente por layout, pero su contenido puede limpiarse por políticas operativas.

## Política de binarios (`ffmpeg`, `ffprobe`, `ytdl-sub`)
- Los binarios deben estar disponibles **dentro de la imagen** (no depender de instalación en host).
- Resolución esperada:
  - `ffmpeg` y `ffprobe`: disponibles en `PATH`.
  - `ytdl-sub`: disponible en `PATH`.
- Se permite override por variables de entorno si el runtime lo implementa, pero el valor por defecto debe funcionar con `PATH`.

## Logs
- Mínimo obligatorio: salida operativa a `stdout/stderr`.
- Opcional: logs estructurados/JSON en `/data/logs` para retención en volumen.

## Healthcheck esperado
El healthcheck del contenedor debe validar, como mínimo:
1. binarios críticos resolubles (`ffmpeg`, `ffprobe`, `ytdl-sub`),
2. existencia de rutas persistentes,
3. permisos de escritura en `/data/logs` y en `/data`.

Ejemplo de criterio (shell):
- `command -v ffmpeg`
- `command -v ffprobe`
- `command -v ytdl-sub`
- `test -d /data/library -a -d /data/logs -a -d /data/compiled-ytdl-sub`
- `test -w /data -a -w /data/logs`

## Validación en pipeline local/CI
Para auditoría de Hito 1, el pipeline debe incluir checks de:
- layout de rutas `/data/...`,
- resolución de binarios,
- persistencia tras reinicio simulado,
- healthcheck en verde en entorno pseudo-container.
