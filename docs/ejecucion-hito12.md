# Ejecución controlada de ytdl-sub (Hito 12)

## Alcance
Este módulo consume artefactos compilados del Hito 11 e invoca `ytdl-sub` por subprocess de forma encapsulada, trazable y serializable.

## Entrada y salida
- Entrada: `CompiledSubscriptionArtifact` o `CompiledArtifactBatch`.
- Salida: `ExecutedJobResult` por unidad de trabajo con:
  - `job_id`, `subscription_id`, `profile_id`, `compilation_signature`,
  - comando construido (`binary_path`, `args`, `cwd`, `timeout_seconds`, `invocation_metadata`),
  - `stdout`, `stderr`, `exit_code`,
  - clasificación (`error_type`, `severity`) y estado final (`success|failed`).

## Contratos de ejecución
1. **Unidad de trabajo explícita**: cada ejecución se asocia a `ExecutionJobUnit` sin introducir cola persistente.
2. **Resolución de binario controlada**: se usa `PATH` efectivo (incluyendo overrides de entorno).
3. **Invocación reproducible**: el comando siempre se construye desde `artifact.yaml` (`mode`, `extra_args`) + `global_args` + ruta del artefacto.
4. **Entorno y temporales**:
   - `cwd` configurable,
   - `env_overrides` soportado,
   - directorio temporal aislado por ejecución (`ZENOYTDL_TMP_DIR`).
5. **Clasificación estable de errores**:
   - `binary_not_found` (recuperable),
   - `timeout` (recuperable),
   - `non_zero_exit` (recuperable),
   - `invalid_compiled_artifact` (no recuperable),
   - `environment_error` (no recuperable).

## Separación con Hito 13+
- No hay cola real ni workers.
- No hay persistencia de estado de jobs en SQLite.
- No hay scheduler, API HTTP ni reintentos avanzados.
- El módulo solo ejecuta y clasifica, dejando trazabilidad serializable para capas futuras.
