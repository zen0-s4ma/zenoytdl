# Contrato de archivos de configuración YAML

## Alcance normativo (Hito 3 + Hito 9)

Este contrato consolida dos decisiones:

1. **Hito 3**: el sistema se define con **4 YAML obligatorios**:
   - `general.yaml`
   - `profiles.yaml`
   - `subscriptions.yaml`
   - `ytdl-sub-conf.yaml`
2. **Hito 3 (decisión formal de bloques opcionales)**: los bloques operativos opcionales **van fuera de `general.yaml`** en archivos dedicados.
3. **Hito 9**: `ytdl-sub-conf.yaml` es la fuente de verdad del acoplamiento con `ytdl-sub`.

## Archivos obligatorios

### `general.yaml`
Propósito: parámetros globales y contexto de ejecución.

Campos mínimos:
- `workspace` (string, ruta base)
- `default_profile` (string)
- `environment` (`development|staging|production`)

Campos opcionales:
- `log_level` (`DEBUG|INFO|WARNING|ERROR`)

### `profiles.yaml`
Propósito: catálogo de perfiles reutilizables.

Estructura:
- lista `profiles` con elementos:
  - `name` (único)
  - `platform`
  - `preset` (clave lógica de traducción)
  - `ytdl_options` (objeto libre)
  - `postprocess` (objeto opcional)

Reglas:
- `name` único.
- `preset` debe estar cubierto por `ytdl-sub-conf.yaml.preset_mapping`.

### `subscriptions.yaml`
Propósito: suscripciones concretas.

Estructura:
- lista `subscriptions` con elementos:
  - `name` (único)
  - `profile` (referencia a `profiles[].name`)
  - `enabled` (bool)
  - `items` (lista no vacía de URL o ids de entrada)
  - `overrides` (objeto opcional)

Reglas:
- toda referencia `profile` debe existir.
- `items` no puede estar vacío.

### `ytdl-sub-conf.yaml`
Propósito: contrato de integración y traducción hacia `ytdl-sub`.

Bloques soportados (Hito 9):
- `integration_version`
- `preset_mapping`
- `field_mapping`
- `translation_rules`
- `compatibility`
- `fallback_policy`
- `validation`
- `invocation`

Reglas:
- `integration_version` obligatoria.
- `preset_mapping` y `field_mapping` obligatorios.
- la validación cruzada debe rechazar perfiles sin preset traducible.

## Archivos opcionales (fuera de `general.yaml`)

Estos ficheros amplían operación, pero no sustituyen el set obligatorio:

- `cache.yaml`: políticas de firma, persistencia e invalidación.
- `queues.yaml`: concurrencia, reintentos y estrategia de scheduling.
- `logging.yaml`: formato y destinos de logs.

## Regla de consistencia inter-ficheros

Una carpeta de configuración solo es válida si:

1. existen los 4 YAML obligatorios,
2. `subscriptions.profile` referencia perfiles existentes,
3. `profiles.preset` tiene mapping en `ytdl-sub-conf.yaml.preset_mapping`,
4. la traducción de campos respeta `field_mapping`/`translation_rules`.

## Regla sobre evolución del README

Si el contrato cambia durante un hito, la documentación de contrato sí debe actualizarse inmediatamente; sin embargo, el `README.md` sólo podrá reflejar ese cambio como capacidad del proyecto cuando el hito correspondiente quede cerrado con regresión acumulada en verde.
