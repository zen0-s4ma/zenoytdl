from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from src.config.config_loader import ParsedConfigBundle
from src.config.effective_resolution import EffectiveSubscriptionConfig, resolve_effective_configs
from src.integration.ytdl_sub.contract import (
    MissingPresetPolicy,
    PreparedYtdlSubTranslation,
    TranslationIssue,
    YtdlSubIntegrationContract,
    parse_integration_contract,
    prepare_translation,
)


@dataclass(frozen=True)
class TranslatedYtdlSubModel:
    subscription_id: str
    profile_id: str
    preset_base: str | None
    preset_bridge: str | None
    ytdl_sub_model: dict[str, Any]
    issues: tuple[TranslationIssue, ...]
    prepared_translation: PreparedYtdlSubTranslation
    translation_signature: str

    @property
    def is_valid(self) -> bool:
        return len(self.issues) == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "subscription_id": self.subscription_id,
            "profile_id": self.profile_id,
            "preset_base": self.preset_base,
            "preset_bridge": self.preset_bridge,
            "ytdl_sub_model": json.loads(
                json.dumps(self.ytdl_sub_model, sort_keys=True, ensure_ascii=False)
            ),
            "issues": [item.to_dict() for item in self.issues],
            "is_valid": self.is_valid,
            "prepared_translation": self.prepared_translation.to_dict(),
            "translation_signature": self.translation_signature,
        }


def translate_effective_config_to_ytdl_sub_model(
    contract: YtdlSubIntegrationContract,
    effective_config: EffectiveSubscriptionConfig,
) -> TranslatedYtdlSubModel:
    prepared = prepare_translation(contract, effective_config)
    issues = list(prepared.issues)

    preset_base, preset_bridge, preset_issues = _resolve_base_and_bridge_preset(
        contract, effective_config
    )
    issues.extend(preset_issues)

    translated_fields: dict[str, str | int | float | bool] = {}
    internal_only_fields: list[str] = []

    for source_field in sorted(contract.field_mapping):
        target_field = contract.field_mapping[source_field]
        rule = contract.translation_rules.get(source_field)

        value = prepared.mapped_fields.get(target_field)
        if value is None:
            continue

        if rule and rule.internal_only:
            internal_only_fields.append(target_field)
            continue

        translated_fields[target_field] = value

    if prepared.is_valid is False:
        issues.append(
            TranslationIssue(
                reason_code="TRANSLATION_PARTIAL_OR_REJECTED",
                message=(
                    "La traducción preparada del Hito 9 no es válida para "
                    "materializar modelo Hito 10."
                ),
            )
        )

    ytdl_sub_model = {
        "integration_version": contract.integration_version,
        "subscription": {
            "id": effective_config.subscription_id,
            "profile": effective_config.profile_id,
            "preset": preset_base,
            "preset_bridge": preset_bridge,
            "options": {key: translated_fields[key] for key in sorted(translated_fields)},
            "invocation": dict(prepared.invocation),
        },
        "meta": {
            "effective_signature": effective_config.effective_signature,
            "prepared_translation_signature": prepared.translation_signature,
            "internal_only_excluded": sorted(internal_only_fields),
            "translation_stage": "hito10_ytdl_sub_model",
        },
    }

    if issues:
        ytdl_sub_model = {}

    payload = {
        "subscription_id": effective_config.subscription_id,
        "profile_id": effective_config.profile_id,
        "preset_base": preset_base,
        "preset_bridge": preset_bridge,
        "ytdl_sub_model": ytdl_sub_model,
        "issues": [item.to_dict() for item in issues],
    }

    signature = hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()

    return TranslatedYtdlSubModel(
        subscription_id=effective_config.subscription_id,
        profile_id=effective_config.profile_id,
        preset_base=preset_base,
        preset_bridge=preset_bridge,
        ytdl_sub_model=ytdl_sub_model,
        issues=tuple(issues),
        prepared_translation=prepared,
        translation_signature=signature,
    )


def translate_batch_to_ytdl_sub_model(
    contract: YtdlSubIntegrationContract,
    effective_configs: tuple[EffectiveSubscriptionConfig, ...],
) -> tuple[TranslatedYtdlSubModel, ...]:
    translated = tuple(
        translate_effective_config_to_ytdl_sub_model(contract, item)
        for item in effective_configs
    )
    return tuple(sorted(translated, key=lambda item: item.subscription_id))


def translate_bundle_to_ytdl_sub_model(
    bundle: ParsedConfigBundle,
) -> tuple[TranslatedYtdlSubModel, ...]:
    contract = parse_integration_contract(bundle.raw_documents["ytdl-sub-conf.yaml"])
    effective_configs = resolve_effective_configs(bundle)
    return translate_batch_to_ytdl_sub_model(contract, effective_configs)


def _resolve_base_and_bridge_preset(
    contract: YtdlSubIntegrationContract,
    effective_config: EffectiveSubscriptionConfig,
) -> tuple[str | None, str | None, tuple[TranslationIssue, ...]]:
    issues: list[TranslationIssue] = []

    by_profile = contract.preset_mapping.get(effective_config.profile_id)

    quality_profile = effective_config.resolved_options.get("quality_profile")
    by_bridge = None
    if isinstance(quality_profile, str):
        by_bridge = contract.preset_mapping.get(quality_profile)

    if by_profile and by_bridge and by_profile != by_bridge:
        issues.append(
            TranslationIssue(
                reason_code="PRESET_AMBIGUOUS",
                message=(
                    "preset_mapping conflictivo: "
                    f"profile_id='{effective_config.profile_id}' -> '{by_profile}' "
                    f"y quality_profile='{quality_profile}' -> '{by_bridge}'."
                ),
            )
        )
        return None, None, tuple(issues)

    preset_base = by_profile or by_bridge
    preset_bridge = by_bridge if by_profile and by_bridge else None

    if (
        preset_base is None
        and contract.fallback_policy.on_missing_preset == MissingPresetPolicy.USE_FALLBACK
    ):
        preset_base = contract.fallback_policy.fallback_preset

    if preset_base is None:
        issues.append(
            TranslationIssue(
                reason_code="PRESET_BASE_UNRESOLVED",
                message="No se pudo resolver preset base ni por mapping ni por fallback.",
            )
        )

    return preset_base, preset_bridge, tuple(issues)
