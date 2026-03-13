import ast
from pathlib import Path

import pytest


@pytest.mark.integration
def test_domain_layer_has_no_infrastructure_imports() -> None:
    domain_files = Path("src/domain").glob("*.py")
    forbidden_prefixes = ("sqlite3", "subprocess", "src.api", "src.persistence")

    for file_path in domain_files:
        module = ast.parse(file_path.read_text(encoding="utf-8"))
        for node in ast.walk(module):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith(forbidden_prefixes), file_path
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith(forbidden_prefixes), file_path
