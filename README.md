# Zenoytdl (core)

Zenoytdl es el **núcleo operativo** que encapsula `ytdl-sub` con contratos YAML, validación, resolución efectiva, traducción, compilación de artefactos, ejecución controlada, persistencia SQLite, caché y cola de trabajos.

> Este repositorio contiene el **core funcional cerrado (hitos 0–21)**. No contiene TUI ni GUI web.

---

## 1) Introducción

### Qué es
Zenoytdl es una aplicación Python orientada a operación técnica: toma un bundle YAML, lo valida, lo resuelve y lo transforma en ejecuciones gobernadas de `ytdl-sub`.

### Qué problema resuelve
`ytdl-sub` es potente, pero su operación directa no cubre por sí sola la capa de producto que normalmente se necesita en un sistema real:
- contrato de configuración estable,
- validación semántica reproducible,
- trazabilidad de ejecución,
- deduplicación/cola/reintentos,
- persistencia del estado e historial,
- interfaz programática reusable.

### Papel respecto a `ytdl-sub`
Zenoytdl **no reemplaza** `ytdl-sub`; lo integra con una frontera controlada (`ytdl-sub-conf.yaml`, traductor, compilador, ejecutor).

### Qué no es
- No es una GUI/TUI.
- No es un reemplazo del motor multimedia subyacente.
- No es una API HTTP pública multiusuario.

### Alcance de este repositorio
Incluye:
- core de configuración + dominio + integración + persistencia + API/CLI,
- pruebas unitarias/integración/e2e/regresión,
- ejemplos YAML por escenario.

No incluye:
- frontends visuales (TUI o GUI web),
- un producto SaaS multiusuario,
- autenticación/autorización de API pública.

---

## 2) Estado del proyecto

- El core se considera **terminado, endurecido y probado** hasta hito 21.
- La base actual está preparada para evolución incremental sin reescribir arquitectura.
- “Core completo” aquí significa que están cerradas las piezas estructurales: contrato YAML, parseo, validación, resolución, integración `ytdl-sub`, compilación, ejecución, persistencia, anti-redescarga/retención, caché, colas, API interna y endurecimiento final.

Evolución razonable desde este punto:
1. mejoras incrementales del core (sin romper contratos),
2. empaquetado/operación (p.ej. Docker del core),
3. proyectos separados de UX (TUI/GUI) apoyados sobre este núcleo.

---

## 3) Arquitectura general

## Capas y responsabilidades

- **`src/config/`**: contrato YAML, parseo, validación semántica y resolución efectiva.
- **`src/domain/`**: modelo interno (perfiles, suscripciones, jobs, estados, prioridades, invariantes).
- **`src/integration/`**: detección de dependencias y puente Zenoytdl ↔ `ytdl-sub` (contrato, traducción, compilación, ejecución).
- **`src/core/`**: pipeline cacheado y runtime de cola con reintentos/concurrencia.
- **`src/persistence/`**: estado operativo en SQLite (runs, items conocidos, cola, dead-letter, métricas, caché indexada).
- **`src/api/`**: frontera consumible por CLI y por integraciones Python (`CoreAPI`).

## Flujo extremo a extremo

```text
YAML bundle (general/profiles/subscriptions/ytdl-sub-conf [+ opcionales])
        |
        v
[Contrato + Parseo] -> ParsedConfigBundle + config_signature
        |
        v
[Validación semántica] -> ValidationReport (issues/fingerprint)
        |
        v
[Resolución efectiva] -> EffectiveSubscriptionConfig (orígenes + firma)
        |
        v
[Traducción ytdl-sub] -> modelo traducido + translation_signature
        |
        v
[Compilación] -> artifacts YAML/JSON por suscripción
        |
        v
[Cola runtime] -> queued/running/retry_pending/dead_letter/completed
        |
        v
[Ejecución controlada] -> subprocess ytdl-sub + resultado estructurado
        |
        v
[Persistencia SQLite] + [Caché] + [Consulta API/CLI]
```

Separación explícita de UX futura:
- este core expone contratos y operaciones reutilizables;
- una TUI/GUI web futura debe vivir como proyecto desacoplado que consume esta frontera.

---

## 4) Organización real del repositorio

