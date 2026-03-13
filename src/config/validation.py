from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from src.config.config_loader import ParsedConfigBundle, load_parsed_config_bundle
from src.config.yaml_contract import REQUIRED_YAML_FILES

Severity = Literal["error", "warning"]

_ALLOWED_PROFILE_KEYS = {
    "name",
    "media_type",
    "quality_profile",
    "element_type",
    "x-meta",
    "override_policies",
}
_ALLOWED_SUBSCRIPTION_KEYS = {
    "name",
    "profile",
    "sources",
    "enabled",
    "schedule",
    "element_type",
    "media_type",
    "audio_language",
    "video_container",
    "max_duration_seconds",
    "x-meta",
    "overrides",
}
_ALLOWED_MEDIA_TYPES = {"audio", "video", "shorts"}


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    path: str
    message: str
    severity: Severity = "error"

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "path": self.path,
            "message": self.message,
            "severity": self.severity,
        }


@dataclass(frozen=True)
class ValidationReport:
    config_signature: str
    issue_fingerprint: str
    issues: tuple[ValidationIssue, ...]

    @property
    def ok(self) -> bool:
        return len(self.issues) == 0

    @property
    def error_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "error")

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "config_signature": self.config_signature,
            "issue_fingerprint": self.issue_fingerprint,
            "error_count": self.error_count,
            "issues": [issue.to_dict() for issue in self.issues],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, ensure_ascii=False)


class SemanticValidationError(ValueError):
    """Configuración inválida en validación estructural/semántica (Hito 5)."""

    def __init__(self, report: ValidationReport):
        self.report = report
        super().__init__(
            f"Validación semántica fallida ({report.error_count} errores). "
            f"fingerprint={report.issue_fingerprint}"
        )


def validate_config_dir(config_dir: str | Path) -> ValidationReport:
    bundle = load_parsed_config_bundle(config_dir)
    return validate_parsed_config_bundle(bundle)


def validate_parsed_config_bundle(bundle: ParsedConfigBundle) -> ValidationReport:
    issues: list[ValidationIssue] = []

    _validate_required_files(bundle, issues)
    _validate_profiles(bundle, issues)
    _validate_subscriptions(bundle, issues)
    _validate_cross_references(bundle, issues)

    fingerprint = _build_issue_fingerprint(issues)
    return ValidationReport(
        config_signature=bundle.signature,
        issue_fingerprint=fingerprint,
        issues=tuple(issues),
    )


def ensure_semantic_valid(bundle: ParsedConfigBundle) -> ValidationReport:
    report = validate_parsed_config_bundle(bundle)
    if not report.ok:
        raise SemanticValidationError(report)
    return report


def _validate_required_files(bundle: ParsedConfigBundle, issues: list[ValidationIssue]) -> None:
    for file_name in REQUIRED_YAML_FILES:
        file_path = bundle.file_paths.get(file_name)
        if file_path is None or not file_path.exists():
            issues.append(
                ValidationIssue(
                    code="CFG_REQUIRED_FILE_MISSING",
                    path=file_name,
                    message=f"Falta archivo obligatorio: {file_name}",
                )
            )


def _validate_profiles(bundle: ParsedConfigBundle, issues: list[ValidationIssue]) -> None:
    raw_profiles = bundle.raw_documents.get("profiles.yaml", {}).get("profiles", [])
    seen_names: set[str] = set()

    for index, profile in enumerate(bundle.profiles):
        if profile.name in seen_names:
            issues.append(
                ValidationIssue(
                    code="PROFILE_DUPLICATED",
                    path=f"profiles.yaml.profiles[{index}].name",
                    message=f"El perfil '{profile.name}' está duplicado.",
                )
            )
        seen_names.add(profile.name)

        if profile.media_type not in _ALLOWED_MEDIA_TYPES:
            issues.append(
                ValidationIssue(
                    code="PROFILE_MEDIA_TYPE_INVALID",
                    path=f"profiles.yaml.profiles[{index}].media_type",
                    message=(
                        "media_type inválido; valores permitidos: "
                        f"{', '.join(sorted(_ALLOWED_MEDIA_TYPES))}"
                    ),
                )
            )

        raw_profile = {}
        if index < len(raw_profiles) and isinstance(raw_profiles[index], dict):
            raw_profile = raw_profiles[index]
        _validate_element_type(
            payload=raw_profile,
            expected="profile",
            path=f"profiles.yaml.profiles[{index}].element_type",
            issues=issues,
        )
        _validate_extensibility_keys(
            payload=raw_profile,
            allowed=_ALLOWED_PROFILE_KEYS,
            path=f"profiles.yaml.profiles[{index}]",
            issues=issues,
        )


