# Esquema de base de datos SQLite

## Tablas principales
### subscriptions
- id
- name
- profile
- status
- created_at
- updated_at

### known_items
- id
- subscription_id
- item_identifier
- signature
- fetched_at

### jobs
- id
- subscription_id
- item_id
- state (`pending|running|success|retry|dead_letter|cancelled`)
- priority
- attempts
- max_attempts
- dedupe_key
- last_error
- created_at
- updated_at

### downloads
- id
- job_id
- file_path
- size
- success
- error_message

### metrics
- id
- job_id
- metric_name
- metric_value
- captured_at

## Invariantes
- `subscriptions.name` único.
- transición de estado válida en `jobs` según: `pending->running|cancelled`, `running->success|retry|cancelled|dead_letter`, `retry->pending|cancelled|dead_letter`.
- integridad referencial preservada.

## Migraciones
Toda migración debe ser reversible o, si no lo es, documentar claramente su impacto.


## Transiciones de estado (jobs)
Estados terminales: `success`, `dead_letter`, `cancelled`.

No se permite:
- transición directa `pending -> success`;
- reapertura desde estados terminales;
- crear un segundo job activo (`pending|running|retry`) con el mismo `dedupe_key`.
