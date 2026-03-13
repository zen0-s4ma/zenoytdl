from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any

from src.config.config_loader import ParsedConfigBundle


class EffectiveResolutionError(ValueError):
    """Error al resolver configuración efectiva."""


@dataclass(frozen=True)
class OverrideDecision:
    field: str
    policy: str
    accepted: bool
    value: str | int | float | bool
    reason_code: str
    reason_message: str
    requested_origin: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "policy": self.policy,
            "accepted": self.accepted,
            "value": self.value,
            "reason_code": self.reason_code,
            "reason_message": self.reason_message,
            "requested_origin": self.requested_origin,
        }


@dataclass(frozen=True)
class EffectiveSubscriptionConfig:
    subscription_id: str
    profile_id: str
    resolved_options: dict[str, str | int | float | bool]
    value_origins: dict[str, str]
    override_decisions: tuple[OverrideDecision, ...]
    effective_signature: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "subscription_id": self.subscription_id,
            "profile_id": self.profile_id,
            "resolved_options": dict(self.resolved_options),
            "value_origins": dict(self.value_origins),
            "override_decisions": [item.to_dict() for item in self.override_decisions],
            "effective_signature": self.effective_signature,
        }


GENERAL_DEFAULTS: dict[str, str | int | float | bool] = {
    "timezone": "UTC",
}

LOCAL_OVERRIDE_KEYS = (
    "quality_profile",
    "media_type",
    "audio_language",
    "video_container",
    "max_duration_seconds",
)


class OverridePolicy(str, Enum):
    ALLOWED = "allowed"
    RESTRICTED = "restricted"
    FORBIDDEN = "forbidden"


@dataclass(frozen=True)
class OverrideRule:
    policy: OverridePolicy
    allowed_values: tuple[str | int | float | bool, ...] = ()
    min_value: int | float | None = None
    max_value: int | float | None = None
    non_empty_string: bool = False


_DEFAULT_RULE = OverrideRule(policy=OverridePolicy.ALLOWED)
_FIELD_TYPE_RULES: dict[str, type[Any]] = {
    "quality_profile": str,
    "media_type": str,
    "audio_language": str,
    "video_container": str,
    "max_duration_seconds": int,
}


def resolve_effective_configs(
    bundle: ParsedConfigBundle,
) -> tuple[EffectiveSubscriptionConfig, ...]:
    profiles_by_name = {profile.name: profile for profile in bundle.profiles}
    raw_profiles = bundle.raw_documents.get("profiles.yaml", {}).get("profiles", [])
    profile_rules = _build_profile_rules(raw_profiles)
    raw_subscriptions = bundle.raw_documents.get("subscriptions.yaml", {}).get("subscriptions", [])

    results: list[EffectiveSubscriptionConfig] = []
    for index, subscription in enumerate(bundle.subscriptions):
        profile = profiles_by_name.get(subscription.profile)
        if profile is None:
            raise EffectiveResolutionError(
                f"No se puede resolver suscripción '{subscription.name}': perfil inexistente"
            )

        raw_sub = raw_subscriptions[index] if index < len(raw_subscriptions) else {}
        if not isinstance(raw_sub, dict):
            raw_sub = {}

        resolved: dict[str, str | int | float | bool] = {}
        origins: dict[str, str] = {}

        _merge_layer(resolved, origins, GENERAL_DEFAULTS, "defaults.general")
        _merge_layer(
            resolved,
            origins,
            {
                "workspace": str(bundle.general.workspace),
                "library_dir": str(bundle.general.library_dir),
                "environment": bundle.general.environment,
                "log_level": bundle.general.log_level.upper(),
                "dry_run": bundle.general.dry_run,
                "default_profile": bundle.general.default_profile,
            },
            "general.yaml",
        )
        _merge_layer(
            resolved,
            origins,
            {
                "media_type": profile.media_type,
                "quality_profile": profile.quality_profile,
                "profile_name": profile.name,
            },
            f"profiles.yaml:{profile.name}",
        )

        raw_override_values = _extract_raw_overrides(raw_sub, subscription.name)
        local_override_values, local_override_origins, decisions = _evaluate_overrides(
            profile_rules=profile_rules.get(profile.name, {}),
            raw_overrides=raw_override_values,
        )
        for key in sorted(local_override_values):
            resolved[key] = local_override_values[key]
            origins[key] = local_override_origins[key]

        sources_canonical = tuple(sorted({source.strip() for source in subscription.sources}))
        _merge_layer(
            resolved,
            origins,
            {
                "enabled": subscription.enabled,
                "schedule_mode": subscription.schedule.mode,
                "schedule_every_hours": subscription.schedule.every_hours or 0,
                "source_kind": _detect_source_kind(sources_canonical),
                "primary_source": sources_canonical[0],
                "source_count": len(sources_canonical),
                "sources_signature": _hash_payload({"sources": sources_canonical}),
            },
            f"subscriptions.yaml:{subscription.name}",
        )

        normalized_options = _normalize_payload(resolved)
        normalized_origins = {key: origins[key] for key in sorted(origins)}
        signature_payload = {
            "subscription_id": subscription.name,
            "profile_id": profile.name,
            "resolved_options": normalized_options,
            "override_decisions": [item.to_dict() for item in decisions],
        }

        results.append(
            EffectiveSubscriptionConfig(
                subscription_id=subscription.name,
                profile_id=profile.name,
                resolved_options=normalized_options,
                value_origins=normalized_origins,
                override_decisions=decisions,
                effective_signature=_hash_payload(signature_payload),
            )
        )

    return tuple(sorted(results, key=lambda item: item.subscription_id))


