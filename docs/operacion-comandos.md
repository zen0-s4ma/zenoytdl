# Comandos operativos del core (Hito 0 en curso)

Estado: **en ejecución**. Esta guía define comandos mínimos operativos sin declarar cierre de hito.

## Entrypoint/arranque
- `python -m src.api.cli --config tests/fixtures/clean/minimal.yaml`

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
