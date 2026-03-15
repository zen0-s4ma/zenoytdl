# Contrato de integración Zenoytdl ↔ ytdl-sub (Hito 9)

## Finalidad
Definir `ytdl-sub-conf.yaml` como **fuente de verdad** del acoplamiento con `ytdl-sub`, sin mezclar esta lógica con el motor de ejecución.

## Referencia oficial usada
Se revisó la guía oficial de ytdl-sub para alinear conceptos de:
- presets y archivo de suscripciones,
- override mode,
- map mode,
- estructura de invocación CLI (`sub`/`dl`) y parámetros.

Fuentes consultadas:
- `usage.rst`
- `config_reference/config_yaml.rst`
- `config_reference/subscription_yaml.rst`
- `config_reference/index.rst`

> Nota: el endpoint ReadTheDocs fue inaccesible desde este entorno (HTTP 403), por lo que se usaron los mismos documentos oficiales desde el repositorio upstream de ytdl-sub.

## Bloques del contrato (`ytdl-sub-conf.yaml`)

### 1) `integration_version`
Versión entera del contrato de integración. Permite evolución controlada sin romper traducciones existentes.

### 2) `preset_mapping`
Mapa declarativo (`profile_id` o `quality_profile` → preset ytdl-sub).

### 3) `field_mapping`
Mapa declarativo (`campo Zenoytdl efectivo` → `campo destino ytdl-sub`).

### 4) `translation_rules`
Reglas por campo para traducir valores:
- `map_values`: mapa explícito de valor origen a valor destino,
- `default`: valor por defecto opcional,
- `required`: obliga traducción válida del campo.
- `internal_only`: permite mapear para validación/traza pero excluir del modelo ytdl-sub traducido (Hito 10).

### 5) `compatibility`
Reglas de versión del proveedor:
- `min_ytdl_sub_version`,
- `max_ytdl_sub_version` (opcional),
- `policy`: `strict | lenient`.

### 6) `fallback_policy`
Políticas declarativas:
- `on_missing_field`: `reject | drop | use_default`,
- `on_missing_preset`: `reject | use_fallback`,
- `fallback_preset` opcional.

### 7) `validation`
Reglas de validación de traducción preparada:
- `strict_unknown_fields`,
- `abort_on_partial_translation`.

### 8) `invocation`
Datos de invocación **sin ejecutar**:
- `binary`,
- `mode` (`sub | dl`),
- `extra_args`.

## Salida preparada (no ejecutada)
La salida del Hito 9 es serializable y estable:
- `preset` resuelto,
- `mapped_fields`,
- `invocation`,
- `issues` con `reason_code`,
- `translation_signature` estable.

## Detección explícita de no traducibilidad
El contrato produce razones trazables cuando una configuración efectiva no tiene traducción válida, p. ej.:
- `PRESET_MAPPING_MISSING`,
- `MISSING_REQUIRED_FIELD`,
- `TRANSLATION_RULE_UNMAPPED_VALUE`,
- `UNSUPPORTED_FIELD`.

## Desacoplamiento garantizado
- El contrato consume `EffectiveSubscriptionConfig` (Hitos 6–8).
- No invoca binarios ni compila artefactos (Hitos 10+ fuera de alcance).
- El mapeo vive en `ytdl-sub-conf.yaml`, no en `if/else` dispersos.

## Handoff a compilación (Hito 11)
La salida de traducción válida (Hito 10) se consume por el compilador de artefactos (Hito 11) con estos requisitos mínimos:
- `ytdl_sub_model.subscription.invocation.binary` y `mode` deben existir para considerarse invocable;
- `meta.effective_signature` y `translation_signature` se propagan a metadatos compilados;
- cualquier traducción con `issues` no se compila.

El contrato de integración sigue siendo declarativo (`ytdl-sub-conf.yaml`); Hito 11 únicamente materializa su resultado en disco.


## Handoff a ejecución controlada (Hito 12)
La salida compilada invocable del Hito 11 se ejecuta por un módulo encapsulado que:
- construye comando reproducible desde `artifact.yaml` + parámetros globales de ejecución;
- resuelve binario en `PATH` efectivo y soporta `cwd`, `env_overrides`, timeout y temporal aislado;
- captura `stdout`, `stderr`, `exit_code` y los serializa junto al `job_id`/unidad de trabajo;
- clasifica fallos en categorías estables (`binary_not_found`, `timeout`, `non_zero_exit`, `invalid_compiled_artifact`, `environment_error`).

Se mantiene el desacoplamiento: el contrato YAML sigue siendo declarativo; la ejecución real ocurre fuera del contrato, en la capa de integración runtime.
