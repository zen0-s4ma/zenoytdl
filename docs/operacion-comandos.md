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