def _validate_subscriptions(bundle: ParsedConfigBundle, issues: list[ValidationIssue]) -> None:
    raw_subscriptions = bundle.raw_documents.get("subscriptions.yaml", {}).get("subscriptions", [])

    for index, subscription in enumerate(bundle.subscriptions):
        raw_sub = (
            raw_subscriptions[index]
            if index < len(raw_subscriptions) and isinstance(raw_subscriptions[index], dict)
            else {}
        )

        _validate_element_type(
            payload=raw_sub,
            expected="subscription",
            path=f"subscriptions.yaml.subscriptions[{index}].element_type",
            issues=issues,
        )
        _validate_extensibility_keys(
            payload=raw_sub,
            allowed=_ALLOWED_SUBSCRIPTION_KEYS,
            path=f"subscriptions.yaml.subscriptions[{index}]",
            issues=issues,
        )

        if subscription.schedule.mode == "interval" and (
            subscription.schedule.every_hours is None or subscription.schedule.every_hours <= 0
        ):
            issues.append(
                ValidationIssue(
                    code="SUBSCRIPTION_INTERVAL_INVALID",
                    path=f"subscriptions.yaml.subscriptions[{index}].schedule.every_hours",
                    message="every_hours debe ser entero > 0 cuando schedule.mode=interval",
                )
            )

        source_kinds = {_classify_source(item) for item in subscription.sources}
        if len(source_kinds) > 1:
            issues.append(
                ValidationIssue(
                    code="SUBSCRIPTION_SOURCE_KIND_MIXED",
                    path=f"subscriptions.yaml.subscriptions[{index}].sources",
                    message="No mezclar canales, playlists y búsquedas en la misma suscripción.",
                )
            )

        declared_media_type = raw_sub.get("media_type")
        if declared_media_type is not None and declared_media_type not in _ALLOWED_MEDIA_TYPES:
            issues.append(
                ValidationIssue(
                    code="SUBSCRIPTION_MEDIA_TYPE_INVALID",
                    path=f"subscriptions.yaml.subscriptions[{index}].media_type",
                    message=(
                        "media_type inválido en suscripción; valores permitidos: "
                        f"{', '.join(sorted(_ALLOWED_MEDIA_TYPES))}"
                    ),
                )
            )

        if declared_media_type == "audio" and not _is_non_empty_string(
            raw_sub.get("audio_language")
        ):
            issues.append(
                ValidationIssue(
                    code="SUBSCRIPTION_AUDIO_LANGUAGE_REQUIRED",
                    path=f"subscriptions.yaml.subscriptions[{index}].audio_language",
                    message="audio_language es obligatorio cuando media_type=audio.",
                )
            )

        if declared_media_type == "video" and not _is_non_empty_string(
            raw_sub.get("video_container")
        ):
            issues.append(
                ValidationIssue(
                    code="SUBSCRIPTION_VIDEO_CONTAINER_REQUIRED",
                    path=f"subscriptions.yaml.subscriptions[{index}].video_container",
                    message="video_container es obligatorio cuando media_type=video.",
                )
            )

        if declared_media_type == "shorts":
            max_duration = raw_sub.get("max_duration_seconds")
            if (
                isinstance(max_duration, bool)
                or not isinstance(max_duration, int)
                or max_duration <= 0
            ):
                issues.append(
                    ValidationIssue(
                        code="SUBSCRIPTION_SHORTS_DURATION_REQUIRED",
                        path=f"subscriptions.yaml.subscriptions[{index}].max_duration_seconds",
                        message=(
                            "max_duration_seconds debe ser entero > 0 "
                            "cuando media_type=shorts."
                        ),
                    )
                )


