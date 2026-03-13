# Hito 5 — Validación estructural y semántica

## Alcance
Este módulo implementa validación fuerte **después del parseo/carga de Hito 4** y **antes de cualquier ejecución/compilación**.

No incluye:
- resolución efectiva de herencia (Hito 6),
- overrides completos (Hito 7),
- postprocesados completos (Hito 8),
- traducción a ytdl-sub (Hitos 9-10),
- caché/DB/cola/API real.

## Módulo
`src/config/validation.py`

### Entrada
- `ParsedConfigBundle` generado por `src/config/config_loader.py`.

### Salida
- `ValidationReport` serializable (`to_dict`, `to_json`) con:
  - `config_signature` (firma de Hito 4),
  - `issues` tipados (`ValidationIssue`: `code`, `path`, `message`, `severity`),
  - `issue_fingerprint` estable (SHA-256 de errores canonizados).

### Corte temprano
- `ensure_semantic_valid(bundle)` devuelve `ValidationReport` cuando no hay errores.
- Si hay errores lanza `SemanticValidationError`, bloqueando etapas posteriores.

## Reglas implementadas
1. Presencia de ficheros obligatorios.
2. Perfiles:
   - duplicados,
   - `media_type` permitido,
   - `element_type: profile`,
   - extensibilidad controlada (claves extra sólo con prefijo `x-`).
3. Suscripciones:
   - `element_type: subscription`,
   - regla `schedule.mode=interval` con `every_hours > 0`,
   - no mezclar tipos de fuente en una misma suscripción,
   - campos dependientes por tipo de medio (`audio_language`, `video_container`, `max_duration_seconds`),
   - extensibilidad controlada.
4. Referencias cruzadas:
   - `general.default_profile` existente,
   - `subscription.profile` existente,
   - `subscription.media_type` consistente con perfil,
   - `quality_profile` mapeado en `ytdl-sub-conf.yaml.profile_preset_map`.

## Estrategia de pruebas
- Unitarias: `tests/unit/test_config_validation.py`
- Integración: `tests/integration/test_config_validation_integration.py`
- E2E: `tests/e2e/test_config_validation_flow.py`
- Regresión: `tests/regression/test_hito5_validation_regression.py`
- Fixtures dedicados: `tests/fixtures/hito5/**`
