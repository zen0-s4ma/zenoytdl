from pathlib import Path


class ConfigBootstrapError(ValueError):
    pass


def ensure_minimal_config(config_path: str) -> Path:
    path = Path(config_path)
    if not path.exists():
        raise ConfigBootstrapError(f"Config no encontrado: {path}")
    if path.suffix not in {".yml", ".yaml"}:
        raise ConfigBootstrapError(f"Extensión no soportada: {path.suffix}")
    if not path.read_text(encoding="utf-8").strip():
        raise ConfigBootstrapError(f"Config vacío: {path}")
    return path
