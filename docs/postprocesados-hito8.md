# Hito 8 — Modelado de postprocesados

## Alcance
Este documento define el modelado formal de postprocesados dentro del core.

Incluye:
- estructura tipada interna para postprocesados,
- resolución perfil → suscripción,
- validaciones de prerequisitos e incompatibilidades,
- serialización estable dentro de la configuración efectiva.

No incluye:
- traducción a ytdl-sub (Hitos 9–10),
- compilación real de artefactos (Hito 11),
- ejecución real (Hito 12).

## Modelo interno
Módulo: `src/config/effective_resolution.py`.

Se introducen:
- `PostprocessingKind`: enum con tipos soportados,
- `ResolvedPostprocessing`: objeto resuelto con parámetros, origen y `parameter_origins`.

Tipos soportados:
- `metadata_text`
- `metadata_images`
- `embed_metadata`
- `export_info_json`
- `max_duration`

## Declaración YAML
Los perfiles y suscripciones aceptan bloque `postprocessings` como lista de objetos:

- `type` (obligatorio)
- `enabled` (opcional, default `true`)
- `parameters` (opcional)

## Herencia y ajuste
1. Se aplican postprocesados del perfil.
2. La suscripción puede:
   - sobrescribir parámetros,
   - desactivar un tipo heredado (`enabled: false`),
   - añadir nuevos tipos.

## Reglas de validación de Hito 8
Por tipo:
- `metadata_text`: `filename` no vacío, `include_description` booleano.
- `metadata_images`: `include_thumbnail` y `include_banner` booleanos.
- `embed_metadata`: `mode` en `{safe, force}`.
- `export_info_json`: `pretty` booleano.
- `max_duration`: `seconds` entero > 0.

Compatibilidad/prerequisitos:
- `embed_metadata` requiere `metadata_text` o `metadata_images` activos.
- `max_duration` es incompatible con `media_type=audio`.
- `metadata_text.filename` con sufijo `.json` es incompatible con `export_info_json`.

## Salida efectiva
`EffectiveSubscriptionConfig` agrega `postprocessings` en su payload serializado.
Cada entrada mantiene:
- `kind`,
- `enabled`,
- `parameters`,
- `origin`,
- `parameter_origins`.

Esta salida es estable y forma parte de la firma efectiva (`effective_signature`).