- `src/api/`: CLI bootstrap (`src.api.cli`) y API programática (`CoreAPI`).
- `src/core/`: `CoreCacheSystem`, `CachedCorePipeline`, `QueueRuntime`.
- `src/config/`: `yaml_contract`, `config_loader`, `validation`, `effective_resolution`, `bootstrap`, `runtime_env`.
- `src/domain/`: entidades, enums y serialización del dominio.
- `src/persistence/`: smoke SQLite y estado operativo (`SQLiteOperationalState`).
- `src/integration/`: detección de binarios y submódulo `ytdl_sub` (contrato/traducción/compilación/ejecución).
- `docs/`: contratos, arquitectura, operación, esquema SQLite, cola/caché, API, criterios de prueba, roadmap.
- `plans/`: ExecPlans por hito.
- `examples/`: configuraciones por escenario (`config-minima`, `core-final`, `tv`, `podcast`, `shorts`).
- `schemas/`: esquema de referencia de bundle (`config.schema.yaml`).
- `tests/`: batería completa por niveles (`unit`, `integration`, `e2e`, `regression`) + fixtures.
- `Makefile` y `test-zenoytdl.ps1`: comandos operativos Linux/macOS y alternativa PowerShell.

---

## 5) Guía completa del CLI real

El CLI actual es un **bootstrap runtime** orientado a smoke/diagnóstico rápido.

## Invocación

```bash
python -m src.api.cli --config <ruta.yaml> [--state-db <ruta.sqlite>]
```

Parámetros:
- `--config` (obligatorio): ruta a YAML mínimo para bootstrap.
- `--state-db` (opcional): ruta de SQLite para smoke check (`.tmp/state.sqlite` por defecto).

## Qué hace exactamente
1. valida que `--config` exista, tenga extensión `.yaml/.yml` y no esté vacío,
2. carga contexto runtime (`workspace`, `log_level`) desde entorno,
3. ejecuta smoke SQLite,
4. detecta binarios `ytdl-sub`, `ffmpeg`, `ffprobe`,
5. imprime **JSON estructurado** y sale con código de proceso controlado.

## Códigos de salida
- `0`: bootstrap OK (todo disponible).
- `1`: ejecución correcta del CLI pero faltan dependencias/runtime (`report.ok == false`).
- `2`: error de bootstrap/config o error operativo no recuperable en bootstrap.

## Payload de éxito (ejemplo)

```json
{
  "ok": true,
  "runtime": {"workspace": "/abs/path/.tmp/workspace", "log_level": "INFO"},
  "config_loaded": true,
  "sqlite_ready": true,
  "dependencies": {
    "ytdl-sub": {"available": true, "detail": "/usr/bin/ytdl-sub"},
    "ffmpeg": {"available": true, "detail": "/usr/bin/ffmpeg"},
    "ffprobe": {"available": true, "detail": "/usr/bin/ffprobe"}
  }
}
```

## Payload de error

```json
{
  "ok": false,
  "error": {
    "code": "CONFIG_BOOTSTRAP_ERROR | RUNTIME_BOOTSTRAP_ERROR",
    "message": "..."
  }
}
```

## Errores operativos frecuentes
- `CONFIG_BOOTSTRAP_ERROR`: ruta inexistente, extensión inválida, fichero vacío.
- `RUNTIME_BOOTSTRAP_ERROR`: fallo SQLite/path u otra excepción de entorno.
- `ok=false` con salida `1`: CLI ejecutó bien, pero faltan binarios en PATH.

## Casos de uso habituales

```bash
# Smoke con fixtures reproducibles
PATH="tests/fixtures/bin:$PATH" python -m src.api.cli --config tests/fixtures/clean/minimal.yaml

# Smoke con DB temporal explícita
PATH="tests/fixtures/bin:$PATH" python -m src.api.cli --config tests/fixtures/clean/minimal.yaml --state-db .tmp/state.sqlite
```

---

## 6) Guía completa de configuración YAML

Zenoytdl trabaja con un **bundle por carpeta**. El núcleo obligatorio son 4 YAML:

1. `general.yaml`
2. `profiles.yaml`
3. `subscriptions.yaml`
4. `ytdl-sub-conf.yaml`

Opcionales detectables por contrato:
- `cache.yaml`
- `queues.yaml`
- `logging.yaml`

Importante:
- el contrato identifica opcionales,
- el parseo operativo del core se basa en los 4 obligatorios.

### Relación entre archivos
- `general.default_profile` debe existir en `profiles`.
- cada `subscriptions[].profile` debe existir en `profiles`.
- cada `profiles[].quality_profile` debe mapear en `ytdl-sub-conf.profile_preset_map`.

