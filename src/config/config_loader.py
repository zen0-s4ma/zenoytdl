from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.config.yaml_contract import REQUIRED_YAML_FILES, _parse_simple_yaml
from src.domain import DomainCatalog, GeneralConfig, Profile, Subscription, SubscriptionSourceKind


class ConfigLoadError(ValueError):
    """Error base para carga y parseo del bundle de configuración."""


class YAMLSyntaxError(ConfigLoadError):
    """Error de sintaxis YAML."""


class YAMLStructureError(ConfigLoadError):
    """Error de estructura/shape del documento."""


class MissingDataError(ConfigLoadError):
    """Error por archivo/campo obligatorio ausente."""


class CoercionError(ConfigLoadError):
    """Error de coerción a tipo esperado."""


class PathResolutionError(ConfigLoadError):
    """Error resolviendo rutas/referencias de ficheros."""


@dataclass(frozen=True)
class ParsedGeneral:
    workspace: Path
    default_profile: str
    environment: str
    log_level: str
    dry_run: bool
    library_dir: Path


@dataclass(frozen=True)
class ParsedProfile:
    name: str
    media_type: str
    quality_profile: str


@dataclass(frozen=True)
class ParsedSchedule:
    mode: str
    every_hours: int | None


@dataclass(frozen=True)
class ParsedSubscription:
    name: str
    profile: str
    sources: tuple[str, ...]
    enabled: bool
    schedule: ParsedSchedule


@dataclass(frozen=True)
class ParsedYtdlSubConf:
    integration_provider: str
    integration_binary: str
    integration_min_version: str
    profile_preset_map: dict[str, str]
    invocation_extra_args: tuple[str, ...]


@dataclass(frozen=True)
class ParsedConfigBundle:
    config_dir: Path
    file_paths: dict[str, Path]
    general: ParsedGeneral
    profiles: tuple[ParsedProfile, ...]
    subscriptions: tuple[ParsedSubscription, ...]
    ytdl_sub_conf: ParsedYtdlSubConf
    raw_documents: dict[str, dict[str, Any]]
    signature: str

    def to_domain_catalog(self) -> DomainCatalog:
        general = GeneralConfig(
            id="general",
            workspace=str(self.general.workspace),
            library_dir=str(self.general.library_dir),
            timezone="UTC",
        )
        profiles = tuple(
            Profile(
                id=item.name,
                name=item.name,
                base_options={
                    "media_type": item.media_type,
                    "quality_profile": item.quality_profile,
                },
            )
            for item in self.profiles
        )
        subscriptions = tuple(
            Subscription(
                id=item.name,
                profile_id=item.profile,
                source_kind=_coerce_source_kind(item.sources[0]),
                source_value=item.sources[0],
            )
            for item in self.subscriptions
        )
        return DomainCatalog.build(
            general_config=general,
            profiles=profiles,
            subscriptions=subscriptions,
            postprocessings=(),
            overrides=(),
        )


def load_parsed_config_bundle(config_dir: str | Path) -> ParsedConfigBundle:
    base = Path(config_dir)
    if not base.is_absolute():
        base = (Path.cwd() / base).resolve()
    if not base.exists() or not base.is_dir():
        raise PathResolutionError(f"Ruta de configuración inválida: {base}")

    file_paths = {name: base / name for name in REQUIRED_YAML_FILES}
    raw_documents = {name: _load_yaml_file(path) for name, path in file_paths.items()}

    general = _parse_general(raw_documents["general.yaml"], base)
    profiles = _parse_profiles(raw_documents["profiles.yaml"])
    subscriptions = _parse_subscriptions(raw_documents["subscriptions.yaml"])
    ytdl_sub_conf = _parse_ytdl_sub_conf(raw_documents["ytdl-sub-conf.yaml"], base)

    return ParsedConfigBundle(
        config_dir=base,
        file_paths=file_paths,
        general=general,
        profiles=profiles,
        subscriptions=subscriptions,
        ytdl_sub_conf=ytdl_sub_conf,
        raw_documents=raw_documents,
        signature=build_config_signature(raw_documents),
    )


