from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from src.config.config_loader import ParsedConfigBundle
from src.config.effective_resolution import EffectiveSubscriptionConfig, resolve_effective_configs
from src.config.yaml_contract import _parse_simple_yaml


class IntegrationContractError(ValueError):
    """Error de validación del contrato de integración con ytdl-sub."""


class CompatibilityPolicy(str, Enum):
    STRICT = "strict"
    LENIENT = "lenient"


class MissingFieldPolicy(str, Enum):
    REJECT = "reject"
    DROP = "drop"
    USE_DEFAULT = "use_default"


class MissingPresetPolicy(str, Enum):
    REJECT = "reject"
    USE_FALLBACK = "use_fallback"


class InvocationMode(str, Enum):
    SUB = "sub"
    DL = "dl"


@dataclass(frozen=True)
class TranslationRule:
    source_field: str
    value_mapping: dict[str, str | int | float | bool]
    default_value: str | int | float | bool | None
    required: bool


@dataclass(frozen=True)
class CompatibilityConfig:
    min_ytdl_sub_version: str
    max_ytdl_sub_version: str | None
    policy: CompatibilityPolicy


@dataclass(frozen=True)
class FallbackPolicy:
    on_missing_field: MissingFieldPolicy
    on_missing_preset: MissingPresetPolicy
    fallback_preset: str | None


@dataclass(frozen=True)
class ValidationConfig:
    strict_unknown_fields: bool
    abort_on_partial_translation: bool


@dataclass(frozen=True)
class InvocationConfig:
    binary: str
    mode: InvocationMode
    extra_args: tuple[str, ...]


@dataclass(frozen=True)
class YtdlSubIntegrationContract:
    integration_version: int
    preset_mapping: dict[str, str]
    field_mapping: dict[str, str]
    translation_rules: dict[str, TranslationRule]
    compatibility: CompatibilityConfig
    fallback_policy: FallbackPolicy
    validation: ValidationConfig
    invocation: InvocationConfig


@dataclass(frozen=True)
class TranslationIssue:
    reason_code: str
    message: str
    field: str | None = None

    def to_dict(self) -> dict[str, str]:
        payload = {"reason_code": self.reason_code, "message": self.message}
        if self.field:
            payload["field"] = self.field
        return payload


@dataclass(frozen=True)
class PreparedYtdlSubTranslation:
    subscription_id: str
    profile_id: str
    preset: str | None
    mapped_fields: dict[str, str | int | float | bool]
    invocation: dict[str, Any]
    issues: tuple[TranslationIssue, ...]
    translation_signature: str

    @property
    def is_valid(self) -> bool:
        return len(self.issues) == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "subscription_id": self.subscription_id,
            "profile_id": self.profile_id,
            "preset": self.preset,
            "mapped_fields": dict(self.mapped_fields),
            "invocation": dict(self.invocation),
            "issues": [issue.to_dict() for issue in self.issues],
            "is_valid": self.is_valid,
            "translation_signature": self.translation_signature,
        }