def resolve_effective_config_for_subscription(
    bundle: ParsedConfigBundle, subscription_id: str
) -> EffectiveSubscriptionConfig:
    normalized_id = subscription_id.strip().lower()
    for item in resolve_effective_configs(bundle):
        if item.subscription_id.lower() == normalized_id:
            return item
    raise EffectiveResolutionError(f"Suscripción no encontrada: {subscription_id}")


def serialize_effective_configs(
    configs: tuple[EffectiveSubscriptionConfig, ...],
) -> dict[str, Any]:
    return {
        "effective_configs": [config.to_dict() for config in configs],
        "batch_signature": _hash_payload([config.to_dict() for config in configs]),
    }


def _merge_layer(
    base: dict[str, str | int | float | bool],
    origins: dict[str, str],
    layer: dict[str, str | int | float | bool],
    origin: str,
) -> None:
    for key in sorted(layer):
        base[key] = layer[key]
        origins[key] = origin


def _normalize_scalar(value: Any) -> str | int | float | bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value
    if isinstance(value, str):
        normalized = " ".join(value.strip().split())
        return normalized
    raise EffectiveResolutionError(f"Valor no soportado para resolución efectiva: {value!r}")


def _normalize_payload(payload: dict[str, Any]) -> dict[str, str | int | float | bool]:
    normalized = {key.strip().lower(): _normalize_scalar(payload[key]) for key in sorted(payload)}
    return normalized


def _hash_payload(payload: Any) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _detect_source_kind(sources: tuple[str, ...]) -> str:
    first = sources[0]
    if "playlist" in first:
        return "playlist"
    if first.startswith("ytsearch") or first.startswith("search:"):
        return "search"
    return "channel"


def _build_profile_rules(raw_profiles: Any) -> dict[str, dict[str, OverrideRule]]:
    rules: dict[str, dict[str, OverrideRule]] = {}
    if not isinstance(raw_profiles, list):
        return rules
    for item in raw_profiles:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        policy_payload = item.get("override_policies", {})
        if policy_payload is None:
            policy_payload = {}
        if not isinstance(policy_payload, dict):
            raise EffectiveResolutionError(
                f"Perfil '{name}' define override_policies inválido; debe ser objeto"
            )
        parsed_rules: dict[str, OverrideRule] = {}
        for field, raw_rule in policy_payload.items():
            if not isinstance(field, str) or field.strip() not in _FIELD_TYPE_RULES:
                raise EffectiveResolutionError(
                    f"Perfil '{name}' define política de override inválida para campo '{field}'"
                )
            parsed_rules[field.strip()] = _parse_override_rule(name, field.strip(), raw_rule)
        rules[name.strip()] = parsed_rules
    return rules


