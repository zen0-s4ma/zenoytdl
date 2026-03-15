.PHONY: lint test-unit test-integration test-e2e test-regression test-all test-hito20 test-hito21 bootstrap

bootstrap:
	PATH="tests/fixtures/bin:$$PATH" python -m src.api.cli --config tests/fixtures/clean/minimal.yaml

lint:
	python -m ruff check src tests

test-unit:
	python -m pytest tests/unit -m unit

test-integration:
	python -m pytest tests/integration -m integration

test-e2e:
	python -m pytest tests/e2e -m e2e

test-regression:
	python -m pytest tests/regression -m regression

test-all:
	python -m pytest -m "unit or integration or e2e or regression"


test-hito20:
	python -m pytest tests/unit/test_hito20_integral_suite.py tests/integration/test_hito20_integral_integration.py tests/e2e/test_hito20_integral_flow.py tests/regression/test_hito20_integral_suite_regression.py


test-hito21:
	python -m pytest tests/unit/test_hito21_core_hardening.py tests/integration/test_hito21_core_hardening_integration.py tests/e2e/test_hito21_core_hardening_flow.py tests/regression/test_hito21_core_hardening_regression.py
