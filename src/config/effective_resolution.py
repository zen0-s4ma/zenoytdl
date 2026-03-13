from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from src.config.config_loader import ParsedConfigBundle


class EffectiveResolutionError(ValueError):
    """Error al resolver configuración efectiva."""


@dataclass(frozen=True)
class EffectiveSubscriptionConfig:
    subscription_id: str
    profile_id: str
    resolved_options: dict[str, str | int | float | bool]
    value_origins: dict[str, str]
    effective_signature: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "subscription_id": self.subscription_id,
            "profile_id": self.profile_id,
            "resolved_options": dict(self.resolved_options),
            "value_origins": dict(self.value_origins),
            "effective_signature": self.effective_signature,
        }


GENERAL_DEFAULTS: dict[str, str | int | float | bool] = {
    "timezone": "UTC",
}

LOCAL_OVERRIDE_KEYS = (
    "media_type",
    "audio_language",
    "video_container",
    "max_duration_seconds",
)


def resolve_effective_configs(
    bundle: ParsedConfigBundle,
) -> tuple[EffectiveSubscriptionConfig, ...]:
    profiles_by_name = {profile.name: profile for profile in bundle.profiles}
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

        local_override_values = {
            key: _normalize_scalar(raw_sub[key]) for key in LOCAL_OVERRIDE_KEYS if key in raw_sub
        }
        _merge_layer(
            resolved,
            origins,
            local_override_values,
            f"subscriptions.yaml:{subscription.name}:local",
        )

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
        }

        results.append(
            EffectiveSubscriptionConfig(
                subscription_id=subscription.name,
                profile_id=profile.name,
                resolved_options=normalized_options,
                value_origins=normalized_origins,
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
