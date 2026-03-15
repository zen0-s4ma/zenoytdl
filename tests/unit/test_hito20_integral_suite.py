from pathlib import Path

import pytest

REQUIRED_SUITE_FILES = {
    "dominio": "tests/unit/test_domain_models.py",
    "parseo": "tests/unit/test_config_loader.py",
    "validacion": "tests/unit/test_config_validation.py",
    "herencia_overrides": "tests/unit/test_override_policies.py",
    "traduccion": "tests/unit/test_ytdl_sub_translation.py",
    "compilacion": "tests/unit/test_artifact_compiler.py",
    "persistencia": "tests/unit/test_sqlite_operational_state.py",
    "cache": "tests/unit/test_hito16_cache_system.py",
    "colas": "tests/unit/test_hito17_queue_models.py",
    "runtime_colas": "tests/unit/test_hito18_queue_runtime.py",
    "api": "tests/unit/test_hito19_core_api.py",
}


@pytest.mark.unit
def test_hito20_unit_suite_covers_all_critical_core_modules() -> None:
    missing = [path for path in REQUIRED_SUITE_FILES.values() if not Path(path).is_file()]
    assert missing == []


@pytest.mark.unit
def test_hito20_unit_suite_keeps_hito20_pyramid_files_present() -> None:
    expected = [
        "tests/unit/test_hito20_integral_suite.py",
        "tests/integration/test_hito20_integral_integration.py",
        "tests/e2e/test_hito20_integral_flow.py",
        "tests/regression/test_hito20_integral_suite_regression.py",
    ]
    missing = [path for path in expected if not Path(path).is_file()]
    assert missing == []
