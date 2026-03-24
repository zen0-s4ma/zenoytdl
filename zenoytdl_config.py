from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


DEFAULT_CONFIG: dict[str, Any] = {
    "containers": {
        "ytdl_sub": "ytdl-sub",
        "beets": "beets-streaming2",
    },
    "paths": {
        "local": {
            "config_user_dir": "config/user",
            "runtime_base_dir": "config/runtime",
        },
        "remote": {
            "project_root": "/config/zenoytdl",
            "config_user_dir": "/config/zenoytdl/config/user",
            "runtime_base_dir": "/config/zenoytdl/config/runtime",
            "remote_trim_script": "/tmp/trim-ambience-video.py",
        },
        "downloads_root": {
            "prod": "/downloads",
            "test": "/downloads-test",
        },
        "beets_library": {
            "prod": "/config/musiclibrary.db",
            "test": "/config/musiclibrary-test.db",
        },
        "beets_log": {
            "prod": "/config/logs/beets-import.log",
            "test": "/config/logs/beets-import-test.log",
        },
    },
}


@dataclass(frozen=True)
class ProjectSettings:
    project_root: Path
    config_file: Path
    config_user_dir: Path
    runtime_base_dir: Path
    mode: str
    downloads_root: str
    beets_library_path: str
    beets_log_path: str
    ytdl_container: str
    beets_container: str
    remote_project_root: str
    remote_config_user_dir: str
    remote_runtime_base_dir: str
    remote_trim_script: str

    @property
    def runtime_dir(self) -> Path:
        return self.runtime_base_dir / self.mode

    @property
    def remote_runtime_dir(self) -> str:
        return f"{self.remote_runtime_base_dir.rstrip('/')}/{self.mode}"


# Compatibilidad hacia atrás con el nombre usado en la versión anterior.
    @property
    def container_project_root(self) -> str:
        return self.remote_project_root


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def _normalize_mode(mode: str) -> str:
    normalized = str(mode).strip().lower()
    if normalized not in {"prod", "test"}:
        raise ValueError(f"Modo no soportado: {mode}")
    return normalized


def resolve_project_root(project_root: Path | None = None, *, reference_file: str | None = None) -> Path:
    if project_root is not None:
        return Path(project_root).expanduser().resolve()
    if reference_file:
        ref_path = Path(reference_file).resolve()
        if ref_path.parent.name == "tools":
            return ref_path.parent.parent
        return ref_path.parent
    return Path(__file__).resolve().parent


def load_raw_config(project_root: Path | None = None, *, reference_file: str | None = None) -> tuple[Path, Path, dict[str, Any]]:
    resolved_root = resolve_project_root(project_root, reference_file=reference_file)
    config_file = resolved_root / "config" / "zenoytdl.yml"
    file_data: dict[str, Any] = {}
    if config_file.exists():
        with config_file.open("r", encoding="utf-8") as fh:
            loaded = yaml.safe_load(fh) or {}
        if not isinstance(loaded, dict):
            raise ValueError(f"El fichero de configuración no contiene un mapa YAML válido: {config_file}")
        file_data = loaded
    merged = _deep_merge(DEFAULT_CONFIG, file_data)
    return resolved_root, config_file, merged


def _require_str(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"Valor vacío para {label}")
    return text


def _get_local_paths(paths: dict[str, Any]) -> dict[str, Any]:
    local = deepcopy(paths.get("local") or {})
    if not local:
        # Compatibilidad con la versión inicial del YAML.
        if paths.get("config_user_dir"):
            local["config_user_dir"] = paths.get("config_user_dir")
        if paths.get("runtime_base_dir"):
            local["runtime_base_dir"] = paths.get("runtime_base_dir")
    return local


def _get_remote_paths(paths: dict[str, Any]) -> dict[str, Any]:
    remote = deepcopy(paths.get("remote") or {})
    if not remote:
        # Compatibilidad con la versión inicial del YAML.
        project_root = paths.get("container_project_root") or "/config/zenoytdl"
        remote = {
            "project_root": project_root,
            "config_user_dir": f"{str(project_root).rstrip('/')}/config/user",
            "runtime_base_dir": f"{str(project_root).rstrip('/')}/config/runtime",
            "remote_trim_script": paths.get("remote_trim_script") or "/tmp/trim-ambience-video.py",
        }
    else:
        project_root = remote.get("project_root") or paths.get("container_project_root") or "/config/zenoytdl"
        remote["project_root"] = project_root
        remote.setdefault("config_user_dir", f"{str(project_root).rstrip('/')}/config/user")
        remote.setdefault("runtime_base_dir", f"{str(project_root).rstrip('/')}/config/runtime")
        remote.setdefault("remote_trim_script", paths.get("remote_trim_script") or "/tmp/trim-ambience-video.py")
    return remote


def resolve_settings(
    mode: str,
    *,
    project_root: Path | None = None,
    downloads_root_override: str | None = None,
    reference_file: str | None = None,
) -> ProjectSettings:
    normalized_mode = _normalize_mode(mode)
    resolved_root, config_file, data = load_raw_config(project_root, reference_file=reference_file)

    paths = data.get("paths") or {}
    containers = data.get("containers") or {}
    local_paths = _get_local_paths(paths)
    remote_paths = _get_remote_paths(paths)

    config_user_dir = resolved_root / _require_str(local_paths.get("config_user_dir"), "paths.local.config_user_dir")
    runtime_base_dir = resolved_root / _require_str(local_paths.get("runtime_base_dir"), "paths.local.runtime_base_dir")

    downloads_root_map = paths.get("downloads_root") or {}
    downloads_root = str(downloads_root_override or downloads_root_map.get(normalized_mode) or "").strip()
    if not downloads_root:
        raise ValueError(f"No se ha podido resolver downloads_root para mode={normalized_mode}")

    beets_library_map = paths.get("beets_library") or {}
    beets_log_map = paths.get("beets_log") or {}

    beets_library_path = _require_str(beets_library_map.get(normalized_mode), f"paths.beets_library.{normalized_mode}")
    beets_log_path = _require_str(beets_log_map.get(normalized_mode), f"paths.beets_log.{normalized_mode}")

    ytdl_container = _require_str(containers.get("ytdl_sub"), "containers.ytdl_sub")
    beets_container = _require_str(containers.get("beets"), "containers.beets")
    remote_project_root = _require_str(remote_paths.get("project_root"), "paths.remote.project_root")
    remote_config_user_dir = _require_str(remote_paths.get("config_user_dir"), "paths.remote.config_user_dir")
    remote_runtime_base_dir = _require_str(remote_paths.get("runtime_base_dir"), "paths.remote.runtime_base_dir")
    remote_trim_script = _require_str(remote_paths.get("remote_trim_script"), "paths.remote.remote_trim_script")

    runtime_base_dir.mkdir(parents=True, exist_ok=True)
    (runtime_base_dir / normalized_mode).mkdir(parents=True, exist_ok=True)

    return ProjectSettings(
        project_root=resolved_root,
        config_file=config_file,
        config_user_dir=config_user_dir,
        runtime_base_dir=runtime_base_dir,
        mode=normalized_mode,
        downloads_root=downloads_root,
        beets_library_path=beets_library_path,
        beets_log_path=beets_log_path,
        ytdl_container=ytdl_container,
        beets_container=beets_container,
        remote_project_root=remote_project_root,
        remote_config_user_dir=remote_config_user_dir,
        remote_runtime_base_dir=remote_runtime_base_dir,
        remote_trim_script=remote_trim_script,
    )