def _parse_override_rule(profile_name: str, field: str, payload: Any) -> OverrideRule:
    if isinstance(payload, str):
        policy = _coerce_policy(profile_name, field, payload)
        return OverrideRule(policy=policy)
    if not isinstance(payload, dict):
        raise EffectiveResolutionError(
            (
                f"Perfil '{profile_name}' define regla inválida para '{field}': "
                "debe ser string u objeto"
            )
        )

    policy = _coerce_policy(profile_name, field, payload.get("policy", "restricted"))
    allowed_values_raw = payload.get("allowed_values", [])
    allowed_values: tuple[str | int | float | bool, ...] = ()
    if allowed_values_raw:
        if not isinstance(allowed_values_raw, list):
            raise EffectiveResolutionError(
                f"Perfil '{profile_name}' define allowed_values inválido para '{field}'"
            )
        allowed_values = tuple(_normalize_scalar(item) for item in allowed_values_raw)

    min_value = payload.get("min_value")
    max_value = payload.get("max_value")
    non_empty_string = payload.get("non_empty_string", False)

    if min_value is not None and (
        isinstance(min_value, bool) or not isinstance(min_value, (int, float))
    ):
        raise EffectiveResolutionError(
            f"Perfil '{profile_name}' define min_value inválido para '{field}'"
        )
    if max_value is not None and (
        isinstance(max_value, bool) or not isinstance(max_value, (int, float))
    ):
        raise EffectiveResolutionError(
            f"Perfil '{profile_name}' define max_value inválido para '{field}'"
        )
    if not isinstance(non_empty_string, bool):
        raise EffectiveResolutionError(
            f"Perfil '{profile_name}' define non_empty_string inválido para '{field}'"
        )

    return OverrideRule(
        policy=policy,
        allowed_values=allowed_values,
        min_value=min_value,
        max_value=max_value,
        non_empty_string=non_empty_string,
    )


def _coerce_policy(profile_name: str, field: str, raw_policy: Any) -> OverridePolicy:
    if not isinstance(raw_policy, str):
        raise EffectiveResolutionError(
            f"Perfil '{profile_name}' define policy inválida para '{field}'"
        )
    normalized = raw_policy.strip().lower()
    try:
        return OverridePolicy(normalized)
    except ValueError as exc:
        raise EffectiveResolutionError(
            f"Perfil '{profile_name}' usa policy desconocida '{raw_policy}' para '{field}'"
        ) from exc


def _extract_raw_overrides(
    raw_sub: dict[str, Any], subscription_name: str
) -> dict[str, tuple[Any, str]]:
    values: dict[str, tuple[Any, str]] = {}
    raw_nested = raw_sub.get("overrides", {})
    if raw_nested is None:
        raw_nested = {}
    if not isinstance(raw_nested, dict):
        raise EffectiveResolutionError(
            f"Suscripción '{subscription_name}' define overrides inválido; debe ser objeto"
        )
    for field, value in raw_nested.items():
        if not isinstance(field, str):
            raise EffectiveResolutionError(
                f"Suscripción '{subscription_name}' define override con campo no string"
            )
        values[field.strip()] = (value, f"subscriptions.yaml:{subscription_name}:overrides")

    for key in LOCAL_OVERRIDE_KEYS:
        if key in raw_sub and key not in values:
            values[key] = (raw_sub[key], f"subscriptions.yaml:{subscription_name}:local")
    return values


