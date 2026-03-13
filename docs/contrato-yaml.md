# Contrato YAML de configuración (Hito 3)

## Alcance normativo

Este documento define **exclusivamente** el contrato declarativo del Hito 3.
No incluye:
- parseo completo a dominio (Hito 4),
- validación semántica fuerte avanzada (Hito 5),
- resolución de herencia efectiva (Hito 6),
- traducción completa a `ytdl-sub` (Hitos 9–10).

## Set obligatorio de archivos

Una carpeta de configuración solo es candidata válida si contiene:
- `general.yaml`
- `profiles.yaml`
- `subscriptions.yaml`
- `ytdl-sub-conf.yaml`

## Decisión de bloques opcionales

Los bloques operativos opcionales se mantienen **fuera** de `general.yaml`:
- `cache.yaml`
- `queues.yaml`
- `logging.yaml`

Esta separación evita mezclar contrato funcional con ajustes operativos de runtime.

## Estructura formal por archivo

### `general.yaml`
Propósito: contexto global de ejecución de Zenoytdl.

Obligatorias:
- `workspace`: `string` no vacía.
- `environment`: `development|staging|production`.
- `default_profile`: `string` que referencia un perfil definido en `profiles.yaml`.

Opcionales:
- `log_level`: `DEBUG|INFO|WARNING|ERROR`.
- `execution` (objeto):
  - `dry_run`: `boolean`.

Defaults declarativos:
- `log_level: INFO`
- `execution.dry_run: false`

---

### `profiles.yaml`
Propósito: catálogo semántico de perfiles reutilizables.

Estructura:
- `profiles`: lista no vacía de objetos.

Obligatorias por perfil:
- `name`: identificador único.
- `media_type`: `video|audio|shorts`.
- `quality_profile`: clave semántica de calidad (ej. `balanced`, `archive`, `compact`).

Opcionales por perfil:
- cualquier bloque semántico adicional de alto nivel (ej. `retention`).

Reglas:
- no se permiten nombres de perfil duplicados.

---

### `subscriptions.yaml`
Propósito: declarar suscripciones de usuario y su vínculo con perfiles.

Estructura:
- `subscriptions`: lista no vacía de objetos.

Obligatorias por suscripción:
- `name`: identificador único.
- `profile`: referencia a `profiles[].name`.
- `sources`: lista no vacía de fuentes declaradas por el usuario.

Opcionales:
- `enabled`: `boolean`.
- `schedule` (objeto):
  - `mode`: `manual|interval`.
  - `every_hours`: entero (condicional).

Condicionales:
- `schedule.every_hours` es obligatorio cuando `schedule.mode = interval`.

Defaults declarativos:
- `enabled: true`

---

### `ytdl-sub-conf.yaml`
Propósito: puente de conectividad de alto nivel con la capa inferior.

Obligatorias:
- `integration` (objeto):
  - `provider`: `ytdl-sub`
  - `min_version`: versión mínima esperada
  - `binary`: ruta o nombre de binario
- `profile_preset_map`: objeto no vacío que mapea `quality_profile` semántico hacia presets de la capa inferior.

Opcionales:
- `invocation` (objeto):
  - `extra_args`: lista de argumentos adicionales.

Defaults declarativos:
- `integration.provider: ytdl-sub`
- `integration.binary: ytdl-sub`
- `invocation.extra_args: []`

## Reglas de consistencia inter-fichero en Hito 3

1. `general.default_profile` debe existir en `profiles[].name`.
2. `subscriptions[].profile` debe existir en `profiles[].name`.
3. Cada `profiles[].quality_profile` debe existir en `ytdl-sub-conf.profile_preset_map`.

## Ejemplos de referencia

- Válidos:
  - `tests/fixtures/contract/valid/minimal/`
  - `tests/fixtures/contract/valid/with-optionals/`
  - `examples/config-minima/`
- Inválidos:
  - `tests/fixtures/contract/invalid/missing-required-file/`
  - `tests/fixtures/contract/invalid/missing-default-profile/`
  - `tests/fixtures/contract/invalid/missing-conditional-every-hours/`
  - `tests/fixtures/contract/invalid/missing-profile-mapping/`
  - `tests/fixtures/contract/invalid/unknown-profile-reference/`
