# Comandos operativos del core (Hito 0 en curso)

Estado: **en ejecución**. Esta guía define comandos mínimos operativos sin declarar cierre de hito.

## Instalación entorno dev
- Linux/macOS: `python -m pip install -e ".[dev]"`
- Windows PowerShell: `python -m pip install -e ".[dev]"`

## Bootstrap oficial (Hito 0 en curso)
- Linux/macOS (make): `make bootstrap`
- Windows PowerShell (oficial, sin `make`): `./scripts/bootstrap-dev.ps1`

## Entrypoint/arranque
- Linux/macOS: `PATH="tests/fixtures/bin:$PATH" python -m src.api.cli --config tests/fixtures/clean/minimal.yaml`
- Windows PowerShell (sin `make`): `./scripts/bootstrap-dev.ps1`
- Windows PowerShell (equivalente inline): `$env:PATH = "tests/fixtures/bin;$env:PATH"; python -m src.api.cli --config tests/fixtures/clean/minimal.yaml`

## Lint
- `python -m ruff check src tests`

## Unit tests
- `python -m pytest tests/unit -m unit`

## Integración
- `python -m pytest tests/integration -m integration`

## E2E
- `python -m pytest tests/e2e -m e2e`

## Regresión acumulada (Hito 0)
- `python -m pytest tests/regression -m regression`
- (opcional consolidado) `python -m pytest -m "unit or integration or e2e or regression"`


## Verificación de dependencias runtime (real)
- `ytdl-sub --version`
- `ffmpeg -version`
- `ffprobe -version`

## Smoke bootstrap con dependencias reales
- Linux/macOS: `make bootstrap` (incluye `tests/fixtures/bin` en `PATH` para smoke reproducible)
- Windows PowerShell: `./scripts/bootstrap-dev.ps1`

## Verificación específica Hito 11 (compilación)
- Unitarias compilador: `python -m pytest tests/unit/test_artifact_compiler.py`
- Integración traductor+compilador: `python -m pytest tests/integration/test_artifact_compiler_integration.py`
- E2E compilación en disco: `python -m pytest tests/e2e/test_artifact_compiler_flow.py`
- Regresión de artefactos compilados: `python -m pytest tests/regression/test_hito11_artifact_compilation_regression.py`


## Verificación específica Hito 12 (ejecución controlada)
- Unitarias ejecutor: `python -m pytest tests/unit/test_ytdl_sub_executor.py`
- Integración compilador+ejecutor: `python -m pytest tests/integration/test_ytdl_sub_executor_integration.py`
- E2E de ejecución controlada: `python -m pytest tests/e2e/test_ytdl_sub_executor_flow.py`
- Regresión Hito 12: `python -m pytest tests/regression/test_hito12_ytdl_sub_executor_regression.py`

## Verificación específica Hito 13 (persistencia SQLite operativa)
- Unitarias persistencia/repositorios: `python -m pytest tests/unit/test_sqlite_operational_state.py`
- Integración ejecutor+persistencia: `python -m pytest tests/integration/test_hito13_persistence_integration.py`
- E2E de huella persistida completa: `python -m pytest tests/e2e/test_hito13_persistence_flow.py`
- Regresión Hito 13: `python -m pytest tests/regression/test_hito13_persistence_regression.py`


## Verificación específica Hito 14 (anti-redescarga, historial y trazabilidad)
- Unitarias anti-redescarga/historial: `python -m pytest tests/unit/test_sqlite_operational_state.py -k hito14`
- Integración anti-redescarga persistida: `python -m pytest tests/integration/test_hito14_anti_redownload_integration.py`
- E2E primera ejecución + descarte duplicado: `python -m pytest tests/e2e/test_hito14_anti_redownload_flow.py`
- Regresión duplicado canónico: `python -m pytest tests/regression/test_hito14_anti_redownload_regression.py`

## Verificación específica Hito 15 (retención, purga y limpieza)
- Unitarias retención/purga: `python -m pytest tests/unit/test_sqlite_operational_state.py -k hito15`
- Integración persistencia+filesystem+purga: `python -m pytest tests/integration/test_hito15_retention_integration.py`
- E2E flujo multi-item + purga automática: `python -m pytest tests/e2e/test_hito15_retention_flow.py`
- Regresión dataset sobrecapacidad determinista: `python -m pytest tests/regression/test_hito15_retention_regression.py`

