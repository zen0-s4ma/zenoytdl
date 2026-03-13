import pytest

from src.integration.dependencies import detect_binary, detect_sqlite


@pytest.mark.unit
def test_detect_sqlite_available() -> None:
    status = detect_sqlite()
    assert status.available is True
    assert status.name == "sqlite"


@pytest.mark.unit
def test_detect_binary_missing_returns_not_available(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.integration.dependencies.shutil.which", lambda _: None)
    status = detect_binary("ytdl-sub")
    assert status.available is False