def _evaluate_overrides(
    profile_rules: dict[str, OverrideRule],
    raw_overrides: dict[str, tuple[Any, str]],
) -> tuple[
    dict[str, str | int | float | bool],
    dict[str, str],
    tuple[OverrideDecision, ...],
]:
    accepted: dict[str, str | int | float | bool] = {}
    accepted_origins: dict[str, str] = {}
    decisions: list[OverrideDecision] = []
    for field in sorted(raw_overrides):
        raw_value, requested_origin = raw_overrides[field]
        if field not in _FIELD_TYPE_RULES:
            decisions.append(
                OverrideDecision(
                    field=field,
                    policy="forbidden",
                    accepted=False,
                    value=_safe_decision_value(raw_value),
                    reason_code="OVERRIDE_FIELD_NOT_SUPPORTED",
                    reason_message="El campo no soporta overrides en Hito 7.",
                    requested_origin=requested_origin,
                )
            )
            continue

        try:
            normalized_value = _normalize_scalar(raw_value)
        except EffectiveResolutionError:
            decisions.append(
                OverrideDecision(
                    field=field,
                    policy="forbidden",
                    accepted=False,
                    value=_safe_decision_value(raw_value),
                    reason_code="OVERRIDE_VALUE_NOT_SCALAR",
                    reason_message="El override debe ser escalar (string/int/float/bool).",
                    requested_origin=requested_origin,
                )
            )
            continue

        type_error = _type_rejection(field, normalized_value)
        if type_error is not None:
            decisions.append(
                OverrideDecision(
                    field=field,
                    policy="forbidden",
                    accepted=False,
                    value=normalized_value,
                    reason_code="OVERRIDE_TYPE_MISMATCH",
                    reason_message=type_error,
                    requested_origin=requested_origin,
                )
            )
            continue

        rule = profile_rules.get(field, _DEFAULT_RULE)
        accepted_flag, reason_code, reason_message = _apply_rule(field, normalized_value, rule)
        decisions.append(
            OverrideDecision(
                field=field,
                policy=rule.policy.value,
                accepted=accepted_flag,
                value=normalized_value,
                reason_code=reason_code,
                reason_message=reason_message,
                requested_origin=requested_origin,
            )
        )
        if accepted_flag:
            accepted[field] = normalized_value
            accepted_origins[field] = requested_origin

    return accepted, accepted_origins, tuple(decisions)


def _type_rejection(field: str, value: str | int | float | bool) -> str | None:
    expected = _FIELD_TYPE_RULES[field]
    if expected is int and isinstance(value, bool):
        return f"{field} requiere tipo int y no bool"
    if not isinstance(value, expected):
        return f"{field} requiere tipo {expected.__name__}"
    return None


def _apply_rule(
    field: str,
    value: str | int | float | bool,
    rule: OverrideRule,
) -> tuple[bool, str, str]:
    if rule.policy is OverridePolicy.FORBIDDEN:
        return False, "OVERRIDE_POLICY_FORBIDDEN", "El perfil bloquea override para este campo."

    if rule.policy is OverridePolicy.ALLOWED:
        return True, "OVERRIDE_ACCEPTED", "Override permitido por política allowed."

    if rule.non_empty_string and isinstance(value, str) and not value.strip():
        return (
            False,
            "OVERRIDE_RESTRICTED_EMPTY_STRING",
            "El campo requiere string no vacío por política restricted.",
        )
    if rule.allowed_values and value not in rule.allowed_values:
        return (
            False,
            "OVERRIDE_RESTRICTED_DISALLOWED_VALUE",
            "El valor no pertenece a allowed_values del perfil.",
        )
    if isinstance(value, (int, float)):
        if rule.min_value is not None and value < rule.min_value:
            return (
                False,
                "OVERRIDE_RESTRICTED_MIN_VALUE",
                f"El valor es menor que min_value={rule.min_value}.",
            )
        if rule.max_value is not None and value > rule.max_value:
            return (
                False,
                "OVERRIDE_RESTRICTED_MAX_VALUE",
                f"El valor excede max_value={rule.max_value}.",
            )
    return True, "OVERRIDE_ACCEPTED", "Override permitido por política restricted."


def _safe_decision_value(value: Any) -> str | int | float | bool:
    if isinstance(value, (str, int, float, bool)):
        return _normalize_scalar(value)
    return json.dumps(value, sort_keys=True, ensure_ascii=False)