## Verificación específica Hito 16 (sistema de caché)
- Unitarias caché core: `python -m pytest tests/unit/test_hito16_cache_system.py`
- Integración caché con validación/traducción/compilación: `python -m pytest tests/integration/test_hito16_cache_integration.py`
- E2E doble ejecución con menor recomputación: `python -m pytest tests/e2e/test_hito16_cache_flow.py`
- Regresión de hits/invalidaciones/igualdad funcional: `python -m pytest tests/regression/test_hito16_cache_regression.py`


## Verificación específica Hito 17 (colas: modelo y persistencia)
- Unitarias entidad/transiciones/firma: `python -m pytest tests/unit/test_hito17_queue_models.py`
- Unitarias esquema persistente cola: `python -m pytest tests/unit/test_sqlite_operational_state.py -k hito17`
- Integración cola + SQLite + asociación: `python -m pytest tests/integration/test_hito17_queue_integration.py`
- E2E alta múltiple + consulta cola completa: `python -m pytest tests/e2e/test_hito17_queue_flow.py`
- Regresión cola canónica: `python -m pytest tests/regression/test_hito17_queue_regression.py`


## Verificación específica Hito 18 (colas: ejecución, reintentos y concurrencia)
- Unitarias runtime/retry/concurrencia/dead-letter: `python -m pytest tests/unit/test_hito18_queue_runtime.py`
- Unitarias persistencia cola H18: `python -m pytest tests/unit/test_sqlite_operational_state.py -k hito18`
- Integración workers + persistencia + reglas de retry/dead-letter: `python -m pytest tests/integration/test_hito18_queue_runtime_integration.py`
- E2E cola poblada -> workers -> estados finales: `python -m pytest tests/e2e/test_hito18_queue_runtime_flow.py`
- Regresión mixta H18 (success+retry+dead-letter): `python -m pytest tests/regression/test_hito18_queue_runtime_regression.py`


## Verificación específica Hito 19 (API propia del core)
- Unitarias handlers/serialización/payload: `python -m pytest tests/unit/test_hito19_core_api.py`
- Integración API + dominio/persistencia/cola/caché: `python -m pytest tests/integration/test_hito19_core_api_integration.py`
- E2E cliente API -> validación/cola/ejecución/estado: `python -m pytest tests/e2e/test_hito19_core_api_flow.py`
- Regresión contrato API H19: `python -m pytest tests/regression/test_hito19_core_api_regression.py`


## Verificación específica Hito 20 (suite de pruebas integral)
- Unitarias de integridad de suite H20: `python -m pytest tests/unit/test_hito20_integral_suite.py`
- Integración transversal del core completo: `python -m pytest tests/integration/test_hito20_integral_integration.py`
- E2E integral controlado + chequeo opcional de binario real: `python -m pytest tests/e2e/test_hito20_integral_flow.py`
- Regresión de contratos cruzados del hito: `python -m pytest tests/regression/test_hito20_integral_suite_regression.py`
- Ejecución focalizada consolidada H20: `python -m pytest tests/unit/test_hito20_integral_suite.py tests/integration/test_hito20_integral_integration.py tests/e2e/test_hito20_integral_flow.py tests/regression/test_hito20_integral_suite_regression.py`


## Verificación específica Hito 21 (core completo endurecido)
- Unitarias de endurecimiento: `python -m pytest tests/unit/test_hito21_core_hardening.py`
- Integración de errores operativos API: `python -m pytest tests/integration/test_hito21_core_hardening_integration.py`
- E2E CLI con payload de error estable: `python -m pytest tests/e2e/test_hito21_core_hardening_flow.py`
- Regresión del hito: `python -m pytest tests/regression/test_hito21_core_hardening_regression.py`
- Ejecución focalizada consolidada H21: `python -m pytest tests/unit/test_hito21_core_hardening.py tests/integration/test_hito21_core_hardening_integration.py tests/e2e/test_hito21_core_hardening_flow.py tests/regression/test_hito21_core_hardening_regression.py`

## Límite explícito tras cierre del core
A partir de este punto el core queda preparado para iniciar, en un proyecto separado, la construcción de TUI/GUI web.
Este repositorio mantiene alcance de núcleo operativo (sin frontend, autenticación ni multiusuario).