### Resolución efectiva
La resolución combina capas (general, perfil, suscripción) y añade metadatos de origen/firma para producir `EffectiveSubscriptionConfig` determinista por suscripción.

---

## 7) Ejemplos reales YAML (alineados al repo)

A continuación, ejemplos basados en `examples/core-final/`.

### `general.yaml` (contexto global)

```yaml
workspace: /data/zenoytdl
environment: production
default_profile: tv-main
log_level: INFO
```

Claves principales:
- `workspace`, `environment`, `default_profile` obligatorias.
- `log_level` opcional (default `INFO`).
- `execution.dry_run` opcional (default `false`).

Errores típicos:
- `default_profile` inexistente,
- `execution.dry_run` no booleano,
- rutas vacías/no resolubles.

### `profiles.yaml` (catálogo semántico)

```yaml
profiles:
  - name: tv-main
    media_type: video
    quality_profile: balanced
  - name: podcast-main
    media_type: audio
    quality_profile: compact
```

Claves principales:
- `name`, `media_type`, `quality_profile` obligatorias.
- `media_type` permitido: `video|audio|shorts`.

Errores típicos:
- lista vacía,
- `media_type` inválido,
- `quality_profile` sin mapeo en `ytdl-sub-conf.yaml`.

### `subscriptions.yaml` (instancias operativas)

```yaml
subscriptions:
  - name: tv-subscription
    profile: tv-main
    sources:
      - https://example.com/channel/tv
  - name: podcast-subscription
    profile: podcast-main
    sources:
      - https://example.com/channel/podcast
```

Claves principales:
- `name`, `profile`, `sources` obligatorias.
- `enabled` opcional (default `true`).
- `schedule.mode` opcional (`manual` default / `interval` con `every_hours` obligatorio).

Errores típicos:
- `sources` vacío,
- mezcla de source kinds en una misma suscripción,
- `profile` inexistente,
- `schedule.mode=interval` sin `every_hours>0`.

### `ytdl-sub-conf.yaml` (puente con motor)

```yaml
integration:
  min_version: "2024.10"
profile_preset_map:
  balanced: tv_show
  compact: podcast_audio
```

Claves principales:
- `integration.min_version` obligatorio.
- `profile_preset_map` obligatorio y no vacío.
- `integration.provider` y `integration.binary` aceptan defaults (`ytdl-sub`).
- `invocation.extra_args` opcional.

Errores típicos:
- mapa de presets vacío,
- preset faltante para un `quality_profile`,
- tipos no string en claves/valores.

### Opcionales de bundle final (`cache.yaml`, `queues.yaml`, `logging.yaml`)

Ejemplos reales (core-final):

```yaml
# cache.yaml
persist_enabled: true
hashing: sha256
invalidation_rules:
  - profile_change
```

```yaml
# queues.yaml
concurrency: 2
retries: 3
priority_strategy: fifo
shutdown_policy: graceful
```

```yaml
# logging.yaml
level: INFO
format: text
sinks:
  - stdout
```

Estos archivos forman parte del bundle final de referencia y del contrato documental; su uso exacto depende del flujo operativo que consuma dicho bloque.

---

## 8) Walkthrough técnico detallado (uso real)

## Paso 0 — entorno

```bash
python -m pip install -U pip
python -m pip install -e ".[dev]"
```

## Paso 1 — preparar configuración
Opción recomendada: copiar `examples/core-final/` a una carpeta propia.

## Paso 2 — bootstrap rápido CLI

```bash
PATH="tests/fixtures/bin:$PATH" python -m src.api.cli --config tests/fixtures/clean/minimal.yaml --state-db .tmp/state.sqlite
```

Valida que runtime + SQLite + binarios se resuelven.

## Paso 3 — validación semántica desde API

```python
from pathlib import Path
from src.api import CoreAPI
from src.persistence import SQLiteOperationalState

state = SQLiteOperationalState(Path('.tmp/state.sqlite'))
state.init_schema()
api = CoreAPI(state=state)

print(api.validate_config(config_dir='examples/core-final'))
```

## Paso 4 — resolución efectiva

```python
print(api.resolve_effective_config(config_dir='examples/core-final'))
# o por suscripción:
print(api.resolve_effective_config(config_dir='examples/core-final', subscription_name='tv-subscription'))
```