def load_integration_contract(config_dir: str | Path) -> YtdlSubIntegrationContract:
    path = Path(config_dir) / "ytdl-sub-conf.yaml"
    if not path.exists():
        raise IntegrationContractError("Falta ytdl-sub-conf.yaml para contrato de integración")
    payload = _parse_simple_yaml(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise IntegrationContractError("ytdl-sub-conf.yaml debe contener un objeto YAML")
    return parse_integration_contract(payload)


def parse_integration_contract(payload: dict[str, Any]) -> YtdlSubIntegrationContract:
    version = payload.get("integration_version")
    if isinstance(version, bool) or not isinstance(version, int) or version <= 0:
        raise IntegrationContractError("integration_version debe ser entero > 0")

    preset_mapping = _parse_string_map(payload.get("preset_mapping"), "preset_mapping")
    field_mapping = _parse_string_map(payload.get("field_mapping"), "field_mapping")
    if not field_mapping:
        raise IntegrationContractError("field_mapping no puede estar vacío")

    translation_rules_payload = payload.get("translation_rules", {})
    if translation_rules_payload is None:
        translation_rules_payload = {}
    if not isinstance(translation_rules_payload, dict):
        raise IntegrationContractError("translation_rules debe ser objeto")
    translation_rules: dict[str, TranslationRule] = {}
    for field, raw_rule in translation_rules_payload.items():
        if not isinstance(field, str) or not field.strip():
            raise IntegrationContractError("translation_rules contiene campo inválido")
        if not isinstance(raw_rule, dict):
            raise IntegrationContractError(f"translation_rules.{field} debe ser objeto")
        map_values = raw_rule.get("map_values", {})
        if map_values is None:
            map_values = {}
        if not isinstance(map_values, dict):
            raise IntegrationContractError(f"translation_rules.{field}.map_values debe ser objeto")
        normalized_mapping = {
            str(k): _coerce_scalar(v, f"translation_rules.{field}.map_values")
            for k, v in map_values.items()
        }
        translation_rules[field.strip()] = TranslationRule(
            source_field=field.strip(),
            value_mapping=normalized_mapping,
            default_value=_coerce_optional_scalar(
                raw_rule.get("default"),
                f"translation_rules.{field}.default",
            ),
            required=_coerce_bool(
                raw_rule.get("required", False),
                f"translation_rules.{field}.required",
            ),
        )

    compatibility_payload = payload.get("compatibility")
    if not isinstance(compatibility_payload, dict):
        raise IntegrationContractError("compatibility debe ser objeto")
    compatibility = CompatibilityConfig(
        min_ytdl_sub_version=_coerce_str(
            compatibility_payload.get("min_ytdl_sub_version"),
            "compatibility.min_ytdl_sub_version",
        ),
        max_ytdl_sub_version=_coerce_optional_str(
            compatibility_payload.get("max_ytdl_sub_version"),
            "compatibility.max_ytdl_sub_version",
        ),
        policy=CompatibilityPolicy(
            _coerce_enum(
                compatibility_payload.get("policy", CompatibilityPolicy.STRICT.value),
                {item.value for item in CompatibilityPolicy},
                "compatibility.policy",
            )
        ),
    )

    fallback_payload = payload.get("fallback_policy")
    if not isinstance(fallback_payload, dict):
        raise IntegrationContractError("fallback_policy debe ser objeto")
    fallback_policy = FallbackPolicy(
        on_missing_field=MissingFieldPolicy(
            _coerce_enum(
                fallback_payload.get("on_missing_field", MissingFieldPolicy.REJECT.value),
                {item.value for item in MissingFieldPolicy},
                "fallback_policy.on_missing_field",
            )
        ),
        on_missing_preset=MissingPresetPolicy(
            _coerce_enum(
                fallback_payload.get("on_missing_preset", MissingPresetPolicy.REJECT.value),
                {item.value for item in MissingPresetPolicy},
                "fallback_policy.on_missing_preset",
            )
        ),
        fallback_preset=_coerce_optional_str(
            fallback_payload.get("fallback_preset"),
            "fallback_policy.fallback_preset",
        ),
    )

    validation_payload = payload.get("validation")
    if not isinstance(validation_payload, dict):
        raise IntegrationContractError("validation debe ser objeto")
    validation = ValidationConfig(
        strict_unknown_fields=_coerce_bool(
            validation_payload.get("strict_unknown_fields", True),
            "validation.strict_unknown_fields",
        ),
        abort_on_partial_translation=_coerce_bool(
            validation_payload.get("abort_on_partial_translation", True),
            "validation.abort_on_partial_translation",
        ),
    )

    invocation_payload = payload.get("invocation")
    if not isinstance(invocation_payload, dict):
        raise IntegrationContractError("invocation debe ser objeto")
    extra_args_raw = invocation_payload.get("extra_args", [])
    if not isinstance(extra_args_raw, list):
        raise IntegrationContractError("invocation.extra_args debe ser lista")
    invocation = InvocationConfig(
        binary=_coerce_str(invocation_payload.get("binary", "ytdl-sub"), "invocation.binary"),
        mode=InvocationMode(
            _coerce_enum(
                invocation_payload.get("mode", InvocationMode.SUB.value),
                {item.value for item in InvocationMode},
                "invocation.mode",
            )
        ),
        extra_args=tuple(_coerce_str(item, "invocation.extra_args[]") for item in extra_args_raw),
    )

    return YtdlSubIntegrationContract(
        integration_version=version,
        preset_mapping=preset_mapping,
        field_mapping=field_mapping,
        translation_rules=translation_rules,
        compatibility=compatibility,
        fallback_policy=fallback_policy,
        validation=validation,
        invocation=invocation,
    )


def prepare_translation(
    contract: YtdlSubIntegrationContract,
    effective_config: EffectiveSubscriptionConfig,
) -> PreparedYtdlSubTranslation:
    issues: list[TranslationIssue] = []

    preset = _resolve_preset(contract, effective_config)
    if preset is None:
        issues.append(
            TranslationIssue(
                reason_code="PRESET_MAPPING_MISSING",
                message=(
                    f"No existe mapeo de preset para profile_id='{effective_config.profile_id}' "
                    "ni quality_profile='"
                    f"{effective_config.resolved_options.get('quality_profile')}'."
                ),
            )
        )

    mapped_fields: dict[str, str | int | float | bool] = {}
    for source_field in sorted(contract.field_mapping):
        target_field = contract.field_mapping[source_field]
        value = effective_config.resolved_options.get(source_field)
        rule = contract.translation_rules.get(source_field)

        if value is None:
            if rule and rule.required:
                if (
                    contract.fallback_policy.on_missing_field == MissingFieldPolicy.USE_DEFAULT
                    and rule.default_value is not None
                ):
                    mapped_fields[target_field] = rule.default_value
                elif contract.fallback_policy.on_missing_field == MissingFieldPolicy.DROP:
                    continue
                else:
                    issues.append(
                        TranslationIssue(
                            reason_code="MISSING_REQUIRED_FIELD",
                            field=source_field,
                            message=f"Campo requerido sin valor traducible: {source_field}",
                        )
                    )
            continue

        mapped_fields[target_field] = _apply_translation_rule(value, source_field, rule, issues)

    if contract.validation.strict_unknown_fields:
        known_fields = set(contract.field_mapping)
        for source_field in sorted(effective_config.resolved_options):
            if source_field in known_fields:
                continue
            issues.append(
                TranslationIssue(
                    reason_code="UNSUPPORTED_FIELD",
                    field=source_field,
                    message=f"Campo no soportado por field_mapping: {source_field}",
                )
            )

    if contract.validation.abort_on_partial_translation and issues:
        mapped_fields = {}

    invocation = {
        "binary": contract.invocation.binary,
        "mode": contract.invocation.mode.value,
        "extra_args": list(contract.invocation.extra_args),
    }

    payload = {
        "subscription_id": effective_config.subscription_id,
        "profile_id": effective_config.profile_id,
        "preset": preset,
        "mapped_fields": mapped_fields,
        "invocation": invocation,
        "issues": [item.to_dict() for item in issues],
        "integration_version": contract.integration_version,
    }
    signature = hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()

    return PreparedYtdlSubTranslation(
        subscription_id=effective_config.subscription_id,
        profile_id=effective_config.profile_id,
        preset=preset,
        mapped_fields=mapped_fields,
        invocation=invocation,
        issues=tuple(issues),
        translation_signature=signature,
    )


def prepare_translation_batch(
    contract: YtdlSubIntegrationContract,
    effective_configs: tuple[EffectiveSubscriptionConfig, ...],
) -> tuple[PreparedYtdlSubTranslation, ...]:
    prepared = tuple(prepare_translation(contract, item) for item in effective_configs)
    return tuple(sorted(prepared, key=lambda item: item.subscription_id))


def prepare_translation_batch_from_bundle(
    bundle: ParsedConfigBundle,
) -> tuple[PreparedYtdlSubTranslation, ...]:
    contract = parse_integration_contract(bundle.raw_documents["ytdl-sub-conf.yaml"])
    effective_configs = resolve_effective_configs(bundle)
    return prepare_translation_batch(contract, effective_configs)


def _resolve_preset(
    contract: YtdlSubIntegrationContract,
    effective_config: EffectiveSubscriptionConfig,
) -> str | None:
    by_profile = contract.preset_mapping.get(effective_config.profile_id)
    if by_profile:
        return by_profile

    quality_profile = effective_config.resolved_options.get("quality_profile")
    if isinstance(quality_profile, str):
        mapped = contract.preset_mapping.get(quality_profile)
        if mapped:
            return mapped

    if contract.fallback_policy.on_missing_preset == MissingPresetPolicy.USE_FALLBACK:
        return contract.fallback_policy.fallback_preset
    return None


def _apply_translation_rule(
    value: str | int | float | bool,
    source_field: str,
    rule: TranslationRule | None,
    issues: list[TranslationIssue],
) -> str | int | float | bool:
    if rule is None:
        return value

    mapped = rule.value_mapping.get(str(value))
    if mapped is not None:
        return mapped
    if rule.default_value is not None:
        return rule.default_value

    if rule.required:
        issues.append(
            TranslationIssue(
                reason_code="TRANSLATION_RULE_UNMAPPED_VALUE",
                field=source_field,
                message=f"Valor '{value}' sin map_values en translation_rules.{source_field}",
            )
        )
    return value


def _parse_string_map(value: Any, scope: str) -> dict[str, str]:
    if not isinstance(value, dict):
        raise IntegrationContractError(f"{scope} debe ser objeto")
    result: dict[str, str] = {}
    for key, item in value.items():
        result[_coerce_str(key, f"{scope}.key")] = _coerce_str(item, f"{scope}.{key}")
    return result


def _coerce_str(value: Any, scope: str) -> str:
    if not isinstance(value, str):
        raise IntegrationContractError(f"{scope} debe ser string")
    normalized = value.strip()
    if not normalized:
        raise IntegrationContractError(f"{scope} no puede estar vacío")
    return normalized


def _coerce_optional_str(value: Any, scope: str) -> str | None:
    if value is None:
        return None
    return _coerce_str(value, scope)


def _coerce_enum(value: Any, allowed: set[str], scope: str) -> str:
    normalized = _coerce_str(value, scope)
    if normalized not in allowed:
        raise IntegrationContractError(
            f"{scope} debe ser uno de: {', '.join(sorted(allowed))}"
        )
    return normalized


def _coerce_bool(value: Any, scope: str) -> bool:
    if not isinstance(value, bool):
        raise IntegrationContractError(f"{scope} debe ser booleano")
    return value


def _coerce_scalar(value: Any, scope: str) -> str | int | float | bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value
    if isinstance(value, str):
        if not value.strip():
            raise IntegrationContractError(f"{scope} contiene string vacío")
        return value
    raise IntegrationContractError(f"{scope} contiene valor no escalar soportado")


def _coerce_optional_scalar(value: Any, scope: str) -> str | int | float | bool | None:
    if value is None:
        return None
    return _coerce_scalar(value, scope)
