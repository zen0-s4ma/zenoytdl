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
- state
- priority
- attempts
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
- transición de estado válida en `jobs`.
- integridad referencial preservada.

## Migraciones
Toda migración debe ser reversible o, si no lo es, documentar claramente su impacto.
