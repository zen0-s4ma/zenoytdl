import shutil
import sqlite3

from src.domain.runtime import DependencyStatus


def detect_binary(name: str) -> DependencyStatus:
    binary_path = shutil.which(name)
    if binary_path:
        return DependencyStatus(name=name, available=True, detail=binary_path)
    return DependencyStatus(name=name, available=False, detail="No encontrado en PATH")


def detect_sqlite() -> DependencyStatus:
    try:
        version = sqlite3.sqlite_version
    except Exception as exc:  # pragma: no cover - extremo defensivo
        return DependencyStatus(name="sqlite", available=False, detail=str(exc))
    return DependencyStatus(name="sqlite", available=True, detail=version)
