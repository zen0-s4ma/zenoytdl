# Hito 4 — Parseo y carga de configuración

## Alcance
Implementa la frontera de entrada desde carpeta YAML a modelo interno tipado para:
- `general.yaml`
- `profiles.yaml`
- `subscriptions.yaml`
- `ytdl-sub-conf.yaml`

Sin adelantar:
- validación semántica fuerte de Hito 5,
- resolución de herencia/efectiva de Hito 6,
- overrides de Hito 7,
- traducción a ytdl-sub (Hitos 9–10).

## Diseño del cargador
Módulo: `src/config/config_loader.py`.

### Entrada y resolución de rutas
- `load_parsed_config_bundle(config_dir)` acepta ruta relativa o absoluta.
- La ruta relativa se resuelve contra `Path.cwd()`.
- `general.workspace` y `general.library_dir` se normalizan a `Path` absoluto.
- `integration.binary` se resuelve a ruta absoluta solo cuando viene con formato path (`./`, `/`, `\\`).

### Salida tipada
- `ParsedGeneral`
- `ParsedProfile`
- `ParsedSchedule`
- `ParsedSubscription`
- `ParsedYtdlSubConf`
- `ParsedConfigBundle`

El bundle expone `to_domain_catalog()` para construir entidades del dominio de Hito 2 (`GeneralConfig`, `Profile`, `Subscription`) sin añadir semántica avanzada.

### Defaults de Hito 4
- `general.log_level = "INFO"`
- `general.execution.dry_run = false`
- `general.library_dir = <workspace>/library`
- `subscription.enabled = true`
- `subscription.schedule.mode = manual`
- `ytdl-sub.integration.provider = ytdl-sub`
- `ytdl-sub.integration.binary = ytdl-sub`
- `ytdl-sub.invocation.extra_args = []`

### Tipos de error
- `YAMLSyntaxError`: error sintáctico en YAML.
- `YAMLStructureError`: shape no válido.
- `MissingDataError`: archivo/campo requerido ausente.
- `CoercionError`: tipo inválido en coerción.
- `PathResolutionError`: ruta de carpeta de configuración inválida.

### Firma/hash base
`build_config_signature(raw_documents)` genera SHA-256 sobre JSON canónico (`sort_keys=True`, separadores estables), reproducible y apto como base para hitos posteriores de caché sin definir todavía políticas de invalidación.

## Fixtures y cobertura
- Válidos: `tests/fixtures/hito4/valid/{minimal,medium,complex}`.
- Inválidos: `tests/fixtures/hito4/invalid/{broken-yaml,missing-required,invalid-coercion}`.
- Regression: `tests/regression/test_hito4_config_loader_regression.py`.