def _validate_cross_references(bundle: ParsedConfigBundle, issues: list[ValidationIssue]) -> None:
    profile_by_name = {profile.name: profile for profile in bundle.profiles}

    if bundle.general.default_profile not in profile_by_name:
        issues.append(
            ValidationIssue(
                code="GENERAL_DEFAULT_PROFILE_UNKNOWN",
                path="general.yaml.default_profile",
                message=(
                    f"default_profile '{bundle.general.default_profile}' no existe en profiles.yaml"
                ),
            )
        )

    for index, subscription in enumerate(bundle.subscriptions):
        profile = profile_by_name.get(subscription.profile)
        if profile is None:
            issues.append(
                ValidationIssue(
                    code="SUBSCRIPTION_PROFILE_UNKNOWN",
                    path=f"subscriptions.yaml.subscriptions[{index}].profile",
                    message=(
                        f"La suscripción '{subscription.name}' referencia perfil inexistente "
                        f"'{subscription.profile}'."
                    ),
                )
            )
            continue

        raw_subscriptions = bundle.raw_documents.get("subscriptions.yaml", {}).get(
            "subscriptions", []
        )
        raw_sub = (
            raw_subscriptions[index]
            if index < len(raw_subscriptions) and isinstance(raw_subscriptions[index], dict)
            else {}
        )
        declared_media_type = raw_sub.get("media_type")
        if declared_media_type is not None and declared_media_type != profile.media_type:
            issues.append(
                ValidationIssue(
                    code="SUBSCRIPTION_MEDIA_TYPE_MISMATCH",
                    path=f"subscriptions.yaml.subscriptions[{index}].media_type",
                    message=(
                        "media_type de suscripción no coincide con media_type del perfil "
                        f"'{profile.name}' ({profile.media_type})."
                    ),
                )
            )

    available_presets = set(bundle.ytdl_sub_conf.profile_preset_map)
    for index, profile in enumerate(bundle.profiles):
        if profile.quality_profile not in available_presets:
            issues.append(
                ValidationIssue(
                    code="PROFILE_QUALITY_PROFILE_UNMAPPED",
                    path=f"profiles.yaml.profiles[{index}].quality_profile",
                    message=(
                        f"quality_profile '{profile.quality_profile}' sin mapeo en "
                        "ytdl-sub-conf.yaml.profile_preset_map"
                    ),
                )
            )


def _validate_element_type(
    payload: dict[str, Any],
    expected: str,
    path: str,
    issues: list[ValidationIssue],
) -> None:
    value = payload.get("element_type")
    if value != expected:
        issues.append(
            ValidationIssue(
                code="ELEMENT_TYPE_INVALID",
                path=path,
                message=f"element_type debe ser '{expected}'.",
            )
        )


def _validate_extensibility_keys(
    payload: dict[str, Any],
    allowed: set[str],
    path: str,
    issues: list[ValidationIssue],
) -> None:
    for key in payload:
        if key not in allowed and not key.startswith("x-"):
            issues.append(
                ValidationIssue(
                    code="EXTENSION_KEY_NOT_ALLOWED",
                    path=f"{path}.{key}",
                    message=(
                        f"Clave '{key}' no permitida. Usa prefijo 'x-' para extensiones "
                        "controladas."
                    ),
                )
            )


def _build_issue_fingerprint(issues: list[ValidationIssue]) -> str:
    canonical = json.dumps(
        [issue.to_dict() for issue in issues],
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _classify_source(source: str) -> str:
    lowered = source.lower()
    if "playlist" in lowered:
        return "playlist"
    if lowered.startswith("search:") or lowered.startswith("ytsearch"):
        return "search"
    return "channel"


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())
