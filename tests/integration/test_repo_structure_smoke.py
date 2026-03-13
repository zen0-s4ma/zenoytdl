from pathlib import Path

import pytest


@pytest.mark.integration
def test_repo_structure_matches_hito0_layered_layout() -> None:
    expected_paths = [
        Path("src/api"),
        Path("src/config"),
        Path("src/domain"),
        Path("src/integration"),
        Path("src/persistence"),
        Path("tests/unit"),
        Path("tests/integration"),
        Path("tests/e2e"),
        Path("tests/regression"),
        Path("examples"),
        Path("docs"),
        Path("schemas"),
    ]
    missing = [str(path) for path in expected_paths if not path.exists()]
    assert missing == []
