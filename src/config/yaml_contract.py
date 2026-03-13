from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

REQUIRED_YAML_FILES = (
    "general.yaml",
    "profiles.yaml",
    "subscriptions.yaml",
    "ytdl-sub-conf.yaml",
)
OPTIONAL_YAML_FILES = ("cache.yaml", "queues.yaml", "logging.yaml")

GENERAL_DEFAULTS = {
    "log_level": "INFO",
    "execution": {"dry_run": False},
}

YTDL_SUB_CONF_DEFAULTS = {
    "integration": {"provider": "ytdl-sub", "binary": "ytdl-sub"},
    "invocation": {"extra_args": []},
}


class ContractValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ContractBundle:
    general: dict[str, Any]
    profiles: dict[str, Any]
    subscriptions: dict[str, Any]
    ytdl_sub_conf: dict[str, Any]
    optional_files: tuple[str, ...]


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    lines = text.splitlines()
    cleaned: list[tuple[int, str]] = []
    for raw in lines:
        content = raw.split("#", 1)[0].rstrip()
        if not content.strip():
            continue
        cleaned.append((len(content) - len(content.lstrip(" ")), content.lstrip()))

    if not cleaned:
        return {}

    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]

    for index, (indent, content) in enumerate(cleaned):
        while stack and indent <= stack[-1][0]:
            stack.pop()
        if not stack:
            raise ContractValidationError("YAML inválido: indentación inconsistente")

        parent = stack[-1][1]
        next_line = cleaned[index + 1] if index + 1 < len(cleaned) else None

        if content.startswith("- "):
            if not isinstance(parent, list):
                raise ContractValidationError("YAML inválido: item de lista fuera de lista")
            item_text = content[2:].strip()
            if not item_text:
                new_item: dict[str, Any] = {}
                parent.append(new_item)
                stack.append((indent, new_item))
                continue
            if ":" in item_text:
                key, value_text = item_text.split(":", 1)
                item: dict[str, Any] = {key.strip(): _parse_scalar(value_text.strip())}
                parent.append(item)
                stack.append((indent, item))
            else:
                parent.append(_parse_scalar(item_text))
            continue

        if ":" not in content:
            raise ContractValidationError("YAML inválido: clave sin ':'")
        key, value_text = content.split(":", 1)
        key = key.strip()
        value_text = value_text.strip()

        if isinstance(parent, list):
            if not parent or not isinstance(parent[-1], dict):
                parent.append({})
            target = parent[-1]
        else:
            target = parent

        if value_text == "":
            next_is_list = bool(
                next_line
                and next_line[0] > indent
                and next_line[1].startswith("- ")
            )
            container: Any = [] if next_is_list else {}
            target[key] = container
            stack.append((indent, container))
        else:
            target[key] = _parse_scalar(value_text)

    if not isinstance(root, dict):
        raise ContractValidationError("YAML raíz inválido")
    return root


def _parse_scalar(value: str) -> Any:
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if value.startswith('"') and value.endswith('"') and len(value) >= 2:
        return value[1:-1]
    if value.startswith("'") and value.endswith("'") and len(value) >= 2:
        return value[1:-1]
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(part.strip()) for part in inner.split(",")]
    if value.isdigit():
        return int(value)
    return value


def load_contract_bundle(config_dir: str | Path) -> ContractBundle:
    base = Path(config_dir)
    if not base.exists() or not base.is_dir():
        raise ContractValidationError(f"Ruta de configuración inválida: {base}")

    loaded = {name: _load_yaml_file(base / name) for name in REQUIRED_YAML_FILES}
    optional = tuple(name for name in OPTIONAL_YAML_FILES if (base / name).exists())

    general = _apply_general_defaults(loaded["general.yaml"])
    profiles = loaded["profiles.yaml"]
    subscriptions = _apply_subscriptions_defaults(loaded["subscriptions.yaml"])
    ytdl_sub_conf = _apply_ytdl_sub_defaults(loaded["ytdl-sub-conf.yaml"])

    _validate_general(general)
    _validate_profiles(profiles)
    _validate_subscriptions(subscriptions)
    _validate_ytdl_sub_conf(ytdl_sub_conf)
    _validate_cross_file_consistency(general, profiles, subscriptions, ytdl_sub_conf)

    return ContractBundle(
        general=general,
        profiles=profiles,
        subscriptions=subscriptions,
        ytdl_sub_conf=ytdl_sub_conf,
        optional_files=optional,
    )