def build_config_signature(raw_documents: dict[str, dict[str, Any]]) -> str:
    canonical = json.dumps(raw_documents, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _load_yaml_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise MissingDataError(f"Falta archivo obligatorio: {path.name}")
    try:
        payload = _parse_simple_yaml(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise YAMLSyntaxError(f"YAML inválido en {path.name}: {exc}") from exc

    if not isinstance(payload, dict):
        raise YAMLStructureError(f"{path.name} debe contener un objeto YAML")
    return payload


def _parse_general(payload: dict[str, Any], config_dir: Path) -> ParsedGeneral:
    workspace = _require_str(payload, "workspace", "general.yaml")
    default_profile = _require_str(payload, "default_profile", "general.yaml")
    environment = _require_str(payload, "environment", "general.yaml")

    log_level = payload.get("log_level", "INFO")
    if not isinstance(log_level, str):
        raise CoercionError("general.yaml.log_level debe ser string")

    execution = payload.get("execution", {})
    if execution is None:
        execution = {}
    if not isinstance(execution, dict):
        raise YAMLStructureError("general.yaml.execution debe ser objeto")
    dry_run = execution.get("dry_run", False)
    if not isinstance(dry_run, bool):
        raise CoercionError("general.yaml.execution.dry_run debe ser booleano")

    workspace_path = _resolve_path(config_dir, workspace)
    library_dir_raw = payload.get("library_dir", str(workspace_path / "library"))
    if not isinstance(library_dir_raw, str):
        raise CoercionError("general.yaml.library_dir debe ser string")
    library_dir = _resolve_path(config_dir, library_dir_raw)

    return ParsedGeneral(
        workspace=workspace_path,
        default_profile=default_profile,
        environment=environment,
        log_level=log_level,
        dry_run=dry_run,
        library_dir=library_dir,
    )


def _parse_profiles(payload: dict[str, Any]) -> tuple[ParsedProfile, ...]:
    entries = payload.get("profiles")
    if not isinstance(entries, list) or not entries:
        raise YAMLStructureError("profiles.yaml.profiles debe ser lista no vacía")
    parsed: list[ParsedProfile] = []
    for index, item in enumerate(entries):
        if not isinstance(item, dict):
            raise YAMLStructureError(f"profiles.yaml.profiles[{index}] debe ser objeto")
        parsed.append(
            ParsedProfile(
                name=_require_str(item, "name", f"profiles.yaml.profiles[{index}]"),
                media_type=_require_str(item, "media_type", f"profiles.yaml.profiles[{index}]"),
                quality_profile=_require_str(
                    item,
                    "quality_profile",
                    f"profiles.yaml.profiles[{index}]",
                ),
            )
        )
    return tuple(parsed)


def _parse_subscriptions(payload: dict[str, Any]) -> tuple[ParsedSubscription, ...]:
    entries = payload.get("subscriptions")
    if not isinstance(entries, list) or not entries:
        raise YAMLStructureError("subscriptions.yaml.subscriptions debe ser lista no vacía")

    parsed: list[ParsedSubscription] = []
    for index, item in enumerate(entries):
        scope = f"subscriptions.yaml.subscriptions[{index}]"
        if not isinstance(item, dict):
            raise YAMLStructureError(f"{scope} debe ser objeto")
        sources_raw = item.get("sources")
        if not isinstance(sources_raw, list) or not sources_raw:
            raise MissingDataError(f"{scope}.sources es obligatorio y no vacío")
        sources = tuple(_coerce_str(value, f"{scope}.sources") for value in sources_raw)

        schedule_raw = item.get("schedule", {})
        if schedule_raw is None:
            schedule_raw = {}
        if not isinstance(schedule_raw, dict):
            raise YAMLStructureError(f"{scope}.schedule debe ser objeto")
        mode = _coerce_str(schedule_raw.get("mode", "manual"), f"{scope}.schedule.mode")
        every_hours_raw = schedule_raw.get("every_hours")
        if every_hours_raw is None:
            every_hours = None
        else:
            every_hours = _coerce_int(every_hours_raw, f"{scope}.schedule.every_hours")

        parsed.append(
            ParsedSubscription(
                name=_require_str(item, "name", scope),
                profile=_require_str(item, "profile", scope),
                sources=sources,
                enabled=_coerce_bool(item.get("enabled", True), f"{scope}.enabled"),
                schedule=ParsedSchedule(mode=mode, every_hours=every_hours),
            )
        )
    return tuple(parsed)


def _parse_ytdl_sub_conf(payload: dict[str, Any], config_dir: Path) -> ParsedYtdlSubConf:
    integration = payload.get("integration")
    if not isinstance(integration, dict):
        raise YAMLStructureError("ytdl-sub-conf.yaml.integration debe ser objeto")

    provider = _coerce_str(integration.get("provider", "ytdl-sub"), "integration.provider")
    min_version = _require_str(integration, "min_version", "ytdl-sub-conf.yaml.integration")
    binary = _coerce_str(integration.get("binary", "ytdl-sub"), "integration.binary")
    binary_path = _resolve_optional_path_like(config_dir, binary)

    profile_preset_map = payload.get("profile_preset_map")
    if not isinstance(profile_preset_map, dict) or not profile_preset_map:
        raise MissingDataError("ytdl-sub-conf.yaml.profile_preset_map es obligatorio")

    parsed_preset_map: dict[str, str] = {}
    for key, value in profile_preset_map.items():
        parsed_preset_map[_coerce_str(key, "profile_preset_map.key")] = _coerce_str(
            value,
            "profile_preset_map.value",
        )

    invocation = payload.get("invocation", {})
    if invocation is None:
        invocation = {}
    if not isinstance(invocation, dict):
        raise YAMLStructureError("ytdl-sub-conf.yaml.invocation debe ser objeto")
    extra_args_raw = invocation.get("extra_args", [])
    if not isinstance(extra_args_raw, list):
        raise CoercionError("ytdl-sub-conf.yaml.invocation.extra_args debe ser lista")
    extra_args = tuple(_coerce_str(arg, "invocation.extra_args") for arg in extra_args_raw)

    return ParsedYtdlSubConf(
        integration_provider=provider,
        integration_binary=str(binary_path),
        integration_min_version=min_version,
        profile_preset_map=parsed_preset_map,
        invocation_extra_args=extra_args,
    )


def _require_str(payload: dict[str, Any], key: str, scope: str) -> str:
    if key not in payload:
        raise MissingDataError(f"{scope}.{key} es obligatorio")
    return _coerce_str(payload[key], f"{scope}.{key}")


def _coerce_str(value: Any, scope: str) -> str:
    if not isinstance(value, str):
        raise CoercionError(f"{scope} debe ser string")
    normalized = value.strip()
    if not normalized:
        raise CoercionError(f"{scope} no puede estar vacío")
    return normalized


def _coerce_bool(value: Any, scope: str) -> bool:
    if not isinstance(value, bool):
        raise CoercionError(f"{scope} debe ser booleano")
    return value


def _coerce_int(value: Any, scope: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise CoercionError(f"{scope} debe ser entero")
    return value


def _resolve_path(base: Path, candidate: str) -> Path:
    try:
        path = Path(candidate)
    except Exception as exc:  # pragma: no cover - protección defensiva
        raise PathResolutionError(f"Ruta inválida: {candidate}") from exc
    return path if path.is_absolute() else (base / path).resolve()


def _resolve_optional_path_like(base: Path, candidate: str) -> Path:
    if "/" in candidate or "\\" in candidate or candidate.startswith("."):
        return _resolve_path(base, candidate)
    return Path(candidate)


def _coerce_source_kind(source: str) -> SubscriptionSourceKind:
    if "playlist" in source:
        return SubscriptionSourceKind.PLAYLIST
    if source.startswith("ytsearch") or source.startswith("search:"):
        return SubscriptionSourceKind.SEARCH
    return SubscriptionSourceKind.CHANNEL
