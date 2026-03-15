# Esquema de base de datos SQLite

## Principio operativo (Hito 13)
SQLite pasa a ser la **fuente de verdad operativa** del core para estado de suscripciones, ejecuciones, items conocidos y trazabilidad mínima.

## Versión de esquema
- `PRAGMA user_version = 1`

## Tablas principales
### `subscriptions`
Estado consolidado por suscripción.
- `subscription_id` (PK)
- `profile_id`
- `source_kind`
- `source_value`
- `config_signature`
- `created_at`
- `updated_at`

### `execution_runs`
Resultado operativo por ejecución controlada (Hito 12 + Hito 13).
- `id` (PK)
- `job_id` (UNIQUE)
- `subscription_id` (FK → `subscriptions.subscription_id`)
- `profile_id`
- `status`
- `error_type`
- `severity`
- `exit_code`
- `error_message`
- `stdout`
- `stderr`
- `command_json`
- `config_signature`
- `effective_signature`
- `translation_signature`
- `compilation_signature`
- `artifact_yaml_path`
- `metadata_json_path`
- `started_at`
- `finished_at`
- `duration_ms`
- `created_at`

### `known_items`
Registro base de elementos conocidos por suscripción.
- `id` (PK)
- `subscription_id` (FK)
- `item_identifier`
- `item_signature`
- `first_seen_at`
- `last_seen_at`
- `last_run_id` (FK → `execution_runs.id`)
- `last_status`
- `UNIQUE(subscription_id, item_identifier)`

### `run_events`
Bitácora de eventos operativos.
- `id` (PK)
- `run_id` (FK)
- `subscription_id` (FK)
- `event_kind` (`download|synchronization|discard|purge`)
- `item_identifier`
- `detail_json`
- `created_at`

### `postprocessing_state`
Estado base de postprocesado por item.
- `id` (PK)
- `run_id` (FK)
- `subscription_id` (FK)
- `item_identifier`
- `postprocessing_id`
- `state`
- `detail_json`
- `updated_at`
- `UNIQUE(subscription_id, item_identifier, postprocessing_id)`

### `run_metrics`
Métricas por ejecución.
- `id` (PK)
- `run_id` (FK)
- `metric_name`
- `metric_value`
- `captured_at`

## Soporte base preparatorio (sin lógica completa Hito 14+)
### `queue_backlog`
Estructura mínima para futura cola persistente.
- `id` (PK)
- `subscription_id`
- `dedupe_key`
- `state`
- `priority`
- `attempts`
- `max_attempts`
- `created_at`
- `updated_at`
- `UNIQUE(subscription_id, dedupe_key)`

### `cache_index`
Índice mínimo para futuras entradas de caché.
- `id` (PK)
- `cache_scope`
- `cache_key`
- `cache_signature`
- `payload_json`
- `created_at`
- `updated_at`
- `UNIQUE(cache_scope, cache_key)`

## Invariantes
- `subscriptions.subscription_id` único y estable.
- `execution_runs.job_id` único para evitar duplicado accidental de huellas.
- Integridad referencial obligatoria (`PRAGMA foreign_keys = ON`).
- `known_items` mantiene último estado observado por item/suscripción.

## Smoke check de persistencia (Hito 0)
Se mantiene el smoke mínimo (`SELECT 1`) para disponibilidad de SQLite, complementado en Hito 13 con inicialización de esquema y escrituras/lecturas reales.