def _load_yaml_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ContractValidationError(f"Falta archivo obligatorio: {path.name}")
    payload = _parse_simple_yaml(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ContractValidationError(f"El archivo {path.name} debe contener un objeto YAML")
    return payload


def _apply_general_defaults(general: dict[str, Any]) -> dict[str, Any]:
    merged = dict(general)
    merged.setdefault("log_level", GENERAL_DEFAULTS["log_level"])
    execution = merged.get("execution")
    if execution is None:
        merged["execution"] = dict(GENERAL_DEFAULTS["execution"])
    elif isinstance(execution, dict):
        execution.setdefault("dry_run", GENERAL_DEFAULTS["execution"]["dry_run"])
    return merged


def _apply_subscriptions_defaults(subscriptions: dict[str, Any]) -> dict[str, Any]:
    merged = dict(subscriptions)
    subs = merged.get("subscriptions")
    if isinstance(subs, list):
        for item in subs:
            if isinstance(item, dict):
                item.setdefault("enabled", True)
    return merged


def _apply_ytdl_sub_defaults(conf: dict[str, Any]) -> dict[str, Any]:
    merged = dict(conf)
    integration = merged.get("integration")
    if integration is None:
        merged["integration"] = dict(YTDL_SUB_CONF_DEFAULTS["integration"])
    elif isinstance(integration, dict):
        integration.setdefault("provider", YTDL_SUB_CONF_DEFAULTS["integration"]["provider"])
        integration.setdefault("binary", YTDL_SUB_CONF_DEFAULTS["integration"]["binary"])

    invocation = merged.get("invocation")
    if invocation is None:
        merged["invocation"] = dict(YTDL_SUB_CONF_DEFAULTS["invocation"])
    elif isinstance(invocation, dict):
        invocation.setdefault(
            "extra_args",
            list(YTDL_SUB_CONF_DEFAULTS["invocation"]["extra_args"]),
        )
    return merged


def _validate_general(general: dict[str, Any]) -> None:
    _require_keys(general, "general.yaml", ("workspace", "environment", "default_profile"))
    _require_enum(general, "environment", {"development", "staging", "production"}, "general.yaml")
    _require_enum(general, "log_level", {"DEBUG", "INFO", "WARNING", "ERROR"}, "general.yaml")

    execution = general.get("execution")
    if execution is not None and not isinstance(execution, dict):
        raise ContractValidationError("general.yaml.execution debe ser un objeto")
    if (
        isinstance(execution, dict)
        and "dry_run" in execution
        and not isinstance(execution["dry_run"], bool)
    ):
        raise ContractValidationError("general.yaml.execution.dry_run debe ser booleano")


def _validate_profiles(profiles: dict[str, Any]) -> None:
    _require_keys(profiles, "profiles.yaml", ("profiles",))
    entries = profiles["profiles"]
    if not isinstance(entries, list) or not entries:
        raise ContractValidationError("profiles.yaml.profiles debe ser una lista no vacía")

    names: set[str] = set()
    for index, profile in enumerate(entries):
        if not isinstance(profile, dict):
            raise ContractValidationError(f"profiles.yaml.profiles[{index}] debe ser un objeto")
        _require_keys(
            profile,
            f"profiles.yaml.profiles[{index}]",
            ("name", "media_type", "quality_profile"),
        )
        _require_enum(
            profile,
            "media_type",
            {"video", "audio", "shorts"},
            f"profiles.yaml.profiles[{index}]",
        )
        name = profile["name"]
        if not isinstance(name, str) or not name.strip():
            raise ContractValidationError(
                f"profiles.yaml.profiles[{index}].name debe ser texto no vacío"
            )
        if name in names:
            raise ContractValidationError(f"profiles.yaml contiene perfil duplicado: {name}")
        names.add(name)


def _validate_subscriptions(subscriptions: dict[str, Any]) -> None:
    _require_keys(subscriptions, "subscriptions.yaml", ("subscriptions",))
    entries = subscriptions["subscriptions"]
    if not isinstance(entries, list) or not entries:
        raise ContractValidationError(
            "subscriptions.yaml.subscriptions debe ser una lista no vacía"
        )

    names: set[str] = set()
    for index, sub in enumerate(entries):
        if not isinstance(sub, dict):
            raise ContractValidationError(
                f"subscriptions.yaml.subscriptions[{index}] debe ser un objeto"
            )
        _require_keys(
            sub,
            f"subscriptions.yaml.subscriptions[{index}]",
            ("name", "profile", "sources"),
        )
        if not isinstance(sub["sources"], list) or not sub["sources"]:
            raise ContractValidationError(
                f"subscriptions.yaml.subscriptions[{index}].sources debe ser lista no vacía"
            )
        schedule = sub.get("schedule")
        if schedule is not None:
            if not isinstance(schedule, dict):
                raise ContractValidationError(
                    f"subscriptions.yaml.subscriptions[{index}].schedule debe ser objeto"
                )
            _require_keys(
                schedule,
                f"subscriptions.yaml.subscriptions[{index}].schedule",
                ("mode",),
            )
            _require_enum(
                schedule,
                "mode",
                {"manual", "interval"},
                f"subscriptions.yaml.subscriptions[{index}].schedule",
            )
            if schedule.get("mode") == "interval" and "every_hours" not in schedule:
                raise ContractValidationError(
                    "subscriptions.yaml.subscriptions"
                    f"[{index}].schedule.every_hours "
                    "es obligatorio cuando mode=interval"
                )
        if "enabled" in sub and not isinstance(sub["enabled"], bool):
            raise ContractValidationError(
                f"subscriptions.yaml.subscriptions[{index}].enabled debe ser booleano"
            )
        name = sub["name"]
        if not isinstance(name, str) or not name.strip():
            raise ContractValidationError(
                f"subscriptions.yaml.subscriptions[{index}].name debe ser texto no vacío"
            )
        if name in names:
            raise ContractValidationError(
                f"subscriptions.yaml contiene suscripción duplicada: {name}"
            )
        names.add(name)


def _validate_ytdl_sub_conf(conf: dict[str, Any]) -> None:
    _require_keys(conf, "ytdl-sub-conf.yaml", ("integration", "profile_preset_map"))
    integration = conf["integration"]
    if not isinstance(integration, dict):
        raise ContractValidationError("ytdl-sub-conf.yaml.integration debe ser un objeto")
    _require_keys(
        integration,
        "ytdl-sub-conf.yaml.integration",
        ("provider", "min_version", "binary"),
    )
    _require_enum(integration, "provider", {"ytdl-sub"}, "ytdl-sub-conf.yaml.integration")

    profile_map = conf["profile_preset_map"]
    if not isinstance(profile_map, dict) or not profile_map:
        raise ContractValidationError(
            "ytdl-sub-conf.yaml.profile_preset_map debe ser objeto no vacío"
        )

    invocation = conf.get("invocation")
    if invocation is not None and not isinstance(invocation, dict):
        raise ContractValidationError("ytdl-sub-conf.yaml.invocation debe ser objeto")
    if isinstance(invocation, dict) and "extra_args" in invocation and not isinstance(
        invocation["extra_args"], list
    ):
        raise ContractValidationError("ytdl-sub-conf.yaml.invocation.extra_args debe ser lista")


def _validate_cross_file_consistency(
    general: dict[str, Any],
    profiles: dict[str, Any],
    subscriptions: dict[str, Any],
    ytdl_sub_conf: dict[str, Any],
) -> None:
    profile_names = {profile["name"] for profile in profiles["profiles"]}
    default_profile = general["default_profile"]
    if default_profile not in profile_names:
        raise ContractValidationError(
            f"general.yaml.default_profile '{default_profile}' no existe en profiles.yaml"
        )

    for sub in subscriptions["subscriptions"]:
        if sub["profile"] not in profile_names:
            raise ContractValidationError(
                f"subscriptions.yaml.profile '{sub['profile']}' no existe en profiles.yaml"
            )

    profile_preset_map = ytdl_sub_conf["profile_preset_map"]
    for profile in profiles["profiles"]:
        quality_profile = profile["quality_profile"]
        if quality_profile not in profile_preset_map:
            raise ContractValidationError(
                "No existe mapeo de quality_profile "
                f"'{quality_profile}' en "
                "ytdl-sub-conf.yaml.profile_preset_map"
            )


def _require_keys(payload: dict[str, Any], scope: str, keys: tuple[str, ...]) -> None:
    missing = [key for key in keys if key not in payload]
    if missing:
        raise ContractValidationError(f"{scope}: faltan claves obligatorias: {', '.join(missing)}")


def _require_enum(payload: dict[str, Any], key: str, allowed: set[str], scope: str) -> None:
    value = payload.get(key)
    if value not in allowed:
        allowed_values = ", ".join(sorted(allowed))
        raise ContractValidationError(f"{scope}.{key} debe ser uno de: {allowed_values}")
