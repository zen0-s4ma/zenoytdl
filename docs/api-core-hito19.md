# API del core (Hito 19)

Este hito introduce una **frontera programática estable** en `src/api/core_api.py` sin acoplarla a UI/TUI ni a un servidor HTTP público.

## Principios
- API interna del core, orientada a automatización.
- Reutiliza lógica existente de validación, resolución, compilación, cola, caché y persistencia.
- Contrato uniforme de respuesta:
  - éxito: `{"ok": true, "data": ...}`
  - error: `{"ok": false, "error": {"code", "message", "details"}}`

## Operaciones expuestas
- **Perfiles**
  - `list_profiles(config_dir)`
  - `get_profile(config_dir, profile_name)`
- **Suscripciones**
  - `list_subscriptions(config_dir)`
  - `get_subscription(config_dir, subscription_name)`
- **Validación y resolución**
  - `validate_config(config_dir)`
  - `resolve_effective_config(config_dir, subscription_name=None)`
- **Cola y sincronización**
  - `trigger_sync(SyncRequest)` encola trabajos desde artefactos compilados.
  - `get_queue(include_terminal=True)`
  - `process_queue_step(config_dir, output_root, timeout_seconds=...)`
- **Historial, purgas y caché**
  - `get_history(config_dir)`
  - `purge_history(subscription_id, max_items, profile_id='api')`
  - `purge_cache(scope=None)`
- **Reintento de fallos**
  - `retry_failed_jobs(RetryRequest)` para `retry_pending` y `dead_letter`.

## Payloads
- `SyncRequest`
  - `config_dir: str`
  - `output_root: str`
  - `priority: int` (>= 0)
  - `max_attempts: int` (> 0)
- `RetryRequest`
  - `job_ids: tuple[str, ...] | None`

## Límites explícitos del hito
- No implementa autenticación/autorización.
- No expone API pública HTTP ni multiusuario.
- No introduce interfaz visual.