## Paso 5 — trigger de sincronización (enqueue)

```python
from src.api import SyncRequest

sync = api.trigger_sync(SyncRequest(
    config_dir='examples/core-final',
    output_root='.tmp/compiled',
    priority=50,
    max_attempts=3,
))
print(sync)
```

## Paso 6 — procesar un ciclo de cola

```python
step = api.process_queue_step(
    config_dir='examples/core-final',
    output_root='.tmp/compiled',
    timeout_seconds=300.0,
)
print(step)
```

## Paso 7 — inspeccionar estado

```python
print(api.get_queue(include_terminal=True))
print(api.get_history(config_dir='examples/core-final'))
```

## Paso 8 — reintentos/purgas

```python
from src.api import RetryRequest

print(api.retry_failed_jobs(RetryRequest()))
print(api.purge_cache(scope='validation'))
print(api.purge_history(subscription_id='tv-subscription', max_items=10))
```

Criterio práctico de salud:
- validación `ok=true`,
- cola sin crecimiento anómalo en `retry_pending/dead_letter`,
- historial coherente por suscripción,
- artefactos compilados y DB actualizándose consistentemente.

---

## 9) Operación y troubleshooting

## Comprobaciones rápidas

```bash
# Lint
python -m ruff check src tests

# Smoke bootstrap
make bootstrap

# Dependencias runtime reales
ytdl-sub --version
ffmpeg -version
ffprobe -version
```

## Diagnóstico por tipo de fallo

- **Config/contrato**: errores `MissingDataError`, `YAMLStructureError`, `CoercionError`, `ContractValidationError`.
- **Validación semántica**: `ValidationReport.ok=false` con `issues[]` y `issue_fingerprint`.
- **Resolución efectiva**: `EffectiveResolutionError` (campos/orígenes no resolubles).
- **Integración ytdl-sub**: `IntegrationContractError` o fallos de ejecución (`ExecutionErrorType`).
- **Cola/runtime**: crecimiento de `retry_pending`/`dead_letter`, límites de concurrencia mal calibrados.
- **Persistencia SQLite**: errores de path/permisos/bloqueo DB.

## Diferenciar rápidamente origen del problema
1. `python -m src.api.cli ...` falla → problema de bootstrap/runtime base.
2. `validate_config` falla → contrato/semántica de YAML.
3. `trigger_sync` falla → compilación/artefactos.
4. `process_queue_step` falla → ejecución runtime/integración externa.
5. `get_queue`/`get_history` incoherente → revisar transiciones de estado y persistencia.

---

## 10) Suite de pruebas y criterio de cierre

## Niveles de prueba
- `tests/unit`: lógica aislada por módulo.
- `tests/integration`: integración entre capas.
- `tests/e2e`: flujos de extremo a extremo.
- `tests/regression`: contrato acumulado por hitos.

## Comandos base (Makefile)

```bash
make lint
make test-unit
make test-integration
make test-e2e
make test-regression
make test-all
make test-hito20
make test-hito21
```

## Alternativa PowerShell
- Script de batería completa: `./test-zenoytdl.ps1`.
- Bootstrap dev sin make: `./scripts/bootstrap-dev.ps1`.

## Criterio de verde acumulado del core
Se considera cierre válido cuando:
1. pasan pruebas específicas del cambio,
2. pasa regresión acumulada,
3. no hay defectos bloqueantes abiertos,
4. documentación técnica y operativa queda sincronizada.

---

## 11) Límites actuales del proyecto

Sí hace:
- núcleo técnico completo de configuración→ejecución→estado,
- persistencia y trazabilidad operacional,
- cola/reintentos/dead-letter/caché,
- API programática estable y CLI de bootstrap.

No hace (deliberadamente en este repo):
- TUI/GUI web,
- API HTTP pública con auth/multiusuario,
- rediseño del motor interno de `ytdl-sub`.

Regla explícita: cualquier TUI/GUI futura debe plantearse como **proyecto separado** consumiendo este core.

---

## 12) Próxima etapa razonable

Zenoytdl entra en fase de **evolución sobre base estable**, no de reconstrucción del núcleo.

Próximos pasos razonables:
1. ampliaciones incrementales del core sin romper contratos estabilizados,
2. mejoras operativas/packaging,
3. construcción de capas UX desacopladas (TUI/GUI o HTTP richer) en repositorios/proyectos separados apoyados en este núcleo.
