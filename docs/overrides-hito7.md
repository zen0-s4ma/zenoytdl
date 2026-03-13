# Hito 7 — Sistema de overrides controlados

## Alcance
Este módulo implementa políticas explícitas de override sobre la resolución efectiva del Hito 6.

Incluye:
- políticas `allowed`, `restricted`, `forbidden` por campo,
- validación de overrides ilegales o no soportados,
- restricciones por tipo de campo (`str` vs `int`),
- motivos de rechazo estables (`reason_code`),
- integración en la salida efectiva con trazabilidad.

No incluye:
- postprocesados (Hito 8),
- traducción a ytdl-sub (Hitos 9–10),
- compilación/ejecución real (Hitos 11–12),
- persistencia/cola/caché/API.

## Contrato de políticas
En `profiles.yaml`, cada perfil puede definir `override_policies`:

- `allowed`: acepta override si el tipo del campo es válido.
- `restricted`: acepta override solo si cumple restricciones (por ejemplo `allowed_values`, `min_value`, `max_value`, `non_empty_string`).
- `forbidden`: rechaza siempre el override para ese campo.

Si un campo no tiene regla explícita, por defecto se usa `allowed`.

## Entrada y salida
Entrada adicional en suscripción:
- `overrides` (objeto clave/valor)
- sigue existiendo compatibilidad con overrides locales del Hito 6.

Salida extendida en `EffectiveSubscriptionConfig`:
- `override_decisions`: lista estable de decisiones por campo con
  - `field`,
  - `policy`,
  - `accepted`,
  - `reason_code`,
  - `reason_message`,
  - `requested_origin`.

## Reason codes principales
- `OVERRIDE_ACCEPTED`
- `OVERRIDE_POLICY_FORBIDDEN`
- `OVERRIDE_FIELD_NOT_SUPPORTED`
- `OVERRIDE_TYPE_MISMATCH`
- `OVERRIDE_VALUE_NOT_SCALAR`
- `OVERRIDE_RESTRICTED_DISALLOWED_VALUE`
- `OVERRIDE_RESTRICTED_MIN_VALUE`
- `OVERRIDE_RESTRICTED_MAX_VALUE`
- `OVERRIDE_RESTRICTED_EMPTY_STRING`

## Cobertura de pruebas (Hito 7)
- Unitarias: `tests/unit/test_override_policies.py`
- Integración: `tests/integration/test_override_policies_integration.py`
- E2E: `tests/e2e/test_override_policies_flow.py`
- Regresión: `tests/regression/test_hito7_override_policies_regression.py`
