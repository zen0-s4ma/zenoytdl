# Criterios de prueba en Zenoytdl

## Tipos de prueba
- Unitarias
- Integración
- Funcionales / E2E
- Regresión
- Rendimiento
- Resiliencia
- Validación de configuración

## Regla de cierre de hito
Un hito no está cerrado hasta pasar:
1. pruebas específicas del hito,
2. regresión acumulada desde Hito 0,
3. validaciones de configuración relevantes,
4. controles de resiliencia aplicables.

## Regla de README
Solo después del cierre real del hito se actualiza el `README.md`. No antes.

## Datos de prueba
Usar `tests/fixtures/valid`, `tests/fixtures/invalid` y snapshots controlados.

## Matriz de compatibilidad auditable (Hito 1)

| Criterio | Local (sin contenedor) | Pseudo-container (`/data/...`) | Evidencia esperada |
|---|---|---|---|
| Resolución de `ffmpeg`/`ffprobe`/`ytdl-sub` | Debe resolver por `PATH` local | Debe resolver por `PATH` dentro del contenedor | `command -v ...` en ambos entornos |
| Layout persistente | Rutas equivalentes en FS local para pruebas | Rutas oficiales: `/data/library`, `/data/tmp`, `/data/logs`, `/data/state.sqlite`, `/data/cache.sqlite`, `/data/compiled-ytdl-sub` | Check de existencia y permisos |
| Persistencia tras reinicio | Simular reinicio de proceso manteniendo archivos | Reinicio/recreación de contenedor conserva volúmenes | Verificación de archivos previos/post reinicio |
| Configuración | Lectura desde carpeta de config local | Bind mount de YAMLs en `/config` | Carga válida de YAMLs mínimos |
| Logs | `stdout/stderr` + archivo opcional local | `stdout/stderr` + `/data/logs` opcional | Logs visibles y archivo si aplica |
| Healthcheck | Script/check local equivalente | Healthcheck de contenedor en estado `healthy` | Salida de `docker compose ps` o check equivalente |

### Criterio de aceptación mínimo para auditar cierre de Hito 1
- Todos los criterios de la matriz deben estar en verde para `local` y `pseudo-container`.
- Debe existir evidencia trazable (comandos y salidas) en CI o pipeline local.
- Cualquier desviación bloquea el cierre formal del hito.
