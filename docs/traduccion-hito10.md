# Traducción a modelo ytdl-sub (Hito 10)

## Alcance
Este módulo implementa la traducción desde `EffectiveSubscriptionConfig` al **modelo traducido ytdl-sub** sin compilar artefactos en disco ni ejecutar binarios.

## Entrada y salida
- Entrada: configuración efectiva (Hitos 6–8) + contrato de integración (Hito 9).
- Salida: `TranslatedYtdlSubModel` serializable y estable con:
  - `preset_base` y `preset_bridge`,
  - `ytdl_sub_model` (payload traducido),
  - `issues` con `reason_code`,
  - `translation_signature` reproducible.

## Reglas de traducción aplicadas
1. Se ejecuta `prepare_translation(...)` del Hito 9 como paso obligatorio.
2. Se resuelve preset base y preset puente:
   - `profile_id -> preset_mapping` prioriza base,
   - `quality_profile -> preset_mapping` actúa como puente,
   - conflicto distinto entre ambos genera `PRESET_AMBIGUOUS`.
3. Se excluyen campos declarados como `internal_only` en `translation_rules`.
4. Si la traducción preparada es parcial/rechazada, se marca `TRANSLATION_PARTIAL_OR_REJECTED` y no se genera payload final.
5. Si existen issues, no hay estado gris: `ytdl_sub_model` queda vacío y la traducción se considera inválida.

## Fallbacks
La resolución de fallback de preset respeta `fallback_policy.on_missing_preset` del contrato del Hito 9.

## Separación con Hito 11+
Este hito no materializa compilados finales ni ejecuta `ytdl-sub`.
Solo deja una representación estable lista para que Hito 11 la consuma.
