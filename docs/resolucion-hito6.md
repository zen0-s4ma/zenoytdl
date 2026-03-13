# Hito 6 — Sistema de herencia y resolución perfil → suscripción

## Alcance
Este módulo implementa la resolución de configuración efectiva **después del parseo (Hito 4)** y **después de la validación semántica (Hito 5)**.

Incluye:
- herencia perfil → suscripción,
- defaults operativos de resolución,
- precedencia explícita,
- normalización interna,
- trazabilidad de origen por clave,
- firma estable de configuración efectiva.

No incluye:
- políticas avanzadas de overrides (Hito 7),
- postprocesados completos (Hito 8),
- traducción a ytdl-sub (Hitos 9–10),
- compilación/ejecución real (Hitos 11–12),
- persistencia/cola/caché/API real.

## Módulo
`src/config/effective_resolution.py`

### Entrada
- `ParsedConfigBundle` producido por `src/config/config_loader.py`.

### Salida
- `EffectiveSubscriptionConfig` por suscripción con:
  - `resolved_options` (mapa final normalizado),
  - `value_origins` (origen de cada clave),
  - `effective_signature` (SHA-256 estable por suscripción).
- `serialize_effective_configs(...)` para snapshot canónico de lote con `batch_signature` estable.

## Precedencia
Orden aplicado por capa (menor → mayor precedencia):
1. `GENERAL_DEFAULTS` internos de resolución (`timezone=UTC`),
2. `general.yaml` (`workspace`, `library_dir`, `environment`, `log_level`, `dry_run`, `default_profile`),
3. `profiles.yaml` (`media_type`, `quality_profile`, `profile_name`),
4. campos locales permitidos de suscripción (`quality_profile`, `media_type`, `audio_language`, `video_container`, `max_duration_seconds`),
5. metadatos de suscripción (`enabled`, `schedule_mode`, `schedule_every_hours`, `primary_source`, `source_kind`, `source_count`, `sources_signature`).

## Normalización y determinismo
- Claves en minúscula y ordenadas.
- Strings con trim y espacios internos colapsados.
- Fuentes deduplicadas y ordenadas antes de cálculo de `primary_source` y firma de fuentes.
- Hash SHA-256 sobre JSON canónico (`sort_keys=True`, separadores estables) para firma por suscripción y firma de lote.

## Trazabilidad
`value_origins` indica la capa que ganó por clave (`defaults.general`, `general.yaml`, `profiles.yaml:<name>`, `subscriptions.yaml:<name>[:local]`).

## Cobertura de pruebas (Hito 6)
- Unitarias: `tests/unit/test_effective_resolution.py`
- Integración: `tests/integration/test_effective_resolution_integration.py`
- E2E: `tests/e2e/test_effective_resolution_flow.py`
- Regresión: `tests/regression/test_hito6_effective_resolution_regression.py`
- Fixtures: `tests/fixtures/hito6/{minimal,medium,complex,equivalent-a,equivalent-b}`
- Snapshot canónico: `tests/fixtures/hito6/snapshots/complex-effective.json`
