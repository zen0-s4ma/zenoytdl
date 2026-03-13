import pytest

from src.persistence.sqlite_health import sqlite_smoke_check


@pytest.mark.integration
def test_sqlite_smoke_check_creates_and_queries_database(tmp_path) -> None:
    db_path = tmp_path / "state.sqlite"
    assert sqlite_smoke_check(str(db_path)) is True
    assert db_path.exists()
