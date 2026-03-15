# Criterios de prueba en Zenoytdl

## Tipos de prueba
- Unitarias
- Integración
- Funcionales / E2E
- Regresión
- Rendimiento
- Resiliencia
- Validación de configuración

## Preparación reproducible de entorno dev (incluye Windows)
- Instalar dependencias dev del proyecto: `python -m pip install -e ".[dev]"`.
- En Windows PowerShell, usar los mismos comandos de lint/tests vía `python -m ...` (sin depender de `make`).
- Bootstrap oficial en Windows PowerShell (sin `make`): `./scripts/bootstrap-dev.ps1`.

## Comandos mínimos operativos (Hito 0 en curso)
- Lint: `python -m ruff check src tests`
- Unitarias: `python -m pytest tests/unit -m unit`
- Integración: `python -m pytest tests/integration -m integration`
- E2E: `python -m pytest tests/e2e -m e2e`
- Regresión acumulada: `python -m pytest tests/regression -m regression`

Detalle operativo ampliado: `docs/operacion-comandos.md`.

## Regla de cierre de hito
Un hito no está cerrado hasta pasar:
1. pruebas específicas del hito,
2. regresión acumulada desde Hito 0,
3. validaciones de configuración relevantes,
4. controles de resiliencia aplicables.

## Regla de README
Solo después del cierre real del hito se actualiza el `README.md`. No antes.

## Datos de prueba
Usar `tests/fixtures/valid`, `tests/fixtures/invalid` y snapshots controlados.

## Dependencias runtime críticas (Hito 0)
La verificación mínima de Hito 0 debe incluir evidencia real de:
- `ytdl-sub`
- `ffmpeg`
- `ffprobe`
- SQLite


## Criterios específicos para colas y caché (Hitos 17-18)
Estados oficiales a validar en pruebas: `pending`, `running`, `success`, `retry`, `dead_letter`, `cancelled`.

Cobertura mínima obligatoria de regresión:
1. flujo de éxito (`pending -> running -> success`),
2. flujo con reintento (`running -> retry -> pending`),
3. agotamiento de reintentos y paso a `dead_letter`,
4. cancelación en `pending` y en `running`,
5. deduplicación por clave de item/firma y por existencia de job activo.

Criterios de aceptación de estas pruebas:
- no hay transiciones inválidas ni reapertura de estados terminales;
- `attempts` incrementa de forma consistente por ejecución real;
- los casos de deduplicación no crean jobs duplicados en `pending|running|retry`.

## Cobertura mínima específica del contrato YAML (Hito 3)
- Unitarias: `tests/unit/test_yaml_contract.py`.
- Integración: `tests/integration/test_yaml_contract_consistency.py`.
- E2E: `tests/e2e/test_yaml_contract_flow.py`.
- Regresión: `tests/regression/test_hito3_yaml_contract_regression.py`.

## Cobertura mínima específica de parseo/carga (Hito 4)
- Unitarias: `tests/unit/test_config_loader.py`.
- Integración: `tests/integration/test_config_loader_domain_integration.py`.
- E2E: `tests/e2e/test_config_loader_flow.py`.
- Regresión: `tests/regression/test_hito4_config_loader_regression.py`.

## Cobertura mínima específica de validación estructural/semántica (Hito 5)
- Unitarias: `tests/unit/test_config_validation.py`.
- Integración: `tests/integration/test_config_validation_integration.py`.
- E2E: `tests/e2e/test_config_validation_flow.py`.
- Regresión: `tests/regression/test_hito5_validation_regression.py`.

## Cobertura mínima específica de resolución efectiva (Hito 6)
- Unitarias: `tests/unit/test_effective_resolution.py`.
- Integración: `tests/integration/test_effective_resolution_integration.py`.
- E2E: `tests/e2e/test_effective_resolution_flow.py`.
- Regresión: `tests/regression/test_hito6_effective_resolution_regression.py`.

## Cobertura mínima específica de overrides controlados (Hito 7)
- Unitarias: `tests/unit/test_override_policies.py`.
- Integración: `tests/integration/test_override_policies_integration.py`.
- E2E: `tests/e2e/test_override_policies_flow.py`.
- Regresión: `tests/regression/test_hito7_override_policies_regression.py`.


## Cobertura mínima específica de modelado de postprocesados (Hito 8)
- Unitarias: `tests/unit/test_postprocessing_resolution.py`.
- Integración: `tests/integration/test_postprocessing_integration.py`.
- E2E: `tests/e2e/test_postprocessing_flow.py`.
- Regresión: `tests/regression/test_hito8_postprocessing_regression.py`.

## Cobertura mínima específica del contrato de integración con ytdl-sub (Hito 9)
- Unitarias: `tests/unit/test_ytdl_sub_contract.py`.
- Integración: `tests/integration/test_ytdl_sub_contract_integration.py`.
- E2E: `tests/e2e/test_ytdl_sub_contract_flow.py`.
- Regresión: `tests/regression/test_hito9_ytdl_sub_contract_regression.py`.

## Cobertura mínima específica de traducción a modelo ytdl-sub (Hito 10)
- Unitarias: `tests/unit/test_ytdl_sub_translation.py`.
- Integración: `tests/integration/test_ytdl_sub_translation_integration.py`.
- E2E: `tests/e2e/test_ytdl_sub_translation_flow.py`.
- Regresión: `tests/regression/test_hito10_ytdl_sub_translation_regression.py`.

## Cobertura mínima específica de compilación de artefactos (Hito 11)
- Unitarias: `tests/unit/test_artifact_compiler.py`.
- Integración: `tests/integration/test_artifact_compiler_integration.py`.
- E2E: `tests/e2e/test_artifact_compiler_flow.py`.
- Regresión: `tests/regression/test_hito11_artifact_compilation_regression.py`.


## Cobertura mínima específica de ejecución controlada ytdl-sub (Hito 12)
- Unitarias: `tests/unit/test_ytdl_sub_executor.py`.
- Integración: `tests/integration/test_ytdl_sub_executor_integration.py`.
- E2E: `tests/e2e/test_ytdl_sub_executor_flow.py`.
- Regresión: `tests/regression/test_hito12_ytdl_sub_executor_regression.py`.

## Cobertura mínima específica de persistencia y estado operativo SQLite (Hito 13)
- Unitarias: `tests/unit/test_sqlite_operational_state.py`.
- Integración: `tests/integration/test_hito13_persistence_integration.py`.
- E2E: `tests/e2e/test_hito13_persistence_flow.py`.
- Regresión: `tests/regression/test_hito13_persistence_regression.py`.


## Cobertura mínima específica de anti-redescarga, historial y trazabilidad (Hito 14)
- Unitarias: `tests/unit/test_sqlite_operational_state.py`.
- Integración: `tests/integration/test_hito14_anti_redownload_integration.py`.
- E2E: `tests/e2e/test_hito14_anti_redownload_flow.py`.
- Regresión: `tests/regression/test_hito14_anti_redownload_regression.py`.
