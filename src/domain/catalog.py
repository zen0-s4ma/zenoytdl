from __future__ import annotations

from dataclasses import dataclass

from src.domain.models import (
    DomainValidationError,
    EffectiveConfig,
    GeneralConfig,
    Override,
    PostProcessing,
    Profile,
    Subscription,
    normalize_identifier,
)


@dataclass(frozen=True)
class DomainCatalog:
    general_config: GeneralConfig
    profiles: dict[str, Profile]
    subscriptions: dict[str, Subscription]
    postprocessings: dict[str, PostProcessing]
    overrides: dict[str, Override]

    @classmethod
    def build(
        cls,
        general_config: GeneralConfig,
        profiles: tuple[Profile, ...],
        subscriptions: tuple[Subscription, ...],
        postprocessings: tuple[PostProcessing, ...],
        overrides: tuple[Override, ...],
    ) -> "DomainCatalog":
        profile_map = _build_unique_map(profiles, "profiles")
        subscription_map = _build_unique_map(subscriptions, "subscriptions")
        postprocessing_map = _build_unique_map(postprocessings, "postprocessings")
        override_map = _build_unique_map(overrides, "overrides")

        for subscription in subscriptions:
            if subscription.profile_id not in profile_map:
                raise DomainValidationError(
                    f"subscription.profile_id '{subscription.profile_id}' no existe"
                )
            for override_id in subscription.override_ids:
                override = override_map.get(override_id)
                if not override:
                    raise DomainValidationError(
                        f"subscription.override_id '{override_id}' no existe"
                    )
                if override.profile_id != subscription.profile_id:
                    raise DomainValidationError(
                        "override.profile_id debe coincidir con subscription.profile_id"
                    )

        for profile in profiles:
            for postprocessing_id in profile.postprocessing_ids:
                if postprocessing_id not in postprocessing_map:
                    raise DomainValidationError(
                        f"profile.postprocessing_id '{postprocessing_id}' no existe"
                    )

        return cls(
            general_config=general_config,
            profiles=profile_map,
            subscriptions=subscription_map,
            postprocessings=postprocessing_map,
            overrides=override_map,
        )

    def resolve_effective_config(self, subscription_id: str) -> EffectiveConfig:
        normalized_subscription_id = normalize_identifier(subscription_id, "subscription_id")
        subscription = self.subscriptions.get(normalized_subscription_id)
        if not subscription:
            raise DomainValidationError(f"subscription '{normalized_subscription_id}' no existe")

        profile = self.profiles[subscription.profile_id]
        resolved_options = dict(profile.base_options)
        for override_id in subscription.override_ids:
            resolved_options.update(self.overrides[override_id].options)

        if "source" in resolved_options:
            raise DomainValidationError("'source' es una clave reservada en resolved_options")
        resolved_options["source"] = subscription.source_value
        resolved_options["source_kind"] = subscription.source_kind.value

        profile_postprocessings = tuple(
            self.postprocessings[postprocessing_id]
            for postprocessing_id in profile.postprocessing_ids
        )

        return EffectiveConfig(
            id=f"effective-{subscription.id}",
            subscription_id=subscription.id,
            profile_id=profile.id,
            resolved_options=resolved_options,
            postprocessings=profile_postprocessings,
        )


def _build_unique_map(items: tuple[object, ...], field_name: str) -> dict[str, object]:
    output: dict[str, object] = {}
    for item in items:
        item_id = item.id  # type: ignore[attr-defined]
        if item_id in output:
            raise DomainValidationError(f"{field_name} contiene id duplicado: {item_id}")
        output[item_id] = item
    return output
